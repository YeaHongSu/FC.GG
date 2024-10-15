import numpy as np

data_label = ['평균 파울 수', '평균 옐로우 카드 수', '평균 드리블 수', '평균 코너킥 수', '평균 오프사이드 수',
                  '평균 슛 수', '평균 유효 슛 수', '슈팅 수 대비 유효 슈팅 수', '슈팅 수 대비 골 수',
                  '평균 헤딩 슛 수', '평균 헤더 골 수', '헤더 골 성공률',  '헤더 골 비율',
                  '평균 프리킥 슛 수', '평균 프리킥 골 수', '프리킥 골 성공률', '프리킥 골 비율',
                  '평균 패널티 안쪽 슛 수', '평균 패널티 안쪽 골 수', '패널티 안쪽 골 성공률', '패널티 안쪽 골 비율',
                  '평균 패널티 바깥쪽 슛 수', '평균 패널티 바깥쪽 골 수', '패널티 바깥쪽 골 성공률', '패널티 바깥쪽 골 비율',
                  '평균 패스 시도', '평균 패스 성공', '평균 패스 성공률',
                  '평균 숏패스 시도 수', '평균 숏패스 성공 수', '평균 숏패스 성공률',
                  '평균 롱패스 시도 수', '평균 롱패스 성공 수', '평균 롱패스 성공률',
                  '평균 드라이브땅볼패스 시도 수', '평균 드라이브땅볼패스 성공 수', '평균 드라이브땅볼패스 성공률',
                  '평균 스루패스 시도 수', '평균 스루패스 성공 수', '평균 스루패스 성공률',
                  '평균 로빙스루패스 시도 수', '평균 로빙스루패스 성공 수', '평균 로빙스루패스 성공률',
                  '평균 차단 시도 수', '평균 차단 성공 수', '평균 차단 성공률',
                  '평균 태클 시도 수', '평균 태클 성공 수', '평균 태클 성공률']

def determine_play_style(max_data, min_data):
    # 각 플레이 스타일별 카운터
    attack_count = 0
    finisher_count = 0  # 마무리형 공격수
    dribbler_count = 0
    playmaker_count = 0
    setpiece_master_count = 0
    header_specialist_count = 0
    penalty_specialist_count = 0
    long_shot_master_count = 0
    defense_count = 0
    interceptor_count = 0  # 인터셉터 (차단 전문)
    tackler_count = 0  # 태클러
    card_collector_count = 0  # 옐로우 카드 수집가 카운터
    lob_pass_master_count = 0  # 로빙스루패스 마스터

    # 공격 지표
    attack_labels = ['평균 슛 수', '평균 유효 슛 수', '슈팅 수 대비 골 수', '평균 패널티 안쪽 골 수']
    
    # 마무리형 공격수 지표 (골을 넣는 데 집중)
    finisher_labels = ['슈팅 수 대비 골 수', '평균 헤더 골 수', '평균 프리킥 골 수', '평균 패널티 안쪽 골 수']
    
    # 방어 지표
    defense_labels = ['평균 차단 성공 수', '평균 태클 성공 수', '평균 차단 시도 수', '평균 태클 시도 수']
    
    # 인터셉터 (차단에 집중하는 플레이어)
    interceptor_labels = ['평균 차단 시도 수', '평균 차단 성공 수']
    
    # 태클러 (태클에 집중하는 플레이어)
    tackler_labels = ['평균 태클 시도 수', '평균 태클 성공 수']
    
    # 패스 지표 (플레이메이커)
    pass_labels = ['평균 패스 성공', '평균 숏패스 성공 수', '평균 롱패스 성공 수', '평균 스루패스 성공 수', '평균 로빙스루패스 성공 수']
    
    # 프리킥의 마술사
    setpiece_labels = ['평균 코너킥 수', '평균 프리킥 골 수', '프리킥 골 성공률', '프리킥 골 비율']
    
    # 헤더 전문 플레이어
    header_labels = ['평균 헤딩 슛 수', '평균 헤더 골 수', '헤더 골 성공률', '헤더 골 비율']
    
    # 패널티 전문가
    penalty_labels = ['평균 패널티 안쪽 슛 수', '평균 패널티 안쪽 골 수', '패널티 안쪽 골 성공률', '패널티 안쪽 골 비율']
    
    # 중거리 마스터 (패널티 바깥쪽 슛 및 골)
    long_shot_labels = ['평균 패널티 바깥쪽 슛 수', '평균 패널티 바깥쪽 골 수', '패널티 바깥쪽 골 성공률', '패널티 바깥쪽 골 비율']
    
    # 드리블 마스터
    dribble_labels = ['평균 드리블 수']
    
    # 로빙스루패스 마스터
    lob_pass_labels = ['평균 로빙스루패스 시도 수', '평균 로빙스루패스 성공 수', '평균 로빙스루패스 성공률']

    # 옐로우 카드 수집가
    card_labels = ['평균 옐로우 카드 수']

    # 상위 지표 분석
    for idx, value in max_data:
        if data_label[idx] in attack_labels:
            attack_count += 1
        elif data_label[idx] in finisher_labels:
            finisher_count += 1
        elif data_label[idx] in defense_labels:
            defense_count += 1
        elif data_label[idx] in interceptor_labels:
            interceptor_count += 1
        elif data_label[idx] in tackler_labels:
            tackler_count += 1
        elif data_label[idx] in pass_labels:
            playmaker_count += 1
        elif data_label[idx] in setpiece_labels:
            setpiece_master_count += 1
        elif data_label[idx] in header_labels:
            header_specialist_count += 1
        elif data_label[idx] in penalty_labels:
            penalty_specialist_count += 1
        elif data_label[idx] in long_shot_labels:
            long_shot_master_count += 1
        elif data_label[idx] in dribble_labels:
            dribbler_count += 1
        elif data_label[idx] in lob_pass_labels:
            lob_pass_master_count += 1
        elif data_label[idx] in card_labels:
            card_collector_count += 1

    # 세분화된 플레이 스타일 결정
    if card_collector_count >= 1:
        return "악질 카드 수집가"
    elif lob_pass_master_count >= 2:
        return "공이 공중에만 떠 있는 플레이어"  # 로빙스루패스 마스터
    elif finisher_count >= 2 and attack_count >= 1:
        return "공격적인 피니셔"  # 공격과 마무리를 동시에 잘하는 선수
    elif finisher_count >= 2 and header_specialist_count >= 2:
        return "헤더 마무리의 신"
    elif attack_count >= 2 and dribbler_count >= 1:
        return "공격형 드리블러"  # 공격 능력과 드리블 능력을 동시에 가진 플레이어
    elif defense_count >= 1 and tackler_count >= 2:
        return "방어적인 태클러"  # 방어와 태클을 동시에 잘하는 선수
    elif interceptor_count >= 2 and defense_count >= 2:
        return "완벽한 차단기"  # 방어형 플레이어이면서 차단에 특화된 선수
    elif playmaker_count >= 2 and dribbler_count >= 1:
        return "드리블형 플레이메이커"  # 드리블을 잘하는 패스 전문가
    elif playmaker_count >= 2 and long_shot_master_count >= 2:
        return "중거리형 플레이메이커"  # 중거리 슛에 강한 패스 전문가
    elif setpiece_master_count >= 2 and header_specialist_count >= 2:
        return "헤더와 프리킥 날먹의 신"
    elif penalty_specialist_count >= 2 and long_shot_master_count >= 2:
        return "다재다능 공격 플레이어"
    elif tackler_count >= 2:
        return "A 없으면 게임 못 하는 플레이어"  # 방어와 태클을 동시에 잘하는 선수
    elif defense_count >= 3:
        return "수비의 신"
    elif attack_count >= 3:
        return "공격의 신"
    elif playmaker_count >= 3:
        return "플레이메이커"
    elif setpiece_master_count >= 2:
        return "프리킥 딸깍의 신"
    elif header_specialist_count >= 2:
        return "헤더 날먹의 신"
    elif penalty_specialist_count >= 2:
        return "패널티박스에만 사는 플레이어"
    elif long_shot_master_count >= 2:
        return "중거리 딸각의 신"
    elif dribbler_count >= 1:
        return "드리블 마스터"
    else:
        return "굴리트급 육각형 플레이어"



# zero_division 문제 해결
def is_zero(a, b):
    if b == 0 or None:
        return np.nan
    else:
        return a/b

def data_list(data):
    match_data = []
    if data['matchDetail']['matchEndType'] == 2 or data['matchDetail']['dribble']==None:
        return None
    match_data.append(data['matchDetail']['foul'])
    match_data.append(data['matchDetail']['yellowCards'])
    match_data.append(data['matchDetail']['dribble'])
    match_data.append(data['matchDetail']['cornerKick'])
    match_data.append(data['matchDetail']['offsideCount'])
    match_data.append(data['shoot']['shootTotal'])
    match_data.append(data['shoot']['effectiveShootTotal'])
    match_data.append(is_zero(data['shoot']['effectiveShootTotal'],data['shoot']['shootTotal']))
    match_data.append(is_zero(data['shoot']['goalTotal'],data['shoot']['shootTotal']))
    match_data.append(data['shoot']['shootHeading'])
    match_data.append(data['shoot']['goalHeading'])
    match_data.append(is_zero(data['shoot']['goalHeading'],data['shoot']['shootHeading']))
    match_data.append(is_zero(data['shoot']['goalHeading'],data['shoot']['goalTotal']))
    match_data.append(data['shoot']['shootFreekick'])
    match_data.append(data['shoot']['goalFreekick'])
    match_data.append(is_zero(data['shoot']['goalFreekick'],data['shoot']['shootFreekick']))
    match_data.append(is_zero(data['shoot']['goalFreekick'],data['shoot']['goalTotal']))
    match_data.append(data['shoot']['shootInPenalty'])
    match_data.append(data['shoot']['goalInPenalty'])
    match_data.append(is_zero(data['shoot']['goalInPenalty'],data['shoot']['shootInPenalty']))
    match_data.append(is_zero(data['shoot']['goalInPenalty'],data['shoot']['goalTotal']))
    match_data.append(data['shoot']['shootOutPenalty'])
    match_data.append(data['shoot']['goalOutPenalty'])
    match_data.append(is_zero(data['shoot']['goalOutPenalty'],data['shoot']['shootOutPenalty']))
    match_data.append(is_zero(data['shoot']['goalOutPenalty'],data['shoot']['goalTotal']))
    match_data.append(data['pass']['passTry'])
    match_data.append(data['pass']['passSuccess'])
    match_data.append(is_zero(data['pass']['passSuccess'],data['pass']['passTry']))
    match_data.append(data['pass']['shortPassTry'])
    match_data.append(data['pass']['shortPassSuccess'])
    match_data.append(is_zero(data['pass']['shortPassSuccess'],data['pass']['shortPassTry']))
    match_data.append(data['pass']['longPassTry'])
    match_data.append(data['pass']['longPassSuccess'])
    match_data.append(is_zero(data['pass']['longPassSuccess'],data['pass']['longPassTry']))
    match_data.append(data['pass']['drivenGroundPassTry'])
    match_data.append(data['pass']['drivenGroundPassSuccess'])
    match_data.append(is_zero(data['pass']['drivenGroundPassSuccess'],data['pass']['drivenGroundPassTry']))
    match_data.append(data['pass']['throughPassTry'])
    match_data.append(data['pass']['throughPassSuccess'])
    match_data.append(is_zero(data['pass']['throughPassSuccess'],data['pass']['throughPassTry']))
    match_data.append(data['pass']['lobbedThroughPassTry'])
    match_data.append(data['pass']['lobbedThroughPassSuccess'])
    match_data.append(is_zero(data['pass']['lobbedThroughPassSuccess'],data['pass'][ 'lobbedThroughPassTry']))
    match_data.append(data['defence']['blockTry'])
    match_data.append(data['defence']['blockSuccess'])
    match_data.append(is_zero(data['defence']['blockSuccess'],data['defence']['blockTry']))
    match_data.append(data['defence']['tackleTry'])
    match_data.append(data['defence']['tackleSuccess'])
    match_data.append(is_zero(data['defence']['tackleSuccess'],data['defence']['tackleTry']))
    return match_data

# 크롤링 데이터에서 필요 요소만 뽑는 함수
def data_list_cl(data):
    cl_data = []
    cl_data.append(data.loc["avgfoul"])
    cl_data.append(data.loc["avgycards"])
    cl_data.append(data.loc["avgdribble"])
    cl_data.append(data.loc["avgcornerkick"])
    cl_data.append(data.loc["avgoffsidecnt"])                              
    cl_data.append(data.loc["avgshoottot"])           
    cl_data.append(data.loc["avgeffshoottot"])                
    cl_data.append(data.loc["avgeffshoottot"]/data.loc["avgshoottot"])
    cl_data.append(data.loc["avggoaltot"]/data.loc["avgshoottot"])
    cl_data.append(data.loc["avgshootheading"])
    cl_data.append(data.loc["avggoalheading"])
    cl_data.append(data.loc["avggoalheading"]/data.loc["avgshootheading"])
    cl_data.append(data.loc["goalheadingratio"]/100)
    cl_data.append(data.loc["avgshootfreekick"])
    cl_data.append(data.loc["avggoalfreekick"])
    cl_data.append(data.loc["avggoalfreekick"]/data.loc["avgshootfreekick"])
    cl_data.append(data.loc["avggoalfreekick"]/data.loc["avggoaltot"])
    cl_data.append(data.loc["avgshootinpenalty"])
    cl_data.append(data.loc["avggoalinpenalty"])
    cl_data.append(data.loc["avggoalinpenalty"]/data.loc["avgshootinpenalty"])
    cl_data.append(data.loc["avggoalinpenalty"]/data.loc["avggoaltot"])
    cl_data.append(data.loc["avgshootoutpenalty"])
    cl_data.append(data.loc["avggoaloutpenalty"])
    cl_data.append(data.loc["avggoaloutpenalty"]/data.loc["avgshootoutpenalty"])
    cl_data.append(data.loc["avggoaloutpenalty"]/data.loc["avggoaltot"])
    cl_data.append(data.loc["avgpasstry"])
    cl_data.append(data.loc["avgpasssuccess"])
    cl_data.append(data.loc["passsuccessratio"]/100)
    cl_data.append(data.loc["avgshortpasstry"])
    cl_data.append(data.loc["avgshortpasssuccess"])
    cl_data.append(data.loc["avgshortpasssuccess"]/data.loc["avgshortpasstry"])
    cl_data.append(data.loc["avglobpasstry"])
    cl_data.append(data.loc["avglobpasssuccess"])
    cl_data.append(data.loc["avglobpasssuccess"]/data.loc["avglobpasstry"])
    cl_data.append(data.loc["avgdrivengroundpasstry"])
    cl_data.append(data.loc["avgdrivengroundpasssuccess"])
    cl_data.append(data.loc["avgdrivengroundpasssuccess"]/data.loc["avgdrivengroundpasstry"])
    cl_data.append(data.loc["avgthroughpasstry"])
    cl_data.append(data.loc["avgthroughpasssuccess"])
    cl_data.append(data.loc["avgthroughpasssuccess"]/data.loc["avgthroughpasstry"])
    cl_data.append(data.loc["avglobbedthroughpasstry"])
    cl_data.append(data.loc["avglobbedthroughpasssuccess"])
    cl_data.append(data.loc["avglobbedthroughpasssuccess"]/data.loc["avglobbedthroughpasstry"])
    cl_data.append(data.loc["avgblocktry"])
    cl_data.append(data.loc["avgblocksuccess"])
    cl_data.append(data.loc["avgblocksuccess"]/data.loc["avgblocktry"])
    cl_data.append(data.loc["avgtackletry"])
    cl_data.append(data.loc["avgtacklesuccess"])
    cl_data.append(data.loc["avgtacklesuccess"]/data.loc["avgtackletry"])
    
    return cl_data
