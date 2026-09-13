from flask import Flask, render_template, request, redirect, url_for, session, redirect, send_from_directory
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime, timedelta, timezone
import os
import traceback
import requests
import pandas as pd
import numpy as np
from config import Config
from flask import flash
from utils.utils import me, you, avg_data, top_n_argmax, top_n_argmin, calculate_time_difference
from utils.data_processing import (
    data_list, data_list_cl, data_label, determine_play_style, build_match_boxscore,
    compute_match_mvp, collect_player_appearances, build_top_players,
    resolve_division_tier, build_pitch_view, generate_match_feedback,
    DIVISION_MAPPING, derive_season_id, get_player_rarity, attach_rarity,
    format_grade_badge, grade_badge_class, PLAYER_IMAGE_FALLBACK_URL_TMPL,
    aggregate_shot_types, build_player_detail_stats, accumulate_shot_xg,
)
from collections import Counter, defaultdict, OrderedDict
from utils.win_utils import calculate_win_improvement
from tier.tier_info import tier
import warnings
import asyncio
import aiohttp
import sqlite3
from flask import jsonify
import re
from urllib.parse import quote_plus
import threading, requests

import time
import functools
from functools import lru_cache


# 데이터베이스 초기화 함수
def init_db():
    # ⚠️ 방어 처리(신규) — initialize_database()와 동일한 이유로, search_data.db가
    # 손상된 상태로 존재할 경우를 대비해 자동 복구합니다.
    try:
        conn = sqlite3.connect('search_data.db')
        conn.execute('SELECT 1')
    except sqlite3.DatabaseError:
        try:
            conn.close()
        except Exception:
            pass
        if os.path.exists('search_data.db'):
            os.remove('search_data.db')
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


# ✅ 1v1 공식경기 최고 티어 표시 (신규) — 매치 목록에 뜨는 닉네임(나/상대) 옆에
# 그 사람의 "공식경기"(matchType=50) 1v1 최고 티어를 같이 보여주기 위한 조회 함수들.
# 한 페이지에 최근 매치가 25개까지 있고 상대가 매번 다를 수 있어서, 닉네임을
# 중복 제거한 뒤 aiohttp로 한꺼번에(동시에) 조회한다 — 순차 호출보다 훨씬 빠르고,
# 이미 match-detail을 동시에 가져오는 fetch_all_match_data와 같은 패턴이다.
async def fetch_ouid_async(session, nickname, headers):
    url = f"https://open.api.nexon.com/fconline/v1/id?nickname={nickname}"
    async with session.get(url, headers=headers) as response:
        data = await response.json()
        return data.get("ouid") if isinstance(data, dict) else None


async def fetch_maxdivision_async(session, ouid, headers):
    url = f"https://open.api.nexon.com/fconline/v1/user/maxdivision?ouid={ouid}"
    async with session.get(url, headers=headers) as response:
        data = await response.json()
        return data if isinstance(data, list) else []


async def fetch_nickname_tier_async(session, nickname, headers, match_type_code):
    ouid = await fetch_ouid_async(session, nickname, headers)
    if not ouid:
        return nickname, {"tier_name": None, "tier_image": None}
    division_info = await fetch_maxdivision_async(session, ouid, headers)
    return nickname, resolve_division_tier(division_info, match_type_code)


async def fetch_tiers_for_nicknames(nicknames, headers, match_type_code):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_nickname_tier_async(session, nn, headers, match_type_code) for nn in nicknames]
        return await asyncio.gather(*tasks, return_exceptions=True)


def get_nickname_tiers(nicknames, headers, match_type_code="50"):
    """닉네임 목록(중복 제거)을 받아 {닉네임: {"tier_name":..., "tier_image":...}} 딕셔너리로 반환.
    개별 닉네임 조회가 실패해도(탈퇴/오타 등) 그 닉네임만 빠지고 나머지는 정상 반환되며,
    전체가 실패해도 빈 dict를 반환해 화면에서는 조용히 뱃지가 생략된다(기존 방어 패턴과 동일)."""
    unique_nicknames = sorted({n for n in nicknames if n})
    if not unique_nicknames:
        return {}
    try:
        results = asyncio.run(fetch_tiers_for_nicknames(unique_nicknames, headers, match_type_code))
    except Exception:
        traceback.print_exc()
        return {}
    tier_map = {}
    for r in results:
        if isinstance(r, Exception) or r is None:
            continue
        nickname, tier_info = r
        tier_map[nickname] = tier_info
    return tier_map
   
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
    # ✅ 2026-09-13 피드백 — "실시간 인기 구단주"에 프로게이머/인플루언서 닉네임이면
    # 이름 옆에 "프로"/"인플루언서" 라벨을 붙인다. PRO_GAMER_NICKNAMES/
    # INFLUENCER_NICKNAMES는 이 파일 아래쪽(인플루언서 페이지용)에 정의돼 있지만,
    # 모듈이 전부 로드된 뒤에 요청이 들어오므로 여기서 참조해도 문제없다.
    top_nicknames = [
        row + (creator_label_for_nickname(row[0]),) for row in c.fetchall()
    ]  # nickname, lv, tier_image, search_count, creator_label
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

# @app.before_request
# def redirect_to_fcgg():
#     # www 도메인을 fcgg.kr로 리다이렉트
#     if request.host.startswith("www."):
#         # 쿼리 스트링이 비어 있지 않은 경우에만 추가
#         if request.query_string and request.query_string != b'':
#             return redirect(f"https://fcgg.kr{request.path}?{request.query_string.decode('utf-8')}", code=301)
#         # 쿼리 스트링이 없으면 ?를 포함하지 않음
#         return redirect(f"https://fcgg.kr{request.path}", code=301)

@app.before_request
def redirect_to_fcgg():
    # 1. ads.txt 리디렉션 (가장 먼저 처리)
    if request.path == "/ads.txt":
        return redirect(
            "https://adstxt.venatusmedia.com/fcgg.kr/ads.txt",
            code=301
        )

    # 2. www → fcgg.kr 리디렉션
    if request.host.startswith("www."):
        if request.query_string and request.query_string != b'':
            return redirect(
                f"https://fcgg.kr{request.path}?{request.query_string.decode('utf-8')}",
                code=301
            )
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

        # ✅ 선수 등급(시즌) 배지용 메타데이터 (신규) — 캐시돼 있어 API 호출은 사실상
        # 1시간에 한 번뿐. 실패해도 빈 dict라 아래 배지 관련 코드가 조용히 생략된다.
        season_meta_map = get_season_meta_map()

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
                            "spPosition": player.get("spPosition"),
                            # ✅ 강화 단계(신규) — 넥슨 공식 match-detail 스키마의 player[].spGrade
                            "spGrade": player.get("spGrade"),
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

            # ✅ 선수 등급(시즌) 배지 (신규) — spId만으로 등급을 알 수 있어서 새 API 호출
            # 없이(seasonid.json은 위에서 이미 캐시해 받아온 season_meta_map 재사용)
            # "몇 카인지" 테두리 배지를 붙일 수 있다.
            df_final["season_id"] = df_final["spId"].apply(derive_season_id)
            df_final["class_name"] = df_final["spId"].apply(
                lambda spId: get_player_rarity(spId, season_meta_map).get("class_name")
            )
            df_final["season_img"] = df_final["spId"].apply(
                lambda spId: get_player_rarity(spId, season_meta_map).get("season_img")
            )
            # ✅ 강화 단계 배지 (신규) — match-detail의 spGrade를 "+N" 텍스트로 표시.
            # 이미지 에셋은 넥슨이 제공하지 않아 직접 렌더링한다.
            df_final["grade_badge"] = df_final["spGrade"].apply(format_grade_badge) if "spGrade" in df_final.columns else None
            # ✅ 강화 단계별 색상(신규) — 1~13강 구간별로 배지 색을 다르게(브론즈/실버/골드/특수).
            df_final["grade_badge_class"] = df_final["spGrade"].apply(grade_badge_class) if "spGrade" in df_final.columns else None
            # ✅ 선수 이미지 폴백용(신규) — playersAction 액션샷이 없는 선수를 위한 대체 URL
            df_final["sd_image_fallback"] = df_final["spId"].apply(
                lambda spId: PLAYER_IMAGE_FALLBACK_URL_TMPL.format(spId=spId)
            )


        # ✅ divisionId → 티어 뱃지 매핑 (신규 "마스터" 티어 추가로 인해 utils/data_processing.py의
        # DIVISION_MAPPING/resolve_division_tier()로 통일 — 예전에는 이 자리에 오래된
        # division_mapping 테이블이 따로 있어서, 새로 생긴 티어(마스터 등)의 유저는
        # "정보 없음"으로 표시되는 문제가 있었다.
        _tier = resolve_division_tier(division_info, match_type)
        tier_name = _tier["tier_name"]
        tier_image = _tier["tier_image"]
        if tier_name is None and tier_image is None:
            tier_name = "정보 없음"

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
        # ✅ 주력 선수 TOP5 (신규) — 최근 매치들에서 실제로 기용된 내 선수 spId를 누적,
        # 평점(찾은 경우에만)도 같이 누적해서 평균을 계산한다
        player_usage = Counter()
        player_rating_sum = defaultdict(float)
        player_rating_count = defaultdict(int)
        # ✅ 강화 단계(신규) — 여러 매치 중 마지막으로 확인된 값을 그대로 사용(자주
        # 안 바뀌는 값이라 어느 매치 기준이든 큰 차이가 없다)
        player_grade_map = {}
        # MVP 표시(신규)에 쓸 spId→이름 매핑. 실패해도 빈 dict라 화면에서 이름만 조용히 빠짐
        spid_name_map = get_spid_name_map()
        # ✅ 슛 타입 분포(신규) — shootDetail이 들어있는 원본 me 사이드를 그대로 모아뒀다가
        # 루프가 끝난 뒤 한 번에 집계한다(추가 API 호출 없음).
        raw_me_sides = []
        # ✅ 선수별 상세 지표 테이블(신규) — spId별로 25경기치 스탯을 누적한다.
        player_stat_acc = defaultdict(lambda: {
            "count": 0, "wins": 0, "win_known": 0,
            "rating_sum": 0.0, "rating_count": 0,
            "position_counts": Counter(),
            "goal": 0, "assist": 0,
            "pass_try": 0, "pass_success": 0,
            "dribble_try": 0, "dribble_success": 0,
            "aerial_try": 0, "aerial_success": 0,
            "tackle_try": 0, "tackle_success": 0,
            "block_try": 0, "block_success": 0,
            "intercept": 0, "last_grade": None,
            # ✅ 공격력/기대득점 지수 계산용(신규, 2026-09-12)
            "shoot_try": 0, "effective_shoot": 0, "xg_sum": 0.0,
        })

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

            # ✅ 슛 타입 분포(신규) — shootDetail을 포함한 원본을 그대로 보관
            raw_me_sides.append(my_data)

            # ✅ 주력 선수 TOP5 (신규) — 이 매치에서 기용된(SUB 제외) 내 선수 spId 누적,
            # 평점을 찾은 선수는 평균 계산용으로 합계/횟수도 같이 누적
            appearances = collect_player_appearances(my_data, match_result=w_l)
            player_usage.update(a['spId'] for a in appearances)
            for a in appearances:
                if a['rating'] is not None:
                    player_rating_sum[a['spId']] += a['rating']
                    player_rating_count[a['spId']] += 1
                if a.get('spGrade') is not None:
                    player_grade_map[a['spId']] = a['spGrade']

                # ✅ 선수별 상세 지표(신규) — player[].status 실제 필드를 spId별로 누적
                acc = player_stat_acc[a['spId']]
                acc["count"] += 1
                if a.get('win') is not None:
                    acc["win_known"] += 1
                    if a['win']:
                        acc["wins"] += 1
                if a['rating'] is not None:
                    acc["rating_sum"] += a['rating']
                    acc["rating_count"] += 1
                if a.get('spPosition') is not None:
                    acc["position_counts"][a['spPosition']] += 1
                if a.get('spGrade') is not None:
                    acc["last_grade"] = a['spGrade']
                stat = a.get('stat') or {}
                acc["goal"] += stat.get("goal") or 0
                acc["assist"] += stat.get("assist") or 0
                acc["pass_try"] += stat.get("passTry") or 0
                acc["pass_success"] += stat.get("passSuccess") or 0
                acc["dribble_try"] += stat.get("dribbleTry") or 0
                acc["dribble_success"] += stat.get("dribbleSuccess") or 0
                acc["aerial_try"] += stat.get("aerialTry") or 0
                acc["aerial_success"] += stat.get("aerialSuccess") or 0
                acc["tackle_try"] += stat.get("tackleTry") or 0
                acc["tackle_success"] += stat.get("tackle") or 0
                acc["block_try"] += stat.get("blockTry") or 0
                acc["block_success"] += stat.get("block") or 0
                acc["intercept"] += stat.get("intercept") or 0
                acc["shoot_try"] += stat.get("shoot") or 0
                acc["effective_shoot"] += stat.get("effectiveShoot") or 0

            # ✅ 공격력 지수의 기대득점(xG) 부분 — shootDetail(슛별 좌표/종류)을
            # 슈팅 선수(spId)별로 누적한다. 추가 API 호출 없음(이미 받아온 my_data 재사용).
            accumulate_shot_xg(player_stat_acc, my_data)

            # ✅ 매치 MVP (신규) — 평점 필드를 못 찾으면 None → result.html에서 자동으로 숨김
            match_mvp = compute_match_mvp(my_data, your_data, spid_name_map)
            # ✅ 매치 상세 박스스코어 (신규) — 이미 받아온 my_data/your_data를 그대로 재사용,
            #    추가 API 호출 없음. build_match_boxscore()가 실패해도 예외를 던지지 않는다.
            my_boxscore = build_match_boxscore(my_data)
            opponent_boxscore = build_match_boxscore(your_data)

            match_data_item = {
                '매치 날짜': date,
                '결과': w_l,
                '플레이어 1 vs 플레이어 2': f'{my_data["nickname"]} vs {your_data["nickname"]}',
                '스코어': f'{my_goal_total} : {your_goal_total}',
                '컨트롤러': f"{my_controller} : {your_controller}",
                '상세': {
                    'me': my_boxscore,
                    'opponent': opponent_boxscore,
                },
                'mvp': match_mvp,
                # ✅ 11v11 잔디밭 뷰 (신규) — 이미 받아온 my_data/your_data를 그대로 재사용,
                #    추가 API 호출 없음. build_pitch_view()가 실패해도 예외를 던지지 않는다.
                '피치뷰': build_pitch_view(my_data, your_data, spid_name_map, match_mvp),
                # ✅ 경기 피드백 (신규, 룰 기반 · AI 미사용) — 이미 계산한 박스스코어를 그대로
                #    재사용해 승/무/패에 따라 "이렇게 했으면 더 좋았을 것"을 최대 3개까지 안내.
                '피드백': generate_match_feedback(my_boxscore, opponent_boxscore, w_l,
                                                 my_goals=my_goal_total, opp_goals=your_goal_total),
            }
            result_list.append(match_data_item)

            if imp is None or imp2 is None:
                continue
            imp_data.append(imp)

        # ✅ 1v1 공식경기 최고 티어 표시 (신규) — 매치 목록의 "나 vs 상대" 닉네임 옆에
        # 각자의 공식경기(matchType=50) 1v1 최고 티어를 표시한다. 내 티어는 이미 받아온
        # division_info를 재사용(추가 API 호출 없음), 상대 티어는 매치별로 다를 수 있어
        # 중복 제거한 닉네임들을 동시에(aiohttp) 조회한다. 실패해도 뱃지만 조용히 빠짐.
        try:
            me_tier_1v1 = resolve_division_tier(division_info, "50")
            opponent_nicknames = [m['플레이어 1 vs 플레이어 2'].split(' vs ')[1] for m in result_list]
            opponent_tier_map = get_nickname_tiers(opponent_nicknames, headers, "50")
            for m in result_list:
                opp_name = m['플레이어 1 vs 플레이어 2'].split(' vs ')[1]
                m['내_티어'] = me_tier_1v1
                m['상대_티어'] = opponent_tier_map.get(opp_name)
        except Exception:
            traceback.print_exc()
            me_tier_1v1 = None
            for m in result_list:
                m['내_티어'] = None
                m['상대_티어'] = None

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

        # ✅ 주력 선수 TOP5 (신규) — 최근 매치들의 평균 평점이 가장 높은 내 선수 5명
        # (2026-09-12: "출전 횟수" 기준 → "평균 평점" 기준으로 변경. build_top_players() 참고)
        player_avg_ratings = {
            sp_id: total / player_rating_count[sp_id]
            for sp_id, total in player_rating_sum.items() if player_rating_count[sp_id] > 0
        }
        top_players = build_top_players(player_usage, spid_name_map, player_avg_ratings, player_grade_map=player_grade_map)
        # ✅ 선수 등급(시즌)/강화 배지 (신규) — TOP5 카드에도 동일하게 배지를 붙인다.
        top_players = [attach_rarity(p, season_meta_map) for p in top_players]
        for p in top_players:
            p["grade_badge"] = format_grade_badge(p.get("spGrade"))
            p["grade_badge_class"] = grade_badge_class(p.get("spGrade"))
            p["image_fallback"] = PLAYER_IMAGE_FALLBACK_URL_TMPL.format(spId=p["spId"])

        # ✅ 슛 타입 분포 (2026-09-12 재조사 후 shootDetail 기반으로 전면 수정) — 이미
        # 받아온 my_data(raw_me_sides)의 shootDetail을 그대로 재사용, 추가 API 호출 없음.
        shot_type_stats = aggregate_shot_types(raw_me_sides)
        # ✅ 대표 선수 프로필 (신규) — "기본정보" 카드에 표시할, 이 유저가 최근
        # 가장 잘 쓴(평균 평점 1위) 선수 한 명. top_players[0]을 그대로 재사용하는
        # 거라 새 API 호출은 없다.
        representative_player = top_players[0] if top_players else None

        # ✅ 선수별 상세 지표 테이블 (신규) — fc-info.com "감독모드 분석" 참고. 25경기
        # 루프에서 이미 누적해둔 player_stat_acc를 화면 표시용으로 변환한다.
        player_detail_stats = build_player_detail_stats(player_stat_acc, spid_name_map, season_meta_map)

        return render_template('result.html', my_data=my_data, match_data=result_list, level_data=level_data, match_type=match_type,
                               max_data=max_data, min_data=min_data, data_label=data_label, jp_num=jp_num,
                               play_style=play_style, most_common_controller=most_common_controller, players=df_final.to_dict(orient="records"),
                               top_players=top_players, representative_player=representative_player,
                               shot_type_stats=shot_type_stats, player_detail_stats=player_detail_stats)
    except Exception:
        # ⚠️ 진단용(신규): 이 except가 원래 어떤 예외든 조용히 삼키고 "최근 전적이
        # 존재하지 않습니다"로 뭉뚱그려 보여주고 있어서, 진짜 원인이 뭔지 콘솔에서
        # 전혀 알 수 없었습니다. 실제로 매치가 없는 경우와 코드 어딘가에서 에러가
        # 난 경우를 구분할 수 있도록 콘솔에 전체 트레이스백을 출력하도록 했습니다.
        # (화면에 보이는 메시지 자체는 바꾸지 않았습니다 — 터미널에서 확인해주세요.)
        traceback.print_exc()
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

@app.route("/privacy", methods=["GET"])
def privacy():
    return render_template("privacy.html")


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


# ============================================================================
# ✅ 인플루언서/프로게이머 목록 (2026-09-14 재정비) — 라운드12 피드백 "토츠지지꺼
# 이미지랑 url 다 참조하면 안되나?"를 반영해, 사용자가 이번엔 tots.gg "전체
# 목록" 페이지를 통째로(렌더링된 HTML 그대로) 붙여넣어줬다. 그 HTML을 파싱해서
# 각 사람의 실제 프로필 사진(photo_url)과 방송 채널 링크(channels, tots.gg가
# 보여주는 SOOP/YOUTUBE/CHZZK 배지 그대로)를 tots.gg에서 직접 가져왔다 — 더 이상
# 우리가 따로 웹 검색해서 "이 채널이 맞는 것 같다"고 추정할 필요가 없어졌고,
# 사진이 없어서 이니셜로 뜨던 사람들도 이제 대부분 실제 사진이 채워진다.
# ⚠️ 이 과정에서 지난 라운드(2026-09-13)에 있던 파싱 버그도 같이 고쳤다: 소속팀이
# 없는 솔로 프로게이머(ELNINO/Froste/Jade/JUBJUB/KBG/Korso/rimGC/Seoby)의 org와
# tag가 서로 뒤바뀌어 들어가 있었다(예: ELNINO의 org가 '정인호', tag가 'ELNINO'여야
# 하는데 반대로 들어있었음) — 이번에 tots.gg 원본 그대로 다시 채워 넣으면서
# 자연히 바로잡혔다(소속 팀이 없으니 "개인 방송" 그룹으로 정상적으로 묶인다).
# TOTS_GG_ROSTER의 각 항목: category(progamer/influencer), org(소속 팀 — 개인
# 방송인/솔로 프로게이머는 None), tag(선수 태그/스트리머 활동명 — 화면에 보여줄
# 이름), real_name(실명), handle(실제 게임 닉네임 — 검색에 쓰는 키. tots.gg에도
# 안 나와 있으면 None), photo_url(tots.gg가 쓰는 프로필 사진 — 프로게이머는
# 넥슨 e스포츠 공식 렌더, 인플루언서는 본인 채널 프로필 사진), channels(tots.gg가
# 표시하는 방송 채널 목록. platform: soop/youtube/chzzk, url: 채널 링크. 없으면
# 빈 리스트 — tots.gg에도 채널이 연결 안 돼 있다는 뜻).
# ⚠️ 원본 자체의 이상치는 그대로 옮기지 않고 각주에 남겼다:
#  1) "호날두"(DN FREECS/두치와뿌꾸) 항목의 실명 자리에 실명이 아닌 'D&B'(하위
#     브랜드로 추정)가 적혀 있는데, tots.gg 원본 그대로 옮겼다(추측으로 고치지 않음).
#     ⚠️ 2026-09-14 round 13 피드백 — tots.gg에는 progamer로 분류돼 있었지만
#     실제로는 인플루언서라는 사용자 확인에 따라 category를 influencer로 정정.
#  2) "TaeGod"(BNK FEARK, 김태신)과 "Light"(BNK FEARK, 김선재) 두 사람의 handle이
#     tots.gg 자체에도 똑같이 'BFXLight'로 나온다(직전 라운드엔 확인 전이라 TaeGod
#     쪽을 비워뒀었는데, tots.gg 원본을 그대로 따르기로 해서 이번엔 그대로 반영했다
#     — tots.gg 쪽 오표기이거나 실제로 계정을 공유하는 상황일 수 있어, 사용자가
#     확인해서 고쳐주면 좋을 부분이다).
# ============================================================================
TOTS_GG_ROSTER = [
    {"category": 'progamer', "org": 'DN FREECS', "tag": '9KKI', "real_name": '김시경', "handle": 'DNS9KKI', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/26.png', "channels": []},
    {"category": 'influencer', "org": None, "tag": '감스트', "real_name": None, "handle": '감스트', "photo_url": 'https://yt3.ggpht.com/rELiEJEE17me3IkoI2bJFFdMssJ4gPnnNMyUbhj4sHcHdPkm_jeP_tpmMhzSGlo0epoT0R0ZUg=s176-c-k-c0x00ffffff-no-rj-mo', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/devil0108'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@gamst6217'}]},
    {"category": 'influencer', "org": None, "tag": '개복어', "real_name": None, "handle": '송도는섬이아니야', "photo_url": 'https://nng-phinf.pstatic.net/MjAyNTA1MTlfMjI5/MDAxNzQ3NjQ3ODE0Njc4.tbyIUduBdDnk9oTMqQdQ1DL8v5CfkBMKJKjKu1ybqmwg.qKGU4IlZwnV7ktT7f6oNWpM7g6AuLLd5BNDuvVj9rwEg.JPEG/A0EBA9_97EC8C.jpg?type=f120_120_na', "channels": [{"platform": 'chzzk', "url": 'https://chzzk.naver.com/55e243bd868e55adf3524c85f8db51b5'}]},
    {"category": 'influencer', "org": None, "tag": '게임하는뱅커', "real_name": None, "handle": '겜뱅이', "photo_url": 'https://yt3.googleusercontent.com/FvMQu-hBdGjO25YFO3Wn82N8B9BLr_z4RIzEZhW13UwSqJWTLNf-L-QHj5ELdLQgsoNGt2lY=s160-c-k-c0x00ffffff-no-rj', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/gamebanker'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@GameBankerTV'}]},
    {"category": 'influencer', "org": None, "tag": '국호형', "real_name": None, "handle": '국호형의강의실', "photo_url": 'https://yt3.ggpht.com/3XmEqd3dhQe7-Fn0P-gnS84Kao_R8jUjcZDhRTi-C5RIX59EP61fR5yIonujI8f-5NPV9HPy=s176-c-k-c0x00ffffff-no-rj-mo', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/hoya10047'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@leeho6912'}]},
    {"category": 'influencer', "org": None, "tag": '단군', "real_name": None, "handle": '단군', "photo_url": 'https://nng-phinf.pstatic.net/MjAyMzEyMjJfMjY3/MDAxNzAzMTcxNTgwOTcy.n9CjlCzP502gZOUbdCKPF1zTVJh3hgr_eVC8FTcVCkog.XhDxHxMOkvWdQTNxyW5vjzhcSj2W1fHOPPCz5Q3vrV0g.JPEG/profile01_98x98.jpg?type=f120_120_na', "channels": [{"platform": 'chzzk', "url": 'https://chzzk.naver.com/243febdbcba51d2248bd97d23d2085af'}]},
    {"category": 'influencer', "org": None, "tag": '두치와뿌꾸', "real_name": 'D&B', "handle": '호날두', "photo_url": 'https://yt3.googleusercontent.com/KXOOZTxoEMfqqR3tXPb9i8oyxh_Opx9UP5u4kQjtyOwfroHf_n556rKs0MVSr8uyHs67D7FF=s160-c-k-c0x00ffffff-no-rj', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/galsa'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@%EB%91%90%EC%B9%98%EC%99%80%EB%BF%8C%EA%BE%B8'}]},
    {"category": 'influencer', "org": None, "tag": '마빡', "real_name": None, "handle": '데이비드베컴', "photo_url": 'https://yt3.googleusercontent.com/kvIbAxOY8oUqdzeiQDsHdP5Vb46eE_pphsQeKkf-8hR2_LP8yEJ_VWSlvYuXJtkJxfANeBU-iA=s160-c-k-c0x00ffffff-no-rj', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/vbvb1230'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@BBAK-GAME'}]},
    {"category": 'influencer', "org": None, "tag": '박성주', "real_name": '울산큰고래', "handle": '케빈울브라위너', "photo_url": 'https://yt3.ggpht.com/zk9H68cSGm7iFc8FdHvJSmPkkZe732fIbsbV8ZU--c6U2bAYcBqfSlOaNWHLnK-Evi58QeBE=s176-c-k-c0x00ffffff-no-rj-mo', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/bach023'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@UBWPSJ'}]},
    {"category": 'influencer', "org": None, "tag": '방배우', "real_name": None, "handle": '방배우', "photo_url": 'https://yt3.ggpht.com/pia9PCGw93IS6YNQEehjibhSkanfJjEmYVR-r798-7BDtkTrOBu5UDqKbF8uGUDvWnuUmBISlQ=s176-c-k-c0x00ffffff-no-rj-mo', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/bsh0329'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@bang_actor'}]},
    {"category": 'influencer', "org": None, "tag": '뱅', "real_name": None, "handle": '감자나라배준식', "photo_url": 'https://nng-phinf.pstatic.net/MjAyNTA0MTFfMTU0/MDAxNzQ0MzA0NTg5MjE5.6toa4kRwjhkudPEPzM5M08cuq8RfU2Ptn9Wg6I3YR4Ig.bgsdMNxOyWwzXIksUTuqR-Wsl4RIKRsjj46lxWMrtpsg.PNG/558C0E86-BEE1-4CB1-8814-F503574FD862-1744304587.png?type=f120_120_na', "channels": [{"platform": 'chzzk', "url": 'https://chzzk.naver.com/9d4f299325b38f9183bdb90b8849d912'}]},
    {"category": 'influencer', "org": None, "tag": '빅윈', "real_name": None, "handle": '포병부대', "photo_url": 'https://yt3.ggpht.com/Xka7MBbXxqaK6wNiS8DXjasI6kzRfMqiyykEfZ1qt_2NccVL_dRd_PkfGeUWsZiKb7jFWamKoA=s176-c-k-c0x00ffffff-no-rj-mo', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/dstv'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@kimbigwin'}]},
    {"category": 'influencer', "org": None, "tag": '스카우터', "real_name": None, "handle": '크라우터', "photo_url": 'https://yt3.ggpht.com/mel-yrsWnTc02-TMBTxdgKaEKUZrP6pCfOAtbceY2P0Q9Cxi_1_BqPCKQ5K6YNgtw2r18y80=s176-c-k-c0x00ffffff-no-rj-mo', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/dlckdghk1'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@%EC%8A%A4%EC%B9%B4%EC%9A%B0%ED%84%B0'}]},
    {"category": 'influencer', "org": None, "tag": '얍얍', "real_name": None, "handle": 'v침대위의메시v', "photo_url": 'https://nng-phinf.pstatic.net/MjAyMzEyMjFfMjYy/MDAxNzAzMTE0MjY0MzEw.4HN2-Prah0mvcdg91VweUfHaVWReJvn4GfnNLoXild4g.uMLiWaqHAhnsVnUozRdWca8fNhNsPlDK1q0bbyIxDeQg.PNG/dbb514f1-469b-479e-b5ba-3ac0f09a2776-profile_image-300x300.png?type=f120_120_na', "channels": [{"platform": 'chzzk', "url": 'https://chzzk.naver.com/dec8d19f0bc4be90a4e8b5d57df9c071'}]},
    {"category": 'influencer', "org": None, "tag": '유봉훈', "real_name": None, "handle": '신림동밀탱크', "photo_url": 'https://yt3.googleusercontent.com/qrST8YvZozcxpBeNW7pQNu6TGyYwwmWfTKMNLcX5emqzQAjPc7wt8mYUfuYsAOEp3WA9POmw=s160-c-k-c0x00ffffff-no-rj', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/6650junghun'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@%EC%9C%A0%EB%B4%89%ED%9B%88'}]},
    {"category": 'influencer', "org": None, "tag": '이상호', "real_name": None, "handle": '메시연', "photo_url": 'https://yt3.ggpht.com/kIYN06qpQsJ12QOUYAON3tGhCixYhAfyGZBT_y_aWhJcHUghleWBr8k6h26ZCQESS9v96zwfTXI=s48-c-k-c0x00ffffff-no-rj', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/lshooooo'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@LeeSangHoTV'}]},
    {"category": 'influencer', "org": None, "tag": '임유진', "real_name": None, "handle": '잉유진', "photo_url": 'https://yt3.googleusercontent.com/-7QT9i_su8Jx9i8RwDQW4bX_wS7dhabEVJps3IswpC_3xtJ8Jz1QriXuJx7fpuWekIyBtJXq=s160-c-k-c0x00ffffff-no-rj', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/hm05082'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@limyujin'}]},
    {"category": 'influencer', "org": None, "tag": '정령왕', "real_name": None, "handle": '정령FC', "photo_url": 'https://yt3.googleusercontent.com/E6kfTGrDYbBfn7a8OcBL4frMirAHNl64jAfoaFgyaLfodrzyynYTsbKqkphZNUBqN9WzI4bXjA=s160-c-k-c0x00ffffff-no-rj', "channels": [{"platform": 'chzzk', "url": 'https://chzzk.naver.com/a9b3377345a2a37e68a6072ba5e77fec'}]},
    {"category": 'influencer', "org": None, "tag": '정성민', "real_name": None, "handle": 'T1Seon9min', "photo_url": 'https://nng-phinf.pstatic.net/MjAyNTA4MTdfODYg/MDAxNzU1NDAwNjQzNzA2.klWxpPeT562EN1OPOwi3p-Pd70IJmyVoQwOG1695chwg.IzxW1r2QKJWtxuzSeGb-rAviRtR8sktBc_fDHEUz3-og.JPEG/KakaoTalk_20220912_210802002.jpg?type=f120_120_na', "channels": [{"platform": 'chzzk', "url": 'https://chzzk.naver.com/2d0720ee1e899b13f74486f0a30ba1c6'}]},
    {"category": 'influencer', "org": None, "tag": '철면수심', "real_name": None, "handle": '차돌짬뻥철면수심', "photo_url": 'https://nng-phinf.pstatic.net/MjAyMzEyMTlfNjAg/MDAxNzAyOTYxMjI1Mjg4.ev-ovcbVksFoIqtNZeCwJ3kS5HZ1s6H49pCYWis0ctQg.DhOocVKPlR6bSH7XNmEyVIv20DrN31q3nlYWqW_2sKMg.PNG/%EC%B2%A0%EB%A9%B4%EC%88%98%EC%8B%AC.png?type=f120_120_na', "channels": [{"platform": 'chzzk', "url": 'https://chzzk.naver.com/c892177b4d613127d8c587e9da11d384'}]},
    {"category": 'influencer', "org": None, "tag": '푸린', "real_name": None, "handle": '푸린', "photo_url": 'https://nng-phinf.pstatic.net/MjAyMzEyMTlfNTQg/MDAxNzAyOTY4NDIzNjE0.GN9Dk4gQE0lIL2pfJ1mIz1VnwxaC6aCDFP7XTumaskkg.HwHFCCnnrnHiJfbq6zogmkKyyr7Y4oiaLdisS7TgAXAg.PNG/%ED%91%B8%EB%A6%B0.png?type=f120_120_na', "channels": [{"platform": 'chzzk', "url": 'https://chzzk.naver.com/75bd327f6ba6f57106c79fe3f2c3d19f'}]},
    {"category": 'progamer', "org": 'Nongshim RedForce', "tag": 'BOX', "real_name": '강성훈', "handle": None, "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/12.png', "channels": []},
    {"category": 'progamer', "org": 'T1', "tag": 'Byul', "real_name": '박기홍', "handle": 'T1Byul', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/2.png', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/01byulbyulii'}]},
    {"category": 'progamer', "org": 'DRX', "tag": 'Chan', "real_name": '박찬화', "handle": 'KRXChan', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/15.png', "channels": []},
    {"category": 'progamer', "org": 'DN FREECS', "tag": 'Chase', "real_name": '권창환', "handle": 'DNSChase', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/7.png', "channels": []},
    {"category": 'progamer', "org": 'Dplus KIA', "tag": 'Check', "real_name": '김준수', "handle": 'Checkkk', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/38.png', "channels": []},
    {"category": 'progamer', "org": 'DN FREECS', "tag": 'clutch', "real_name": '박지민', "handle": 'DNSClutch', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/30.png', "channels": []},
    {"category": 'progamer', "org": 'GEN CITY', "tag": 'Crong', "real_name": '황세종', "handle": 'GCTCrong', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/6.png', "channels": []},
    {"category": 'progamer', "org": 'kt Rolster', "tag": 'Dike', "real_name": '강무진', "handle": 'KTDike', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/20.png', "channels": []},
    {"category": 'progamer', "org": None, "tag": 'ELNINO', "real_name": '정인호', "handle": '리바이브엘니뇨', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/14.png', "channels": []},
    {"category": 'progamer', "org": 'Nongshim RedForce', "tag": 'Exito', "real_name": '윤형석', "handle": 'Exit0', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/31.png', "channels": []},
    {"category": 'progamer', "org": None, "tag": 'Froste', "real_name": '김승환', "handle": 'Froste', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/24.png', "channels": []},
    {"category": 'progamer', "org": 'T1', "tag": 'Hoseok', "real_name": '최호석', "handle": 'T1Hoseok', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/3.png', "channels": []},
    {"category": 'progamer', "org": None, "tag": 'Jade', "real_name": '이현민', "handle": '제이드', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/25.png', "channels": []},
    {"category": 'progamer', "org": 'GEN CITY', "tag": 'JiffyJay', "real_name": 'Jifree Baikadem', "handle": None, "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/40.png', "channels": []},
    {"category": 'progamer', "org": 'kt Rolster', "tag": 'JM', "real_name": '김정민', "handle": 'KT김정민', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/9.png', "channels": []},
    {"category": 'progamer', "org": None, "tag": 'JUBJUB', "real_name": '파타나삭 워라난', "handle": None, "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/32.png', "channels": []},
    {"category": 'progamer', "org": 'BNK FEARK', "tag": 'Kaiser', "real_name": '송현수', "handle": 'BFXTaeGod', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/35.png', "channels": []},
    {"category": 'progamer', "org": None, "tag": 'KBG', "real_name": '김병권', "handle": 'KoBigG', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/18.png', "channels": []},
    {"category": 'progamer', "org": None, "tag": 'Korso', "real_name": '배재성', "handle": '1226', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/28.png', "channels": []},
    {"category": 'progamer', "org": 'Dplus KIA', "tag": 'KWAK', "real_name": '곽준혁', "handle": 'DKKWAK', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/29.png', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/904jun'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@FCKWAK'}]},
    {"category": 'progamer', "org": 'BNK FEARK', "tag": 'Light', "real_name": '김선재', "handle": 'BFXLight', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/34.png', "channels": []},
    {"category": 'progamer', "org": 'Dplus KIA', "tag": 'MiBOB', "real_name": '김태현', "handle": 'DKMiBOB', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/39.png', "channels": []},
    {"category": 'progamer', "org": 'DRX', "tag": 'MINION', "real_name": '조민혁', "handle": 'KRXMINION', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/33.png', "channels": []},
    {"category": 'progamer', "org": 'T1', "tag": 'Navy', "real_name": '김유민', "handle": 'T1YooMin', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/4.png', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/kimyoumandu0'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@FConline_KimYooMin'}]},
    {"category": 'progamer', "org": 'BNK FEARK', "tag": 'NoiZ', "real_name": '노영진', "handle": 'BFXNoiZ', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/19.png', "channels": []},
    {"category": 'progamer', "org": 'T1', "tag": 'Ofel', "real_name": '강준호', "handle": 'T1Ofel', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/1.png', "channels": [{"platform": 'soop', "url": 'https://ch.sooplive.co.kr/xjxj4040'}, {"platform": 'youtube', "url": 'https://www.youtube.com/@kangjunho1017'}]},
    {"category": 'progamer', "org": 'DRX', "tag": 'ONE', "real_name": '이원주', "handle": 'KRXONE', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/13.png', "channels": []},
    {"category": 'progamer', "org": 'Nongshim RedForce', "tag": 'ppuljebi', "real_name": '김경식', "handle": 'ppuljebi', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/22.png', "channels": []},
    {"category": 'progamer', "org": 'GEN CITY', "tag": 'RILLA', "real_name": '박세영', "handle": 'GCTRILLA', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/5.png', "channels": []},
    {"category": 'progamer', "org": None, "tag": 'rimGC', "real_name": '장재근', "handle": 'Prime림광철', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/21.png', "channels": []},
    {"category": 'progamer', "org": 'Nongshim RedForce', "tag": 'RYUK', "real_name": '윤창근', "handle": 'ryuK', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/10.png', "channels": []},
    {"category": 'progamer', "org": 'DRX', "tag": 'Savior', "real_name": '이상민', "handle": 'DRXSavior', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/16.png', "channels": []},
    {"category": 'progamer', "org": None, "tag": 'Seoby', "real_name": '신경섭', "handle": '뽀송단수장', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/5/17.png', "channels": []},
    {"category": 'progamer', "org": 'DN FREECS', "tag": 'Shype', "real_name": '김승환', "handle": 'DNSShype', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/27.png', "channels": []},
    {"category": 'progamer', "org": 'GEN CITY', "tag": 'Solid', "real_name": '임태산', "handle": None, "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/41.png', "channels": []},
    {"category": 'progamer', "org": 'BNK FEARK', "tag": 'TaeGod', "real_name": '김태신', "handle": 'BFXLight', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/36.png', "channels": []},
    {"category": 'progamer', "org": 'kt Rolster', "tag": 'TK777', "real_name": '이태경', "handle": 'KTTK77', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/23.png', "channels": []},
    {"category": 'progamer', "org": 'Dplus KIA', "tag": 'TOBIO', "real_name": 'Niwae Banyawat', "handle": None, "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/37.png', "channels": []},
    {"category": 'progamer', "org": 'kt Rolster', "tag": 'UTA', "real_name": '이지환', "handle": 'KTUTA', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/11.png', "channels": []},
    {"category": 'progamer', "org": 'GEN CITY', "tag": 'Wonder08', "real_name": '고원재', "handle": 'GCTwonder08', "photo_url": 'https://ssl.nexon.com/s2/game/fc/online/esports/static/player/7/8.png', "channels": []},
]

# ✅ tots.gg "전체 목록" 페이지 자체에는 없지만(이전 라운드부터) FC.GG가 이미
# 확인해 둔 인플루언서들 — 목록에서 빠졌다고 지우면 오히려 퇴보이므로 별도로
# 유지한다.
# ⚠️ 2026-09-14 round 13 피드백 — 채널을 확실히 확인 못 해 비워뒀던 천국/굴리트/
# 뀨뀨rr/af박준효/김칠홍/유튜브싸커러리는 사용자 요청으로 목록에서 아예 제외했다.
# 교로텔리: 사용자가 직접 SOOP(https://www.sooplive.com/station/phonics1)와
# 유튜브(https://www.youtube.com/@Onepunchk1ng_mk) 채널 링크를 알려줬다. 유튜브
# 채널의 실제 프로필 이름을 확인해보니 "튜브김민교"였고, 이는 사용자가 앞서
# 알려준 실명(김민교)과도 일치해 동일 인물로 확인했다.
# ⚠️ 2026-09-14 round 14 피드백 — 타워/af김우다는 사용자 요청으로 제외했다.
# lictfe의 실명은 사용자가 "정준홍"이라고 확인해줬다(채널 핸들 @junho_J와도
# 자연스럽게 맞는다). 교로텔리(튜브김민교)는 유튜브 채널 페이지에서 실제 프로필
# 사진(og:image)을 직접 확인해 채워 넣었다.
SUPPLEMENTARY_INFLUENCER_ENTRIES = [
    {"category": "influencer", "org": None, "tag": "해설한승엽", "real_name": None, "handle": "해설한승엽",
     "photo_url": "https://yt3.ggpht.com/ytc/AIdro_lajVamFuFW9nRiyIGPmPnwzjbaRhtxhx2VDzFONvhrBC4=s192-c-k-c0x00ffffff-no-rj",
     "channels": [{"platform": "youtube", "url": "https://www.youtube.com/channel/UCdiqIXkagCScUoQnvT_spYw"}]},
    {"category": "influencer", "org": None, "tag": "튜브김민교", "real_name": "김민교", "handle": "교로텔리",
     "photo_url": "https://yt3.googleusercontent.com/ytc/AIdro_mme313qwR54BAkBgchsY38c85NZXC07dIB1HfDeJavz4A=s192-c-k-c0x00ffffff-no-rj",
     "channels": [{"platform": "soop", "url": "https://www.sooplive.com/station/phonics1"},
                  {"platform": "youtube", "url": "https://www.youtube.com/@Onepunchk1ng_mk"}]},
    {"category": "influencer", "org": None, "tag": "lictfe", "real_name": "정준홍", "handle": "lictfe",
     "photo_url": "https://yt3.ggpht.com/h5A6aYBsbKXH7O6CemhmR1h2gP9VqbyGlz_R6gA40_q4F4-YkVuRiwC2PYl-MH0DalHEENzXEUw=s192-c-k-c0x00ffffff-no-rj",
     "channels": [{"platform": "youtube", "url": "https://www.youtube.com/@junho_J"}]},
]

ALL_CREATOR_ENTRIES = TOTS_GG_ROSTER + SUPPLEMENTARY_INFLUENCER_ENTRIES

# ⚠️ 아래 두 리스트는 templates/result.html에서도 그대로 참조한다(Jinja
# 전역으로 등록해서 매번 손으로 맞출 필요 없이 항상 이 두 리스트와 동기화된다 —
# app.jinja_env.globals 등록 부분 참고). TaeGod/Light처럼 같은 handle을 공유하는
# 경우가 있어 dict.fromkeys로 중복 제거(순서는 유지)한다.
PRO_GAMER_NICKNAMES = list(dict.fromkeys(e["handle"] for e in ALL_CREATOR_ENTRIES if e["category"] == "progamer" and e["handle"]))
INFLUENCER_NICKNAMES = list(dict.fromkeys(e["handle"] for e in ALL_CREATOR_ENTRIES if e["category"] == "influencer" and e["handle"]))


def creator_label_for_nickname(nickname):
    """✅ 신규(2026-09-13) — "실시간 인기 구단주" 위젯 등에서 닉네임이 프로게이머/
    인플루언서 목록에 있으면 "프로"/"인플루언서" 라벨을, 아니면 None을 반환한다."""
    if nickname in PRO_GAMER_NICKNAMES:
        return "프로"
    if nickname in INFLUENCER_NICKNAMES:
        return "인플루언서"
    return None


# ✅ result.html의 influencerList/proGamerList가 이 두 리스트를 Jinja tojson으로
# 그대로 읽어가도록 전역 등록(2026-09-13) — 예전엔 result.html에 따로 옮겨 적은
# 하드코딩 배열이라 여기서 닉네임을 바꿀 때마다 손으로 맞춰야 했는데, 이제 한
# 군데만 고치면 자동으로 동기화된다.
app.jinja_env.globals['INFLUENCER_NICKNAMES'] = INFLUENCER_NICKNAMES
app.jinja_env.globals['PRO_GAMER_NICKNAMES'] = PRO_GAMER_NICKNAMES

# ✅ 2026-09-14 round 12 피드백 5번 — 기존에는 여기 INFLUENCER_META 딕셔너리에
# 사람마다 채널 URL/사진을 직접 조사해서 채워 넣었지만, 이제는 사용자가 붙여준
# tots.gg(/influencer) 실제 페이지 HTML을 그대로 파싱해서 TOTS_GG_ROSTER /
# SUPPLEMENTARY_INFLUENCER_ENTRIES 각 항목에 photo_url/channels를 직접 채워
# 넣었으므로(위 참고) 이 중간 딕셔너리는 더 이상 필요 없어 삭제했다.
PLATFORM_LABELS = {
    "youtube": "유튜브",
    "chzzk": "치지직",
    "twitch": "트위치",
    "afreeca": "숲(아프리카TV)",
    "soop": "SOOP",
}


@app.route('/인플루언서', methods=['GET'])
def influencer_list():
    # ✅ 2026-09-13 전면 재설계 — tots.gg처럼 "팀/실명/게임 닉네임" 형태로 보여준다.
    # ALL_CREATOR_ENTRIES(TOTS_GG_ROSTER + 보충 목록)를 그대로 카드로 변환하고,
    # 소속 팀(org)별로 묶어서 team_groups로도 만든다(개인 방송인은 org가 없어
    # "개인 방송" 그룹으로 따로 모은다). 기존 people 플랫 리스트/탭 필터 UI는
    # 그대로 유지해 하위 호환한다.
    def build_person(entry):
        handle = entry.get("handle")
        category = entry["category"]
        tag = entry.get("tag")
        real_name = entry.get("real_name")
        # ✅ 2026-09-14 round 16 피드백 — lictfe처럼 tag가 게임 닉네임(handle)과
        # 완전히 같은 경우(=따로 붙인 활동명이 없다는 뜻)는 큰 이름 자리에 tag를
        # 그대로 다시 보여주는 대신, 실명이 있으면 그걸 큰 이름으로 쓰고 "게임
        # 닉네임" 줄에 handle만 보여준다("정준홍" + "게임 닉네임 lictfe"). tag가
        # handle과 다르면(활동명이 따로 있으면) 기존처럼 tag를 그대로 큰 이름으로 쓴다.
        if tag and tag != handle:
            display_name = tag
        elif real_name:
            display_name = real_name
        else:
            display_name = tag or handle or "?"
        # 큰 이름 자리에 이미 실명이 쓰였으면 "실명 OOO" 줄은 중복이라 생략한다.
        real_name_for_display = real_name if real_name != display_name else None
        channels = [
            {
                "platform": c["platform"],
                "url": c["url"],
                "label": PLATFORM_LABELS.get(c["platform"], c["platform"]),
            }
            for c in entry.get("channels") or []
        ]
        first_channel = channels[0] if channels else {}
        return {
            "nickname": handle,  # 기존 코드/테스트 호환용 필드명(실제 게임 닉네임)
            "handle": handle,
            "has_handle": handle is not None,
            "category": category,
            "category_label": "프로게이머" if category == "progamer" else "인플루언서",
            "org": entry.get("org"),
            "tag": tag,
            "real_name": real_name_for_display,
            "display_name": display_name,
            "channels": channels,
            # 기존 코드/테스트 호환용 — 채널이 여러 개면 tots.gg 표시 순서상 첫 번째만.
            "channel_url": first_channel.get("url"),
            "channel_platform": first_channel.get("platform"),
            "channel_platform_label": first_channel.get("label"),
            "photo_url": entry.get("photo_url"),
        }

    people = [build_person(e) for e in ALL_CREATOR_ENTRIES]

    # ✅ 2026-09-14 round 15 피드백 — 인플루언서 카드 노출 순서를 사용자가 지정한
    # 6명(감스트, 교로텔리=김민교, 메시연=이상호, 호날두=두치와뿌꾸, 잉유진, 방배우)
    # 순서로 먼저 보여주고, 그 다음 나머지 인플루언서는 표시 이름(가나다) 순으로
    # 정렬한다. 핸들(게임 닉네임) 기준으로 매칭해서 표시 이름이 바뀌어도 안전하다.
    INFLUENCER_PRIORITY_HANDLES = ["감스트", "교로텔리", "메시연", "호날두", "잉유진", "방배우"]

    def influencer_sort_key(p):
        if p["category"] == "influencer":
            handle = p["handle"] or ""
            if handle in INFLUENCER_PRIORITY_HANDLES:
                return (0, 0, INFLUENCER_PRIORITY_HANDLES.index(handle), "")
            return (0, 1, 0, p["display_name"] or "")
        # 프로게이머는 기존 tots.gg 표시 순서를 그대로 유지(안정 정렬)한다.
        return (1, 0, 0, "")

    people_for_groups = sorted(people, key=influencer_sort_key)

    teams = OrderedDict()
    for p in people_for_groups:
        # ✅ round 15 피드백 — 인플루언서는 예전 소속 팀 표기(예: 호날두-DN FREECS)가
        # 남아있어도 이 목록에서는 항상 "개인 방송" 그룹으로 모아, 위에서 지정한
        # 순서가 실제 카드 나열에 그대로 반영되도록 한다(프로게이머만 소속 팀별로
        # 묶는다).
        key = p["org"] if (p["org"] and p["category"] == "progamer") else "__solo__"
        if key not in teams:
            org_for_group = key if key != "__solo__" else None
            teams[key] = {"org": org_for_group, "label": org_for_group or "개인 방송", "members": []}
        teams[key]["members"].append(p)
    team_groups = list(teams.values())

    return render_template('influencer.html', people=people, team_groups=team_groups)


# 기존 URL 리다이렉트
@app.route('/influencer.html', methods=['GET'])
def influencer_list_redirect():
    return redirect(url_for('influencer_list'), code=301)


# ============================================================================
# spid.json(선수 id↔이름) 캐시
# - result()가 검색 1건마다 매번 새로 받아오던 것을, 서버 메모리에 캐시(1시간)해서
#   재사용하도록 했습니다. 선수 목록은 자주 안 바뀌는 정적 데이터라 매 요청마다
#   다시 받을 필요가 없어요 — 넥슨 API 호출 횟수도 줄고 응답도 빨라집니다.
#   (MVP 표시, 주력 선수 TOP5에서 선수 이름 조회에도 이 캐시를 재사용합니다)
# ============================================================================
_spid_cache = {"data": None, "ts": 0.0}
_spid_cache_lock = threading.Lock()
SPID_CACHE_TTL_SECONDS = 3600


def get_spid_list():
    """spid.json(선수 id/이름 목록)을 캐시해서 반환. 실패 시 예외를 그대로 전파."""
    now = time.time()
    if _spid_cache["data"] is not None and (now - _spid_cache["ts"]) < SPID_CACHE_TTL_SECONDS:
        return _spid_cache["data"]

    with _spid_cache_lock:
        # 락을 얻는 동안 다른 스레드가 이미 채웠을 수 있으니 다시 확인
        now = time.time()
        if _spid_cache["data"] is not None and (now - _spid_cache["ts"]) < SPID_CACHE_TTL_SECONDS:
            return _spid_cache["data"]

        headers = {"x-nxopen-api-key": f"{app.config['API_KEY']}"}
        resp = requests.get(
            "https://open.api.nexon.com/static/fconline/meta/spid.json",
            headers=headers, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _spid_cache["data"] = data
        _spid_cache["ts"] = time.time()
        return data


def get_spid_name_map():
    """spId -> 선수 한글 이름 dict. 캐시 실패 시 빈 dict(화면에서 이름만 조용히 빠짐)."""
    try:
        return {p.get('id'): p.get('name') for p in get_spid_list()}
    except Exception:
        return {}


# ============================================================================
# ✅ 선수 등급(시즌) 메타데이터 캐시 (신규, 2026-09-12)
#   spid.json 캐시와 완전히 동일한 패턴 — seasonid.json도 로그인/OAuth가 필요 없는
#   완전 공개 정적 데이터라 매 요청마다 새로 받을 필요가 없다. 선수 카드에 등급
#   배지("몇 카인지")를 보여주는 데 쓴다(utils/data_processing.py의
#   derive_season_id()/get_player_rarity() 참고).
# ============================================================================
_season_meta_cache = {"data": None, "ts": 0.0}
_season_meta_cache_lock = threading.Lock()
SEASON_META_CACHE_TTL_SECONDS = 3600


def get_season_meta_list():
    """seasonid.json(시즌/등급 메타데이터)을 캐시해서 반환. 실패 시 예외를 그대로 전파."""
    now = time.time()
    if _season_meta_cache["data"] is not None and (now - _season_meta_cache["ts"]) < SEASON_META_CACHE_TTL_SECONDS:
        return _season_meta_cache["data"]

    with _season_meta_cache_lock:
        # 락을 얻는 동안 다른 스레드가 이미 채웠을 수 있으니 다시 확인
        now = time.time()
        if _season_meta_cache["data"] is not None and (now - _season_meta_cache["ts"]) < SEASON_META_CACHE_TTL_SECONDS:
            return _season_meta_cache["data"]

        headers = {"x-nxopen-api-key": f"{app.config['API_KEY']}"}
        resp = requests.get(
            "https://open.api.nexon.com/static/fconline/meta/seasonid.json",
            headers=headers, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _season_meta_cache["data"] = data
        _season_meta_cache["ts"] = time.time()
        return data


def get_season_meta_map():
    """seasonId(int) -> {"class_name":.., "season_img":..} dict.
    캐시/API 실패 시 빈 dict(화면에서는 등급 배지만 조용히 빠짐)."""
    try:
        return {
            item.get("seasonId"): {
                "class_name": item.get("className"),
                "season_img": item.get("seasonImg"),
            }
            for item in get_season_meta_list()
        }
    except Exception:
        return {}


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
    # ⚠️ 방어 처리(신규): 저장소에 커밋된 community_data.db가 원래 내용이 없는(0바이트)
    # 상태여야 하는데, git으로 받는 방식(웹 UI로 파일 생성 등)에 따라 1바이트짜리
    # 개행문자만 있는 손상된 파일로 저장되는 경우가 있었습니다. sqlite3 버전/환경에
    # 따라 이걸 "file is not a database" 에러로 판단해 앱이 아예 실행되지 않는
    # 문제가 있어(Windows에서 확인됨), 여기서 연결 시도 후 손상된 파일로 판명되면
    # 자동으로 지우고 새로 만들도록 했습니다. 정상 사용에는 영향 없습니다.
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('SELECT 1')
    except sqlite3.DatabaseError:
        try:
            conn.close()
        except Exception:
            pass
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
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
            (95, '키보드게시판', '피파봇', '피파봇 화이팅!', '2026-01-27 10:00:00'),
            (94, '건의사항', 'ㅋ', '공피하기 겜 어떻게 하는거임', '2026-01-26 10:00:00'),
            (93, '키보드게시판', '맨체스터유나이티드앱갤러리', '맨체스터유나이티드앱갤러리 화이팅', '2026-01-25 10:00:00'),
            (92, '패드게시판', '리무진', 'WANGok <--- 순경 패드립 볼돌 유저임 만나면 채팅 끄고 하시는게 이로움', '2026-01-21 10:00:00'),
            (91, '키보드게시판', '아스널', '아스널 팬 모여라👇👇', '2026-01-20 10:00:00'),
            (90, '자유게시판', 'NEKOLA', 'Zerosugar > 패드립과 욕설사용', '2026-01-19 10:00:00'),
            (89, '자유게시판', '상윤', '화이팅', '2026-01-18 10:00:00'),
            (88, '키보드게시판', '서울이왔다', '파워슛하면 잔디가파여요', '2026-01-17 10:00:00'),
            (87, '자유게시판', '길거리마인부', '클상도의 희망 서도일 화이팅', '2026-01-13 10:00:00'),
            (86, '자유게시판', '90호', '주먹다짐하실분 인게임 친추부탁드리겠습니다.', '2026-01-12 10:00:00'),
            (85, '자유게시판', '성덕동', '저는 탈주가 조아요 조아요', '2026-01-11 10:00:00'),
            (84, '자유게시판', '슥속샤악', '실제로 했어요', '2026-01-10 10:00:00'),
            (83, '자유게시판', '문창중맥토미니', '이기고 싶어요', '2026-01-09 10:00:00'),
            (82, '자유게시판', '술탄오브스윙', '이 사람 맨날 태클만 박아요', '2026-01-08 10:00:00'),
            (81, '키보드게시판', '길군숯불돼지갈비', '왜 저의 파워 슛은 잔디깎기 슛만 나갈까요', '2026-01-02 10:00:00'),
            (80, '자유게시판', '날두루치기', '뜨자용', '2026-01-01 10:00:00'),
            (79, '키보드게시판', 'ㅈㄴㄱㅃㅅㅈㅎㄱ', 'ㅅㄴㄱㄴㅈㄱㅈㄱ', '2025-12-31 10:00:00'),
            (78, '키보드게시판', 'yjyfjjyr', '게임', '2025-12-30 10:00:00'),
            (77, '키보드게시판', '킵킵', 'ZeroSuger < 일방적인 시비 및 인신공격 및 패드립', '2025-12-11 10:00:00'),
            (76, '자유게시판', '발', '발롱 시즌 패키지에서 좀 줄어들어서 그럴수더?', '2025-12-07 10:00:00'),
            (75, '자유게시판', 'ㅇㅇ', '발롱 에우제비우 지금 금카를 못구하길래 강화로 붙였는데 얼마까지 오를까요.. 그나저나 이거 왜 빨간 불이에요?', '2025-12-05 10:00:00'),
            (74, '키보드게시판', '12', '주은 < 인맥모집', '2025-11-23 10:00:00'),
            (73, '자유게시판', '도날덕', '펠레!', '2025-11-16 10:00:00'),
            (72, '자유게시판', 'I생II제I르II망I', '불법프로그램으로 IP유추 및 신상 협박 욕설 사용', '2025-11-07 10:00:00'),
            (71, '키보드게시판', 'I생II제I르II망I', '불법프로그램 사용으로 신상 협박 욕설사용', '2025-11-07 10:00:00'),
            (70, '키보드게시판', 'I생II제I르II망I', '불법프로그램 사용으로 신상 협박 욕설사용', '2025-11-07 10:00:00'),
            (69, '키보드게시판', '키보드', '불법프로그램 사용으로 신상 협박 욕설사용', '2025-11-07 10:00:00'),
            (68, '자유게시판', '전생의 긱스', '광고가 너무 많아요 광고 좀 줄여줘요 ㅡㅡ', '2025-10-24 10:00:00'),
            (67, '자유게시판', '전생의 루니', '업데이트 주기는 얼마나 되나여', '2025-10-23 10:00:00'),
            (66, '자유게시판', 'lee상호', '중거리호!', '2025-09-28 10:00:00'),
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
# ⚠️ 방어 처리(신규) — init_db()는 원래 `if __name__ == '__main__':` 안에서만 호출되고
# 있었는데, 이러면 gunicorn/waitress 같은 WSGI 서버가 app.py를 "모듈로 import"만 하고
# __main__으로 실행하지 않는 배포 방식에서는 search_data.db/nickname_searches 테이블이
# 아예 생성되지 않아 닉네임 검색 저장 시 "no such table" 오류가 날 수 있었다.
# initialize_database()와 동일하게 모듈 로드 시점에 항상 실행되도록 맞춘다.
init_db()
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
        callback_url = body.get("userRequest", {}).get("callbackUrl")

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
        text = re.sub(r"^@\S+\s*", "", text)  # @축구봇 제거
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


        basic = json_get("https://open.api.nexon.com/fconline/v1/user/basic",
                         {"ouid": ouid}, headers)
        lv = basic.get("level", "?")

        # 티어 이미지(여유 있을 때만)
        tier_image = None

        # ✅ 신규 "마스터" 티어 추가로 인해 공용 DIVISION_MAPPING(utils/data_processing.py)을
        # 재사용하도록 변경 — 예전에 여기 따로 있던 오래된 테이블은 새 티어를 못 찾아
        # 정보 없음으로 표시되는 문제가 있었다.
        division_mapping = DIVISION_MAPPING
        divi = json_get("https://open.api.nexon.com/fconline/v1/user/maxdivision",
                        {"ouid": ouid}, headers)
        tier_image = pick_tier_image(divi, mode)

        badge_url = None
        if tier_image:
            public_root = app.config.get("PUBLIC_ROOT", request.url_root.rstrip("/"))
            # badge_url = f"{public_root}/tierbadge?url={quote_plus(tier_image)}&size=240&bgw=1000&bgh=600"
            badge_url = f"{public_root}/tierbadge?url={quote_plus(tier_image)}&size=480&bgw=1000&bgh=600"

        # ---------- 최근 경기 ----------
        
        matches = json_get("https://open.api.nexon.com/fconline/v1/user/match",
                           {"ouid": ouid, "matchtype": mode, "limit": MAX_DETAIL},
                           headers)

        # ---------- 경량 상세/계산 ----------
        win_rate_text = "데이터 없음"
        play_style_text = "플레이스타일 분석 불가"
        original_win_rate = modified_win_rate = win_rate_improvement = None
        improved_features_text = ""

        if matches:
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

            if imp_rows:
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

        #         if found_cmd == "승률개선":
        #             try:
        #                 padded_imp = np.array(filt, dtype=float)
        #                 (
        #                     top_n,
        #                     increase_ratio,
        #                     improved_features_text,
        #                     original_win_rate,
        #                     modified_win_rate,
        #                     win_rate_improvement,
        #                 ) = calculate_win_improvement(padded_imp, w_l_data, data_label)
        #             except Exception:
        #                 original_win_rate = modified_win_rate = win_rate_improvement = None
        #                 improved_features_text = ""

        # # ---------- 카드 ----------
        MATCH_TYPE_MAP = globals().get("MATCH_TYPE_MAP", {})
        result_url = f"https://fcgg.kr/전적검색/{nick}/공식경기"
        imp_url    = f"https://fcgg.kr/승률개선결과/{nick}/공식경기"

        # if found_cmd == "승률개선":
            
        #     # -----------------------------
        #     # 여기서는 카드(card)만 만들어두고
        #     # 즉시 리턴하지 않는다 (중요)
        #     # -----------------------------
        #     if (
        #         original_win_rate is not None and
        #         modified_win_rate is not None and
        #         win_rate_improvement is not None
        #     ):
        #         head = f"{nick}  Lv.{lv}"
        #         body_lines = [
        #             "",
        #             "❮개선 시 승률❯\n"
        #             f"{original_win_rate * 100:.2f}% ➜ {modified_win_rate * 100:.2f}% "
        #             f"(＋{win_rate_improvement * 100:.2f}%p)\n\n"
        #             "❮개선해야하는 지표❯"
        #         ]
        #         if improved_features_text:
        #             feat_lines = [
        #                 ln.strip()
        #                 for ln in improved_features_text.splitlines()
        #                 if ln.strip()
        #             ]
        #             feat_lines = (
        #                 feat_lines[:5]
        #                 if len(feat_lines) > 5 else feat_lines
        #             )
        #             body_lines.extend(feat_lines)
        #         else:
        #             body_lines.append("분석 데이터가 부족합니다.")
        #         description = head + "\n" + "\n".join(body_lines)
        #         card = {
        #             "basicCard": {
        #                 "description": description,
        #                 "thumbnail": (
        #                     {"imageUrl": badge_url} if badge_url else {}
        #                 ),
        #                 "buttons": [
        #                     {
        #                         "label": "승률개선 자세히 보기",
        #                         "action": "webLink",
        #                         "webLinkUrl": imp_url
        #                     },
        #                     {
        #                         "label": "전적검색",
        #                         "action": "block",
        #                         "blockId": JJ_id,
        #                         "extra": {"params": {"nick": nick}}
        #                     }
        #                 ]
        #             }
        #         }
        #     else:
        #         card = {
        #             "simpleText": {
        #                 "text": "최근 전적 경기 수가 부족합니다."
        #             }
        #         }

        #     # -----------------------------
        #     # 콜백 처리
        #     # -----------------------------
        #     if callback_url:
        #         # 긴 계산 끝난 결과(card)를 callback_url로 따로 보내기
        #         def _send_callback():
        #             try:
        #                 payload = {
        #                     "version": "2.0",
        #                     "template": {"outputs": [card]}
        #                 }
        #                 # timeout은 콜백 POST 한 번에 대한 네트워크 제한일 뿐이니
        #                 # 60 정도로 넉넉히 잡아도 돼 (5초 제한은 skill 응답쪽임)
        #                 requests.post(callback_url, json=payload, timeout=60)
        #             except Exception as e:
        #                 print("[callback error]", e)

        #         threading.Thread(
        #             target=_send_callback,
        #             daemon=True
        #         ).start()

        #         # 먼저 즉답: useCallback=true를 돌려서
        #         # 카카오가 "콜백 기다리는 중" 상태로 들어가게
        #         return jsonify({
        #             "version": "2.0",
        #             "useCallback": True,
        #             "data": {
        #                 "text": f"{nick}님의 승률을 끌어올리는 중입니다!"
        #             }
        #         })

        #     # fallback (콜백 미지원일 경우 = callback_url 없음)
        #     return jsonify({
        #         "version": "2.0",
        #         "template": {"outputs": [card]}
        #     })
         # ---------- 승률개선 비동기 처리 ----------
        if found_cmd == "승률개선":
            import threading, requests, numpy as np

            def _async_improve_and_callback():
                """오래 걸리는 승률개선 계산을 백그라운드에서 수행하고 callback_url로 카드 전송"""
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

                # ----- 카드 생성 -----
                if (
                    original_win_rate is not None and
                    modified_win_rate is not None and
                    win_rate_improvement is not None
                ):
                    head = f"{nick}  Lv.{lv}"
                    body_lines = [
                        "",
                        "❮개선 시 승률❯\n"
                        f"{original_win_rate * 100:.2f}% ➜ {modified_win_rate * 100:.2f}% "
                        f"(＋{win_rate_improvement * 100:.2f}%p)\n\n"
                        "❮개선해야하는 지표❯"
                    ]
                    if improved_features_text:
                        feat_lines = [
                            ln.strip()
                            for ln in improved_features_text.splitlines()
                            if ln.strip()
                        ]
                        feat_lines = feat_lines[:5] if len(feat_lines) > 5 else feat_lines
                        body_lines.extend(feat_lines)
                    else:
                        body_lines.append("분석 데이터가 부족합니다.")
                    description = head + "\n" + "\n".join(body_lines)
                    card = {
                        "basicCard": {
                            "description": description,
                            "thumbnail": (
                                {"imageUrl": badge_url} if badge_url else {}
                            ),
                            "buttons": [
                                {
                                    "label": "승률개선 자세히 보기",
                                    "action": "webLink",
                                    "webLinkUrl": imp_url
                                },
                                {
                                    "label": "전적검색",
                                    "action": "block",
                                    "blockId": JJ_id,
                                    "extra": {"params": {"nick": nick}}
                                }
                            ]
                        }
                    }
                else:
                    card = {
                        "simpleText": {"text": "최근 전적 경기 수가 부족합니다."}
                    }

                # ----- 콜백 전송 -----
                if callback_url:
                    try:
                        payload = {
                            "version": "2.0",
                            "template": {"outputs": [card]}
                        }
                        requests.post(callback_url, json=payload, timeout=60)
                        print(f"[callback sent] {nick}")
                    except Exception as e:
                        print("[callback error]", e)

            # 비동기 스레드로 실행 (즉시 응답 위해)
            threading.Thread(target=_async_improve_and_callback, daemon=True).start()

            # 즉시 응답 (카카오 5초 제한 내)
            return jsonify({
                "version": "2.0",
                "useCallback": True,
                "data": {
                    "text": f"{nick}님의 승률을 끌어올리는 중입니다!"
                }
            })
        else:
            # ---------------- 기존 전적검색 분기 ----------------
            if len(matches) == 0:
                return jsonify({
                    "version": "2.0",
                    "template": {
                        "outputs": [{
                            "simpleText": {
                                "text": "최근 전적 경기 수가 부족합니다."
                            }
                        }]
                    }
                })

            title = f"{nick} · Lv.{lv}"
            desc_common = (
                f"승률 {win_rate_text}\n"
                f"❮플레이스타일❯\n"
                f"{play_style_text}"
            )
            card = {
                "basicCard": {
                    "description": (
                        f"{title}\n\n"
                        f"{desc_common}\n\n"
                        f"최근 {min(len(matches or []), MAX_DETAIL)}경기 기반 전적입니다."
                    ),
                    "thumbnail": (
                        {"imageUrl": badge_url} if badge_url else {}
                    ),
                    "buttons": [
                        {
                            "label": "전적 자세히 보기",
                            "action": "webLink",
                            "webLinkUrl": result_url
                        },
                        {
                            "label": "승률개선",
                            "action": "block",
                            "blockId": SL_id,
                            "extra": {"params": {"nick": nick}}
                        }
                    ]
                }
            }

            return jsonify({
                "version": "2.0",
                "template": {"outputs": [card]}
            })

    except Exception as e:
        print("[ERROR]", e)
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": "분석 중 오류가 발생했습니다. 다시 시도해 주세요."
                    }
                }]
            }
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


# ------------------------------------------------------------
# 승부차기 미니게임 - 채팅방별 랭킹 지원 완성본
# ------------------------------------------------------------
import random, threading
from flask import request, jsonify

# 전역 게임 상태
# 개인별 현재 진행중인 게임만 관리 (방 구분 X, uid 단위 턴제라 그대로 둬도 됨)
PENALTY_GAMES = {}  # { uid: {"shots": [True/False...], "max": 5} }
PG_LOCK = threading.Lock()

# 전역 누적(커리어) 성공률 저장
# CAREER[room_id][uid] = {"goals": int, "shots": int}
CAREER = {}
C_LOCK = threading.Lock()

# (선택) 닉네임 캐싱 - 멘션이 불가한 경우 fallback로 쓸 수 있음
NAMEBOOK = {}  # { uid: "nickname" }
N_LOCK = threading.Lock()


# ========================= 누적/리더보드 유틸 =========================
def _career_add(room_id: str, uid: str, goals: int, shots: int):
    """이번 게임 성적을 해당 room_id(채팅방) 커리어에 누적."""
    if shots <= 0:
        return
    with C_LOCK:
        room_stat = CAREER.setdefault(room_id, {})
        st = room_stat.setdefault(uid, {"goals": 0, "shots": 0})
        st["goals"] += goals
        st["shots"] += shots


def _career_rate(room_id: str, uid: str):
    """room_id 안에서 uid의 누적 성공률(0~1). 없으면 None."""
    with C_LOCK:
        room_stat = CAREER.get(room_id, {})
        st = room_stat.get(uid)
        if not st or st["shots"] <= 0:
            return None
        return st["goals"] / st["shots"]


def _leaders(room_id: str):
    """
    room_id(현재 채팅방) 내에서 성공률 기준 내림차순 정렬 리스트 반환
    [(uid, rate, goals, shots), ...]
    """
    with C_LOCK:
        room_stat = CAREER.get(room_id, {})
        items = []
        for k, v in room_stat.items():
            shots = v.get("shots", 0)
            goals = v.get("goals", 0)
            if shots > 0:
                rate = goals / shots
                items.append((k, rate, goals, shots))
    # 동률 안정화를 위해: 성공률↓, 시도수↓, uid↑
    items.sort(key=lambda x: (-x[1], -x[3], x[0]))
    return items


def _rank_of(room_id: str, uid: str):
    """(등수, 총원). 해당 room_id 내에서만 계산. 기록 없으면 (None, 총원)"""
    items = _leaders(room_id)
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


def _format_leaderboard_and_mentions(room_id: str, uid: str, limit: int = 10):
    """
    특정 room_id(=채팅방) 기준으로만 리더보드 텍스트와 extra.mentions 딕셔너리를 생성.
    - user1은 항상 요청자(uid)
    - 상위 limit명까지 user2, user3 ... 로 멘션 키 자동 할당
    - 본문에는 "{{#mentions.userX}}" 토큰을 정확히 매칭
    """
    items = _leaders(room_id)
    if not items:
        text = "아직 이 채팅방에는 기록이 없습니다.\n승부차기를 먼저 플레이해 주세요!"
        mentions = {"user1": {"type": "botUserKey", "id": uid}}
        return text, mentions

    top_uid, top_rate, _, _ = items[0]
    header = (
        "승부차기 평균 성공률 결과\n\n"
        f"🥇현재 1등 : {round(top_rate * 100)}%\n\n"
    )

    # mentions: user1은 항상 요청자
    mentions = {"user1": {"type": "botUserKey", "id": uid}}

    lines = []
    dyn_idx = 2  # user2부터 시작
    for i, (k, rate, goals, shots) in enumerate(items[:limit], start=1):
        if k == uid:
            # 요청자 줄: user1 멘션 사용
            line = f"{i}. " + "{{#mentions.user1}}" + f" {round(rate * 100)}%"
        else:
            # 다른 유저도 멘션으로 표시하려면 user2, user3 ... 동적 할당
            key = f"user{dyn_idx}"
            mentions[key] = {"type": "botUserKey", "id": k}
            line = (
                f"{i}. "
                + "{{#mentions." + key + "}}"
                + f" {round(rate * 100)}%"
            )
            dyn_idx += 1
        lines.append(line)

    # 내 현재 등수도 보여주자 (채팅방 기준)
    my_rank, total = _rank_of(room_id, uid)
    if my_rank:
        lines.append(f"\n내 현재 등수: {my_rank}등")

    lines.append("\n랭킹은 주기적으로 갱신됩니다.")

    text = header + "\n".join(lines)
    return text, mentions

# ====================================================================


# ---- Payload helpers ---------------------------------------------------------
def _uid(body: dict) -> str:
    """
    Kakao 스펙 기준: user.id (type=botUserKey).
    환경에 따라 accountId 등도 들어올 수 있어 안전 처리.
    """
    user = ((body.get("userRequest") or {}).get("user") or {})
    uid = (user.get("id") or "").strip()
    return uid or "unknown"


def _uname(body: dict) -> str:
    """
    카카오 문서에는 nickname 필드가 보장되지 않음 → 표시명은 uid로 대체.
    가능하면 properties.nickname 사용.
    """
    user = ((body.get("userRequest") or {}).get("user") or {})
    props = user.get("properties") or {}
    nickname = (props.get("nickname") or "").strip()
    uid = (user.get("id") or "").strip() or "unknown"
    return nickname or uid


def _room_id(body: dict) -> str:
    """
    채팅방(그룹채팅방) 식별자 추출.

    우선순위
    1) userRequest.chat.properties.botGroupKey  -> 문서상 '팀채팅방 식별키'
    2) userRequest.chat.id                      -> chat.id 도 botGroupKey와 동일하게 내려온다고 명시
    3) conversation.id                          -> 일부 환경에서만 존재
    4) "global"                                 -> 최후 fallback
    """
    ur = body.get("userRequest") or {}

    chat = ur.get("chat") or {}
    chat_props = chat.get("properties") or {}

    group_key_from_props = (chat_props.get("botGroupKey") or "").strip()
    group_key_from_chat_id = (chat.get("id") or "").strip()

    conv = body.get("conversation") or {}
    conv_id = (conv.get("id") or "").strip()

    room = (
        group_key_from_props
        or group_key_from_chat_id
        or conv_id
        or "global"
    )
    return str(room)


def _param_from_action(body: dict, key: str) -> str:
    """action.params 우선, 없으면 action.detailParams[key].value"""
    
    action = body.get("action") or {}
    params = action.get("params") or {}
    # if key in params and params[key] is not None:
    #     return str(params[key])
    # dparams = action.get("detailParams") or {}
    # if key in dparams and dparams[key] is not None:
    #     val = (dparams[key] or {}).get("value")
    #     if val is not None:
    #         return str(val)
    if key in params and params[key] is not None:
        userRequest = body.get("userRequest") or {}
        dir = userRequest.get("utterance") or {}
        
        if dir is not None:
            return dir
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
    opts = ["왼쪽", "가운데", "오른쪽", "왼쪽위", "왼쪽아래", "오른쪽위", "오른쪽아래"]
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
                if s is val:
                    c += 1
                else:
                    break
            return c

        def _pick(arr):
            return random.choice(arr) if arr else ""

        # ✅ GitHub Raw URL 버전 (유지)
        RIGHT_GOAL_URL  = "https://raw.githubusercontent.com/YeaHongSu/FC.GG/refs/heads/main/right_goal.png"
        CENTER_GOAL_URL = "https://raw.githubusercontent.com/YeaHongSu/FC.GG/refs/heads/main/center_goal.png"
        LEFT_GOAL_URL   = "https://raw.githubusercontent.com/YeaHongSu/FC.GG/refs/heads/main/left_goal.png"

        RIGHT_MISS_URL  = "https://raw.githubusercontent.com/YeaHongSu/FC.GG/refs/heads/main/right_miss.png"
        CENTER_MISS_URL = "https://raw.githubusercontent.com/YeaHongSu/FC.GG/refs/heads/main/center_miss.png"
        LEFT_MISS_URL   = "https://raw.githubusercontent.com/YeaHongSu/FC.GG/refs/heads/main/left_miss.png"

        # ✅ (추가) 방향×결과 매핑 (골/노골에 따라 다른 PNG 선택)
        RESULT_IMG = {
            "left":   {True: LEFT_GOAL_URL,   False: LEFT_MISS_URL},
            "center": {True: CENTER_GOAL_URL, False: CENTER_MISS_URL},
            "right":  {True: RIGHT_GOAL_URL,  False: RIGHT_MISS_URL},
        }

        def _normalize_dir(direction_text: str) -> str:
            d = (direction_text or "").strip().lower()
            if ("왼" in d) or ("left" in d):
                return "left"
            if ("오" in d) or ("right" in d):
                return "right"
            # 가운데/중앙/center 또는 애매하면 center
            return "center"

        def _pick_result_img(direction_text: str, is_goal: bool) -> str:
            key = _normalize_dir(direction_text)
            return RESULT_IMG[key][is_goal]

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
        room_id = _room_id(body)  # ★ 채팅방 ID 추출 (핵심)
        print("[DEBUG] room_id =", _room_id(body), "| botGroupKey =", ((body.get("userRequest") or {}).get("bot") or {}).get("botGroupKey"))

        # 닉네임 캐싱
        _save_name(uid, uname)

        uter = (body.get("userRequest") or {}).get("utterance") or ""
        st = _state(uid)

        GM_id = ((body.get("userRequest")).get("block")).get("id")  # "블록ID 예: 68c7f4b6..."

        # ---- (A) '결과보기' 요청 처리 -----------------------------------------
        if uter in ['결과보기', '결과 보기', '랭킹', '랭킹보기', '결과']:
            # 이 채팅방(room_id) 기준으로만 리더보드 생성
            lb_text, mentions = _format_leaderboard_and_mentions(room_id, uid, limit=10)
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
                            "text": "📣 승부차기 종료!"
                        }
                    }, {
                "textCard": {
                    "title": "다시 도전할까요? 😀",
                    "buttons": [
                        {"label": "승부차기",  "action": "block", "blockId": GM_id},
                        {"label": "결과보기", "action": "message", "messageText": "결과보기"}
                    ], "buttonLayout": "horizontal"
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
                                "📣 승부차기가 시작됩니다! 기회는 5번!🧍‍ vs 🧤"
                            )
                        }
                    },{ "textCard": {
                        "title": "방향을 선택하세요.",
                        "buttons": [
                            # ✅ (수정) message -> block 로 같은 블록으로 강제 라우팅
                            {"label": "왼쪽", "action": "block", "blockId": GM_id, "messageText": "왼쪽"},
                            {"label": "가운데", "action": "block", "blockId": GM_id, "messageText": "가운데"},
                            {"label": "오른쪽", "action": "block", "blockId": GM_id, "messageText": "오른쪽"}]
                    }}],
                }
            })

        # 현재 상태/회차
        st = _state(uid)
        if not st:
            # 잘못된 진입 보호
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{
                        "simpleText": {
                            "text": "먼저 '@축구봇 승부차기'로 시작해 주세요!"
                        }
                    }]
                }
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
                                f"현재: {board}"
                            )
                        }
                    }, {"textCard": {
                        "title": "방향을 선택하세요.",
                        "buttons": [
                            # ✅ (수정) message -> block
                            {"label": "왼쪽", "action": "block", "blockId": GM_id, "messageText": "왼쪽"},
                            {"label": "가운데", "action": "block", "blockId": GM_id, "messageText": "가운데"},
                            {"label": "오른쪽", "action": "block", "blockId": GM_id, "messageText": "오른쪽"}]
                    }}]
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

        # ✅ (핵심) 이번 슛 결과(success)에 따라 골/노골 PNG 선택
        result_img_url = _pick_result_img(dir_text, success)
        
        # 연속 카운트 계산
        def _streak_tail_local(shots_local, val):
            c = 0
            for s in reversed(shots_local):
                if s is val:
                    c += 1
                else:
                    break
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
        prefix = (
            "{{#mentions.user1}}"
            + f" {head} {board} ({n}/5회)\n"
            + "🧍‍ vs 🧤  |  현재 스코어 "
            + f"{total}골"
        )
        reaction = f"\n{vibe}\n{gk_line}"

        if done:
            # ---- 게임 종료: 커리어 누적 & 요약 + 버튼(승부차기/결과보기) ----------
            _career_add(room_id, uid, total, len(shots))  # ★ 방별 커리어 누적

            badge = end_badge(total)
            summary = (
                f"\n\n📣 게임 종료! {total}/5 성공! (성공률 {round(total/5*100)}%)\n"
                f"{badge}\n"
            )
            card = {
                "basicCard": {
                    "title": "다시 도전할까요? 😀",
                    "thumbnail": {"imageUrl": result_img_url},
                    "buttons": [
                        {"label": "승부차기",  "action": "block", "blockId": GM_id},
                        {"label": "결과보기", "action": "message", "messageText": "결과보기"}
                    ], "buttonLayout": "horizontal"
                }
            }
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [
                        # ✅ (추가) 이미지 먼저
                        {"simpleText": {"text": prefix + reaction + summary}},
                        card
                    ]
                },
                "extra": {
                    # 종료 메시지는 요청자 멘션만 유지(짧게)
                    "mentions": {"user1": {"type": "botUserKey", "id": uid}}
                }
            })

        # 진행 중이면 다음 입력 유도
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [
                    # ✅ (추가) 이미지 먼저
                    {"simpleText": {"text": prefix + reaction}},
                    { "basicCard": {
                        "title": "방향을 선택하세요.",
                        "thumbnail": {"imageUrl": result_img_url},
                        "buttons": [
                            # ✅ (수정) message -> block
                            {"label": "왼쪽", "action": "block", "blockId": GM_id, "messageText": "왼쪽"},
                            {"label": "가운데", "action": "block", "blockId": GM_id, "messageText": "가운데"},
                            {"label": "오른쪽", "action": "block", "blockId": GM_id, "messageText": "오른쪽"}]
                    }}
                ],
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
                        "text": "문제가 발생했어요. '@축구봇 승부차기'로 다시 시작해 주세요."
                    }
                }]
            }
        })


# ============================================================================
# 초성퀴즈(선수 이름 맞추기) + 폴백 라우터
# - /kakao/playerquiz        : 초성퀴즈 전용 스킬
# - /kakao/fallback_router   : "미처리발화/도움말(풀백) 블록"이 호출할 스킬
#     -> 퀴즈 진행 중이면 playerquiz 로직으로 위임(정답판정)
#     -> 아니면 (순위보기/시작어 등은 playerquiz로 위임) / 그 외는 도움말
# ============================================================================

import time, random, threading, re
from flask import request, jsonify

from player_info import all_players as _all_players
from player_info import make_chosung as _make_chosung

PQ_TIME_LIMIT = 60
PQ_MAX_HINTS = 4

PQ_LOCK = threading.Lock()

# ✅ "현재 진행중인 문제" 상태 (진행중 여부 판단은 이 dict 존재 여부로)
# room_id -> {"player":..., "started_at":..., "hint_idx":...}
PQ_STATE = {}

# ✅ 방 단위 98명 사이클 중복 방지용(진행 상태와 분리!)
# room_id -> [seen_player_id, ...]
PQ_CYCLE = {}

# ✅ 랭킹(방 단위)
# room_id -> {uid: score}
PQ_RANK_LOCK = threading.Lock()
PQ_RANK = {}

MENTION_RE = re.compile(r"^\s*@[^\s]+\s*")  # '@축구봇 ' 제거

# ✅ 멘션 토큰은 절대 format() 쓰면 깨질 수 있음. 그대로 출력만 한다.
MENTION_KEY = "sender"
MENTION_TOKEN = "{{#mentions.sender}}"

# ----------------------------
# ✅ 공용 응답 (기존 유지)
# ----------------------------
def pq_text(msg: str, mentions):
    resp = {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": msg}}],
        }
    }
    if mentions is not None:
        resp["extra"] = {"mentions": mentions}
    return jsonify(resp)
    
def pq_text_with_buttons(msg: str, mentions):
    if mentions is None:
        return jsonify({
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": msg}}, {
                        "textCard": {
                            "title": "다시 도전할까요? 😀",
                            "buttons": [
                                {"label": "초성퀴즈", "action": "message", "blockId": "초성퀴즈"}
                            ]
                        }
            }]}
        })
    else:
        return jsonify({
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": msg}}, {
                        "textCard": {
                            "title": "다시 도전할까요? 😀",
                            "buttons": [
                                {"label": "초성퀴즈", "action": "message", "blockId": "초성퀴즈"}
                            ]
                        }
                    }]},
            "extra": {"mentions": mentions}
        })

def pq_text_with_hint(msg: str, mentions):
    if mentions is None:
        return jsonify({
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": msg}}, {
                        "textCard": {
                            "title": "힌트가 필요하신가요? 😀",
                            "buttons": [
                                {"label": "힌트", "action": "message", "blockId": "힌트"}
                            ]
                        }
            }]}
        })
    else:
        return jsonify({
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": msg}}, {
                        "textCard": {
                            "title": "힌트가 필요하신가요? 😀",
                            "buttons": [
                                {"label": "힌트", "action": "message", "blockId": "힌트"}
                            ]
                        }
                    }]},
            "extra": {"mentions": mentions}
        })

def pq_text_with_mention(msg: str, mentions):
    if mentions is None:
        return jsonify({
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": msg}}, {
                        "textCard": {
                            "title": "정답을 입력해보세요! 😄",
                            "buttons": [
                                {"label": "@축구봇", "action": "mention"}
                            ]
                        }
            }]}
        })
        
def pq_text_with_quickreplies(msg: str, mentions, quick_replies=None):
    resp = {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": msg}}],
        }
    }
    if quick_replies:
        resp["template"]["quickReplies"] = quick_replies
    if mentions is not None:
        resp["extra"] = {"mentions": mentions}
    return jsonify(resp)

# ----------------------------
# ✅ 정답/시간초과/포기: 텍스트 + 이미지 + '다음 문제/순위보기' 버튼
# ----------------------------
def pq_text_with_image_next(msg: str, img_url: str, alt_text: str, mentions):
    outputs = [{"simpleText": {"text": msg}}]

    # if img_url:
    #     outputs.append({
    #         "simpleImage": {
    #             "imageUrl": img_url,
    #             "altText": alt_text or "player"
    #         }
    #     })
    
    from urllib.parse import quote_plus
    
    def public_root_from_request(app, request):
        # PUBLIC_ROOT가 있으면 그걸 쓰고, 없으면 현재 요청 host 기준
        return app.config.get("PUBLIC_ROOT", request.url_root.rstrip("/"))
    
    def wrap_img_url(app, request, raw_url: str, *, size=480, bgw=1000, bgh=600) -> str:
        """
        raw_url: 원본 이미지 URL(넥슨 CDN 등)
        return: /tierbadge?url=... 로 래핑된 최종 URL
        """
        public_root = public_root_from_request(app, request)
        return f"{public_root}/tierbadge?url={quote_plus(raw_url)}&size={int(size)}&bgw={int(bgw)}&bgh={int(bgh)}"
    
    
    img_url = wrap_img_url(app, request, img_url, size=480, bgw=1000, bgh=600)

    # ✅ 결과 카드(항상 노출) + "순위보기" 버튼 추가
    outputs.append({
        "basicCard": {
            "title": "다음 문제로 갈까요?",
            "thumbnail": {"imageUrl": img_url},
            "buttons": [
                {"label": "순위보기", "action": "message", "messageText": "순위보기"},
                {"label": "초성퀴즈", "action": "message", "messageText": "초성퀴즈"},
            ], "buttonLayout": "horizontal"
        }
    })

    resp = {
        "version": "2.0",
        "template": {
            "outputs": outputs,
        }
    }
    if mentions is not None:
        resp["extra"] = {"mentions": mentions}
    return jsonify(resp)

def pq_strip_mention(s: str) -> str:
    s = (s or "").strip()
    while True:
        ns = MENTION_RE.sub("", s).strip()
        if ns == s:
            return s
        s = ns

def pq_norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"^(정답|답)\s*[:：]\s*", "", s)     # "정답: 메시"
    s = re.sub(r"[^0-9a-z가-힣]+", "", s)          # 한글/영문/숫자만 남김
    return s

def extract_utterance(body: dict) -> str:
    ur = body.get("userRequest") or {}
    utter = ur.get("utterance")
    if utter:
        return utter

    action = body.get("action") or {}
    params = action.get("params") or {}
    if isinstance(params, dict) and params.get("utterance"):
        return str(params.get("utterance"))

    detail = action.get("detailParams") or {}
    if isinstance(detail, dict):
        for v in detail.values():
            if isinstance(v, dict) and v.get("value"):
                return str(v.get("value"))

    return ""

def deep_get(d, path, default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def get_room_id(body: dict) -> str:
    """
    ✅ 같은 단톡방이면 무조건 같은 room_id가 나오게 후보 키를 최대한 넓게 탐색
    """
    ur = body.get("userRequest") or {}
    candidates = [
        ("context.groupChat.id", deep_get(ur, ["context", "groupChat", "id"])),
        ("context.room.id",      deep_get(ur, ["context", "room", "id"])),
        ("context.chat.id",      deep_get(ur, ["chat", "id"])),
        ("context.conversationId", deep_get(ur, ["context", "conversationId"])),
        ("room.id",              deep_get(ur, ["room", "id"])),
    ]
    for _, v in candidates:
        if v:
            return str(v)

    user_id = deep_get(ur, ["user", "id"]) or "anon"
    return str(user_id)

def load_players():
    players = _all_players() or []
    out = []
    for p in players:
        p = dict(p)
        if not p.get("chosung"):
            p["chosung"] = _make_chosung(p.get("name_ko", ""))
        out.append(p)
    return out

def get_state(room_id: str):
    with PQ_LOCK:
        return PQ_STATE.get(room_id)

def clear_state(room_id: str):
    with PQ_LOCK:
        PQ_STATE.pop(room_id, None)

def remaining(st) -> int:
    elapsed = time.time() - float(st.get("started_at") or 0)
    return max(0, PQ_TIME_LIMIT - int(elapsed))

def pick_player(room_id: str):
    """
    ✅ 방 단위 98명(전체) 사이클 중복 방지:
    - PQ_CYCLE[room_id]에 누적
    - 전체 선수 수에 도달하면 그때 리셋
    """
    players = load_players()
    if not players:
        return None

    total = len(players)

    with PQ_LOCK:
        seen_ids = list(PQ_CYCLE.get(room_id) or [])
        if len(seen_ids) >= total:
            seen_ids = []

        seen_set = set(seen_ids)
        candidates = [p for p in players if p.get("id") not in seen_set]
        if not candidates:
            seen_ids = []
            candidates = players

        chosen = random.choice(candidates)
        seen_ids.append(chosen.get("id"))
        PQ_CYCLE[room_id] = seen_ids  # ✅ 사이클 기록은 유지

        PQ_STATE[room_id] = {
            "player": chosen,
            "started_at": time.time(),
            "hint_idx": 0,
        }

    return chosen

# def problem_text(player: dict, remain: int) -> str:
#     return (
#         "⚽ 축구 선수 초성 퀴즈!\n"
#         "초성을 보고 선수 이름을 맞춰보세요!\n\n"
#         f"초성은 [{player.get('chosung','')}] 입니다.\n"
#         f"⏱ 제한시간: {PQ_TIME_LIMIT}초\n\n"
#         "정답을 채팅에 입력하세요! (예: @축구봇 손흥민)\n"
#         "힌트가 필요하면 '@축구봇 힌트'라고 말해요!"
#     )

def problem_text(player: dict, remain: int) -> str:
    return (
        "⚽ 축구 선수 초성 퀴즈!\n"
        "초성을 보고 선수 이름을 맞춰보세요.\n\n"
        f"초성은 [{player.get('chosung','')}] 입니다.\n"
        f"⏱ 제한시간: {PQ_TIME_LIMIT}초\n\n"
        "✍️ 정답: 예) @축구봇 손흥민\n"
        "🧠 힌트: @축구봇 힌트\n"
        "🏳️ 포기: @축구봇 포기"
        # "🏆 순위: '순위보기'\n"
        # "※ 60초가 지나면 다음 입력에서 시간초과 처리돼요."
    )

def hint_text(player: dict, idx: int, remain: int) -> str:
    if idx == 1:
        return (
            "🧩 1번째 힌트\n"
            f"- 출생년도: {player.get('birth_year')}\n\n"
            f"(⏱ 남은 시간: {remain}초)"
        )
    if idx == 2:
        return (
            "🧩 2번째 힌트\n"
            f"- 국적: {player.get('nationality')}\n\n"
            f"(⏱ 남은 시간: {remain}초)"
        )
    if idx == 3:
        return (
            "🧩 3번째 힌트\n"
            f"- 포지션: {player.get('position')}\n\n"
            f"(⏱ 남은 시간: {remain}초)"
        )
    return (
        "🧩 4번째 힌트\n"
        f"- 소개: {player.get('one_liner')}\n\n"
        f"(⏱ 남은 시간: {remain}초)"
    )


def help_text() -> str:
    return jsonify({
        "version": "2.0",
        "template": {"outputs": [{"textCard": {
            "title": "🤔 잘 이해하지 못했어요. \n 아래 버튼을 눌러 사용법을 확인하세요.\n",
            "buttons": [{"label": "축구봇 사용법", "action": "webLink", "webLinkUrl": "https://pf.kakao.com/_xoxlZen/111143579"}]
        }}]}
    })

def _uid(body: dict) -> str:
    user = ((body.get("userRequest") or {}).get("user") or {})
    uid = (user.get("id") or "").strip()
    return uid or "unknown"

def _build_mentions(body: dict):
    uid = _uid(body)
    if not uid or uid == "unknown":
        return None
    return {MENTION_KEY: {"type": "botUserKey", "id": uid}}

def _with_mention_prefix(text: str, mentions):
    if mentions is None:
        return text
    return f"{MENTION_TOKEN} {text}"

# ----------------------------
# ✅ 랭킹: 점수 +1 / 순위 텍스트 생성
# ----------------------------
def pq_add_point(room_id: str, uid: str, delta: int = 1):
    if not uid or uid == "unknown":
        return
    with PQ_RANK_LOCK:
        room_map = PQ_RANK.get(room_id)
        if room_map is None:
            room_map = {}
            PQ_RANK[room_id] = room_map
        room_map[uid] = int(room_map.get(uid) or 0) + int(delta)

def pq_build_leaderboard(room_id: str, topn: int = 10):
    with PQ_RANK_LOCK:
        room_map = dict(PQ_RANK.get(room_id) or {})

    if not room_map:
        return ("🏆 초성퀴즈 순위\n\n아직 점수가 없어요! 정답을 맞히면 +1점 👍", None)

    items = sorted(room_map.items(), key=lambda x: (-x[1], x[0]))[:topn]

    mentions = {}
    lines = ["🏆 초성퀴즈 순위 (TOP {})".format(min(topn, len(items))), ""]
    for i, (uid, score) in enumerate(items, start=1):
        key = f"u{i}"
        mentions[key] = {"type": "botUserKey", "id": uid}
        token = f"{{{{#mentions.{key}}}}}"  # ✅ 반드시 이 형태!
        lines.append(f"{i}. {token} {score}점")

    lines.append("\n랭킹은 주기적으로 갱신됩니다.")  
    
    return ("\n".join(lines), mentions)

def _expired_response(room_id: str, mentions):
    st = get_state(room_id)
    if not st:
        return None
    player = st["player"]
    ans = player.get("name_ko")
    img_url = player.get("img_url", "")
    clear_state(room_id)
    msg = _with_mention_prefix(f"⏰ 시간 초과! 정답은 '{ans}' 입니다!", mentions)
    return pq_text_with_image_next(msg, img_url, ans, mentions)

def _playerquiz_handle(body: dict):
    room_id = get_room_id(body)

    utter_raw = extract_utterance(body)
    utter = pq_strip_mention(utter_raw)
    cmd = (utter or "").strip()
    cmd_n = pq_norm(cmd)

    mentions = _build_mentions(body)
    uid = _uid(body)

    st = get_state(room_id)
    rem = remaining(st) if st else None
    print(f"[PQ] room={room_id} utter_raw={utter_raw!r} cmd={cmd!r} pq={'Y' if st else 'N'} remain={rem}")

    start_cmds = {pq_norm(x) for x in ["초성퀴즈", "초성 퀴즈", "선수퀴즈", "선수 퀴즈", "퀴즈", "초성"]}
    rank_cmds  = {pq_norm(x) for x in ["순위보기", "랭킹보기", "랭킹", "순위", "순위 보기"]}

    # ✅ 순위보기: 진행중 아니어도 항상 가능
    if cmd_n in rank_cmds:
        text, m = pq_build_leaderboard(room_id, topn=10)
        return pq_text_with_buttons(text, m)

    # ✅ (4) 시간 초과면: 어떤 입력이든 즉시 시간초과 처리
    if st and remaining(st) <= 0:
        return _expired_response(room_id, mentions)

    # ✅ 시작: 진행 중이면 새 문제 뽑지 말고 현재 문제 공유(=공동 진행)
    if cmd_n in start_cmds:
        if st and remaining(st) > 0:
            player = st["player"]
            quick = [
                {"label": "힌트", "action": "message", "messageText": "힌트"},
                {"label": "포기", "action": "message", "messageText": "포기"},
                {"label": "순위보기", "action": "message", "messageText": "순위보기"},
            ]
            return pq_text_with_mention(problem_text(player, remaining(st)), None)

        player = pick_player(room_id)
        if not player:
            return pq_text("선수 DB가 비어있어요. player_info.py의 PLAYER_DB를 채워주세요!", None)

        st = get_state(room_id)
        quick = [
            {"label": "힌트", "action": "message", "messageText": "힌트"},
            {"label": "포기", "action": "message", "messageText": "포기"},
            {"label": "순위보기", "action": "message", "messageText": "순위보기"},
        ]
        return pq_text_with_mention(problem_text(player, remaining(st)), None)

    # 종료/포기/힌트
    if cmd in ["초성퀴즈 종료", "종료", "그만", "나가기"]:
        if st:
            clear_state(room_id)
            return pq_text("📣 초성퀴즈를 종료했어요! 다시 하려면 '@축구봇 초성퀴즈'라고 말해요.", None)
        return pq_text("'초성퀴즈'로 먼저 시작해 주세요!", None)

    if cmd in ["초성퀴즈 포기", "포기", "패스"]:
        if not st:
            return pq_text("'초성퀴즈'로 먼저 시작해 주세요!", None)

        player = st["player"]
        ans = player.get("name_ko")
        img_url = player.get("img_url", "")
        clear_state(room_id)

        msg = _with_mention_prefix(f"🏳️ 포기! 정답은 '{ans}' 입니다!", mentions)
        return pq_text_with_image_next(msg, img_url, ans, mentions)

    if cmd.lower() in ["힌트", "hint"]:
        if not st:
            return pq_text_with_buttons("먼저 '@축구봇 초성퀴즈'로 시작해 주세요!", None)

        player = st["player"]
        idx = int(st.get("hint_idx") or 0)
        if idx >= PQ_MAX_HINTS:
            return pq_text(_with_mention_prefix("힌트가 더 없어요. 정답을 입력하거나 '@축구봇 포기'라고 말해요!", mentions), mentions)

        idx += 1
        with PQ_LOCK:
            if room_id in PQ_STATE:
                PQ_STATE[room_id]["hint_idx"] = idx

        st2 = get_state(room_id)
        return pq_text(_with_mention_prefix(hint_text(player, idx, remaining(st2)), mentions), mentions)

    # 정답 시도
    if not st:
        return pq_text("'@축구봇 초성퀴즈'로 먼저 시작해 주세요!", None)

    guess_n = pq_norm(cmd)
    if not guess_n:
        return pq_text(_with_mention_prefix("정답을 입력하거나 '@축구봇 힌트'라고 말해요!", mentions), mentions)

    player = st["player"]
    answers = [player.get("name_ko", "")] + (player.get("aliases") or [])
    answers_n = {pq_norm(a) for a in answers if a}

    if guess_n in answers_n:
        ans = player.get("name_ko")
        img_url = player.get("img_url", "")
        clear_state(room_id)

        # ✅ 정답자 +1점 (방 단위 랭킹)
        pq_add_point(room_id, uid, 1)

        msg = _with_mention_prefix(f"🎉 정답! '{ans}' 입니다! (+1점)", mentions)
        return pq_text_with_image_next(msg, img_url, ans, mentions)

    msg = _with_mention_prefix(
        f"❌ 땡! 다시 시도해보세요.\n(⏱ 남은 시간: {remaining(st)}초)\n",
        mentions
    )
    return pq_text_with_hint(msg, mentions)

# ----------------------------
# (1) 초성퀴즈 전용 스킬
# ----------------------------
@app.route("/kakao/playerquiz", methods=["POST"])
def kakao_playerquiz():
    body = request.get_json(silent=True) or {}
    return _playerquiz_handle(body)

# ----------------------------
# (2) 폴백 라우터
# ----------------------------
@app.route("/kakao/fallback_router", methods=["POST"])
def kakao_fallback_router():
    body = request.get_json(silent=True) or {}
    room_id = get_room_id(body)

    st = get_state(room_id)
    rem = remaining(st) if st else None
    utter_raw = extract_utterance(body)
    cmd = pq_strip_mention(utter_raw)
    cmd_n = pq_norm(cmd)

    start_cmds = {pq_norm(x) for x in ["초성퀴즈", "초성 퀴즈", "선수퀴즈", "선수 퀴즈", "퀴즈", "초성"]}
    rank_cmds  = {pq_norm(x) for x in ["순위보기", "랭킹보기", "랭킹", "순위", "순위 보기"]}

    print(f"[FB] room={room_id} utter_raw={utter_raw!r} pq_active={'Y' if st else 'N'} remain={rem}")

    # ✅ 퀴즈 진행 중이면(시간 초과 포함) 무조건 위임
    if st:
        return _playerquiz_handle(body)

    # ✅ 퀴즈 비진행 중이어도: "초성퀴즈"/"순위보기"는 playerquiz로 위임
    if cmd_n in start_cmds or cmd_n in rank_cmds:
        return _playerquiz_handle(body)

    return help_text()



# 포트 설정 및 웹에 띄우기
# 초기화 실행 및 Flask 앱 실행
if __name__ == '__main__':
    init_db()  # 데이터베이스 및 테이블 생성
    app.run('0.0.0.0', port=3000, debug=True)
