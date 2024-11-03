from flask import Flask, render_template, request, redirect, url_for, session
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
      session['character_name'] = character_name
      match_type = request.form.get('match_type')
      session['match_type'] = match_type
      return redirect(url_for('result'))
   return render_template('home.html')

# 전적 검색 페이지
@app.route('/result.html', methods=['GET', 'POST'])
def result():
    try:
        # 유저 닉네임 받기
        character_name = request.args.get('character_name')
        if not character_name:
            flash("닉네임이 존재하지 않아 검색이 불가능합니다.")
            return render_template('home.html')

        # 닉네임에서 띄어쓰기 제거
        character_name = character_name.replace(" ", "")
       
        # match 종류 확인
        match_type = request.args.get('match_type')
       
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

        level_data = {
            "nickname": character_name,
            "level": lv,
            "tier_name": tier_name,
            "tier_image": tier_image
        }


        # 유저 매치 데이터 20개 불러와 저장 (전적 띄우기 용 + 중요 정보 저장)
        urlString = "https://open.api.nexon.com/fconline/v1/user/match?ouid=" + characterName + "&matchtype="+match_type+"&limit=20"
        response = requests.get(urlString, headers=headers)
        matches = response.json()

        if len(matches) == 0:
            return render_template('result.html', level_data=level_data, no_recent_matches=True)

        match_data_list = get_match_data(matches, headers)

        result_list = []
        imp_data = []

        # 각 매치 데이터 처리
        for data in match_data_list:
            date = calculate_time_difference(data['matchDate'])
            my_data = me(data, character_name)
            your_data = you(data, character_name)
            imp = data_list(my_data)
            imp2 = data_list(your_data)
            if imp == None or imp2 == None:
               continue
            w_l = my_data['matchDetail']['matchResult']

            # 비정상 게임 3:0으로 처리
            my_goal_total = my_data['shoot']['goalTotal'] if my_data['shoot']['goalTotal'] is not None else 0
            your_goal_total = your_data['shoot']['goalTotal'] if your_data['shoot']['goalTotal'] is not None else 0

            match_data = {
                '매치 날짜': date,
                '결과': w_l,
                '플레이어 1 vs 플레이어 2': f'{my_data["nickname"]} vs {your_data["nickname"]}',
                '스코어': f'{my_goal_total}:{your_goal_total}'
            }
            # 전적 표시용
            result_list.append(match_data)
            # 중요 정보 저장용
            imp_data.append(imp)

        # 중요 지표 평균 계산
        my_avg = np.nanmean(imp_data, axis=0)

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
                            play_style=play_style)

    except Exception as e:
        print(e)
        flash("닉네임이 존재하지 않거나 경기 수가 부족하여 검색이 불가능합니다.")
        return render_template('home.html')



# 승률 개선 솔루션 페이지
@app.route('/wr_imp.html', methods=['GET', 'POST'])
def wr_imp():
    return render_template('wr_imp.html')

@app.route('/wr_result.html', methods=['GET'])
def wr_result():
    try:
        character_name = request.args.get('character_name') or session.get('character_name')
        if not character_name:
            flash("닉네임이 존재하지 않아 검색이 불가능합니다.")
            return redirect(url_for('home'))

        # 닉네임에서 띄어쓰기 제거
        character_name = character_name.replace(" ", "")

        # match 종류 확인
        match_type = request.args.get('match_type')
       
        headers = {"x-nxopen-api-key": f"{app.config['API_KEY']}"}
        urlString = "https://open.api.nexon.com/fconline/v1/id?nickname=" + character_name
        characterName = requests.get(urlString, headers=headers).json()["ouid"]

        urlString = "https://open.api.nexon.com/fconline/v1/user/basic?ouid=" + characterName
        lv = requests.get(urlString, headers=headers).json()["level"]

        level_data = {
            "nickname": character_name,
            "level": lv
        }

        urlString = "https://open.api.nexon.com/fconline/v1/user/match?ouid=" + characterName + "&matchtype=" + match_type + "&limit=20"
        response = requests.get(urlString, headers=headers)
        matches = response.json()

        if len(matches) <= 5:
            flash("경기 수가 부족하여 검색이 불가능합니다 (최소 5경기가 필요합니다)")
            return redirect(url_for('home'))
           
        match_data_list = get_match_data(matches, headers)
        
        result_list = []
        imp_data = []
        w_l_data = []

        # for i in matches:
        #     urlString = "https://open.api.nexon.com/fconline/v1/match-detail?matchid=" + i
        #     response = requests.get(urlString, headers=headers)
        #     data = response.json()
        for data in match_data_list:
            my_data = me(data, character_name)
            imp = data_list(my_data)
            imp2 = data_list(you(data, character_name))
            if imp == None or imp2 == None:
                continue
               
            w_l = my_data['matchDetail']['matchResult']
            match_data = {
                '결과': w_l
            }
            result_list.append(match_data)
            imp_data.append(imp)
            w_l_data.append(w_l)

        my_avg = np.nanmean(imp_data, axis=0)
        cl_data = np.array(data_list_cl(avg_data(match_type)))

        jp_num = 20
        threshold = 0.9

        max_diff = (my_avg - cl_data) / cl_data
        max_idx, max_values = top_n_argmax(max_diff, jp_num)
        # 상위 5개만 남기기
        filtered_max_idx = max_idx[:5]
        filtered_max_values = max_values[:5]

        min_diff = (my_avg - cl_data) / cl_data
        min_idx, min_values = top_n_argmin(min_diff, jp_num)

        filtered_min_idx = [idx for idx, value in zip(min_idx, min_values) if abs(value) < threshold][:5]
        filtered_min_values = [value for value in min_values if abs(value) < threshold][:5]

        max_data = zip(filtered_max_idx, filtered_max_values)
        min_data = zip(filtered_min_idx, filtered_min_values)

        top_n, increase_ratio, improved_features_text, original_win_rate, modified_win_rate, win_rate_improvement = calculate_win_improvement(imp_data, w_l_data, data_label)

        return render_template('wr_result.html', my_data=my_data, match_data=result_list, level_data=level_data, 
                               max_data=max_data, min_data=min_data, data_label=data_label, jp_num=jp_num,
                               top_n=top_n, increase_ratio=increase_ratio, improved_features_text=improved_features_text, 
                               original_win_rate=original_win_rate, modified_win_rate=modified_win_rate, win_rate_improvement=win_rate_improvement)

    except Exception as e:
        print(e)
        flash("닉네임이 존재하지 않거나 경기 수가 부족하여 검색이 불가능합니다.")
        return redirect(url_for('home'))

# 선수 티어 페이지
@app.route('/player_tier.html', methods=['GET', 'POST'])
def player_tier():
    tier_list = tier
    return render_template('player_tier.html', tier_forward_list=tier_list)

# 빠칭코 페이지
@app.route('/random.html', methods=['GET', 'POST'])
def random():
    return render_template('random.html')

# 수수료 계산기 페이지
@app.route('/calculate.html', methods=['GET', 'POST'])
def calculate():
    return render_template('calculate.html')


# 포트 설정 및 웹에 띄우기
if __name__ == '__main__':  
   app.run('0.0.0.0',port=3000,debug=True)
