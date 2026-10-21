"""Team-approved 2025 Q4 sales-industry grouping transcribed from the supplied table.

The labels are analytical categories for the 62 industries with observed Q4
estimated sales. They do not create new categories in the 10-column dong
consumption source, and an industry sale is not a dong consumption transaction.
"""

from __future__ import annotations

import pandas as pd


# (공통 그룹, 소비 항목, 원천 추정매출 업종명). Keep the supplied row order.
GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("외식", "음식", ("한식음식점", "중식음식점", "일식음식점", "양식음식점", "제과점",
                    "패스트푸드점", "치킨전문점", "분식전문점", "커피-음료")),
    ("유흥", "주점", ("호프-간이주점",)),
    ("식료품", "식료품", ("슈퍼마켓", "편의점", "미곡판매", "육류판매", "수산물판매", "청과상", "반찬가게")),
    ("의료", "의료비", ("일반의원", "치과의원", "한의원", "의약품", "의료기기")),
    ("교육", "교육", ("일반교습학원", "외국어학원", "예술학원")),
    ("의류·잡화", "의류·신발", ("일반의류", "신발", "가방", "안경", "시계및귀금속", "섬유제품")),
    ("생활용품", "생활용품", ("화장품", "가구", "가전제품", "철물점", "인테리어", "조명용품",
                         "문구", "화초", "애완동물", "컴퓨터및주변장치판매", "핸드폰")),
    ("여가·오락", "여가·문화", ("PC방", "노래방", "당구장", "골프연습장", "스포츠클럽",
                          "스포츠 강습", "서적", "완구", "운동/경기용품")),
    ("숙박", "숙박", ("여관",)),
    ("생활서비스", "미용·관리", ("미용실", "네일숍", "피부관리실")),
    ("생활서비스", "수리·세탁", ("세탁소", "가전제품수리")),
    ("부동산", "부동산서비스", ("부동산중개업",)),
    ("교통", "교통", ("자동차수리", "자동차미용", "자전거 및 기타운송장비")),
    ("분석 제외", "—", ("전자상거래업",)),
)
EXPECTED_COUNTS = (9, 1, 7, 5, 3, 6, 11, 9, 1, 3, 2, 1, 3, 1)


def classification_frame(source: pd.DataFrame) -> pd.DataFrame:
    """Map every observed industry exactly once; fail if source names drift."""
    names = source[["서비스_업종_코드", "서비스_업종_코드_명"]].drop_duplicates()
    if len(names) != 62 or names["서비스_업종_코드"].duplicated().any() or names["서비스_업종_코드_명"].duplicated().any():
        raise ValueError("Expected 62 unique code/name pairs in Q4 sales")
    if tuple(len(items) for _, _, items in GROUPS) != EXPECTED_COUNTS:
        raise ValueError("The final classification row counts changed")
    labels = [name for _, _, items in GROUPS for name in items]
    if len(labels) != 62 or len(set(labels)) != 62:
        raise ValueError("The final classification must cover 62 distinct industries")
    missing = set(names["서비스_업종_코드_명"]) - set(labels)
    extra = set(labels) - set(names["서비스_업종_코드_명"])
    if missing or extra:
        raise ValueError(f"Industry mapping mismatch: missing={sorted(missing)}, extra={sorted(extra)}")
    code_by_name = dict(zip(names["서비스_업종_코드_명"], names["서비스_업종_코드"]))
    rows = [
        {"서비스_업종_코드": code_by_name[name], "서비스_업종_코드_명": name,
         "공통_그룹": group, "소비_항목": item, "분석_포함": group != "분석 제외"}
        for group, item, items in GROUPS for name in items
    ]
    return pd.DataFrame(rows)
