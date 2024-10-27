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
    # 각 플레이 스타일별 카운터 초기화
    counters = {
        'attack': 0,
        'finisher': 0,
        'dribbler': 0,
        'playmaker': 0,
        'setpiece_master': 0,
        'header_specialist': 0,
        'penalty_specialist': 0,
        'long_shot_master': 0,
        'defense': 0,
        'interceptor': 0,
        'tackler': 0,
        'card_collector': 0,
        'lob_pass_master': 0,
        'drive_pass_master': 0,
        'offside': 0
    }

    # 각 data_label을 플레이 스타일 카운터와 매핑
    label_to_counter = {
        '평균 슛 수': 'attack', '평균 유효 슛 수': 'attack', '슈팅 수 대비 골 수': 'attack',
        '평균 패널티 안쪽 골 수': 'attack', '슈팅 수 대비 골 수': 'finisher', '평균 헤더 골 수': 'finisher',
        '평균 프리킥 골 수': 'finisher', '평균 패널티 안쪽 골 수': 'finisher', '평균 차단 성공 수': 'defense',
        '평균 태클 성공 수': 'defense', '평균 차단 시도 수': 'defense', '평균 태클 시도 수': 'defense',
        '평균 차단 시도 수': 'interceptor', '평균 차단 성공 수': 'interceptor', '평균 태클 시도 수': 'tackler',
        '평균 태클 성공 수': 'tackler', '평균 패스 성공': 'playmaker', '평균 숏패스 성공 수': 'playmaker',
        '평균 롱패스 성공 수': 'playmaker', '평균 스루패스 성공 수': 'playmaker',
        '평균 로빙스루패스 성공 수': 'playmaker', '평균 코너킥 수': 'setpiece_master',
        '평균 프리킥 골 수': 'setpiece_master', '프리킥 골 성공률': 'setpiece_master',
        '프리킥 골 비율': 'setpiece_master', '평균 헤딩 슛 수': 'header_specialist',
        '평균 헤더 골 수': 'header_specialist', '헤더 골 성공률': 'header_specialist',
        '헤더 골 비율': 'header_specialist', '평균 패널티 안쪽 슛 수': 'penalty_specialist',
        '평균 패널티 안쪽 골 수': 'penalty_specialist', '패널티 안쪽 골 성공률': 'penalty_specialist',
        '패널티 안쪽 골 비율': 'penalty_specialist', '평균 패널티 바깥쪽 슛 수': 'long_shot_master',
        '평균 패널티 바깥쪽 골 수': 'long_shot_master', '패널티 바깥쪽 골 성공률': 'long_shot_master',
        '패널티 바깥쪽 골 비율': 'long_shot_master', '평균 드리블 수': 'dribbler',
        '평균 로빙스루패스 시도 수': 'lob_pass_master', '평균 로빙스루패스 성공 수': 'lob_pass_master',
        '평균 로빙스루패스 성공률': 'lob_pass_master', '평균 드라이브땅볼패스 시도 수': 'drive_pass_master',
        '평균 드라이브땅볼패스 성공 수': 'drive_pass_master', '평균 드라이브땅볼패스 성공률': 'drive_pass_master',
        '평균 옐로우 카드 수': 'card_collector', '평균 오프사이드 수': 'offside'
    }

    # 상위 지표 분석
    for idx, value in max_data:
        label = data_label[idx]
        if label in label_to_counter:
            counters[label_to_counter[label]] += 1

    # 세분화된 플레이 스타일 결정
    if counters['drive_pass_master'] >= 2:
        return "잔디와 한 몸인 땅볼 패스 마스터"
    elif counters['offside'] >= 1:
        return "옵사를 사랑하는 플레이어"
    elif counters['lob_pass_master'] >= 2:
        return "공이 공중에만 있는 플레이어"
    elif counters['finisher'] >= 1 and counters['attack'] >= 1:
        return "공격적인 피니셔"
    elif counters['finisher'] >= 1 and counters['header_specialist'] >= 1:
        return "헤더 마무리의 신"
    elif counters['attack'] >= 1 and counters['dribbler'] >= 1:
        return "공격형 드리블러"
    elif counters['defense'] >= 1 and counters['tackler'] >= 1:
        return "방어적인 태클러"
    elif counters['interceptor'] >= 1 and counters['defense'] >= 1:
        return "완벽한 차단기"
    elif counters['playmaker'] >= 1 and counters['dribbler'] >= 1:
        return "드리블형 플레이메이커"
    elif counters['playmaker'] >= 1 and counters['long_shot_master'] >= 1:
        return "중거리형 플레이메이커"
    elif counters['setpiece_master'] >= 1 and counters['header_specialist'] >= 1:
        return "헤더와 프리킥 날먹의 신"
    elif counters['penalty_specialist'] >= 1 and counters['long_shot_master'] >= 1:
        return "다재다능 공격 플레이어"
    elif counters['tackler'] >= 2:
        return "태클키 없으면 게임 못 하는 플레이어"
    elif counters['defense'] >= 2:
        return "수비의 신"
    elif counters['attack'] >= 2:
        return "공격의 신"
    elif counters['playmaker'] >= 2:
        return "플레이메이커"
    elif counters['header_specialist'] >= 2:
        return "헤더 날먹의 신"
    elif counters['penalty_specialist'] >= 2:
        return "패널티박스에만 사는 플레이어"
    elif counters['long_shot_master'] >= 2:
        return "중거리 딸깍의 신"
    elif counters['dribbler'] >= 1:
        return "드리블 마스터"
    elif counters['card_collector'] >= 1:
        return "악질 카드 수집가"
    elif counters['setpiece_master'] >= 2:
        return "프리킥 딸깍의 신"
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
