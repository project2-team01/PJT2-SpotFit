import pandas as pd
import numpy as np
import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUT_DATA_DIR = DATA_DIR / "processed" / "eda_reclassified"
OUT_IMG_DIR = BASE_DIR / "images" / "eda_reclassified"

OUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_IMG_DIR.mkdir(parents=True, exist_ok=True)

print("Starting Reclassified EDA 2025...")

# 1. Load Industry Mapping
mapping_csv = BASE_DIR / "C:/Users/USER/.gemini/antigravity-ide/brain/4f70ab43-e0e4-48bf-8ee5-4db007d4aa3c/scratch/industry_mapping.csv"
if not mapping_csv.exists():
    mapping_csv = Path(r"C:\Users\USER\.gemini\antigravity-ide\brain\4f70ab43-e0e4-48bf-8ee5-4db007d4aa3c\scratch\industry_mapping.csv")

mapping_df = pd.read_csv(mapping_csv, encoding="utf-8-sig")
ind_map = dict(zip(mapping_df["code"], mapping_df["common_group"]))
ind_submap = dict(zip(mapping_df["code"], mapping_df["spend_item"]))

# 2. Load Consumption Data (OA-22166)
cons_df = pd.read_csv(RAW_DIR / "OA-22166_소비_행정동.csv", encoding="utf-8-sig")

item_cols = [
    "식료품_지출_총금액", "의류_신발_지출_총금액", "생활용품_지출_총금액",
    "의료비_지출_총금액", "교통_지출_총금액", "교육_지출_총금액",
    "유흥_지출_총금액", "여가_문화_지출_총금액", "기타_지출_총금액", "음식_지출_총금액"
]

cons_dong = cons_df.groupby(["행정동_코드", "행정동_코드_명"])[["지출_총금액"] + item_cols].sum().reset_index()

for col in item_cols:
    ratio_col = col.replace("_지출_총금액", "_비중")
    cons_dong[ratio_col] = cons_dong[col] / cons_dong["지출_총금액"]

ratio_cols = [col.replace("_지출_총금액", "_비중") for col in item_cols]
cons_dong["최대_항목_비중"] = cons_dong[ratio_cols].max(axis=1)
cons_dong["최대_항목"] = cons_dong[ratio_cols].idxmax(axis=1).str.replace("_비중", "")

# Flag 24 outlier dongs (>= 70%)
cons_dong["is_special_hub"] = cons_dong["최대_항목_비중"] >= 0.70

print(f"Total Dongs: {len(cons_dong)}")
print(f"Normal Dongs (일반 상권군): {(~cons_dong['is_special_hub']).sum()}")
print(f"Special Hub Dongs (특수 허브 상권군): {cons_dong['is_special_hub'].sum()}")

# 3. Load Commercial District Sales (OA-15572) and Store (OA-15577)
sales_df = pd.read_csv(RAW_DIR / "상권" / "OA-15572_추정매출_상권.csv", encoding="utf-8-sig")
store_df = pd.read_csv(RAW_DIR / "상권" / "OA-15577_점포_상권.csv", encoding="utf-8-sig")
area_df = pd.read_csv(RAW_DIR / "상권" / "OA-15560_영역_상권.csv", encoding="utf-8-sig")

# Map common group
sales_df["공통_그룹"] = sales_df["서비스_업종_코드"].map(ind_map)
sales_df["세부_분류"] = sales_df["서비스_업종_코드"].map(ind_submap)

store_df["공통_그룹"] = store_df["서비스_업종_코드"].map(ind_map)

# Filter out '분석 제외' (전자상거래업)
sales_clean = sales_df[sales_df["공통_그룹"] != "분석 제외"].copy()
store_clean = store_df[store_df["공통_그룹"] != "분석 제외"].copy()

# 4. Analyze Commercial Sales by Common Group
group_sales = sales_clean.groupby("공통_그룹")["당월_매출_금액"].sum().reset_index()
group_sales["매출_비중"] = group_sales["당월_매출_금액"] / group_sales["당월_매출_금액"].sum() * 100

# Store counts (Q4 2025)
q4_stores = store_clean[store_clean["기준_년분기_코드"] == 20254]

# Column 7 is total stores, 11 is open, 13 is close
store_col = store_clean.columns[7]
open_col = store_clean.columns[11]
close_col = store_clean.columns[13]

group_stores = q4_stores.groupby("공통_그룹")[store_col].sum().reset_index()
group_stores.rename(columns={store_col: "점포_수"}, inplace=True)
group_stores["점포_비중"] = group_stores["점포_수"] / group_stores["점포_수"].sum() * 100

# Open/Close stores in 2025
open_stores = store_clean.groupby("공통_그룹")[open_col].sum().reset_index()
open_stores.rename(columns={open_col: "개업_점포_수"}, inplace=True)

close_stores = store_clean.groupby("공통_그룹")[close_col].sum().reset_index()
close_stores.rename(columns={close_col: "폐업_점포_수"}, inplace=True)

group_summary = group_sales.merge(group_stores, on="공통_그룹", how="left")
group_summary = group_summary.merge(open_stores, on="공통_그룹", how="left")
group_summary = group_summary.merge(close_stores, on="공통_그룹", how="left")
group_summary["연간매출(조원)"] = group_summary["당월_매출_금액"] / 1e12
group_summary["점포당_평균연매출(백만원)"] = (group_summary["당월_매출_금액"] / group_summary["점포_수"]) / 1e6
group_summary["순증감_점포수"] = group_summary["개업_점포_수"] - group_summary["폐업_점포_수"]

group_summary = group_summary.sort_values("당월_매출_금액", ascending=False)
group_summary.to_csv(OUT_DATA_DIR / "01_공통그룹별_상권매출_점포현황.csv", index=False, encoding="utf-8-sig")

# 5. Map Sales to Dong Level via Area Mapping
# OA-15560 has '상권_코드' and '행정동_코드'
sales_with_dong = sales_clean.merge(area_df[["상권_코드", "행정동_코드"]], on="상권_코드", how="left")

# Aggregate Sales by Dong and Common Group
dong_group_sales = sales_with_dong.groupby(["행정동_코드", "공통_그룹"])["당월_매출_금액"].sum().unstack(fill_value=0).reset_index()

# Rename columns to indicate sales
dong_group_sales.columns = [f"상권매출_{col}" if col != "행정동_코드" else col for col in dong_group_sales.columns]

# Merge Consumption and Sales at Dong Level
merged_dong = cons_dong.merge(dong_group_sales, on="행정동_코드", how="left").fillna(0)

# 6. Consumption Gap Calculation for 401 Normal Dongs vs 24 Special Hub Dongs
# Compare:
# 외식: 음식_지출_총금액 vs 상권매출_외식
# 식료품: 식료품_지출_총금액 vs 상권매출_식료품
# 의류·잡화: 의류_신발_지출_총금액 vs 상권매출_의류·잡화
# 생활용품: 생활용품_지출_총금액 vs 상권매출_생활용품
# 의료: 의료비_지출_총금액 vs 상권매출_의료
# 교육: 교육_지출_총금액 vs 상권매출_교육
# 유흥: 유흥_지출_총금액 vs 상권매출_유흥
# 여가·오락: 여가_문화_지출_총금액 vs 상권매출_여가·오락

compare_pairs = [
    ("외식", "음식_지출_총금액", "상권매출_외식"),
    ("식료품", "식료품_지출_총금액", "상권매출_식료품"),
    ("의류·잡화", "의류_신발_지출_총금액", "상권매출_의류·잡화"),
    ("생활용품", "생활용품_지출_총금액", "상권매출_생활용품"),
    ("의료", "의료비_지출_총금액", "상권매출_의료"),
    ("교육", "교육_지출_총금액", "상권매출_교육"),
    ("유흥", "유흥_지출_총금액", "상권매출_유흥"),
    ("여가·오락", "여가_문화_지출_총금액", "상권매출_여가·오락")
]

for grp_name, spend_c, sales_c in compare_pairs:
    if sales_c in merged_dong.columns:
        merged_dong[f"소비갭_{grp_name}"] = merged_dong[spend_c] - merged_dong[sales_c]
        merged_dong[f"소비배율_{grp_name}"] = merged_dong[spend_c] / (merged_dong[sales_c] + 1e6)

merged_dong.to_csv(OUT_DATA_DIR / "02_행정동_투트랙_소비갭_패널.csv", index=False, encoding="utf-8-sig")

# 7. Summary Stats for Normal vs Special Hub
normal_dongs = merged_dong[~merged_dong["is_special_hub"]]
special_dongs = merged_dong[merged_dong["is_special_hub"]]

summary_stats = {
    "구분": ["일반 상권군 (Normal)", "특수 허브 상권군 (Special Hub)"],
    "행정동 수": [len(normal_dongs), len(special_dongs)],
    "연간 총지출(조원)": [round(normal_dongs["지출_총금액"].sum() / 1e12, 2), round(special_dongs["지출_총금액"].sum() / 1e12, 2)],
    "지출 비중(%)": [round(normal_dongs["지출_총금액"].sum() / merged_dong["지출_총금액"].sum() * 100, 1), round(special_dongs["지출_총금액"].sum() / merged_dong["지출_총금액"].sum() * 100, 1)],
    "동평균 총지출(억원)": [round(normal_dongs["지출_총금액"].mean() / 1e8, 1), round(special_dongs["지출_총금액"].mean() / 1e8, 1)],
    "동중앙값 총지출(억원)": [round(normal_dongs["지출_총금액"].median() / 1e8, 1), round(special_dongs["지출_총금액"].median() / 1e8, 1)],
    "음식지출 비중 중앙값(%)": [round(normal_dongs["음식_비중"].median() * 100, 1), round(special_dongs["음식_비중"].median() * 100, 1)],
    "식료품 비중 중앙값(%)": [round(normal_dongs["식료품_비중"].median() * 100, 1), round(special_dongs["식료품_비중"].median() * 100, 1)],
    "상권 외식매출 중앙값(억원)": [round(normal_dongs["상권매출_외식"].median() / 1e8, 1), round(special_dongs["상권매출_외식"].median() / 1e8, 1)]
}

summary_df = pd.DataFrame(summary_stats)
summary_df.to_csv(OUT_DATA_DIR / "03_투트랙_비교_요약.csv", index=False, encoding="utf-8-sig")

# 8. Top Opportunity Dongs by Common Group in Normal Dongs
opportunity_dongs = {}
for grp_name, _, _ in compare_pairs:
    gap_col = f"소비갭_{grp_name}"
    if gap_col in normal_dongs.columns:
        top_dongs = normal_dongs.sort_values(gap_col, ascending=False)[["행정동_코드", "행정동_코드_명", gap_col, f"소비배율_{grp_name}"]].head(5)
        opportunity_dongs[grp_name] = top_dongs.to_dict(orient="records")

with open(OUT_DATA_DIR / "04_일반상권_공통그룹별_유망동.json", "w", encoding="utf-8") as f:
    json.dump(opportunity_dongs, f, ensure_ascii=False, indent=2)

print("Reclassified EDA finished successfully!")
print("Saved files to:", OUT_DATA_DIR)
