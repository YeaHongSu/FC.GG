"""축구 선수 초성퀴즈용 선수 DB (샘플 10명).

- 운영 시에는 PLAYER_DB에 약 300명까지 확장해서 넣으면 됩니다.
- app.py의 /kakao/playerquiz(또는 미처리 발화 라우팅)에서 사용합니다.

필드(권장)
- id, name_ko, aliases, birth_year, nationality, position, one_liner
- chosung은 비워도 됩니다(없으면 app.py에서 자동 생성).
"""

from __future__ import annotations
from typing import Dict, List

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
            idx = (code - 0xAC00) // 588
            out.append(_CHOSUNG_LIST[idx])
        else:
            out.append(ch)
    return "".join(out)


PLAYER_DB: List[Dict] = [
    {
        "id": "cristiano_ronaldo",
        "name_ko": "크리스티아누 호날두",
        "aliases": ["호날두", "CR7", "Ronaldo", "크호"],
        "chosung": "",
        "birth_year": 1985,
        "nationality": "포르투갈",
        "position": "FW",
        "one_liner": "‘CR7’로 불리며 챔스·리그에서 득점 기록을 쌓아온 포르투갈 레전드 공격수",
    },
    {
        "id": "lionel_messi",
        "name_ko": "리오넬 메시",
        "aliases": ["메시", "Messi", "라풀가", "LaPulga"],
        "chosung": "",
        "birth_year": 1987,
        "nationality": "아르헨티나",
        "position": "FW",
        "one_liner": "바르셀로나의 상징으로 불린 왼발 드리블러, 발롱도르급 커리어로 유명",
    },
    {
        "id": "neymar",
        "name_ko": "네이마르",
        "aliases": ["네이마르 주니오르", "네이마르 Jr", "Neymar", "Ney"],
        "chosung": "",
        "birth_year": 1992,
        "nationality": "브라질",
        "position": "FW",
        "one_liner": "산투스·바르사·PSG에서 화제를 모은 브라질 스타, 화려한 개인기 이미지가 강함",
    },
    {
        "id": "kylian_mbappe",
        "name_ko": "킬리안 음바페",
        "aliases": ["음바페", "Mbappe", "Mbappé"],
        "chosung": "",
        "birth_year": 1998,
        "nationality": "프랑스",
        "position": "FW",
        "one_liner": "월드컵에서도 주목받은 프랑스 공격수, 폭발적인 스피드와 침투가 트레이드마크",
    },
    {
        "id": "erling_haaland",
        "name_ko": "엘링 홀란",
        "aliases": ["홀란", "홀란드", "Haaland"],
        "chosung": "",
        "birth_year": 2000,
        "nationality": "노르웨이",
        "position": "FW",
        "one_liner": "박스 안 결정력과 피지컬로 유명한 노르웨이 스트라이커, 득점 기계 이미지",
    },
    {
        "id": "son_heung_min",
        "name_ko": "손흥민",
        "aliases": ["손흥민", "Son", "쏘니"],
        "chosung": "",
        "birth_year": 1992,
        "nationality": "대한민국",
        "position": "FW",
        "one_liner": "프리미어리그에서 활약한 한국 대표 공격수, 양발 슈팅·역습 침투로 유명",
    },
    {
        "id": "robert_lewandowski",
        "name_ko": "로베르트 레반도프스키",
        "aliases": ["레반도프스키", "레반", "Lewandowski", "Lewy"],
        "chosung": "",
        "birth_year": 1988,
        "nationality": "폴란드",
        "position": "FW",
        "one_liner": "바이에른·바르사에서 득점력을 뽐낸 폴란드 골잡이, 박스 안 움직임이 강점",
    },
    {
        "id": "kevin_de_bruyne",
        "name_ko": "케빈 더브라위너",
        "aliases": ["더브라위너", "KDB", "De Bruyne", "DeBruyne"],
        "chosung": "",
        "birth_year": 1991,
        "nationality": "벨기에",
        "position": "MF",
        "one_liner": "‘KDB’로 불리는 맨체스터 시티의 핵심 미드필더, 킬패스와 크로스가 상징",
    },
    {
        "id": "luka_modric",
        "name_ko": "루카 모드리치",
        "aliases": ["모드리치", "Modric", "Modrić"],
        "chosung": "",
        "birth_year": 1985,
        "nationality": "크로아티아",
        "position": "MF",
        "one_liner": "레알 마드리드 중원의 상징, 탈압박·템포 조절로 유명한 크로아티아 미드필더",
    },
    {
        "id": "virgil_van_dijk",
        "name_ko": "버질 반다이크",
        "aliases": ["반다이크", "Van Dijk", "VanDijk", "VVD"],
        "chosung": "",
        "birth_year": 1991,
        "nationality": "네덜란드",
        "position": "DF",
        "one_liner": "리버풀 수비를 리빌드한 센터백으로 평가받는 네덜란드 수비수, 공중볼·리더십",
    },
]


def all_players() -> List[Dict]:
    return list(PLAYER_DB)
