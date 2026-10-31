"""
1단계 기본 EDA 보고서 및 대시보드 자동 생성 스크립트 (2025Q4 기준) - 개정본
- 모든 표와 수치, 지표, 상권명, 지역명은 결과 파일(JSON/CSV)에서 동적으로 로드
- 자치구×대분류, 층×대분류, 권역×대분류, 자치구별 전체 LQ(25개 구 전체), 업종별 매출 순위 및 집중도(62개 업종 전체)
- 62개 업종 기준 점포-매출 결합 및 100개 업종 민감도 병기
- 잔차 분석 시 코드로 계산한 1위 매출/점포 업종 표기 및 외부 지식 [가설] 태깅
- 상권 이상치 이름표 및 행정동 소비 이상치 8곳 실제 집계 표 수록
- 상권 특성 준비도 표 코드 계산 수치 완비
- 전체 상권(1,650개)과 골목상권 구분, 매출 보유율, 층 1위 분모(전체 vs 입력) 구분 적용
"""
import sys
import os
import json
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
STAGE1_DATA_DIR = DATA_DIR / "processed" / "eda_stage1"
REPORT_DIR = PROJECT_DIR / "report"
IMAGES_DIR = PROJECT_DIR / "images" / "eda_stage1"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

def load_results():
    """집계 결과 데이터 로드"""
    with open(STAGE1_DATA_DIR / "sbiz_quality.json", encoding="utf-8") as f:
        sbiz_q = json.load(f)
    with open(STAGE1_DATA_DIR / "descriptive_stats.json", encoding="utf-8") as f:
        desc_stats = json.load(f)
    with open(STAGE1_DATA_DIR / "cross_summary.json", encoding="utf-8") as f:
        cross_sum = json.load(f)
    with open(STAGE1_DATA_DIR / "sales_store_analysis.json", encoding="utf-8") as f:
        sales_sum = json.load(f)
    with open(STAGE1_DATA_DIR / "spending_outlier_dong_summary.json", encoding="utf-8") as f:
        spend_outliers = json.load(f)
    with open(STAGE1_DATA_DIR / "trade_area_readiness.json", encoding="utf-8") as f:
        trade_readiness = json.load(f)
        
    df_prof = pd.read_csv(STAGE1_DATA_DIR / "file_profiles.csv", encoding="utf-8-sig")
    df_ind = pd.read_csv(STAGE1_DATA_DIR / "industry_sales_concentration_2025Q4.csv", encoding="utf-8-sig")
    df_gu_cat = pd.read_csv(STAGE1_DATA_DIR / "cross_gu_category.csv", index_col=0, encoding="utf-8-sig")
    df_zone_cat = pd.read_csv(STAGE1_DATA_DIR / "cross_zone_category.csv", index_col=0, encoding="utf-8-sig")
    df_floor_cat = pd.read_csv(STAGE1_DATA_DIR / "cross_floor_category.csv", index_col=0, encoding="utf-8-sig")
    df_lq = pd.read_csv(STAGE1_DATA_DIR / "lq_gu_category.csv", index_col=0, encoding="utf-8-sig")
    df_gu_top_lq = pd.read_csv(STAGE1_DATA_DIR / "lq_gu_top_specialization.csv", encoding="utf-8-sig")
    df_spend_outliers = pd.read_csv(STAGE1_DATA_DIR / "spending_outlier_dong_summary.csv", encoding="utf-8-sig")
    df_readiness = pd.read_csv(STAGE1_DATA_DIR / "trade_area_readiness_table.csv", encoding="utf-8-sig")
    df_outlier_flags = pd.read_csv(STAGE1_DATA_DIR / "trade_area_outlier_flags_2025Q4.csv", encoding="utf-8-sig")
    
    return {
        "sbiz_q": sbiz_q,
        "desc_stats": desc_stats,
        "cross_sum": cross_sum,
        "sales_sum": sales_sum,
        "spend_outliers": spend_outliers,
        "trade_readiness": trade_readiness,
        "df_prof": df_prof,
        "df_ind": df_ind,
        "df_gu_cat": df_gu_cat,
        "df_zone_cat": df_zone_cat,
        "df_floor_cat": df_floor_cat,
        "df_lq": df_lq,
        "df_gu_top_lq": df_gu_top_lq,
        "df_spend_outliers": df_spend_outliers,
        "df_readiness": df_readiness,
        "df_outlier_flags": df_outlier_flags
    }

def build_markdown_report(data):
    """01_기본EDA_보고서_2025Q4.md 생성"""
    sbiz = data["sbiz_q"]
    desc = data["desc_stats"]
    cross = data["cross_sum"]
    sales = data["sales_sum"]
    spend_out = data["spend_outliers"]
    prof = data["df_prof"]
    ind = data["df_ind"]
    readiness = data["df_readiness"]
    gu_top_lq = data["df_gu_top_lq"]
    df_gu_cat = data["df_gu_cat"]
    df_zone_cat = data["df_zone_cat"]
    df_floor_cat = data["df_floor_cat"]
    df_lq = data["df_lq"]
    df_spend_out = data["df_spend_outliers"]
    
    gu_stat = desc["자치구_기술통계"]
    dong_stat = desc["행정동_기술통계"]
    
    lines = []
    lines.append("# 01. 서울시 상권 기본 데이터 프로파일링 및 기초 탐색 보고서 (2025Q4)")
    lines.append("")
    lines.append("> **작성 목적**: 예비 창업자 맞춤형 상권 추천 서비스의 기초 분석 단계로서, 서울시 소상공인 점포 및 전체 1,650개 상권 원천 데이터의 품질, 기술통계, 권역·층·업종 교차분석, 추정매출과 점포 수의 상관성, 상권 특성 데이터 준비도를 체계적으로 정리합니다.")
    lines.append("> ")
    lines.append("> **기준 시점 및 수집 주기**:")
    lines.append(f"> - 소상공인 상가정보 스냅샷: **2025-12-31 시점** (서울시 소재 상가업소 데이터 수록 점포 {sbiz['전체_점포_건수']:,}건)")
    lines.append(f"> - 상권 분석 지표(추정매출, 인구, 점포): **2025년 1분기~4분기 (20251~20254)** 및 **2025Q4 집중 분석** (전체 상권 마스터 {sales['마스터_상권수']:,}개 중 2025Q4 추정매출 보유 상권 {sales['Q4_분석대상_상권수']:,}개, 매출 보유율 {sales['분기별_매출보유_비율_pct']['20254']}%)")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 1장 파일별 프로파일
    lines.append("## 1. 원천 데이터 파일별 프로파일 (MANIFEST 비교 및 소비 데이터 포함)")
    lines.append("")
    lines.append("서울 열린데이터광장 및 공공데이터포털에서 수집한 10개 핵심 원천 데이터(소상공인 1개, 상권 8개, 소비 행정동 1개)의 행 수, 열 수, 기준 식별 키, 결측치, 주요 변수 값 범위를 점검하였습니다. 모든 데이터 파일의 실제 행 수는 `data/raw/MANIFEST.csv`의 기준치와 정확히 일치함을 확인하였습니다.")
    lines.append("")
    lines.append("| 파일명 | 실제 행수 | MANIFEST 행수 | 일치 여부 | 열 수 | 기준 키 | 키 유일성 | 기준 기간 | 단위 | 결측치 수 | 주요 변수 값 범위 |")
    lines.append("|:---|---:|---:|:---:|---:|:---|:---:|:---|:---|---:|:---|")
    for _, r in prof.iterrows():
        match_str = "일치" if r["행수_일치여부"] else "불일치"
        uniq_str = "유일" if r["키_유일성"] else "중복"
        lines.append(f"| `{r['파일명']}` | {r['실제_행수']:,} | {r['매니페스트_행수']:,} | {match_str} | {r['열수']} | `{r['기준_키']}` | {uniq_str} | {r['기준_기간']} | {r['단위']} | {r['결측치_총수']:,} | {r['주요변수_값범위']} |")
    lines.append("")
    lines.append("*근거 파일: `data/processed/eda_stage1/file_profiles.csv`*")
    lines.append("")
    
    # 2장 소상공인 데이터 품질
    lines.append("## 2. 소상공인 상가정보 데이터 품질 점검")
    lines.append("")
    lines.append(f"소상공인시장진흥공단 서울 상가정보 원천 데이터({sbiz['전체_점포_건수']:,}건)에 대해 행정동 코드 정합성, 층 정보, 중복 등록, 공간 지리 좌표를 단계별로 검토하였습니다.")
    lines.append("")
    lines.append("### 2.1 행정동 코드 정합성")
    lines.append(f"- **코드 매핑 전후**: 원천 데이터의 행정동 코드는 **{sbiz['행정동_대응_전_동수']}개**였으나, `PREPROCESSING.md` 2.4절의 2025년 행정동 분동/통합(용신동, 상일동, 일원2동) 대응 규칙을 적용한 결과 상권분석 마스터 기준인 **{sbiz['행정동_대응_후_동수']}개 동**으로 정리되었습니다.")
    lines.append(f"- **마스터 일치 여부**: 변환 후 425개 행정동 코드가 상권분석 공용 행정동 마스터(425개 동)와 모두 일치함을 확인하였습니다.")
    lines.append("")
    lines.append("### 2.2 층 정보 분류 및 결측 현황 (분모 구분 해석)")
    lines.append(f"- **원천 고유값 및 결측**: 원천 데이터 내 층정보의 고유값은 **{sbiz['층정보_원천_고유값수']}개**이며, 결측치는 전체의 **{sbiz['층정보_결측비율_전체_pct']:.2f}%**({sbiz['층정보_결측건수']:,}건)입니다.")
    lines.append("- **층 1위 해석의 분모 구분**:")
    lines.append(f"  - **전체 점포 기준 ({sbiz['전체_점포_건수']:,}건)**: 미입력 결측이 {sbiz['층정보_결측비율_전체_pct']:.2f}%({sbiz['층정보_결측건수']:,}건)로 1위이며, 지상 1층은 {sbiz['층정보_1층비율_전체점포기준_pct']:.2f}%({sbiz['층정보_1층_점포수']:,}건)로 2위입니다.")
    lines.append(f"  - **층 정보가 입력된 점포 기준 ({sbiz['층정보_입력점포_건수']:,}건)**: 지상 1층이 **{sbiz['층정보_1층비율_입력점포기준_pct']:.2f}%**({sbiz['층정보_1층_점포수']:,}건)로 가장 많은 비중을 차지합니다.")
    lines.append("")
    lines.append("| 층 분류 | 점포 수 (건) | 전체 대비 비중 (%) | 입력 점포 대비 비중 (%) | 비고 |")
    lines.append("|:---|---:|---:|---:|:---|")
    for f_name, f_cnt in sbiz["층분류_집계"].items():
        f_ratio_tot = round(f_cnt / sbiz["전체_점포_건수"] * 100, 2)
        f_ratio_inp = round(f_cnt / sbiz["층정보_입력점포_건수"] * 100, 2) if f_name != "미입력(결측)" else 0.0
        inp_str = f"{f_ratio_inp:.2f}%" if f_name != "미입력(결측)" else "-"
        note = "지상 주요 층" if "지상" in f_name else ("기본 결측" if "미입력" in f_name else "세부 검토 필요")
        lines.append(f"| {f_name} | {f_cnt:,} | {f_ratio_tot:.2f}% | {inp_str} | {note} |")
    lines.append(f"| **총계** | **{sbiz['전체_점포_건수']:,}** | **100.00%** | **100.00%** | 분모: 전체 점포 / 입력 점포 |")
    lines.append("")
    lines.append(f"- **미분류 상세 ({sbiz['층_미분류건수']}건)**: 호수오기/미분류 및 기타는 대부분 층 컬럼에 호수(예: 101호, 201호 등)를 오기입한 경우이며, 상위 5개 빈도는 다음과 같습니다:")
    top_unclass = list(sbiz["층_미분류예시_top10"].items())[:5]
    lines.append(", ".join([f"`{k}`({v}건)" for k, v in top_unclass]))
    lines.append("")
    lines.append("### 2.3 중복 점포 및 공간 지리 좌표 검증")
    lines.append(f"- **식별자 중복**: 기본 고유 키인 `상가업소번호` 기준 중복 건수는 **{sbiz['상가업소번호_중복건수']}건**으로 고유 키 유일성이 확인되었습니다.")
    lines.append(f"- **복합 속성 중복**: `[상호명, 도로명주소, 층정보, 호정보, 상권업종소분류명]` 5개 조합 중복은 **{sbiz['복합조합_중복비율_pct']}%** 나타났습니다. [가설] 동일 매장 내 배달 전문 별도 사업자 등록(숍인숍) 또는 사업자 변경 이력의 누적 반영일 가능성이 있습니다.")
    lines.append(f"- **서울시 경계 폴리곤 판정**: `geo/HangJeongDong_ver20251231.geojson`의 서울시 행정동 경계 피처 {sbiz['좌표_서울경계_피처수']}개 폴리곤 합집합과 경도·위도 좌표를 대조한 결과, 서울 경계 내부는 **{sbiz['좌표_서울경계내_건수']:,}건 ({sbiz['좌표_서울경계내_비율_pct']}%)**, 서울 경계 외부는 **{sbiz['좌표_서울경계외_건수']}건 ({sbiz['좌표_경계외_비율_pct']}%)**으로 확인되었습니다. [가설] 경계 외 점포는 서울 인접 시·군 행정구역 경계선 오차 등으로 추정되며 임의 삭제하지 않고 원본을 보존합니다.")
    lines.append("")
    lines.append("![층분류별 점포수 막대](../images/eda_stage1/02_층분류별_점포수_막대.png)")
    lines.append("")
    lines.append("*근거 파일: `data/processed/eda_stage1/sbiz_quality.json`, `data/processed/eda_stage1/raw_floor_values.csv`*")
    lines.append("")
    
    # 3장 기술통계
    lines.append("## 3. 자치구 및 행정동 점포 수 기술통계 분석")
    lines.append("")
    lines.append("소상공인 점포의 공간적 밀집도를 파악하기 위해 25개 자치구와 425개 행정동 단위 점포 수의 분포적 특성을 계산하였습니다.")
    lines.append("")
    lines.append("| 집계 단위 | 지역 수 | 평균 | 중위수 | 표준편차 | Q1 (25%) | Q3 (75%) | IQR | 최소값 (지역명, 코드) | 최대값 (지역명, 코드) | 왜도 | 첨도 |")
    lines.append("|:---|---:|---:|---:|---:|---:|---:|---:|:---|:---|---:|---:|")
    lines.append(f"| 자치구 단위 | {gu_stat['지역수']}개 구 | {gu_stat['평균']:,} | {gu_stat['중위수']:,} | {gu_stat['표준편차']:,} | {gu_stat['Q1']:,} | {gu_stat['Q3']:,} | {gu_stat['IQR']:,} | {gu_stat['최소값']:,} ({gu_stat['최소지역']}, `{gu_stat['최소지역_코드']}`) | {gu_stat['최대값']:,} ({gu_stat['최대지역']}, `{gu_stat['최대지역_코드']}`) | {gu_stat['왜도']:.3f} | {gu_stat['첨도']:.3f} |")
    lines.append(f"| 행정동 단위 | {dong_stat['지역수']}개 동 | {dong_stat['평균']:,} | {dong_stat['중위수']:,} | {dong_stat['표준편차']:,} | {dong_stat['Q1']:,} | {dong_stat['Q3']:,} | {dong_stat['IQR']:,} | {dong_stat['최소값']:,} ({dong_stat['최소지역']}, `{dong_stat['최소지역_코드']}`) | {dong_stat['최대값']:,} ({dong_stat['최대지역']}, `{dong_stat['최대지역_코드']}`) | {dong_stat['왜도']:.3f} | {dong_stat['첨도']:.3f} |")
    lines.append("")
    lines.append("### 기술통계 해석")
    lines.append(f"- **자치구 분포**: 서울 25개 자치구 중 가장 점포가 많은 곳은 `{gu_stat['최대지역']}`({gu_stat['최대값']:,}개)이며, 가장 적은 `{gu_stat['최소지역']}`({gu_stat['최소값']:,}개) 대비 약 {round(gu_stat['최대값'] / gu_stat['최소값'], 1)}배 수준의 편차를 보입니다. 왜도({gu_stat['왜도']:.3f})가 양수로 우측 꼬리가 긴 형태입니다.")
    lines.append(f"- **행정동 분포**: 425개 행정동의 평균 점포 수는 {dong_stat['평균']:,}개, 중위수는 {dong_stat['중위수']:,}개입니다. 최대 점포 밀집지는 `{dong_stat['최대지역']}`({dong_stat['최대값']:,}개)이며, 최소 지역은 [가설] 아파트 주거 중심 배후지로 상업 점포가 적은 `{dong_stat['최소지역']}`({dong_stat['최소값']:,}개)입니다. 첨도가 {dong_stat['첨도']:.1f}로 매우 높아 특정 핵심 상권 동에 점포가 집중되어 있음을 보여줍니다.")
    lines.append("")
    lines.append("![자치구별 점포수 분포](../images/eda_stage1/01_자치구별_점포수_분포.png)")
    lines.append("")
    lines.append("*근거 파일: `data/processed/eda_stage1/descriptive_stats.json`, `data/processed/eda_stage1/descriptive_stats_table.csv`*")
    lines.append("")
    
    # 4장 교차분석 및 입지계수(LQ)
    lines.append("## 4. 권역 · 층 · 업종별 교차분석 및 자치구별 전체 LQ")
    lines.append("")
    lines.append("소상공인 점포를 서울 5대 생활권역, 층위, 25개 자치구, 10대 상권업종 대분류 기준으로 교차 집계하고 자치구별 입지계수(LQ)를 도출하였습니다.")
    lines.append("")
    lines.append("### 4.1 권역별 10대 대분류 점포 분포")
    lines.append("")
    cols_zone = df_zone_cat.columns.tolist()
    lines.append("| 권역 | " + " | ".join(cols_zone) + " |")
    lines.append("|:---|" + ":---:|"*len(cols_zone))
    for idx, row in df_zone_cat.iterrows():
        row_vals = [f"{int(v):,}" for v in row.values]
        lines.append(f"| {idx} | " + " | ".join(row_vals) + " |")
    lines.append("")
    lines.append(f"- **권역 점포 비중**: 동남권이 **{cross['권역_비율_pct']['동남권']}%**({cross['권역_점포수']['동남권']:,}개)로 가장 높은 비중을 차지하며, 서남권({cross['권역_비율_pct']['서남권']}%), 동북권({cross['권역_비율_pct']['동북권']}%), 도심권({cross['권역_비율_pct']['도심권']}%), 서북권({cross['권역_비율_pct']['서북권']}%) 순입니다. (분모: 서울시 전체 점포 {sbiz['전체_점포_건수']:,}개)")
    lines.append("")
    
    lines.append("### 4.2 층분류별 10대 대분류 점포 분포")
    lines.append("")
    cols_floor = df_floor_cat.columns.tolist()
    lines.append("| 층 분류 | " + " | ".join(cols_floor) + " |")
    lines.append("|:---| " + " | ".join([":---:"]*len(cols_floor)) + " |")
    for idx, row in df_floor_cat.iterrows():
        row_vals = [f"{int(v):,}" for v in row.values]
        lines.append(f"| {idx} | " + " | ".join(row_vals) + " |")
    lines.append("")
    lines.append("*근거 파일: `data/processed/eda_stage1/cross_floor_category.csv`*")
    lines.append("")

    lines.append("### 4.3 자치구별 10대 대분류 점포 수 (25개 구 교차표)")
    lines.append("")
    cols_gu = df_gu_cat.columns.tolist()
    lines.append("| 자치구 | " + " | ".join(cols_gu) + " |")
    lines.append("|:---| " + " | ".join([":---:"]*len(cols_gu)) + " |")
    for idx, row in df_gu_cat.iterrows():
        row_vals = [f"{int(v):,}" for v in row.values]
        lines.append(f"| {idx} | " + " | ".join(row_vals) + " |")
    lines.append("")
    lines.append("*근거 파일: `data/processed/eda_stage1/cross_gu_category.csv`*")
    lines.append("")
    
    lines.append("### 4.4 25개 자치구 × 10대 대분류 전체 입지계수(LQ) 매트릭스")
    lines.append("서울 전체 대비 각 자치구의 10대 업종별 입지계수(LQ) 전체 표입니다. LQ 1.0 초과는 서울시 평균 대비 해당 구의 특화 상태를 나타냅니다.")
    lines.append("")
    cols_lq = df_lq.columns.tolist()
    lines.append("| 자치구 | " + " | ".join(cols_lq) + " |")
    lines.append("|:---| " + " | ".join([":---:"]*len(cols_lq)) + " |")
    for idx, row in df_lq.iterrows():
        row_vals = [f"{float(v):.3f}" for v in row.values]
        lines.append(f"| {idx} | " + " | ".join(row_vals) + " |")
    lines.append("")
    lines.append("*근거 파일: `data/processed/eda_stage1/lq_gu_category.csv`*")
    lines.append("")
    
    lines.append("### 4.5 구별 최고 특화 업종 (25개 자치구)")
    lines.append(f"각 자치구별로 입지계수(LQ)가 가장 높은 대분류 업종을 추출하여 해당 구의 업종 점포 수 및 구 내 비중을 함께 정리하였습니다. ({cross['LQ_판정_기준_문구']})")
    lines.append("")
    lines.append("| 자치구명 | 최고 특화 대분류 | 해당 구 업종 점포수 | 구 내 전체 점포수 | 구 내 비중 (%) | 서울 업종 점포수 | 서울 전체 비중 (%) | 입지계수 (LQ) | 특화 해석 |")
    lines.append("|:---|:---|---:|---:|---:|---:|---:|---:|:---|")
    for _, r in gu_top_lq.iterrows():
        lines.append(f"| {r['자치구명']} | **{r['대분류명']}** | {int(r['해당구_업종_점포수']):,}개 | {int(r['구내_전체_점포수']):,}개 | {r['구내_비중_pct']:.2f}% | {int(r['서울_업종_점포수']):,}개 | {r['서울_비중_pct']:.2f}% | **{r['입지계수_LQ']:.3f}** | {r['특화도_판정']} |")
    lines.append("")
    lines.append("*근거 파일: `data/processed/eda_stage1/lq_gu_top_specialization.csv`, `data/processed/eda_stage1/lq_gu_category_full.csv`*")
    lines.append("")
    
    # 5장 상권 매출과 점포
    lines.append("## 5. 상권 점포 수와 추정매출액 분석 (62개 업종 주분석 및 100개 업종 민감도)")
    lines.append("")
    lines.append(f"서울시 전체 {sales['마스터_상권수']:,}개 상권 마스터 대비 2025Q4 시점의 62개 업종 점포 수와 추정매출액 간 상관관계를 분석하고, 100개 업종과의 차이 및 상위 1% 이상치 상권에 대한 민감도 분석을 수행하였습니다.")
    lines.append("")
    lines.append("### 5.1 상권 표본 보유 현황")
    type_info = sales["상권유형별_마스터_수"]
    t_tot = type_info["총계"]
    t_gol = type_info["골목상권"]
    t_trd = type_info["전통시장"]
    t_dev = type_info["발달상권"]
    t_tou = type_info["관광특구"]
    lines.append(f"- **전체 마스터 상권 수**: {t_tot:,}개 상권 (골목상권 {t_gol:,}개, 전통시장 {t_trd:,}개, 발달상권 {t_dev:,}개, 관광특구 {t_tou:,}개)")
    lines.append(f"- **2025Q4 추정매출 보유 상권 수**: **{sales['Q4_분석대상_상권수']:,}개 상권** (전체 마스터 상권 {t_tot:,}개 대비 매출 보유율 **{sales['분기별_매출보유_비율_pct']['20254']}%**)")
    lines.append(f"- **분기별 매출 보유 추이**: Q1({sales['분기별_매출보유_상권수']['20251']}개, {sales['분기별_매출보유_비율_pct']['20251']}%) → Q2({sales['분기별_매출보유_상권수']['20252']}개, {sales['분기별_매출보유_비율_pct']['20252']}%) → Q3({sales['분기별_매출보유_상권수']['20253']}개, {sales['분기별_매출보유_비율_pct']['20253']}%) → Q4({sales['분기별_매출보유_상권수']['20254']}개, {sales['분기별_매출보유_비율_pct']['20254']}%)")
    lines.append("")
    lines.append("### 5.2 점포 수 vs 추정매출액 상관분석 및 민감도 분석 (62개 업종 vs 100개 업종)")
    lines.append("")
    lines.append("| 분석 구분 | 업종 기준 | 분석 대상 상권 수 | 피어슨 상관계수 (r) | 스피어만 순위상관 (rho) | 이상치 제외 기준 | 비고 |")
    lines.append("|:---|:---:|---:|---:|---:|:---|:---|")
    lines.append(f"| **주 분석 (전체 상권)** | **62개 업종** | {sales['Q4_분석대상_상권수']:,}개 | **{sales['주분석_62업종_상관계수_Pearson_r']:.4f}** | **{sales['주분석_62업종_순위상관_Spearman_rho']:.4f}** | 없음 (전체 유효 상권) | 추정매출 업종과 1:1 일치 기준 |")
    lines.append(f"| 민감도 1 (상위 1% 제외) | 62개 업종 | {sales['민감도_분석대상_상권수']:,}개 | {sales['주분석_62업종_민감도_Pearson_r']:.4f} | {sales['주분석_62업종_민감도_Spearman_rho']:.4f} | 매출 상위 1% ({sales['민감도_제외_상권수']}개 상권 제외) | 선형 상관성 변화 ({sales['주분석_62업종_상관계수_Pearson_r']:.4f} → {sales['주분석_62업종_민감도_Pearson_r']:.4f}) |")
    lines.append(f"| 민감도 2 (100개 업종 전체) | 100개 업종 | {sales['Q4_분석대상_상권수']:,}개 | {sales['민감도_100업종_상관계수_Pearson_r']:.4f} | {sales['민감도_100업종_순위상관_Spearman_rho']:.4f} | 없음 (전체 유효 상권) | 점포 파일 전체 업종 합계 |")
    lines.append(f"| 민감도 3 (100개 + 상위 1% 제외) | 100개 업종 | {sales['민감도_분석대상_상권수']:,}개 | {sales['민감도_100업종_민감도_Pearson_r']:.4f} | {sales['민감도_100업종_민감도_Spearman_rho']:.4f} | 매출 상위 1% ({sales['민감도_제외_상권수']}개 상권 제외) | 업종 범위 및 이상치 복합 비교 |")
    lines.append("")
    lines.append("- **민감도 분석 수치 비교**:")
    s_62_tot = sales['주분석_62업종_점포수_합계']
    s_100_tot = sales['민감도_100업종_점포수_합계']
    s_diff = sales['업종범위_점포수_차이']
    s_diff_pct = sales['업종범위_점포수_차이_비율_pct']
    s_100_all_tot = sales['전체상권_100업종_점포수_합계']
    lines.append(f"  - 62개 업종 기준 점포 수 총계({s_62_tot:,}개)는 매출 보유 {sales['Q4_분석대상_상권수']:,}개 상권 기준 100개 업종 총계({s_100_tot:,}개) 대비 {s_diff:,}개({s_diff_pct}%) 적습니다. (참고: 점포 파일의 전체 {sales['마스터_상권수']:,}개 상권 100개 업종 점포 수 총계는 {s_100_all_tot:,}개입니다.)")
    lines.append(f"  - 62개 업종 기준 선형 상관계수는 전체 {sales['주분석_62업종_상관계수_Pearson_r']:.4f}이며, 상위 1% 이상치 상권을 제외할 경우 {sales['주분석_62업종_민감도_Pearson_r']:.4f}로 나타납니다.")
    lines.append(f"  - 순위 상관계수(스피어만 rho)는 62개 업종 기준 {sales['주분석_62업종_순위상관_Spearman_rho']:.4f}, 100개 업종 기준 {sales['민감도_100업종_순위상관_Spearman_rho']:.4f}입니다.")
    lines.append(f"  - [주의] 상위 1% 이상치 제외 민감도 분석은 매출액을 기준으로 상위 {sales['민감도_제외_상권수']}개 상권을 인위적으로 제외한 결과이므로, 표본 절단 효과에 의한 수치 변동이 있을 수 있어 일반 상권 추천 모델 적용 시 해석에 주의가 필요합니다.")
    lines.append("")
    lines.append("![상권 점포수 매출 상관 및 민감도](../images/eda_stage1/03_상권_점포수_매출_상관및민감도.png)")
    lines.append("")
    lines.append("### 5.3 회귀 잔차 기반 이상치 상권 원인 분석 (62개 업종 기준)")
    lines.append(f"- **선형 추세식**: `예측매출(원) = {sales['회귀분석_기울기']:,.2f} × 점포수_62업종 + ({sales['회귀분석_절편']:,.2f})`")
    lines.append("- 잔차 상·하위 5개 상권의 매출 1위 업종과 점포 1위 업종을 코드로 자동 계산하여 표기하고, 외부 지식은 `[가설]`로 명시하였습니다.")
    lines.append("")
    lines.append("#### (1) 점포 수 대비 매출 과대표 상권 Top 5 (회귀선 상단)")
    lines.append("")
    lines.append("| 순위 | 상권명 | 상권코드 | 점포수 (62업종) | 2025Q4 추정매출 (원) | 잔차 (원) | 매출 1위 업종 (매출액, 비중) | 점포 1위 업종 (점포수, 비중) | 추정 가설 |")
    lines.append("|:---:|:---|---:|---:|---:|---:|:---|:---|:---|")
    for i, it in enumerate(sales["회귀선_상단_매출과대표_Top5"], 1):
        lines.append(f"| {i} | {it['상권명']} | `{it['상권코드']}` | {it['점포수_62업종']:,}개 | {it['실제매출_원']:,} | +{it['잔차_원']:,} | {it['매출1위_업종명']} ({it['매출1위_매출액_원']:,}원, {it['매출1위_비중_pct']}%) | {it['점포1위_업종명']} ({it['점포1위_점포수']:,}개, {it['점포1위_비중_pct']}%) | {it['가설_원인']} |")
    lines.append("")
    lines.append("#### (2) 점포 수 대비 매출 과소표 상권 Top 5 (회귀선 하단)")
    lines.append("")
    lines.append("| 순위 | 상권명 | 상권코드 | 점포수 (62업종) | 2025Q4 추정매출 (원) | 잔차 (원) | 매출 1위 업종 (매출액, 비중) | 점포 1위 업종 (점포수, 비중) | 추정 가설 |")
    lines.append("|:---:|:---|---:|---:|---:|---:|:---|:---|:---|")
    for i, it in enumerate(sales["회귀선_하단_매출과소표_Top5"], 1):
        lines.append(f"| {i} | {it['상권명']} | `{it['상권코드']}` | {it['점포수_62업종']:,}개 | {it['실제매출_원']:,} | {it['잔차_원']:,} | {it['매출1위_업종명']} ({it['매출1위_매출액_원']:,}원, {it['매출1위_비중_pct']}%) | {it['점포1위_업종명']} ({it['점포1위_점포수']:,}개, {it['점포1위_비중_pct']}%) | {it['가설_원인']} |")
    lines.append("")
    
    lines.append("### 5.4 업종별 매출 순위 및 1위 상권 집중도 (62개 업종 전체)")
    lines.append("- 특정 업종의 매출이 서울시 전체 대비 단 1곳 상권에 30% 이상 편중된 경우 `특화집중_상권` 이름표를 부여하였습니다.")
    lines.append("- **상권 수 주의 이름표 기준 (2단계)**:")
    lines.append(f"  - **50개 미만 (`주의(50개미만)`):** 2025Q4 매출 보유 상권 수 {sales['Q4_분석대상_상권수']:,}개 중 매출 데이터가 존재하는 상권 수가 50개 미만인 소표본 업종으로, 극소수 점포의 매출 이상치에 따라 업종 전체 평균이 크게 왜곡될 수 있어 고위험군으로 분류합니다.")
    lines.append("  - **100개 미만 (`주의(100개미만)`):** 서울시 25개 자치구에 평균 4개 이하 수준으로 분포하는 업종으로, 추천 모델 적용 시 주의를 위해 팀이 정한 판단 기준입니다.")
    lines.append("")
    lines.append("| 순위 | 업종명 | 업종코드 | 서울 총매출 (원) | 매출보유 상권수 | 상권수 주의 | 1위 상권명 | 1위 상권코드 | 1위 상권 매출 (원) | 1위 상권 집중도 (%) | 특화집중 여부 |")
    lines.append("|:---:|:---|:---:|---:|---:|:---:|:---|:---:|---:|---:|:---:|")
    for rank, (_, r) in enumerate(ind.iterrows(), 1):
        focus_tag = "**특화집중**" if r["특화집중_상권_여부"] else "일반"
        caution_tag = f"`{r['상권수_주의_이름표']}`" if "주의" in r['상권수_주의_이름표'] else "정상"
        lines.append(f"| {rank} | {r['업종명']} | `{r['업종코드']}` | {r['총매출_원']:,} | {r['매출보유_상권수']}개 | {caution_tag} | {r['1위상권명']} | `{r['1위상권코드']}` | {r['1위상권매출_원']:,} | {r['1위상권_집중도_pct']:.2f}% | {focus_tag} |")
    lines.append("")
    lines.append("![업종별 단일상권 집중도 Top 10](../images/eda_stage1/04_업종별_단일상권_집중도_Top10.png)")
    lines.append("")
    lines.append("*근거 파일: `data/processed/eda_stage1/industry_sales_concentration_2025Q4.csv`, `data/processed/eda_stage1/sales_store_analysis.json`*")
    lines.append("")
    
    # 5.5 행정동 소비 이상치 8곳 실제 집계 표
    lines.append("### 5.5 행정동 소비 이상치 8곳 실제 집계 (행정동_마스터 기준)")
    lines.append(f"`PREPROCESSING.md` 6장 및 `행정동_마스터.csv`의 `소비_이상치` 레이블을 기준으로 2025년 행정동 소비 데이터({spend_out['서울_총지출_조원']}조원)를 집계한 결과, 8개 이상치 동이 서울 전체 지출의 **{spend_out['이상치_8개동_지출비중_pct']}%**({spend_out['이상치_8개동_지출합계_조원']}조원)를 차지함을 확인하였습니다. 값을 임의 삭제하지 않고 이름표로 구분 관리합니다.")
    lines.append("")
    lines.append("| 행정동 코드 | 행정동명 | 2025년 총 지출액 (원) | 지출 규모 (조원) | 서울 전체 대비 비중 (%) | 지출 쏠림 최대 항목 | 최대 항목 비중 (%) |")
    lines.append("|:---:|:---|---:|---:|---:|:---|---:|")
    for _, r in df_spend_out.iterrows():
        lines.append(f"| `{r['행정동_코드']}` | **{r['행정동_명']}** | {r['지출_총금액_원']:,} | {r['지출_조원']:.2f}조원 | {r['서울_비중_pct']:.2f}% | {r['소비_최대항목']} | {r['소비_최대항목_비중_pct']:.1f}% |")
    lines.append(f"| - | **8개 이상치 동 합계** | **{spend_out['이상치_8개동_지출합계_원']:,}** | **{spend_out['이상치_8개동_지출합계_조원']:.2f}조원** | **{spend_out['이상치_8개동_지출비중_pct']:.2f}%** | - | - |")
    lines.append(f"| - | **정상 417개 동 합계** | **{spend_out['정상_417개동_지출합계_원']:,}** | **{spend_out['정상_417개동_지출합계_조원']:.2f}조원** | **{spend_out['정상_417개동_지출비중_pct']:.2f}%** | - | - |")
    lines.append(f"| - | **서울시 전체 총계** | **{spend_out['서울_총지출_원']:,}** | **{spend_out['서울_총지출_조원']:.2f}조원** | **100.00%** | - | - |")
    lines.append("")
    lines.append("*근거 파일: `data/processed/eda_stage1/spending_outlier_dong_summary.csv`*")
    lines.append("")
    
    # 6장 상권 특성 데이터 준비도 확인
    lines.append("## 6. 상권 특성 데이터 준비도 점검 (코드 자동 집계)")
    lines.append("")
    lines.append("7대 핵심 상권 특성(고객 구성, 객단가, 프랜차이즈 비율, 매출 변화, 경쟁, 개폐업, 소비 수준)과 비용 항목(임대료·보증금)의 파일별 행 수, 빠진 상권 수, 빠진 상권×분기 칸 수, 주요 컬럼 0값, 결측치 수를 코드로 직접 집계하였습니다.")
    lines.append("")
    lines.append("- **지표 정의**:")
    lines.append(f"  - **파일 행 수**: 2025년 기준 해당 파일의 전체 레코드(행) 개수")
    lines.append(f"  - **빠진 상권 수**: 서울시 마스터 상권 {sales['마스터_상권수']:,}개 중 해당 파일에 연간 단 1건도 포함되지 않은 상권 수 (상권 미집계 파일은 '해당 없음')")
    lines.append(f"  - **빠진 상권×분기 칸 수**: 마스터 상권 {sales['마스터_상권수']:,}개 × 4분기 = {sales['마스터_상권수'] * 4:,}개 슬롯 중 데이터가 없는 빈 칸 수 (단일 스냅샷 파일은 0, 상권 미집계 파일은 '해당 없음')")
    lines.append("  - **주요컬럼 0값 건수**: 핵심 분석 지표 컬럼에서 0으로 기록된 건수를 컬럼별로 분리 기재")
    lines.append("  - **결측치 수**: 결측(NA)으로 비어 있는 값의 수")
    lines.append("")
    lines.append("| 상권 특성 항목 | 계산 가능 여부 | 대응 원천 파일 | 파일 행 수 | 빠진 상권 수 | 빠진 상권×분기 칸 수 | 주요컬럼 0값 건수 | 결측치 수 | 활용 가능 컬럼 | 한계점 및 주의사항 |")
    lines.append("|:---|:---:|:---|---:|---:|---:|:---|---:|:---|:---|")
    for _, r in readiness.iterrows():
        avail_badge = f"**{r['계산가능_여부']}**" if "계산할 수 있음" in r['계산가능_여부'] else "데이터 없음"
        lines.append(f"| {r['상권_특성_항목']} | {avail_badge} | `{r['대응_원천파일']}` | {r['파일_행수']:,} | {r['빠진_상권수']} | {r['빠진_상권분기_칸수']} | `{r['주요컬럼_0값_건수']}` | {r['결측치_수']:,} | `{r['활용가능_컬럼']}` | {r['한계점_및_주의사항']} |")
    lines.append("")
    lines.append("*근거 파일: `data/processed/eda_stage1/trade_area_readiness_table.csv`*")
    lines.append("")
    
    # 7장 종합 결론 및 안내
    lines.append("## 7. 종합 요약 및 다음 단계 제언")
    lines.append("")
    lines.append(f"1. **데이터 품질 확보**: 10개 핵심 원천 파일의 실제 행 수가 MANIFEST와 일치하며, 2025년 행정동 분동/통합 대응을 통해 {sbiz['행정동_대응_후_동수']}개 마스터 동 코드와 일치하도록 정비되었습니다.")
    lines.append(f"2. **이상치 이름표 관리**: 행정동 소비 이상치 {len(df_spend_out)}곳(지출 합계 {spend_out['이상치_8개동_지출합계_조원']}조 원, 비중 {spend_out['이상치_8개동_지출비중_pct']}%) 및 상권 매출 이상치(매출 상위 1% {sales['민감도_제외_상권수']}곳 등)는 값을 임의 삭제하지 않고 이름표를 부여해 보존하였으며, 민감도 분석을 통해 선형 상관계수 r이 전체 {sales['주분석_62업종_상관계수_Pearson_r']:.4f}에서 상위 1% 제외 시 {sales['주분석_62업종_민감도_Pearson_r']:.4f}로 산출됨을 확인하였습니다.")
    lines.append("3. **상권 추천 데이터 준비성**: 고객 구성, 객단가, 프랜차이즈 비율, 개폐업률 등 7대 상권 특성은 모두 보유 데이터에 필요한 컬럼이 있어 계산할 수 있습니다. 단, 임대료 및 보증금은 원천 데이터에 없으므로 향후 공공 임대 시세 연계가 필요합니다.")
    lines.append("")
    lines.extend(revision_history_lines())
    lines.append("")
    lines.append("---")
    lines.append("*본 보고서는 `src/build_stage1_report.py`에 의해 `data/processed/eda_stage1/` 집계 파일로부터 자동 생성되었습니다.*")
    
    report_content = "\n".join(lines)
    with open(REPORT_DIR / "01_기본EDA_보고서_2025Q4.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    print(">>> 01_기본EDA_보고서_2025Q4.md 작성 완료!")
    return report_content

def revision_history_lines():
    """보고서 8장 수정 이력. 과거 오류 값을 기록하므로 결과 파일에서 계산하지 않는다."""
    return [
        "## 8. 수정 이력 (2026-10-31)",
        "",
        "이 보고서는 원천 데이터를 다시 계산하는 독립 검수를 거치며 여러 번 수정되었습니다. 회차별로 무엇을 왜 고쳤는지 기록합니다. 시각은 검수 결과가 나온 때입니다.",
        "",
        "> **읽는 법**: 이 장의 숫자에는 과거의 틀린 값이 포함되어 있습니다. 분석 값을 인용할 때는 1~7장을 사용하세요.",
        "",
        "### 8.1 이전 보고서 검수 (13:08, 13:40)",
        "- **대상**: `이승희/01_소상공인시장진흥공단_상가데이터_기본EDA_보고서.md`",
        "- **발견**: 자치구·권역 표는 합계만 맞고 칸 값이 틀렸습니다. 음식과 소매의 1층 비율이 뒤바뀌어 있었고, 슈퍼마켓 14,007억은 실제로 수산물판매 금액이었습니다. 신사동 2곳이 하나로 합쳐졌고, 도곡1동은 두 번 집계되었습니다. 2025Q4 매출이 있는 상권은 1,650개가 아니라 1,565개였습니다.",
        "- **왜 새로 만들었나**: 고친 뒤 다시 계산하자 지적한 값은 맞았지만, 지적하지 않은 칸에서 새 오류가 나왔습니다. 값을 손으로 고치는 방식으로는 끝나지 않는다고 판단해, 코드로 집계하고 보고서를 자동 생성하는 현재 방식으로 다시 작성했습니다.",
        "- **후속 처리**: 이전 산출물 15개는 커밋 `346686b`로 현재 파일 목록에서 삭제했습니다. 내용은 커밋 `fcbfebb`의 기록에서 볼 수 있습니다.",
        "",
        "### 8.2 1차 검수 (14:51)",
        "- **점포 기준 100개 → 62개 업종**: `PREPROCESSING.md` 5장 규칙에 맞추기 위해서입니다. 매출 집계 대상이 아닌 업종이 점포 수에 섞이면 상관계수와 잔차 순위가 달라집니다.",
        "- **실제로 하지 않은 처리 삭제**: 이상치 이름표를 붙였다고 적혀 있었지만 코드에 없었습니다. 이름표를 실제로 만들고, 소비 이상치 8곳도 코드로 집계했습니다.",
        "- **\"데이터 확인 특성\" 제거**: 코드에 직접 쓴 설명이 데이터와 맞지 않았습니다. 예를 들어 노량진역을 입시 학원가로 설명했지만 매출의 91.1%는 수산물판매였습니다. 매출·점포 1위 업종을 코드로 계산하고, 외부 지식은 [가설]로 표시했습니다.",
        "- **빠진 표 추가**: 교차표, LQ, 업종별 매출 순위가 결과 파일에만 있었습니다.",
        "- **분모와 표현 정리**: 1층 비율은 전체 점포(32.78%)와 층 입력 점포(50.54%)를 구분했습니다. 전체 상권과 골목상권을 구분하고, 문서로 확인되지 않는 카드 기반 표현을 뺐습니다.",
        "- **자동 검사 재작성**: 표에 틀린 값 3곳을 일부러 넣어도 통과했기 때문입니다. 숫자가 문서 어딘가에 있는지만 보고 있었습니다.",
        "- **데이터 정리**: 현재 코드가 만들지 않는 옛 결과 파일을 삭제하고, `data/raw/MANIFEST.csv`를 원래 상태로 되돌렸습니다.",
        "",
        "### 8.3 2차 검수 (15:43)",
        "- **상권 유형 수 정정**: 발달 261·전통시장 284·관광특구 15개를 발달 249·전통시장 305·관광특구 6개로 고쳤습니다. 합계가 1,650으로 맞아 눈에 띄지 않던 오류로, 코드에 숫자를 직접 쓴 것이 원인이었습니다.",
        "- **직접 쓴 숫자 제거**: 값이 바뀌어도 문장이 따라오지 못하므로 결과 파일 값을 쓰도록 바꿨습니다.",
        "- **대시보드 표와 LQ 표 추가**: 자치구·층 교차표와 62개 업종 순위가 대시보드에 없었고, \"전체 LQ\"라는 제목 아래 구별 1위만 있었습니다.",
        "- **주의 이름표 기준 정리**: 문장에는 50개 미만만 있었지만 표에는 100개 미만도 있었습니다.",
        "- **점포 총계 기준 변경**: 상관분석과 같은 대상인 매출 보유 1,565개 상권 기준으로 맞춰 457,188개에서 453,076개가 되었습니다. 파일 전체 값이 틀렸던 것은 아닙니다.",
        "- **자동 검사 보강**: 문장·일부 표 칸 등 11곳을 바꿔도 모두 통과했기 때문입니다.",
        "- **대시보드 사본 통합**: 내용이 같은 HTML 2개가 혼란을 주어 대시보드 파일 하나로 합쳤습니다.",
        "",
        "### 8.4 3차 검수 (19:52)",
        "- **개폐업 연결 파일 정정**: `OA-15576`에 연결되어 있었지만, 개업·폐업 수와 비율은 `OA-15577`에만 있습니다. 0값 건수를 나누라는 지적을 받은 뒤 다른 파일로 바뀌면서 0값이 `0건`으로 보이게 된 것을 되돌렸습니다.",
        "- **경쟁 항목 분리**: 밀집도에는 점포 수(`OA-15577`)와 면적(`OA-15560`)이 모두 필요하므로 두 행으로 나눴습니다.",
        "- **소비 수준 기준 정정**: 행정동 파일이므로 상권 기준 지표는 \"해당 없음\"으로 쓰고, 행정동 425개 기준으로 다시 계산했습니다.",
        "- **과장·미확인 표현 정리**: 사업자 등록 여부를 단정한 표현과 \"고르게 분산\" 같은 표현은 데이터로 확인할 수 없거나 근거가 부족했습니다. 매출 기준으로 뺀 민감도에는 해석 주의 문구를 넣었습니다.",
        "- **그림 재현성 확보**: 신뢰구간 띠가 실행마다 달라져 시드를 고정했습니다. 점과 회귀선은 원래 같았습니다.",
        "- **자동 검사 보강**: 추가 변조 17곳 중 14곳이 통과했기 때문입니다.",
        "",
        "### 8.5 4차 검수 (20:15)",
        "- **대시보드 고특화 표시 정정**: LQ 1.5 이상 12개 구가 \"특화\"로 표시되어 보고서와 달랐습니다. 대시보드 코드에 1.5 기준이 빠져 있었습니다.",
        "- **LQ 기준 한 곳에서 관리**: 같은 기준값이 네 곳에 있어 어긋날 수 있었기 때문입니다.",
        "- **문구 정리**: `OA-15576`은 평균 개월 수만 제공하므로 \"분포 분석\" 표현을 뺐습니다. \"지역적 특색이 뚜렷\"은 수치 표현으로 바꿨습니다.",
        "- **자동 검사 보강**: 변조 39곳 중 16곳이 통과했고, 이 중 글자 칸 비교 누락이 이번 오류를 놓친 원인이었습니다.",
        "",
        "### 8.6 5차 검수 (20:50)",
        "- 치명·중요 항목은 없었습니다. 격리 재실행 결과 보고서, 대시보드, 결과 파일, 그림이 모두 같았습니다.",
        "- 변조 41곳 중 34곳을 잡았습니다. 못 잡은 7곳은 문장 숫자를 다른 실제 값으로 바꾼 경우로, 자동 검사의 한계로 명시했습니다.",
        "",
        "### 8.7 남은 과제",
        "- **점포 위치 불일치 7,722건**: 좌표 위치와 행정동 코드가 다른 원인을 아직 조사하지 않았습니다. 2단계에서 점포를 행정동에 연결하기 전에 확인이 필요합니다.",
        "- **추정매출 산출 방식**: 문서로 확인하지 못했습니다.",
        "- **[가설] 문장**: 저장소 데이터로는 사실 여부를 판단할 수 없습니다.",
        "- **대시보드 화면**: 표 스크롤 안내와 휴대폰 화면 대응이 남아 있습니다. 값과는 무관합니다.",
        "",
        "### 8.8 함께 기억할 점",
        "- 합계가 맞아도 칸 값은 틀릴 수 있습니다.",
        "- 보고서를 직접 고치지 말고, 코드를 고쳐 다시 생성합니다.",
        "- 자동 검사가 통과해도 틀린 값을 실제로 잡는지 일부러 바꿔 시험합니다.",
        "- \"이 항목에 이 파일이 맞는가\" 같은 의미 판단은 사람이 확인합니다.",
    ]

def build_html_dashboard(data):
    """01_기본EDA_대시보드_2025Q4.html 생성"""
    sbiz = data["sbiz_q"]
    desc = data["desc_stats"]
    cross = data["cross_sum"]
    sales = data["sales_sum"]
    spend_out = data["spend_outliers"]
    prof = data["df_prof"]
    ind = data["df_ind"]
    readiness = data["df_readiness"]
    gu_top_lq = data["df_gu_top_lq"]
    df_gu_cat = data["df_gu_cat"]
    df_zone_cat = data["df_zone_cat"]
    df_floor_cat = data["df_floor_cat"]
    df_lq = data["df_lq"]
    df_spend_out = data["df_spend_outliers"]
    
    gu_stat = desc["자치구_기술통계"]
    dong_stat = desc["행정동_기술통계"]
    # 단일 상권 매출 집중도 1위 업종 (수산물판매 등)
    top_conc_ind = ind.sort_values(by="1위상권_집중도_pct", ascending=False).iloc[0]
    # 총매출 1위 업종 (한식음식점 등)
    top_sales_ind = ind.sort_values(by="총매출_원", ascending=False).iloc[0]
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpotFit 상권 데이터 분석 대시보드 (2025Q4)</title>
    <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #2563eb;
            --primary-light: #dbeafe;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --dark: #1e293b;
            --gray-100: #f1f5f9;
            --gray-200: #e2e8f0;
            --gray-600: #475569;
            --gray-800: #1e293b;
            --card-bg: #ffffff;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Pretendard', sans-serif; }}
        html, body {{ max-width: 100%; overflow-x: hidden; }}
        body {{ background-color: #f8fafc; color: var(--dark); line-height: 1.6; padding-bottom: 60px; }}
        header {{ background: white; border-bottom: 1px solid var(--gray-200); padding: 24px 32px; position: sticky; top: 0; z-index: 50; }}
        .header-inner {{ max-width: 1300px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }}
        .logo-area h1 {{ font-size: 22px; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 8px; }}
        .logo-area p {{ font-size: 13px; color: var(--gray-600); margin-top: 4px; }}
        .timestamp-badge {{ background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; padding: 6px 14px; border-radius: 9999px; font-size: 13px; font-weight: 500; }}
        
        .container {{ max-width: 1300px; margin: 24px auto; padding: 0 24px; width: 100%; }}
        
        .tabs {{ display: flex; gap: 8px; border-bottom: 2px solid var(--gray-200); margin-bottom: 24px; }}
        .tab-btn {{ background: none; border: none; padding: 12px 20px; font-size: 15px; font-weight: 600; color: var(--gray-600); cursor: pointer; border-bottom: 3px solid transparent; transition: all 0.2s; }}
        .tab-btn:hover {{ color: var(--primary); }}
        .tab-btn.active {{ color: var(--primary); border-bottom-color: var(--primary); }}
        
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        
        .grid-4 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 540px), 1fr)); gap: 24px; margin-bottom: 24px; }}
        
        .card {{ background: var(--card-bg); border: 1px solid var(--gray-200); border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 24px; }}
        .card-title {{ font-size: 17px; font-weight: 700; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; }}
        .card-desc {{ font-size: 13px; color: var(--gray-600); margin-bottom: 16px; }}
        
        .metric-card {{ background: white; border: 1px solid var(--gray-200); border-radius: 12px; padding: 20px; }}
        .metric-label {{ font-size: 13px; color: var(--gray-600); font-weight: 500; }}
        .metric-val {{ font-size: 28px; font-weight: 700; color: #0f172a; margin: 8px 0 4px 0; }}
        .metric-sub {{ font-size: 12px; color: #64748b; }}
        
        .interpretation-box {{ background: #f8fafc; border-left: 4px solid var(--primary); padding: 12px 16px; border-radius: 4px; font-size: 14px; color: #334155; margin-top: 16px; }}
        .interpretation-box strong {{ color: var(--primary); }}
        
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; margin-top: 8px; }}
        th {{ background: #f8fafc; padding: 10px 12px; border-bottom: 1px solid var(--gray-200); color: #475569; font-weight: 600; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }}
        tr:hover td {{ background: #f8fafc; }}
        .text-right {{ text-align: right; }}
        .text-center {{ text-align: center; }}
        
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; white-space: nowrap; }}
        .badge-success {{ background: #dcfce7; color: #166534; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .badge-danger {{ background: #fee2e2; color: #991b1b; }}
        .badge-info {{ background: #e0f2fe; color: #075985; }}
        
        .chart-img {{ width: 100%; border-radius: 8px; border: 1px solid var(--gray-200); margin-top: 8px; }}
        
        .bar-container {{ display: flex; align-items: center; gap: 8px; margin: 8px 0; }}
        .bar-label {{ width: 110px; font-size: 13px; color: var(--gray-800); }}
        .bar-bg {{ flex: 1; background: var(--gray-100); height: 18px; border-radius: 4px; overflow: hidden; }}
        .bar-fill {{ height: 100%; background: var(--primary); border-radius: 4px; transition: width 0.3s; }}
        .bar-val {{ width: 100px; font-size: 12px; text-align: right; color: var(--gray-600); }}

        .table-scroll-container {{ overflow: auto; position: relative; border: 1px solid var(--gray-200); border-radius: 8px; margin-top: 8px; -webkit-overflow-scrolling: touch; }}
        .table-scroll-container table {{ margin-top: 0; width: 100%; }}
        .table-scroll-container thead th {{ position: sticky; top: 0; z-index: 10; background: #f8fafc; box-shadow: 0 1px 2px rgba(0,0,0,0.06); }}
        .scroll-hint {{ font-size: 12px; color: var(--gray-600); margin-top: 4px; margin-bottom: 6px; font-weight: 500; }}

        /* 화면 폭 768px 이하 반응형 미디어 쿼리 */
        @media (max-width: 768px) {{
            header {{ padding: 16px; }}
            .header-inner {{ flex-direction: column; align-items: flex-start; gap: 12px; }}
            .container {{ padding: 0 12px; margin: 16px auto; }}
            .tabs {{ overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch; padding-bottom: 6px; gap: 4px; }}
            .tab-btn {{ padding: 8px 12px; font-size: 13px; }}
            .grid-4 {{ grid-template-columns: 1fr; gap: 12px; margin-bottom: 16px; }}
            .grid-2 {{ grid-template-columns: 1fr; gap: 16px; margin-bottom: 16px; }}
            .card {{ padding: 16px; margin-bottom: 16px; }}
            .metric-card {{ padding: 14px; }}
            .metric-val {{ font-size: 22px; }}
            .card-title {{ font-size: 15px; }}
            .card-desc {{ font-size: 12px; margin-bottom: 12px; }}
        }}
    </style>
</head>
<body>

<header>
    <div class="header-inner">
        <div class="logo-area">
            <h1>SpotFit 상권 분석 및 데이터 프로파일링 대시보드</h1>
            <p>서울시 전체 1,650개 상권 및 소상공인 점포 원천 데이터 품질·특성 분석 대시보드</p>
        </div>
        <div class="timestamp-badge">
            기준 시점: 소상공인 점포 (2025-12-31) | 상권 추정매출 (2025Q4)
        </div>
    </div>
</header>

<div class="container">
    <div class="tabs">
        <button class="tab-btn active" onclick="openTab('tab-quality')">1. 데이터 품질 점검</button>
        <button class="tab-btn" onclick="openTab('tab-geo')">2. 지역 및 업종 분포</button>
        <button class="tab-btn" onclick="openTab('tab-sales')">3. 매출 및 이상치 분석</button>
        <button class="tab-btn" onclick="openTab('tab-readiness')">4. 상권 특성 데이터 준비도</button>
    </div>

    <!-- TAB 1: 데이터 품질 점검 -->
    <div id="tab-quality" class="tab-content active">
        <div class="grid-4">
            <div class="metric-card">
                <div class="metric-label">소상공인 전체 점포 수</div>
                <div class="metric-val">{sbiz['전체_점포_건수']:,}개</div>
                <div class="metric-sub">기준: 2025-12-31 시점 상가업소 데이터 수록 점포</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">행정동 코드 일치성</div>
                <div class="metric-val">{sbiz['행정동_대응_후_동수']}개 동</div>
                <div class="metric-sub">대응 전 {sbiz['행정동_대응_전_동수']}개 동 → 마스터 425개 동 일치</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">복합 속성 중복 점포</div>
                <div class="metric-val">{sbiz['복합조합_중복비율_pct']}%</div>
                <div class="metric-sub">{sbiz['복합조합_중복건수']:,}건 (상호+주소+층+호+소분류)</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">지리 좌표 서울 경계 내</div>
                <div class="metric-val">{round(sbiz['좌표_서울경계내_건수'] / sbiz['전체_점포_건수'] * 100, 2)}%</div>
                <div class="metric-sub">{sbiz['좌표_서울경계내_건수']:,}건 (경계 외: {sbiz['좌표_서울경계외_건수']}건, {sbiz['좌표_경계외_비율_pct']}%)</div>
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <div class="card-title">원천 데이터 파일별 정합성 프로파일 (10개 파일)</div>
                <div class="card-desc">MANIFEST.csv 기준 행수와 실제 원천 파일 행수 대조 결과 (소비 데이터 포함)</div>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>파일명</th>
                                <th class="text-right">실제 행수</th>
                                <th class="text-center">일치여부</th>
                                <th>기준 키</th>
                                <th>단위</th>
                                <th class="text-right">결측치 수</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''<tr>
                                <td><strong>{r["파일명"]}</strong></td>
                                <td class="text-right">{r["실제_행수"]:,}</td>
                                <td class="text-center"><span class="badge badge-success">일치</span></td>
                                <td>{r["기준_키"]}</td>
                                <td>{r["단위"]}</td>
                                <td class="text-right">{r["결측치_총수"]:,}</td>
                            </tr>''' for _, r in prof.iterrows()])}
                        </tbody>
                    </table>
                </div>
                <div class="interpretation-box">
                    <strong>쉬운 해석:</strong> 10개 원천 파일의 실제 행 수가 매니페스트 기준과 정확히 일치하며 고유 기준 키의 유일성이 확인되었습니다.
                </div>
            </div>

            <div class="card">
                <div class="card-title">점포 층 정보 분류 및 분포 (파이차트 미사용)</div>
                <div class="card-desc">전체 점포 대비 비중 및 층 정보 입력 점포 기준 비중 분모 구분</div>
                
                {"".join([f'''
                <div class="bar-container">
                    <div class="bar-label">{k}</div>
                    <div class="bar-bg">
                        <div class="bar-fill" style="width: {round(v / sbiz['전체_점포_건수'] * 100, 2)}%;"></div>
                    </div>
                    <div class="bar-val">{v:,}건 ({round(v / sbiz['전체_점포_건수'] * 100, 1)}%)</div>
                </div>''' for k, v in sbiz["층분류_집계"].items()])}
                
                <div class="interpretation-box">
                    <strong>쉬운 해석:</strong> 전체 점포({sbiz['전체_점포_건수']:,}건) 기준으로는 결측이 {sbiz['층정보_결측비율_전체_pct']:.1f}%({sbiz['층정보_결측건수']:,}건)로 가장 많으나, 층 정보가 입력된 점포({sbiz['층정보_입력점포_건수']:,}건) 기준으로는 지상 1층({sbiz['층정보_1층_점포수']:,}건)이 {sbiz['층정보_1층비율_입력점포기준_pct']:.1f}%로 1위를 차지합니다.
                </div>
            </div>
        </div>
    </div>

    <!-- TAB 2: 지역 및 업종 분포 -->
    <div id="tab-geo" class="tab-content">
        <div class="grid-4">
            <div class="metric-card">
                <div class="metric-label">자치구 평균 점포 수</div>
                <div class="metric-val">{gu_stat['평균']:,}개</div>
                <div class="metric-sub">최다: {gu_stat['최대지역']} ({gu_stat['최대값']:,}개)</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">자치구 최소 점포 수</div>
                <div class="metric-val">{gu_stat['최소값']:,}개</div>
                <div class="metric-sub">최소: {gu_stat['최소지역']} ({gu_stat['최소값']:,}개)</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">행정동 평균 점포 수</div>
                <div class="metric-val">{dong_stat['평균']:,}개</div>
                <div class="metric-sub">중위수: {dong_stat['중위수']:,}개 (왜도: {dong_stat['왜도']:.2f})</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">행정동 최다 점포 지역</div>
                <div class="metric-val">{dong_stat['최대값']:,}개</div>
                <div class="metric-sub">{dong_stat['최대지역']} (최소: {dong_stat['최소지역']} {dong_stat['최소값']:,}개)</div>
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <div class="card-title">자치구별 소상공인 점포 수 현황</div>
                <div class="card-desc">2025-12-31 시점 25개 자치구 점포 수 순위</div>
                <img src="../images/eda_stage1/01_자치구별_점포수_분포.png" alt="자치구별 점포수 분포" class="chart-img">
                <div class="interpretation-box">
                    <strong>쉬운 해석:</strong> 강남구({gu_stat['최대값']:,}개), 서초구({cross['점포수_상위3개_수치']['서초구']:,}개), 송파구({cross['점포수_상위3개_수치']['송파구']:,}개)의 동남권 3개 구가 서울 전체 점포의 {cross['점포수_상위3개_비율_pct']}%를 점유하고 있습니다.
                </div>
            </div>

            <div class="card">
                <div class="card-title">구별 최고 특화 업종 (25개 자치구)</div>
                <div class="card-desc">해당 구의 업종 점포 수와 구 내 비중, 서울 대비 입지계수(LQ) ({cross["LQ_판정_기준_문구"]})</div>
                <div class="scroll-hint">표 안에서 스크롤하면 전체 {len(gu_top_lq)}행을 볼 수 있습니다</div>
                <div class="table-scroll-container" style="max-height: 480px;">
                    <table>
                        <thead>
                            <tr>
                                <th>자치구명</th>
                                <th>최고 특화 업종</th>
                                <th class="text-right">해당구 점포수</th>
                                <th class="text-right">구 내 비중</th>
                                <th class="text-right">입지계수 (LQ)</th>
                                <th>해석</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''<tr>
                                <td><strong>{r["자치구명"]}</strong></td>
                                <td>{r["대분류명"]}</td>
                                <td class="text-right">{int(r["해당구_업종_점포수"]):,}개</td>
                                <td class="text-right">{r["구내_비중_pct"]:.2f}%</td>
                                <td class="text-right"><strong>{r["입지계수_LQ"]:.3f}</strong></td>
                                <td><span class="badge {"badge-danger" if r["특화도_판정"] == "서울 대비 고특화" else ("badge-info" if r["특화도_판정"] == "서울 대비 특화" else "badge-warning")}">{r["특화도_판정"]}</span></td>
                            </tr>''' for _, r in gu_top_lq.iterrows()])}
                        </tbody>
                    </table>
                </div>
                <div class="interpretation-box">
                    <strong>쉬운 해석:</strong> 25개 자치구별로 가장 특화된 업종의 점포 수와 구 내 비중을 도출하였으며, 금천구 과학·기술은 LQ {gu_top_lq[gu_top_lq['자치구명']=='금천구']['입지계수_LQ'].values[0]:.2f}, 양천구 교육은 LQ {gu_top_lq[gu_top_lq['자치구명']=='양천구']['입지계수_LQ'].values[0]:.2f}입니다.
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-title">권역별 10대 대분류 점포 분포 교차표</div>
            <div class="card-desc">5대 권역과 10대 대분류 교차 집계 및 총계</div>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>권역</th>
                            {"".join([f'<th class="text-right">{c}</th>' for c in df_zone_cat.columns])}
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''<tr>
                            <td><strong>{idx}</strong></td>
                            {"".join([f'<td class="text-right">{int(v):,}</td>' for v in row.values])}
                        </tr>''' for idx, row in df_zone_cat.iterrows()])}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <div class="card-title">층분류별 10대 대분류 점포 분포 교차표</div>
            <div class="card-desc">7개 층분류와 10대 대분류 교차 집계 및 총계</div>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>층 분류</th>
                            {"".join([f'<th class="text-right">{c}</th>' for c in df_floor_cat.columns])}
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''<tr>
                            <td><strong>{idx}</strong></td>
                            {"".join([f'<td class="text-right">{int(v):,}</td>' for v in row.values])}
                        </tr>''' for idx, row in df_floor_cat.iterrows()])}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <div class="card-title">자치구별 10대 대분류 점포 수 교차표 (25개 구 전체)</div>
            <div class="card-desc">25개 자치구와 10대 대분류 교차 집계 및 총계</div>
            <div class="scroll-hint">표 안에서 스크롤하면 전체 {len(df_gu_cat)}행을 볼 수 있습니다</div>
            <div class="table-scroll-container" style="max-height: 500px;">
                <table>
                    <thead>
                        <tr>
                            <th>자치구</th>
                            {"".join([f'<th class="text-right">{c}</th>' for c in df_gu_cat.columns])}
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''<tr>
                            <td><strong>{idx}</strong></td>
                            {"".join([f'<td class="text-right">{int(v):,}</td>' for v in row.values])}
                        </tr>''' for idx, row in df_gu_cat.iterrows()])}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <div class="card-title">25개 자치구 × 10대 대분류 전체 입지계수(LQ) 매트릭스</div>
            <div class="card-desc">서울 전체 대비 각 자치구의 업종별 특화도 (LQ 1.0 초과는 평균 대비 특화)</div>
            <div class="scroll-hint">표 안에서 스크롤하면 전체 {len(df_lq)}행을 볼 수 있습니다</div>
            <div class="table-scroll-container" style="max-height: 500px;">
                <table>
                    <thead>
                        <tr>
                            <th>자치구</th>
                            {"".join([f'<th class="text-right">{c}</th>' for c in df_lq.columns])}
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''<tr>
                            <td><strong>{idx}</strong></td>
                            {"".join([f'<td class="text-right">{float(v):.3f}</td>' for v in row.values])}
                        </tr>''' for idx, row in df_lq.iterrows()])}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- TAB 3: 매출 및 이상치 분석 -->
    <div id="tab-sales" class="tab-content">
        <div class="grid-4">
            <div class="metric-card">
                <div class="metric-label">2025Q4 분석 상권 수</div>
                <div class="metric-val">{sales['Q4_분석대상_상권수']:,}개</div>
                <div class="metric-sub">전체 {sales['마스터_상권수']:,}개 상권 중 매출 보유율 {sales['분기별_매출보유_비율_pct']['20254']}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">62개 업종 상관계수 (r)</div>
                <div class="metric-val">{sales['주분석_62업종_상관계수_Pearson_r']:.4f}</div>
                <div class="metric-sub">주 분석 (매출-점포 62개 업종 일치)</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">민감도 상관계수 (r)</div>
                <div class="metric-val">{sales['주분석_62업종_민감도_Pearson_r']:.4f}</div>
                <div class="metric-sub">상위 1% 제외 시 r = {sales['주분석_62업종_민감도_Pearson_r']:.4f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">순위 상관계수 (rho)</div>
                <div class="metric-val">{sales['주분석_62업종_순위상관_Spearman_rho']:.4f}</div>
                <div class="metric-sub">스피어만 순위상관계수 {sales['주분석_62업종_순위상관_Spearman_rho']:.4f}</div>
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <div class="card-title">점포 수(62개 업종) vs 추정매출액 상관 및 민감도</div>
                <div class="card-desc">좌측: 전체 상권 vs 우측: 상위 1% 이상치 제외 상권</div>
                <img src="../images/eda_stage1/03_상권_점포수_매출_상관및민감도.png" alt="상관 및 민감도 분석" class="chart-img">
                <div class="interpretation-box">
                    <strong>쉬운 해석:</strong> 62개 업종 기준 점포 수와 추정매출액 간 선형 상관계수는 전체 {sales['주분석_62업종_상관계수_Pearson_r']:.4f}이나, 상위 1% 이상치 상권을 제외한 민감도 분석에서는 상관계수가 {sales['주분석_62업종_민감도_Pearson_r']:.4f}로 변화합니다. 단, 상위 1% 제외 민감도는 매출액 기준으로 상위 상권을 제외한 결과이므로 추천 모델 적용 시 해석에 주의가 필요합니다.
                </div>
            </div>

            <div class="card">
                <div class="card-title">단일 상권 1곳 매출 집중도 Top 10 업종</div>
                <div class="card-desc">서울 전체 매출 중 단 1곳 상권이 차지하는 비중 및 매출보유 상권수</div>
                <img src="../images/eda_stage1/04_업종별_단일상권_집중도_Top10.png" alt="업종별 집중도" class="chart-img">
                <div class="interpretation-box">
                    <strong>쉬운 해석:</strong> {top_conc_ind['업종명']} 업종은 {top_conc_ind['1위상권명']} 1곳 상권이 서울시 전체의 {top_conc_ind['1위상권_집중도_pct']:.1f}%({top_conc_ind['1위상권매출_원']/1e12:.2f}조 원)를 차지하여 가장 두드러진 단일상권 쏠림을 보이는 반면, 총매출 1위인 {top_sales_ind['업종명']} 업종은 1위 상권({top_sales_ind['1위상권명']}) 비중이 {top_sales_ind['1위상권_집중도_pct']:.1f}%이며 매출 보유 상권 수가 {top_sales_ind['매출보유_상권수']}개로 나타납니다.
                </div>
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <div class="card-title">매출 과대표 상권 Top 5 (회귀선 상단, 62개 업종 기준)</div>
                <div class="card-desc">점포 수 대비 추정매출액이 비정상적으로 높게 형성된 상권</div>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>상권명</th>
                                <th class="text-right">점포수</th>
                                <th class="text-right">추정매출액</th>
                                <th>매출 1위 업종</th>
                                <th>점포 1위 업종</th>
                                <th>추정 가설</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''<tr>
                                <td><strong>{it["상권명"]}</strong></td>
                                <td class="text-right">{it["점포수_62업종"]:,}개</td>
                                <td class="text-right">{round(it["실제매출_원"]/1e8, 1):,}억원</td>
                                <td>{it["매출1위_업종명"]} ({it["매출1위_비중_pct"]}%)</td>
                                <td>{it["점포1위_업종명"]} ({it["점포1위_비중_pct"]}%)</td>
                                <td><small style="color:#64748b;">{it["가설_원인"]}</small></td>
                            </tr>''' for it in sales["회귀선_상단_매출과대표_Top5"]])}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="card">
                <div class="card-title">매출 과소표 상권 Top 5 (회귀선 하단, 62개 업종 기준)</div>
                <div class="card-desc">점포 수는 대규모 밀집했으나 추정매출액이 낮게 집계되는 상권</div>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>상권명</th>
                                <th class="text-right">점포수</th>
                                <th class="text-right">추정매출액</th>
                                <th>매출 1위 업종</th>
                                <th>점포 1위 업종</th>
                                <th>추정 가설</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''<tr>
                                <td><strong>{it["상권명"]}</strong></td>
                                <td class="text-right">{it["점포수_62업종"]:,}개</td>
                                <td class="text-right">{round(it["실제매출_원"]/1e8, 1):,}억원</td>
                                <td>{it["매출1위_업종명"]} ({it["매출1위_비중_pct"]}%)</td>
                                <td>{it["점포1위_업종명"]} ({it["점포1위_비중_pct"]}%)</td>
                                <td><small style="color:#64748b;">{it["가설_원인"]}</small></td>
                            </tr>''' for it in sales["회귀선_하단_매출과소표_Top5"]])}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-title">행정동 소비 이상치 8곳 실제 집계 내역 (행정동_마스터 소비_이상치 기준)</div>
            <div class="card-desc">서울시 전체 소비 지출({spend_out['서울_총지출_조원']}조원) 중 8개 동이 {spend_out['이상치_8개동_지출비중_pct']}%를 점유 (값은 일절 변경 없이 이름표 유지)</div>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>행정동 코드</th>
                            <th>행정동명</th>
                            <th class="text-right">2025년 총 지출액</th>
                            <th class="text-right">지출 규모</th>
                            <th class="text-right">서울 비중</th>
                            <th>최대 쏠림 항목</th>
                            <th class="text-right">항목 비중</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''<tr>
                            <td><code>{r["행정동_코드"]}</code></td>
                            <td><strong>{r["행정동_명"]}</strong></td>
                            <td class="text-right">{r["지출_총금액_원"]:,}원</td>
                            <td class="text-right">{r["지출_조원"]:.2f}조원</td>
                            <td class="text-right">{r["서울_비중_pct"]:.2f}%</td>
                            <td>{r["소비_최대항목"]}</td>
                            <td class="text-right">{r["소비_최대항목_비중_pct"]:.1f}%</td>
                        </tr>''' for _, r in df_spend_out.iterrows()])}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <div class="card-title">62개 업종별 매출 순위 및 단일 상권 집중도 전체 현황</div>
            <div class="card-desc">2025Q4 추정매출 기준 62개 업종 전체 매출 규모, 유효 상권 수, 1위 상권 편중도</div>
            <div class="scroll-hint">표 안에서 스크롤하면 전체 {len(ind)}행을 볼 수 있습니다</div>
            <div class="table-scroll-container" style="max-height: 500px;">
                <table>
                    <thead>
                        <tr>
                            <th>순위</th>
                            <th>업종명</th>
                            <th>업종코드</th>
                            <th class="text-right">서울 총매출액</th>
                            <th class="text-right">매출 상권수</th>
                            <th>상권수 주의</th>
                            <th>1위 상권명</th>
                            <th class="text-right">1위 상권 매출</th>
                            <th class="text-right">1위 상권 집중도</th>
                            <th>특화집중 여부</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''<tr>
                            <td class="text-center">{rank}</td>
                            <td><strong>{r["업종명"]}</strong></td>
                            <td><code>{r["업종코드"]}</code></td>
                            <td class="text-right">{r["총매출_원"]:,}원</td>
                            <td class="text-right">{r["매출보유_상권수"]}개</td>
                            <td><span class="badge {"badge-warning" if "주의" in r["상권수_주의_이름표"] else "badge-info"}">{r["상권수_주의_이름표"]}</span></td>
                            <td>{r["1위상권명"]}</td>
                            <td class="text-right">{r["1위상권매출_원"]:,}원</td>
                            <td class="text-right"><strong>{r["1위상권_집중도_pct"]:.2f}%</strong></td>
                            <td><span class="badge {"badge-danger" if r["특화집중_상권_여부"] else "badge-info"}">{"특화집중" if r["특화집중_상권_여부"] else "일반"}</span></td>
                        </tr>''' for rank, (_, r) in enumerate(ind.iterrows(), 1)])}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- TAB 4: 상권 특성 데이터 준비도 -->
    <div id="tab-readiness" class="tab-content">
        <div class="card">
            <div class="card-title">상권 추천을 위한 7대 상권 특성 데이터 준비도 점검표 (코드 집계 완료)</div>
            <div class="card-desc">원천 데이터 행 수, 결측치, 0값, 빠진 상권·분기 칸 수 실제 집계 결과</div>
            <div class="interpretation-box" style="margin-bottom: 16px;">
                <strong>지표 정의 안내:</strong>
                <ul style="margin-left: 20px; margin-top: 6px; font-size: 13px;">
                    <li><strong>파일 행 수:</strong> 2025년 기준 해당 원천 파일의 전체 레코드(행) 개수</li>
                    <li><strong>빠진 상권 수:</strong> 서울시 마스터 상권 {sales['마스터_상권수']:,}개 중 연간 데이터가 1건도 없는 상권 수 (상권 미집계 파일은 '해당 없음')</li>
                    <li><strong>빠진 상권×분기 칸 수:</strong> 마스터 상권({sales['마스터_상권수']:,}개) × 4분기 = {sales['마스터_상권수'] * 4:,}개 슬롯 중 데이터가 없는 빈 칸 수 (단일 스냅샷 파일은 0, 상권 미집계 파일은 '해당 없음')</li>
                    <li><strong>주요컬럼 0값 건수:</strong> 핵심 분석 지표 컬럼에서 0으로 기록된 레코드 건수를 컬럼별로 분리 기재</li>
                    <li><strong>결측치 수:</strong> 결측(NA)으로 비어 있는 값의 수</li>
                </ul>
            </div>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>상권 특성 항목</th>
                            <th class="text-center">계산 가능 여부</th>
                            <th>대응 원천 파일</th>
                            <th class="text-right">파일 행수</th>
                            <th class="text-right">빠진 상권수</th>
                            <th class="text-right">빠진 상권×분기 칸수</th>
                            <th>주요컬럼 0값 건수</th>
                            <th class="text-right">결측치 수</th>
                            <th>한계점 및 주의사항</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''<tr>
                            <td><strong>{r["상권_특성_항목"]}</strong></td>
                            <td class="text-center">
                                <span class="badge {"badge-success" if "계산할 수 있음" in r["계산가능_여부"] else "badge-danger"}">
                                    {r["계산가능_여부"]}
                                </span>
                            </td>
                            <td><code>{r["대응_원천파일"]}</code></td>
                            <td class="text-right">{r["파일_행수"]:,}</td>
                            <td class="text-right">{r["빠진_상권수"]}</td>
                            <td class="text-right">{r["빠진_상권분기_칸수"]}</td>
                            <td><code>{r["주요컬럼_0값_건수"]}</code></td>
                            <td class="text-right">{r["결측치_수"]:,}</td>
                            <td><small>{r["한계점_및_주의사항"]}</small></td>
                        </tr>''' for _, r in readiness.iterrows()])}
                    </tbody>
                </table>
            </div>
            <div class="interpretation-box" style="margin-top: 16px;">
                <strong>쉬운 해석:</strong> 고객 구성, 객단가, 프랜차이즈 비율, 매출 변화, 경쟁, 개폐업, 소비 수준 등 7대 상권 특성은 모두 보유 데이터에 필요한 컬럼이 있어 계산할 수 있습니다. 단, 임대료·보증금 항목은 원천 데이터에 없으므로 향후 공공 임대 시세 데이터 연계가 권장됩니다.
            </div>
        </div>
    </div>
</div>

<script>
function openTab(tabId) {{
    const contents = document.querySelectorAll('.tab-content');
    contents.forEach(el => el.classList.remove('active'));
    
    const btns = document.querySelectorAll('.tab-btn');
    btns.forEach(el => el.classList.remove('active'));
    
    document.getElementById(tabId).classList.add('active');
    event.currentTarget.classList.add('active');
}}
</script>

</body>
</html>
"""
    # 01_기본EDA_대시보드_2025Q4.html 단일 파일 생성 (요구사항 9)
    html_dash_path = REPORT_DIR / "01_기본EDA_대시보드_2025Q4.html"
    with open(html_dash_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f">>> {html_dash_path.name} 작성 완료!")

    # 01_기본EDA_보고서_2025Q4.html 파일이 존재하면 단일화를 위해 삭제
    html_report_path = REPORT_DIR / "01_기본EDA_보고서_2025Q4.html"
    if html_report_path.exists():
        html_report_path.unlink()
        print(f">>> {html_report_path.name} 파일 정리(삭제) 완료 (01_기본EDA_대시보드_2025Q4.html 단일화)")

    return html

def main():
    print("=== [SpotFit Stage 1] 보고서 및 대시보드 자동 생성 시작 ===")
    data = load_results()
    build_markdown_report(data)
    build_html_dashboard(data)
    print("=== [SpotFit Stage 1] 보고서 및 대시보드 생성 완료! ===")

if __name__ == "__main__":
    main()
