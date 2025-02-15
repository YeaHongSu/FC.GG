# Import necessary modules
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By  
import time
import numpy as np
from sklearn.cluster import KMeans
from collections import Counter 
from meta_score import get_meta_score
from dt_info import XPATHS, pos_threshold, column_mapping, cr_info

# position 정보
positions = ["ST","CF", "LW", "RW", "CAM", "CM", "CDM", "CB", "LB", "RB", "GK"]

# position 별 상위 100명 선수 정보 크롤링
def pos_info(position):
    # 옵션 설정
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    # 드라이버 설정 (Chrome 드라이버 경로 지정 필요)
    driver = webdriver.Chrome(options=options)

    # 페이지 열기
    driver.get("https://fconline.nexon.com/datacenter/PlayerStat")

    # 페이지 로드 대기
    time.sleep(3)  

    # XPath를 이용하여 버튼 클릭하기
    pos_path = XPATHS[position]
    button = driver.find_element(By.XPATH, pos_path)
    driver.execute_script("arguments[0].click();", button)

    time.sleep(1)

    button2 = driver.find_element(By.XPATH, '//*[@id="form1"]/div[2]/div[2]/a')
    driver.execute_script("arguments[0].click();", button2)

    # 버튼 클릭 후 페이지 로드 대기 
    time.sleep(3)  

    # 페이지 소스 가져오기
    html = driver.page_source

    # BeautifulSoup으로 파싱
    soup = BeautifulSoup(html, 'html.parser')

    # 각 선수의 데이터를 저장할 리스트
    player_data = []
    players = soup.find_all('div', class_='tr')
    # # 수정 전
    # html = cr_info[position]
    
    # # BeautifulSoup 객체로 변환합니다
    # soup = BeautifulSoup(html, 'html.parser')
    # # 각 선수의 데이터를 저장할 리스트
    # player_data = []
    # players = soup.find_all('div', class_='tr')
    
    # 첫 100명만 크롤링하도록 수정
    for i, player in enumerate(players[:100]):
        name_tag = player.find('div', class_='name')
        
        # 선수 이름이 있으면 처리 시작
        if name_tag:
            player_name = name_tag.get_text(strip=True)
            
            # 각 통계 항목을 저장할 딕셔너리
            stats = {'선수 이름': player_name}
            
            # 시즌 정보 추출 (img 태그의 src 속성에서 가져오기)
            season_tag = player.find('div', class_='season').find('img')
            if season_tag:
                season_src = season_tag['src']
                # season_code = season_src.split('/')[-1].split('.')[0]  # '/LN.png'에서 'LN' 추출
                # stats['시즌'] = season_code
                stats['시즌'] = season_src
            
            # 선수 이미지 URL 추출
            thumb_tag = player.find('div', class_='thumb').find('img')
            if thumb_tag:
                image_url = thumb_tag['src']
                stats['미니페이스온'] = image_url
            
            # 각 통계 데이터를 해당 클래스에서 추출
            for column, class_name in column_mapping.items():
                stat_tag = player.find('div', class_=f'td {class_name}')
                if stat_tag:
                    stat_value = stat_tag.get_text(strip=True)
                    stats[column] = stat_value
                else:
                    stats[column] = 'N/A'  # 데이터가 없는 경우
            
            # 한 선수의 데이터를 추가
            player_data.append(stats)

    # 드라이버 종료
    driver.quit()

    return player_data


def scale_value(value, min_value=0, max_value=100):
    return (value - min_value) / (max_value - min_value)

def clean_numeric_value(value):
    return float(value.replace(',', ''))

def tier_gen(position):
    # 포지션 별 정보 및 threshold 저장
    player_data = pos_info(position)
    threshold = pos_threshold[position]

    # 각 선수의 FC스코어 계산하고 저장
    for player in player_data:
        meta_score = get_meta_score(player, position)
        appearances = clean_numeric_value(player['출전'])  # 출전수에서 쉼표 제거 후 변환
        appearances_scaled = scale_value(appearances)  # 출전수 스케일링
        fc_score = (2.5 * meta_score) + (1 * appearances_scaled)  # FC스코어 계산
        player['FC스코어'] = fc_score

    # FC스코어가 높은 순서대로 정렬
    sorted_players = sorted(player_data, key=lambda x: x['FC스코어'], reverse=True)


    # threshold 이상인 선수들을 "OP티어"로 지정
    op_players = [player for player in player_data if player['FC스코어'] >= threshold]

    # threshold 미만인 선수들을 필터링
    filtered_players = [player for player in player_data if player['FC스코어'] < threshold]

    # 해당 선수들의 FC스코어 추출
    filtered_fc_scores = np.array([player['FC스코어'] for player in filtered_players]).reshape(-1, 1)

    # K-means 클러스터링 적용 (5개의 클러스터로 분류)
    kmeans = KMeans(n_clusters=5, random_state=0)
    kmeans.fit(filtered_fc_scores)

    # 클러스터 라벨을 각 선수 데이터에 추가
    for i, player in enumerate(filtered_players):
        player['티어'] = kmeans.labels_[i]  # 0~3 클러스터 번호를 저장

    # 각 클러스터별 FC스코어 평균을 계산
    cluster_avg_scores = {}
    for i in range(5):
        cluster_scores = [player['FC스코어'] for player in filtered_players if player['티어'] == i]
        cluster_avg_scores[i] = np.mean(cluster_scores)

    # 클러스터 평균 FC스코어를 기준으로 클러스터 번호를 재배정 (높은 점수일수록 1티어)
    sorted_clusters = sorted(cluster_avg_scores, key=cluster_avg_scores.get, reverse=True)

    # 티어 재배정 (FC스코어 높은 클러스터가 1티어, 낮은 클러스터가 4티어)
    cluster_to_tier = {cluster: tier + 1 for tier, cluster in enumerate(sorted_clusters)}

    for player in filtered_players:
        player['티어'] = cluster_to_tier[player['티어']]

    # 선수들을 티어별로 분류
    tier_1 = [player for player in filtered_players if player['티어'] == 1]
    tier_2 = [player for player in filtered_players if player['티어'] == 2]
    tier_3 = [player for player in filtered_players if player['티어'] == 3]
    tier_4 = [player for player in filtered_players if player['티어'] == 4]
    tier_5 = [player for player in filtered_players if player['티어'] == 5]

    # 티어별 선수 정보 출력 (미니페이스온 포함) - 순서를 '시즌', '미니페이스온', '선수 이름', 'FC스코어', '출전'으로 변경
    # FC스코어 소수점 둘째 자리까지만 표시
    tier_texts = {
        "0티어": [{"시즌": player["시즌"], "미니페이스온": player["미니페이스온"], "선수 이름": player["선수 이름"], "FC스코어": round(player["FC스코어"], 2), "출전": player["출전"]} for player in op_players],
        "1티어": [{"시즌": player["시즌"], "미니페이스온": player["미니페이스온"], "선수 이름": player["선수 이름"], "FC스코어": round(player["FC스코어"], 2), "출전": player["출전"]} for player in tier_1],
        "2티어": [{"시즌": player["시즌"], "미니페이스온": player["미니페이스온"], "선수 이름": player["선수 이름"], "FC스코어": round(player["FC스코어"], 2), "출전": player["출전"]} for player in tier_2],
        "3티어": [{"시즌": player["시즌"], "미니페이스온": player["미니페이스온"], "선수 이름": player["선수 이름"], "FC스코어": round(player["FC스코어"], 2), "출전": player["출전"]} for player in tier_3],
        "4티어": [{"시즌": player["시즌"], "미니페이스온": player["미니페이스온"], "선수 이름": player["선수 이름"], "FC스코어": round(player["FC스코어"], 2), "출전": player["출전"]} for player in tier_4],
        "5티어": [{"시즌": player["시즌"], "미니페이스온": player["미니페이스온"], "선수 이름": player["선수 이름"], "FC스코어": round(player["FC스코어"], 2), "출전": player["출전"]} for player in tier_5]
    }

    # 각 티어 내에서 FC스코어 높은 순으로 정렬하여 출력
    for tier in tier_texts.keys():
        tier_texts[tier] = sorted(tier_texts[tier], key=lambda x: x["FC스코어"], reverse=True)

    return tier_texts

def tier():
    tier_list = {}
    for position in positions:
        tier_info = tier_gen(position)
        tier_list[position] = tier_info
    return tier_list

filename = './tier/tier_info.py'
TIER_DATA = tier()

# Open the file in write mode
with open(filename, 'w') as file:
    # Write the dictionary as a variable
    file.write(f"tier = {TIER_DATA}\n")
