import numpy as np
import matplotlib.pyplot as plt
#from tier_gen import pos_info, clean_numeric_value, scale_value
from dt_info import XPATHS, column_mapping
from meta_score import get_meta_score
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By  
import time

# 한글 폰트 설정 (시스템에 설치된 폰트를 지정해야 함)
#plt.rcParams['font.family'] = 'AppleGothic'  # Mac의 경우
plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows의 경우
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

#"CF", "LW", "RW", "CAM", "CM", "CDM", "CB", "LB", "RB", "GK"
position = "ST"

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
                season_code = season_src.split('/')[-1].split('.')[0]  # '/LN.png'에서 'LN' 추출
                stats['시즌'] = season_code
            
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

player_data = pos_info(position)

for player in player_data:
    meta_score = get_meta_score(player, position)
    appearances = clean_numeric_value(player['출전'])  # 출전수에서 쉼표 제거 후 변환
    appearances_scaled = scale_value(appearances)  # 출전수 스케일링
    fc_score = (2.5 * meta_score) + (1 * appearances_scaled)  # FC스코어 계산
    player['FC스코어'] = fc_score

fc_scores = np.array([player['FC스코어'] for player in player_data])

# FC스코어 분포를 히스토그램으로 시각화
plt.figure(figsize=(10, 6))
plt.hist(fc_scores, bins=10, color='skyblue', edgecolor='black')
plt.title('FC스코어 분포 (100명의 선수)', fontsize=15)
plt.xlabel('FC스코어', fontsize=12)
plt.ylabel('선수 수', fontsize=12)
plt.grid(True)
plt.show()