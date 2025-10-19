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
import re
from urllib.parse import quote_plus

import time
import functools
from functools import lru_cache


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

# 공피하기
@app.route('/공피하기', methods=['GET', 'POST'])
def ball_new():
    return render_template('ball_game.html')

# 기존 URL 리다이렉트
@app.route('/ball_game.html', methods=['GET', 'POST'])
def ball_redirect():
    return redirect(url_for('ball_new'), code=301)



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

            
            if imp is None or imp2 is None:
                continue
            
            w_l = my_data['matchDetail']['matchResult']
            match_data = {'결과': w_l}
            result_list.append(match_data)
            w_l_data.append(w_l)

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
            (65, '자유게시판', '오잉', '모바일로는 감모밖에 안되는거 아님? 모바일 감모는 전적에 뜨던데요', '2025-09-12 10:00:00'),
            (64, '자유게시판', 'zz', 'zz', '2025-09-11 10:00:00'),
            (63, '자유게시판', '메루', '모바일로도 공식경기하면 전적에 표시되나?', '2025-09-11 11:00:00'),
            (62, '자유게시판', 'ㄲㄲ', '클로제 개사기 무조건 쓰셈ㅋ', '2025-08-28 10:00:00'),
            (61, '건의사항', '흠냐', '상위, 하위 지표 관련해서 랭커대비 700% 높다고 나와도 크게 체감이 안되는데 좀더 세부적인 데이터로 볼수있게는 안될까요', '2025-08-27 10:00:00'),
            (60, '키보드게시판', '키보드', '아무도없나', '2025-08-26 10:00:00'),
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

from io import BytesIO
from PIL import Image, ImageOps
import requests
from flask import send_file, request

@app.route("/tierbadge")
def tierbadge():
    url = request.args.get("url", "")
    size = int(request.args.get("size", 480))   # 아이콘 실제 크기
    bg_w, bg_h = 1000, 600                      # 카드에 보낼 전체 캔버스

    r = requests.get(url, timeout=2)
    icon = Image.open(BytesIO(r.content)).convert("RGBA")
    icon = ImageOps.contain(icon, (size, size))

    bg = Image.new("RGBA", (bg_w, bg_h), (255, 255, 255, 255))
    x = (bg_w - icon.width)//2
    y = (bg_h - icon.height)//2
    bg.paste(icon, (x, y), icon)

    buf = BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/kakao/skill", methods=["POST"])
def kakao_skill():
    """
    - 모든 모드 별칭을 즉시 숫자 코드(50/60/52/40)로 정규화
    - '친선경기/친선/클래식/클겜'과 '커스텀매치/커스텀/커겜' 제대로 동작
    - 전적검색/승률개선 공통, 5초 제약 대비 경량화 유지
    """
    try:
        import time, re

        t0 = time.time()

        # ---- 튜닝 ----
        API_TIMEOUT = 1.2
        MAX_DETAIL  = 25
        TIME_BUDGET = 4.2

        # ---- 유틸 ----
        def now(): return time.time()

        def json_get(url, params, headers, timeout=API_TIMEOUT):
            import requests
            try:
                r = requests.get(url, params=params, headers=headers, timeout=timeout)
                return r.json()
            except Exception:
                return {}

        def kakao_text(msg):
            return jsonify({"version":"2.0","template":{"outputs":[{"simpleText":{"text":msg}}]}})

        def pick_tier_image(division_info, mode_code):
            try:
                mt = int(mode_code)
                mt_info = next((i for i in (division_info or []) if i.get("matchType") == mt), None)
                if not mt_info:
                    return None
                div = mt_info.get("division")
                m = next((d for d in division_mapping if d["divisionId"] == div), None)
                return (m or {}).get("divisionName")
            except Exception:
                return None

        # ---------- 바디/발화 파싱 ----------
        body = request.get_json(silent=True) or {}
        utter = ((body.get("userRequest") or {}).get("utterance") or "").strip()
        # print(((body.get("userRequest")).get("block")).get("id"))
        JJ_id = "68a44ed5d2032812d4a7df8b"
        SL_id = "68b4464f171fb452df215e52"

        CMD_SYNONYMS = {
            "전적검색": ["전적검색", "전적", "검색"],
            "승률개선": ["승률개선", "승개", "개선", "개선검색", "승률"]
        }
        WORD2CMD = {w: cmd for cmd, words in CMD_SYNONYMS.items() for w in words}

        def _p(key):
            return (
                (body.get("action", {}).get("params", {}) or {}).get(key)
                or (body.get("detailParams", {}).get(key, {}) or {}).get("value")
                or ""
            )

        # 파라미터
        nick = (_p("nick") or "").strip()

        # 발화 전처리
        text = re.sub(r"\s+", " ", utter)
        text = re.sub(r"^@\S+\s*", "", text)  # @피파봇 제거
        tokens = text.split(" ") if text else []

        # 명령어 탐지
        found_cmd = ""
        for i, t in enumerate(list(tokens)):
            if t in WORD2CMD:
                found_cmd = WORD2CMD[t]
                tokens.pop(i)
                break
        if not found_cmd:
            found_cmd = "전적검색"

        # 남은 토큰 = 닉네임(공백 허용)
        found_nick = " ".join(tokens).strip()

        nick = nick or found_nick
        mode = "50"

        if not nick or not mode:
            return kakao_text("닉네임/모드를 인식하지 못했어요.")

        # ---------- 기본 정보 조회 ----------
        headers = {"x-nxopen-api-key": f"{app.config['API_KEY']}"}

        j = json_get("https://open.api.nexon.com/fconline/v1/id",
                     {"nickname": nick}, headers)
        ouid = j.get("ouid")
        if not ouid:
            return kakao_text(f"'{nick}' 유저를 찾지 못했습니다.")

        if now() - t0 > TIME_BUDGET:
            result_url = f"https://fcgg.kr/전적검색/{nick}/공식경기"
            imp_url    = f"https://fcgg.kr/승률개선결과/{nick}/공식경기"
            return jsonify({"version":"2.0","template":{"outputs":[{
                "basicCard":{
                    "title": f"{nick}",
                    "description":"네트워크 지연으로 간단 요약만 제공해요. 버튼으로 상세 페이지에서 확인하세요.",
                    "buttons":[
                        {"label":"전적 자세히 보기","action":"webLink","webLinkUrl":result_url},
                        {"label":"승률개선","action":"webLink","webLinkUrl":imp_url},
                    ]
                }
            }]}})

        basic = json_get("https://open.api.nexon.com/fconline/v1/user/basic",
                         {"ouid": ouid}, headers)
        lv = basic.get("level", "?")

        # 티어 이미지(여유 있을 때만)
        tier_image = None
        if now() - t0 < TIME_BUDGET - 0.5:
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
            divi = json_get("https://open.api.nexon.com/fconline/v1/user/maxdivision",
                            {"ouid": ouid}, headers)
            tier_image = pick_tier_image(divi, mode)

        badge_url = None
        if tier_image:
            public_root = app.config.get("PUBLIC_ROOT", request.url_root.rstrip("/"))
            # badge_url = f"{public_root}/tierbadge?url={quote_plus(tier_image)}&size=240&bgw=1000&bgh=600"
            badge_url = f"{public_root}/tierbadge?url={quote_plus(tier_image)}&size=480&bgw=1000&bgh=600"

        # ---------- 최근 경기 ----------
        if now() - t0 > TIME_BUDGET - 1.5:
            result_url = f"https://fcgg.kr/전적검색/{nick}/공식경기"
            imp_url    = f"https://fcgg.kr/승률개선결과/{nick}/공식경기"
            return jsonify({"version":"2.0","template":{"outputs":[{
                "basicCard":{
                    "title": f"{nick} · Lv.{lv}",
                    "description":"요청이 많아 간단 요약만 보여드려요. 상세 전적은 버튼으로 확인해 주세요.",
                    # **({"thumbnail":{"imageUrl":tier_image, "width":1600,"height":1600}} if tier_image else {}),
                    **({"thumbnail":{"imageUrl": badge_url}} if badge_url else {}),
                    "buttons":[
                        {"label":"전적 자세히 보기","action":"webLink","webLinkUrl":result_url},
                        {"label":"승률개선","action":"webLink","webLinkUrl":imp_url},
                    ]
                }
            }]}})

        matches = json_get("https://open.api.nexon.com/fconline/v1/user/match",
                           {"ouid": ouid, "matchtype": mode, "limit": MAX_DETAIL},
                           headers)

        # ---------- 경량 상세/계산 ----------
        win_rate_text = "데이터 없음"
        play_style_text = "플레이스타일 분석 불가"
        original_win_rate = modified_win_rate = win_rate_improvement = None
        improved_features_text = ""

        if matches and (now() - t0) < TIME_BUDGET - 0.3:
            match_data_list = get_match_data(matches[:MAX_DETAIL], headers)

            results, w_l_data, imp_rows = [], [], []
            for data in match_data_list or []:
                my = me(data, nick)
                opp = you(data, nick)
                row = data_list(my)
                opp_row = data_list(opp)
                if row is None or opp_row is None:
                    continue
                res = my["matchDetail"]["matchResult"]
                results.append(res); w_l_data.append(res); imp_rows.append(row)

            total = len(results)
            wins = sum(1 for r in results if r == "승")
            if total:
                win_rate_text = f"{wins / total * 100:.2f}%"

            if imp_rows and (now() - t0) < TIME_BUDGET - 0.2:
                import numpy as np
                filt = [[v for v in row if isinstance(v, (int, float))] for row in imp_rows]
                my_avg = np.nanmean(np.array(filt, dtype=float), axis=0)

                cl = np.array(data_list_cl(avg_data(mode)))
                diff = (my_avg - cl) / cl

                max_idx, max_vals = top_n_argmax(diff, 20)
                min_idx, min_vals = top_n_argmin(diff, 20)
                threshold = 0.9
                max_data = list(zip(max_idx[:5], max_vals[:5]))
                min_data = [(i, v) for i, v in zip(min_idx, min_vals) if abs(v) < threshold][:5]

                style = determine_play_style(max_data, min_data)
                play_style_text = style.get("summary", str(style)) if isinstance(style, dict) else str(style)

                if found_cmd == "승률개선" and (now() - t0) < TIME_BUDGET - 0.4:
                    try:
                        padded_imp = np.array(filt, dtype=float)
                        (
                            top_n,
                            increase_ratio,
                            improved_features_text,
                            original_win_rate,
                            modified_win_rate,
                            win_rate_improvement,
                        ) = calculate_win_improvement(padded_imp, w_l_data, data_label)
                    except Exception:
                        original_win_rate = modified_win_rate = win_rate_improvement = None
                        improved_features_text = ""

        # ---------- 카드 ----------
        MATCH_TYPE_MAP = globals().get("MATCH_TYPE_MAP", {})
        result_url = f"https://fcgg.kr/전적검색/{nick}/공식경기"
        imp_url    = f"https://fcgg.kr/승률개선결과/{nick}/공식경기"

        if found_cmd == "승률개선":
            if (original_win_rate is not None and
                modified_win_rate is not None and
                win_rate_improvement is not None):
                head = f"{nick}  Lv.{lv}"
                body_lines = [
                    "",
                    "【개선 시 승률】\n"
                    f"{original_win_rate * 100:.2f}% ➜ {modified_win_rate * 100:.2f}% "
                    f"(＋{win_rate_improvement * 100:.2f}%p)\n\n"
                    "【개선해야하는 지표】"
                ]
                if improved_features_text:
                    feat_lines = [ln.strip() for ln in improved_features_text.splitlines() if ln.strip()]
                    feat_lines = feat_lines[:5] if len(feat_lines) > 5 else feat_lines
                    body_lines.extend(feat_lines)
                else:
                    body_lines.append("분석 데이터가 부족합니다.")
                description = head + "\n" + "\n".join(body_lines)
                card = {
                    "basicCard": {
                        "title": "승률 개선 솔루션",
                        "description": description,
                        # "thumbnail": {"imageUrl": tier_image} if tier_image else {},
                        "thumbnail": {"imageUrl": badge_url} if badge_url else {},
                        "buttons": [
                            {"label": "승률개선 자세히 보기", "action": "webLink", "webLinkUrl": imp_url},
                            # {"label": "전적검색", "action": "webLink", "webLinkUrl": result_url},
                            {"label": "전적검색",  "action": "block", "blockId": JJ_id, 
                            "extra":{"params":{"nick": nick}}}
                        ]
                    }
                }
            else:
                return jsonify({"version":"2.0","template":{"outputs":[{"simpleText":{"text":"최근 전적 경기 수가 부족합니다."}}]}})
                # # 개선 계산 실패/데이터 부족 폴백
                # description = (
                #     f"{nick}  Lv.{lv}\n\n"
                #     "[개선 시 승률]\n"
                #     "분석 데이터가 부족합니다.\n\n"
                #     "[개선해야하는 지표]\n"
                #     "최근 경기가 충분하지 않거나 일부 지표가 누락되었습니다."
                # )
                # card = {
                #     "basicCard": {
                #         "title": "승률 개선 솔루션",
                #         "description": description,
                #         **({"thumbnail": {"imageUrl": tier_image, "width":1600,"height":1600}} if tier_image else {}),
                #         "buttons": [
                #             {"label": "승률개선 자세히 보기", "action": "webLink", "webLinkUrl": imp_url},
                #             # {"label": "전적검색",  "action": "webLink", "webLinkUrl": result_url},
                #             {"label": "전적검색",  "action": "block", "blockId": JJ_id, 
                #             "extra":{"params":{"nick": nick}}}
                #         ]
                #     }
                # }
        else:
            if len(matches) == 0:
                return jsonify({"version":"2.0","template":{"outputs":[{"simpleText":{"text":"최근 전적 경기 수가 부족합니다."}}]}})
            title = f"{nick} · Lv.{lv}"
            desc_common = f"승률  {win_rate_text}\n【플레이스타일】\n {play_style_text}"
            card = {
                "basicCard": {
                    "title": title,
                    "description": f"{desc_common}\n\n 최근 {min(len(matches or []), MAX_DETAIL)}경기 기반 전적입니다.",
                    # **({"thumbnail": {"imageUrl": tier_image, "width":16,"height":16}} if tier_image else {}),
                    **({"thumbnail": {"imageUrl": badge_url}} if badge_url else {}),
                    "buttons": [
                        {"label": "전적 자세히 보기",  "action": "webLink", "webLinkUrl": result_url},
                        # {"label": "승률개선", "action": "webLink", "webLinkUrl": imp_url},
                        {"label": "승률개선",  "action": "block", "blockId": SL_id, 
                        "extra":{"params":{"nick": nick}}}
                    ]
                }
            }

        return jsonify({"version":"2.0","template":{"outputs":[card]}})

    except Exception:
        return jsonify({
            "version":"2.0",
            "template":{"outputs":[{"simpleText":{"text":"분석 중 오류가 발생했습니다. 다시 시도해 주세요."}}]}
        })




# -------------------------------------------
# [NEW] 티어리스트 전용 Kakao 스킬 엔드포인트: /kakao/skill2
# - 오픈빌더에서 이 URL만 새 스킬로 연결하면 동작
# - 파라미터: position(선택, 예: ST/공격수/공미/수미/GK 등), top(선택, 기본 5)
# - 발화 예: "티어리스트 ST", "티어리스트 공격수", "티어 ST"
# -------------------------------------------

# === helpers: position normalize & top-n extraction ===
POS_SYNONYMS = {
    "ST": ["ST", "공격수", "스트라이커", "포워드", "원톱", "투톱"],
    "CF": ["CF", "세컨톱"],
    "LW": ["LW", "레프트윙", "왼윙"],
    "RW": ["RW", "라이트윙", "오윙"],
    "CAM": ["CAM", "공미", "공격형미드"],
    "CM": ["CM", "중미", "중앙미드"],
    "CDM": ["CDM", "수미", "수비형미드"],
    "LB": ["LB", "레프트백", "왼쪽풀백"],
    "RB": ["RB", "라이트백", "오른쪽풀백"],
    "CB": ["CB", "센터백", "중앙수비"],
    "GK": ["GK", "골키퍼", "키퍼"],
}
WORD2POS = {alias: pos for pos, aliases in POS_SYNONYMS.items() for alias in aliases}

# 티어 노출 우선순위
TIER_ORDER = ["0티어", "1티어", "2티어", "3티어", "4티어"]

def normalize_position(text: str, default="ST"):
    if not text:
        return default
    # 영문 대문자 우선 처리
    t = text.strip().upper()
    if t in WORD2POS:
        return WORD2POS[t]
    # 한글 별칭 그대로 들어온 경우
    return WORD2POS.get(text.strip(), default)

def get_top_players(position_code: str, top_n: int = 5):
    """tier[position]에서 상위 티어 순으로 최대 top_n명 추출"""
    data = tier.get(position_code, {})
    rows = []
    for tier_name in TIER_ORDER:
        for p in data.get(tier_name, []):
            rows.append({
                "tier_name": tier_name,
                "name": p.get("선수 이름", ""),
                "mini": p.get("미니페이스온", ""),
                "season": p.get("시즌", ""),
                "score": p.get("FC스코어", ""),
                "apps": p.get("출전", "")
            })
            if len(rows) >= top_n:
                return rows
    return rows

@app.route("/kakao/skill2", methods=["POST"])
def kakao_skill2_tierlist():
    try:
        body = request.get_json(silent=True) or {}
        utter = ((body.get("userRequest") or {}).get("utterance") or "").strip()

        def _p(key):
            return (
                (body.get("action", {}).get("params", {}) or {}).get(key)
                or (body.get("detailParams", {}).get(key, {}) or {}).get("value")
                or ""
            )

        # 1) 파라미터 우선
        param_pos = (_p("position") or "").strip()
        param_top = (_p("top") or "").strip()

        # 2) 발화에서 포지션 추정 (예: "티어리스트 ST", "티어 공격수")
        import re
        text = re.sub(r"\s+", " ", utter)
        text = re.sub(r"^@\S+\s*", "", text)  # @봇 제거
        tokens = text.split(" ") if text else []

        found_pos = ""
        for i, t in enumerate(list(tokens)):
            tt = t.strip()
            if tt in WORD2POS:
                found_pos = WORD2POS[tt]
                break

        # 최종 포지션/탑N
        pos_code = normalize_position(param_pos or found_pos or "ST")
        try:
            top_n = int(param_top) if param_top else 5
            top_n = max(1, min(top_n, 8))  # listCard 너무 길지 않게 1~8 제한
        except Exception:
            top_n = 5

        # 3) 데이터 추출
        rows = get_top_players(pos_code, top_n=top_n)
        if not rows:
            return jsonify({
                "version": "2.0",
                "template": {"outputs": [
                    {"simpleText": {"text": "해당 포지션의 티어 데이터를 찾지 못했어요."}}
                ]}
            })

        # 4) listCard 구성
        items = []
        for i, r in enumerate(rows, 1):
            title = f"{i}. {r['name']}"
            desc  = f"{r['tier_name']} | FC스코어:{r['score']} | 출전:{r['apps']}"
            image = r["mini"] or r["season"] or None
            item = {"title": title, "description": desc}
            if image:
                item["imageUrl"] = image
                item["imageTitle"] = r["name"]
            items.append(item)

        # 5) 버튼(웹 상세 보기)
        # view_url = f"https://fcgg.kr/선수티어/{pos_code}"
        view_url = f"https://fcgg.kr/선수티어"
        card = {
            "listCard": {
                "header": {"title": f"선수 티어리스트 · {pos_code}"},
                "items": items,
                "buttons": [
                    {"label": "자세히 보기", "action": "webLink", "webLinkUrl": view_url}
                    # {"label": "더 보기",   "action": "webLink", "webLinkUrl": view_url}
                ]
            }
        }
        return jsonify({"version": "2.0", "template": {"outputs": [card]}})

    except Exception:
        return jsonify({
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": "티어리스트 분석 중 오류가 발생했습니다. 다시 시도해 주세요."}}]}
        })

# 승부차기 미니게임
import random, threading
from flask import request, jsonify

PENALTY_GAMES = {}  # { uid: {"shots": [True/False...], "max": 5} }
PG_LOCK = threading.Lock()

# ---- 누적(커리어) 성공률 집계용 전역 저장소 -----------------------------------
CAREER = {}  # { uid: {"goals": int, "shots": int} }
C_LOCK = threading.Lock()

def _career_add(uid: str, goals: int, shots: int):
    """이번 게임 성적을 커리어에 누적."""
    if shots <= 0:
        return
    with C_LOCK:
        st = CAREER.setdefault(uid, {"goals": 0, "shots": 0})
        st["goals"] += goals
        st["shots"] += shots

def _career_rate(uid: str):
    """uid의 누적 성공률(0~1). 없으면 None."""
    with C_LOCK:
        st = CAREER.get(uid)
        if not st or st["shots"] <= 0:
            return None
        return st["goals"] / st["shots"]

def _leaders():
    """성공률 기준 내림차순 정렬 리스트 [(uid, rate, goals, shots), ...]"""
    with C_LOCK:
        items = []
        for k, v in CAREER.items():
            shots = v.get("shots", 0)
            goals = v.get("goals", 0)
            rate = (goals / shots) if shots > 0 else None
            if rate is not None:
                items.append((k, rate, goals, shots))
        items.sort(key=lambda x: x[1], reverse=True)
        return items

def _rank_of(uid: str):
    """(등수, 총원). 기록 없으면 (None, 총원)"""
    items = _leaders()
    total = len(items)
    for i, (k, _, _, _) in enumerate(items, start=1):
        if k == uid:
            return i, total
    return None, total

def _short(u: str, n: int = 6) -> str:
    """닉네임 대체용 uid 축약 표시"""
    return u[:n] if u else "unknown"

def _format_leaderboard(uid: str, limit: int = 10) -> str:
    """결과보기 출력용 포맷"""
    items = _leaders()
    if not items:
        return "아직 기록이 없습니다.\n승부차기를 먼저 플레이해 주세요!"

    # 1등 헤더
    top_uid, top_rate, top_goals, top_shots = items[0]
    header = "승부차기 평균 성공률 결과\n\n" \
             f"🥇현재 전체 1등 : {round(top_rate*100)}%\n\n"

    lines = []
    for i, (k, rate, goals, shots) in enumerate(items[:limit], start=1):
        # 현재 유저인 경우 멘션 표기를 넣어 강조
        if k == uid:
            # ✅ f-string 안에서 {{ }}가 한 겹 사라지므로 4겹 또는 문자열 연결 방식 사용
            line = f"{i}. " + "{{#mentions.user1}}" + f" {round(rate*100)}%"
            # 또는 같은 효과:
            # line = f"{i}. {{{{#mentions.user1}}}} {round(rate*100)}%"
        else:
            # 다른 유저는 @축약 uid 표기
            line = f"{i}. @{_short(k, 6)} {round(rate*100)}%"
        lines.append(line)

    return header + "\n".join(lines)

# ------------------------------------------------------------
# 승부차기 미니게임 - 결과보기(리더보드)에서 다수 멘션 토큰 지원 완성본
# ------------------------------------------------------------
import random, threading
from flask import request, jsonify

# 전역 게임 상태
PENALTY_GAMES = {}  # { uid: {"shots": [True/False...], "max": 5} }
PG_LOCK = threading.Lock()

# 전역 누적(커리어) 성공률 저장
CAREER = {}  # { uid: {"goals": int, "shots": int} }
C_LOCK = threading.Lock()

# (선택) 닉네임 캐싱 - 멘션이 불가한 경우 fallback로 쓸 수 있음
NAMEBOOK = {}  # { uid: "nickname" }
N_LOCK = threading.Lock()


# ========================= 누적/리더보드 유틸 =========================
def _career_add(uid: str, goals: int, shots: int):
    """이번 게임 성적을 커리어에 누적."""
    if shots <= 0:
        return
    with C_LOCK:
        st = CAREER.setdefault(uid, {"goals": 0, "shots": 0})
        st["goals"] += goals
        st["shots"] += shots

def _career_rate(uid: str):
    """uid의 누적 성공률(0~1). 없으면 None."""
    with C_LOCK:
        st = CAREER.get(uid)
        if not st or st["shots"] <= 0:
            return None
        return st["goals"] / st["shots"]

def _leaders():
    """
    성공률 기준 내림차순 정렬 리스트 반환
    [(uid, rate, goals, shots), ...]
    """
    with C_LOCK:
        items = []
        for k, v in CAREER.items():
            shots = v.get("shots", 0)
            goals = v.get("goals", 0)
            if shots > 0:
                rate = goals / shots
                items.append((k, rate, goals, shots))
    # 동률 안정화를 위해: 성공률↓, 시도수↓, uid↑
    items.sort(key=lambda x: (-x[1], -x[3], x[0]))
    return items

def _rank_of(uid: str):
    """(등수, 총원). 기록 없으면 (None, 총원)"""
    items = _leaders()
    total = len(items)
    for i, (k, *_rest) in enumerate(items, start=1):
        if k == uid:
            return i, total
    return None, total

def _short(u: str, n: int = 6) -> str:
    return u[:n] if u else "unknown"

def _save_name(uid: str, name: str):
    with N_LOCK:
        if name:
            NAMEBOOK[uid] = name

def _get_name(uid: str, fallback_short: bool = True) -> str:
    with N_LOCK:
        nm = NAMEBOOK.get(uid)
    if nm:
        return nm
    return _short(uid, 6) if fallback_short else uid

def _format_leaderboard_and_mentions(uid: str, limit: int = 10):
    """
    리더보드 텍스트와 extra.mentions 딕셔너리를 함께 생성하여 반환.
    - user1은 항상 요청자(uid)
    - 상위 limit명까지 user2, user3 ... 로 멘션 키 자동 할당
    - 본문에는 "{{#mentions.userX}}" 토큰을 정확히 매칭 (f-string 이스케이프 이슈 회피)
    """
    items = _leaders()
    if not items:
        text = "아직 기록이 없습니다.\n승부차기를 먼저 플레이해 주세요!"
        mentions = {"user1": {"type": "botUserKey", "id": uid}}
        return text, mentions

    top_uid, top_rate, _, _ = items[0]
    header = "승부차기 평균 성공률 결과\n\n" \
             f"🥇현재 전체 1등 : {round(top_rate*100)}%\n\n"

    # mentions: user1은 항상 요청자
    mentions = {"user1": {"type": "botUserKey", "id": uid}}

    lines = []
    dyn_idx = 2  # user2부터 시작
    for i, (k, rate, goals, shots) in enumerate(items[:limit], start=1):
        if k == uid:
            # 요청자 줄: user1 멘션 사용
            line = f"{i}. " + "{{#mentions.user1}}" + f" {round(rate*100)}%"
        else:
            # 다른 유저도 멘션으로 표시하려면 user2, user3 ... 동적 할당
            key = f"user{dyn_idx}"
            mentions[key] = {"type": "botUserKey", "id": k}
            line = f"{i}. " + "{{#mentions." + key + "}}" + f" {round(rate*100)}%"
            dyn_idx += 1
        lines.append(line)

    # # 내 현재 등수
    # my_rank, total = _rank_of(uid)
    # if my_rank:
    #     lines.append(f"\n내 현재 등수: {my_rank}/{total}")
    lines.append("\n\n랭킹은 주기적으로 갱신됩니다.")

    text = header + "\n".join(lines)
    return text, mentions
# ====================================================================


# ---- Payload helpers ---------------------------------------------------------
def _uid(body: dict) -> str:
    """Kakao 스펙 기준: user.id (type=botUserKey). 환경에 따라 accountId 등도 들어올 수 있어 안전 처리."""
    user = ((body.get("userRequest") or {}).get("user") or {})
    uid = (user.get("id") or "").strip()
    return uid or "unknown"

def _uname(body: dict) -> str:
    """카카오 문서에는 nickname 필드가 보장되지 않음 → 표시명은 uid로 대체.
    가능하면 properties.nickname 사용하여 저장 (fallback은 uid)
    """
    user = ((body.get("userRequest") or {}).get("user") or {})
    props = user.get("properties") or {}
    nickname = (props.get("nickname") or "").strip()
    uid = (user.get("id") or "").strip() or "unknown"
    return nickname or uid

def _param_from_action(body: dict, key: str) -> str:
    """action.params 우선, 없으면 action.detailParams[key].value"""
    action = body.get("action") or {}
    params = action.get("params") or {}
    if key in params and params[key] is not None:
        return str(params[key])
    dparams = action.get("detailParams") or {}
    if key in dparams and dparams[key] is not None:
        val = (dparams[key] or {}).get("value")
        if val is not None:
            return str(val)
    return ""

def _get_kick_input(body: dict, cur_idx: int) -> str:
    """
    1) 다중 슬롯: dir{cur_idx} (예: dir0, dir1 ...)
    2) 단일 슬롯: dir
    둘 다 없으면 빈 문자열
    """
    key = f"dir{cur_idx}"
    v = _param_from_action(body, key)
    if v:
        return v
    return _param_from_action(body, "dir")

# ---- Game helpers ------------------------------------------------------------
def _board(shots, total=5):
    marks = "".join("⭕️" if s else "❌️" for s in shots)
    return marks + "⬜️" * (total - len(shots))

def _kick_prob(direction_text: str) -> float:
    s = (direction_text or "").strip().lower()
    # 가운데(센터)만 33%, 그 외(왼/오/사분면 포함) 66%
    return 0.33 if s in {"가운데", "center", "c"} else 0.66

def _start(uid: str):
    with PG_LOCK:
        PENALTY_GAMES[uid] = {"shots": [], "max": 5}

def _state(uid: str):
    with PG_LOCK:
        return PENALTY_GAMES.get(uid)

def _reset(uid: str):
    """현재 사용자 게임 상태 완전 초기화"""
    with PG_LOCK:
        if uid in PENALTY_GAMES:
            del PENALTY_GAMES[uid]

def _record(uid: str, success: bool):
    with PG_LOCK:
        st = PENALTY_GAMES.setdefault(uid, {"shots": [], "max": 5})
        st["shots"].append(success)
        done = len(st["shots"]) >= st["max"]
        if done:
            final = st["shots"][:]
            del PENALTY_GAMES[uid]
            return final, True
        return st["shots"][:], False

def _quick_replies():
    opts = ["왼쪽","가운데","오른쪽","왼쪽위","왼쪽아래","오른쪽위","오른쪽아래"]
    # Kakao QuickReply(message) 포맷
    return [{"action": "message", "label": o, "messageText": o} for o in opts]


# ---- Endpoint ----------------------------------------------------------------
@app.route("/kakao/penalty", methods=["POST"])
def kakao_penalty():
    try:
        # ---------------- 멘트/연출 유틸 ----------------
        def _streak_tail(shots, val):
            """shots의 끝에서부터 val(True/False)와 같은 값이 몇 번 연속인지 카운트"""
            c = 0
            for s in reversed(shots):
                if s is val: c += 1
                else: break
            return c

        def _pick(arr):
            return random.choice(arr) if arr else ""

        # 골/노골 기본 멘트 풀
        GOAL_BASE = [
            "🔥 절정의 컨디션!",
            "💥 강슛이네요!",
            "🥳 완벽한 코스!",
            "😎 침착했다!",
            "🎯 정확도 미쳤다!",
            "🚀 골망이 찢어지겠어!"
        ]
        MISS_BASE = [
            "😰 긴장했나 봐요!",
            "🧤 골키퍼 선방!",
            "🙈 아깝다, 포스트!",
            "😵 살짝 빗나갔어요.",
            "😬 다음엔 더 과감하게!",
            "🌪️ 페인트에 걸렸나?"
        ]

        # 연속 상황 멘트 (상황별로 우선 적용)
        def goal_streak_msg(st):
            if st >= 5: return "🔥🔥🔥 5연속 골! 오늘은 당신의 날!"
            if st == 4: return "🔥🔥 4연속 골! 멈출 수 없다!"
            if st == 3: return "🔥 3연속 골! 흐름 제대로 탔다!"
            if st == 2: return "⚡ 2연속 골! 페이스 좋아요!"
            return ""

        def miss_streak_msg(st):
            if st >= 3: return "🧊 연속 실축… 호흡 가다듬고 다시!"
            if st == 2: return "🧊 2연속 실축… 코스 바꿔볼까요?"
            return ""

        # 엔딩 보상/칭호
        def end_badge(total):
            if total == 5: return "🏆 5골 입니다. 퍼펙트 키커!"
            if total == 4: return "🥇 4골 입니다. 엘리트 스트라이커!"
            if total == 3: return "🥈 3골 입니다. 안정적인 피니셔!"
            if total == 2: return "🥉 2골 입니다. 아직 워밍업이네요!"
            return "🪙 1골 입니다. 다음엔 더 잘할 수 있어요!"

        # ----------------------------------------------
        body = request.get_json(silent=True) or {}
        uid = _uid(body)
        uname = _uname(body)
        # 닉네임 캐싱
        _save_name(uid, uname)

        uter = (body.get("userRequest") or {}).get("utterance") or ""
        st = _state(uid)
        
        GM_id = ((body.get("userRequest")).get("block")).get("id")  # "블록ID 예: 68c7f4b6..."

        # ---- (A) '결과보기' 요청 처리 -----------------------------------------
        if uter in ['결과보기', '결과 보기', '랭킹', '랭킹보기', '결과']:
            lb_text, mentions = _format_leaderboard_and_mentions(uid, limit=10)
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{
                        "simpleText": {"text": lb_text}
                    }, {
                        "textCard": {
                            "title": "다시 도전할까요? 😀",
                            "buttons": [
                                {"label": "승부차기", "action": "block", "blockId": GM_id}
                            ]
                        }
                    }],
                },
                "extra": {
                    # 여러 명 멘션 동적 삽입 (예: user1~userN)
                    "mentions": mentions
                }
            })

        # 종료/나가기
        if uter in ['종료', '나가기', '홈으로']:
            _reset(uid)
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{
                        "simpleText": {
                            "text": "📣 승부차기 종료!\n다시 시작하려면 '@피파봇 승부차기'라고 말해주세요!"
                        }
                    }]
                }
            })

        # 시작 트리거
        if not st and uter in ['승부차기', '승차']:
            _start(uid)
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{
                        "simpleText": {
                            "text": (
                                "📣 승부차기가 시작됩니다! 기회는 5번!\n"
                                "🧍‍ vs 🧤\n"
                                "“왼쪽, 가운데, 오른쪽” 중에 하나를 입력해주세요."
                            )
                        }
                    }],
                    "quickReplies": _quick_replies()
                }
            })

        # 현재 상태/회차
        st = _state(uid)
        if not st:
            # 잘못된 진입 보호
            return jsonify({
                "version": "2.0",
                "template": {"outputs": [{"simpleText": {"text": "먼저 '@피파봇 승부차기'로 시작해 주세요!"}}]}
            })

        cur_idx = len(st["shots"])

        # 입력 파싱
        dir_text = _get_kick_input(body, cur_idx)
        # 입력 없으면 현재 보드만 안내
        if not dir_text or uter in ['승부차기', '승차']:
            board = _board(st["shots"], st["max"])
            n = cur_idx
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{
                        "simpleText": {
                            "text": (
                                f"🧍‍ 키커 준비 완료! (진행 {n}/{st['max']}회)\n"
                                f"현재: {board}\n"
                                f"“왼쪽/가운데/오른쪽” 중 하나를 선택해 주세요."
                            )
                        }
                    }]
                },
                "extra": {
                    "mentions": {
                        "user1": {"type": "botUserKey", "id": uid}
                    }
                }
            })

        # 판정
        success = (random.random() < _kick_prob(dir_text))
        shots, done = _record(uid, success)

        # 보드/스코어/연출
        board = _board(shots, 5)
        n = len(shots)
        total = sum(1 for s in shots if s)

        # 연속 카운트 계산
        def _streak_tail_local(shots_local, val):
            c = 0
            for s in reversed(shots_local):
                if s is val: c += 1
                else: break
            return c
        g_streak = _streak_tail_local(shots, True)   # 연속 골
        m_streak = _streak_tail_local(shots, False)  # 연속 노골

        # 멘트 조립
        if success:
            head = "골! "
            vibe = goal_streak_msg(g_streak) or _pick(GOAL_BASE)
            gk_line = _pick([
                "🧤 골키퍼가 움직이기도 전에 훅!",
                "🧤 골키퍼가 반대편으로 뛰었네요!",
                "🧤 완벽하게 속였습니다!"
            ])
        else:
            head = "노골! "
            vibe = miss_streak_msg(m_streak) or _pick(MISS_BASE)
            gk_line = _pick([
                "🧤 골키퍼가 읽었어요!",
                "🧤 손끝에 살짝 걸렸습니다!",
                "🧤 코스가 들켰나 봐요!"
            ])

        # 키커/골키퍼 이모지 연출 + 현재 스코어 표시
        # 예: "{{#mentions.user1}} 골! ⭕️⭕️⬜️⬜️⬜️ (2/5회)  🧍‍ vs 🧤  |  현재 스코어 2"
        prefix = "{{#mentions.user1}}" + f" {head} {board} ({n}/5회)\n🧍‍ vs 🧤  |  현재 스코어 {total}골"
        reaction = f"\n{vibe}\n{gk_line}"

        if done:
            # ---- 게임 종료: 커리어 누적 & 요약 + 버튼(승부차기/결과보기) ----------
            _career_add(uid, total, len(shots))  # 누적 저장

            badge = end_badge(total)
            summary = (
                f"\n\n📣 게임 종료! {total}/5 성공! (성공률 {round(total/5*100)}%)\n"
                f"{badge}\n"
            )
            card = {
                "textCard": {
                    "title": "다시 도전할까요? 😀",
                    "buttons": [
                        {"label": "승부차기",  "action": "block", "blockId": GM_id},
                        {"label": "결과보기", "action": "message", "messageText": "결과보기"}
                    ]
                }
            }
            return jsonify({
                "version": "2.0",
                "template": {"outputs": [{"simpleText": {"text": prefix + reaction + summary}}, card]},
                "extra": {
                    # 종료 메시지는 요청자 멘션만 유지(짧게)
                    "mentions": {"user1": {"type": "botUserKey", "id": uid}}
                }
            })

        # 진행 중이면 다음 입력 유도
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": prefix + reaction}}],
                "quickReplies": _quick_replies()
            },
            "extra": {
                "mentions": {"user1": {"type": "botUserKey", "id": uid}}
            }
        })

    except Exception:
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": "문제가 발생했어요. '@피파봇 승부차기'로 다시 시작해 주세요."
                    }
                }]
            }
        })



# 포트 설정 및 웹에 띄우기
# 초기화 실행 및 Flask 앱 실행
if __name__ == '__main__':
    init_db()  # 데이터베이스 및 테이블 생성
    app.run('0.0.0.0', port=3000, debug=True)
