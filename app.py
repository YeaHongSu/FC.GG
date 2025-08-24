from flask import Flask, render_template, request, redirect, url_for, session, redirect, send_from_directory
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime, timedelta, timezone
import os
import requests
import pandas as pd
import numpy as np
from config import Config
from flask import flash
from utils.utils import me, you, avg_data, top_n_argmax, top_n_argmin, calculate_time_difference
from utils.data_processing import data_list, data_list_cl, data_label, determine_play_style
from utils.win_utils import calculate_win_improvement
from tier.tier_info import tier
import warnings
import asyncio
import aiohttp
import sqlite3
from flask import jsonify

# 데이터베이스 초기화 함수
def init_db():
    conn = sqlite3.connect('search_data.db')
    c = conn.cursor()
    # 닉네임 검색 기록 테이블에 lv와 tier_image 컬럼 추가
    c.execute('''CREATE TABLE IF NOT EXISTS nickname_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nickname TEXT NOT NULL,
                    lv INTEGER,
                    tier_image TEXT,
                    search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()


# 검색된 닉네임 저장 함수
def save_nickname_search(nickname, lv, tier_image):
    conn = sqlite3.connect('search_data.db')
    c = conn.cursor()
    c.execute('''INSERT INTO nickname_searches (nickname, lv, tier_image) 
                 VALUES (?, ?, ?)''', (nickname, lv, tier_image))
    conn.commit()
    conn.close()


async def fetch_match_data(session, match_id, headers):
    url = f"https://open.api.nexon.com/fconline/v1/match-detail?matchid={match_id}"
    async with session.get(url, headers=headers) as response:
        return await response.json()

async def fetch_all_match_data(matches, headers):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_match_data(session, match_id, headers) for match_id in matches]
        return await asyncio.gather(*tasks)

def get_match_data(matches, headers):
    return asyncio.run(fetch_all_match_data(matches, headers))
   
# Flask 선언
app = Flask(__name__)
app.config.from_object(Config)

# home 화면 
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        character_name = request.form.get('character_name')
        if character_name:
            save_nickname_search(character_name)
            session['character_name'] = character_name
            return redirect(url_for('result'))

    # 많이 검색된 상위 5개 닉네임과 레벨, 티어 이미지 가져오기
    conn = sqlite3.connect('search_data.db')
    c = conn.cursor()
    c.execute('''SELECT nickname, lv, tier_image, COUNT(nickname) as search_count
                 FROM nickname_searches
                 GROUP BY nickname
                 ORDER BY search_count DESC
                 LIMIT 5''')
    top_nicknames = c.fetchall()  # nickname, lv, tier_image를 포함한 리스트
    conn.close()
    
    return render_template('home.html', top_nicknames=top_nicknames)

@app.route('/sitemap.xml')
def serve_sitemap():
    return send_from_directory('.', 'sitemap.xml', mimetype='application/xml')

@app.route('/robots.txt')
def serve_robots():
    return send_from_directory('.', 'robots.txt', mimetype='text/plain')

@app.route('/ads.txt')
def serve_ads():
    return send_from_directory('.', 'ads.txt', mimetype='text/plain')

@app.before_request
def redirect_to_fcgg():
    # www 도메인을 fcgg.kr로 리다이렉트
    if request.host.startswith("www."):
        # 쿼리 스트링이 비어 있지 않은 경우에만 추가
        if request.query_string and request.query_string != b'':
            return redirect(f"https://fcgg.kr{request.path}?{request.query_string.decode('utf-8')}", code=301)
        # 쿼리 스트링이 없으면 ?를 포함하지 않음
        return redirect(f"https://fcgg.kr{request.path}", code=301)

# match_type 값을 이름으로 변환
MATCH_TYPE_MAP = {
    "50": "공식경기",
    "60": "친선경기",
    "52": "감독모드",
    "40": "커스텀매치"
}

REVERSE_MATCH_TYPE_MAP = {v: k for k, v in MATCH_TYPE_MAP.items()}

# 전적 검색 페이지
# 간단한 URL 라우트 및 기존 라우트 통합
@app.route('/전적검색/<character_name>/<match_type_name>', methods=['GET'])
@app.route('/result.html', methods=['GET'])
def result(character_name=None, match_type_name=None):
    try:
        # 간단한 URL 요청 처리
        if character_name and match_type_name:
            # match_type_name을 match_type으로 변환
            match_type = REVERSE_MATCH_TYPE_MAP.get(match_type_name)
            if not match_type:
                flash("잘못된 경기 유형입니다.")
                return redirect(url_for('home'))
        else:
            # 기존 URL 요청 처리
            character_name = request.args.get('character_name')
            match_type = request.args.get('match_type')
            if not character_name or not match_type:
                flash("닉네임 또는 경기 유형이 누락되었습니다.")
                return redirect(url_for('home'))
            
            # match_type을 이름으로 변환
            match_type_name = MATCH_TYPE_MAP.get(match_type)
            if not match_type_name:
                flash("잘못된 경기 유형입니다.")
                return redirect(url_for('home'))

            # 기존 URL 요청을 간단한 URL로 리다이렉트
            return redirect(url_for('result', character_name=character_name, match_type_name=match_type_name), code=301)

        # 닉네임에서 불필요한 공백 제거
        character_name = character_name.strip()
       
        # API key 설정
        headers = {"x-nxopen-api-key": f"{app.config['API_KEY']}"}
        
        # ✅ 유저 닉네임 및 레벨 가져오기
        url_user = f"https://open.api.nexon.com/fconline/v1/id?nickname={character_name}"
        characterName = requests.get(url_user, headers=headers).json()["ouid"]

        url_level = f"https://open.api.nexon.com/fconline/v1/user/basic?ouid={characterName}"
        lv = requests.get(url_level, headers=headers).json()["level"]

        url_division = f"https://open.api.nexon.com/fconline/v1/user/maxdivision?ouid={characterName}"
        division_info = requests.get(url_division, headers=headers).json()

        # ✅ 최근 매치 ID 가져오기 (최근 경기 1개)
        url_recent_matches = f"https://open.api.nexon.com/fconline/v1/user/match?ouid={characterName}&matchtype={match_type}&limit=2"
        recent_matches = requests.get(url_recent_matches, headers=headers).json()
        if not recent_matches:
            return render_template('result.html', my_data={}, match_data=[], level_data={"nickname": character_name, "level": lv, "tier_name": None, "tier_image": None}, match_type=match_type,
                                   max_data=[], min_data=[], data_label=[], jp_num=0, play_style={}, no_recent_matches=True,
                                   players=df_final.to_dict(orient="records") if 'df_final' in globals() and not df_final.empty else [])
        
        recent_match_id = recent_matches[1]  # 가장 최근 경기 ID

        # ✅ 최근 경기의 상세 정보 가져오기
        url_match_detail = f"https://open.api.nexon.com/fconline/v1/match-detail?matchid={recent_match_id}"
        match_data = requests.get(url_match_detail, headers=headers).json()

        # ✅ 해당 경기에서 유저가 사용한 선수 정보 가져오기 (SUB 제외)
        player_list = []
        for match in match_data.get("matchInfo", []):
            if match.get("nickname", "").strip().lower() == character_name.lower():
                for player in match.get("player", []):
                    if player.get("spPosition") != 28:
                        player_list.append({
                            "spId": player.get("spId"),
                            "spPosition": player.get("spPosition")
                        })

        # ✅ 선수 정보 DataFrame 변환
        df_match_players = pd.DataFrame(player_list)

        # ✅ 선수 데이터 요청 (한 번만 실행)
        SPID_URL = "https://open.api.nexon.com/static/fconline/meta/spid.json"
        player_data = requests.get(SPID_URL, headers=headers).json()
        df_player = pd.DataFrame(player_data)
        df_player.rename(columns={"id": "spId", "name": "name"}, inplace=True)

        # ✅ 선수 정보와 매칭 (최종 선수 목록)
        df_final = df_match_players.merge(df_player, on="spId", how="left") if not df_match_players.empty else pd.DataFrame()

        # ★ 추가: 각 선수별 sd_image URL 생성 및 포지션 좌표, 포지션 약어 추가
        if not df_final.empty:
            df_final["sd_image"] = df_final["spId"].apply(
                lambda spId: f"https://fco.dn.nexoncdn.co.kr/live/externalAssets/common/playersAction/p{spId}.png"
            )
            # 포지션 좌표 매핑
            vertical_position_mapping = {
                0:  (50, 90),   # GK (골키퍼 - 가장 하단 중앙)
                1:  (50, 82),   # SW (스위퍼)
                2:  (80, 70),   # RWB (오른쪽 윙백)
                3:  (85, 65),   # RB (오른쪽 수비수)
                4:  (63, 78),   # RCB (오른쪽 중앙 수비수)
                5:  (50, 78),   # CB (중앙 수비수)
                6:  (37, 78),   # LCB (왼쪽 중앙 수비수)
                7:  (15, 65),   # LB (왼쪽 수비수)
                8:  (20, 70),   # LWB (왼쪽 윙백)
                9:  (65, 57),   # RDM (오른쪽 수비형 미드필더)
                10: (50, 57),   # CDM (중앙 수비형 미드필더)
                11: (35, 57),   # LDM (왼쪽 수비형 미드필더)
                12: (85, 35),   # RM (오른쪽 미드필더)
                13: (65, 50),   # RCM (오른쪽 중앙 미드필더)
                14: (50, 50),   # CM (중앙 미드필더)
                15: (35, 50),   # LCM (왼쪽 중앙 미드필더)
                16: (15, 35),   # LM (왼쪽 미드필더)
                17: (80, 35),   # RAM (오른쪽 공격형 미드필더)
                18: (50, 35),   # CAM (중앙 공격형 미드필더)
                19: (20, 35),   # LAM (왼쪽 공격형 미드필더)
                20: (60, 25),   # RF (오른쪽 공격수)
                21: (50, 25),   # CF (중앙 공격수)
                22: (40, 25),   # LF (왼쪽 공격수)
                23: (80, 25),   # RW (오른쪽 윙어)
                24: (65, 20),   # RS (오른쪽 스트라이커; 경우에 따라 다름)
                25: (50, 17),   # ST (센터 스트라이커)
                26: (35, 20),   # LS (왼쪽 스트라이커)
                27: (20, 25)    # LW (왼쪽 윙어)
                # 28: SUB (제외)
            }
            # 포지션 약어 매핑 (예시)
            position_desc = {
                0: "GK", 1: "SW", 2: "RWB", 3: "RB", 4: "RCB", 5: "CB",
                6: "LCB", 7: "LB", 8: "LWB", 9: "RDM", 10: "CDM", 11: "LDM",
                12: "RM", 13: "RCM", 14: "CM", 15: "LCM", 16: "LM", 17: "RAM",
                18: "CAM", 19: "LAM", 20: "RF", 21: "CF", 22: "LF", 23: "RW",
                24: "RS", 25: "ST", 26: "LS", 27: "LW"
            }

            df_final["x_coord"] = df_final["spPosition"].apply(lambda pos: vertical_position_mapping.get(pos, (0, 0))[0])
            df_final["y_coord"] = df_final["spPosition"].apply(lambda pos: vertical_position_mapping.get(pos, (0, 0))[1])
            df_final["pos_desc"] = df_final["spPosition"].apply(lambda pos: position_desc.get(pos, ""))


        # divisionId와 divisionName 매핑 테이블
        division_mapping = [
            {"divisionId": 800, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank0.png"},
            {"divisionId": 900, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank1.png"},
            {"divisionId": 1000, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank2.png"},
            {"divisionId": 1100, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank3.png"},
            {"divisionId": 1200, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank4.png"},
            {"divisionId": 1300, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank5.png"},
            {"divisionId": 2000, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank6.png"},
            {"divisionId": 2100, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank7.png"},
            {"divisionId": 2200, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank8.png"},
            {"divisionId": 2300, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank9.png"},
            {"divisionId": 2400, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank10.png"},
            {"divisionId": 2500, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank11.png"},
            {"divisionId": 2600, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank12.png"},
            {"divisionId": 2700, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank13.png"},
            {"divisionId": 2800, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank14.png"},
            {"divisionId": 2900, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank15.png"},
            {"divisionId": 3000, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank16.png"},
            {"divisionId": 3100, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank17.png"}
        ]
        
        # matchType의 division 가져오기
        match_type_info = next((item for item in division_info if item["matchType"] == int(match_type)), None)
        if match_type_info:
            tier_id = match_type_info.get("division", "정보 없음")
            division_item = next((item for item in division_mapping if item["divisionId"] == tier_id), None)
            if division_item:
                if division_item["divisionName"].startswith("http"):
                    tier_name = None
                    tier_image = division_item["divisionName"]
                else:
                    tier_name = division_item["divisionName"]
                    tier_image = None
            else:
                tier_name = "정보 없음"
                tier_image = None
        else:
            tier_name = "정보 없음"
            tier_image = None

        save_nickname_search(character_name, lv, tier_image)

        level_data = {
            "nickname": character_name,
            "level": lv,
            "tier_name": tier_name,
            "tier_image": tier_image
        }

        # 유저 매치 데이터 25개 불러오기
        response = requests.get(f"https://open.api.nexon.com/fconline/v1/user/match?ouid={characterName}&matchtype={match_type}&limit=25", headers=headers)
        matches = response.json() if response.ok else []
        if not matches:
            return render_template('result.html', my_data={}, match_data=[], level_data=level_data, match_type=match_type,
                                   max_data=[], min_data=[], data_label=[], jp_num=0, play_style={}, no_recent_matches=True,
                                   players=df_final.to_dict(orient="records"))
        
        # match 데이터 가져오기
        match_data_list = get_match_data(matches, headers)
        if not match_data_list:
            return render_template('result.html', level_data=level_data, no_recent_matches=True)

        result_list = []
        imp_data = []
        controller_stats = {"🎮": 0, "⌨️": 0, "탈주": 0}

        for data in match_data_list:
            date = calculate_time_difference(data['matchDate'])
            my_data = me(data, character_name)
            your_data = you(data, character_name)
            imp = data_list(my_data)
            imp2 = data_list(your_data)

            my_controller = my_data['matchDetail'].get('controller', 'Unknown')
            your_controller = your_data['matchDetail'].get('controller', 'Unknown')

            if my_controller is None:
                my_controller = "탈주"
            elif my_controller == 'gamepad':
                my_controller = '🎮'
            elif my_controller == 'keyboard':
                my_controller = '⌨️'

            if your_controller is None:
                your_controller = "탈주"
            elif your_controller == 'gamepad':
                your_controller = '🎮'
            elif your_controller == 'keyboard':
                your_controller = '⌨️'

            if my_controller in controller_stats:
                controller_stats[my_controller] += 1

            w_l = my_data['matchDetail']['matchResult']
            my_goal_total = my_data['shoot']['goalTotal'] if my_data['shoot']['goalTotal'] is not None else 0
            your_goal_total = your_data['shoot']['goalTotal'] if your_data['shoot']['goalTotal'] is not None else 0

            match_data_item = {
                '매치 날짜': date,
                '결과': w_l,
                '플레이어 1 vs 플레이어 2': f'{my_data["nickname"]} vs {your_data["nickname"]}',
                '스코어': f'{my_goal_total} : {your_goal_total}',
                '컨트롤러': f"{my_controller} : {your_controller}"
            }
            result_list.append(match_data_item)

            if imp is None or imp2 is None:
                continue
            imp_data.append(imp)

        most_common_controller = max(controller_stats, key=controller_stats.get)
        if len(imp_data) == 0:
            return render_template('result.html', level_data=level_data, no_recent_matches=True)
        
        filtered_imp_data = [[value for value in row if isinstance(value, (int, float))] for row in imp_data]
        filtered_imp_data = np.array(filtered_imp_data, dtype=float)
        my_avg = np.nanmean(filtered_imp_data, axis=0)
        cl_data = np.array(data_list_cl(avg_data(match_type)))
       
        jp_num = 20
        threshold = 0.9

        max_diff = (my_avg - cl_data) / cl_data
        max_idx, max_values = top_n_argmax(max_diff, jp_num)
        filtered_max_idx = max_idx[:5]
        filtered_max_values = max_values[:5]

        min_diff = (my_avg - cl_data) / cl_data
        min_idx, min_values = top_n_argmin(min_diff, jp_num)
        filtered_min_idx = [idx for idx, value in zip(min_idx, min_values) if abs(value) < threshold][:5]
        filtered_min_values = [value for value in min_values if abs(value) < threshold][:5]

        max_data = list(zip(filtered_max_idx, filtered_max_values))
        min_data = list(zip(filtered_min_idx, filtered_min_values))
        play_style = determine_play_style(max_data, min_data)

        return render_template('result.html', my_data=my_data, match_data=result_list, level_data=level_data, match_type=match_type,
                               max_data=max_data, min_data=min_data, data_label=data_label, jp_num=jp_num,
                               play_style=play_style, most_common_controller=most_common_controller, players=df_final.to_dict(orient="records"))
    except Exception:
        try:
            # 문제가 발생하면 최근 경기의 선수 정보를 다시 시도하여 포함시킵니다.
            url_recent_matches = f"https://open.api.nexon.com/fconline/v1/user/match?ouid={characterName}&matchtype={match_type}&limit=1"
            recent_matches = requests.get(url_recent_matches, headers=headers).json()
            if not recent_matches:
                return render_template('result.html', my_data={}, match_data=[], level_data=level_data, match_type=match_type,
                                       max_data=[], min_data=[], data_label=[], jp_num=0, play_style={}, no_recent_matches=True,
                                       players=df_final.to_dict(orient="records"))
            recent_match_id = recent_matches[0]
            url_match_detail = f"https://open.api.nexon.com/fconline/v1/match-detail?matchid={recent_match_id}"
            match_data = requests.get(url_match_detail, headers=headers).json()
            player_list = []
            for match in match_data.get("matchInfo", []):
                if match.get("nickname", "").strip().lower() == character_name.lower():
                    for player in match.get("player", []):
                        if player.get("spPosition") != 28:
                            player_list.append({
                                "spId": player.get("spId"),
                                "spPosition": player.get("spPosition")
                            })
            df_match_players = pd.DataFrame(player_list)
            SPID_URL = "https://open.api.nexon.com/static/fconline/meta/spid.json"
            player_data = requests.get(SPID_URL, headers=headers).json()
            df_player = pd.DataFrame(player_data)
            df_player.rename(columns={"id": "spId", "name": "name"}, inplace=True)
            df_final = df_match_players.merge(df_player, on="spId", how="left") if not df_match_players.empty else pd.DataFrame()
            if not df_final.empty:
                df_final["sd_image"] = df_final["spId"].apply(lambda spId: f"https://fco.dn.nexoncdn.co.kr/live/externalAssets/common/playersAction/p{spId}.png")
            return render_template('result.html', my_data={}, match_data=[], level_data=level_data, match_type=match_type,
                                   max_data=[], min_data=[], data_label=[], jp_num=0, play_style={}, no_recent_matches=True,
                                   players=[[df_final.to_dict(orient="records")]])
        except Exception:
            flash("닉네임이 존재하지 않거나 경기 수가 부족하여 검색이 불가능합니다.")
            return render_template('home.html')



# 승률개선검색
@app.route('/승률개선검색', methods=['GET', 'POST'])
def wr_imp_new():
    return render_template('wr_imp.html')

# 기존 URL 리다이렉트
@app.route('/wr_imp.html', methods=['GET', 'POST'])
def wr_imp_redirect():
    return redirect(url_for('wr_imp_new'), code=301)



# 승률 개선 솔루션 결과 페이지
@app.route('/승률개선결과/<character_name>/<match_type_name>', methods=['GET'])
@app.route('/wr_result.html', methods=['GET'])
def wr_result(character_name=None, match_type_name=None):
    try:
        if character_name and match_type_name:
            match_type = REVERSE_MATCH_TYPE_MAP.get(match_type_name)
            if not match_type:
                flash("잘못된 경기 유형입니다.")
                return redirect(url_for('home'))
        else:
            character_name = request.args.get('character_name') or session.get('character_name')
            match_type = request.args.get('match_type')

            if not character_name or not match_type:
                flash("닉네임 또는 경기 유형이 누락되었습니다.")
                return redirect(url_for('home'))

            match_type_name = MATCH_TYPE_MAP.get(match_type)
            if not match_type_name:
                flash("잘못된 경기 유형입니다.")
                return redirect(url_for('home'))

            return redirect(
                url_for('wr_result', character_name=character_name, match_type_name=match_type_name),
                code=301
            )

        character_name = character_name.replace(" ", "")
        headers = {"x-nxopen-api-key": f"{app.config['API_KEY']}"}
        urlString = "https://open.api.nexon.com/fconline/v1/id?nickname=" + character_name
        characterName = requests.get(urlString, headers=headers).json()["ouid"]

        urlString = "https://open.api.nexon.com/fconline/v1/user/basic?ouid=" + characterName
        lv = requests.get(urlString, headers=headers).json()["level"]

        level_data = {"nickname": character_name, "level": lv}

        urlString = f"https://open.api.nexon.com/fconline/v1/user/match?ouid={characterName}&matchtype={match_type}&limit=25"
        response = requests.get(urlString, headers=headers)
        matches = response.json()

        if len(matches) <= 5:
            flash("경기 수가 부족하여 검색이 불가능합니다 (최소 5경기가 필요합니다)")
            return redirect(url_for('home'))

        match_data_list = get_match_data(matches, headers)
        result_list = []
        imp_data = []
        w_l_data = []

        for data in match_data_list:
            my_data = me(data, character_name)
            imp = data_list(my_data)
            imp2 = data_list(you(data, character_name))

            w_l = my_data['matchDetail']['matchResult']
            match_data = {'결과': w_l}
            result_list.append(match_data)
            w_l_data.append(w_l)

            if imp is None or imp2 is None:
                continue

            imp_data.append(imp)

        # imp_data에서 숫자 데이터만 필터링
        filtered_imp_data = [[value for value in row if isinstance(value, (int, float))] for row in imp_data]
        padded_imp_data = np.array(filtered_imp_data, dtype=float)

        # 평균 계산
        my_avg = np.nanmean(padded_imp_data, axis=0)

        # `cl_data`를 `my_avg` 길이에 맞추기
        cl_data = np.array(data_list_cl(avg_data(match_type)))

        # 길이 일치
        if cl_data.shape[0] > my_avg.shape[0]:
            cl_data = cl_data[:my_avg.shape[0]]
        elif cl_data.shape[0] < my_avg.shape[0]:
            cl_data = np.pad(cl_data, (0, my_avg.shape[0] - cl_data.shape[0]), constant_values=np.nan)

        # max_diff 및 min_diff 계산
        max_diff = (my_avg - cl_data) / cl_data
        max_idx, max_values = top_n_argmax(max_diff, 20)

        min_diff = (my_avg - cl_data) / cl_data
        min_idx, min_values = top_n_argmin(min_diff, 20)

        # 상위/하위 5개 지표 필터링
        filtered_max_idx = max_idx[:5]
        filtered_max_values = max_values[:5]

        threshold = 0.9

        filtered_min_idx = [idx for idx, value in zip(min_idx, min_values) if abs(value) < threshold][:5]
        filtered_min_values = [value for value in min_values if abs(value) < threshold][:5]

        max_data = zip(filtered_max_idx, filtered_max_values)
        min_data = zip(filtered_min_idx, filtered_min_values)

        top_n, increase_ratio, improved_features_text, original_win_rate, modified_win_rate, win_rate_improvement = calculate_win_improvement(
            padded_imp_data, w_l_data, data_label
        )

        return render_template(
            'wr_result.html',
            my_data=my_data,
            match_data=result_list,
            level_data=level_data,
            max_data=max_data,
            min_data=min_data,
            data_label=data_label,
            top_n=top_n,
            increase_ratio=increase_ratio,
            improved_features_text=improved_features_text,
            original_win_rate=original_win_rate,
            modified_win_rate=modified_win_rate,
            win_rate_improvement=win_rate_improvement
        )

    except Exception as e:
        flash("닉네임이 존재하지 않거나 경기 수가 부족하여 검색이 불가능합니다.")
        return redirect(url_for('home'))


# 선수 티어 페이지
@app.route('/선수티어', methods=['GET', 'POST'])
def player_tier_new():
    tier_list = tier
    return render_template('player_tier.html', tier_forward_list=tier_list)

# 기존 URL 리다이렉트
@app.route('/player_tier.html', methods=['GET', 'POST'])
def player_tier_redirect():
    return redirect(url_for('player_tier_new'), code=301)


# 빠칭코 페이지
@app.route('/빠칭코연습실', methods=['GET', 'POST'])
def random_new():
    return render_template('random.html')

# 기존 URL 리다이렉트
@app.route('/random.html', methods=['GET', 'POST'])
def random_redirect():
    return redirect(url_for('random_new'), code=301)

# 수수료 계산기 페이지
@app.route('/수수료계산기', methods=['GET', 'POST'])
def calculate_new():
    return render_template('calculate.html')

# 기존 URL 리다이렉트
@app.route('/calculate.html', methods=['GET', 'POST'])
def calculate_redirect():
    return redirect(url_for('calculate_new'), code=301)

# SQLite 데이터베이스 경로
DB_PATH = 'community_data.db'

# 데이터베이스 초기화 함수
def initialize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 커뮤니티 게시글 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            nickname TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 초기 데이터 삽입
    # 기존 데이터가 없는 경우에만 삽입
    cursor.execute('SELECT COUNT(*) FROM posts')
    if cursor.fetchone()[0] == 0:  # 데이터가 없을 경우에만 삽입
        cursor.executemany('''
            INSERT INTO posts (id, category, nickname, content, timestamp) 
            VALUES (?, ?, ?, ?, ?)
        ''', [
            (59, '자유게시판', '케리', '흥민이형 거기선 행복해', '2025-08-18 10:00:00'),
            (58, '친추게시판', '방현준', 'dd', '2025-08-05 10:00:00'),
            (57, '자유게시판', 'ㄱㄷㄹ', 'LN급 카드들은 다 걍 유지되거나 떨어질거같으넫', '2025-08-03 10:00:00'),
            (56, '자유게시판', 'ㄱㅁㄱㅂㅇ', 'LN 셰우첸코 금카 가격 오를까요?', '2025-08-02 10:00:00'),
            (55, '자유게시판', '소', '게임 패치 되고 나쁘진 않네', '2025-07-25 10:00:00'),
            (54, '자유게시판', '케케', '요즘 헤더골수 자체가 줄어서 다른 사람대비 상위 지표로 뜰듯?', '2025-07-15 10:00:00'),
            (53, '자유게시판', 'ㅇㅇ', '헤딩골 거의 넣은적없는데 지표젤높은건 뭐지 ?', '2025-07-14 10:00:00'),
            (52, '자유게시판', '몰라', '이상호급 중거리 딸깍!', '2025-07-07 10:00:00'),
            (51, '자유게시판', '예아', '4123 개사기네요 ㄷㄷㄷ', '2025-07-06 19:00:00'),
            (50, '자유게시판', 'FCGM', '닉네임 검색 관련 요청에 대해서는 검토 중에 있습니다. 이용 중 불편을 드려 죄송합니다. 빠른 시일 내에 해결하도록 하겠습니다.', '2025-07-05 14:00:00'),
            (49, '자유게시판', '이수맥', '계정 만든지도 몇달됐고 게임도 몇백판을 했는데 닉네임 검색이 안돼요....', '2025-07-03 14:00:00'),
            (48, '자유게시판', 'fc염', '이사람 게임 지고 패드립하고 나감 ㅋㅋ', '2025-06-20 14:00:00'),
            (47, '자유게시판', '7조', '7조 이벤트 개꿀이네', '2025-05-25 14:00:00'),
            (46, '자유게시판', '그래요', '다행히 2차 전날에 올려둬서 적당히 털었습니다ㅜ', '2025-05-22 14:00:00'),
            (45, '자유게시판', 'kk', 'ㅋㅋㅋㅋ아스날 코인 어떻게됐을까', '2025-05-20 14:00:00'),
            (44, '자유게시판', '하', '하 형님들 아스날 코인 탔는데 2차전 희망있을까요', '2025-05-02 14:00:00'),
            (43, '자유게시판', 'ㅇㅈ', '공경보다 유독 커스텀 매치가 체감 문제 더 심한듯', '2025-04-09 14:00:00'),
            (42, '자유게시판', 'ㄴㄴㄴ', '공식경기 마다 하루가 다르게 선수들 체감이 다르다는게 이해는 하겠습니다 상대의 전술 포메 선수 전부 다르니깐요 그런데 친구나 지인이랑 하는 클랙식 경기는 늘 같은 전술 포메 선수들인데 체감이 어제 오늘 뒤죽박죽 다른건 대체 이유가 뭘까요?? 비유를 하자면 꼭 아침에 출근 하려고 차 시동을 걸고 주행하는데 풀악셀을 밟아도 어제는 100키로 달리던게 오늘은 80키로 달리고 다음 날이면 90키로로 달리고 차가 바뀐것도 아니고 항상 같은 차인데 말입니다 저만 이렇게 느낄까요???', '2025-04-09 13:00:00'),
            (41, '자유게시판', 'FCGM', '안녕하세요, 프리킥 골 비율은 프리킥을 얻고 나서 패스 후 골을 넣어도 골로 적용이 됩니다. 그렇기에 프리킥을 얻고 특정 시간동안 골을 넣으면 프리킥 지표가 높아집니다. 감사합니다.', '2025-03-29 13:00:00'),
            (40, '자유게시판', 'ㅇㅇ', '프리킥골 비율은 뭔 지표인가여 프리킥으로 골 넣은 적 없는데 왜캐 높죠?', '2025-03-28 13:00:00'),
            (39, '자유게시판', '두산케어', '', '2025-03-27 13:00:00'),
            (38, '자유게시판', 'CKM', '몰라요', '2025-03-26 13:00:00'),
            (37, '자유게시판', 'ㅂㅇ', '20일에 나옴', '2025-03-10 13:00:00'),
            (36, '자유게시판', '박칭호', '빠칭코 언제 나옴', '2025-03-09 13:00:00'),
            (35, '자유게시판', '깔룰루', '깔룰루~', '2025-02-19 13:00:00'),
            (34, '자유게시판', '두어', '보통 그러면 신규시즌 8카 선점해서 돈 불려야함', '2025-02-16 13:00:00'),
            (33, '자유게시판', 'AGW펠레', '원래 구단가치117조 정도 되면 보강하기힘듬𓃇𓃇 이제 선수가 이제 넘 비싸네', '2025-02-16 13:00:00'),
            (32, '자유게시판', '수삼', '그나마 첼시..?', '2025-02-08 13:00:00'),
            (31, '자유게시판', '류민지', '수원삼성 유니폼이랑 비슷한 팀 있나요', '2025-02-07 13:00:00'),
            (30, '자유게시판', 'dd', 'ddd', '2025-02-03 13:00:00'),
            (29, '건의사항', '요종도', '자기 선수 뭐쓰는지도 나오게 해주세요', '2025-02-01 13:00:00'),
            (28, '자유게시판', '케케', '토요일인데 내일 업데이트임?', '2025-01-18 13:00:00'),
            (27, '자유게시판', 'ㅌㅁ', '이번에 신규 시즌 나오면 패닉셀 할걸요 그때 ㄱ', '2025-01-12 13:00:00'),
            (26, '자유게시판', '갱드리', '지금 팀 맞추는거 별로임 ?', '2025-01-11 13:00:00'),
            (25, '자유게시판', 'qwerqewr', 'ㅋㅋㅋㅋ넷플 23년 구독', '2025-01-06 13:00:00'),
            (24, '자유게시판', 'ㅈㅂ', '무조건 이번달 말까지 존버', '2025-01-02 13:00:00'),
            (23, '자유게시판', '패키지', '멤버십 패키지 ㅊㅊ점', '2024-12-31 13:00:00'),
            (22, '자유게시판', 'ㅁㄴㅇ', 'ㅁㄴㅇㅁㄹ', '2024-12-30 13:00:00'),
            (21, '자유게시판', 'ㅁㄴㅇㄹ', 'ㅁㄴㅇㄹ', '2024-12-27 13:00:00'),
            (20, '자유게시판', 'ㅇ', '80포 모은걸로 상자 다까고 나머지로 20포 돌리는거', '2024-12-21 13:00:00'),
            (19, '자유게시판', '이벤', '님들 그 다오있는 이벤트 80포 모으는게 베스트?', '2024-12-20 13:00:00'),
            (18, '키보드게시판', '부르노', 'ㅇㅇ 일록님 z키 맞음', '2024-12-20 13:00:00'),
            (17, '자유게시판', '견태', '견사합니다', '2024-12-17 13:00:00'),
            (16, '자유게시판', '마테우스', '부산아재x견태 저분 인플루언서인가요?', '2024-12-17 13:00:00'),
            (15, '자유게시판', '앙리', '부산아재 견태가 뭔데 1위임??', '2024-12-17 13:00:00'),
            (14, '키보드게시판', '윤일록', '라인 의도적으로 내리려면 shift+<이고, 선수 패스 받으러 내려오게 하려면 그냥 z키? 이거 맞나요?', '2024-12-17 13:00:00'),
            (13, '자유게시판', '4222', '4222 그 LS랑 RF 버전인가요?', '2024-12-08 13:00:00'),
            (12, '키보드게시판', '워싱시', '키보드슈챔중에 4222 쓰는사람꺼 쓰생', '2024-12-04 13:00:00'),
            (11, '자유게시판', 'riqoeo', '5일까지 존버 ㄱ', '2024-12-01 13:00:00'),
            (10, '자유게시판', '현질', '10000fc정도 있는데 빠칭코가 효율 가장 좋나요', '2024-11-30 13:00:00'),
            (9, '키보드게시판', '하요', '하이용', '2024-11-25 13:00:00'),
            (8, '자유게시판', 'ds', '아약스 센백 추천 금카기준', '2024-11-25 13:00:00'),
            (7, '자유게시판', '모룽이', '아약스 가성비로 23NG 바시 추천', '2024-11-25 13:00:00'),
            (6, '키보드게시판', 'qwer', '키보드로 퍼터 대각선으로 치는 법 있나요? 자꾸 삑이 납니다. 현 월클 2부입니다..', '2024-11-25 13:00:00'),
            (5, '패드게시판', '패추', '패드 입문 하려능데 추천 점', '2024-11-25 13:00:00'),
            (4, '패드게시판', 'toto', '패드 무선 5만원짜리 조이트론 다이어울프 ㅊㅊ', '2024-11-25 13:00:00'),
            (3, '패드게시판', '루치치', '패드유저인데 키를 입력하면 3초쯤 뒤에 이상하게 먹히던데 어떻게 해야되죠?', '2024-11-26 13:00:00'),
            (2, '패드게시판', '뽀로로', '투치치님 저는 전에 스팀 켜져있어서 키입력 오류 있었슴다 한번 다른 창들 다 꺼놓고 ㄱㄱ연', '2024-11-26 13:00:00'),
            (1, '키보드게시판', '워킹데', '원래 삑 많아 나서 동시에 누르는게 최선', '2024-11-27 13:00:00')
        ])

    conn.commit()
    conn.close()

# 초기화 실행
initialize_database()

# 시간 차이를 계산하는 필터
@app.template_filter('timeago')
def timeago_filter(timestamp):
    # 한국 표준시 시간대를 정의
    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(tz=kst)
    
    try:
        # 입력된 timestamp를 datetime 객체로 변환 (한국 시간으로 변환 필요)
        input_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        # 입력 시간을 KST로 설정
        input_time = input_time.replace(tzinfo=timezone.utc).astimezone(kst)
    except ValueError:
        # 잘못된 포맷의 경우 예외 처리
        return "날짜 오류"
    
    # 시간 차이 계산
    time_difference = current_time - input_time

    # 시간 차이에 따른 결과 반환
    if time_difference < timedelta(days=1):
        hours_diff = int(time_difference.total_seconds() // 3600)
        minutes_diff = int((time_difference.total_seconds() % 3600) // 60)
        if hours_diff == 0:
            if minutes_diff <= 1:
                return "방금 전"
            else:
                return f"{minutes_diff}분 전"
        elif hours_diff == 1:
            return "1시간 전"
        else:
            return f"{hours_diff}시간 전"
    else:
        days_diff = time_difference.days
        if days_diff == 1:
            return "1일 전"
        else:
            return f"{days_diff}일 전"

# 커뮤니티 작성 폼 정의
class CommunityForm(FlaskForm):
    nickname = StringField('닉네임', validators=[DataRequired()])
    category = SelectField('카테고리', choices=[
        ('자유게시판', '자유게시판'),
        ('키보드게시판', '키보드게시판'),
        ('패드게시판', '패드게시판'),
        ('친추게시판', '친추게시판'),
        ('건의사항', '건의사항')
    ], validators=[DataRequired()])
    content = TextAreaField('내용', validators=[DataRequired()])
    submit = SubmitField('작성하기')

# 전체 커뮤니티 페이지
@app.route('/커뮤니티', methods=['GET', 'POST'])
def community_new():
    form = CommunityForm()
    if form.validate_on_submit():
        nickname = form.nickname.data
        category = form.category.data
        content = form.content.data

        # 게시글 DB 저장
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO posts (category, nickname, content) VALUES (?, ?, ?)', (category, nickname, content))
        conn.commit()
        conn.close()

        return redirect(url_for('community_new'))

    # 전체 게시글 데이터 로드
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, category, nickname, content, timestamp FROM posts ORDER BY timestamp DESC')
    posts = cursor.fetchall()
    conn.close()

    return render_template('community.html', form=form, posts=posts, selected_category="전체")

@app.route('/커뮤니티/<category>', methods=['GET', 'POST'])
def community_category(category):
    form = CommunityForm()
    if form.validate_on_submit():
        nickname = form.nickname.data
        content = form.content.data

        # 게시글 DB 저장
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO posts (category, nickname, content) VALUES (?, ?, ?)', (category, nickname, content))
        conn.commit()
        conn.close()

        return redirect(url_for('community_category', category=category))

    # 선택된 카테고리의 게시글만 가져오기
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, category, nickname, content, timestamp FROM posts WHERE category = ? ORDER BY timestamp DESC', (category,))
    posts = cursor.fetchall()
    conn.close()

    return render_template('community.html', form=form, posts=posts, selected_category=category)

# 기존 URL 리다이렉트
@app.route('/community.html', methods=['GET', 'POST'])
def community_redirect():
    return redirect(url_for('community_new'), code=301)

# 빠칭코 페이지
@app.route('/현질을 안 했다면?', methods=['GET', 'POST'])
def fun_new():
    return render_template('fun.html')

# 기존 URL 리다이렉트
@app.route('/fun.html', methods=['GET', 'POST'])
def fun_redirect():
    return redirect(url_for('fun_new'), code=301)

@app.route("/kakao/skill", methods=["POST"])
def kakao_skill():
    try:
        body = request.get_json(silent=True) or {}

        # ① 사용자가 친 원문(멘션/명령어 포함) 한 줄
        utter = ((body.get("userRequest") or {}).get("utterance") or "").strip()

        # ② 기존처럼 오픈빌더가 주면 우선 사용
        def _p(key):
            return (
                (body.get("action", {}).get("params", {}) or {}).get(key)
                or (body.get("detailParams", {}).get(key, {}) or {}).get("value")
                or ""
            )
        nick = _p("nick").strip()
        mode = _p("mode").strip()

        # ③ 비어있으면 utterance에서 직접 파싱
        if not nick or not mode:
            # 모드 동의어 테이블 (원하는 대로 추가 가능)
            MODE_SYNONYMS = {
                "50": ["50", "공식경기", "공식", "공경", "랭크", "랭겜"],
                "60": ["60", "친선경기", "친선", "클래식", "클겜"],
                "52": ["52", "감독모드", "감독", "감모"],
                "40": ["40", "커스텀매치", "커스텀", "커겜"],
            }
            WORD2CODE = {w: code for code, words in MODE_SYNONYMS.items() for w in words}

            # "@피파봇 전적검색 모설 공식경기" → "모설 공식경기"
            text = re.sub(r"\s+", " ", utter)
            text = re.sub(r"^@\S+\s*", "", text)                 # @멘션 제거
            text = re.sub(r"^(전적검색|전적|검색)\s*", "", text)  # 명령어 제거

            tokens = text.split(" ") if text else []

            # 뒤에서부터 모드(동의어/숫자) 찾기
            found_mode = ""
            for i in range(len(tokens) - 1, -1, -1):
                t = tokens[i]
                if t in WORD2CODE:           # 한글 동의어 → 코드
                    found_mode = WORD2CODE[t]
                    tokens.pop(i)
                    break
                if t in MODE_SYNONYMS:       # 숫자 코드 그대로 들어온 경우
                    found_mode = t
                    tokens.pop(i)
                    break

            found_nick = " ".join(tokens).strip()

            if not nick:
                nick = found_nick
            if not mode:
                mode = found_mode

        # 2) 모드가 한글로 왔을 수도 있으니 최종 맵핑 한번 더
        mode = REVERSE_MATCH_TYPE_MAP.get(mode, mode)

        # 3) 필수 체크
        if not nick or not mode:
            ex = "예) 전적검색 모설 공식경기 / 전적검색 모설 50"
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [
                        {"simpleText": {"text": f"닉네임과 모드를 인식하지 못했어요.\n{ex} 형태로 입력해 주세요."}}
                    ]
                }
            })

        # ------------------ 아래부터는 기존 요약/카드 생성 로직 동일 ------------------
        headers = {"x-nxopen-api-key": f"{app.config['API_KEY']}"}

        # 기본정보
        ouid = requests.get(
            f"https://open.api.nexon.com/fconline/v1/id?nickname={nick}",
            headers=headers, timeout=1.8
        ).json()["ouid"]

        lv = requests.get(
            f"https://open.api.nexon.com/fconline/v1/user/basic?ouid={ouid}",
            headers=headers, timeout=1.8
        ).json()["level"]

        # 티어 이미지
        division_info = requests.get(
            f"https://open.api.nexon.com/fconline/v1/user/maxdivision?ouid={ouid}",
            headers=headers, timeout=1.8
        ).json()
        division_mapping = [
            {"divisionId": 800, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank0.png"},
            {"divisionId": 900, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank1.png"},
            {"divisionId": 1000, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank2.png"},
            {"divisionId": 1100, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank3.png"},
            {"divisionId": 1200, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank4.png"},
            {"divisionId": 1300, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank5.png"},
            {"divisionId": 2000, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank6.png"},
            {"divisionId": 2100, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank7.png"},
            {"divisionId": 2200, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank8.png"},
            {"divisionId": 2300, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank9.png"},
            {"divisionId": 2400, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank10.png"},
            {"divisionId": 2500, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank11.png"},
            {"divisionId": 2600, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank12.png"},
            {"divisionId": 2700, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank13.png"},
            {"divisionId": 2800, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank14.png"},
            {"divisionId": 2900, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank15.png"},
            {"divisionId": 3000, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank16.png"},
            {"divisionId": 3100, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2009/ico_rank17.png"},
        ]
        tier_image = None
        try:
            mt = int(mode)
            mt_info = next((i for i in division_info if i.get("matchType") == mt), None)
            if mt_info:
                div = mt_info.get("division")
                m = next((d for d in division_mapping if d["divisionId"] == div), None)
                tier_image = (m or {}).get("divisionName")
        except Exception:
            pass

        # 최근 25경기 → 승/패/승률 + 플레이스타일
        matches = requests.get(
            f"https://open.api.nexon.com/fconline/v1/user/match?ouid={ouid}&matchtype={mode}&limit=25",
            headers=headers, timeout=1.8
        ).json()

        wins = losses = 0
        win_rate_text = "데이터 없음"
        play_style_text = "플레이스타일 분석 불가"

        if matches:
            match_data_list = get_match_data(matches, headers)
            results, imp_data = [], []
            for data in match_data_list:
                my = me(data, nick)
                results.append(my["matchDetail"]["matchResult"])
                imp = data_list(my)
                if imp: imp_data.append(imp)

            total = len(results)
            wins = sum(1 for r in results if r == "승")
            losses = sum(1 for r in results if r == "패")
            if total:
                win_rate_text = f"{round(wins/total*100, 2)}%"

            if imp_data:
                filt = [[v for v in row if isinstance(v, (int, float))] for row in imp_data]
                my_avg = np.nanmean(np.array(filt, dtype=float), axis=0)
                cl = np.array(data_list_cl(avg_data(mode)))
                diff = (my_avg - cl) / cl
                max_idx, max_vals = top_n_argmax(diff, 20)
                min_idx, min_vals = top_n_argmin(diff, 20)
                threshold = 0.9
                max_data = list(zip(max_idx[:5], max_vals[:5]))
                min_data = [(i, v) for i, v in zip(min_idx, min_vals) if abs(v) < threshold][:5]
                play_style = determine_play_style(max_data, min_data)
                play_style_text = play_style.get("summary", str(play_style)) if isinstance(play_style, dict) else str(play_style)

        result_url = f"https://fcgg.kr/result.html?character_name={nick}&match_type={mode}"

        card = {
            "basicCard": {
                "title": nick,
                "description": f"【플레이스타일】 {play_style_text}\n\n레벨  {lv}\n승    {wins}\n패    {losses}\n승률  {win_rate_text}",
                "thumbnail": {"imageUrl": tier_image} if tier_image else None,
                "buttons": [
                    {"label": "자세히 보기", "action": "webLink", "webLinkUrl": result_url},
                    {"label": "최근 전적 보기", "action": "webLink", "webLinkUrl": result_url}
                ]
            }
        }
        if not tier_image:
            del card["basicCard"]["thumbnail"]

        return jsonify({"version": "2.0", "template": {"outputs": [card]}})

    except Exception:
        return jsonify({
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": "분석 중 오류가 발생했습니다. 다시 시도해 주세요."}}]}
        })




# 포트 설정 및 웹에 띄우기
# 초기화 실행 및 Flask 앱 실행
if __name__ == '__main__':
    init_db()  # 데이터베이스 및 테이블 생성
    app.run('0.0.0.0', port=3000, debug=True)
