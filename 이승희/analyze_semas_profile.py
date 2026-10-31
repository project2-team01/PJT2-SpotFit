# -*- coding: utf-8 -*-
"""STEP 1 소상공인시장진흥공단 서울시 상가(상권)정보 데이터 프로파일링 & EDA 집계 스크립트."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
SPOTFIT_REPO = PROJECT_DIR.parent / "Spotfit" / "seoul-commercial-analysis"
SEMAS_FILE = (
    SPOTFIT_REPO
    / "data"
    / "raw"
    / "semas"
    / "extracted"
    / "semas_store_20251231"
    / "소상공인시장진흥공단_상가(상권)정보_서울_202512.csv"
)
OUTPUT_DIR = PROJECT_DIR / "report_latest"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Reading: {SEMAS_FILE}")
if not SEMAS_FILE.exists():
    print(f"Error: {SEMAS_FILE} not found!")
    sys.exit(1)

# Read full CSV with UTF-8
df = pd.read_csv(SEMAS_FILE, encoding="utf-8", low_memory=False)
total_rows, total_cols = df.shape
print(f"Total Rows: {total_rows:,}, Total Columns: {total_cols}")

# 영문 표준 컬럼명 매핑 (인코딩 독립적 처리)
col_rename = {
    df.columns[0]: "store_id",        # 상가업소번호
    df.columns[1]: "store_name",      # 상호명
    df.columns[2]: "branch_name",     # 지점명
    df.columns[3]: "macro_code",      # 상권업종대분류코드
    df.columns[4]: "macro_name",      # 상권업종대분류명
    df.columns[5]: "mid_code",        # 상권업종중분류코드
    df.columns[6]: "mid_name",        # 상권업종중분류명
    df.columns[7]: "sub_code",        # 상권업종소분류코드
    df.columns[8]: "sub_name",        # 상권업종소분류명
    df.columns[9]: "std_code",        # 표준산업분류코드
    df.columns[10]: "std_name",       # 표준산업분류명
    df.columns[11]: "sido_code",      # 시도코드
    df.columns[12]: "sido_name",      # 시도명
    df.columns[13]: "sigungu_code",   # 시군구코드
    df.columns[14]: "sigungu_name",   # 시군구명 (구)
    df.columns[15]: "dong_code",      # 행정동코드
    df.columns[16]: "dong_name",      # 행정동명
    df.columns[17]: "bjdong_code",    # 법정동코드
    df.columns[18]: "bjdong_name",    # 법정동명
    df.columns[24]: "jibun_addr",     # 지번주소
    df.columns[26]: "road_name",      # 도로명
    df.columns[30]: "bldg_name",      # 건물명
    df.columns[31]: "road_addr",      # 도로명주소
    df.columns[35]: "floor",          # 층정보
    df.columns[37]: "lon",            # 경도
    df.columns[38]: "lat",            # 위도
}
original_cols = list(df.columns)
df = df.rename(columns=col_rename)

# 1. Basic Profiling
null_counts = df.isnull().sum()
null_ratio = {}
for orig_col, new_col in col_rename.items():
    null_ratio[orig_col] = round(float(null_counts.get(new_col, 0) / total_rows * 100), 2)

unique_store_ids = int(df["store_id"].nunique())
id_duplicates = int(total_rows - unique_store_ids)

# 좌표 결측 및 서울 영역(BBox: 경도 126.7~127.3, 위도 37.4~37.7) 검증
coord_null = int(df["lon"].isnull().sum() + df["lat"].isnull().sum())
valid_coords = df["lon"].between(126.7, 127.3) & df["lat"].between(37.4, 37.7)
invalid_coords_count = int((~valid_coords).sum())

# 2. Regional Distribution (Gu & Dong)
gu_counts = {str(k): int(v) for k, v in df["sigungu_name"].value_counts().items()}
dong_counts = {str(k): int(v) for k, v in df["dong_name"].value_counts().head(25).items()}

# 3. Industry Category Hierarchy
macro_counts = {str(k): int(v) for k, v in df["macro_name"].value_counts().items()}
mid_counts = {str(k): int(v) for k, v in df["mid_name"].value_counts().head(20).items()}
sub_counts = {str(k): int(v) for k, v in df["sub_name"].value_counts().head(25).items()}

# 4. Cross Analysis: Gu x Macro Industry
gu_macro = pd.crosstab(df["sigungu_name"], df["macro_name"])
gu_macro_pct = (gu_macro.div(gu_macro.sum(axis=1), axis=0) * 100).round(2)
gu_macro_data = {
    "gu_names": [str(x) for x in gu_macro.index],
    "macro_cols": [str(x) for x in gu_macro.columns],
    "counts": [[int(v) for v in row] for row in gu_macro.values],
    "pcts": [[float(v) for v in row] for row in gu_macro_pct.values],
}

# 5. Coffee / Cafe specific analysis
cafe_mask = df["sub_name"].astype(str).str.contains("커피|카페", na=False) | df["store_name"].astype(str).str.contains("카페|커피|COFFEE|CAFE", case=False, na=False)
cafe_df = df[cafe_mask]
cafe_gu_counts = {str(k): int(v) for k, v in cafe_df["sigungu_name"].value_counts().items()}
cafe_dong_counts = {str(k): int(v) for k, v in cafe_df["dong_name"].value_counts().head(15).items()}

# 6. Restaurant subcategory breakdown (음식 대분류)
food_df = df[df["macro_name"] == "음식"]
food_sub_counts = {str(k): int(v) for k, v in food_df["sub_name"].value_counts().head(15).items()}

# 7. Franchise / Chain keywords frequency
brands = {
    "CU (편의점)": "CU",
    "GS25 (편의점)": "GS25",
    "스타벅스 (카페)": "스타벅스",
    "이디야 (카페)": "이디야",
    "메가MGC커피": "메가커피|메가엠지씨",
    "컴포즈커피": "컴포즈",
    "투썸플레이스": "투썸",
    "빽다방": "빽다방",
    "세븐일레븐": "세븐일레븐",
    "올리브영 (H&B)": "올리브영",
    "파리바게뜨 (베이커리)": "파리바게",
    "배스킨라빈스 (아이스크림)": "배스킨라빈스|베스킨라빈스",
    "다이소 (생활용품)": "다이소",
    "BHC (치킨)": "BHC|bhc",
    "교촌치킨": "교촌",
    "맘스터치 (버거)": "맘스터치",
    "맥도날드": "맥도날드",
    "버거킹": "버거킹",
}
brand_counts_clean = {}
store_name_series = df["store_name"].fillna("").astype(str)
for label, pattern in brands.items():
    cnt = int(store_name_series.str.contains(pattern, case=False, regex=True).sum())
    brand_counts_clean[label] = cnt

brand_counts_clean = dict(sorted(brand_counts_clean.items(), key=lambda x: x[1], reverse=True))

# 8. Floor information distribution
floor_counts = {str(k): int(v) for k, v in df["floor"].fillna("미기재").value_counts().head(10).items()}

# 9. Shannon Diversity Index per Gu
def shannon_diversity(series):
    counts = series.value_counts()
    p = counts / counts.sum()
    return float(-np.sum(p * np.log(p)))

gu_diversity = df.groupby("sigungu_name")["sub_name"].apply(shannon_diversity).round(3).to_dict()
gu_diversity = {str(k): float(v) for k, v in sorted(gu_diversity.items(), key=lambda x: x[1], reverse=True)}

# 10. Sample Points for Map Preview (1,500 points stratified by Gu)
sample_df = df.groupby("sigungu_name").sample(n=60, random_state=42)
map_points = []
for _, row in sample_df.iterrows():
    if pd.notnull(row["lat"]) and pd.notnull(row["lon"]):
        map_points.append({
            "name": str(row["store_name"]),
            "gu": str(row["sigungu_name"]),
            "dong": str(row["dong_name"]),
            "cat_macro": str(row["macro_name"]),
            "cat_sub": str(row["sub_name"]),
            "lat": round(float(row["lat"]), 5),
            "lng": round(float(row["lon"]), 5),
            "floor": str(row["floor"]) if pd.notnull(row["floor"]) else "-"
        })

profile_data = {
    "generated_at": "2026-10-31",
    "dataset_info": {
        "file_name": "소상공인시장진흥공단_상가(상권)정보_서울_202512.csv",
        "reference_period": "2025년 12월 31일 기준 (2025Q4 스냅숏)",
        "source": "공공데이터포털 / 소상공인시장진흥공단 (SEMAS S01)",
        "total_stores": int(total_rows),
        "total_columns": int(total_cols),
        "unique_stores": int(unique_store_ids),
        "id_duplicate_count": int(id_duplicates),
        "invalid_coords_count": int(invalid_coords_count),
    },
    "column_null_ratios": null_ratio,
    "gu_counts": gu_counts,
    "dong_counts": dong_counts,
    "macro_counts": macro_counts,
    "mid_counts": mid_counts,
    "sub_counts": sub_counts,
    "food_sub_counts": food_sub_counts,
    "cafe_gu_counts": cafe_gu_counts,
    "cafe_dong_counts": cafe_dong_counts,
    "cafe_total": int(len(cafe_df)),
    "gu_macro_matrix": gu_macro_data,
    "brand_counts": brand_counts_clean,
    "floor_counts": floor_counts,
    "gu_diversity": gu_diversity,
    "map_points_sample": map_points[:1200]
}

out_file = OUTPUT_DIR / "semas_profile_data.json"
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(profile_data, f, ensure_ascii=False, indent=2)

print(f"Data profile successfully exported to: {out_file}")
