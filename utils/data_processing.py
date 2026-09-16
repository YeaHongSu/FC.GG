import hashlib
import math
import numpy as np
from collections import defaultdict, Counter

data_label = ['평균 파울 수', '평균 옐로우 카드 수', '평균 드리블 수', '평균 코너킥 수', '평균 오프사이드 수',
              '평균 슛 수', '평균 유효 슛 수', '슈팅 수 대비 유효 슈팅 수', '슈팅 수 대비 골 수',
              '평균 헤딩 슛 수', '평균 헤더 골 수', '헤더 골 성공률', '헤더 골 비율',
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
    counters = {
        'attack': 0, 'finisher': 0, 'dribbler': 0, 'playmaker': 0,
        'setpiece_master': 0, 'corner_master': 0, 'header_specialist': 0,
        'penalty_specialist': 0, 'long_shot_master': 0, 'defense': 0,
        'interceptor': 0, 'tackler': 0, 'card_collector': 0,
        'lob_pass_master': 0, 'drive_pass_master': 0, 'offside': 0,
        'short_pass_master': 0, 'long_pass_master': 0
    }

    label_to_counter = {
        '평균 슛 수': 'attack', '평균 유효 슛 수': 'attack', '슈팅 수 대비 골 수': 'attack',
        '평균 패널티 안쪽 골 수': 'attack', '평균 헤더 골 수': 'finisher', '평균 프리킥 골 수': 'finisher',
        '평균 패널티 안쪽 골 수': 'finisher', '평균 차단 성공 수': 'defense', '평균 태클 성공 수': 'defense',
        '평균 차단 시도 수': 'defense', '평균 태클 시도 수': 'defense', '평균 차단 시도 수': 'interceptor',
        '평균 차단 성공 수': 'interceptor', '평균 태클 시도 수': 'tackler', '평균 태클 성공 수': 'tackler',
        '평균 패스 성공': 'playmaker', '평균 숏패스 성공 수': 'playmaker', '평균 롱패스 성공 수': 'playmaker',
        '평균 스루패스 성공 수': 'playmaker', '평균 로빙스루패스 성공 수': 'playmaker',
        '평균 코너킥 수': 'corner_master', '평균 프리킥 골 수': 'setpiece_master',
        '프리킥 골 성공률': 'setpiece_master', '프리킥 골 비율': 'setpiece_master',
        '평균 헤딩 슛 수': 'header_specialist', '평균 헤더 골 수': 'header_specialist',
        '헤더 골 성공률': 'header_specialist', '헤더 골 비율': 'header_specialist',
        '평균 패널티 안쪽 슛 수': 'penalty_specialist', '패널티 안쪽 골 성공률': 'penalty_specialist',
        '패널티 안쪽 골 비율': 'penalty_specialist', '평균 패널티 바깥쪽 슛 수': 'long_shot_master',
        '평균 패널티 바깥쪽 골 수': 'long_shot_master', '패널티 바깥쪽 골 성공률': 'long_shot_master',
        '패널티 바깥쪽 골 비율': 'long_shot_master', '평균 드리블 수': 'dribbler',
        '평균 로빙스루패스 시도 수': 'lob_pass_master', '평균 로빙스루패스 성공 수': 'lob_pass_master',
        '평균 로빙스루패스 성공률': 'lob_pass_master', '평균 드라이브땅볼패스 시도 수': 'drive_pass_master',
        '평균 드라이브땅볼패스 성공 수': 'drive_pass_master', '평균 드라이브땅볼패스 성공률': 'drive_pass_master',
        '평균 옐로우 카드 수': 'card_collector', '평균 오프사이드 수': 'offside',
        '평균 숏패스 성공 수': 'short_pass_master', '평균 숏패스 성공률': 'short_pass_master',
        '평균 롱패스 성공 수': 'long_pass_master', '평균 롱패스 성공률': 'long_pass_master'
    }

    for idx, value in max_data:
        label = data_label[idx]
        if label in label_to_counter:
            counters[label_to_counter[label]] += 1

    # 🎯 새롭게 추가된 플레이스타일
    if counters['short_pass_master'] >= 2:
        return "미친 짧패의 달인"
    elif counters['long_pass_master'] >= 2:
        return "하늘 가르는 롱패 장인"
    elif counters['corner_master'] >= 1 and counters['lob_pass_master'] >= 2:
        return "무조건 크로스하는 플레이어"
    elif counters['tackler'] >= 2 and counters['card_collector'] >= 1:
        return "태클이 아니라 격투"
    elif counters['short_pass_master'] >= 1 and counters['playmaker'] >= 1 and counters['dribbler'] >= 1:
        return "창조축구의 마에스트로"

    # 기존 플레이스타일 유지
    elif counters['offside'] >= 1:
        return "옵사를 사랑하는 플레이어"
    elif counters['corner_master'] >= 1 and counters['header_specialist'] >= 1:
        return "코너킥 딸깍의 신"
    elif counters['finisher'] >= 1 and counters['attack'] >= 1:
        return "골 냄새 잘 맡는 플레이어"
    elif counters['finisher'] >= 1 and counters['header_specialist'] >= 1:
        return "헤더 원샷원킬의 신"
    elif counters['attack'] >= 1 and counters['dribbler'] >= 1:
        return "공격적인 드리블러"
    elif counters['defense'] >= 1 and counters['tackler'] >= 1:
        return "방어적인 태클러"
    elif counters['interceptor'] >= 1 and counters['defense'] >= 1:
        return "완벽한 차단기"
    elif counters['playmaker'] >= 1 and counters['dribbler'] >= 1:
        return "드리블로 빌드업하는 플레이어"
    elif counters['playmaker'] >= 1 and counters['long_shot_master'] >= 1:
        return "빌드업 후 중거리 딸각의 신"
    elif counters['drive_pass_master'] >= 2:
        return "땅볼 패스 티키타카의 신"
    elif counters['setpiece_master'] >= 1 and counters['header_specialist'] >= 1:
        return "헤더와 프리킥 날먹의 신"
    elif counters['penalty_specialist'] >= 1 and counters['long_shot_master'] >= 1:
        return "신규 메타 적응의 신"
    elif counters['tackler'] >= 2:
        return "태클키 없으면 게임 못 하는 플레이어"
    elif counters['defense'] >= 2:
        return "수비 파이터의 신"
    elif counters['attack'] >= 2:
        return "유일무이한 공격의 신"
    elif counters['playmaker'] >= 2:
        return "패스 플레이메이커"
    elif counters['header_specialist'] >= 2:
        return "크로스 원툴 헤더 날먹의 신"
    elif counters['penalty_specialist'] >= 2:
        return "패널티박스에만 사는 플레이어"
    elif counters['long_shot_master'] >= 2:
        return "이상호급 중거리 딸깍의 신"
    elif counters['dribbler'] >= 1:
        return "드리블 트릭스터의 신"
    elif counters['card_collector'] >= 1:
        return "악질 옐로우 카드 수집가"
    elif counters['setpiece_master'] >= 3:
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
    match_data.append(data['matchDetail']['controller'])
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


# ─────────────────────────────────────────────────────────────────────────
# 매치 상세 박스스코어 (신규)
#
# match-detail API 응답(매치당 matchInfo[0], matchInfo[1] 각각의 dict)은 이미
# result() 라우트에서 me()/you()로 양쪽을 꺼내 shoot/pass/defence/matchDetail을
# 100% 읽고 있었지만, 지금까지는 승률개선검색(평균 지표 비교)에만 쓰이고
# 실제 화면(전적검색 결과)에는 날짜/결과/스코어 정도만 노출되고 있었습니다.
# 여기서는 같은 데이터를 그대로 재사용해 "경기당 상세 스탯" 형태로 정리합니다.
# → 새로운 API 호출이 전혀 없고, 이미 검증된 키만 사용하므로 안전합니다.
#
# possession / averageRating / redCards / ownGoal / injury 는 이 저장소의
# utils/utils.py::avg_data() 벤치마크 데이터에 avgpossession / avgavgrating /
# avgrcards / avgowngoal / avginjury 로 존재하는 것으로 보아 API 응답에도
# 대응 필드가 있을 가능성이 높지만, 실제 필드명을 100% 확인하지 못했습니다.
# 그래서 아래에서는 후보 키를 여러 개 시도하고, 전부 없으면 조용히 None으로
# 두어(화면에서 자동으로 숨김) 잘못된 값으로 오작동하지 않도록 방어적으로 처리했습니다.
# scripts/inspect_match_detail.py 로 실제 키를 확인해 필요하면 후보 목록에 추가/수정하세요.
def _safe_pct(success, tried):
    try:
        if tried in (None, 0):
            return None
        return round((success or 0) / tried * 100, 1)
    except (TypeError, ZeroDivisionError):
        return None


def _first_present(d, keys):
    """d(dict)에서 keys 후보 중 처음으로 존재하는(None이 아닌) 값을 반환."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _empty_boxscore():
    """build_match_boxscore()의 '데이터 없음' 상태를 반환한다.
    ⚠️ 버그 수정: 예전에는 shoot/pass/defence/discipline/extra가 그냥 빈 dict({})라서,
    result.html의 매치 상세 패널이 한쪽(예: 나)만 available=True이고 반대쪽(상대)이
    available=False인 매치를 만나면 templates/components/match_boxscore.html이
    side.pass.total.success 같은 중첩 키에 접근하다가
    "jinja2.exceptions.UndefinedError: 'dict object' has no attribute 'total'"로 그대로
    죽어서 매치 상세 렌더링 자체가 실패하고(전적검색 결과 페이지 렌더링 도중 예외가
    나면 result()의 except 블록이 이를 삼키고 "최근 전적이 존재하지 않습니다"로
    잘못 표시됨) 화면이 깨졌습니다. 실제 박스스코어(box)와 완전히 동일한 중첩 구조를
    갖되 모든 값을 None으로 채워서, 템플릿의 `if ... is not none else '-'` 처리가
    항상 안전하게 동작하도록 했습니다."""
    return {
        "available": False,
        "nickname": None,
        "shoot": {
            "total": None, "effective": None, "goal": None, "effective_pct": None,
            "heading": {"try": None, "goal": None},
            "freekick": {"try": None, "goal": None},
            "in_penalty": {"try": None, "goal": None},
            "out_penalty": {"try": None, "goal": None},
        },
        "pass": {
            "total": {"try": None, "success": None, "pct": None},
            "short": {"try": None, "success": None, "pct": None},
            "long": {"try": None, "success": None, "pct": None},
            "driven_ground": {"try": None, "success": None, "pct": None},
            "through": {"try": None, "success": None, "pct": None},
            "lobbed_through": {"try": None, "success": None, "pct": None},
        },
        "defence": {
            "tackle": {"try": None, "success": None, "pct": None},
            "block": {"try": None, "success": None, "pct": None},
        },
        "discipline": {
            "foul": None, "yellow_cards": None, "dribble": None,
            "corner_kick": None, "offside": None,
        },
        "extra": {
            "possession": None, "rating": None, "red_cards": None,
            "own_goal": None, "injury": None,
        },
    }


def build_match_boxscore(side_data):
    """me(data, nickname) 또는 you(data, nickname) 결과 하나를 받아
    화면에 표시할 박스스코어 dict로 변환한다. 실패해도 예외를 던지지 않고
    비어있는 형태를 반환해 result.html 렌더링이 절대 깨지지 않도록 한다."""
    empty = _empty_boxscore()
    if not isinstance(side_data, dict):
        return empty

    match_detail = side_data.get("matchDetail") or {}
    shoot = side_data.get("shoot") or {}
    pass_ = side_data.get("pass") or {}
    defence = side_data.get("defence") or {}

    # 기권/시스템 일시정지 등으로 스탯이 비어있는 경기는 data_list()와 동일하게 제외
    if match_detail.get("matchEndType") == 2 or match_detail.get("dribble") is None:
        return empty

    box = {
        "available": True,
        "nickname": side_data.get("nickname"),
        "shoot": {
            "total": shoot.get("shootTotal"),
            "effective": shoot.get("effectiveShootTotal"),
            "goal": shoot.get("goalTotal"),
            "effective_pct": _safe_pct(shoot.get("effectiveShootTotal"), shoot.get("shootTotal")),
            "heading": {"try": shoot.get("shootHeading"), "goal": shoot.get("goalHeading")},
            "freekick": {"try": shoot.get("shootFreekick"), "goal": shoot.get("goalFreekick")},
            "in_penalty": {"try": shoot.get("shootInPenalty"), "goal": shoot.get("goalInPenalty")},
            "out_penalty": {"try": shoot.get("shootOutPenalty"), "goal": shoot.get("goalOutPenalty")},
            # ✅ 신규(2026-09-12) — 넥슨 공식 스키마 확인 완료(shootPenaltyKick/goalPenaltyKick).
            # 페널티 박스 안/밖 슛과는 별개로, 승부차기 등 PK 자체 시도/성공.
            "penalty_kick": {"try": shoot.get("shootPenaltyKick"), "goal": shoot.get("goalPenaltyKick")},
        },
        "pass": {
            "total": {"try": pass_.get("passTry"), "success": pass_.get("passSuccess"),
                      "pct": _safe_pct(pass_.get("passSuccess"), pass_.get("passTry"))},
            "short": {"try": pass_.get("shortPassTry"), "success": pass_.get("shortPassSuccess"),
                      "pct": _safe_pct(pass_.get("shortPassSuccess"), pass_.get("shortPassTry"))},
            "long": {"try": pass_.get("longPassTry"), "success": pass_.get("longPassSuccess"),
                     "pct": _safe_pct(pass_.get("longPassSuccess"), pass_.get("longPassTry"))},
            "driven_ground": {"try": pass_.get("drivenGroundPassTry"), "success": pass_.get("drivenGroundPassSuccess"),
                               "pct": _safe_pct(pass_.get("drivenGroundPassSuccess"), pass_.get("drivenGroundPassTry"))},
            "through": {"try": pass_.get("throughPassTry"), "success": pass_.get("throughPassSuccess"),
                        "pct": _safe_pct(pass_.get("throughPassSuccess"), pass_.get("throughPassTry"))},
            "lobbed_through": {"try": pass_.get("lobbedThroughPassTry"), "success": pass_.get("lobbedThroughPassSuccess"),
                                "pct": _safe_pct(pass_.get("lobbedThroughPassSuccess"), pass_.get("lobbedThroughPassTry"))},
        },
        "defence": {
            "tackle": {"try": defence.get("tackleTry"), "success": defence.get("tackleSuccess"),
                       "pct": _safe_pct(defence.get("tackleSuccess"), defence.get("tackleTry"))},
            "block": {"try": defence.get("blockTry"), "success": defence.get("blockSuccess"),
                      "pct": _safe_pct(defence.get("blockSuccess"), defence.get("blockTry"))},
        },
        "discipline": {
            "foul": match_detail.get("foul"),
            "yellow_cards": match_detail.get("yellowCards"),
            "dribble": match_detail.get("dribble"),
            "corner_kick": match_detail.get("cornerKick"),
            "offside": match_detail.get("offsideCount"),
        },
        # ⚠️ 검증 필요(후보 키 방식) — scripts/inspect_match_detail.py 로 실제 키 확인 권장
        "extra": {
            "possession": _first_present(match_detail, ["possession", "avgPossession"]),
            "rating": _first_present(match_detail, ["averageRating", "avgRating", "rating"]),
            "red_cards": _first_present(match_detail, ["redCards", "redCard"]),
            "own_goal": _first_present(match_detail, ["ownGoal", "ownGoals"]),
            "injury": _first_present(match_detail, ["injury", "injuries"]),
        },
    }
    return box


# ─────────────────────────────────────────────────────────────────────────
# MVP / 주력 선수 TOP5 (신규)
#
# match-detail 응답의 매치당 player[] 배열은 이미 result()가 spId/spPosition을
# 꺼내 포메이션 표시에 쓰고 있었지만(spPosition==28은 SUB이라 제외하는 것도
# 기존 코드와 동일한 규칙입니다), 선수 개인별 "평점" 필드의 정확한 이름은
# 이 환경에서 실제 API 응답으로 확인하지 못했습니다. 그래서 아래에서도
# build_match_boxscore()의 extra 필드와 동일한 방식으로 후보 키를 여러 개
# 시도하고, 끝내 못 찾으면 조용히 None을 반환해(화면에서 MVP 영역만 자동으로
# 숨겨짐) 잘못된 값을 보여주거나 에러가 나지 않도록 방어적으로 처리했습니다.
# scripts/inspect_nexon_api.py 실행 결과로 실제 필드명을 확인하면
# _RATING_KEY_CANDIDATES만 좁혀주면 됩니다.
_RATING_KEY_CANDIDATES = ["spRating", "rating", "playerRating", "averageRating", "average_rating"]
_NAME_KEY_CANDIDATES = ["name", "playerName", "spName"]

PLAYER_IMAGE_URL_TMPL = "https://fco.dn.nexoncdn.co.kr/live/externalAssets/common/playersAction/p{spId}.png"
# ✅ 이미지 폴백용(신규, 2026-09-12) — 넥슨 "이미지 정보 조회" 카테고리에 액션샷
# (playersAction) 말고 플레인 카드 이미지(players) 템플릿도 따로 있다. 일부 선수는
# 액션샷 에셋이 없어서 playersAction 쪽이 404가 나는 경우가 있는데, 그럴 때
# 프론트에서 이 템플릿으로 한 번 더 시도한다(둘 다 실패하면 인라인 SVG로 대체).
PLAYER_IMAGE_FALLBACK_URL_TMPL = "https://fco.dn.nexoncdn.co.kr/live/externalAssets/common/players/p{spId}.png"


# ✅ 경기수 선택(신규, 2026-09-16 피드백) — "최근 25경기 선수 지표"가 항상
# 25경기로 고정이라 아쉽다는 요청으로, 조회할 매치 개수를 25/50/100 중에서
# 고를 수 있게 한다. 이 함수는 쿼리스트링(?match_count=...) 값을 검증하는
# 부분만 따로 떼어내서 테스트하기 쉽게 만든 것 — URL 조작이나 오타로 이상한
# 값(음수, 문자열, 허용 목록에 없는 숫자 등)이 들어와도 조용히 기본값으로
# 되돌린다.
def resolve_match_count(raw_value, allowed=(25, 50, 100), default=25):
    """쿼리스트링에서 받은 match_count 원본 값을 검증해 허용된 정수로 바꾼다."""
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return value if value in allowed else default


def format_grade_badge(sp_grade):
    """강화 단계(spGrade)를 "+3" 같은 배지 텍스트로 바꾼다. 0/None/강화 없음이면
    None(화면에서 배지 자체를 조용히 생략)."""
    try:
        grade = int(sp_grade)
    except (TypeError, ValueError):
        return None
    if grade <= 0:
        return None
    return f"+{grade}"


# ✅ 강화 단계별 색상(2026-09-12, 사용자 스크린샷 기준 재수정) — 넥슨이 제공하는 강화
# 배지 "이미지" 에셋은 없지만(이미지 정보 조회 카테고리에 playersAction/players 두
# 템플릿뿐), 강화 구간별로 다른 색을 쓰는 건 FC 온라인 커뮤니티/데이터 사이트에서
# 널리 쓰이는 관례라 CSS 클래스로 재현한다. ⚠️ 처음엔 11~13강을 각각 별도 색으로
# 잘못 배정했었는데, 사용자가 준 참고 스크린샷을 다시 보니 11~13강도 실버 색상이었다
# (1~3 브론즈, 4~7 실버, 8~10 골드, 11~13 다시 실버). 실제 색상 값은
# static/css/result.css의 .grade-tier-* 규칙에서 정의한다.
def grade_badge_class(sp_grade):
    """강화 단계(spGrade)를 색상 구간 CSS 클래스명으로 변환한다. 0/None이면 None."""
    try:
        grade = int(sp_grade)
    except (TypeError, ValueError):
        return None
    if grade <= 0:
        return None
    if grade <= 3:
        return "grade-tier-bronze"
    if grade <= 7:
        return "grade-tier-silver"
    if grade <= 10:
        return "grade-tier-gold"
    return "grade-tier-silver"


# ============================================================================
# ✅ 선수 등급(시즌) 배지 (신규, 2026-09-12)
# 넥슨 공식 문서(openapi.nexon.com > 메타데이터 정보 조회 > spid.json 설명)에
# "선수 고유 식별자(spId)는 시즌 아이디(seasonId) 3자리 + 선수 아이디(pid) 6자리로
# 구성된다"고 명시돼 있다. 즉 이미 갖고 있는 spId만으로 등급(시즌) 코드를 뽑아낼 수
# 있고, /static/fconline/meta/seasonid.json(spid.json과 마찬가지로 완전 공개 —
# 로그인/OAuth 불필요)에서 그 코드를 실제 등급명(className)/등급 아이콘(seasonImg)
# 으로 바꿀 수 있다. 시세(거래가)는 이 데이터로 알 수 없어서 넣지 않았다.
# ============================================================================

def derive_season_id(sp_id):
    """spId(시즌아이디 3자리 + 선수아이디 6자리)에서 시즌(등급) 아이디만 추출한다.
    pid가 항상 6자리라고 문서에 명시돼 있어서, 정수 나눗셈(// 10**6)으로 spId
    전체 자릿수와 무관하게 안전하게 뽑아낼 수 있다. spId가 없거나 형식이
    이상하면 None(호출부에서 조용히 배지를 생략하면 된다)."""
    try:
        sp_id_int = int(sp_id)
    except (TypeError, ValueError):
        return None
    if sp_id_int <= 0:
        return None
    return sp_id_int // 1_000_000


def get_player_rarity(sp_id, season_meta_map):
    """spId → {"season_id", "class_name", "season_img"}를 방어적으로 조회한다.
    season_meta_map: {seasonId(int): {"class_name":.., "season_img":..}} 형태로
    app.py에서 seasonid.json을 캐시해 전달한다. 매핑에 없거나 season_meta_map이
    비어 있으면(API 실패 등) season_id만 채우고 나머지는 None — 화면에서는
    class_name/season_img가 없으면 조용히 배지를 생략하면 된다."""
    season_id = derive_season_id(sp_id)
    if season_id is None:
        return {"season_id": None, "class_name": None, "season_img": None}
    meta = (season_meta_map or {}).get(season_id) or {}
    return {
        "season_id": season_id,
        "class_name": meta.get("class_name"),
        "season_img": meta.get("season_img"),
    }


def attach_rarity(player_dict, season_meta_map, sp_id_key="spId"):
    """선수 카드 dict(top_players/MVP 등에서 쓰는 형태)에 등급 정보를 덧붙인 새
    dict를 반환한다(원본은 변경하지 않음)."""
    if not isinstance(player_dict, dict):
        return player_dict
    sp_id = player_dict.get(sp_id_key)
    merged = dict(player_dict)
    merged.update(get_player_rarity(sp_id, season_meta_map))
    return merged


def _player_rating(player):
    """선수 개인 dict에서 평점을 방어적으로 추출. 못 찾으면 None."""
    if not isinstance(player, dict):
        return None
    val = _first_present(player, _RATING_KEY_CANDIDATES)
    if val is None and isinstance(player.get("status"), dict):
        val = _first_present(player["status"], _RATING_KEY_CANDIDATES)
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _player_display_name(player, spid_name_map=None):
    """선수 이름을 응답 필드 → spid_name_map(spId→이름 캐시) 순으로 방어적으로 추출."""
    if not isinstance(player, dict):
        return None
    name = _first_present(player, _NAME_KEY_CANDIDATES)
    if name:
        return name
    sp_id = player.get("spId")
    if spid_name_map and sp_id in spid_name_map:
        return spid_name_map.get(sp_id)
    return None


def compute_match_mvp(my_data, your_data, spid_name_map=None):
    """한 매치의 양 팀 player[] 전체에서 평점이 가장 높은 선수를 MVP로 반환한다.
    평점 필드를 한 명도 못 찾으면 None(화면에서 MVP 영역이 자동으로 숨겨짐)."""
    best = None
    for side_key, side_data, side_label in (
        ("me", my_data, "나"), ("opponent", your_data, "상대"),
    ):
        if not isinstance(side_data, dict):
            continue
        for player in side_data.get("player") or []:
            if not isinstance(player, dict) or player.get("spPosition") == 28:  # SUB 제외
                continue
            rating = _player_rating(player)
            if rating is None:
                continue
            if best is None or rating > best["rating"]:
                sp_id = player.get("spId")
                best = {
                    "spId": sp_id,
                    "name": _player_display_name(player, spid_name_map),
                    "rating": rating,
                    "side": side_key,
                    "side_label": side_label,
                    "nickname": side_data.get("nickname"),
                    "image": PLAYER_IMAGE_URL_TMPL.format(spId=sp_id) if sp_id else None,
                    "image_fallback": PLAYER_IMAGE_FALLBACK_URL_TMPL.format(spId=sp_id) if sp_id else None,
                }
    return best


def collect_player_appearances(my_data, match_result=None):
    """한 매치에서 실제로 기용된(SUB 제외) 내 선수들의 출전 정보를 반환한다.
    각 원소: {"spId", "rating", "spGrade", "spPosition", "win", "stat"}.
    여러 매치에 걸쳐 누적하면 "주력 선수 TOP5"(출전 횟수 + 평균 평점)나 선수별 상세
    지표 테이블(build_player_detail_stats)을 만들 수 있다.
    match_result(선택): 그 매치의 "승"/"무"/"패" — 넘기면 각 원소에 win(True/False/None)을
    같이 채워서, 이 선수가 뛴 경기들의 승률을 계산할 수 있다."""
    if not isinstance(my_data, dict):
        return []
    win = (match_result == "승") if match_result is not None else None
    out = []
    for player in my_data.get("player") or []:
        if not isinstance(player, dict) or player.get("spPosition") == 28:  # SUB 제외
            continue
        sp_id = player.get("spId")
        if sp_id is not None:
            status = player.get("status") if isinstance(player.get("status"), dict) else {}
            out.append({
                "spId": sp_id,
                "rating": _player_rating(player),
                # ✅ 강화 단계(신규, 2026-09-12) — 넥슨 공식 match-detail 스키마의
                # player[].spGrade. 시즌(등급)과는 다른 필드로, 그 매치 시점에 그
                # 선수 카드가 몇 강이었는지를 나타낸다(사용자별로 강화하는 값이라
                # spid.json 같은 정적 메타데이터로는 알 수 없고, 매치 데이터에만 있음).
                "spGrade": player.get("spGrade"),
                "spPosition": player.get("spPosition"),
                "win": win,
                # ✅ 선수별 상세 지표(신규, 2026-09-12) — 넥슨 공식 match-detail 스키마의
                # player[].status에서 그대로 가져온다(모두 실제 API 필드).
                "stat": {
                    "goal": status.get("goal"),
                    "assist": status.get("assist"),
                    # ✅ 공격력 지수 계산용(신규, 2026-09-12) — 넥슨 공식 스키마의
                    # player[].status.shoot/effectiveShoot(슛 시도/유효 슛 수, 슛 종류별
                    # 세분화가 아닌 선수 개인 합계).
                    "shoot": status.get("shoot"),
                    "effectiveShoot": status.get("effectiveShoot"),
                    "passTry": status.get("passTry"),
                    "passSuccess": status.get("passSuccess"),
                    "dribbleTry": status.get("dribbleTry"),
                    "dribbleSuccess": status.get("dribbleSuccess"),
                    "aerialTry": status.get("aerialTry"),
                    "aerialSuccess": status.get("aerialSuccess"),
                    "tackleTry": status.get("tackleTry"),
                    "tackle": status.get("tackle"),
                    "blockTry": status.get("blockTry"),
                    "block": status.get("block"),
                    "intercept": status.get("intercept"),
                },
            })
    return out


def count_used_players(my_data):
    """collect_player_appearances()의 spId 목록만 뽑아 반환(하위 호환용)."""
    return [a["spId"] for a in collect_player_appearances(my_data)]


def build_top_players(player_usage_counter, spid_name_map=None, player_avg_ratings=None, top_n=5, player_grade_map=None):
    """{spId: 출전 횟수} Counter를 받아 TOP N을 카드 표시용 dict 리스트로 변환한다.
    player_avg_ratings: {spId: 평균 평점} (선택). player_grade_map: {spId: 강화 단계}(선택,
    여러 매치에 걸쳐 마지막으로 확인된 값을 그대로 씀 — 강화값은 자주 안 바뀌는
    값이라 어느 매치 기준이든 큰 차이가 없다).
    ⚠️ 순위 기준은 "평균 평점"입니다(출전 횟수 기준 → 평점 기준으로 변경, 2026-09-12).
    평점이 아예 없는 선수(못 찾은 경우)는 순위를 매길 수 없으므로 뒤로 밀리되,
    표시 자체가 사라지지는 않도록 출전 횟수만으로 채워 넣는다(그래도 상위 랭킹은
    평점 데이터가 있는 선수가 우선한다)."""
    player_avg_ratings = player_avg_ratings or {}
    player_grade_map = player_grade_map or {}

    def sort_key(sp_id):
        avg_rating = player_avg_ratings.get(sp_id)
        # 평점 있음(1) > 평점 없음(0) 우선, 그 다음 평점 내림차순, 마지막으로 출전 횟수 내림차순(동점자 타이브레이커)
        return (
            1 if avg_rating is not None else 0,
            avg_rating if avg_rating is not None else 0,
            player_usage_counter[sp_id],
        )

    ranked_sp_ids = sorted(player_usage_counter.keys(), key=sort_key, reverse=True)[:top_n]

    top = []
    for sp_id in ranked_sp_ids:
        avg_rating = player_avg_ratings.get(sp_id)
        top.append({
            "spId": sp_id,
            "name": (spid_name_map or {}).get(sp_id),
            "count": player_usage_counter[sp_id],
            "avg_rating": round(avg_rating, 2) if avg_rating is not None else None,
            "image": PLAYER_IMAGE_URL_TMPL.format(spId=sp_id),
            "spGrade": player_grade_map.get(sp_id),
        })
    return top


# ✅ 선수별 상세 지표 테이블 (2026-09-12 fc-info.com 스타일 UI 반영을 위해 확장) —
# fc-info.com의 "감독모드 분석" 표를 참고. 포지션/출전/승률/골/어시/패스%/드리블%/
# 공중볼%/가로채기/태클%/블록%/평점은 전부 match-detail의 player[].status 실제
# 필드로 계산한 값이다.
# ⚠️ 공격력/수비력/기대득점률: fc-info.com이 보여주는 동일 이름의 칼럼은 그 사이트만의
# 비공개 산식이라 그대로 재현할 수 없다(값 자체를 그대로 베낄 수 없음). 대신 넥슨
# 공식 API에서 실제로 확인 가능한 값들(골/어시/유효슛/드리블/공중볼/패스 성공,
# shootDetail 좌표 기반 기대득점 근사치)을 우리 나름대로 조합한 "우리 자체 지수"로
# 계산해 넣었다 — 숫자의 절대적 의미(예: fc-info의 996.1과 우리의 996.1이 같은 뜻)가
# 아니라, 그 선수가 이 스쿼드 안에서 상대적으로 얼마나 공격/수비에 기여했는지를
# 보여주는 용도다. 선방력은 넥슨 API에 골키퍼 선방 관련 필드 자체가 없어서 뺐다.
def _minmax_heat(value, lo, hi):
    """value를 [lo, hi] 구간에서 0~1로 정규화(구간이 0이면 0.5 고정)."""
    if value is None:
        return None
    if hi <= lo:
        return 0.5
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def build_player_detail_stats(player_stat_acc, spid_name_map=None, season_meta_map=None):
    """app.py가 25경기 루프에서 collect_player_appearances()/accumulate_shot_xg()로 모은
    원시 누적치(player_stat_acc: {spId: {...합계들...}})를 화면 표시용 리스트로 변환한다.
    출전 횟수(count) 내림차순으로 정렬. 데이터가 없으면 빈 리스트."""
    def pct(success, tried):
        return _safe_pct(success, tried)

    rows = []
    for sp_id, acc in (player_stat_acc or {}).items():
        count = acc.get("count", 0)
        if count <= 0:
            continue
        wins = acc.get("wins", 0)
        win_known = acc.get("win_known", 0)
        rating_sum = acc.get("rating_sum", 0.0)
        rating_count = acc.get("rating_count", 0)
        position_counts = acc.get("position_counts") or {}
        main_position = max(position_counts.items(), key=lambda kv: kv[1])[0] if position_counts else None

        goal = acc.get("goal", 0)
        assist = acc.get("assist", 0)
        dribble_success = acc.get("dribble_success", 0)
        pass_success = acc.get("pass_success", 0)
        aerial_success = acc.get("aerial_success", 0)
        tackle_success = acc.get("tackle_success", 0)
        block_success = acc.get("block_success", 0)
        intercept = acc.get("intercept", 0)
        effective_shoot = acc.get("effective_shoot", 0)
        xg_sum = acc.get("xg_sum", 0.0)

        # ✅ 우리 자체 지수(신규) — 가중치는 "공격 기여가 큰 항목일수록 크게" 정도의
        # 상식적인 기준으로 정한 값이며, fc-info.com의 실제 가중치와는 무관하다.
        attack_score = round(
            goal * 40 + assist * 25 + effective_shoot * 8 + dribble_success * 3
            + pass_success * 0.4 + aerial_success * 1.5 + xg_sum * 30, 1)
        defense_score = round(
            tackle_success * 10 + block_success * 10 + intercept * 6 + aerial_success * 2.5, 1)
        expected_goal = round(xg_sum * 10, 1)

        row = {
            "spId": sp_id,
            "name": (spid_name_map or {}).get(sp_id),
            "spPosition": main_position,
            "pos_desc": POSITION_DESC.get(main_position, "") if main_position is not None else "",
            "count": count,
            "win_pct": pct(wins, win_known) if win_known else None,
            "attack_score": attack_score,
            "defense_score": defense_score,
            "expected_goal": expected_goal,
            "attack_points": goal + assist,
            "goal": goal,
            "assist": assist,
            "pass_pct": pct(pass_success, acc.get("pass_try", 0)),
            "dribble_pct": pct(dribble_success, acc.get("dribble_try", 0)),
            "aerial_pct": pct(aerial_success, acc.get("aerial_try", 0)),
            "intercept_avg": round(intercept / count, 1) if count else None,
            "tackle_pct": pct(tackle_success, acc.get("tackle_try", 0)),
            "block_pct": pct(block_success, acc.get("block_try", 0)),
            "rating": round(rating_sum / rating_count, 2) if rating_count else None,
            "spGrade": acc.get("last_grade"),
            "image": PLAYER_IMAGE_URL_TMPL.format(spId=sp_id),
            "image_fallback": PLAYER_IMAGE_FALLBACK_URL_TMPL.format(spId=sp_id),
        }
        row["grade_badge"] = format_grade_badge(row["spGrade"])
        row["grade_badge_class"] = grade_badge_class(row["spGrade"])
        # ✅ 포지션 그룹별 색상 구분(2026-09-13 피드백) — 수비수는 파란색 계열,
        # 미드필더는 초록색 계열, 공격수는 빨간색 계열, 골키퍼는 주황색 계열.
        row["pos_group"] = POSITION_GROUP.get(main_position) if main_position is not None else None
        row["pos_group_class"] = f"pos-group-{row['pos_group'].lower()}" if row["pos_group"] else ""

        # ✅ 위험표시(2026-09-14 피드백 재설계) — 예전엔 "이 표 안에서 하위 20%"
        # 같은 상대 기준이라 표에 선수가 적거나 다들 고만고만하면 아무도 안
        # 걸리는 문제가 있었다("위험 표시 뜨는 애가 아무도 없네?"). 그래서
        # 포지션별 실제 축구 상식에 맞는 절대 기준(한 경기 평균)으로 바꿨다.
        # 골키퍼는 대상에서 제외하고, 수비수는 수비 지수만, 공격수는 공격
        # 지수만, 미드필더는 둘 다 기준 미달일 때만 "아쉬운 선수"로 본다.
        # 표본이 너무 적으면(3경기 미만) 판단을 유보한다. 이 숫자들은 fc-info
        # 같은 공식 기준이 아니라 우리가 잡은 자체 판단 기준이다.
        attack_pg = (attack_score / count) if count else 0.0
        defense_pg = (defense_score / count) if count else 0.0
        risk = False
        if row["pos_group"] and count >= RISK_MIN_APPEARANCES:
            if row["pos_group"] == "FW":
                risk = attack_pg < FW_ATTACK_PG_MIN
            elif row["pos_group"] == "DF":
                risk = defense_pg < DF_DEFENSE_PG_MIN
            elif row["pos_group"] == "MF":
                risk = attack_pg < MF_ATTACK_PG_MIN and defense_pg < MF_DEFENSE_PG_MIN
            # GK는 위험표시 대상에서 제외(골키퍼에게 공격/수비 지수 기준을
            # 들이대는 게 맞지 않다는 피드백 반영)
        row["risk_flag"] = risk
        row["risk_tooltip"] = "기준에서 벗어나는 선수 (영입 고려 필요)" if risk else None

        if season_meta_map is not None:
            row.update(get_player_rarity(sp_id, season_meta_map))
        rows.append(row)

    # ✅ 2026-09-13 피드백 — 기본 정렬을 출전 횟수순에서 공격 지수 내림차순으로 변경.
    # (동점일 땐 평점, 그다음 출전 횟수로 안정적으로 타이브레이크)
    rows.sort(key=lambda r: (-r["attack_score"], -(r["rating"] or 0), -r["count"]))

    # ✅ fc-info.com 스타일 색상 강조(신규) — 공격 지수/수비 지수 칼럼을 이 표 안에서
    # 상대적으로 높은/낮은 값에 따라 붉은색/파란색 그라데이션으로 강조한다(정확한
    # 값이 아니라 이 스쿼드 안에서의 상대적 위치를 보여주는 용도).
    if rows:
        attack_vals = [r["attack_score"] for r in rows]
        defense_vals = [r["defense_score"] for r in rows]
        a_lo, a_hi = min(attack_vals), max(attack_vals)
        d_lo, d_hi = min(defense_vals), max(defense_vals)
        for r in rows:
            a_heat = _minmax_heat(r["attack_score"], a_lo, a_hi)
            d_heat = _minmax_heat(r["defense_score"], d_lo, d_hi)
            r["attack_bg"] = f"rgba(220, 38, 38, {0.12 + 0.68 * a_heat:.2f})"
            r["defense_bg"] = f"rgba(37, 99, 235, {0.12 + 0.68 * d_heat:.2f})"
            r["attack_text_light"] = a_heat >= 0.55
            r["defense_text_light"] = d_heat >= 0.55

    return rows


# ✅ 슛 타입 분포 (2026-09-12 재조사 후 전면 수정)
# ⚠️ 이전 버전은 "슛 종류(기술)" 필드가 넥슨 공식 API에 없다고 판단해 위치/상황
# 기준(헤더/프리킥/페널티박스 안팎/PK)으로 대체했었다. 하지만 openapi.nexon.com의
# 실제 매치 상세 정보 조회 문서를 다시 확인한 결과, match-detail 응답의
# shootDetail[] 배열 안에 "type"이라는 필드가 있고, 1~12 코드가 전부 문서에
# 명시돼 있었다(1 normal, 2 finesse, 3 header, 4 lob, 5 flare, 6 low, 7 volley,
# 8 free-kick, 9 penalty, 10 KNUCKLE, 11 BICYCLE, 12 super) — 이게 정확히
# "슛 기술" 분류였다. 그래서 이제 진짜 선수가 쏜 슛의 종류 그대로 집계한다
# (감아차기/낮은슛/파워샷 등 원하던 세분화가 전부 가능해졌다).
SHOT_TYPE_CODE_LABELS = {
    1: "일반슛",
    2: "감아차기",
    3: "헤더",
    4: "로빙슛",
    5: "플레어슛",
    6: "낮은슛",
    7: "발리슛",
    8: "프리킥",
    9: "페널티킥",
    10: "무회전슛",
    11: "바이시클킥",
    12: "파워슛",
}


def aggregate_shot_types(raw_side_list):
    """me(raw 매치 사이드, shootDetail 포함) 여러 개(25경기치)를 모아 슛 종류별로
    시도/유효슛/골/성공률/전체 대비 비중을 집계한다. shootDetail[].result는
    1(유효슛), 2(빗나감), 3(골)이다. 시도가 0인 타입은 목록에서 빠지고, 시도가
    많은 순으로 정렬한다. 데이터가 전혀 없으면 빈 리스트를 반환해 화면에서
    위젯 자체가 조용히 생략된다."""
    totals = defaultdict(lambda: {"try": 0, "on_target": 0, "goal": 0})
    total_shots = 0
    for side in raw_side_list or []:
        if not isinstance(side, dict):
            continue
        match_detail = side.get("matchDetail") or {}
        # 기권/시스템 일시정지 등으로 스탯이 비어있는 경기는 build_match_boxscore()와
        # 동일한 기준으로 제외
        if match_detail.get("matchEndType") == 2 or match_detail.get("dribble") is None:
            continue
        for shot in side.get("shootDetail") or []:
            if not isinstance(shot, dict):
                continue
            shot_type = shot.get("type")
            if shot_type is None:
                continue
            result = shot.get("result")
            totals[shot_type]["try"] += 1
            if result in (1, 3):
                totals[shot_type]["on_target"] += 1
            if result == 3:
                totals[shot_type]["goal"] += 1
            total_shots += 1

    # ⚠️ 버그 수정(2026-09-12) — SHOT_TYPE_CODE_LABELS에 없는 코드(문서화되지 않은 값)를
    # "기타슛(N)"으로 표시했었는데, 사용자 피드백으로는 정체를 알 수 없는 분류라 오히려
    # 혼란스럽고, 이 항목 하나 때문에 카드 그리드가 2행 4열로 깔끔하게 안 맞았다.
    # 문서에 없는 코드는 집계에서 아예 제외한다(비중 분모 total_shots에도 넣지 않음).
    out = []
    for shot_type, t in totals.items():
        if t["try"] <= 0 or shot_type not in SHOT_TYPE_CODE_LABELS:
            continue
        out.append({
            "key": shot_type,
            "label": SHOT_TYPE_CODE_LABELS[shot_type],
            "try": t["try"],
            "on_target": t["on_target"],
            "goal": t["goal"],
            "pct": _safe_pct(t["goal"], t["try"]),
            "share": _safe_pct(t["try"], total_shots),
        })
    out.sort(key=lambda s: -s["try"])
    return out


# ✅ 기대득점(xG) 근사 모델 (신규, 2026-09-12) — fc-info.com의 "기대득점률" 칼럼은
# 그 사이트만의 비공개 산식이라 그대로 재현할 수 없지만, 넥슨 공식 API의
# shootDetail[].x/y(슛 좌표, 슈팅 팀 기준 0~1 정규화 — 상대 골대가 x=1, y=0.5 쪽)와
# type(슛 종류)만으로도 "이 위치·이 종류의 슛이 평균적으로 골이 될 확률"을 거리/각도
# 기반으로 근사하는 건 축구 분석에서 널리 쓰이는 방식이다. 여기서는 그 공개된 방식을
# 우리 나름대로 단순화해 구현한 것으로, fc-info.com의 실제 산식과는 다르다는 점을
# 분명히 밝혀둔다(사용자에게도 전달 필요).
_SHOT_TYPE_XG_MULTIPLIER = {
    1: 1.0,   # 일반슛
    2: 1.0,   # 감아차기
    3: 0.8,   # 헤더
    4: 0.85,  # 로빙슛
    5: 0.9,   # 플레어슛
    6: 1.05,  # 낮은슛
    7: 0.9,   # 발리슛
    10: 0.95,  # 무회전슛
    11: 0.75,  # 바이시클킥
    12: 1.1,  # 파워샷
}


def estimate_shot_xg(shot):
    """슛 하나(shootDetail 원소)의 대략적인 기대득점(xG, 0~1 확률)을 근사한다.
    페널티킥(9)은 실축이 드물어 고정값, 프리킥(8)은 직접 프리킥 특성상 낮은 고정값을
    쓰고, 그 외에는 골대(x=1, y=0.5)까지의 거리 기반 로지스틱 곡선에 슛 종류별
    가중치를 곱한다. 좌표가 없으면 보수적으로 낮은 기본값을 반환."""
    if not isinstance(shot, dict):
        return 0.0
    shot_type = shot.get("type")
    if shot_type == 9:
        return 0.75
    if shot_type == 8:
        return 0.05
    x, y = shot.get("x"), shot.get("y")
    if x is None or y is None:
        return 0.1
    try:
        dist = math.sqrt((1 - float(x)) ** 2 + (float(y) - 0.5) ** 2)
    except (TypeError, ValueError):
        return 0.1
    base = 1 / (1 + math.exp(9 * (dist - 0.22)))
    xg = base * _SHOT_TYPE_XG_MULTIPLIER.get(shot_type, 1.0)
    return max(0.01, min(0.95, xg))


def accumulate_shot_xg(player_stat_acc, side_data):
    """한 매치의 me 사이드(shootDetail 포함)를 받아, 슛을 쏜 선수(shootDetail[].spId)별로
    xG 합계를 player_stat_acc에 누적한다. player_stat_acc는 app.py에서 만든
    defaultdict라 없는 spId는 자동으로 기본값이 채워진다(그 선수가 collect_player_appearances
    쪽에서 한 번도 안 잡혔다면 count=0으로 남아 build_player_detail_stats()에서
    자동으로 걸러진다)."""
    if not isinstance(side_data, dict):
        return
    match_detail = side_data.get("matchDetail") or {}
    if match_detail.get("matchEndType") == 2 or match_detail.get("dribble") is None:
        return
    for shot in side_data.get("shootDetail") or []:
        if not isinstance(shot, dict):
            continue
        sp_id = shot.get("spId")
        if sp_id is None:
            continue
        acc = player_stat_acc[sp_id]
        acc["xg_sum"] = acc.get("xg_sum", 0.0) + estimate_shot_xg(shot)


# ✅ 1v1 공식경기 최고 티어 표시 (신규) — divisionId → 티어 뱃지(이미지 또는 이름) 매핑.
# app.py 안에 똑같은 테이블이 두 군데(전적검색, 카카오톡 스킬 라우트) 중복돼 있던 것을
# 여기 하나로 모아서 재사용한다.
# ⚠️ 2026-09-12 업데이트 — 신규 "마스터" 티어 추가(divisionId 1700/1800/1900)로 인해
# GitHub main 브랜치에 반영된 최신 테이블(update_2026 경로, ico_rank0~20)로 맞춤.
# dev 브랜치가 예전 update_2009 테이블(1300 다음 바로 2000으로 건너뜀)을 그대로 쓰고
# 있어서, 새로 생긴 티어의 유저는 division_mapping에서 못 찾아 "정보 없음"으로 뜨던
# 문제를 여기서 고친다.
DIVISION_MAPPING = [
    {"divisionId": 800, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank0.png"},
    {"divisionId": 900, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank1.png"},
    {"divisionId": 1000, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank2.png"},
    {"divisionId": 1100, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank3.png"},
    {"divisionId": 1200, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank4.png"},
    {"divisionId": 1300, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank5.png"},
    {"divisionId": 1700, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank6.png"},
    {"divisionId": 1800, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank7.png"},
    {"divisionId": 1900, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank8.png"},
    {"divisionId": 2000, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank9.png"},
    {"divisionId": 2100, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank10.png"},
    {"divisionId": 2200, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank11.png"},
    {"divisionId": 2300, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank12.png"},
    {"divisionId": 2400, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank13.png"},
    {"divisionId": 2500, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank14.png"},
    {"divisionId": 2600, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank15.png"},
    {"divisionId": 2700, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank16.png"},
    {"divisionId": 2800, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank17.png"},
    {"divisionId": 2900, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank18.png"},
    {"divisionId": 3000, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank19.png"},
    {"divisionId": 3100, "divisionName": "https://ssl.nexon.com/s2/game/fo4/obt/rank/large/update_2026/ico_rank20.png"},
]


def resolve_division_tier(division_info, match_type_code):
    """Nexon maxdivision API 응답(division_info: [{"matchType": int, "division": int}, ...])에서
    특정 matchType(예: 50 = 공식경기)의 티어를 뽑아 {"tier_name": str|None, "tier_image": url|None}으로
    반환한다. 정보가 없으면 둘 다 None — 화면에서는 조용히 뱃지를 생략하면 된다."""
    if not division_info:
        return {"tier_name": None, "tier_image": None}
    try:
        code = int(match_type_code)
    except (TypeError, ValueError):
        return {"tier_name": None, "tier_image": None}
    match_type_info = next((item for item in division_info if item.get("matchType") == code), None)
    if not match_type_info:
        return {"tier_name": None, "tier_image": None}
    tier_id = match_type_info.get("division")
    division_item = next((item for item in DIVISION_MAPPING if item["divisionId"] == tier_id), None)
    if not division_item:
        return {"tier_name": None, "tier_image": None}
    if division_item["divisionName"].startswith("http"):
        return {"tier_name": None, "tier_image": division_item["divisionName"]}
    return {"tier_name": division_item["divisionName"], "tier_image": None}


def division_rank(division_info, match_type_code):
    """maxdivision API 응답에서 특정 matchType의 divisionId가 DIVISION_MAPPING
    안에서 몇 번째(0부터, 낮을수록 하위 티어)인지 반환한다. 못 찾으면 None —
    "상대 전적 검색" 트리거 멘트("맞밸이 아니신데요?")에서 티어 격차를 비교하는
    용도라, 실패해도 그 멘트만 조용히 생략하면 된다."""
    if not division_info:
        return None
    try:
        code = int(match_type_code)
    except (TypeError, ValueError):
        return None
    match_type_info = next((item for item in division_info if item.get("matchType") == code), None)
    if not match_type_info:
        return None
    tier_id = match_type_info.get("division")
    for idx, item in enumerate(DIVISION_MAPPING):
        if item["divisionId"] == tier_id:
            return idx
    return None


# ============================================================================
# ✅ 상대 전적 검색 (신규, 2026-09-16 피드백) — 프로/인플루언서 페이지에서
# 닉네임 두 개를 넣으면 서로 붙었던 경기만 골라 역대 전적을 보여주는 기능.
# Nexon API에는 "두 유저 간 매치만" 조회하는 엔드포인트가 없어서, 앱단에서
# nick1의 최근 매치(최대 100경기)를 순회하며 상대가 nick2인 경기만 걸러내는
# 방식으로 구현한다(app.py의 head_to_head_search 라우트가 그 필터링을 하고,
# 여기서는 그 결과를 화면 표시용으로 요약한다).
# ============================================================================

# ⚠️ 2026-09-16 9차 피드백 — "트리거 멘트도 좀 다양화 해달라, '요즘 상대가
# 안 되시는데요?'처럼 전적이 살짝 밀릴 때 나오는 것도 있으면 좋겠다"는 요청.
# 기존엔 "완전 전승/완전 전패/정확히 동률"인 극단적인 경우만 멘트가 붙고,
# 그 사이(이기는 쪽으로 치우침/지는 쪽으로 치우침)는 아무 멘트도 안 붙었다.
# 그 사이 구간을 메우는 조건 2개(_H2H_TRIGGER_LOSING_EDGE/_WINNING_EDGE)를
# 추가하고, 기존 조건들도 문구를 1개→여러 개 풀로 늘려 같은 조건이어도 검색할
# 때마다(닉네임 조합 기준 결정적으로) 다른 멘트가 나오게 했다.
_H2H_TRIGGER_SWEEP_WIN = [
    "이 상대한테는 전승이시네요! 완전 유리한 상성이에요 🔥",
    "이 상대 앞에서는 무적이시네요 — 상성 甲이에요 💪",
    "이 상대만 만나면 자신감이 뿜뿜이시겠어요 😎",
]
_H2H_TRIGGER_SWEEP_LOSE = [
    "이 상대한테는 아직 이겨본 적이 없네요... 설욕전이 필요해요 😮‍💨",
    "이 상대만 만나면 고개를 못 드시네요... 극복이 필요해요 😣",
    "천적을 제대로 만나셨네요 — 진지하게 대책이 필요해 보여요 🫠",
]
_H2H_TRIGGER_RIVAL = [
    "엎치락뒤치락, 진짜 라이벌 상성이네요!",
    "물고 물리는 각축전 — 이 정도면 숙명의 라이벌이에요 🥊",
    "승부는 그때그때 다르네요 — 붙을 때마다 재밌을 상성이에요",
]
_H2H_TRIGGER_LOSING_EDGE = [
    "요즘 상대가 안 되시는데요...? 전적이 살짝 밀리고 있어요 😅",
    "이 상대한테는 요즘 고전 중이시네요 — 전적이 조금 아쉬워요",
    "근소하게 열세인 상성이네요, 다음 판엔 뒤집어보세요!",
]
_H2H_TRIGGER_WINNING_EDGE = [
    "그래도 이 상대한테는 한 수 위시네요! 전적상 우위예요 😏",
    "근소하지만 유리한 상성이에요 — 계속 이 흐름 가져가보세요",
    "이 상대 앞에서는 그래도 어깨 좀 펴셔도 될 것 같아요 🙂",
]
_H2H_TRIGGER_FEW_MEETS = [
    "아직 몇 번 안 붙어봤네요 — 좀 더 붙어봐야 진짜 상성이 보일 것 같아요",
    "표본이 좀 적어서, 상성을 논하기엔 아직 일러요",
]


def head_to_head_trigger_message(wins, draws, losses, rank1=None, rank2=None, seed=""):
    """상대 전적 검색 결과를 보고 재미있는 "트리거" 멘트를 하나 고른다(스트리머들이
    서로 상대 전적을 볼 때 재밌어할 만한 것 — 사용자 피드백). 실제 전적/티어 격차
    데이터로만 판단하며, 여러 조건에 해당하면 더 눈에 띄는 것부터 우선한다.
    seed(보통 "닉네임1|닉네임2")를 넘기면 같은 조건 안에서도 멘트 풀 중 하나를
    결정적으로 골라 다양성을 준다(_pick_from_pool 재사용)."""
    total = wins + draws + losses
    if rank1 is not None and rank2 is not None and abs(rank1 - rank2) >= 6:
        return "맞밸이 아니신데요...? 티어 차이가 꽤 나네요 👀"
    if total >= 3 and losses == 0 and wins > 0:
        return _pick_from_pool(_H2H_TRIGGER_SWEEP_WIN, seed + ':sweep_win')
    if total >= 3 and wins == 0 and losses > 0:
        return _pick_from_pool(_H2H_TRIGGER_SWEEP_LOSE, seed + ':sweep_lose')
    if total >= 2 and wins == losses and wins > 0:
        return _pick_from_pool(_H2H_TRIGGER_RIVAL, seed + ':rival')
    if total >= 3 and losses > wins and wins > 0:
        return _pick_from_pool(_H2H_TRIGGER_LOSING_EDGE, seed + ':losing_edge')
    if total >= 3 and wins > losses and losses > 0:
        return _pick_from_pool(_H2H_TRIGGER_WINNING_EDGE, seed + ':winning_edge')
    if total == 1:
        return "딱 한 번 만난 사이네요 — 데이터가 더 쌓이면 진짜 상성을 알 수 있어요"
    if total == 2:
        return _pick_from_pool(_H2H_TRIGGER_FEW_MEETS, seed + ':few_meets')
    return None


def build_head_to_head_summary(match_results, rank1=None, rank2=None, nick1="", nick2=""):
    """match_results: [{"result": "승"/"무"/"패", "my_goal": int, "opp_goal": int},
    ...] — nick1 시점 기준으로 이미 걸러진 두 사람 간 매치 목록. 승/무/패,
    평균 득실, 재미 트리거 멘트를 종합해 반환한다.
    ⚠️ 2026-09-16 피드백 — "포메이션은 딱히 안보여줘도 된다"는 요청으로
    "우세했던 포메이션" 계산/반환을 제거했다(대신 플레이 스타일 분석을 새로
    추가 — build_head_to_head_analysis() 참고).
    ⚠️ 2026-09-16 9차 피드백 — 트리거 멘트 다양화를 위해 nick1/nick2를
    head_to_head_trigger_message()의 seed로 그대로 넘긴다."""
    total = len(match_results)
    wins = sum(1 for m in match_results if m['result'] == '승')
    draws = sum(1 for m in match_results if m['result'] == '무')
    losses = sum(1 for m in match_results if m['result'] == '패')
    goal_for = sum(m.get('my_goal') or 0 for m in match_results)
    goal_against = sum(m.get('opp_goal') or 0 for m in match_results)

    return {
        "total": total, "wins": wins, "draws": draws, "losses": losses,
        "win_pct": round(wins / total * 100, 1) if total else 0.0,
        "goal_for": goal_for, "goal_against": goal_against,
        "avg_goal_for": round(goal_for / total, 1) if total else 0.0,
        "avg_goal_against": round(goal_against / total, 1) if total else 0.0,
        "trigger": head_to_head_trigger_message(
            wins, draws, losses, rank1, rank2, seed=f"{nick1.lower()}|{nick2.lower()}"
        ),
    }


# ✅ 상대 전적 플레이 스타일 분석 (신규, 2026-09-16 3차 피드백, 2026-09-16
# 6차 피드백으로 "장단점 분석" → "플레이 스타일 분석"으로 리프레이밍) —
# "교로텔리 vs 메시연 검색했을 때 서로 장단점도 분석해주면 좋을듯? 잘했던거
# 못했던거"라는 요청에서 시작해, "장단점 분석말고 플레이 스타일 분석 느낌이
# 날듯?"이라는 후속 피드백으로 성적표(잘함/못함) 톤 대신 각자의 플레이
# 성향을 짚어주는 톤으로 다시 정리했다.
# 두 선수가 맞붙은 매치들(build_match_boxscore()로 이미 만들어둔 박스스코어)만
# 모아 평균 골/유효슈팅률/패스성공률/태클성공률/평균 드리블 성공을 비교해서,
# 한쪽이 뚜렷하게(각 지표별 최소 차이 이상) 앞선 지표를 상대 강점/내 약점으로
# 나눠 문장으로 만든다. 지표 최소 차이(min_diff) 미만이면 "비슷했다"고 보고
# 그 지표는 그냥 건너뛴다 — 잘하지도 못하지도 않은 걸 억지로 강점/약점으로
# 우기지 않기 위함. 실제 경기 데이터로만 판단하며 픽션 추가 없음.
# 가장 두드러진 지표(지표별 min_diff 대비 편차가 가장 큰 것)는 "⚽ 피니셔형"
# 같은 플레이 스타일 태그로도 뽑아 헤드라인으로 보여준다(_H2H_STYLE_LABELS).
def _accumulate_h2h_box_stats(acc, box):
    """build_match_boxscore() 결과 하나를 누적 합계(acc, plain dict)에 더한다."""
    if not isinstance(box, dict) or not box.get("available"):
        return
    acc["matches"] = acc.get("matches", 0) + 1
    acc["goal"] = acc.get("goal", 0) + (box["shoot"]["goal"] or 0)
    acc["shoot_try"] = acc.get("shoot_try", 0) + (box["shoot"]["total"] or 0)
    acc["shoot_effective"] = acc.get("shoot_effective", 0) + (box["shoot"]["effective"] or 0)
    acc["pass_try"] = acc.get("pass_try", 0) + (box["pass"]["total"]["try"] or 0)
    acc["pass_success"] = acc.get("pass_success", 0) + (box["pass"]["total"]["success"] or 0)
    acc["tackle_try"] = acc.get("tackle_try", 0) + (box["defence"]["tackle"]["try"] or 0)
    acc["tackle_success"] = acc.get("tackle_success", 0) + (box["defence"]["tackle"]["success"] or 0)
    acc["dribble"] = acc.get("dribble", 0) + (box["discipline"].get("dribble") or 0)


_H2H_ANALYSIS_METRICS = [
    # (누적 키, 라벨, 강점일 때 문구, 약점일 때 문구, 최소 유효 차이, 표시 포맷)
    # ⚠️ 2026-09-16 7차 피드백 — "슈팅 정교형, 수비형 이런거 너무 식상하다,
    # 인플루언서 전적검색은 서로 놀리는 편이니까 좀 재밌게"라는 요청으로
    # 문구를 딱딱한 리포트 톤에서 서로 놀리는 듯한 캐스터/중계 톤으로 바꿨다.
    # 숫자·판정 로직(min_diff 등)은 그대로라 어디까지나 "말투"만 바뀐 것.
    ("goal_avg", "평균 득점", "골 냄새는 기가 막히게 맡았어요", "골 앞에서는 유독 조용했어요", 0.4, "{:.1f}골"),
    ("shoot_pct", "유효슈팅률", "쏘는 족족 골로 꽂혔어요", "슛은 쏘는데 골은 어디 갔을까요", 8, "{:.0f}%"),
    ("pass_pct", "패스 성공률", "패스 하나는 국가대표급이었어요", "패스가 자꾸 상대 발로 배달갔어요", 5, "{:.0f}%"),
    ("tackle_pct", "수비 성공률", "몸으로 다 막아냈어요", "태클만 하면 헛발질이었어요", 10, "{:.0f}%"),
    ("dribble_avg", "평균 드리블 성공", "혼자서 다 뚫고 다녔어요", "드리블하다 공을 자주 헌납했어요", 1.5, "{:.1f}회"),
]

# ✅ 지표별 플레이 스타일 태그 (2026-09-16 6차 피드백, 7차 피드백으로 톤 수정)
# — 강점 지표들 중 가장 두드러진 것 하나를 뽑아 헤드라인으로 붙여준다.
# "잘함/못함" 평가가 아니라 "이 사람은 이런 스타일"이라는 인상을 주기 위한
# 라벨인데, "슈팅 정교형/수비형 같은거 너무 식상하다, 인플루언서 상대 전적은
# 서로 놀리는 편이니까 좀 재밌게"라는 요청으로 딱딱한 "OO형" 대신 실제
# 중계/커뮤니티에서 쓰는 장난스러운 별명 톤으로 바꿨다.
# ⚠️ 2026-09-16 9차 피드백 — ① "플레이 스타일이 안 뜰 때가 있다, 항상 나오게
# 안 되냐"는 요청으로, 강점 지표가 하나도 없는(=min_diff를 넘는 우위가 전혀
# 없는) 선수에게도 이제 스타일 태그를 붙인다(_H2H_STYLE_FALLBACK_LABELS —
# "이거다!" 할 만큼 튀는 지표는 없지만 그 자체를 장난스럽게 표현) ② "스타일이
# 좀 다양했으면"이라는 요청으로 각 지표별 라벨을 1개→여러 개 후보 풀로 늘리고,
# 검색한 두 닉네임으로 만든 해시로 그중 하나를 결정적으로 골라준다(같은 두
# 사람을 다시 검색하면 항상 같은 태그가 나오지만, 다른 사람들끼리는 다양하게
# 갈린다 — 매번 무작위로 바뀌는 것보다 이게 "이 사람 스타일"이라는 느낌에 더
# 맞다고 판단).
_H2H_STYLE_LABEL_POOLS = {
    "goal_avg": [
        "⚽ 닥치고 골 넣는 해결사", "⚽ 골 냄새 하나는 기가 막힘", "⚽ 만나기만 하면 골 넣는 저승사자",
    ],
    "shoot_pct": [
        "🎯 한 방이면 끝나는 스나이퍼", "🎯 헛발질 없는 명사수", "🎯 쐈다 하면 무조건 골",
    ],
    "pass_pct": [
        "🧠 그라운드 위의 감독", "🧠 패스 하나는 국가대표급", "🧠 축구 지능만큼은 甲",
    ],
    "tackle_pct": [
        "🛡️ 뚫리지 않는 벽", "🛡️ 몸으로 다 막는 수문장", "🛡️ 철벽 방패",
    ],
    "dribble_avg": [
        "⚡ 혼자서도 다 하는 발재간 부자", "⚡ 드리블 쇼맨", "⚡ 발재간으로 다 풀어내는 마술사",
    ],
}

# 강점 지표가 하나도 없어도(=뚜렷하게 앞선 지표가 없어도) "무조건 뜨게 해달라"는
# 요청에 맞춰 붙여주는 캐치올 태그 — 특정 지표를 잘한다고 우기지 않고, "뭐든
# 고르게 한다"는 뉘앙스로만 표현해 근거 없는 강점을 지어내지 않는다.
_H2H_STYLE_FALLBACK_LABELS = [
    "🧩 종잡을 수 없는 올라운더", "🎭 뭐든 고르게 하는 팔방미인", "⚖️ 밸런스 하나는 甲",
]


def _pick_from_pool(pool, seed):
    """seed 문자열을 md5로 해시해 pool에서 하나를 결정적으로 골라 반환한다.
    같은 seed는 항상 같은 결과 — "이 사람 스타일"이라는 느낌을 유지하기 위함."""
    if not pool:
        return None
    if len(pool) == 1:
        return pool[0]
    digest = hashlib.md5(seed.encode('utf-8')).hexdigest()
    return pool[int(digest, 16) % len(pool)]


def build_head_to_head_analysis(acc1, acc2, min_matches=2, nick1="", nick2=""):
    """_accumulate_h2h_box_stats()로 누적한 두 선수의 맞대결 스탯 합계(acc1=nick1,
    acc2=nick2)를 비교해 플레이 스타일 태그와 강점/약점 문장 리스트를 반환한다.
    {"player1": {"style": str, "strengths": [...], "weaknesses": [...]},
     "player2": {...}}
    ⚠️ 2026-09-16 8차 피드백 — "표본이 부족하면 섹션 전체가 조용히 사라지는데,
    그러지 말고 무조건 뜨게 해달라"는 요청으로 더 이상 None을 반환하지 않는다.
    대신 표본이 부족하거나(2경기 미만) 두 사람의 지표가 다 고만고만해서 뚜렷한
    차이가 없을 때도 {"fallback": True, "message": ...} 형태로 안내 문구를
    반환해, 화면에서는 항상 뭔가는 보여주되 근거 없는 강점/약점을 지어내지는
    않는다.
    ⚠️ 2026-09-16 9차 피드백 — "스타일 태그도 항상 뜨게, 좀 다양하게"라는 요청.
    nick1/nick2를 넘겨주면 그 둘의 닉네임 조합으로 스타일 태그를 결정적으로
    고른다(_pick_from_pool) — 강점 지표가 있으면 그 지표의 라벨 풀에서,
    강점이 하나도 없는 선수는 _H2H_STYLE_FALLBACK_LABELS 풀에서 고른다."""
    m1, m2 = acc1.get("matches", 0), acc2.get("matches", 0)
    if m1 < min_matches or m2 < min_matches:
        return {
            "fallback": True,
            "message": "아직 두 분이 붙은 경기 수가 적어서 스타일 분석은 다음 맞대결 때 보여드릴게요!",
        }

    def metrics(acc):
        n = acc["matches"]
        return {
            "goal_avg": acc["goal"] / n,
            "shoot_pct": _safe_pct(acc["shoot_effective"], acc["shoot_try"]),
            "pass_pct": _safe_pct(acc["pass_success"], acc["pass_try"]),
            "tackle_pct": _safe_pct(acc["tackle_success"], acc["tackle_try"]),
            "dribble_avg": acc["dribble"] / n,
        }

    v1, v2 = metrics(acc1), metrics(acc2)
    strengths1, weaknesses1, strengths2, weaknesses2 = [], [], [], []
    # 강점으로 뽑힌 지표 중 (min_diff 대비 편차가 가장 큰) 하나를 스타일 태그로 승격
    best1 = best2 = None  # (score, key)

    for key, label, good_phrase, bad_phrase, min_diff, fmt in _H2H_ANALYSIS_METRICS:
        a, b = v1.get(key), v2.get(key)
        if a is None or b is None:
            continue
        diff = a - b
        if abs(diff) < min_diff:
            continue
        score = abs(diff) / min_diff
        if diff > 0:
            strengths1.append(f"{label} · {good_phrase} ({fmt.format(a)} vs {fmt.format(b)})")
            weaknesses2.append(f"{label} · {bad_phrase} ({fmt.format(b)} vs {fmt.format(a)})")
            if best1 is None or score > best1[0]:
                best1 = (score, key)
        else:
            strengths2.append(f"{label} · {good_phrase} ({fmt.format(b)} vs {fmt.format(a)})")
            weaknesses1.append(f"{label} · {bad_phrase} ({fmt.format(a)} vs {fmt.format(b)})")
            if best2 is None or score > best2[0]:
                best2 = (score, key)

    if not (strengths1 or weaknesses1 or strengths2 or weaknesses2):
        return {
            "fallback": True,
            "message": "다섯 개 지표가 다 도긴개긴이에요 — 진짜 스타일이 닮은 라이벌인가 봐요!",
        }

    def style_for(best, seed):
        if best:
            pool = _H2H_STYLE_LABEL_POOLS.get(best[1])
            picked = _pick_from_pool(pool, seed + ':' + best[1])
            if picked:
                return picked
        return _pick_from_pool(_H2H_STYLE_FALLBACK_LABELS, seed + ':fallback')

    seed_base = f"{nick1.lower()}|{nick2.lower()}"
    return {
        "player1": {
            "style": style_for(best1, seed_base + ':1'),
            "strengths": strengths1[:3], "weaknesses": weaknesses1[:3],
        },
        "player2": {
            "style": style_for(best2, seed_base + ':2'),
            "strengths": strengths2[:3], "weaknesses": weaknesses2[:3],
        },
    }


# ✅ 11v11 잔디밭 뷰 (신규) — 한 매치의 나/상대 선수 11명씩(SUB 제외)을 잔디밭 배경 위
# 좌표(%)로 변환한다. app.py의 "최근 경기" 스쿼드 위젯에서 쓰는 spPosition→좌표 매핑과
# 같은 값을 쓰되, 여기서는 한 화면에 두 팀을 동시에 그리기 위해 별도로 둔다(단일 팀
# 위젯 쪽 코드는 건드리지 않아 기존 동작에 영향 없음).
POSITION_COORDS = {
    0: (50, 90), 1: (50, 82), 2: (80, 70), 3: (85, 65), 4: (63, 78), 5: (50, 78),
    6: (37, 78), 7: (15, 65), 8: (20, 70), 9: (65, 57), 10: (50, 57), 11: (35, 57),
    12: (85, 35), 13: (65, 50), 14: (50, 50), 15: (35, 50), 16: (15, 35),
    17: (80, 35), 18: (50, 35), 19: (20, 35), 20: (60, 25), 21: (50, 25),
    22: (40, 25), 23: (80, 25), 24: (65, 20), 25: (50, 17), 26: (35, 20), 27: (20, 25),
}
POSITION_DESC = {
    0: "GK", 1: "SW", 2: "RWB", 3: "RB", 4: "RCB", 5: "CB", 6: "LCB", 7: "LB", 8: "LWB",
    9: "RDM", 10: "CDM", 11: "LDM", 12: "RM", 13: "RCM", 14: "CM", 15: "LCM", 16: "LM",
    17: "RAM", 18: "CAM", 19: "LAM", 20: "RF", 21: "CF", 22: "LF", 23: "RW",
    24: "RS", 25: "ST", 26: "LS", 27: "LW",
}

# ✅ 포지션 그룹 분류(2026-09-13, "최근 25경기 선수 지표" 포지션 색상 구분 피드백) —
# 골키퍼/수비수/미드필더/공격수 4개 그룹으로 묶어 색상을 다르게 표시한다.
POSITION_GROUP = {
    0: "GK",
    1: "DF", 2: "DF", 3: "DF", 4: "DF", 5: "DF", 6: "DF", 7: "DF", 8: "DF",
    9: "MF", 10: "MF", 11: "MF", 12: "MF", 13: "MF", 14: "MF", 15: "MF", 16: "MF",
    17: "MF", 18: "MF", 19: "MF",
    20: "FW", 21: "FW", 22: "FW", 23: "FW", 24: "FW", 25: "FW", 26: "FW", 27: "FW",
}

# ✅ "최근 25경기 선수 지표" 위험표시 절대 기준(2026-09-14, round 12 피드백) —
# build_player_detail_stats()에서 사용. 한 경기 평균(attack_score/count,
# defense_score/count) 기준이며, fc-info 등 공식 기준이 아니라 우리가 정한
# 판단 기준이다. 필요하면 실제 데이터를 더 보고 조정할 수 있다.
FW_ATTACK_PG_MIN = 15.0     # 공격수: 이 미만이면 공격 기여가 아쉬움
DF_DEFENSE_PG_MIN = 12.0    # 수비수: 이 미만이면 수비 기여가 아쉬움
MF_ATTACK_PG_MIN = 12.0     # 미드필더: 공격/수비 지수가 "둘 다" 이 미만이어야 위험표시
MF_DEFENSE_PG_MIN = 8.0
RISK_MIN_APPEARANCES = 3    # 표본이 이보다 적으면(3경기 미만) 판단 보류


# ============================================================================
# ✅ 포메이션별 승률 분석 (신규, 2026-09-16 피드백) — "내가 어떤 포메이션일 때
# 승률이 좋은지" / "상대의 어떤 포메이션에 약한지"를 최근 N경기에서 집계한다.
# 새 API 호출은 없다 — 이미 매치 루프에서 받아온 my_data/your_data의 선수
# spPosition 분포만으로 포메이션을 추정한다.
# ============================================================================

def derive_formation(appearances):
    """collect_player_appearances() 결과(spPosition 포함)에서 GK/SUB을 제외한
    10명의 포지션 분포로 포메이션 문자열("4-2-3-1", "4-4-2" 등)을 만든다.
    수비형 미드필더(RDM/CDM/LDM, spPosition 9~11)가 있으면 미드필더를 수비형/
    공격형 두 줄로 나눠 4줄로, 없으면 3줄로 표시한다(흔히 쓰는 포메이션 표기
    관례와 동일). 선수 10명이 정확히 안 채워지면(데이터 누락 등) None을
    반환해 호출부에서 그 경기는 조용히 집계에서 빠진다."""
    outfield = [a for a in appearances if a.get('spPosition') not in (0, 28, None)]
    if len(outfield) != 10:
        return None
    df = sum(1 for a in outfield if POSITION_GROUP.get(a['spPosition']) == 'DF')
    dmf = sum(1 for a in outfield if a['spPosition'] in (9, 10, 11))
    amf = sum(1 for a in outfield if a['spPosition'] in (12, 13, 14, 15, 16, 17, 18, 19))
    fw = sum(1 for a in outfield if POSITION_GROUP.get(a['spPosition']) == 'FW')
    if df + dmf + amf + fw != 10:
        return None
    parts = [df]
    if dmf:
        parts.append(dmf)
    if amf:
        parts.append(amf)
    parts.append(fw)
    return '-'.join(str(p) for p in parts)


# ✅ 2026-09-16 피드백 — "5-2-3 같은 것도 보통 5에서 양쪽 풀백은 살짝 더 위로
# 가있잖아, 기본 베이스를 생각하고 가자(넥슨 공식 스쿼드메이커 참고)". 수비
# 라인이 일자로 늘어서지 않고 풀백/윙백(양 끝)이 센터백들보다 공격 방향으로
# 살짝 더 나가 있는 완만한 곡선이 실제 전술판의 기본형이라, formation_to_dots()의
# 맨 뒷줄(수비 라인)에서만 중앙에서 멀수록 y를 줄여(더 앞으로) 이 곡선을 만든다.
# 이 숫자(%p)는 넥슨 스쿼드메이커(fconline.nexon.com/squadmaker) 캡처 화면을
# 참고해 감으로 잡은 값 — 정확한 좌표 API가 아니라 어디까지나 "모양"을 보여주는
# 개념도라는 점은 동일하다.
BACKLINE_CURVE_MAX = 9  # %p — 맨 끝 풀백/윙백이 중앙 센터백보다 최대 이만큼 위로


def formation_to_dots(formation_code):
    """'4-2-3-1' 같은 포메이션 코드를 미니 축구장 위 점 배치(x%, y%) 리스트로
    바꾼다. 그 경기의 실제 좌표가 아니라 포메이션 "모양"을 보여주는 개념도라서,
    골키퍼는 항상 맨 아래 중앙에 하나 추가하고, 나머지 줄은 뒤(수비, y 큰 값)에서
    앞(공격, y 작은 값)으로 갈수록 균등한 간격으로 배치한다. 맨 뒷줄(수비 라인)은
    양 끝(풀백/윙백)이 중앙(센터백)보다 살짝 앞으로 나온 완만한 곡선으로 배치해
    일자로 늘어선 부자연스러운 모양을 피한다(BACKLINE_CURVE_MAX 참고)."""
    if not formation_code:
        return []
    try:
        tiers = [int(t) for t in formation_code.split('-')]
    except (TypeError, ValueError):
        return []
    if not tiers:
        return []
    dots = [{"x": 50, "y": 92, "label": "GK"}]
    n = len(tiers)
    for tier_idx, count in enumerate(tiers):
        if count <= 0:
            continue
        base_y = 45 if n == 1 else round(78 - tier_idx * (63 / (n - 1)), 1)
        center = (count - 1) / 2
        for i in range(count):
            x = round((i + 1) * 100 / (count + 1), 1)
            y = base_y
            if tier_idx == 0 and count > 1:
                normalized = abs(i - center) / center if center else 0
                y = round(base_y - BACKLINE_CURVE_MAX * (normalized ** 2), 1)
            dots.append({"x": x, "y": y, "label": None})
    return dots


_FORMATION_TIP_FALLBACK = "포메이션 정보가 부족해 구체적인 공략 팁은 어려워요."
_FORMATION_STRENGTH_FALLBACK = "이 포메이션에서 좋은 흐름을 만들고 있어요 — 지금의 빌드업/전진 패턴을 유지해보세요."


def _parse_formation_shape(formation_code):
    """포메이션 코드("4-2-3-1" 등)를 {"back", "fw", "mid_tiers"}로 분해한다.
    mid_tiers는 df/fw 사이의 숫자들 — derive_formation()의 규칙상 dmf/amf 중
    하나만 있으면 길이 1(어느 쪽인지 코드만으로는 구분 불가), 둘 다 있으면
    길이 2([dmf, amf])다. 파싱 실패(빈 코드, 숫자 2개 미만)면 None."""
    if not formation_code:
        return None
    tiers = [int(t) for t in formation_code.split('-') if t.strip().isdigit()]
    if len(tiers) < 2:
        return None
    return {"back": tiers[0], "fw": tiers[-1], "mid_tiers": tiers[1:-1]}


# ⚠️ 2026-09-16 4차 피드백 — "피드백이 너무 1차원적이야, 너무 당연한 소리하는거
# 같은데 제대로 찾아서 기입해줘"라는 지적으로, back/mid/fw 세 가지를 각각 독립
# 판단해서 문장 조각을 조립하는 방식으로 한 번 바꿨었다.
# ⚠️ 2026-09-16 8차 피드백 — 그런데 그 결과가 "3문장이 항상 다 붙어서 너무
# 길고 매번 비슷한 틀로 느껴진다"는 지적을 받아, back/mid/fw 중 가장 특징적인
# 축 "하나만" 골라 한 문장으로 바꿨었다.
# ⚠️ 2026-09-16 9차 피드백 — 그런데 축 하나만 보고 고르다 보니, 예를 들어
# 4-2-2-2와 4-2-3-1은 back(4)도 같고 중원의 dmf(수비형 미드필더 수)도 둘 다
# 2라서 "수미 2명" 카테고리가 똑같이 뽑혀 서로 다른 포메이션인데 문구가
# 완전히 같아지는 문제가 있었다("하나라도 같으면 안 된다"는 지적). 그래서
# 이번엔 back/mid(dmf·amf 또는 단일 중원 수 그대로)/fw 세 숫자를 전부
# 문장 안에 실제 숫자로 박아 넣는 방식으로 바꿨다 — formation_code 자체가
# 이 세 숫자(들)의 조합이므로, 코드가 다르면 숫자 중 하나는 반드시 달라지고,
# 그 숫자가 문장에 그대로 들어가는 이상 텍스트도 항상 달라진다(진짜로
# 겹칠 수 없음). 대신 각 축의 설명을 "숫자 + 짧은 전술 힌트" 한 덩어리로
# 압축하고 " · "로만 이어붙여 3문장을 나열하던 것보다 훨씬 짧게 유지한다.
# ⚠️ 2026-09-16 10차 피드백 — "모든 포메이션 팁이 다 '백4은 무난한 뒷라인'
# 으로 시작해서 너무 획일적이다, 포메이션마다 진짜 상대법이 있는 것처럼
# 그럴싸하게" 라는 지적. back 값은 사실 mid_tiers+fw가 정해지면 자동으로
# 정해진다(정식 포메이션 코드는 항상 back+중원 합+fw=10명이므로) — 즉
# back 숫자를 문장에 넣지 않아도 mid/fw 두 축만으로 formation_code가 다르면
# 문구도 항상 달라진다는 수학적 보장은 그대로 유지된다. 이 여유를 이용해
# ① back 표현을 "무난하다"는 밋밋한 사실 진술 대신 실제 공략 포인트가
# 담긴 여러 문구 후보 풀로 늘리고 ② 세 절(back/mid/fw)을 항상 같은 순서로
# 나열하지 않고 formation_code를 해시해 순서를 섞어서, "다 똑같은 틀로
# 시작한다"는 인상 자체를 없앴다(같은 코드는 항상 같은 순서 — 랜덤이 아니라
# 결정적이라 같은 포메이션을 다시 봐도 문구가 안 바뀐다).
_FORMATION_BACK_POOL_HIGH = [
    "백{back}(스리백+윙백)이라 윙백이 전진했을 때 뒷공간을 그대로 파고들 수 있음",
    "백{back}이라 숫자는 많지만 윙백이 붕 뜨는 타이밍에 크로스로 흔들면 잘 먹힘",
    "백{back} 스리백이라 측면이 비는 순간 빠른 역습이 잘 통함",
]
_FORMATION_BACK_POOL_THREE = [
    "스리백이라 측면 1대1로 승부를 걸면 승산이 큼",
    "스리백 특성상 풀백 없이 윙백만 있어 빠른 사이드 돌파에 약함",
    "스리백이라 중앙보다 사이드 공략이 확실한 정답",
]
_FORMATION_BACK_POOL_DEFAULT = [
    "백{back}은 무난한 편이라도 풀백이 전진했을 때 뒷공간이 살짝 비는 편",
    "백{back} 기준형이라 크게 안 흔들리지만 스루패스 타이밍만큼은 노려볼만",
    "백{back}이 안정적이어도 측면 오버래핑 직후 커버가 한 박자 늦는 편",
]


def _formation_back_clause(back, seed):
    if back >= 5:
        pool = _FORMATION_BACK_POOL_HIGH
    elif back == 3:
        pool = _FORMATION_BACK_POOL_THREE
    else:
        pool = _FORMATION_BACK_POOL_DEFAULT
    return _pick_from_pool(pool, seed + ':back').format(back=back)


_FORMATION_MID_POOL_DMF_HEAVY = [
    "수미{dmf}·공미{amf}로 중앙은 두껍지만 측면으로 전환하면 뚫림",
    "수미{dmf}·공미{amf}라 중앙 스루패스는 잘 막혀도 크로스는 열려 있음",
]
_FORMATION_MID_POOL_AMF_HEAVY = [
    "수미{dmf}·공미{amf}로 인원이 앞쪽에 몰려 있어 역습 타이밍이 큼",
    "수미{dmf}·공미{amf}라 전방 압박만 풀면 뒷공간이 바로 열림",
]
_FORMATION_MID_POOL_EVEN = [
    "수미{dmf}·공미{amf}로 하프스페이스가 비니 그쪽을 파고들면 좋음",
    "수미{dmf}·공미{amf}라 대각선으로 찔러주는 패스에 특히 약함",
]
_FORMATION_MID_POOL_SINGLE_HIGH = [
    "중원 {mid}명으로 숫자는 밀려도 역습 타이밍만큼은 확실히 있음",
    "중원 {mid}명이라 볼 점유엔 강해도 빠른 전환 수비는 약한 편",
]
_FORMATION_MID_POOL_SINGLE_LOW = [
    "중원 {mid}명뿐이라 한 번만 뺏으면 바로 스루패스 찬스",
    "중원 {mid}명이라 미드필더끼리 간격이 넓어 그 틈을 노리면 좋음",
]
_FORMATION_MID_POOL_SINGLE_MID = [
    "중원 {mid}명이라 빠른 좌우 전환에 특히 취약",
    "중원 {mid}명이 넓게 벌어져 있어 중앙 돌파가 의외로 잘 먹힘",
]
_FORMATION_MID_POOL_EMPTY = [
    "중원 자체가 없다시피 해서 뒷공간이 바로 열림",
    "중원이 거의 비어 있어 롱패스 한 방으로 뒷공간을 바로 노릴 수 있음",
]


def _formation_mid_clause(mid_tiers, seed):
    if len(mid_tiers) == 2:
        dmf, amf = mid_tiers
        if dmf > amf:
            pool = _FORMATION_MID_POOL_DMF_HEAVY
        elif amf > dmf:
            pool = _FORMATION_MID_POOL_AMF_HEAVY
        else:
            pool = _FORMATION_MID_POOL_EVEN
        return _pick_from_pool(pool, seed + ':mid').format(dmf=dmf, amf=amf)
    if len(mid_tiers) == 1:
        mid = mid_tiers[0]
        if mid >= 5:
            pool = _FORMATION_MID_POOL_SINGLE_HIGH
        elif mid <= 2:
            pool = _FORMATION_MID_POOL_SINGLE_LOW
        else:
            pool = _FORMATION_MID_POOL_SINGLE_MID
        return _pick_from_pool(pool, seed + ':mid').format(mid=mid)
    return _pick_from_pool(_FORMATION_MID_POOL_EMPTY, seed + ':mid')


_FORMATION_FW_POOL_HIGH = [
    "최전방 {fw}명이라 역습은 빠른 대신 수비 가담이 적어 뒷공간이 큼",
    "최전방 {fw}명이 한꺼번에 전진해 있어 전방 압박에는 약한 편",
]
_FORMATION_FW_POOL_ONE = [
    "최전방 {fw}명만 확실히 묶으면 공격 전개 자체가 끊김",
    "최전방 {fw}명뿐이라 그 선수만 고립시키면 볼 배급이 막힘",
]
_FORMATION_FW_POOL_TWO = [
    "최전방 {fw}명(투톱)이라 오프사이드 트랩이 잘 통함",
    "최전방 {fw}명(투톱)이라 수비 라인을 높게 올리면 자주 걸림",
]


def _formation_fw_clause(fw, seed):
    if fw >= 3:
        pool = _FORMATION_FW_POOL_HIGH
    elif fw == 1:
        pool = _FORMATION_FW_POOL_ONE
    else:
        pool = _FORMATION_FW_POOL_TWO
    return _pick_from_pool(pool, seed + ':fw').format(fw=fw)


_FORMATION_CLAUSE_ORDERS = [
    (0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0),
]


def formation_counter_tip(formation_code):
    """상대가 이 포메이션을 쓸 때 어떻게 공략하면 좋을지, 백라인/중원/최전방
    세 축을 실제 숫자와 함께 짧은 문구로 조립해 반환한다. mid_tiers·fw
    숫자만으로도 formation_code가 다르면 back은 자동으로 결정되므로(정식
    포메이션은 항상 back+중원+fw=10명), 이 둘이 문장에 그대로 들어가는 이상
    문구도 formation_code가 다르면 항상 달라진다(수학적으로 겹칠 수 없음).
    back 문구·세 절의 나열 순서는 formation_code를 해시해 결정적으로 고르므로
    같은 포메이션은 항상 같은 문구를 주면서도, 포메이션마다 시작하는 절이
    달라져 "다 똑같은 틀"이라는 인상은 사라진다."""
    shape = _parse_formation_shape(formation_code)
    if not shape:
        return _FORMATION_TIP_FALLBACK
    back, fw, mid_tiers = shape["back"], shape["fw"], shape["mid_tiers"]
    seed = formation_code
    clauses = [
        _formation_back_clause(back, seed),
        _formation_mid_clause(mid_tiers, seed),
        _formation_fw_clause(fw, seed),
    ]
    order = _FORMATION_CLAUSE_ORDERS[int(hashlib.md5(('order:' + seed).encode('utf-8')).hexdigest(), 16) % len(_FORMATION_CLAUSE_ORDERS)]
    ordered = [clauses[i] for i in order]
    return " · ".join(ordered) + "."


def formation_strength_note(formation_code):
    """내가 이 포메이션을 쓸 때 왜 잘 통하는 편인지(내 강점 관점)를 조립해서
    반환한다. formation_counter_tip()과 같은 back/mid/fw 분해를 쓰되, "상대를
    어떻게 공략할지"가 아니라 "내가 이 배치를 왜 유지하면 좋을지"로 문장을
    다르게 조립한다."""
    shape = _parse_formation_shape(formation_code)
    if not shape:
        return _FORMATION_STRENGTH_FALLBACK
    back, fw, mid_tiers = shape["back"], shape["fw"], shape["mid_tiers"]
    clauses = []

    if back >= 5:
        clauses.append("백5라 수비 뒷공간을 최소화한 채로 윙백을 전진시켜 안정적으로 공격 숫자를 더할 수 있는 배치입니다")
    elif back == 3:
        clauses.append("스리백 기반이라 윙백을 높게 두고도 중앙 수비 숫자가 유지돼, 실점 부담 없이 폭 넓은 공격이 가능합니다")
    else:
        clauses.append("백4 기준형이라 수비 밸런스를 잃지 않으면서 풀백의 오버래핑으로 측면 공격을 더할 수 있는 배치입니다")

    if len(mid_tiers) == 2:
        dmf, amf = mid_tiers
        if dmf >= 2:
            clauses.append(f"수비형 미드필더 {dmf}명이 중앙을 지켜주는 덕분에 공격형 미드필더들이 볼 뺏길 걱정 없이 과감하게 전진할 수 있습니다")
        elif amf >= 3:
            clauses.append(f"공격형 미드필더가 {amf}명이라 중앙 점유율이 높아 상대가 쉽게 볼을 뺏어가지 못합니다")
        else:
            clauses.append("중원이 앞뒤로 나뉘어 있어 볼 전개와 마무리 구간의 역할이 명확하게 분리됩니다")
    elif len(mid_tiers) == 1:
        mid = mid_tiers[0]
        if mid >= 5:
            clauses.append(f"미드필더 라인이 {mid}명으로 두꺼워 중원 싸움에서 수적 우위를 가져갈 수 있습니다")
        elif mid <= 2:
            clauses.append("미드필더 라인이 간결해 공수 전환 속도가 빠른 편입니다")
        else:
            clauses.append("중원 인원이 균형 있게 배치돼 있어 공수 어느 쪽에도 치우치지 않습니다")
    else:
        clauses.append("최소 인원 구성이라 공수 전환이 빠릅니다")

    if fw >= 3:
        clauses.append("최전방이 3명이라 역습 상황에서 숫자 우위로 빠르게 마무리할 수 있습니다")
    elif fw == 1:
        clauses.append("최전방 1명에게 힘을 실어주는 대신 중원·수비 숫자를 더 확보해 안정적으로 운영할 수 있습니다")
    else:
        clauses.append("투톱이 서로 커버하며 최전방에서부터 압박을 걸 수 있습니다")

    return ". ".join(clauses[:3]) + "."


def build_formation_analysis(my_formation_stats, opp_formation_stats, overall_goals_against_avg=None,
                              min_matches=2, weak_top_n=3, best_top_n=3):
    """포메이션별 승/무/패 누적(app.py 매치 루프에서 만든 defaultdict)을 화면
    표시용으로 변환한다.
    - main_formation: 내가 가장 많이 쓴 포메이션(점 배치도 포함) — "내 주력 포메이션"
    - best_formations: 승률이 좋았던 내 포메이션 TOP N(표본 min_matches경기 이상,
      1승도 없는(승률 0%) 포메이션은 "승률 좋음" 취지에 안 맞아 제외) — 실제
      전체 평균 대비 승률 비교(data_insight, 유의미할 때만)와 큐레이션 강점
      노트(tip)를 같이 담는다.
    - weak_formations: 상대가 이 포메이션일 때 내 승률이 낮았던 TOP N(표본
      min_matches경기 이상) — 실제 전적/평균 실점(data_insight, 유의미할 때만)과
      큐레이션 공략 팁(tip)을 같이 담는다.
    경기 수가 적어 표본 기준을 만족하는 포메이션이 하나도 없으면 각 리스트이
    빈 채로 반환되고, 화면에서는 조용히 섹션이 생략된다.
    ⚠️ 2026-09-16 4차 피드백 반영 — best_formations의 승률 0% 항목 제외,
    best_formations에도 data_insight/tip 추가(원래 weak_formations만 있었음)."""
    def win_pct(stat):
        return round(stat['wins'] / stat['count'] * 100, 1) if stat['count'] else 0.0

    main_formation = None
    if my_formation_stats:
        best_code, best_stat = max(my_formation_stats.items(), key=lambda kv: kv[1]['count'])
        main_formation = {
            "code": best_code,
            "count": best_stat['count'],
            "win_pct": win_pct(best_stat),
            "dots": formation_to_dots(best_code),
        }

    total_matches = sum(stat['count'] for stat in my_formation_stats.values())
    total_wins = sum(stat['wins'] for stat in my_formation_stats.values())
    overall_win_pct = round(total_wins / total_matches * 100, 1) if total_matches else None

    best_formations = []
    for code, stat in my_formation_stats.items():
        # ✅ 4차 피드백 — "승률 좋음이 0%인 게 있으면 굳이 안나와도 될거같아"라서
        # 1승도 없으면(wins == 0) 아예 후보에서 제외한다(표본 부족과 별개로).
        if stat['count'] < min_matches or stat['wins'] <= 0:
            continue
        pct = win_pct(stat)
        entry = {
            "code": code, "count": stat['count'], "win_pct": pct,
            "wins": stat['wins'], "draws": stat['draws'], "losses": stat['losses'],
            "dots": formation_to_dots(code),
            "tip": formation_strength_note(code),
            "data_insight": None,
        }
        if overall_win_pct is not None and pct > overall_win_pct + 8:
            entry["data_insight"] = (
                f"이 포메이션을 썼을 때 승률 {pct}%로, 전체 평균 승률({overall_win_pct}%)보다 높았습니다."
            )
        best_formations.append(entry)
    best_formations.sort(key=lambda f: (-f['win_pct'], -f['count']))
    best_formations = best_formations[:best_top_n]

    weak_formations = []
    for code, stat in opp_formation_stats.items():
        if stat['count'] < min_matches:
            continue
        avg_against = stat['goals_against_sum'] / stat['count']
        entry = {
            "code": code,
            "count": stat['count'],
            "wins": stat['wins'], "draws": stat['draws'], "losses": stat['losses'],
            "win_pct": win_pct(stat),
            "avg_goals_against": round(avg_against, 1),
            "dots": formation_to_dots(code),
            "tip": formation_counter_tip(code),
            "data_insight": None,
        }
        if overall_goals_against_avg is not None and avg_against > overall_goals_against_avg + 0.3:
            entry["data_insight"] = (
                f"이 포메이션 상대로는 평균 {avg_against:.1f}실점으로, "
                f"전체 평균({overall_goals_against_avg:.1f}실점)보다 실점이 많았습니다."
            )
        weak_formations.append(entry)
    weak_formations.sort(key=lambda f: (f['win_pct'], -f['count']))
    weak_formations = weak_formations[:weak_top_n]

    return {
        "main_formation": main_formation,
        "best_formations": best_formations,
        "weak_formations": weak_formations,
    }


def _pitch_players_for_side(side_data, spid_name_map, x_transform):
    """side_data(my_data/your_data 형태)에서 SUB을 제외한 선수 목록을 좌표가 달린
    카드 표시용 dict 리스트로 변환하고, 팀 평균 평점(평점을 찾은 선수 기준)도 같이 계산.
    ⚠️ 2026-09-13 3차 재설계 — 위/아래 절반 분리(라운드10)로도 "선수가 겹친다"는
    피드백이 다시 나왔다(사용자가 스크린샷 두 장에 직접 그려준 파란 테두리 박스를
    픽셀 단위로 비교해보니, 두 박스는 세로로는 거의 전체 높이를 차지하고 가로로만
    정확히 반씩 나뉘어 있었다 — 즉 "위/아래"가 아니라 "좌/우"로 완전히 분리해야
    한다는 뜻). 그래서 이번엔 포메이션의 깊이(depth: 자기 진영↔상대 진영)를 화면
    가로(x)축에, 원래 좌우 폭(width_pos)은 세로(y)축에 매핑한다: 상대 팀은 왼쪽
    절반(자기 골대가 왼쪽 가장자리), 내 팀은 오른쪽 절반(자기 골대가 오른쪽
    가장자리)에 배치되고, 두 팀의 공격 라인이 중앙 부근에서 마주보되 x축 구간이
    아예 겹치지 않으므로(상대: ~4~46%, 나: ~54~96%) 어떤 경우에도 서로의 영역을
    침범할 수 없다. 호출부에서 팀별로 다른 x_transform(depth_rank → x%) 함수를
    넘겨준다.
    ⚠️ 마커 확대(피드백 #5)에 따른 겹침 방지 — POSITION_COORDS의 원래 깊이값은
    간격이 들쭉날쭉해서(예: CDM 57 vs CM 50은 겨우 7 차이), 마커를 키우니 같은 라인의
    포지션끼리 겹치는 문제가 생겼다. 그래서 원래 깊이값을 그대로 압축하는 대신, 이번
    매치에 실제로 나온 선수들의 깊이값만 모아 "서로 다른 깊이 단계"를 오름차순으로
    나열한 뒤 0~1 사이에 균등한 간격으로 다시 배치(rank 정규화)한다. 포메이션이
    무엇이든(원톱/투톱, 미드필더 숫자 등) 실제 쓰인 라인 수에 맞춰 자동으로 간격이
    벌어지므로 겹침 없이 항상 보기 좋게 배치된다."""
    if not isinstance(side_data, dict):
        return [], None

    raw_players = []
    for player in side_data.get("player") or []:
        if not isinstance(player, dict) or player.get("spPosition") == 28:  # SUB 제외
            continue
        pos = player.get("spPosition")
        width_pos, depth = POSITION_COORDS.get(pos, (50, 50))
        raw_players.append((player, pos, width_pos, depth))

    if not raw_players:
        return [], None

    # ⚠️ 완전히 겹치는 마커 방지(2026-09-12) — 두 선수의 spPosition이 같거나(예: 포메이션에
    # 따라 최전방 공격수 코드가 중복 배정되는 경우), POSITION_COORDS에 없는 코드라서 둘 다
    # 기본값(50,50)으로 떨어지면, 화면 좌표가 완전히 같아져 마커가 정확히 포개져 버린다.
    # (width_pos, depth) 좌표가 같은 선수들을 묶어서 실제 축구장에서 "좌우로 나란히 선"
    # 것처럼 폭(width_pos) 축으로 부채꼴 모양으로 균등하게 벌려준다.
    coord_to_indices = defaultdict(list)
    for idx, (_, _, width_pos, depth) in enumerate(raw_players):
        coord_to_indices[(width_pos, depth)].append(idx)

    adjusted_width_pos = [width_pos for (_, _, width_pos, _) in raw_players]
    SPREAD_STEP = 14  # %p 단위 간격
    for indices in coord_to_indices.values():
        n = len(indices)
        if n <= 1:
            continue
        base_width_pos = raw_players[indices[0]][2]
        for order, idx in enumerate(indices):
            offset = (order - (n - 1) / 2) * SPREAD_STEP
            adjusted_width_pos[idx] = max(6, min(94, base_width_pos + offset))

    # 실제로 쓰인 깊이값들만 오름차순 정렬 후 0~1로 균등 재배치(rank 정규화)
    distinct_depths = sorted(set(depth for _, _, _, depth in raw_players))
    if len(distinct_depths) > 1:
        depth_rank = {
            d: i / (len(distinct_depths) - 1) for i, d in enumerate(distinct_depths)
        }
    else:
        depth_rank = {distinct_depths[0]: 0.5}

    players = []
    ratings = []
    for i, (player, pos, width_pos, depth) in enumerate(raw_players):
        screen_y = adjusted_width_pos[i]
        sp_id = player.get("spId")
        rating = _player_rating(player)
        if rating is not None:
            ratings.append(rating)
        # ✅ 2026-09-16 피드백 — 잔디밭 뷰에서 선수를 마우스오버/클릭했을 때 뜨는
        # 미니 카드(골/어시스트/슛/패스/태클/가로채기)용 원본 스탯. 이미 받아온
        # match-detail 응답(player.status)을 그대로 재사용 — 추가 API 호출 없음.
        # collect_player_appearances()의 stat 필드와 동일한 소스/이름 규칙을 쓴다.
        status = player.get("status") if isinstance(player.get("status"), dict) else {}
        players.append({
            "spId": sp_id,
            "name": _player_display_name(player, spid_name_map),
            "pos_desc": POSITION_DESC.get(pos, ""),
            "x": x_transform(depth_rank[depth]),
            "y": screen_y,
            "rating": round(rating, 1) if rating is not None else None,
            "image": PLAYER_IMAGE_URL_TMPL.format(spId=sp_id) if sp_id is not None else None,
            "image_fallback": PLAYER_IMAGE_FALLBACK_URL_TMPL.format(spId=sp_id) if sp_id is not None else None,
            "is_mvp": False,
            "goal": status.get("goal"),
            "assist": status.get("assist"),
            "shoot": status.get("shoot"),
            "effective_shoot": status.get("effectiveShoot"),
            "pass_try": status.get("passTry"),
            "pass_success": status.get("passSuccess"),
            "tackle_try": status.get("tackleTry"),
            "tackle_success": status.get("tackle"),
            "intercept": status.get("intercept"),
        })
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    return players, avg_rating


def build_pitch_view(my_data, your_data, spid_name_map=None, mvp=None):
    """한 매치의 나/상대 선수 11명씩을 "하나의 잔디밭" 좌표로 변환해 반환한다.
    ⚠️ 2026-09-13 3차 재설계(사용자 피드백: "아직도 선수가 겹친다", 스크린샷에 직접
    그려준 파란 테두리 박스 2장을 픽셀 비교해보니 좌/우로 정확히 반씩 나뉜 전체
    높이의 박스였음) — 위/아래 절반 분리(라운드10)를 다시 좌/우 절반 분리로 되돌리되,
    라운드10에서 추가된 "실제 사용된 깊이 단계만 모아 균등 재배치" 로직은 그대로
    유지해 예전 좌/우 시도 때 겪었던 같은 팀 내부 겹침 문제는 재발하지 않는다.
    ⚠️ 2026-09-14 4차 수정(피드백: "내 스쿼드가 왼쪽, 상대 스쿼드가 오른쪽에 있어야
    한다") — 좌/우 배치 자체는 그대로 두고 어느 쪽에 누굴 놓을지만 뒤집었다. 내 팀은
    왼쪽 절반(x≈4~46, 자기 골대가 왼쪽 가장자리), 상대 팀은 오른쪽 절반(x≈54~96,
    자기 골대가 오른쪽 가장자리)에 배치해 두 팀의 공격 라인이 중앙선 부근(46~54
    사이)에서 마주보되, x축 구간이 절대 겹치지 않아 서로의 영역을 침범할 수 없다.
    각 팀의 평균 평점(평점 있는 선수 기준)도 같이 계산하고, MVP 선수는 is_mvp=True로
    표시한다. 데이터가 없으면 빈 리스트를 반환해 화면에서는 조용히 섹션이 생략된다."""
    me_players, me_avg = _pitch_players_for_side(
        my_data, spid_name_map, x_transform=lambda rank: 46 - rank * 42)
    opp_players, opp_avg = _pitch_players_for_side(
        your_data, spid_name_map, x_transform=lambda rank: 54 + rank * 42)
    mvp_sp_id = mvp.get("spId") if mvp else None
    mvp_side = mvp.get("side") if mvp else None
    if mvp_sp_id is not None:
        for p in me_players:
            if mvp_side == "me" and p["spId"] == mvp_sp_id:
                p["is_mvp"] = True
        for p in opp_players:
            if mvp_side == "opponent" and p["spId"] == mvp_sp_id:
                p["is_mvp"] = True
    return {
        "me": {"players": me_players, "avg_rating": me_avg},
        "opponent": {"players": opp_players, "avg_rating": opp_avg},
    }


# ✅ 경기 피드백 (신규) — AI 없이, 박스스코어 수치를 정해진 기준(트리거)과 비교해서
# "이렇게 했으면 더 좋았을 것"을 알려주는 규칙 기반 엔진. build_match_boxscore()가
# 이미 만들어둔 상세 지표(me/opponent)를 그대로 재사용하므로 추가 API 호출이 없다.
def _g(box, *keys):
    """중첩 dict에서 안전하게 값 하나를 꺼낸다. 중간에 None/다른 타입이 나오면 조용히 None."""
    cur = box
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def generate_match_feedback(my_box, opponent_box, result, my_goals=None, opp_goals=None):
    """한 매치의 결과(result: '승'/'무'/'패')와 박스스코어를 보고, 여러 트리거를
    "심각도(severity)" 점수로 평가한 뒤 가장 중요한 순서로 최대 3개를 골라 반환한다.
    ⚠️ 2026-09-12 고도화 — 예전에는 트리거 5~7개를 if/elif로 나열하고 코드에 적힌
    순서 그대로 앞의 3개만 보여줬다(중요도와 무관). 지금은 슈팅/패스(스루·롱 패스 포함)/
    수비(태클·차단)/점유율/규율(파울·경고·오프사이드·자책골·퇴장)/스코어 마진까지 훨씬
    많은 지표를 후보로 만들고, 각 후보에 심각도 점수를 매겨 내림차순 정렬 후 상위 3개만
    보여준다. 판정 근거가 될 지표가 아예 없으면(available=False 등) 빈 리스트를 반환해
    화면에서 섹션이 조용히 생략된다.
    my_goals/opp_goals(선택): 스코어를 함께 넘기면 "아슬아슬한 승리"/"큰 점수 차 패배" 같은
    스코어 마진 인지형 피드백도 추가된다(안 넘겨도 나머지 트리거는 그대로 동작)."""
    if not isinstance(my_box, dict) or not my_box.get("available"):
        return []

    def g(*keys):
        return _g(my_box, *keys)

    opp_available = isinstance(opponent_box, dict) and opponent_box.get("available")

    def og(*keys):
        return _g(opponent_box, *keys) if opp_available else None

    my_shoot_total = g("shoot", "total")
    my_shoot_pct = g("shoot", "effective_pct")
    my_pass_pct = g("pass", "total", "pct")
    my_through_try = g("pass", "through", "try")
    my_through_pct = g("pass", "through", "pct")
    my_long_try = g("pass", "long", "try")
    my_long_pct = g("pass", "long", "pct")
    my_tackle_try = g("defence", "tackle", "try")
    my_tackle_pct = g("defence", "tackle", "pct")
    my_block_try = g("defence", "block", "try")
    my_block_pct = g("defence", "block", "pct")
    my_possession = g("extra", "possession")
    my_foul = g("discipline", "foul")
    my_offside = g("discipline", "offside")
    my_yellow = g("discipline", "yellow_cards")
    my_own_goal = g("extra", "own_goal")
    my_red_cards = g("extra", "red_cards")

    opp_shoot_total = og("shoot", "total")
    opp_possession = og("extra", "possession")

    won = result == "승"
    needs_improvement = not won  # 무 또는 패

    candidates = []  # [(severity, text), ...] — severity가 높을수록 먼저 노출

    def add(cond, severity, text):
        if cond:
            candidates.append((severity, text))

    # ── 슈팅 ────────────────────────────────────────────────────────────
    if my_shoot_pct is not None and my_shoot_total and my_shoot_total >= 3:
        if my_shoot_pct < 30:
            add(True, 8 if needs_improvement else 7,
                f"슈팅 유효율이 {my_shoot_pct:.0f}%로 낮았어요. 마무리 정확도를 높이면 "
                f"{'승리에 더 가까워질' if needs_improvement else '더 큰 점수 차로 이길'} 수 있어요.")
        elif my_shoot_pct < 50:
            add(True, 5 if needs_improvement else 4,
                f"슈팅 유효율이 {my_shoot_pct:.0f}%였어요. 마무리 정확도를 높였다면 "
                f"{'승부를 더 유리하게 가져갔을' if needs_improvement else '더 큰 점수 차로 이길'} 수 있었을 거예요.")

    if my_shoot_total is not None and opp_shoot_total is not None:
        diff = opp_shoot_total - my_shoot_total
        if diff >= 8:
            add(True, 9, f"슈팅 시도가 상대보다 많이 적었어요({my_shoot_total} vs {opp_shoot_total}). 공격 전개 자체가 부족했던 것 같아요.")
        elif diff >= 4:
            add(True, 6, f"슈팅 시도가 상대보다 적었어요({my_shoot_total} vs {opp_shoot_total}). 공격 기회를 더 만들었다면 승리에 가까웠을 거예요.")
        elif diff >= 1:
            add(True, 4, f"슈팅 시도가 상대보다 살짝 적었어요({my_shoot_total} vs {opp_shoot_total}). 공격 기회를 조금 더 만들어도 좋을 것 같아요.")
        elif diff <= -4 and needs_improvement:
            add(True, 5, f"슈팅은 상대보다 많았는데({my_shoot_total} vs {opp_shoot_total}) 이기지 못했어요. 만든 기회를 살리는 마무리가 아쉬웠어요.")

    # ── 패스(짧은/스루/롱 패스까지 세분화) ──────────────────────────────
    if my_pass_pct is not None:
        if my_pass_pct < 60:
            add(True, 7, f"패스 성공률이 {my_pass_pct:.0f}%로 많이 낮았어요. 패스 정확도를 높이면 훨씬 안정적으로 경기를 운영할 수 있어요.")
        elif my_pass_pct < 75:
            add(True, 5, f"패스 성공률이 {my_pass_pct:.0f}%로 낮았어요. 패스 정확도를 높이면 더 안정적으로 경기를 운영할 수 있어요.")

    if my_through_try is not None and my_through_try >= 5 and my_through_pct is not None and my_through_pct < 30:
        add(True, 4, f"스루패스 성공률이 {my_through_pct:.0f}%로 낮았어요({my_through_try}회 시도). 타이밍을 조절하면 결정적인 찬스를 더 만들 수 있어요.")

    if my_long_try is not None and my_long_try >= 5 and my_long_pct is not None and my_long_pct < 40:
        add(True, 3, f"롱패스 성공률이 {my_long_pct:.0f}%로 낮았어요. 짧은 패스 위주로 전개하면 볼 소유를 더 안정적으로 지킬 수 있어요.")

    # ── 수비(태클/차단) ──────────────────────────────────────────────────
    if my_tackle_try is not None and my_tackle_try >= 3 and my_tackle_pct is not None:
        if my_tackle_pct < 40:
            add(True, 7, f"태클 성공률이 {my_tackle_pct:.0f}%로 낮았어요. 무리한 태클보다 위치 선정으로 압박하면 실점을 줄일 수 있어요.")
        elif my_tackle_pct < 55:
            add(True, 5, f"태클 성공률이 {my_tackle_pct:.0f}%였어요. 수비 타이밍을 개선하면 실점을 줄일 수 있어요.")

    if my_block_try is not None and my_block_try >= 3 and my_block_pct is not None and my_block_pct < 40:
        add(True, 3, f"슈팅 차단 성공률이 {my_block_pct:.0f}%로 낮았어요. 슈팅 코스를 먼저 막는 수비 위치 선정이 필요해요.")

    # ── 점유율 ──────────────────────────────────────────────────────────
    if my_possession is not None and opp_possession is not None:
        gap = opp_possession - my_possession
        if gap >= 15:
            add(True, 6, f"점유율에서 상대({opp_possession:.0f}% vs {my_possession:.0f}%)에게 크게 밀렸어요. 볼 소유권을 더 가져가면 경기를 주도할 수 있어요.")
        elif gap >= 5:
            add(True, 4 if needs_improvement else 3,
                f"점유율은 상대({opp_possession:.0f}%)에게 내줬"
                + ("지만 이겼어요. 볼 소유까지 가져갔다면 더 압도적인 경기가 됐을 거예요." if won
                   else "어요. 볼 소유권을 더 가져가면 경기를 주도할 수 있어요."))

    # ── 규율/실수(자책골·퇴장·파울·경고·오프사이드) ─────────────────────
    add(bool(my_own_goal), 9, "자책골이 있었어요. 수비 클리어링 상황을 조금 더 신중하게 처리하면 좋을 것 같아요.")
    add(bool(my_red_cards), 8, "퇴장이 있었어요. 무리한 태클/파울을 줄이면 수적 열세를 피할 수 있어요.")
    if my_foul is not None:
        if my_foul >= 8:
            add(True, 6, f"파울이 {my_foul}번으로 많았어요. 무리한 몸싸움을 줄이면 위험한 세트피스 실점을 줄일 수 있어요.")
        elif my_foul >= 5:
            add(True, 4, f"파울이 {my_foul}번으로 다소 많았어요. 무리한 몸싸움을 줄이면 위험한 세트피스 실점을 줄일 수 있어요.")
    if my_yellow is not None and my_yellow >= 3:
        add(True, 3, f"경고가 {my_yellow}번 누적됐어요. 카드 관리를 신경 쓰면 다음 경기 운영에도 유리해요.")
    if my_offside is not None:
        if my_offside >= 3:
            add(True, 5, f"오프사이드가 {my_offside}번이나 나왔어요. 침투 타이밍을 조절하면 득점 기회를 더 살릴 수 있어요.")
        elif my_offside >= 2:
            add(True, 3, f"오프사이드가 {my_offside}번 나왔어요. 침투 타이밍을 조절하면 득점 기회를 더 살릴 수 있어요.")

    # ── 스코어 마진 인지(선택) — my_goals/opp_goals를 넘겼을 때만 동작 ───
    if my_goals is not None and opp_goals is not None:
        margin = my_goals - opp_goals
        if won and margin == 1 and ((my_shoot_pct is not None and my_shoot_pct < 50) or (my_pass_pct is not None and my_pass_pct < 70)):
            add(True, 3, "한 골 차로 아슬아슬하게 승리했어요. 위 지표들을 개선하면 다음엔 더 여유 있게 이길 수 있어요.")
        if needs_improvement and (opp_goals - my_goals) >= 3:
            add(True, 7, f"{opp_goals - my_goals}점 차로 크게 밀렸어요. 전반적인 경기 운영을 점검해볼 필요가 있어요.")

    # ── 심각도 내림차순 정렬 후 상위 3개만 노출 ──────────────────────────
    candidates.sort(key=lambda c: -c[0])
    tips = [text for _, text in candidates[:3]]

    if not tips:
        if won:
            best_stat = None
            if my_shoot_pct is not None and my_shoot_pct >= 70:
                best_stat = f"슈팅 유효율 {my_shoot_pct:.0f}%"
            elif my_pass_pct is not None and my_pass_pct >= 85:
                best_stat = f"패스 성공률 {my_pass_pct:.0f}%"
            suffix = f" ({best_stat})" if best_stat else ""
            tips.append(f"특별히 아쉬운 지표가 안 보여요 — 흠잡을 데 없는 승리였어요!{suffix}")
        else:
            tips.append("특별히 아쉬운 지표는 없었어요 — 골 결정력에서 근소한 차이가 있었던 것 같아요.")

    return tips
