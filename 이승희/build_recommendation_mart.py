# -*- coding: utf-8 -*-
"""SpotFit 창업자 맞춤 상권 추천 통합 데이터 마트 및 파생변수 생성 파이프라인.
- STEP 2: 상권(1,650개) × 62개 업종 × 배후지표(인구/소비/변화지표) 다차원 결합
- STEP 3: 창업 추천 특화 파생변수 도출 (수요/경쟁 백분위, 기회 갭 지수, 사분면 유형, 안정성, 종합 점수)
"""
import json
import math
import sys
from pathlib import Path
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_COMMERCIAL = PROJECT_DIR / "data" / "raw" / "상권"
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = PROJECT_DIR / "report_latest"
LEE_DIR = PROJECT_DIR / "이승희"

print("=" * 70)
print("[STEP 2 & 3] 창업자 맞춤 상권 추천 통합 마트 빌드 파이프라인 시작")
print("=" * 70)

# 1. 상권 영역 마스터 로드 (1,650개 상권)
print("[1/7] 상권 영역 마스터 로드 및 WGS84 좌표 변환 중...")
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:5181", "EPSG:4326", always_xy=True)

df_area = pd.read_csv(RAW_COMMERCIAL / "OA-15560_영역_상권.csv", encoding="utf-8")

# 행정동명 클렌징 (? -> ·)
df_area["행정동_코드_명"] = df_area["행정동_코드_명"].astype(str).str.replace("?", "·", regex=False)
df_area["상권_코드_명"] = df_area["상권_코드_명"].astype(str).str.replace("?", "·", regex=False)

area_master = df_area[[
    "상권_구분_코드", "상권_구분_코드_명", "상권_코드", "상권_코드_명",
    "엑스좌표_값", "와이좌표_값", "자치구_코드", "자치구_코드_명", "행정동_코드", "행정동_코드_명"
]].copy().rename(columns={"자치구_코드_명": "자치구_명", "행정동_코드_명": "행정동_명"})

# EPSG:5181 -> WGS84 위경도 변환
lngs, lats = transformer.transform(area_master["엑스좌표_값"].values, area_master["와이좌표_값"].values)
area_master["위도"] = np.round(lats, 6)
area_master["경도"] = np.round(lngs, 6)

print(f"  -> 상권 마스터: 총 {len(area_master):,}개 상권 매핑 및 WGS84 위경도 변환 완료")

# 2. 2025년 상권 추정매출 로드 및 집계
print("[2/7] 2025년 상권 추정매출 로드 및 분기 집계 중...")
sales_cols = [
    "기준_년분기_코드", "상권_코드", "서비스_업종_코드", "서비스_업종_코드_명",
    "당월_매출_금액", "당월_매출_건수", "주중_매출_금액", "주말_매출_금액",
    "시간대_00~06_매출_금액", "시간대_06~11_매출_금액", "시간대_11~14_매출_금액",
    "시간대_14~17_매출_금액", "시간대_17~21_매출_금액", "시간대_21~24_매출_금액",
    "남성_매출_금액", "여성_매출_금액",
    "연령대_10_매출_금액", "연령대_20_매출_금액", "연령대_30_매출_금액",
    "연령대_40_매출_금액", "연령대_50_매출_금액", "연령대_60_이상_매출_금액"
]
df_sales = pd.read_csv(RAW_COMMERCIAL / "OA-15572_추정매출_상권.csv", encoding="utf-8", usecols=sales_cols)

# 2025 연간 매출 합계 계산
sales_annual = df_sales.groupby(["상권_코드", "서비스_업종_코드"]).agg(
    연간_매출_금액=("당월_매출_금액", "sum"),
    연간_매출_건수=("당월_매출_건수", "sum"),
    관측_분기_수=("기준_년분기_코드", "nunique")
).reset_index()

# 2025Q4 (최신 분기) 매출 데이터 필터
sales_q4 = df_sales[df_sales["기준_년분기_코드"] == 20254].copy()

# 2025Q3 매출 (성장률 계산용)
sales_q3 = df_sales[df_sales["기준_년분기_코드"] == 20253][["상권_코드", "서비스_업종_코드", "당월_매출_금액"]].rename(
    columns={"당월_매출_금액": "Q3_매출_금액"}
)
sales_q4 = sales_q4.merge(sales_q3, on=["상권_코드", "서비스_업종_코드"], how="left")
raw_growth = np.where(
    sales_q4["Q3_매출_금액"] > 0,
    ((sales_q4["당월_매출_금액"] - sales_q4["Q3_매출_금액"]) / sales_q4["Q3_매출_금액"]) * 100,
    0.0
)
sales_q4["전분기대비_매출성장률"] = np.clip(raw_growth, -100.0, 500.0).round(1)

# 연간 매출 조인
sales_q4 = sales_q4.merge(sales_annual, on=["상권_코드", "서비스_업종_코드"], how="left")

# 세부 소비 패턴 파생 (주말 비중, 연령대 비중, 피크 시간대)
sales_q4["주말_매출_비중"] = np.where(
    sales_q4["당월_매출_금액"] > 0,
    (sales_q4["주말_매출_금액"] / sales_q4["당월_매출_금액"]) * 100,
    0.0
).round(1)

gender_sum = sales_q4["남성_매출_금액"] + sales_q4["여성_매출_금액"]
sales_q4["여성_매출_비중"] = np.where(
    gender_sum > 0,
    (sales_q4["여성_매출_금액"] / gender_sum) * 100,
    50.0
).round(1)

age_cols = ["연령대_10_매출_금액", "연령대_20_매출_금액", "연령대_30_매출_금액", "연령대_40_매출_금액", "연령대_50_매출_금액", "연령대_60_이상_매출_금액"]
age_sum = sales_q4[age_cols].sum(axis=1)

sales_q4["2030_매출_비중"] = np.where(
    age_sum > 0,
    ((sales_q4["연령대_20_매출_금액"] + sales_q4["연령대_30_매출_금액"]) / age_sum) * 100,
    0.0
).round(1)

# 주요 소비 연령대 판별
age_names = ["10대", "20대", "30대", "40대", "50대", "60대이상"]
sales_q4["주요_소비_연령대"] = sales_q4[age_cols].apply(
    lambda r: age_names[np.argmax(r.values)] if r.sum() > 0 else "미상", axis=1
)

# 피크 시간대 판별 (점심 11~14, 오후 14~17, 저녁 17~21, 심야 21~24, 오전 06~11, 새벽 00~06)
time_cols = [
    "시간대_00~06_매출_금액", "시간대_06~11_매출_금액", "시간대_11~14_매출_금액",
    "시간대_14~17_매출_금액", "시간대_17~21_매출_금액", "시간대_21~24_매출_금액"
]
time_names = ["심야(00~06)", "아침(06~11)", "점심(11~14)", "오후(14~17)", "저녁(17~21)", "야간(21~24)"]
sales_q4["피크_시간대"] = sales_q4[time_cols].apply(
    lambda r: time_names[np.argmax(r.values)] if r.sum() > 0 else "종일", axis=1
)

print(f"  -> 2025Q4 매출 데이터: {len(sales_q4):,}개 상권-업종 행 가공 완료")

# 3. 2025Q4 점포 데이터 로드 및 결합
print("[3/7] 점포 데이터 및 개폐업율 결합 중...")
store_cols = [
    "기준_년분기_코드", "상권_코드", "서비스_업종_코드",
    "전체_점포_수", "일반_점포_수", "프랜차이즈_점포_수",
    "개업_점포_수", "폐업_점포_수"
]
df_store = pd.read_csv(RAW_COMMERCIAL / "OA-15577_점포_상권.csv", encoding="utf-8", usecols=store_cols)
store_q4 = df_store[df_store["기준_년분기_코드"] == 20254].copy()

# 파생: 폐업률, 개업률, 프랜차이즈 비중
store_q4["폐업률"] = np.where(
    store_q4["전체_점포_수"] > 0,
    (store_q4["폐업_점포_수"] / store_q4["전체_점포_수"]) * 100,
    0.0
).round(2)
store_q4["개업률"] = np.where(
    store_q4["전체_점포_수"] > 0,
    (store_q4["개업_점포_수"] / store_q4["전체_점포_수"]) * 100,
    0.0
).round(2)
store_q4["프랜차이즈_비율"] = np.where(
    store_q4["전체_점포_수"] > 0,
    (store_q4["프랜차이즈_점포_수"] / store_q4["전체_점포_수"]) * 100,
    0.0
).round(1)

# 매출과 점포 결합
mart = sales_q4.merge(
    store_q4[["상권_코드", "서비스_업종_코드", "전체_점포_수", "일반_점포_수", "프랜차이즈_점포_수", "개업_점포_수", "폐업_점포_수", "폐업률", "개업률", "프랜차이즈_비율"]],
    on=["상권_코드", "서비스_업종_코드"],
    how="inner"
)

# 4. 상권 변화지표 및 영업기간 결합
print("[4/7] 상권변화지표 및 영업기간 결합 중...")
df_change = pd.read_csv(RAW_COMMERCIAL / "OA-15576_상권변화지표_상권.csv", encoding="utf-8")
change_q4 = df_change[df_change["기준_년분기_코드"] == 20254][
    ["상권_코드", "상권_변화_지표_명", "운영_영업_개월_평균", "폐업_영업_개월_평균"]
].drop_duplicates("상권_코드")

mart = mart.merge(change_q4, on="상권_코드", how="left")
mart["상권_변화_지표_명"] = mart["상권_변화_지표_명"].fillna("정체")
mart["운영_영업_개월_평균"] = mart["운영_영업_개월_평균"].fillna(mart["운영_영업_개월_평균"].median())
mart["폐업_영업_개월_평균"] = mart["폐업_영업_개월_평균"].fillna(mart["폐업_영업_개월_평균"].median())

# 5. 배후 인구 및 집객시설 결합 (상권 단위)
print("[5/7] 배후 인구(유동/직장/상주) 및 시설 결합 중...")
df_flow = pd.read_csv(RAW_COMMERCIAL / "OA-15568_길단위인구_상권.csv", encoding="utf-8")
flow_q4 = df_flow[df_flow["기준_년분기_코드"] == 20254][["상권_코드", "총_유동인구_수"]].drop_duplicates("상권_코드")

df_work = pd.read_csv(RAW_COMMERCIAL / "OA-15569_직장인구_상권.csv", encoding="utf-8")
work_q4 = df_work[df_work["기준_년분기_코드"] == 20254][["상권_코드", "총_직장_인구_수"]].drop_duplicates("상권_코드")

df_stay = pd.read_csv(RAW_COMMERCIAL / "OA-15584_상주인구_상권.csv", encoding="utf-8")
stay_q4 = df_stay[df_stay["기준_년분기_코드"] == 20254][["상권_코드", "총_상주인구_수"]].drop_duplicates("상권_코드")

df_fac = pd.read_csv(RAW_COMMERCIAL / "OA-15580_집객시설_상권.csv", encoding="utf-8")
fac_q4 = df_fac[df_fac["기준_년분기_코드"] == 20254][["상권_코드", "집객시설_수"]].drop_duplicates("상권_코드")

mart = mart.merge(flow_q4, on="상권_코드", how="left")
mart = mart.merge(work_q4, on="상권_코드", how="left")
mart = mart.merge(stay_q4, on="상권_코드", how="left")
mart = mart.merge(fac_q4, on="상권_코드", how="left")

mart["총_유동인구_수"] = mart["총_유동인구_수"].fillna(0)
mart["총_직장_인구_수"] = mart["총_직장_인구_수"].fillna(0)
mart["총_상주인구_수"] = mart["총_상주인구_수"].fillna(0)
mart["집객시설_수"] = mart["집객시설_수"].fillna(0)

# 상권 마스터 정보(이름, 위치, 행정동, 자치구) 조인
mart = mart.merge(area_master, on="상권_코드", how="left")

# 6. STEP 3: 창업 추천 특화 핵심 파생변수 산출
print("[6/7] STEP 3 파생변수(수요/경쟁 백분위, 기회갭, 사분면, 점수) 계산 중...")

# (1) 점포당 월 추정매출액 (만원 단위: 3개월 분기매출 / 점포수 / 3 / 10000)
mart["점포당_월평균매출_만원"] = np.where(
    mart["전체_점포_수"] > 0,
    (mart["당월_매출_금액"] / mart["전체_점포_수"] / 3 / 10000).round(1),
    0.0
)

# (2) 건당 평균 결제금액 (객단가, 원 단위)
mart["건당_결제단가_원"] = np.where(
    mart["당월_매출_건수"] > 0,
    (mart["당월_매출_금액"] / mart["당월_매출_건수"]).round(0).astype(int),
    0
)

# (3) 동일 업종 내 백분위 순위 (수요 백분위, 경쟁 백분위) - 벡터화 계산
mart["수요_백분위수"] = (mart.groupby("서비스_업종_코드")["당월_매출_금액"].rank(pct=True) * 100).round(1)
mart["경쟁_백분위수"] = (mart.groupby("서비스_업종_코드")["전체_점포_수"].rank(pct=True) * 100).round(1)
mart["점포당매출_백분위수"] = (mart.groupby("서비스_업종_코드")["점포당_월평균매출_만원"].rank(pct=True) * 100).round(1)

# (4) 기회 갭 지수 (Opportunity Gap Index = 수요 백분위 - 경쟁 백분위, 범위: -100 ~ +100)
mart["기회_갭_지수"] = (mart["수요_백분위수"] - mart["경쟁_백분위수"]).round(1)

# (5) 수요-경쟁 2x2 사분면 유형 분류
# - 블루오션 (기회형): 수요 >= 50 & 경쟁 < 50 (높은 매출 규모 대비 경쟁 점포가 적어 신규 진입 매력도 최상)
# - 격전지 (스타형): 수요 >= 50 & 경쟁 >= 50 (대형 메가상권, 수요 폭발적이나 치열한 경쟁 감내 필요)
# - 틈새시장 (안정형): 수요 < 50 & 경쟁 < 50 (동네 로컬 골목상권, 단골 위주 안정적 소자본 창업)
# - 레드오션 (위험형): 수요 < 50 & 경쟁 >= 50 (매출 파이는 작은데 점포만 과밀, 폐업 위험 매우 높음)
def classify_quadrant(row):
    d = row["수요_백분위수"]
    c = row["경쟁_백분위수"]
    if d >= 50.0 and c < 50.0:
        return "블루오션(기회형)"
    elif d >= 50.0 and c >= 50.0:
        return "격전지(스타형)"
    elif d < 50.0 and c < 50.0:
        return "틈새시장(안정형)"
    else:
        return "레드오션(위험형)"

mart["사분면_유형"] = mart.apply(classify_quadrant, axis=1)

# (6) 상권 생존 안정성 점수 (0 ~ 100점)
# - 폐업률 감점: 폐업률 0% -> 50점 만점, 폐업률 15% 이상 -> 0점
closure_score = np.clip(50 - (mart["폐업률"] * 3.33), 0, 50)
# - 평균 운영개월수 가점: 120개월(10년) 기준 30점 만점
tenure_score = np.clip((mart["운영_영업_개월_평균"] / 120.0) * 30, 0, 30)
# - 상권변화지표 가점: 상권확장 20점, 다이나믹 15점, 정체 10점, 상권쇠퇴 0점
change_weight = {"상권확장": 20, "다이나믹": 15, "정체": 10, "상권쇠퇴": 0}
change_score = mart["상권_변화_지표_명"].map(change_weight).fillna(10)

mart["안정성_점수"] = (closure_score + tenure_score + change_score).round(1)

# (7) 배후 유동인구 지수 (전체 서울 상권 내 백분위 0 ~ 100)
mart["유동인구_백분위수"] = (mart["총_유동인구_수"].rank(pct=True) * 100).round(1)

# (8) SpotFit 종합 창업 추천 점수 (0 ~ 100점 Score)
# 가중치: 기회 갭 지수(35%) + 점포당 매출(25%) + 안정성(20%) + 배후 유동인구(20%)
# 기회갭을 0~100으로 리스케일: (기회갭 + 100) / 2
gap_normalized = (mart["기회_갭_지수"] + 100.0) / 2.0
mart["SpotFit_추천점수"] = (
    (gap_normalized * 0.35) +
    (mart["점포당매출_백분위수"] * 0.25) +
    (mart["안정성_점수"] * 0.20) +
    (mart["유동인구_백분위수"] * 0.20)
).round(1)

# 7. 최종 데이터 저장 및 요약 메트릭 생성
print("[7/7] 최종 통합 마트 저장 및 검증...")

target_cols = [
    "상권_코드", "상권_코드_명", "상권_구분_코드_명", "자치구_명", "행정동_명", "행정동_코드",
    "서비스_업종_코드", "서비스_업종_코드_명",
    # 핵심 파생 지표
    "SpotFit_추천점수", "사분면_유형", "기회_갭_지수",
    "수요_백분위수", "경쟁_백분위수", "점포당매출_백분위수",
    "점포당_월평균매출_만원", "건당_결제단가_원",
    # 매출 및 성장성
    "당월_매출_금액", "당월_매출_건수", "연간_매출_금액", "전분기대비_매출성장률",
    # 경쟁 및 점포
    "전체_점포_수", "일반_점포_수", "프랜차이즈_점포_수", "프랜차이즈_비율", "개업률", "폐업률",
    # 안정성 및 상권변화
    "안정성_점수", "상권_변화_지표_명", "운영_영업_개월_평균", "폐업_영업_개월_평균",
    # 고객 페르소나 및 패턴
    "주요_소비_연령대", "2030_매출_비중", "주말_매출_비중", "여성_매출_비중", "피크_시간대",
    # 배후 지표 및 좌표
    "총_유동인구_수", "총_직장_인구_수", "총_상주인구_수", "집객시설_수",
    "엑스좌표_값", "와이좌표_값", "위도", "경도"
]

missing = [c for c in target_cols if c not in mart.columns]
if missing:
    print(f"⚠️ Missing columns in mart: {missing}")

final_cols = [c for c in target_cols if c in mart.columns]
mart_final = mart[final_cols].sort_values("SpotFit_추천점수", ascending=False)

# Parquet 및 CSV 저장
parquet_path = PROCESSED_DIR / "상권_추천_통합마트_2025.parquet"
csv_path = PROCESSED_DIR / "상권_추천_통합마트_2025.csv"

mart_final.to_parquet(parquet_path, index=False)
print(f"  -> Parquet 저장 완료: {parquet_path} ({len(mart_final):,}행, {len(final_cols)}열)")
mart_final.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"  -> Full CSV 저장 완료: {csv_path}")

# 샘플 상위 5,000행 CSV (경량 공유용)
sample_csv_path = PROCESSED_DIR / "상권_추천_통합마트_2025_샘플5000.csv"
mart_final.head(5000).to_csv(sample_csv_path, index=False, encoding="utf-8-sig")

# 사분면별 분포 및 기초 통계 검증 출력
quad_counts = mart_final["사분면_유형"].value_counts()
print("\n" + "=" * 50)
print("📊 사분면 유형별 상권-업종 분포:")
for q_name, cnt in quad_counts.items():
    pct = (cnt / len(mart_final)) * 100
    print(f"  - {q_name:<16}: {cnt:>6,}건 ({pct:5.1f}%)")

print("\n📈 SpotFit 종합 추천점수 5수치 요약:")
print(mart_final["SpotFit_추천점수"].describe().round(1))

# 주요 업종별 Top 3 추천 상권 추출 샘플 검증
key_industries = ["CS100010", "CS100001", "CS100005"] # 커피-음료, 한식음식점, 제과점
print("\n🏆 주요 업종별 Top 추천 상권 예시:")
for ind_code in key_industries:
    sub = mart_final[mart_final["서비스_업종_코드"] == ind_code].head(3)
    ind_name = sub.iloc[0]["서비스_업종_코드_명"]
    print(f"\n[{ind_name}] 추천 상위 3곳:")
    for _, row in sub.iterrows():
        print(f"  • {row['상권_코드_명']} ({row['자치구_명']} {row['행정동_명']}) | 추천점수: {row['SpotFit_추천점수']}점 | 사분면: {row['사분면_유형']} | 점포당월매출: {row['점포당_월평균매출_만원']:,.0f}만원 | 기회갭: {row['기회_갭_지수']:+.1f}")

# JSON 요약 데이터 내보내기 (대시보드 및 리포트 시각화용)
summary_export = {
    "total_rows": len(mart_final),
    "total_commercial_districts": mart_final["상권_코드"].nunique(),
    "total_industries": mart_final["서비스_업종_코드"].nunique(),
    "quadrant_distribution": quad_counts.to_dict(),
    "score_stats": {
        "mean": round(float(mart_final["SpotFit_추천점수"].mean()), 2),
        "median": round(float(mart_final["SpotFit_추천점수"].median()), 2),
        "std": round(float(mart_final["SpotFit_추천점수"].std()), 2),
        "min": round(float(mart_final["SpotFit_추천점수"].min()), 2),
        "max": round(float(mart_final["SpotFit_추천점수"].max()), 2),
        "q25": round(float(mart_final["SpotFit_추천점수"].quantile(0.25)), 2),
        "q75": round(float(mart_final["SpotFit_추천점수"].quantile(0.75)), 2),
    },
    "opportunity_gap_stats": {
        "mean": round(float(mart_final["기회_갭_지수"].mean()), 2),
        "median": round(float(mart_final["기회_갭_지수"].median()), 2),
        "std": round(float(mart_final["기회_갭_지수"].std()), 2),
    },
    "top_recommendations_by_industry": {}
}

# 62개 전체 업종별 Top 5 추천 상권 요약
for ind_code, group in mart_final.groupby("서비스_업종_코드"):
    ind_name = group.iloc[0]["서비스_업종_코드_명"]
    top5 = group.head(5)[[
        "상권_코드", "상권_코드_명", "상권_구분_코드_명", "자치구_명", "행정동_명",
        "SpotFit_추천점수", "사분면_유형", "기회_갭_지수", "점포당_월평균매출_만원",
        "폐업률", "안정성_점수", "주요_소비_연령대", "2030_매출_비중", "피크_시간대",
        "전체_점포_수", "당월_매출_금액", "위도", "경도"
    ]].to_dict(orient="records")
    summary_export["top_recommendations_by_industry"][ind_name] = top5

for out_dir in [REPORT_DIR, LEE_DIR]:
    json_path = out_dir / "recommendation_mart_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_export, f, ensure_ascii=False, indent=2)
    print(f"  -> 요약 JSON 저장 완료: {json_path}")

print("=" * 70)
print("🎉 [STEP 2 & 3] 데이터 마트 및 파생변수 구축 완료!")
print("=" * 70)
