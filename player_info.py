"""player_info.py

축구 선수 퀴즈용 데이터.

사용 방식
1) PLAYER_DB 리스트에 선수 dict를 300명 정도 채워 넣습니다.
2) app.py(카카오 스킬)에서 이 파일을 import 해서 랜덤으로 1명을 뽑습니다.

필수 필드(권장)
- id: 문자열(고유)
- name_ko: 한국어 표기
- aliases: 별칭/약칭 리스트(정답 인정용)
- chosung: 초성 문자열(공백 포함 가능)
- birth_year: 출생년도(int)
- nationality: 국적(문자열)
- position: 포지션(예: FW/MF/DF/GK)
- one_liner: 나무위키 한줄 소개 스타일(힌트4)

주의
- one_liner는 "창의적인 드리블" 같은 범용 문구보다, 떠올리기 쉬운 키워드(별명/대표 클럽/대표 업적/역할)를 1~2개 넣는 걸 추천합니다.
- 사실성 이슈를 피하려면, 너무 구체적 수상/횟수 대신 널리 알려진 식별자(별명, 대표 팀, 포지션, 플레이 특징)를 권장합니다.
"""

from __future__ import annotations

from typing import Dict, List


# -----------------------------------------------------------------------------
# 초성 생성 유틸 (name_ko에서 자동 생성하고 싶을 때 사용)
# -----------------------------------------------------------------------------

_CHOSUNG_LIST = [
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
]


def make_chosung(text: str) -> str:
    """한글 문자열에서 초성만 추출. 공백/영문/숫자는 그대로 둠."""
    out: List[str] = []
    for ch in text:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            # (초성*21*28) + (중성*28) + 종성 + 0xAC00
            idx = (code - 0xAC00) // 588
            out.append(_CHOSUNG_LIST[idx])
        else:
            out.append(ch)
    return "".join(out)


# -----------------------------------------------------------------------------
# 선수 DB (여기에 300명 채우기)
# -----------------------------------------------------------------------------

PLAYER_DB: List[Dict] = [
    {
        "id": "cristiano_ronaldo",
        "name_ko": "크리스티아누 호날두",
        "aliases": ["호날두", "CR7"],
        "chosung": "ㅋㄹㅅㅌㅇㄴ ㅎㄴㄷ",
        "birth_year": 1985,
        "nationality": "포르투갈",
        "position": "FW",
        "one_liner": "포르투갈의 'CR7'로 불리며 득점력과 자기관리로 유명한 공격수",
    },
    {
        "id": "lionel_messi",
        "name_ko": "리오넬 메시",
        "aliases": ["메시", "La Pulga"],
        "chosung": "ㄹㅇㄴ ㄴ ㅁㅅ",
        "birth_year": 1987,
        "nationality": "아르헨티나",
        "position": "FW",
        "one_liner": "'메시'라는 이름 자체가 상징이 된, 압도적인 볼 컨트롤과 창조성을 가진 공격수",
    },
    {
        "id": "neymar",
        "name_ko": "네이마르",
        "aliases": ["네이마르 주니오르", "네이마르 Jr", "Ney"],
        "chosung": "ㄴㅇㅁㄹ",
        "birth_year": 1992,
        "nationality": "브라질",
        "position": "FW",
        "one_liner": "브라질 특유의 개인기와 쇼맨십으로 화제를 모은 스타 플레이어",
    },
]


def all_players() -> List[Dict]:
    """외부에서 안전하게 사용할 수 있도록 복사본 반환."""
    return list(PLAYER_DB)
