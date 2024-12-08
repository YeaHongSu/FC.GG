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
            return redirect(
                url_for('result', character_name=character_name, match_type_name=match_type_name),
                code=301
            )

        # 닉네임에서 공백 제거
        character_name = character_name.replace(" ", "")
       
        # API key 설정
        headers = {"x-nxopen-api-key" : f"{app.config['API_KEY']}"}
        
        # 유저 닉네임 및 레벨 데이터 저장
        urlString = "https://open.api.nexon.com/fconline/v1/id?nickname=" + character_name
        characterName = requests.get(urlString, headers=headers).json()["ouid"]
    
        urlString = "https://open.api.nexon.com/fconline/v1/user/basic?ouid=" + characterName
        lv = requests.get(urlString, headers = headers).json()["level"]

        # JSON 데이터를 가져옴
        urlString = "https://open.api.nexon.com/fconline/v1/user/maxdivision?ouid=" + characterName
        division_info = requests.get(urlString, headers=headers).json()

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
            # divisionId로 divisionName을 찾아서 level_data에 추가
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

        # 유저 매치 데이터 20개 불러오기
        response = requests.get(f"https://open.api.nexon.com/fconline/v1/user/match?ouid={characterName}&matchtype={match_type}&limit=25", headers=headers)
        matches = response.json() if response.ok else []

        # matches가 빈 리스트인 경우 바로 렌더링
        if not matches:
            return render_template(
                'result.html', 
                my_data={},  # my_data에 빈 딕셔너리를 기본값으로 설정
                match_data=[],  # match_data에 빈 리스트를 기본값으로 설정
                level_data=level_data, 
                match_type=match_type, 
                max_data=[],  # max_data에 빈 리스트를 기본값으로 설정
                min_data=[],  # min_data에 빈 리스트를 기본값으로 설정
                data_label=[],  # data_label에 빈 리스트를 기본값으로 설정
                jp_num=0,  # jp_num 기본값 설정
                play_style={},  # play_style에 빈 딕셔너리를 기본값으로 설정
                no_recent_matches=True  # no_recent_matches 값 전달
            )

        # match 데이터 가져오기
        match_data_list = get_match_data(matches, headers)

        if not match_data_list:
            return render_template('result.html', level_data=level_data, no_recent_matches=True)

        result_list = []
        imp_data = []

        # 유저 컨트롤러 통계를 저장할 리스트 추가
        controller_stats = {"🎮": 0, "⌨️": 0, "오류": 0}

        # 각 매치 데이터 처리
        for data in match_data_list:
            date = calculate_time_difference(data['matchDate'])
            my_data = me(data, character_name)
            your_data = you(data, character_name)
            imp = data_list(my_data)
            imp2 = data_list(your_data)

            # 컨트롤러 값 가져오기
            my_controller = my_data['matchDetail'].get('controller', 'Unknown')  # 기본값 "Unknown"
            your_controller = your_data['matchDetail'].get('controller', 'Unknown')

            # None 값을 "오류"로 처리 및 매핑
            if my_controller is None:
                my_controller = "오류"
            elif my_controller == 'gamepad':  # 'is' 대신 '=='
                my_controller = '🎮'
            elif my_controller == 'keyboard':
                my_controller = '⌨️'

            if your_controller is None:
                your_controller = "오류"
            elif your_controller == 'gamepad':
                your_controller = '🎮'
            elif your_controller == 'keyboard':
                your_controller = '⌨️'

            # 컨트롤러 통계 업데이트
            if my_controller in controller_stats:
                controller_stats[my_controller] += 1

            w_l = my_data['matchDetail']['matchResult']

            # 비정상 게임 3:0으로 처리
            my_goal_total = my_data['shoot']['goalTotal'] if my_data['shoot']['goalTotal'] is not None else 0
            your_goal_total = your_data['shoot']['goalTotal'] if your_data['shoot']['goalTotal'] is not None else 0

            match_data = {
                '매치 날짜': date,
                '결과': w_l,
                '플레이어 1 vs 플레이어 2': f'{my_data["nickname"]} vs {your_data["nickname"]}',
                '스코어': f'{my_goal_total} : {your_goal_total}',
                '컨트롤러': f"{my_controller} : {your_controller}"
            }
            result_list.append(match_data)

            if imp == None or imp2 == None:
                continue

            # 중요 정보 저장용
            imp_data.append(imp)

        # 가장 많이 사용된 my_controller 추출
        most_common_controller = max(controller_stats, key=controller_stats.get)

        if len(imp_data) == 0:
            return render_template('result.html', level_data=level_data, no_recent_matches=True)
        
        # 숫자 데이터만 필터링
        filtered_imp_data = [[value for value in row if isinstance(value, (int, float))] for row in imp_data]

        # 평균 계산
        filtered_imp_data = np.array(filtered_imp_data, dtype=float)  # 숫자 데이터만 포함
        my_avg = np.nanmean(filtered_imp_data, axis=0)

        # 전체 유저 중요 지표 평균 불러오기
        cl_data = np.array(data_list_cl(avg_data(match_type)))
       
        # 상위/하위 10개 중요 지표 선정
        jp_num = 20  # 먼저 10개의 지표를 가져옴
        threshold = 0.9  # 극단적인 차이를 제외하기 위한 임계값 설정

        # 상위 지표에서 10개 추출 후 임계값 적용한 필터링
        max_diff = (my_avg - cl_data) / cl_data
        max_idx, max_values = top_n_argmax(max_diff, jp_num)

        # 상위 5개만 남기기
        filtered_max_idx = max_idx[:5]
        filtered_max_values = max_values[:5]

        # 하위 지표에서 10개 추출 후 임계값 적용한 필터링
        min_diff = (my_avg - cl_data) / cl_data
        min_idx, min_values = top_n_argmin(min_diff, jp_num)

        # 극단적인 값을 필터링한 후 하위 5개만 남기기
        filtered_min_idx = []
        filtered_min_values = []

        filtered_min_idx = [idx for idx, value in zip(min_idx, min_values) if abs(value) < threshold][:5]
        filtered_min_values = [value for value in min_values if abs(value) < threshold][:5]

        # zip을 리스트로 변환하여 여러 번 사용할 수 있게 함
        max_data = list(zip(filtered_max_idx, filtered_max_values))
        min_data = list(zip(filtered_min_idx, filtered_min_values))

        # 플레이스타일 결정
        play_style = determine_play_style(max_data, min_data)

        return render_template('result.html', my_data=my_data, match_data=result_list, level_data=level_data, match_type = match_type,
                            max_data=max_data, min_data=min_data, data_label=data_label, jp_num=jp_num,
                            play_style=play_style, most_common_controller=most_common_controller)

    except Exception:
        try:
            # 문제가 발생하면 result.html 먼저 시도
            return render_template(
                'result.html', 
                my_data={},  # my_data에 빈 딕셔너리를 기본값으로 설정
                match_data=[],  # match_data에 빈 리스트를 기본값으로 설정
                level_data=level_data, 
                match_type=match_type, 
                max_data=[],  # max_data에 빈 리스트를 기본값으로 설정
                min_data=[],  # min_data에 빈 리스트를 기본값으로 설정
                data_label=[],  # data_label에 빈 리스트를 기본값으로 설정
                jp_num=0,  # jp_num 기본값 설정
                play_style={},  # play_style에 빈 딕셔너리를 기본값으로 설정
                no_recent_matches=True  # no_recent_matches 값 전달
            )
        except Exception:
            # result.html이 안 되면 home.html로 이동
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
            (13, '자유게시판', '4222', '4222 그 LS랑 RF 버전인가요?', '2024-12-08 23:30:00'),
            (12, '키보드게시판', '워싱시', '키보드슈챔중에 4222 쓰는사람꺼 쓰생', '2024-12-04 13:00:00'),
            (11, '자유게시판', 'riqoeo', '5일까지 존버 ㄱ', '2024-12-01 13:00:00'),
            (10, '자유게시판', '현질', '10000fc정도 있는데 빠칭코가 효율 가장 좋나요', '2024-11-30 13:00:00')
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

# 포트 설정 및 웹에 띄우기
# 초기화 실행 및 Flask 앱 실행
if __name__ == '__main__':
    init_db()  # 데이터베이스 및 테이블 생성
    app.run('0.0.0.0', port=3000, debug=True)
