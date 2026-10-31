"""
1단계 데이터 프로파일링 및 기본 EDA 자동 검증 스크립트 (재검수 결과 반영 개정본)

검증 원칙:
1. 보고서(Markdown) 및 대시보드(HTML)의 모든 표를 파싱하여,
   숫자가 포함된 칸은 결과 파일(data/processed/eda_stage1/*.csv, *.json)과 대조 검증한다.
   (잔차표 1위 금액·비중, 기술통계 최소·최대 및 코드, 값 범위, 0값 건수, 소비 조원·항목 비중, 특화집중 태그, 주의 라벨 포함)
2. 비숫자 텍스트 칸은 실제 텍스트 내용과 컬럼 기준에 따라 분류하여 내역을 출력한다.
3. 보고서 본문 및 대시보드 본문 문장 속 숫자를 추출해 결과 파일 값과 대조한다.
4. 잔차 분석 문장의 [가설] 및 표 밖 3개 지정 위치의 [가설] 표기, 주의 라벨(50개/100개 미만) 부착을 검사한다.
5. 변조 시험 15종을 수행하여 검증기가 비정상 값을 감지·차단하는지 확인한다.
6. 금지어 9종 및 주관적 단정 표현을 검사한다.
7. 자동 검사가 보증하지 못하는 한계 범위를 명확히 기술하며, "전수"나 "완벽" 등 과장 표현을 사용하지 않는다.
"""
import sys
import os
import json
import re
from pathlib import Path
from html.parser import HTMLParser
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
STAGE1_DATA_DIR = DATA_DIR / "processed" / "eda_stage1"
REPORT_DIR = PROJECT_DIR / "report"

# LQ 판정 기준 상수 및 함수 (단일 정의 원칙)
LQ_HIGH_THRESHOLD = 1.5
LQ_MID_THRESHOLD = 1.2

def get_lq_label(lq_val: float) -> str:
    """입지계수(LQ) 판정 함수 (기준: 1.5 이상 고특화, 1.2 이상 1.5 미만 특화, 1.2 미만 평균 수준)"""
    if lq_val >= LQ_HIGH_THRESHOLD:
        return "서울 대비 고특화"
    elif lq_val >= LQ_MID_THRESHOLD:
        return "서울 대비 특화"
    else:
        return "평균 수준"

# ------------------------------------------------------------------------------
# 헬퍼 함수: 텍스트 및 숫자 정제
# ------------------------------------------------------------------------------
def clean_num(val_str):
    """표 셀 문자열에서 볼드, 코드, 콤마 등을 제거하고 숫자 문자열 반환"""
    s = str(val_str).replace('**', '').replace('`', '').replace(',', '').strip()
    m = re.search(r'-?\d+(?:\.\d+)?', s)
    if m:
        return m.group(0)
    return s

def parse_markdown_tables(md_text):
    """마크다운 문서 내 파이프(|) 구분 표들을 파싱하여 2차원 리스트 목록으로 반환"""
    lines = md_text.splitlines()
    tables = []
    current_table = []
    in_table = False
    for line in lines:
        line_str = line.strip()
        if line_str.startswith('|') and line_str.endswith('|'):
            parts = [p.strip() for p in line_str.split('|')[1:-1]]
            is_sep = all(set(p).issubset({'-', ':', ' '}) and '-' in p for p in parts)
            if is_sep:
                continue
            current_table.append(parts)
            in_table = True
        else:
            if in_table and current_table:
                tables.append(current_table)
                current_table = []
            in_table = False
    if in_table and current_table:
        tables.append(current_table)
    return tables

class HTMLTableParser(HTMLParser):
    """HTML 문서 내 <table> 태그들을 파싱하여 2차원 리스트 목록으로 반환"""
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = []
        self.current_row = []
        self.current_cell = []
        self.in_table = False
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
            self.current_table = []
        elif tag == "tr" and self.in_table:
            self.current_row = []
        elif tag in ("td", "th") and self.in_table:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_table:
            self.in_cell = False
            cell_text = "".join(self.current_cell).strip()
            self.current_row.append(cell_text)
        elif tag == "tr" and self.in_table:
            if self.current_row:
                self.current_table.append(self.current_row)
        elif tag == "table":
            self.in_table = False
            if self.current_table:
                self.tables.append(self.current_table)

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)

def parse_html_tables(html_text):
    parser = HTMLTableParser()
    parser.feed(html_text)
    return parser.tables

# ------------------------------------------------------------------------------
# 검사 1: 데이터 집계 일관성 (총합, 부분합, 비율합 100%)
# ------------------------------------------------------------------------------
def test_1_data_integrity():
    print("[검사 1] 데이터 집계 일관성 검증 (총합, 부분합, 비율합 100%)")
    with open(STAGE1_DATA_DIR / "sbiz_quality.json", encoding="utf-8") as f:
        sbiz = json.load(f)
    with open(STAGE1_DATA_DIR / "cross_summary.json", encoding="utf-8") as f:
        cross = json.load(f)

    tot = sbiz["전체_점포_건수"]
    assert tot == sum(cross["대분류_점포수"].values()), "대분류 합계 불일치"
    assert tot == sum(cross["권역_점포수"].values()), "권역 합계 불일치"
    assert tot == sum(sbiz["층분류_집계"].values()), "층분류 합계 불일치"

    # 교차표 부분합 검사
    tables = [
        "cross_gu_category.csv",
        "cross_zone_category.csv",
        "cross_floor_category.csv"
    ]
    for fname in tables:
        df = pd.read_csv(STAGE1_DATA_DIR / fname, index_col=0, encoding="utf-8-sig")
        content = df.loc[df.index != "총계", df.columns != "총계"]
        row_totals = df.loc[df.index != "총계", "총계"]
        col_totals = df.loc["총계", df.columns != "총계"]
        grand_total = df.loc["총계", "총계"]

        for idx in content.index:
            assert int(content.loc[idx].sum()) == int(row_totals[idx]), f"[{fname}] 행 부분합 불일치: {idx}"
        for col in content.columns:
            assert int(content[col].sum()) == int(col_totals[col]), f"[{fname}] 열 부분합 불일치: {col}"
        assert int(grand_total) == tot, f"[{fname}] 전체 총계 불일치: {grand_total} != {tot}"

    # 비율 합계 검사
    zone_sum_pct = sum(cross["권역_비율_pct"].values())
    assert abs(zone_sum_pct - 100.0) <= 0.05, f"권역 비율합 오차 초과: {zone_sum_pct}"
    floor_sum_pct = sum(cross["층분류_비율_pct"].values())
    assert abs(floor_sum_pct - 100.0) <= 0.05, f"층분류 비율합 오차 초과: {floor_sum_pct}"

    print(f" -> 통과: 점포 총계({tot:,}건), 대분류/권역/층별 합계 및 3대 교차표 행·열 부분합, 비율합(100.0%) 일치")

# ------------------------------------------------------------------------------
# 검사 2: 마크다운 보고서 14개 표 전체 대조 및 비숫자 칸 사유 집계
# ------------------------------------------------------------------------------
def verify_markdown_tables(md_tables):
    print("[검사 2] 보고서(Markdown) 14개 표 숫자 칸 및 텍스트 칸 상세 대조")
    assert len(md_tables) >= 14, f"보고서 내 파싱된 표 개수 부족: {len(md_tables)} < 14"

    stats = {
        "compared_cells": 0,
        "skipped_text_cells": 0,
        "skip_reasons": {}
    }

    def record_skip(category_name, actual_content=""):
        stats["skipped_text_cells"] += 1
        stats["skip_reasons"][category_name] = stats["skip_reasons"].get(category_name, 0) + 1

    def match_val(actual_str, expected_num, tolerance=0.005):
        stats["compared_cells"] += 1
        a_clean = clean_num(actual_str)
        try:
            a_val = float(a_clean)
            e_val = float(expected_num)
            if abs(a_val - e_val) > tolerance:
                raise AssertionError(f"수치 불일치: 실제표='{actual_str}' ({a_val}) != 결과값={e_val} (오차: {abs(a_val-e_val)})")
        except ValueError:
            raise AssertionError(f"숫자 변환 실패: '{actual_str}'")

    # Table 1: 파일 프로파일 (10행)
    df_prof = pd.read_csv(STAGE1_DATA_DIR / 'file_profiles.csv', encoding='utf-8-sig')
    t1 = md_tables[0]
    for i, (_, r) in enumerate(df_prof.iterrows()):
        row = t1[i+1]
        assert r['파일명'] in row[0], f"파일명 불일치: {r['파일명']} not in {row[0]}"
        record_skip("원천 데이터 파일명")
        match_val(row[1], r['실제_행수'])
        match_val(row[2], r['매니페스트_행수'])
        record_skip("행수 일치여부 상태문구")
        match_val(row[4], r['열수'])
        record_skip("기준 키 컬럼정의")
        record_skip("키 유일성 여부")
        record_skip("기준 기간")
        record_skip("데이터 수집 단위")
        match_val(row[9], r['결측치_총수'])
        # 주요변수 값범위 문자열 대조 및 내부 수치 카운트
        assert row[10] == r['주요변수_값범위'], f"값범위 불일치: {row[10]} != {r['주요변수_값범위']}"
        for num in re.findall(r'[\d,]+(?:\.\d+)?', row[10]):
            stats["compared_cells"] += 1

    # Table 2: 층분류 분포 (8행)
    with open(STAGE1_DATA_DIR / 'sbiz_quality.json', encoding='utf-8') as f:
        sbiz = json.load(f)
    t2 = md_tables[1]
    f_items = list(sbiz["층분류_집계"].items()) + [("총계", sbiz["전체_점포_건수"])]
    tot_stores = sbiz["전체_점포_건수"]
    inp_stores = sbiz["층정보_입력점포_건수"]
    for i, (f_name, f_cnt) in enumerate(f_items):
        row = t2[i+1]
        record_skip("층위 분류 구분명")
        match_val(row[1], f_cnt)
        match_val(row[2], f_cnt / tot_stores * 100)
        if row[3] != "-":
            if f_name == "총계":
                match_val(row[3], 100.0)
            else:
                match_val(row[3], f_cnt / inp_stores * 100)
        else:
            record_skip("결측행 입력비율 제외표시(-)")
        record_skip("층별 특성 비고설명")

    # Table 3: 기술통계 (자치구/행정동 2행)
    df_desc = pd.read_csv(STAGE1_DATA_DIR / 'descriptive_stats_table.csv', encoding='utf-8-sig')
    t3 = md_tables[2]
    for i, (_, r) in enumerate(df_desc.iterrows()):
        row = t3[i+1]
        record_skip("공간 집계단위명")
        match_val(row[1], r['지역수'])
        match_val(row[2], r['평균'])
        match_val(row[3], r['중위수'])
        match_val(row[4], r['표준편차'])
        match_val(row[5], r['Q1'])
        match_val(row[6], r['Q3'])
        match_val(row[7], r['IQR'])
        # 최소값, 최소지역 명칭 및 코드 비교
        m_min = re.search(r'([\d,]+)\s*\(([^,]+),\s*`?(\d+)`?\)', row[8])
        if m_min:
            match_val(m_min.group(1), r['최소값'])
            match_val(m_min.group(3), r['최소지역_코드'])
            assert r['최소지역'] in m_min.group(2), f"최소지역명 불일치: {r['최소지역']} not in {m_min.group(2)}"
        # 최대값, 최대지역 명칭 및 코드 비교
        m_max = re.search(r'([\d,]+)\s*\(([^,]+),\s*`?(\d+)`?\)', row[9])
        if m_max:
            match_val(m_max.group(1), r['최대값'])
            match_val(m_max.group(3), r['최대지역_코드'])
            assert r['최대지역'] in m_max.group(2), f"최대지역명 불일치: {r['최대지역']} not in {m_max.group(2)}"
        match_val(row[10], r['왜도'])
        match_val(row[11], r['첨도'])

    # Table 4: 권역별 10대 대분류 (6행)
    df_zone = pd.read_csv(STAGE1_DATA_DIR / 'cross_zone_category.csv', index_col=0, encoding='utf-8-sig')
    t4 = md_tables[3]
    for r_idx, (z_name, z_row) in enumerate(df_zone.iterrows()):
        row = t4[r_idx+1]
        assert row[0] == z_name, f"권역명 불일치: {row[0]} != {z_name}"
        record_skip("생활권역 명칭")
        for c_idx, col_name in enumerate(df_zone.columns):
            match_val(row[c_idx+1], z_row[col_name])

    # Table 5: 층분류별 10대 대분류 (8행)
    df_floor = pd.read_csv(STAGE1_DATA_DIR / 'cross_floor_category.csv', index_col=0, encoding='utf-8-sig')
    t5 = md_tables[4]
    for r_idx, (f_name, f_row) in enumerate(df_floor.iterrows()):
        row = t5[r_idx+1]
        assert row[0] == f_name, f"층분류명 불일치: {row[0]} != {f_name}"
        record_skip("층위 분류 명칭")
        for c_idx, col_name in enumerate(df_floor.columns):
            match_val(row[c_idx+1], f_row[col_name])

    # Table 6: 자치구별 10대 대분류 (26행)
    df_gu = pd.read_csv(STAGE1_DATA_DIR / 'cross_gu_category.csv', index_col=0, encoding='utf-8-sig')
    t6 = md_tables[5]
    for r_idx, (g_name, g_row) in enumerate(df_gu.iterrows()):
        row = t6[r_idx+1]
        assert row[0] == g_name, f"자치구명 불일치: {row[0]} != {g_name}"
        record_skip("자치구 명칭")
        for c_idx, col_name in enumerate(df_gu.columns):
            match_val(row[c_idx+1], g_row[col_name])

    # Table 7: 25개 자치구 x 10대 대분류 전체 LQ 매트릭스 (26행)
    df_lq_all = pd.read_csv(STAGE1_DATA_DIR / 'lq_gu_category.csv', index_col=0, encoding='utf-8-sig')
    t7 = md_tables[6]
    for r_idx, (g_name, g_row) in enumerate(df_lq_all.iterrows()):
        row = t7[r_idx+1]
        assert row[0] == g_name, f"자치구명 불일치: {row[0]} != {g_name}"
        record_skip("자치구 명칭")
        for c_idx, col_name in enumerate(df_lq_all.columns):
            match_val(row[c_idx+1], g_row[col_name])

    # Table 8: 구별 최고 특화 업종 (25행)
    df_top_lq = pd.read_csv(STAGE1_DATA_DIR / 'lq_gu_top_specialization.csv', encoding='utf-8-sig')
    t8 = md_tables[7]
    for r_idx, (_, r) in enumerate(df_top_lq.iterrows()):
        row = t8[r_idx+1]
        assert row[0] == r['자치구명'], f"구명 불일치: {row[0]} != {r['자치구명']}"
        record_skip("자치구 명칭")
        assert r['대분류명'] in row[1], f"특화업종명 불일치: {r['대분류명']} not in {row[1]}"
        record_skip("최고 특화 대분류명")
        match_val(row[2], r['해당구_업종_점포수'])
        match_val(row[3], r['구내_전체_점포수'])
        match_val(row[4], r['구내_비중_pct'])
        match_val(row[5], r['서울_업종_점포수'])
        match_val(row[6], r['서울_비중_pct'])
        match_val(row[7], r['입지계수_LQ'])
        expected_lq_label = get_lq_label(r['입지계수_LQ'])
        assert expected_lq_label in row[8], f"보고서 LQ 판정문구 불일치: {expected_lq_label} not in {row[8]}"

    # Table 9: 점포 수 vs 추정매출액 상관분석 및 민감도 (4행)
    with open(STAGE1_DATA_DIR / 'sales_store_analysis.json', encoding='utf-8') as f:
        sales = json.load(f)
    t9 = md_tables[8]
    # 4개 행: 주분석, 민감도1, 민감도2, 민감도3
    comparisons = [
        ("주분석_62", sales['Q4_분석대상_상권수'], sales['주분석_62업종_상관계수_Pearson_r'], sales['주분석_62업종_순위상관_Spearman_rho']),
        ("민감도1_62", sales['민감도_분석대상_상권수'], sales['주분석_62업종_민감도_Pearson_r'], sales['주분석_62업종_민감도_Spearman_rho']),
        ("민감도2_100", sales['Q4_분석대상_상권수'], sales['민감도_100업종_상관계수_Pearson_r'], sales['민감도_100업종_순위상관_Spearman_rho']),
        ("민감도3_100", sales['민감도_분석대상_상권수'], sales['민감도_100업종_민감도_Pearson_r'], sales['민감도_100업종_민감도_Spearman_rho'])
    ]
    for idx, (label, n_trd, p_r, s_rho) in enumerate(comparisons, 1):
        record_skip("분석 구분 라벨")
        record_skip("업종 기준 라벨")
        match_val(t9[idx][2], n_trd)
        match_val(t9[idx][3], p_r)
        match_val(t9[idx][4], s_rho)
        record_skip("이상치 제외 기준설명")
        record_skip("분석 비고설명")

    # Table 10 & 11: 회귀 잔차 상단 Top 5 & 하단 Top 5 (각 5행)
    for table_idx, key_name in [(9, '회귀선_상단_매출과대표_Top5'), (10, '회귀선_하단_매출과소표_Top5')]:
        tbl = md_tables[table_idx]
        for r_idx, item in enumerate(sales[key_name]):
            row = tbl[r_idx+1]
            match_val(row[0], r_idx + 1) # 순위 번호 숫자 대조
            assert row[1] == item['상권명'], f"상권명 불일치: {row[1]} != {item['상권명']}"
            record_skip("상권 명칭")
            assert str(item['상권코드']) in row[2], f"상권코드 불일치: {item['상권코드']} not in {row[2]}"
            match_val(row[2], item['상권코드']) # 상권코드 숫자 대조
            match_val(row[3], item['점포수_62업종'])
            match_val(row[4], item['실제매출_원'])
            match_val(row[5], item['잔차_원'])
            # 매출 1위 업종명, 매출액, 비중 대조
            assert item['매출1위_업종명'] in row[6], f"매출1위 업종 불일치: {item['매출1위_업종명']} not in {row[6]}"
            record_skip("매출1위 업종명칭")
            m_s_amt = re.search(r'([\d,]+)원', row[6])
            m_s_pct = re.search(r'([\d.]+)%', row[6])
            if m_s_amt:
                match_val(m_s_amt.group(1), item['매출1위_매출액_원'])
            if m_s_pct:
                match_val(m_s_pct.group(1), item['매출1위_비중_pct'])
            # 점포 1위 업종명, 점포수, 비중 대조
            assert item['점포1위_업종명'] in row[7], f"점포1위 업종 불일치: {item['점포1위_업종명']} not in {row[7]}"
            record_skip("점포1위 업종명칭")
            m_st_cnt = re.search(r'([\d,]+)개', row[7])
            m_st_pct = re.search(r'([\d.]+)%', row[7])
            if m_st_cnt:
                match_val(m_st_cnt.group(1), item['점포1위_점포수'])
            if m_st_pct:
                match_val(m_st_pct.group(1), item['점포1위_비중_pct'])
            # 가설 원인 및 [가설] 태그 검사
            assert "[가설]" in row[8], f"가설 표기 누락: {row[8]}"
            record_skip("가설 원인 설명문구")

    # Table 12: 업종별 매출 순위 및 집중도 (62행)
    df_ind = pd.read_csv(STAGE1_DATA_DIR / 'industry_sales_concentration_2025Q4.csv', encoding='utf-8-sig')
    t12 = md_tables[11]
    for r_idx, (_, r) in enumerate(df_ind.iterrows()):
        row = t12[r_idx+1]
        match_val(row[0], r_idx + 1) # 순위 번호 대조
        assert row[1] == r['업종명'], f"업종명 불일치: {row[1]} != {r['업종명']}"
        record_skip("업종 명칭")
        assert r['업종코드'] in row[2], f"업종코드 불일치: {r['업종코드']} not in {row[2]}"
        record_skip("업종 코드 식별자")
        match_val(row[3], r['총매출_원'])
        match_val(row[4], r['매출보유_상권수'])
        # 주의 라벨 정확 대조
        expected_caution = f"`{r['상권수_주의_이름표']}`" if "주의" in r['상권수_주의_이름표'] else "정상"
        assert row[5] == expected_caution, f"주의라벨 불일치: {row[5]} != {expected_caution}"
        record_skip("상권수 주의 분류라벨")
        assert row[6] == r['1위상권명'], f"1위상권명 불일치: {row[6]} != {r['1위상권명']}"
        record_skip("1위 상권 명칭")
        match_val(row[7], r['1위상권코드']) # 1위 상권코드 숫자 대조
        match_val(row[8], r['1위상권매출_원'])
        match_val(row[9], r['1위상권_집중도_pct'])
        # 특화집중 여부 태그 대조
        expected_focus = "**특화집중**" if r["특화집중_상권_여부"] else "일반"
        assert row[10] == expected_focus, f"특화집중태그 불일치: {row[10]} != {expected_focus}"
        record_skip("특화집중 상태태그")

    # Table 13: 행정동 소비 이상치 8곳 (11행)
    df_sp_out = pd.read_csv(STAGE1_DATA_DIR / 'spending_outlier_dong_summary.csv', encoding='utf-8-sig')
    with open(STAGE1_DATA_DIR / 'spending_outlier_dong_summary.json', encoding='utf-8') as f:
        sp_json = json.load(f)
    t13 = md_tables[12]
    for r_idx, (_, r) in enumerate(df_sp_out.iterrows()):
        row = t13[r_idx+1]
        match_val(row[0], r['행정동_코드']) # 행정동 코드 숫자 대조
        assert r['행정동_명'] in row[1], f"행정동명 불일치: {r['행정동_명']} not in {row[1]}"
        record_skip("행정동 명칭")
        match_val(row[2], r['지출_총금액_원'])
        match_val(row[3], r['지출_조원']) # 소비 조원 숫자 대조
        match_val(row[4], r['서울_비중_pct'])
        assert r['소비_최대항목'] in row[5], f"소비 최대항목명 불일치: {r['소비_최대항목']} not in {row[5]}"
        match_val(row[6], r['소비_최대항목_비중_pct']) # 항목 비중 숫자 대조
    # 요약 3행
    match_val(t13[9][2], sp_json['이상치_8개동_지출합계_원'])
    match_val(t13[9][3], sp_json['이상치_8개동_지출합계_조원'])
    match_val(t13[9][4], sp_json['이상치_8개동_지출비중_pct'])
    match_val(t13[10][2], sp_json['정상_417개동_지출합계_원'])
    match_val(t13[10][3], sp_json['정상_417개동_지출합계_조원'])
    match_val(t13[10][4], sp_json['정상_417개동_지출비중_pct'])
    match_val(t13[11][2], sp_json['서울_총지출_원'])
    match_val(t13[11][3], sp_json['서울_총지출_조원'])
    match_val(t13[11][4], 100.0)

    # Table 14: 상권 특성 데이터 준비도 (12개 행)
    df_read = pd.read_csv(STAGE1_DATA_DIR / 'trade_area_readiness_table.csv', encoding='utf-8-sig')
    t14 = md_tables[13]
    for r_idx, (_, r) in enumerate(df_read.iterrows()):
        row = t14[r_idx+1]
        assert r['상권_특성_항목'] in row[0], f"특성항목 불일치: {r['상권_특성_항목']} not in {row[0]}"
        record_skip("상권 특성 항목명")
        assert r['계산가능_여부'] in row[1], f"계산 가능여부 불일치: {r['계산가능_여부']} not in {row[1]}"
        assert r['대응_원천파일'] in row[2], f"원천파일명 불일치: {r['대응_원천파일']} not in {row[2]}"
        record_skip("대응 원천파일명")
        match_val(row[3], r['파일_행수'])
        if str(r['빠진_상권수']).isdigit():
            match_val(row[4], r['빠진_상권수'])
        else:
            assert row[4].strip() == r['빠진_상권수'], f"빠진 상권수 불일치: {row[4]} != {r['빠진_상권수']}"
        if str(r['빠진_상권분기_칸수']).isdigit():
            match_val(row[5], r['빠진_상권분기_칸수'])
        else:
            assert row[5].strip() == r['빠진_상권분기_칸수'], f"빠진 분기칸수 불일치: {row[5]} != {r['빠진_상권분기_칸수']}"
        # 0값 건수 문자열 대조 및 내부 수치 카운트
        assert r['주요컬럼_0값_건수'] in row[6], f"0값건수 불일치: {r['주요컬럼_0값_건수']} not in {row[6]}"
        for num in re.findall(r'[\d,]+', row[6]):
            stats["compared_cells"] += 1
        record_skip("주요컬럼 0값 집계내역")
        match_val(row[7], r['결측치_수'])
        record_skip("활용가능 컬럼목록")
        record_skip("데이터 한계점 및 주의사항")

    print(f" -> 통과: 마크다운 14개 표에서 {stats['compared_cells']}개 수치/코드 칸 대조 완료")
    print(f"    [비숫자 텍스트 칸 (총 {stats['skipped_text_cells']}개) 실제 내용별 내역]:")
    for cat, count in sorted(stats['skip_reasons'].items(), key=lambda x: -x[1])[:6]:
        print(f"      - {cat}: {count}칸")

# ------------------------------------------------------------------------------
# 검사 3: 대시보드(HTML) 11개 표 전체 대조 및 비숫자 칸 사유 집계
# ------------------------------------------------------------------------------
def verify_html_tables(html_tables):
    print("[검사 3] 대시보드(HTML) 11개 표 숫자 칸 및 텍스트 칸 상세 대조")
    assert len(html_tables) >= 11, f"대시보드 내 파싱된 표 개수 부족: {len(html_tables)} < 11"

    stats = {
        "compared_cells": 0,
        "skipped_text_cells": 0,
        "skip_reasons": {}
    }

    def record_skip(category_name):
        stats["skipped_text_cells"] += 1
        stats["skip_reasons"][category_name] = stats["skip_reasons"].get(category_name, 0) + 1

    def match_val(actual_str, expected_num, tolerance=0.005):
        stats["compared_cells"] += 1
        a_clean = clean_num(actual_str)
        try:
            a_val = float(a_clean)
            e_val = float(expected_num)
            if abs(a_val - e_val) > tolerance:
                raise AssertionError(f"HTML 수치 불일치: 실제표='{actual_str}' ({a_val}) != 결과값={e_val}")
        except ValueError:
            raise AssertionError(f"HTML 숫자 변환 실패: '{actual_str}'")

    # Table 0: 파일 프로파일 (10행)
    df_prof = pd.read_csv(STAGE1_DATA_DIR / 'file_profiles.csv', encoding='utf-8-sig')
    h0 = html_tables[0]
    for i, (_, r) in enumerate(df_prof.iterrows()):
        row = h0[i+1]
        assert r['파일명'] in row[0], f"HTML 파일명 불일치: {r['파일명']} not in {row[0]}"
        record_skip("원천 파일명")
        match_val(row[1], r['실제_행수'])
        record_skip("일치여부 배지")
        record_skip("기준 키 컬럼")
        record_skip("수집 단위")
        match_val(row[5], r['결측치_총수'])

    # Table 1: 구별 최고 특화 업종 (25개 구)
    df_top_lq = pd.read_csv(STAGE1_DATA_DIR / 'lq_gu_top_specialization.csv', encoding='utf-8-sig')
    h1 = html_tables[1]
    for r_idx, (_, r) in enumerate(df_top_lq.iterrows()):
        row = h1[r_idx+1]
        assert row[0] == r['자치구명'], f"HTML 자치구명 불일치: {row[0]} != {r['자치구명']}"
        record_skip("자치구 명칭")
        assert r['대분류명'] in row[1], f"HTML 특화업종명 불일치: {r['대분류명']} not in {row[1]}"
        record_skip("최고 특화 대분류명")
        match_val(row[2], r['해당구_업종_점포수'])
        match_val(row[3], r['구내_비중_pct'])
        match_val(row[4], r['입지계수_LQ'])
        expected_lq_label = get_lq_label(r['입지계수_LQ'])
        assert expected_lq_label in row[5], f"HTML LQ 판정문구 불일치: {expected_lq_label} not in {row[5]}"

    # Table 2: 권역 x 대분류 (6행)
    df_zone = pd.read_csv(STAGE1_DATA_DIR / 'cross_zone_category.csv', index_col=0, encoding='utf-8-sig')
    h2 = html_tables[2]
    for r_idx, (z_name, z_row) in enumerate(df_zone.iterrows()):
        row = h2[r_idx+1]
        assert row[0] == z_name, f"HTML 권역명 불일치: {row[0]} != {z_name}"
        record_skip("권역 명칭")
        for c_idx, col_name in enumerate(df_zone.columns):
            match_val(row[c_idx+1], z_row[col_name])

    # Table 3: 층 x 대분류 (8행)
    df_floor = pd.read_csv(STAGE1_DATA_DIR / 'cross_floor_category.csv', index_col=0, encoding='utf-8-sig')
    h3 = html_tables[3]
    for r_idx, (f_name, f_row) in enumerate(df_floor.iterrows()):
        row = h3[r_idx+1]
        assert row[0] == f_name, f"HTML 층명 불일치: {row[0]} != {f_name}"
        record_skip("층위 분류명")
        for c_idx, col_name in enumerate(df_floor.columns):
            match_val(row[c_idx+1], f_row[col_name])

    # Table 4: 자치구 x 대분류 (26행)
    df_gu = pd.read_csv(STAGE1_DATA_DIR / 'cross_gu_category.csv', index_col=0, encoding='utf-8-sig')
    h4 = html_tables[4]
    for r_idx, (g_name, g_row) in enumerate(df_gu.iterrows()):
        row = h4[r_idx+1]
        assert row[0] == g_name, f"HTML 자치구명 불일치: {row[0]} != {g_name}"
        record_skip("자치구 명칭")
        for c_idx, col_name in enumerate(df_gu.columns):
            match_val(row[c_idx+1], g_row[col_name])

    # Table 5: 25개 자치구 전체 LQ 매트릭스 (26행)
    df_lq_all = pd.read_csv(STAGE1_DATA_DIR / 'lq_gu_category.csv', index_col=0, encoding='utf-8-sig')
    h5 = html_tables[5]
    for r_idx, (g_name, g_row) in enumerate(df_lq_all.iterrows()):
        row = h5[r_idx+1]
        assert row[0] == g_name, f"HTML 자치구명 불일치: {row[0]} != {g_name}"
        record_skip("자치구 명칭")
        for c_idx, col_name in enumerate(df_lq_all.columns):
            match_val(row[c_idx+1], g_row[col_name])

    # Table 6 & 7: 회귀 잔차 상하위 Top 5
    with open(STAGE1_DATA_DIR / 'sales_store_analysis.json', encoding='utf-8') as f:
        sales = json.load(f)
    h6 = html_tables[6]
    for r_idx, item in enumerate(sales['회귀선_상단_매출과대표_Top5']):
        row = h6[r_idx+1]
        assert item['상권명'] in row[0], f"HTML 상권명 불일치: {item['상권명']} not in {row[0]}"
        record_skip("상권 명칭")
        match_val(row[1], item['점포수_62업종'])
        match_val(row[2], round(item['실제매출_원'] / 1e8, 1))
        assert item['매출1위_업종명'] in row[3], f"매출1위 불일치: {item['매출1위_업종명']} not in {row[3]}"
        m_s_pct = re.search(r'([\d.]+)%', row[3])
        assert m_s_pct, f"HTML 매출1위 비중 누락: {row[3]}"
        match_val(m_s_pct.group(1), item['매출1위_비중_pct'])
        record_skip("매출1위 업종")
        assert item['점포1위_업종명'] in row[4], f"점포1위 불일치: {item['점포1위_업종명']} not in {row[4]}"
        m_st_pct = re.search(r'([\d.]+)%', row[4])
        assert m_st_pct, f"HTML 점포1위 비중 누락: {row[4]}"
        match_val(m_st_pct.group(1), item['점포1위_비중_pct'])
        record_skip("점포1위 업종")
        assert "[가설]" in row[5], f"HTML 가설표기 누락: {row[5]}"
        record_skip("가설 원인설명")

    h7 = html_tables[7]
    for r_idx, item in enumerate(sales['회귀선_하단_매출과소표_Top5']):
        row = h7[r_idx+1]
        assert item['상권명'] in row[0], f"HTML 상권명 불일치: {item['상권명']} not in {row[0]}"
        record_skip("상권 명칭")
        match_val(row[1], item['점포수_62업종'])
        match_val(row[2], round(item['실제매출_원'] / 1e8, 1))
        assert item['매출1위_업종명'] in row[3], f"매출1위 불일치: {item['매출1위_업종명']} not in {row[3]}"
        m_s_pct = re.search(r'([\d.]+)%', row[3])
        assert m_s_pct, f"HTML 매출1위 비중 누락: {row[3]}"
        match_val(m_s_pct.group(1), item['매출1위_비중_pct'])
        record_skip("매출1위 업종")
        assert item['점포1위_업종명'] in row[4], f"점포1위 불일치: {item['점포1위_업종명']} not in {row[4]}"
        m_st_pct = re.search(r'([\d.]+)%', row[4])
        assert m_st_pct, f"HTML 점포1위 비중 누락: {row[4]}"
        match_val(m_st_pct.group(1), item['점포1위_비중_pct'])
        record_skip("점포1위 업종")
        assert "[가설]" in row[5], f"HTML 가설표기 누락: {row[5]}"
        record_skip("가설 원인설명")

    # Table 8: 행정동 소비 이상치 8곳
    df_sp_out = pd.read_csv(STAGE1_DATA_DIR / 'spending_outlier_dong_summary.csv', encoding='utf-8-sig')
    h8 = html_tables[8]
    for r_idx, (_, r) in enumerate(df_sp_out.iterrows()):
        row = h8[r_idx+1]
        match_val(row[0], r['행정동_코드']) # 행정동 코드 숫자 대조
        assert r['행정동_명'] in row[1], f"HTML 행정동명 불일치: {r['행정동_명']} not in {row[1]}"
        record_skip("행정동 명칭")
        match_val(row[2], r['지출_총금액_원'])
        match_val(row[3], r['지출_조원']) # 소비 조원 숫자 대조
        match_val(row[4], r['서울_비중_pct'])
        assert r['소비_최대항목'] in row[5], f"HTML 소비 최대항목명 불일치: {r['소비_최대항목']} not in {row[5]}"
        match_val(row[6], r['소비_최대항목_비중_pct']) # 항목 비중 숫자 대조

    # Table 9: 62개 업종별 매출 순위 및 집중도 전체
    df_ind = pd.read_csv(STAGE1_DATA_DIR / 'industry_sales_concentration_2025Q4.csv', encoding='utf-8-sig')
    h9 = html_tables[9]
    for r_idx, (_, r) in enumerate(df_ind.iterrows()):
        row = h9[r_idx+1]
        match_val(row[0], r_idx + 1) # 순위 숫자 대조
        assert r['업종명'] in row[1], f"HTML 업종명 불일치: {r['업종명']} not in {row[1]}"
        record_skip("업종 명칭")
        assert r['업종코드'] in row[2], f"HTML 업종코드 불일치: {r['업종코드']} not in {row[2]}"
        record_skip("업종 코드")
        match_val(row[3], r['총매출_원'])
        match_val(row[4], r['매출보유_상권수'])
        assert r['상권수_주의_이름표'] in row[5], f"HTML 주의라벨 불일치: {r['상권수_주의_이름표']} not in {row[5]}"
        record_skip("주의 분류라벨")
        assert r['1위상권명'] in row[6], f"HTML 1위상권명 불일치: {r['1위상권명']} not in {row[6]}"
        record_skip("1위 상권 명칭")
        match_val(row[7], r['1위상권매출_원'])
        match_val(row[8], r['1위상권_집중도_pct'])
        expected_focus = "특화집중" if r["특화집중_상권_여부"] else "일반"
        assert expected_focus in row[9], f"HTML 집중여부 불일치: {expected_focus} not in {row[9]}"
        record_skip("특화집중 상태배지")

    # Table 10: 상권 특성 데이터 준비도 (12행)
    df_read = pd.read_csv(STAGE1_DATA_DIR / 'trade_area_readiness_table.csv', encoding='utf-8-sig')
    h10 = html_tables[10]
    for i, (_, r) in enumerate(df_read.iterrows()):
        row = h10[i+1]
        assert r['상권_특성_항목'] in row[0], f"HTML 특성항목 불일치: {r['상권_특성_항목']} not in {row[0]}"
        record_skip("특성 항목명")
        assert r['계산가능_여부'] in row[1], f"HTML 계산 가능여부 불일치: {r['계산가능_여부']} not in {row[1]}"
        assert r['대응_원천파일'] in row[2], f"HTML 원천파일 불일치: {r['대응_원천파일']} not in {row[2]}"
        record_skip("원천 파일명")
        match_val(row[3], r['파일_행수'])
        if str(r['빠진_상권수']).isdigit():
            match_val(row[4], r['빠진_상권수'])
        else:
            assert row[4].strip() == r['빠진_상권수'], f"HTML 빠진 상권수 불일치: {row[4]} != {r['빠진_상권수']}"
        if str(r['빠진_상권분기_칸수']).isdigit():
            match_val(row[5], r['빠진_상권분기_칸수'])
        else:
            assert row[5].strip() == r['빠진_상권분기_칸수'], f"HTML 빠진 분기칸수 불일치: {row[5]} != {r['빠진_상권분기_칸수']}"
        assert r['주요컬럼_0값_건수'] in row[6], f"HTML 0값건수 불일치: {r['주요컬럼_0값_건수']} not in {row[6]}"
        for num in re.findall(r'[\d,]+', row[6]):
            stats["compared_cells"] += 1
        record_skip("주요컬럼 0값 집계내역")
        match_val(row[7], r['결측치_수'])
        record_skip("한계점 설명문구")

    print(f" -> 통과: 대시보드 11개 표에서 {stats['compared_cells']}개 수치/코드 칸 대조 완료")
    print(f"    [비숫자 텍스트 칸 (총 {stats['skipped_text_cells']}개) 실제 내용별 내역]:")
    for cat, count in sorted(stats['skip_reasons'].items(), key=lambda x: -x[1])[:5]:
        print(f"      - {cat}: {count}칸")

# ------------------------------------------------------------------------------
# 검사 4: 보고서 및 대시보드 본문 문장 속 숫자 추출 및 결과 파일 값 대조
# ------------------------------------------------------------------------------
def get_allowed_numbers():
    """결과 데이터 파일로부터 허용되는 모든 분석 수치 추출 집합 생성"""
    allowed_numbers = set()

    def register_val(v):
        if v is None:
            return
        if isinstance(v, (int, float)):
            allowed_numbers.add(str(v))
            if isinstance(v, int):
                allowed_numbers.add(f"{v:,}")
            else:
                allowed_numbers.add(f"{v:.4f}")
                allowed_numbers.add(f"{v:.3f}")
                allowed_numbers.add(f"{v:.2f}")
                allowed_numbers.add(f"{v:.1f}")
                allowed_numbers.add(str(round(v, 4)))
                allowed_numbers.add(str(round(v, 3)))
                allowed_numbers.add(str(round(v, 2)))
                allowed_numbers.add(str(round(v, 1)))
                allowed_numbers.add(f"{v/1e12:.2f}") # 조원
                allowed_numbers.add(f"{v/1e8:.1f}")  # 억원
            if v < 0:
                abs_v = abs(v)
                allowed_numbers.add(str(abs_v))
                allowed_numbers.add(f"{abs_v:,}")
                allowed_numbers.add(f"{abs_v:.2f}")
                allowed_numbers.add(f"{abs_v:,.2f}")
        elif isinstance(v, str):
            allowed_numbers.add(v)
            m = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', v)
            for num in m:
                allowed_numbers.add(num)
                allowed_numbers.add(num.replace(',', ''))
        elif isinstance(v, dict):
            for sub_k, sub_v in v.items():
                register_val(sub_k)
                register_val(sub_v)
        elif isinstance(v, list):
            for sub_v in v:
                register_val(sub_v)

    # 6개 JSON 로드
    for fname in ["sbiz_quality.json", "descriptive_stats.json", "cross_summary.json",
                  "sales_store_analysis.json", "spending_outlier_dong_summary.json", "trade_area_readiness.json"]:
        with open(STAGE1_DATA_DIR / fname, encoding="utf-8") as f:
            d = json.load(f)
            register_val(d)

    # CSV 파일들의 컬럼 수치도 등록
    for csv_name in ["file_profiles.csv", "industry_sales_concentration_2025Q4.csv", "lq_gu_top_specialization.csv"]:
        df = pd.read_csv(STAGE1_DATA_DIR / csv_name, encoding="utf-8-sig")
        for col in df.columns:
            for val in df[col].dropna():
                register_val(val)

    return allowed_numbers

REVISION_HISTORY_HEADING = "## 8. 수정 이력"
SUMMARY_HEADING = "## 7. 종합 요약"

def test_4_prose_numbers(md_text, html_text):
    print("[검사 4] 보고서 및 대시보드 본문 문장 속 숫자 추출 및 결과 파일 값 대조")
    allowed_numbers = get_allowed_numbers()

    structural_patterns = [
        r'geo/HangJeongDong[^\s`]+',     # geojson 파일 경로
        r'HangJeongDong[^\s`]+',         # geojson 파일명
        r'#+ \d+(?:\.\d+)*\.?',          # ## 1., ### 2.1 등
        r'^\d+\.\s',                    # 1. 2. 3. 리스트 번호
        r'2025-\d{2}-\d{2}',             # 날짜
        r'2025[1-4]',                    # 분기코드
        r'2025Q[1-4]',                   # 분기표기
        r'2025년',                       # 연도
        r'2025',                         # 단순 연도
        r'OA-\d+',                       # 공공데이터 파일명 식별자
        r'01_',                          # 산출물 파일 접두사
        r'Q[1-4]',                       # Q1~Q4
    ]

    # (1) 마크다운 보고서 문장 검사 (8장 수정 이력은 과거 오류 값을 기록하므로 대조에서 제외)
    history_at = md_text.find(REVISION_HISTORY_HEADING)
    summary_at = md_text.find(SUMMARY_HEADING)
    assert history_at > summary_at >= 0, "수정 이력 장은 7장 뒤에 있어야 합니다."
    md_prose_lines = []
    for line in md_text[:history_at].splitlines():
        line_s = line.strip()
        if not line_s or line_s.startswith('|') or line_s.startswith('---'):
            continue
        md_prose_lines.append(line_s)

    unmatched_md = []
    for line in md_prose_lines:
        temp_line = line
        for pat in structural_patterns:
            temp_line = re.sub(pat, ' ', temp_line)

        nums = re.findall(r'\b\d+(?:,\d+)*(?:\.\d+)?%?', temp_line)
        for n in nums:
            clean_n = n.replace('%', '').strip()
            raw_n = clean_n.replace(',', '')
            if clean_n in allowed_numbers or raw_n in allowed_numbers:
                continue

            try:
                val_f = float(raw_n)
                matched = False
                for cand in allowed_numbers:
                    try:
                        if abs(float(cand) - val_f) < 0.005:
                            matched = True
                            break
                    except:
                        pass
                if matched:
                    continue
            except:
                pass

            unmatched_md.append((n, line))

    if unmatched_md:
        print(f"\n[오류] 보고서 문장 속 미대조 숫자 발견 ({len(unmatched_md)}건):")
        for num, line in unmatched_md:
            print(f"  - 미대조 숫자: '{num}' | 문장: {line[:90]}")
        raise AssertionError(f"보고서 문장 속 숫자 {len(unmatched_md)}건이 결과 파일 값과 대조되지 않았습니다.")

    # (2) 대시보드 본문 문장 검사
    clean_html = re.sub(r'<(style|script|table)[\s\S]*?</\1>', ' ', html_text, flags=re.I)
    html_prose_raw = re.sub(r'<[^>]+>', ' ', clean_html)
    html_lines = [l.strip() for l in html_prose_raw.splitlines() if l.strip() and len(re.findall(r'[가-힣]', l)) >= 2]

    unmatched_html = []
    for line in html_lines:
        temp_line = line
        for pat in structural_patterns:
            temp_line = re.sub(pat, ' ', temp_line)

        nums = re.findall(r'\b\d+(?:,\d+)*(?:\.\d+)?%?', temp_line)
        for n in nums:
            clean_n = n.replace('%', '').strip()
            raw_n = clean_n.replace(',', '')
            if clean_n in allowed_numbers or raw_n in allowed_numbers:
                continue

            try:
                val_f = float(raw_n)
                matched = False
                for cand in allowed_numbers:
                    try:
                        if abs(float(cand) - val_f) < 0.005:
                            matched = True
                            break
                    except:
                        pass
                if matched:
                    continue
            except:
                pass

            unmatched_html.append((n, line))

    if unmatched_html:
        print(f"\n[오류] 대시보드 문장 속 미대조 숫자 발견 ({len(unmatched_html)}건):")
        for num, line in unmatched_html:
            print(f"  - 미대조 숫자: '{num}' | 문장: {line[:90]}")
        raise AssertionError(f"대시보드 문장 속 숫자 {len(unmatched_html)}건이 결과 파일 값과 대조되지 않았습니다.")

    print(" -> 통과: 보고서 및 대시보드 본문 문장 속 추출 수치가 결과 파일 값과 일치함을 확인")

# ------------------------------------------------------------------------------
# 검사 5: [가설] 표시 및 주의 라벨 부착 검사 (표 안 + 표 밖 지정 위치)
# ------------------------------------------------------------------------------
def test_5_hypothesis_and_caution_labels(md_text, html_text):
    print("[검사 5] 이상치 원인 문장 [가설] 태그 및 주의 라벨 부착 검사")

    # (1) 잔차 표 [가설] 표시 검사
    with open(STAGE1_DATA_DIR / "sales_store_analysis.json", encoding="utf-8") as f:
        sales = json.load(f)

    for item in sales['회귀선_상단_매출과대표_Top5'] + sales['회귀선_하단_매출과소표_Top5']:
        assert "[가설]" in item['가설_원인'], f"회귀 상권 {item['상권명']} 원인 설명에 [가설] 누락: {item['가설_원인']}"

    # (2) 표 밖 지정 3개 위치의 [가설] 표기 검사
    pos1 = "[가설] 동일 매장 내 배달 전문 별도 사업자 등록(숍인숍)"
    assert pos1 in md_text, f"2.3절 복합속성 중복 문장 [가설] 누락: {pos1}"
    pos2 = "[가설] 경계 외 점포는 서울 인접 시·군 행정구역 경계선 오차 등"
    assert pos2 in md_text, f"2.3절 서울시 경계 외 점포 설명 [가설] 누락: {pos2}"
    pos3 = "[가설] 아파트 주거 중심 배후지로 상업 점포가 적은"
    assert pos3 in md_text, f"3장 기술통계 행정동 최소지역 설명 [가설] 누락: {pos3}"

    # (3) 주의 라벨 검사
    df_ind = pd.read_csv(STAGE1_DATA_DIR / 'industry_sales_concentration_2025Q4.csv', encoding='utf-8-sig')
    under_50 = df_ind[df_ind['매출보유_상권수'] < 50]
    under_100 = df_ind[(df_ind['매출보유_상권수'] >= 50) & (df_ind['매출보유_상권수'] < 100)]

    for _, r in under_50.iterrows():
        assert r['상권수_주의_이름표'] == "주의(50개미만)", f"50개 미만 업종 {r['업종명']}에 '주의(50개미만)' 누락: {r['상권수_주의_이름표']}"
    for _, r in under_100.iterrows():
        assert r['상권수_주의_이름표'] == "주의(100개미만)", f"100개 미만 업종 {r['업종명']}에 '주의(100개미만)' 누락: {r['상권수_주의_이름표']}"

    # (4) LQ 판정 기준 문구 검사 (보고서 및 대시보드)
    with open(STAGE1_DATA_DIR / "cross_summary.json", encoding="utf-8") as f:
        cross = json.load(f)
    lq_crit = cross["LQ_판정_기준_문구"]
    assert lq_crit in md_text, f"보고서 내 LQ 판정 기준 문구 누락: {lq_crit}"
    assert lq_crit in html_text, f"대시보드 내 LQ 판정 기준 문구 누락: {lq_crit}"

    # (5) [주의] 문구 검사 (상위 1% 제외 해석 주의 및 상권수 주의)
    assert "[주의]" in md_text, "보고서 내 [주의] 태그 누락"
    assert "상위 1% 이상치 제외 민감도 분석은 매출액을 기준으로" in md_text and "해석에 주의가 필요합니다" in md_text, "보고서 내 상위 1% 주의문구 누락"
    assert "상위 1% 제외 민감도는 매출액 기준으로 상위 상권을 제외한 결과이므로 추천 모델 적용 시 해석에 주의가 필요합니다" in html_text, "대시보드 내 상위 1% 주의문구 누락"
    assert "주의(50개미만)" in md_text and "주의(100개미만)" in md_text, "보고서 내 주의 라벨 문구 누락"
    assert "주의(50개미만)" in html_text and "주의(100개미만)" in html_text, "대시보드 내 주의 라벨 문구 누락"

    print(f" -> 통과: 잔차 이상치 10곳 및 표 밖 3개 지정 위치 [가설] 완비, 표본부족 주의라벨({len(under_50)}개 50미만, {len(under_100)}개 100미만), [주의] 문구 및 LQ 판정 기준 문구 확인")

# ------------------------------------------------------------------------------
# 검사 6: 주관적/단정적 금지 표현 및 금지 단어 검사
# ------------------------------------------------------------------------------
def test_6_prohibited_words(md_text, html_text):
    print("[검사 6] 주관적/단정적 금지 표현 및 금지어 미사용 확인")
    prohibited = ["완벽", "무결", "검증 완료", "최종", "입증", "압도적", "반드시 성공", "실측", "전국 최대"]
    for word in prohibited:
        assert word not in md_text, f"보고서에 금지어 '{word}'가 사용되었습니다."
        assert word not in html_text, f"대시보드에 금지어 '{word}'가 사용되었습니다."

    assert "전수 스냅샷" not in md_text and "전수 스냅샷" not in html_text, "금지 표현 '전수 스냅샷'이 발견되었습니다."
    assert "사업자 등록 점포" not in md_text, "보고서 머리말에 금지 표현 '사업자 등록 점포'가 발견되었습니다."
    print(" -> 통과: 9개 금지어 및 금지 표현 미사용 확인")

# ------------------------------------------------------------------------------
# 검사 7: 변조 시험 15종 (Mutation Testing)
# ------------------------------------------------------------------------------
def test_7_mutation_suite(md_text, html_text):
    print("[검사 7] 변조 시험 15종 (고의 변조 시 검증 차단 기능 검증)")

    # 1. 표 셀 숫자 변조: Table 1 소상공인 행수 (534,978 -> 999,999)
    print("  [변조 1] Table 1 표 셀 숫자 변조 (534,978 -> 999,999)")
    mut_1 = md_text.replace("| `소상공인_상가정보_서울.csv` | 534,978 |", "| `소상공인_상가정보_서울.csv` | 999,999 |", 1)
    assert mut_1 != md_text, "변조 1 치환 실패"
    try:
        verify_markdown_tables(parse_markdown_tables(mut_1))
        raise Exception("변조 1 실패: 검증기가 표 셀 숫자 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 2. 마크다운 본문 문장 속 숫자 변조: 62개 업종 점포수 (453,076 -> 888,888)
    print("  [변조 2] 마크다운 본문 문장 속 숫자 변조 (453,076 -> 888,888)")
    mut_2 = md_text.replace("453,076개", "888,888개", 1)
    assert mut_2 != md_text, "변조 2 치환 실패"
    try:
        test_4_prose_numbers(mut_2, html_text)
        raise Exception("변조 2 실패: 검증기가 문장 속 숫자 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 3. 대시보드 본문 문장 속 숫자 변조: 강남구 점포수 (64,123 -> 99,999)
    print("  [변조 3] 대시보드 본문 문장 속 숫자 변조 (64,123 -> 99,999)")
    mut_3 = html_text.replace("64,123개", "99,999개", 1)
    assert mut_3 != html_text, "변조 3 치환 실패"
    try:
        test_4_prose_numbers(md_text, mut_3)
        raise Exception("변조 3 실패: 검증기가 대시보드 문장 속 숫자 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 4. 표 비율(%) 수치 변조: Table 12 노량진역 1위 상권 집중도 (82.03% -> 12.34%)
    print("  [변조 4] Table 12 표 비율(%) 변조 (82.03% -> 12.34%)")
    mut_4 = md_text.replace("| 82.03% |", "| 12.34% |", 1)
    assert mut_4 != md_text, "변조 4 치환 실패"
    try:
        verify_markdown_tables(parse_markdown_tables(mut_4))
        raise Exception("변조 4 실패: 검증기가 표 비율 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 5. 주의 라벨 삭제 변조: `주의(50개미만)` -> `정상`
    print("  [변조 5] Table 12 주의 라벨 삭제 변조 (`주의(50개미만)` -> `정상`)")
    mut_5 = md_text.replace("| `주의(50개미만)` |", "| `정상` |", 1)
    assert mut_5 != md_text, "변조 5 치환 실패"
    try:
        verify_markdown_tables(parse_markdown_tables(mut_5))
        raise Exception("변조 5 실패: 검증기가 주의 라벨 삭제를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 6. 특화집중 태그 변조: `**특화집중**` -> `일반`
    print("  [변조 6] Table 12 특화집중 태그 변조 (`**특화집중**` -> `일반`)")
    mut_6 = md_text.replace("| **특화집중** |", "| 일반 |", 1)
    assert mut_6 != md_text, "변조 6 치환 실패"
    try:
        verify_markdown_tables(parse_markdown_tables(mut_6))
        raise Exception("변조 6 실패: 검증기가 특화집중 태그 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 7. Table 10 잔차 설명에서 [가설] 태그 삭제 변조
    print("  [변조 7] Table 10 잔차 설명에서 [가설] 태그 삭제 변조")
    mut_7 = md_text.replace("[가설] 수산물 대량 유통 및 도매 결제 집중", "수산물 대량 유통 및 도매 결제 집중", 1)
    assert mut_7 != md_text, "변조 7 치환 실패"
    try:
        verify_markdown_tables(parse_markdown_tables(mut_7))
        raise Exception("변조 7 실패: 검증기가 표 내부 [가설] 태그 삭제를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 8. 표 밖 2.3절 복합속성 중복 문장에서 [가설] 태그 삭제 변조
    print("  [변조 8] 표 밖 2.3절 본문에서 [가설] 태그 삭제 변조")
    mut_8 = md_text.replace("[가설] 동일 매장 내 배달 전문 별도 사업자 등록", "동일 매장 내 배달 전문 별도 사업자 등록", 1)
    assert mut_8 != md_text, "변조 8 치환 실패"
    try:
        test_5_hypothesis_and_caution_labels(mut_8, html_text)
        raise Exception("변조 8 실패: 검증기가 표 밖 [가설] 태그 삭제를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 9. 표의 텍스트(제외 칸) 변조: Table 8 자치구명 '강남구' -> '해외구'
    print("  [변조 9] 표의 텍스트 칸 변조: Table 8 강남구 -> 해외구")
    mut_9 = md_text.replace("| 강남구 | **과학·기술** |", "| 해외구 | **과학·기술** |", 1)
    assert mut_9 != md_text, "변조 9 치환 실패"
    try:
        verify_markdown_tables(parse_markdown_tables(mut_9))
        raise Exception("변조 9 실패: 검증기가 표 텍스트 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 10. 대시보드 구별 최고 특화 표 고특화 -> 특화 변조
    print("  [변조 10] 대시보드 구별 최고 특화 표 변조 (고특화 -> 특화)")
    mut_10 = html_text.replace('<span class="badge badge-danger">서울 대비 고특화</span>', '<span class="badge badge-info">서울 대비 특화</span>', 1)
    assert mut_10 != html_text, "변조 10 치환 실패"
    try:
        verify_html_tables(parse_html_tables(mut_10))
        raise Exception("변조 10 실패: 검증기가 대시보드 고특화 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 11. 준비도 표 '해당 없음' -> '0개' 변조
    print("  [변조 11] 준비도 표 '해당 없음' -> '0개' 변조")
    mut_11 = md_text.replace("| 해당 없음 | 해당 없음 |", "| 0개 | 0개 |", 1)
    assert mut_11 != md_text, "변조 11 치환 실패"
    try:
        verify_markdown_tables(parse_markdown_tables(mut_11))
        raise Exception("변조 11 실패: 검증기가 준비도 표 해당 없음 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 12. 기술통계 최소 지역명 '도봉구' -> '노원구' 변조
    print("  [변조 12] 기술통계 최소 지역명 '도봉구' -> '노원구' 변조")
    mut_12 = md_text.replace("(도봉구, `11320`)", "(노원구, `11320`)", 1)
    assert mut_12 != md_text, "변조 12 치환 실패"
    try:
        verify_markdown_tables(parse_markdown_tables(mut_12))
        raise Exception("변조 12 실패: 검증기가 기술통계 지역명 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 13. 대시보드 잔차표 매출 1위 비중 변조 (91.1% -> 99.9%)
    print("  [변조 13] 대시보드 잔차표 매출 1위 비중 변조 (91.1% -> 99.9%)")
    mut_13 = html_text.replace("수산물판매 (91.1%)", "수산물판매 (99.9%)", 1)
    assert mut_13 != html_text, "변조 13 치환 실패"
    try:
        verify_html_tables(parse_html_tables(mut_13))
        raise Exception("변조 13 실패: 검증기가 대시보드 잔차표 비중 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 14. LQ 판정 기준 문구 변조 (1.5 -> 2.0)
    print("  [변조 14] LQ 판정 기준 문구 변조 (1.5 -> 2.0)")
    with open(STAGE1_DATA_DIR / "cross_summary.json", encoding="utf-8") as f:
        cross = json.load(f)
    lq_crit_str = cross["LQ_판정_기준_문구"]
    mut_14 = md_text.replace(lq_crit_str, lq_crit_str.replace("1.5", "2.0"), 1)
    assert mut_14 != md_text, "변조 14 치환 실패"
    try:
        test_5_hypothesis_and_caution_labels(mut_14, html_text)
        raise Exception("변조 14 실패: 검증기가 LQ 판정 기준 문구 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    # 15. 수정 이력 장을 앞으로 옮겨 본문 숫자를 대조에서 빼는 변조
    print("  [변조 15] 수정 이력 제목을 7장 앞으로 이동 변조")
    mut_15 = md_text.replace(REVISION_HISTORY_HEADING, "## 8. 이력", 1).replace(SUMMARY_HEADING, f"{REVISION_HISTORY_HEADING}\n{SUMMARY_HEADING}", 1)
    assert mut_15 != md_text, "변조 15 치환 실패"
    try:
        test_4_prose_numbers(mut_15, html_text)
        raise Exception("변조 15 실패: 검증기가 수정 이력 위치 변조를 감지하지 못함")
    except AssertionError as e:
        print(f"   -> 차단 성공: {e}")

    print(" -> 통과: 15건의 고의 변조 시험 모두 검증기가 성공적으로 감지하여 차단 완료")

# ------------------------------------------------------------------------------
# 메인 함수 및 자동 검사 한계 명시
# ------------------------------------------------------------------------------
def main():
    print("================================================================")
    print("   [SpotFit Stage 1] 강화된 자동 검증 실행 (verify_stage1)")
    print("================================================================")

    report_path = REPORT_DIR / "01_기본EDA_보고서_2025Q4.md"
    html_dash_path = REPORT_DIR / "01_기본EDA_대시보드_2025Q4.html"

    assert report_path.exists(), f"보고서 파일이 존재하지 않습니다: {report_path}"
    assert html_dash_path.exists(), f"대시보드 HTML 파일이 존재하지 않습니다: {html_dash_path}"

    md_text = report_path.read_text(encoding="utf-8")
    html_dash_text = html_dash_path.read_text(encoding="utf-8")

    md_tables = parse_markdown_tables(md_text)
    html_tables = parse_html_tables(html_dash_text)

    try:
        test_1_data_integrity()
        verify_markdown_tables(md_tables)
        verify_html_tables(html_tables)
        test_4_prose_numbers(md_text, html_dash_text)
        test_5_hypothesis_and_caution_labels(md_text, html_dash_text)
        test_6_prohibited_words(md_text, html_dash_text)
        test_7_mutation_suite(md_text, html_dash_text)

        print("\n================================================================")
        print("   >>> 검증 통과: 1단계 데이터 프로파일링 및 기본 EDA 일관성 확인 <<<")
        print("================================================================")
        print("\n[자동 검사가 보증하지 못하는 범위 및 한계 안내]")
        print("1. 본문 문장 속 숫자 검사는 추출된 숫자가 결과 파일에 존재하는지만 대조하며, 엉뚱한 위치의 숫자로 값 바꿔치기된 오류는 감지하지 못합니다.")
        print("2. 공공 데이터 원천 수집 자체의 누락이나 추정 방식 내부의 오차는 검증하지 못합니다.")
        print("3. 이상치 원인 설명의 [가설] 태그 부착 여부는 검사하나, 해당 가설의 현실적·경제학적 진실성은 보증하지 못합니다.")
        print("4. 비정형 한글 문장의 문맥적 유려성 및 독자 이해도는 검증하지 못합니다.")
        print("5. 보고서 8장 수정 이력은 과거 오류 값을 기록한 장이라 문장 숫자 대조에서 제외하며, 금지어 검사만 적용합니다.")
        print("6. 본 검증은 산출된 결과 파일과 보고서/대시보드 간의 수치 일치성과 논리적 정합성만을 검사합니다.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[검사 실패 - 정합성 오류]: {e}")
        print("================================================================")
        sys.exit(1)
    except Exception as e:
        print(f"\n[실행 오류 발생]: {e}")
        print("================================================================")
        sys.exit(1)

if __name__ == "__main__":
    main()
