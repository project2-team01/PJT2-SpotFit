# -*- coding: utf-8 -*-
"""STEP 1 & STEP 2 결합 심화 EDA 및 다차원 통계 집계 스크립트.
- 파이차트 배제용 데이터 생성
- 기술통계량(평균, 중위수, 표준편차, 사분위수, 왜도, 첨도)
- 교차표(Crosstab) 및 피봇테이블(Pivot)
- 자치구별 업종 입지계수(LQ)
- 서울시 62개 서비스업종 1:N 매핑 및 상권/행정동 2계층 결합
- 상권 점포수 vs 매출액 상관분석
"""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

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
SALES_FILE = (
    SPOTFIT_REPO
    / "data"
    / "raw"
    / "seoul"
    / "extracted"
    / "seoul_sales_trdar_2025"
    / "서울시 상권분석서비스(추정매출-상권)_2025년.csv"
)
AREA_INFO_FILE = list((PROJECT_DIR / "data" / "raw").rglob("*15560*"))[0]
OUTPUT_DIR = PROJECT_DIR / "report_latest"

print(f"[1/4] Reading SEMAS file: {SEMAS_FILE}")
semas_df = pd.read_csv(SEMAS_FILE, encoding="utf-8", low_memory=False)

# 컬럼 리네임
col_rename = {
    semas_df.columns[0]: "store_id",
    semas_df.columns[1]: "store_name",
    semas_df.columns[2]: "branch_name",
    semas_df.columns[3]: "macro_code",
    semas_df.columns[4]: "macro_name",
    semas_df.columns[5]: "mid_code",
    semas_df.columns[6]: "mid_name",
    semas_df.columns[7]: "sub_code",
    semas_df.columns[8]: "sub_name",
    semas_df.columns[11]: "sido_code",
    semas_df.columns[12]: "sido_name",
    semas_df.columns[13]: "sigungu_code",
    semas_df.columns[14]: "sigungu_name",
    semas_df.columns[15]: "dong_code",
    semas_df.columns[16]: "dong_name",
    semas_df.columns[35]: "floor",
    semas_df.columns[37]: "lon",
    semas_df.columns[38]: "lat",
}
semas_df = semas_df.rename(columns=col_rename)
total_stores = len(semas_df)

# 권역 매핑 정의
REGION_MAP = {
    '강남구': '동남권', '서초구': '동남권', '송파구': '동남권', '강동구': '동남권',
    '종로구': '도심권', '중구': '도심권', '용산구': '도심권',
    '마포구': '서북권', '서대문구': '서북권', '은평구': '서북권',
    '영등포구': '서남권', '구로구': '서남권', '금천구': '서남권', '동작구': '서남권', '관악구': '서남권', '강서구': '서남권', '양천구': '서남권',
    '성동구': '동북권', '광진구': '동북권', '동대문구': '동북권', '중랑구': '동북권', '성북구': '동북권', '강북구': '동북권', '도봉구': '동북권', '노원구': '동북권'
}
semas_df['region'] = semas_df['sigungu_name'].map(REGION_MAP).fillna('기타')

# -------------------------------------------------------------
# [TAB 1] 소상공인 데이터 심층 프로파일링 & 통계
# -------------------------------------------------------------
print("[2/4] Processing Tab 1 statistics...")

# 1. 기술통계량 (구별 점포수 & 행정동별 점포수)
gu_store_counts = semas_df['sigungu_name'].value_counts()
dong_store_counts = semas_df['dong_name'].value_counts()

def calc_descriptive_stats(series):
    q25, q75 = float(np.percentile(series, 25)), float(np.percentile(series, 75))
    return {
        "count": int(len(series)),
        "mean": round(float(np.mean(series)), 2),
        "std": round(float(np.std(series, ddof=1)), 2),
        "median": round(float(np.median(series)), 2),
        "min": int(np.min(series)),
        "max": int(np.max(series)),
        "q25": round(q25, 2),
        "q75": round(q75, 2),
        "iqr": round(q75 - q25, 2),
        "skewness": round(float(stats.skew(series)), 3),
        "kurtosis": round(float(stats.kurtosis(series)), 3),
    }

gu_desc_stats = calc_descriptive_stats(gu_store_counts.values)
dong_desc_stats = calc_descriptive_stats(dong_store_counts.values)

# 자치구별 행정동 점포수 박스플롯용 분포 통계 (25개 구 각각의 동 단위 분포)
dong_by_gu = semas_df.groupby(['sigungu_name', 'dong_name']).size().reset_index(name='count')
gu_dong_boxplot = {}
for gu, group in dong_by_gu.groupby('sigungu_name'):
    vals = group['count'].values
    gu_dong_boxplot[gu] = {
        "min": int(np.min(vals)),
        "q25": round(float(np.percentile(vals, 25)), 1),
        "median": round(float(np.median(vals)), 1),
        "q75": round(float(np.percentile(vals, 75)), 1),
        "max": int(np.max(vals)),
        "dong_count": int(len(vals)),
        "total_stores": int(np.sum(vals))
    }
# 정렬 (점포수 내림차순)
gu_dong_boxplot = dict(sorted(gu_dong_boxplot.items(), key=lambda x: x[1]['total_stores'], reverse=True))

# 2. 교차표 및 피봇테이블 (자치구 x 10대 대분류)
gu_macro_ct = pd.crosstab(semas_df['sigungu_name'], semas_df['macro_name'])
gu_macro_pct = (gu_macro_ct.div(gu_macro_ct.sum(axis=1), axis=0) * 100).round(2)

# 권역 x 10대 대분류 피봇
region_macro_ct = pd.crosstab(semas_df['region'], semas_df['macro_name'])
region_macro_pct = (region_macro_ct.div(region_macro_ct.sum(axis=1), axis=0) * 100).round(2)

# 층정보 분류 (단순화: 1층, 2층, 지하1층, 3층이상, 미기재)
def simplify_floor(val):
    if pd.isnull(val) or val == "미기재":
        return "미기재"
    s = str(val).strip()
    if s in ["1", "1층", "지상1층"]:
        return "1층"
    elif s in ["2", "2층", "지상2층"]:
        return "2층"
    elif "지하" in s or s in ["-1", "B1", "b1", "지하1층"]:
        return "지하1층"
    elif s in ["3", "4", "5", "6", "7", "8", "9", "10"] or any(f"{i}층" in s for i in range(3, 11)):
        return "3층 이상"
    return "기타"

semas_df['floor_simple'] = semas_df['floor'].apply(simplify_floor)
floor_macro_ct = pd.crosstab(semas_df['macro_name'], semas_df['floor_simple'])
floor_macro_pct = (floor_macro_ct.div(floor_macro_ct.sum(axis=1), axis=0) * 100).round(2)

# 3. 입지계수 (Location Quotient, LQ) 계산
# LQ = (e_i / e) / (E_i / E)
seoul_macro_total = semas_df['macro_name'].value_counts()
lq_matrix = {}
for gu in gu_macro_ct.index:
    lq_matrix[gu] = {}
    gu_total = gu_store_counts[gu]
    for macro in gu_macro_ct.columns:
        gu_macro_val = gu_macro_ct.loc[gu, macro]
        seoul_macro_val = seoul_macro_total[macro]
        lq = (gu_macro_val / gu_total) / (seoul_macro_val / total_stores)
        lq_matrix[gu][macro] = round(float(lq), 3)

# -------------------------------------------------------------
# [TAB 2] 서울시 상권 62개 업종 결합 및 점포-매출 분석
# -------------------------------------------------------------
print("[3/4] Processing Tab 2 Seoul Commercial 결합...")

# 1. 서울시 상권분석 62개 업종 매핑 사전 (소상공인 소분류 -> 서울시 62개 업종)
# 전체 62개 업종 키워드 기반 정밀 매핑 맵 구축
MAPPING_RULES = {
    "한식음식점": ["한식", "백반", "국밥", "찌개", "구이", "삼겹살", "돼지", "소고기", "곱창", "막창", "족발", "보쌈", "갈비", "불고기", "감자탕", "해물탕", "아구", "칼국수", "수제비", "냉면", "샤브샤브", "닭볶음", "추어탕", "오리", "삼계탕", "쌈밥", "한정식", "기사식당", "설렁탕", "곰탕"],
    "중식음식점": ["중식", "중국", "짜장", "짬뽕", "탕수육", "마라", "양꼬치", "딤섬"],
    "일식음식점": ["일식", "초밥", "스시", "회", "사시미", "돈가스", "우동", "라멘", "참치", "이자카야", "덮밥", "가츠"],
    "양식음식점": ["양식", "이탈리안", "파스타", "피자", "스테이크", "레스토랑", "샐러드", "브런치", "패밀리레스토랑"],
    "제과점": ["제과", "빵", "베이커리", "도넛", "케이크", "디저트", "떡", "한과"],
    "패스트푸드점": ["패스트푸드", "버거", "샌드위치", "토스트", "핫도그"],
    "치킨전문점": ["치킨", "통닭", "닭강정"],
    "분식전문점": ["분식", "김밥", "떡볶이", "순대", "튀김", "만두", "라면"],
    "호프-간이주점": ["호프", "맥주", "주점", "포차", "술집", "바(BAR)", "와인", "위스키", "생맥주", "이자카야"],
    "커피-음료": ["카페", "커피", "생과일", "주스", "차", "밀크티", "디저트카페", "베이커리카페", "빙수"],
    
    # 도소매업
    "슈퍼마켓": ["슈퍼마켓", "식료품", "마트", "농수산"],
    "편의점": ["편의점", "CVS"],
    "컴퓨터및주변장치판매": ["컴퓨터", "주변기기", "노트북"],
    "핸드폰": ["핸드폰", "휴대폰", "통신", "스마트폰"],
    "문구": ["문구", "사무용품", "팬시"],
    "서적": ["서적", "서점", "책"],
    "화장품": ["화장품", "뷰티", "향수", "화장품 소매"],
    "일반의류": ["의류", "옷", "패션", "여성의류", "남성의류", "아동복", "청바지"],
    "신발": ["신발", "제화", "구두", "운동화"],
    "가방": ["가방", "핸드백"],
    "안경": ["안경", "선글라스", "렌즈"],
    "시계및귀금속": ["귀금속", "보석", "시계", "주얼리", "금은방"],
    "의약품": ["약국", "한약국"],
    "의료기기": ["의료기기", "보청기"],
    "운동/경기용품": ["스포츠용품", "운동용품", "골프용품", "낚시"],
    "화초": ["꽃", "화원", "플라워", "화초", "식물"],
    "가구": ["가구", "침대", "소파", "수납장"],
    "가전제품": ["가전", "전자제품", "에어컨"],
    "철물점": ["철물", "공구", "건재"],
    "조명용품": ["조명", "전등"],
    "인테리어": ["인테리어", "도배", "장판", "커튼", "블라인드"],
    "미곡판매": ["쌀", "미곡"],
    "육류판매": ["정육점", "축산물", "육류"],
    "수산물판매": ["수산물", "생선", "건어물"],
    "청과상": ["과일", "청과", "야채", "채소"],
    "반찬가게": ["반찬"],
    "애완동물": ["애완동물", "반려동물", "펫숍", "동물병원"],
    "자전거 및 기타운송장비": ["자전거", "오토바이", "바이크"],
    "완구": ["완구", "장난감"],
    "섬유제품": ["원단", "직물", "침구", "이불"],
    "전자상거래업": ["전자상거래", "통신판매", "쇼핑몰"],

    # 서비스업
    "일반교습학원": ["입시", "보습", "단과", "학원", "교습", "공부방", "독서실"],
    "외국어학원": ["외국어", "어학원", "영어", "일본어", "중국어"],
    "예술학원": ["미술", "음악", "피아노", "무용", "연기"],
    "스포츠 강습": ["태권도", "유도", "검도", "수영"],
    "일반의원": ["일반의원", "내과", "이비인후과", "안과", "피부과", "정형외과", "성형외과", "소아과"],
    "치과의원": ["치과", "치과의원"],
    "한의원": ["한의원", "한방병원"],
    "당구장": ["당구", "당구장"],
    "골프연습장": ["골프연습", "스크린골프"],
    "PC방": ["PC방", "인터넷카페"],
    "노래방": ["노래방", "코인노래"],
    "미용실": ["미용실", "헤어", "바버샵"],
    "네일숍": ["네일", "네일아트", "패디"],
    "피부관리실": ["피부관리", "에스테틱", "스파", "마사지"],
    "세탁소": ["세탁소", "빨래방", "크린토피아", "세탁"],
    "가전제품수리": ["수리", "AS센터", "전자수리"],
    "부동산중개업": ["부동산", "공인중개사"],
    "여관": ["모텔", "여관", "게스트하우스", "호스텔"],
    "자동차수리": ["카센터", "자동차정비", "타이어", "오토바이수리"],
    "자동차미용": ["세차", "광택", "틴팅", "썬팅"],
    "스포츠클럽": ["헬스", "피트니스", "필라테스", "요가", "크로스핏"]
}

# 62개 역매핑 함수
def map_to_62_service(sub_name, store_name):
    target = f"{sub_name} {store_name}"
    for s_name, keywords in MAPPING_RULES.items():
        for kw in keywords:
            if kw in target:
                return s_name
    return "기타서비스"

# 매핑 실행 (표본 2만개 분석 및 전체 대분류 추정)
print("Mapping SEMAS subcategories to Seoul 62 service codes...")
sub_to_62 = {}
for sub in semas_df['sub_name'].unique():
    sub_to_62[sub] = map_to_62_service(str(sub), "")

semas_df['service_62'] = semas_df['sub_name'].map(sub_to_62)
mapped_62_counts = semas_df['service_62'].value_counts().head(20).to_dict()

# 2. 서울시 상권 추정매출(K01) 로드
print(f"Reading Seoul sales data: {SALES_FILE}")
sales_cols = ['기준_년분기_코드', '상권_구분_코드_명', '상권_코드', '상권_코드_명', '서비스_업종_코드_명', '당월_매출_금액', '당월_매출_건수']
sales_df = pd.read_csv(SALES_FILE, encoding='cp949', usecols=sales_cols)
# 2025년 최신 분기 (2025Q4) 우선 필터
sales_2025q4 = sales_df[sales_df['기준_년분기_코드'] == 20254]
if len(sales_2025q4) == 0:
    latest_q = sales_df['기준_년분기_코드'].max()
    sales_2025q4 = sales_df[sales_df['기준_년분기_코드'] == latest_q]

# 상권별 매출 집계
trdar_sales = sales_2025q4.groupby(['상권_코드', '상권_코드_명', '상권_구분_코드_명']).agg(
    total_sales=('당월_매출_금액', 'sum'),
    total_tx=('당월_매출_건수', 'sum'),
    industry_count=('서비스_업종_코드_명', 'nunique')
).reset_index()

# 3. 상권 영역 마스터(OA-15560)와 결합
print(f"Reading area master: {AREA_INFO_FILE}")
area_df = pd.read_csv(AREA_INFO_FILE, encoding='utf-8')
area_map = area_df[['상권_코드', '자치구_코드_명', '행정동_코드', '행정동_코드_명', '영역_면적']].drop_duplicates('상권_코드')

trdar_merged = pd.merge(trdar_sales, area_map, on='상권_코드', how='left')
trdar_merged['area_m2'] = trdar_merged['영역_면적'].fillna(0)

# 행정동별 소상공인 점포수 매핑 (동코드 앞 8자리 기준)
semas_df['dong_cd_8'] = semas_df['dong_code'].astype(str).str[:8]
dong_semas_cnt = semas_df.groupby('dong_cd_8').size().to_dict()

# 행정동별 서울시 상권 매출 롤업
dong_sales_rollup = trdar_merged.groupby(['행정동_코드', '행정동_코드_명', '자치구_코드_명']).agg(
    trdar_count=('상권_코드', 'count'),
    total_sales=('total_sales', 'sum'),
    total_tx=('total_tx', 'sum'),
    total_area=('area_m2', 'sum')
).reset_index()

# 행정동 단위 점포수 vs 매출 결합 데이터프레임
dong_sales_rollup['dong_cd_str'] = dong_sales_rollup['행정동_코드'].astype(str).str[:8]
dong_sales_rollup['semas_stores'] = dong_sales_rollup['dong_cd_str'].map(dong_semas_cnt).fillna(0).astype(int)

# 유효 데이터 필터링 (점포수 > 0 및 매출 > 0)
valid_dong = dong_sales_rollup[(dong_sales_rollup['semas_stores'] > 0) & (dong_sales_rollup['total_sales'] > 0)]

# 4. 상관분석 (Correlation Analysis)
pearson_r, pearson_p = stats.pearsonr(valid_dong['semas_stores'], valid_dong['total_sales'])
spearman_r, spearman_p = stats.spearmanr(valid_dong['semas_stores'], valid_dong['total_sales'])

# 회귀선 기울기 & 절편 (y = ax + b)
slope, intercept, r_val, p_val, std_err = stats.linregress(valid_dong['semas_stores'], valid_dong['total_sales'] / 1e8)

# 상권 구분별 피봇 요약 (골목상권, 발달상권, 전통시장, 관광특구)
trdar_type_pivot = trdar_merged.groupby('상권_구분_코드_명').agg(
    trdar_count=('상권_코드', 'count'),
    mean_sales=('total_sales', lambda x: round(np.mean(x) / 1e8, 2)),
    median_sales=('total_sales', lambda x: round(np.median(x) / 1e8, 2)),
    sum_sales_trillion=('total_sales', lambda x: round(np.sum(x) / 1e12, 2)),
    mean_area=('area_m2', lambda x: round(np.mean(x), 1))
).reset_index().to_dict('records')

# 62개 업종별 매출 TOP 15
industry_sales_top15 = sales_2025q4.groupby('서비스_업종_코드_명')['당월_매출_금액'].sum().sort_values(ascending=False).head(15)
industry_sales_top15_dict = {k: round(v / 1e8, 1) for k, v in industry_sales_top15.items()}

# 행정동 산점도 샘플 (Scatter plot data points)
scatter_points = [
    {
        "dong": row['행정동_코드_명'],
        "gu": row['자치구_코드_명'],
        "stores": int(row['semas_stores']),
        "sales_100m": round(float(row['total_sales']) / 1e8, 1),
        "tx_k": round(float(row['total_tx']) / 1000, 1),
        "trdar_cnt": int(row['trdar_count'])
    }
    for _, row in valid_dong.iterrows()
]

# -------------------------------------------------------------
# [TAB 1 & 2 통합 JSON 페이로드 구성]
# -------------------------------------------------------------
print("[4/4] Assembling comprehensive JSON...")
advanced_payload = {
    "generated_at": "2026-10-31",
    "dataset_info": {
        "semas_stores": int(total_stores),
        "seoul_trdars": int(len(trdar_merged)),
        "reference_period": "2025년 10월 01일 ~ 2025년 12월 31일 (2025Q4 기준)",
        "sales_quarter": "2025년 4분기 추정매출"
    },
    "tab1": {
        "gu_descriptive_stats": gu_desc_stats,
        "dong_descriptive_stats": dong_desc_stats,
        "gu_dong_boxplot": gu_dong_boxplot,
        "gu_macro_crosstab": {
            "gus": list(gu_macro_ct.index),
            "macros": list(gu_macro_ct.columns),
            "counts": gu_macro_ct.values.tolist(),
            "pcts": gu_macro_pct.values.tolist()
        },
        "region_macro_pivot": {
            "regions": list(region_macro_ct.index),
            "macros": list(region_macro_ct.columns),
            "counts": region_macro_ct.values.tolist(),
            "pcts": region_macro_pct.values.tolist()
        },
        "floor_macro_crosstab": {
            "macros": list(floor_macro_ct.index),
            "floors": list(floor_macro_ct.columns),
            "counts": floor_macro_ct.values.tolist(),
            "pcts": floor_macro_pct.values.tolist()
        },
        "lq_matrix": lq_matrix,
        "sub_top15": semas_df['sub_name'].value_counts().head(15).to_dict()
    },
    "tab2": {
        "mapped_62_counts": mapped_62_counts,
        "trdar_type_pivot": trdar_type_pivot,
        "industry_sales_top15": industry_sales_top15_dict,
        "correlation": {
            "pearson_r": round(float(pearson_r), 3),
            "pearson_p": float(pearson_p),
            "spearman_r": round(float(spearman_r), 3),
            "spearman_p": float(spearman_p),
            "slope": round(float(slope), 4),
            "intercept": round(float(intercept), 2),
            "sample_dongs": int(len(valid_dong))
        },
        "scatter_points": scatter_points
    }
}

out_json = OUTPUT_DIR / "semas_advanced_eda_data.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(advanced_payload, f, ensure_ascii=False, indent=2)

print(f"Advanced EDA data successfully generated: {out_json}")

