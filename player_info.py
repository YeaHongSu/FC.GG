"""축구 선수 초성퀴즈용 선수 DB.

- PLAYER_DB에 선수 dict를 채우면 됩니다.
- app.py의 /kakao/playerquiz에서 사용합니다.

필드(권장)
- id, name_ko, aliases, birth_year, nationality, position, one_liner
- chosung은 없어도 됩니다(없으면 app.py에서 자동 생성).
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
        "aliases": ["호날두", "CR7", "Ronaldo"],
        "chosung": "",  # 비워도 됨(자동 생성)
        "birth_year": 1985,
        "nationality": "포르투갈",
        "position": "FW",
        "one_liner": "‘CR7’로 불리는 포르투갈 공격수, 강력한 득점력과 피지컬로 상징되는 선수",
    },
    {
        "id": "lionel_messi",
        "name_ko": "리오넬 메시",
        "aliases": ["메시", "Messi", "LaPulga", "라풀가"],
        "chosung": "",
        "birth_year": 1987,
        "nationality": "아르헨티나",
        "position": "FW",
        "one_liner": "바르셀로나 ‘라 마시아’ 출신으로 떠오르는, 왼발 드리블·창의성이 상징인 선수",
    },
    {
        "id": "neymar",
        "name_ko": "네이마르",
        "aliases": ["네이마르 주니오르", "네이마르 Jr", "Neymar", "Ney"],
        "chosung": "",
        "birth_year": 1992,
        "nationality": "브라질",
        "position": "FW",
        "one_liner": "브라질 특유의 개인기·쇼맨십 이미지로 유명한 스타 윙어/공격수",
    },
    {
        "id": "kylian_mbappe",
        "name_ko": "킬리안 음바페",
        "aliases": ["음바페", "Mbappe", "Mbappé"],
        "chosung": "",
        "birth_year": 1998,
        "nationality": "프랑스",
        "position": "FW",
        "one_liner": "폭발적인 스피드와 뒷공간 침투로 떠오르는 프랑스 대표 공격수",
    },
    {
        "id": "erling_haaland",
        "name_ko": "엘링 홀란",
        "aliases": ["홀란", "Haaland", "홀란드"],
        "chosung": "",
        "birth_year": 2000,
        "nationality": "노르웨이",
        "position": "FW",
        "one_liner": "강한 피지컬과 박스 안 결정력으로 유명한 노르웨이 스트라이커",
    },
    {
        "id": "son_heung_min",
        "name_ko": "손흥민",
        "aliases": ["손흥민", "Son", "쏘니"],
        "chosung": "",
        "birth_year": 1992,
        "nationality": "대한민국",
        "position": "FW",
        "one_liner": "양발 슈팅과 빠른 침투 이미지가 강한 대한민국 대표 공격수",
    },
    {
        "id": "robert_lewandowski",
        "name_ko": "로베르트 레반도프스키",
        "aliases": ["레반도프스키", "레반", "Lewandowski", "Lewy"],
        "chosung": "",
        "birth_year": 1988,
        "nationality": "폴란드",
        "position": "FW",
        "one_liner": "박스 안 움직임·결정력이 상징인 폴란드 대표 골잡이",
    },
    {
        "id": "kevin_de_bruyne",
        "name_ko": "케빈 더브라위너",
        "aliases": ["더브라위너", "데브라위너", "KDB", "DeBruyne", "De Bruyne"],
        "chosung": "",
        "birth_year": 1991,
        "nationality": "벨기에",
        "position": "MF",
        "one_liner": "‘KDB’로 불리며 킬패스·크로스·중거리로 떠오르는 플레이메이커",
    },
    {
        "id": "luka_modric",
        "name_ko": "루카 모드리치",
        "aliases": ["모드리치", "Modric", "Modrić"],
        "chosung": "",
        "birth_year": 1985,
        "nationality": "크로아티아",
        "position": "MF",
        "one_liner": "중원에서 템포 조절과 탈압박 이미지가 강한 크로아티아 레전드급 미드필더",
    },
    {
        "id": "virgil_van_dijk",
        "name_ko": "버질 반다이크",
        "aliases": ["반다이크", "VanDijk", "Van Dijk", "VVD"],
        "chosung": "",
        "birth_year": 1991,
        "nationality": "네덜란드",
        "position": "DF",
        "one_liner": "공중볼·대인수비·수비 리더 이미지로 유명한 네덜란드 센터백",
    },
]


def all_players() -> List[Dict]:
    return list(PLAYER_DB)
