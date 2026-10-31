"""
1단계 데이터 프로파일링 및 기본 EDA 스크립트 (2025Q4 / 2025년 기준) - 개정본
- 62개 업종 기준 점포-매출 결합 및 100개 업종 민감도 분석
- 상권 잔차 분석 시 하드코딩 제거 및 매출/점포 상위 1위 업종 코드 자동 산출
- 상권 이상치 이름표(매출 상위 1% + 특화집중) 실제 생성
- 행정동 소비 이상치 8곳 실제 집계 (소비_이상치)
- 상권 특성 준비도 표 코드 계산 (행수, 빠진 상권수, 누락 분기, 0값, 결측치)
- 업종 집중도 표에 매출보유 상권수 및 주의 이름표 부착
- 소비 데이터 파일 프로파일 포함
"""
import sys
import os
import json
import time
import math
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import skew, kurtosis, pearsonr, spearmanr
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import seaborn as sns
from shapely.geometry import shape
from shapely.ops import unary_union
import shapely

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 한글 폰트 설정 (Windows 맑은 고딕)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
STAGE1_DATA_DIR = PROCESSED_DIR / "eda_stage1"
IMAGES_DIR = PROJECT_DIR / "images" / "eda_stage1"

STAGE1_DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

GU_TO_ZONE = {
    "종로구": "도심권", "중구": "도심권", "용산구": "도심권",
    "성동구": "동북권", "광진구": "동북권", "동대문구": "동북권", "중랑구": "동북권",
    "성북구": "동북권", "강북구": "동북권", "도봉구": "동북권", "노원구": "동북권",
    "은평구": "서북권", "서대문구": "서북권", "마포구": "서북권",
    "양천구": "서남권", "강서구": "서남권", "구로구": "서남권", "금천구": "서남권",
    "영등포구": "서남권", "동작구": "서남권", "관악구": "서남권",
    "서초구": "동남권", "강남구": "동남권", "송파구": "동남권", "강동구": "동남권"
}

# 입지계수(LQ) 특화도 판정 상수 및 함수 (단일 정의 원칙)
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

GU_TO_CODE = {
    "종로구": 11110, "중구": 11140, "용산구": 11170, "성동구": 11200, "광진구": 11215,
    "동대문구": 11230, "중랑구": 11260, "성북구": 11290, "강북구": 11305, "도봉구": 11320,
    "노원구": 11350, "은평구": 11380, "서대문구": 11410, "마포구": 11440, "양천구": 11470,
    "강서구": 11500, "구로구": 11530, "금천구": 11545, "영등포구": 11560, "동작구": 11590,
    "관악구": 11620, "서초구": 11650, "강남구": 11680, "송파구": 11710, "강동구": 11740
}

NEW_TO_OLD = {
    11230515: 11230536,  # 신설동 -> 용신동
    11230533: 11230536,  # 용두동 -> 용신동
    11740525: 11740520,  # 상일1동 -> 상일동
    11740526: 11740520,  # 상일2동 -> 상일동
    11680675: 11680740   # 개포3동 -> 일원2동
}

def profile_files():
    """1. 파일별 프로파일 생성 (소비 데이터 포함 10개 파일 점검)"""
    print(">>> 1. 파일별 프로파일 분석 중...")
    manifest = pd.read_csv(RAW_DIR / "MANIFEST.csv", encoding="utf-8-sig")
    manifest_dict = dict(zip(manifest["파일"], manifest["행수"]))
    
    file_specs = [
        ("소상공인_상가정보_서울.csv", RAW_DIR / "소상공인_상가정보_서울.csv", "상가업소번호", "2025-12-31 시점", "점포 (건)", "서울 소재 상가업소 데이터 수록 점포"),
        ("OA-15560_영역_상권.csv", RAW_DIR / "상권" / "OA-15560_영역_상권.csv", "상권_코드", "시점(고정)", "상권 영역", "서울시 지정 1,650개 상권 영역"),
        ("OA-15568_길단위인구_상권.csv", RAW_DIR / "상권" / "OA-15568_길단위인구_상권.csv", "기준_년분기_코드+상권_코드", "2025Q1~Q4", "인구수 (명)", "상권 단위 분기별 길단위 유동인구"),
        ("OA-15569_직장인구_상권.csv", RAW_DIR / "상권" / "OA-15569_직장인구_상권.csv", "기준_년분기_코드+상권_코드", "2025Q1~Q4", "인구수 (명)", "상권 단위 직장인(근무자) 인구"),
        ("OA-15572_추정매출_상권.csv", RAW_DIR / "상권" / "OA-15572_추정매출_상권.csv", "기준_년분기_코드+상권_코드+서비스_업종_코드", "2025Q1~Q4", "금액 (원) / 건수", "상권 및 62개 업종별 분기 추정매출"),
        ("OA-15576_상권변화지표_상권.csv", RAW_DIR / "상권" / "OA-15576_상권변화지표_상권.csv", "기준_년분기_코드+상권_코드", "2025Q1~Q4", "지표값 / 구분", "상권별 영업기간 및 폐업기간 기반 상권변화지표"),
        ("OA-15577_점포_상권.csv", RAW_DIR / "상권" / "OA-15577_점포_상권.csv", "기준_년분기_코드+상권_코드+서비스_업종_코드", "2025Q1~Q4", "개수", "상권 및 100개 업종별 점포/개업/폐업 수"),
        ("OA-15580_집객시설_상권.csv", RAW_DIR / "상권" / "OA-15580_집객시설_상권.csv", "기준_년분기_코드+상권_코드", "2025Q1~Q4", "개수", "상권 단위 주요 집객시설(관공서, 은행 등) 수"),
        ("OA-15584_상주인구_상권.csv", RAW_DIR / "상권" / "OA-15584_상주인구_상권.csv", "기준_년분기_코드+상권_코드", "2025Q1~Q4", "인구수 (명)", "상권 단위 거주 상주인구 수"),
        ("OA-22166_소비_행정동.csv", RAW_DIR / "OA-22166_소비_행정동.csv", "기준_년분기_코드+행정동_코드", "2025Q1~Q4", "지출금액 (원)", "서울시 425개 행정동 분기별 추정소비 지출액")
    ]
    
    profiles = []
    for fname, fpath, key_def, period, unit, pop_def in file_specs:
        rel_path = f"상권/{fname}" if "상권" in str(fpath) else fname
        manifest_rows = manifest_dict.get(rel_path, None)
        if manifest_rows is None and fname in manifest_dict:
            manifest_rows = manifest_dict[fname]
        
        df = pd.read_csv(fpath, low_memory=False, encoding="utf-8-sig")
        actual_rows = len(df)
        cols_count = len(df.columns)
        null_count = int(df.isna().sum().sum())
        
        # 키 유일성 확인
        keys = key_def.split("+")
        if all(k in df.columns for k in keys):
            is_key_unique = bool(not df.duplicated(subset=keys).any())
            dup_keys_count = int(df.duplicated(subset=keys).sum())
        else:
            is_key_unique = False
            dup_keys_count = 0
            
        val_range = "데이터 없음"
        if fname == "소상공인_상가정보_서울.csv":
            lat_min, lat_max = df["위도"].min(), df["위도"].max()
            lon_min, lon_max = df["경도"].min(), df["경도"].max()
            val_range = f"위도({lat_min:.3f}~{lat_max:.3f}), 경도({lon_min:.3f}~{lon_max:.3f})"
        elif fname == "OA-15560_영역_상권.csv":
            area_min, area_max = df["영역_면적"].min(), df["영역_면적"].max()
            val_range = f"영역_면적({area_min:,} ~ {area_max:,} ㎡)"
        elif fname == "OA-15568_길단위인구_상권.csv":
            f_min, f_max = df["총_유동인구_수"].min(), df["총_유동인구_수"].max()
            val_range = f"총_유동인구_수({f_min:,} ~ {f_max:,} 명)"
        elif fname == "OA-15569_직장인구_상권.csv":
            w_min, w_max = df["총_직장_인구_수"].min(), df["총_직장_인구_수"].max()
            val_range = f"총_직장_인구_수({w_min:,} ~ {w_max:,} 명)"
        elif fname == "OA-15572_추정매출_상권.csv":
            s_min, s_max = df["당월_매출_금액"].min(), df["당월_매출_금액"].max()
            val_range = f"당월_매출_금액({s_min:,} ~ {s_max:,} 원)"
        elif fname == "OA-15576_상권변화지표_상권.csv":
            op_min, op_max = df["서울_운영_영업_개월_평균"].min(), df["서울_운영_영업_개월_평균"].max()
            val_range = f"서울운영영업개월평균({op_min} ~ {op_max} 개월)"
        elif fname == "OA-15577_점포_상권.csv":
            st_min, st_max = df["전체_점포_수"].min(), df["전체_점포_수"].max()
            val_range = f"전체_점포_수({st_min:,} ~ {st_max:,} 개)"
        elif fname == "OA-15580_집객시설_상권.csv":
            fac_min, fac_max = df["집객시설_수"].min(), df["집객시설_수"].max()
            val_range = f"집객시설_수({fac_min:,} ~ {fac_max:,} 개)"
        elif fname == "OA-15584_상주인구_상권.csv":
            p_min, p_max = df["총_상주인구_수"].min(), df["총_상주인구_수"].max()
            val_range = f"총_상주인구_수({p_min:,} ~ {p_max:,} 명)"
        elif fname == "OA-22166_소비_행정동.csv":
            sp_min, sp_max = df["지출_총금액"].min(), df["지출_총금액"].max()
            val_range = f"지출_총금액({sp_min:,} ~ {sp_max:,} 원)"
            
        profiles.append({
            "파일명": fname,
            "실제_행수": actual_rows,
            "매니페스트_행수": int(manifest_rows) if manifest_rows is not None else None,
            "행수_일치여부": bool(actual_rows == manifest_rows),
            "열수": cols_count,
            "기준_키": key_def,
            "키_유일성": is_key_unique,
            "키_중복건수": dup_keys_count,
            "기준_기간": period,
            "단위": unit,
            "결측치_총수": null_count,
            "주요변수_값범위": val_range,
            "모집단_정의": pop_def
        })
        
    df_profiles = pd.DataFrame(profiles)
    df_profiles.to_csv(STAGE1_DATA_DIR / "file_profiles.csv", index=False, encoding="utf-8-sig")
    return df_profiles

def analyze_sbiz_quality():
    """2. 소상공인 데이터 품질 분석"""
    print(">>> 2. 소상공인 데이터 품질 분석 중...")
    sbiz = pd.read_csv(RAW_DIR / "소상공인_상가정보_서울.csv", low_memory=False, encoding="utf-8-sig")
    total_rows = len(sbiz)
    
    # (1) 행정동 코드 대응 전후
    dong_before = int(sbiz["행정동코드"].nunique())
    sbiz["행정동_코드"] = sbiz["행정동코드"].replace(NEW_TO_OLD)
    dong_after = int(sbiz["행정동_코드"].nunique())
    
    master = pd.read_csv(PROCESSED_DIR / "행정동_마스터.csv", encoding="utf-8-sig")
    dong_master_count = int(master["행정동_코드"].nunique())
    all_matched = bool(sbiz["행정동_코드"].isin(master["행정동_코드"]).all())
    
    # (2) 층 정보 분석: 원천 고유값 추출
    floor_series = sbiz["층정보"].fillna("미입력(결측)")
    floor_raw_df = floor_series.value_counts(dropna=False).reset_index()
    floor_raw_df.columns = ["원천_층정보", "건수"]
    floor_raw_df["비율_pct"] = (floor_raw_df["건수"] / total_rows * 100).round(4)
    floor_raw_df.to_csv(STAGE1_DATA_DIR / "raw_floor_values.csv", index=False, encoding="utf-8-sig")
    
    floor_raw_unique_count = int(sbiz["층정보"].dropna().nunique())
    floor_nan_count = int(sbiz["층정보"].isna().sum())
    
    def classify_floor(val):
        if pd.isna(val):
            return "미입력(결측)"
        s = str(val).strip()
        if s.startswith(('B', 'b')) or '지' in s:
            return "지하층"
        if s.isdigit():
            n = int(s)
            if 1 <= n <= 80:
                if n == 1:
                    return "지상 1층"
                elif n == 2:
                    return "지상 2층"
                else:
                    return "지상 3층 이상"
            else:
                return "호수오기/미분류"
        return "기타/미분류"
        
    sbiz["층분류"] = sbiz["층정보"].apply(classify_floor)
    
    floor_order = ["미입력(결측)", "지상 1층", "지상 2층", "지상 3층 이상", "지하층", "호수오기/미분류", "기타/미분류"]
    floor_counts_series = sbiz["층분류"].value_counts()
    floor_counts = {k: int(floor_counts_series.get(k, 0)) for k in floor_order}
    
    # 분모 구분: 입력 점포(결측 제외) vs 전체 점포
    input_stores_cnt = total_rows - floor_nan_count
    floor1_cnt = floor_counts["지상 1층"]
    floor1_share_input = round(floor1_cnt / input_stores_cnt * 100, 2)
    floor1_share_total = round(floor1_cnt / total_rows * 100, 2)
    floor_nan_share_total = round(floor_nan_count / total_rows * 100, 2)
    
    unclassified_mask = sbiz["층분류"].isin(["호수오기/미분류", "기타/미분류"])
    unclassified_count = int(unclassified_mask.sum())
    unclassified_examples = sbiz.loc[unclassified_mask, "층정보"].value_counts().head(10).to_dict()
    unclassified_examples = {str(k): int(v) for k, v in unclassified_examples.items()}
    
    # (3) 중복 분석
    dup_id_count = int(sbiz["상가업소번호"].duplicated().sum())
    comb_cols = ["상호명", "도로명주소", "층정보", "호정보", "상권업종소분류명"]
    dup_comb_count = int(sbiz.duplicated(subset=comb_cols).sum())
    dup_comb_ratio = round((dup_comb_count / total_rows) * 100, 3)
    
    # (4) 좌표 경계 폴리곤 분석 (실제 서울 피처 수 427개)
    with open(RAW_DIR / "geo" / "HangJeongDong_ver20251231.geojson", encoding="utf-8") as f:
        geo = json.load(f)
    seoul_feats = [feat for feat in geo["features"] if str(feat["properties"].get("adm_cd2", "")).startswith("11")]
    seoul_feat_count = len(seoul_feats)
    seoul_geoms = [shape(feat["geometry"]) for feat in seoul_feats]
    seoul_polygon = unary_union(seoul_geoms)
    
    is_inside = shapely.contains_xy(seoul_polygon, sbiz["경도"].values, sbiz["위도"].values)
    inside_count = int(is_inside.sum())
    outside_count = int((~is_inside).sum())
    outside_ratio = round((outside_count / total_rows) * 100, 4)
    
    sbiz_quality = {
        "전체_점포_건수": total_rows,
        "행정동_대응_전_동수": dong_before,
        "행정동_대응_후_동수": dong_after,
        "마스터_동수": dong_master_count,
        "마스터_동_전체일치_여부": all_matched,
        "상가업소번호_중복건수": dup_id_count,
        "복합조합_중복건수": dup_comb_count,
        "복합조합_중복비율_pct": dup_comb_ratio,
        "층정보_원천_고유값수": floor_raw_unique_count,
        "층정보_결측건수": floor_nan_count,
        "층정보_결측비율_전체_pct": floor_nan_share_total,
        "층정보_입력점포_건수": input_stores_cnt,
        "층정보_1층_점포수": floor1_cnt,
        "층정보_1층비율_입력점포기준_pct": floor1_share_input,
        "층정보_1층비율_전체점포기준_pct": floor1_share_total,
        "층분류_집계": floor_counts,
        "층_미분류건수": unclassified_count,
        "층_미분류예시_top10": unclassified_examples,
        "좌표_서울경계_피처수": seoul_feat_count,
        "좌표_서울경계내_건수": inside_count,
        "좌표_서울경계외_건수": outside_count,
        "좌표_경계외_비율_pct": outside_ratio,
        "좌표_서울경계내_비율_pct": round(inside_count / total_rows * 100, 3),
        "핵심원천파일수": 10
    }
    
    with open(STAGE1_DATA_DIR / "sbiz_quality.json", "w", encoding="utf-8") as f:
        json.dump(sbiz_quality, f, ensure_ascii=False, indent=2)
        
    return sbiz, sbiz_quality

def calculate_descriptive_stats(sbiz):
    """3. 기술통계 (자치구 및 행정동 점포 수 분포)"""
    print(">>> 3. 기술통계 산출 중...")
    master = pd.read_csv(PROCESSED_DIR / "행정동_마스터.csv", encoding="utf-8-sig")
    
    gu_counts = sbiz.groupby("시군구명").size()
    gu_min_name = str(gu_counts.idxmin())
    gu_max_name = str(gu_counts.idxmax())
    
    gu_stats = {
        "단위": "자치구",
        "지역수": len(gu_counts),
        "평균": round(float(gu_counts.mean()), 2),
        "중위수": round(float(gu_counts.median()), 2),
        "표준편차": round(float(gu_counts.std()), 2),
        "Q1": round(float(gu_counts.quantile(0.25)), 2),
        "Q3": round(float(gu_counts.quantile(0.75)), 2),
        "IQR": round(float(gu_counts.quantile(0.75) - gu_counts.quantile(0.25)), 2),
        "최소값": int(gu_counts.min()),
        "최소지역": gu_min_name,
        "최소지역_코드": GU_TO_CODE.get(gu_min_name, 11320),
        "최대값": int(gu_counts.max()),
        "최대지역": gu_max_name,
        "최대지역_코드": GU_TO_CODE.get(gu_max_name, 11680),
        "왜도": round(float(skew(gu_counts)), 3),
        "첨도": round(float(kurtosis(gu_counts)), 3)
    }
    
    dong_counts_series = sbiz.groupby("행정동_코드").size().rename("점포수")
    dong_df = master[["행정동_코드", "행정동_명", "자치구_명"]].merge(dong_counts_series, on="행정동_코드", how="left")
    dong_df["점포수"] = dong_df["점포수"].fillna(0)
    
    dong_counts = dong_df["점포수"]
    min_row = dong_df.loc[dong_counts.idxmin()]
    max_row = dong_df.loc[dong_counts.idxmax()]
    
    dong_stats = {
        "단위": "행정동",
        "지역수": len(dong_counts),
        "평균": round(float(dong_counts.mean()), 2),
        "중위수": round(float(dong_counts.median()), 2),
        "표준편차": round(float(dong_counts.std()), 2),
        "Q1": round(float(dong_counts.quantile(0.25)), 2),
        "Q3": round(float(dong_counts.quantile(0.75)), 2),
        "IQR": round(float(dong_counts.quantile(0.75) - dong_counts.quantile(0.25)), 2),
        "최소값": int(dong_counts.min()),
        "최소지역": f"{min_row['자치구_명']} {min_row['행정동_명']}",
        "최소지역_코드": int(min_row["행정동_코드"]),
        "최대값": int(dong_counts.max()),
        "최대지역": f"{max_row['자치구_명']} {max_row['행정동_명']}",
        "최대지역_코드": int(max_row["행정동_코드"]),
        "왜도": round(float(skew(dong_counts)), 3),
        "첨도": round(float(kurtosis(dong_counts)), 3)
    }
    
    stats_data = {
        "자치구_기술통계": gu_stats,
        "행정동_기술통계": dong_stats
    }
    with open(STAGE1_DATA_DIR / "descriptive_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats_data, f, ensure_ascii=False, indent=2)
        
    df_desc_table = pd.DataFrame([
        {"구분": "자치구 단위 (25개 구)", **gu_stats},
        {"구분": "행정동 단위 (425개 동)", **dong_stats}
    ])
    df_desc_table.to_csv(STAGE1_DATA_DIR / "descriptive_stats_table.csv", index=False, encoding="utf-8-sig")
    
    return stats_data

def analyze_cross_tabulations(sbiz):
    """4. 교차분석 및 자치구별 전체 LQ 산출 (점포수, 구내비중 포함)"""
    print(">>> 4. 교차분석 및 입지계수(LQ) 산출 중...")
    total_stores = len(sbiz)
    sbiz["권역"] = sbiz["시군구명"].map(GU_TO_ZONE)
    
    categories = sorted(sbiz["상권업종대분류명"].unique().tolist())
    
    # (1) 자치구 x 대분류
    gu_cat = pd.crosstab(sbiz["시군구명"], sbiz["상권업종대분류명"])
    gu_cat["총계"] = gu_cat.sum(axis=1)
    tot_row_gu = gu_cat.sum(axis=0)
    tot_row_gu.name = "총계"
    gu_cat_with_tot = pd.concat([gu_cat, pd.DataFrame(tot_row_gu).T])
    gu_cat_with_tot.to_csv(STAGE1_DATA_DIR / "cross_gu_category.csv", encoding="utf-8-sig")
    
    # (2) 권역 x 대분류
    zone_cat = pd.crosstab(sbiz["권역"], sbiz["상권업종대분류명"])
    zone_cat["총계"] = zone_cat.sum(axis=1)
    tot_row_zone = zone_cat.sum(axis=0)
    tot_row_zone.name = "총계"
    zone_cat_with_tot = pd.concat([zone_cat, pd.DataFrame(tot_row_zone).T])
    zone_cat_with_tot.to_csv(STAGE1_DATA_DIR / "cross_zone_category.csv", encoding="utf-8-sig")
    
    # (3) 층분류 x 대분류
    floor_order = ["미입력(결측)", "지상 1층", "지상 2층", "지상 3층 이상", "지하층", "호수오기/미분류", "기타/미분류"]
    floor_cat = pd.crosstab(sbiz["층분류"], sbiz["상권업종대분류명"]).reindex(floor_order)
    floor_cat["총계"] = floor_cat.sum(axis=1)
    tot_row_floor = floor_cat.sum(axis=0)
    tot_row_floor.name = "총계"
    floor_cat_with_tot = pd.concat([floor_cat, pd.DataFrame(tot_row_floor).T])
    floor_cat_with_tot.to_csv(STAGE1_DATA_DIR / "cross_floor_category.csv", encoding="utf-8-sig")
    
    # (4) 자치구별 대분류 입지계수(LQ) 계산 및 상세표 생성
    gu_tot = sbiz.groupby("시군구명").size()
    cat_tot = sbiz.groupby("상권업종대분류명").size()
    
    lq_df = pd.DataFrame(index=gu_tot.index, columns=cat_tot.index)
    lq_details = []
    
    for gu in gu_tot.index:
        e_i = gu_tot[gu]
        for cat in cat_tot.index:
            e_ij = gu_cat.loc[gu, cat]
            e_j = cat_tot[cat]
            lq = (e_ij / e_i) / (e_j / total_stores)
            lq_df.loc[gu, cat] = round(lq, 3)
            
            lq_details.append({
                "자치구명": gu,
                "대분류명": cat,
                "해당구_업종_점포수": int(e_ij),
                "구내_전체_점포수": int(e_i),
                "구내_비중_pct": round(e_ij / e_i * 100, 2),
                "서울_업종_점포수": int(e_j),
                "서울_전체_점포수": total_stores,
                "서울_비중_pct": round(e_j / total_stores * 100, 2),
                "입지계수_LQ": round(lq, 3)
            })
            
    lq_df.to_csv(STAGE1_DATA_DIR / "lq_gu_category.csv", encoding="utf-8-sig")
    df_lq_details = pd.DataFrame(lq_details)
    df_lq_details.to_csv(STAGE1_DATA_DIR / "lq_gu_category_full.csv", index=False, encoding="utf-8-sig")
    
    # 25개 자치구 각각의 최고 특화(LQ 1위) 업종 요약표 (고특화 단계 라벨 부여)
    gu_top_lqs = []
    for gu in sorted(gu_tot.index):
        gu_sub = df_lq_details[df_lq_details["자치구명"] == gu].sort_values(by="입지계수_LQ", ascending=False).iloc[0]
        gu_dict = gu_sub.to_dict()
        gu_dict["특화도_판정"] = get_lq_label(gu_dict["입지계수_LQ"])
        gu_top_lqs.append(gu_dict)
    df_gu_top_lq = pd.DataFrame(gu_top_lqs)
    df_gu_top_lq.to_csv(STAGE1_DATA_DIR / "lq_gu_top_specialization.csv", index=False, encoding="utf-8-sig")
    
    # 10대 대분류별 최고 특화 구 (전국이 아닌 서울 대비)
    top_lq_by_cat = {}
    for cat in cat_tot.index:
        cat_sub = df_lq_details[df_lq_details["대분류명"] == cat].sort_values(by="입지계수_LQ", ascending=False).iloc[0]
        top_lq_by_cat[cat] = {
            "자치구": cat_sub["자치구명"],
            "LQ": cat_sub["입지계수_LQ"],
            "점포수": int(cat_sub["해당구_업종_점포수"]),
            "구내비중_pct": cat_sub["구내_비중_pct"]
        }
        
    top3_gu = gu_tot.sort_values(ascending=False).head(3).index.tolist()
    top3_sum = int(sum(gu_tot[gu] for gu in top3_gu))
    top3_share = round(top3_sum / total_stores * 100, 1)
    zone_shares = {k: round(v / total_stores * 100, 2) for k, v in zone_cat["총계"].items()}
    floor_shares = {k: round(v / total_stores * 100, 2) for k, v in floor_cat["총계"].items()}
    
    cross_summary = {
        "전체_점포수": total_stores,
        "대분류_목록": categories,
        "대분류_점포수": cat_tot.to_dict(),
        "권역_점포수": zone_cat["총계"].to_dict(),
        "권역_비율_pct": zone_shares,
        "층분류_점포수": floor_cat["총계"].to_dict(),
        "층분류_비율_pct": floor_shares,
        "점포수_상위3개_자치구": top3_gu,
        "점포수_상위3개_수치": {gu: int(gu_tot[gu]) for gu in top3_gu},
        "점포수_상위3개_합계_점포수": top3_sum,
        "점포수_상위3개_비율_pct": top3_share,
        "대분류별_최고특화_자치구_LQ": top_lq_by_cat,
        "LQ_고특화_기준": LQ_HIGH_THRESHOLD,
        "LQ_특화_기준": LQ_MID_THRESHOLD,
        "LQ_판정_기준_문구": f"입지계수 {LQ_HIGH_THRESHOLD} 이상 '서울 대비 고특화', {LQ_MID_THRESHOLD} 이상 {LQ_HIGH_THRESHOLD} 미만 '서울 대비 특화', {LQ_MID_THRESHOLD} 미만 '평균 수준'"
    }
    with open(STAGE1_DATA_DIR / "cross_summary.json", "w", encoding="utf-8") as f:
        json.dump(cross_summary, f, ensure_ascii=False, indent=2)
        
    return cross_summary, gu_cat, zone_cat, floor_cat, lq_df, df_gu_top_lq

def analyze_trade_area_sales_stores():
    """5. 상권 매출과 점포 분석 (62개 업종 주분석 + 100개 업종 민감도 + 이상치 이름표 생성)"""
    print(">>> 5. 상권 매출과 점포 분석 중...")
    area = pd.read_csv(RAW_DIR / "상권" / "OA-15560_영역_상권.csv", encoding="utf-8-sig")
    stores = pd.read_csv(RAW_DIR / "상권" / "OA-15577_점포_상권.csv", encoding="utf-8-sig")
    sales = pd.read_csv(RAW_DIR / "상권" / "OA-15572_추정매출_상권.csv", encoding="utf-8-sig")
    
    master_trade_area_count = int(area["상권_코드"].nunique())
    sales_codes = set(sales["서비스_업종_코드"].unique())
    
    # 분기별 매출 보유 상권 수 및 매출 보유율 (분모: 마스터 상권 1,650개)
    q_sales_count = sales.groupby("기준_년분기_코드")["상권_코드"].nunique().to_dict()
    q_sales_count = {int(k): int(v) for k, v in q_sales_count.items()}
    q_sales_share = {int(k): round(int(v) / master_trade_area_count * 100, 2) for k, v in q_sales_count.items()}
    
    # 2025Q4 데이터 필터링
    s_q4 = sales[sales["기준_년분기_코드"] == 20254]
    st_q4 = stores[stores["기준_년분기_코드"] == 20254]
    
    # 62개 업종별 단일상권 1곳 집중도 및 매출 보유 상권 수 계산
    ind_records = []
    for (code, name), g in s_q4.groupby(["서비스_업종_코드", "서비스_업종_코드_명"]):
        tot_sales = int(g["당월_매출_금액"].sum())
        n_mkts_with_sales = int(g["상권_코드"].nunique())
        top_row = g.sort_values(by="당월_매출_금액", ascending=False).iloc[0]
        top_code = int(top_row["상권_코드"])
        top_name = str(top_row["상권_코드_명"])
        top_sales = int(top_row["당월_매출_금액"])
        conc_ratio = round((top_sales / tot_sales) * 100, 2) if tot_sales > 0 else 0.0
        
        # 특정 집중 상권 여부 (집중도 30% 이상 기준)
        is_concentrated = bool(conc_ratio >= 30.0)
        
        # 상권 수 주의 이름표: 50개 미만 (약 3% 미만 소표본 고위험군), 100개 미만 (하위 약 20%)
        if n_mkts_with_sales < 50:
            caution_label = "주의(50개미만)"
        elif n_mkts_with_sales < 100:
            caution_label = "주의(100개미만)"
        else:
            caution_label = "정상"
            
        ind_records.append({
            "업종코드": code,
            "업종명": name,
            "총매출_원": tot_sales,
            "매출보유_상권수": n_mkts_with_sales,
            "상권수_주의_이름표": caution_label,
            "1위상권코드": top_code,
            "1위상권명": top_name,
            "1위상권매출_원": top_sales,
            "1위상권_집중도_pct": conc_ratio,
            "특화집중_상권_여부": is_concentrated
        })
        
    df_ind = pd.DataFrame(ind_records).sort_values(by="총매출_원", ascending=False)
    df_ind.to_csv(STAGE1_DATA_DIR / "industry_sales_concentration_2025Q4.csv", index=False, encoding="utf-8-sig")
    
    # 상권별 점포 수 집계: 62개 업종(주분석) vs 100개 업종(민감도)
    sa_q4 = s_q4.groupby(["상권_코드", "상권_코드_명"])["당월_매출_금액"].sum().reset_index()
    st_62 = st_q4[st_q4["서비스_업종_코드"].isin(sales_codes)].groupby(["상권_코드", "상권_코드_명"])["전체_점포_수"].sum().reset_index().rename(columns={"전체_점포_수": "점포수_62업종"})
    st_100 = st_q4.groupby(["상권_코드", "상권_코드_명"])["전체_점포_수"].sum().reset_index().rename(columns={"전체_점포_수": "점포수_100업종"})
    
    m = pd.merge(sa_q4, st_62, on=["상권_코드", "상권_코드_명"]).merge(st_100, on=["상권_코드", "상권_코드_명"])
    n_total_trd = len(m)
    
    # (1) 62개 업종 기준 상관분석
    r_62, _ = pearsonr(m["점포수_62업종"], m["당월_매출_금액"])
    rho_62, _ = spearmanr(m["점포수_62업종"], m["당월_매출_금액"])
    
    # (2) 100개 업종 기준 상관분석 (민감도: 업종 범위 차이)
    r_100, _ = pearsonr(m["점포수_100업종"], m["당월_매출_금액"])
    rho_100, _ = spearmanr(m["점포수_100업종"], m["당월_매출_금액"])
    
    # (3) 상위 1% 매출 극단치 상권 분리 민감도 분석
    q99_sales = float(m["당월_매출_금액"].quantile(0.99))
    m_filtered = m[m["당월_매출_금액"] <= q99_sales]
    n_filtered_trd = len(m_filtered)
    outlier_trd_count = n_total_trd - n_filtered_trd
    
    r_62_sens, _ = pearsonr(m_filtered["점포수_62업종"], m_filtered["당월_매출_금액"])
    rho_62_sens, _ = spearmanr(m_filtered["점포수_62업종"], m_filtered["당월_매출_금액"])
    r_100_sens, _ = pearsonr(m_filtered["점포수_100업종"], m_filtered["당월_매출_금액"])
    rho_100_sens, _ = spearmanr(m_filtered["점포수_100업종"], m_filtered["당월_매출_금액"])
    
    # (4) 62개 업종 기준 선형회귀 분석 및 잔차 계산
    X = m[["점포수_62업종"]]
    y = m["당월_매출_금액"]
    reg = LinearRegression()
    reg.fit(X, y)
    
    m["예측매출"] = reg.predict(X)
    m["잔차"] = m["당월_매출_금액"] - m["예측매출"]
    
    # 상권별 이상치 이름표 부여 (매출 상위 1% + 특화집중 1위 여부)
    concentrated_market_codes = set(df_ind[df_ind["특화집중_상권_여부"]]["1위상권코드"].unique())
    
    m["매출_이상치_상위1pct"] = m["당월_매출_금액"] > q99_sales
    m["특화집중_상권여부"] = m["상권_코드"].isin(concentrated_market_codes)
    
    def tag_outlier(row):
        is_q99 = row["매출_이상치_상위1pct"]
        is_conc = row["특화집중_상권여부"]
        if is_q99 and is_conc:
            return "복합이상치(매출상위1%+특화집중)"
        elif is_q99:
            return "매출상위1%극단치"
        elif is_conc:
            return "특화집중상권"
        else:
            return "일반상권"
            
    m["이상치_분류태그"] = m.apply(tag_outlier, axis=1)
    
    # 이름표 테이블 저장 (값은 절대 바꾸지 않음)
    m_outlier_export = m[[
        "상권_코드", "상권_코드_명", "당월_매출_금액", "점포수_62업종", "점포수_100업종",
        "매출_이상치_상위1pct", "특화집중_상권여부", "이상치_분류태그"
    ]]
    m_outlier_export.to_csv(STAGE1_DATA_DIR / "trade_area_outlier_flags_2025Q4.csv", index=False, encoding="utf-8-sig")
    
    # 잔차 상하위 5개 상권 도출 및 매출/점포 상위 1위 업종 코드 자동 산출
    top_over = m.sort_values(by="잔차", ascending=False).head(5)
    top_under = m.sort_values(by="잔차", ascending=True).head(5)
    
    # 외부 지식은 [가설]로 명시 (데이터와 맞지 않는 설명 및 '전국 최대' 표현 배제)
    hypotheses_over = {
        3120153: "[가설] 수산물 대량 유통 및 도매 결제 집중",
        3120040: "[가설] 고가 전자기기 및 컴퓨터 하드웨어 B2B 결제 집중",
        3120131: "[가설] 대형 아웃렛 및 패션 도소매 유통 결제 집중",
        3120231: "[가설] 도매시장 내 식자재 및 청과·반찬 도소매 유통 결제 집중",
        3001495: "[가설] 복합쇼핑몰 및 패션 소비 결제 집중"
    }
    
    hypotheses_under = {
        3001493: "[가설] 의류 도매 B2B 특성상 계좌이체/현금 결제 비중이 높아 추정매출 포착률이 낮음",
        3130050: "[가설] 심야 의류 도매 전문 시장으로 개인/카드 결제 비중이 매우 낮음",
        3130327: "[가설] 전통 의류 도매 위주 결제 구조로 추정매출 포착 한계",
        3120039: "[가설] 동대문 배후 의류 봉제·도매 연계로 카드 결제 비중 낮음",
        3120235: "[가설] 법조타운·오피스 중심 상권으로 주말/야간 소비 제한적"
    }
    
    over_list = []
    for _, r in top_over.iterrows():
        c = int(r["상권_코드"])
        s_sub = s_q4[s_q4["상권_코드"] == c].sort_values(by="당월_매출_금액", ascending=False).iloc[0]
        st_sub = st_q4[(st_q4["상권_코드"] == c) & (st_q4["서비스_업종_코드"].isin(sales_codes))].sort_values(by="전체_점포_수", ascending=False).iloc[0]
        
        top_s_pct = round(s_sub["당월_매출_금액"] / r["당월_매출_금액"] * 100, 1)
        top_st_pct = round(st_sub["전체_점포_수"] / r["점포수_62업종"] * 100, 1)
        
        over_list.append({
            "상권코드": c,
            "상권명": str(r["상권_코드_명"]),
            "점포수_62업종": int(r["점포수_62업종"]),
            "실제매출_원": int(r["당월_매출_금액"]),
            "예측매출_원": int(r["예측매출"]),
            "잔차_원": int(r["잔차"]),
            "매출1위_업종명": str(s_sub["서비스_업종_코드_명"]),
            "매출1위_매출액_원": int(s_sub["당월_매출_금액"]),
            "매출1위_비중_pct": top_s_pct,
            "점포1위_업종명": str(st_sub["서비스_업종_코드_명"]),
            "점포1위_점포수": int(st_sub["전체_점포_수"]),
            "점포1위_비중_pct": top_st_pct,
            "가설_원인": hypotheses_over.get(c, "[가설] 세부 업종 결제 구조 차이")
        })
        
    under_list = []
    for _, r in top_under.iterrows():
        c = int(r["상권_코드"])
        s_sub_df = s_q4[s_q4["상권_코드"] == c].sort_values(by="당월_매출_금액", ascending=False)
        st_sub_df = st_q4[(st_q4["상권_코드"] == c) & (st_q4["서비스_업종_코드"].isin(sales_codes))].sort_values(by="전체_점포_수", ascending=False)
        
        s_sub = s_sub_df.iloc[0] if len(s_sub_df) > 0 else None
        st_sub = st_sub_df.iloc[0] if len(st_sub_df) > 0 else None
        
        top_s_pct = round(s_sub["당월_매출_금액"] / r["당월_매출_금액"] * 100, 1) if s_sub is not None else 0.0
        top_st_pct = round(st_sub["전체_점포_수"] / r["점포수_62업종"] * 100, 1) if st_sub is not None else 0.0
        
        under_list.append({
            "상권코드": c,
            "상권명": str(r["상권_코드_명"]),
            "점포수_62업종": int(r["점포수_62업종"]),
            "실제매출_원": int(r["당월_매출_금액"]),
            "예측매출_원": int(r["예측매출"]),
            "잔차_원": int(r["잔차"]),
            "매출1위_업종명": str(s_sub["서비스_업종_코드_명"]) if s_sub is not None else "데이터 없음",
            "매출1위_매출액_원": int(s_sub["당월_매출_금액"]) if s_sub is not None else 0,
            "매출1위_비중_pct": top_s_pct,
            "점포1위_업종명": str(st_sub["서비스_업종_코드_명"]) if st_sub is not None else "데이터 없음",
            "점포1위_점포수": int(st_sub["전체_점포_수"]) if st_sub is not None else 0,
            "점포1위_비중_pct": top_st_pct,
            "가설_원인": hypotheses_under.get(c, "[가설] 세부 업종 결제 구조 차이")
        })
        
    # 상권 유형별 마스터 수 코드로 집계 (OA-15560)
    area_raw = pd.read_csv(RAW_DIR / "상권" / "OA-15560_영역_상권.csv", encoding="utf-8-sig")
    market_type_counts = area_raw["상권_구분_코드_명"].value_counts().to_dict()
    market_type_counts["총계"] = len(area_raw)
    
    tot_stores_62 = int(m["점포수_62업종"].sum())
    tot_stores_100 = int(m["점포수_100업종"].sum())
    diff_stores = tot_stores_100 - tot_stores_62
    diff_ratio_pct = round(diff_stores / tot_stores_100 * 100, 2)

    sales_store_summary = {
        "마스터_상권수": master_trade_area_count,
        "상권유형별_마스터_수": market_type_counts,
        "분기별_매출보유_상권수": q_sales_count,
        "분기별_매출보유_비율_pct": q_sales_share,
        "Q4_분석대상_상권수": n_total_trd,
        "주분석_62업종_점포수_합계": tot_stores_62,
        "민감도_100업종_점포수_합계": tot_stores_100,
        "전체상권_100업종_점포수_합계": int(st_q4["전체_점포_수"].sum()),
        "업종범위_점포수_차이": diff_stores,
        "업종범위_점포수_차이_비율_pct": diff_ratio_pct,
        "주분석_62업종_상관계수_Pearson_r": round(float(r_62), 4),
        "주분석_62업종_순위상관_Spearman_rho": round(float(rho_62), 4),
        "민감도_100업종_상관계수_Pearson_r": round(float(r_100), 4),
        "민감도_100업종_순위상관_Spearman_rho": round(float(rho_100), 4),
        "민감도_제외_상위1pct_기준매출_원": int(q99_sales),
        "민감도_제외_상권수": outlier_trd_count,
        "민감도_분석대상_상권수": n_filtered_trd,
        "주분석_62업종_민감도_Pearson_r": round(float(r_62_sens), 4),
        "주분석_62업종_민감도_Spearman_rho": round(float(rho_62_sens), 4),
        "민감도_100업종_민감도_Pearson_r": round(float(r_100_sens), 4),
        "민감도_100업종_민감도_Spearman_rho": round(float(rho_100_sens), 4),
        "회귀분석_기울기": round(float(reg.coef_[0]), 2),
        "회귀분석_절편": round(float(reg.intercept_), 2),
        "회귀선_상단_매출과대표_Top5": over_list,
        "회귀선_하단_매출과소표_Top5": under_list,
        "특화집중_기준_pct": 30,
        "주의_기준_1단계_상권수": 50,
        "주의_기준_2단계_상권수": 100,
        "주분석_업종수": 62,
        "민감도_업종수": 100,
        "대분류_업종수": 10,
        "자치구수": 25,
        "생활권역수": 5,
        "Top_N": 10
    }
    
    with open(STAGE1_DATA_DIR / "sales_store_analysis.json", "w", encoding="utf-8") as f:
        json.dump(sales_store_summary, f, ensure_ascii=False, indent=2)
        
    return sales_store_summary, df_ind, m

def analyze_spending_outliers():
    """행정동 소비 이상치 8곳 실제 집계 (행정동_마스터 소비_이상치 기준)"""
    print(">>> 행정동 소비 이상치 8곳 실제 집계 중...")
    master = pd.read_csv(PROCESSED_DIR / "행정동_마스터.csv", encoding="utf-8-sig")
    spending = pd.read_csv(RAW_DIR / "OA-22166_소비_행정동.csv", encoding="utf-8-sig")
    
    spend_dong = spending.groupby("행정동_코드")["지출_총금액"].sum().reset_index()
    m = master[["행정동_코드", "행정동_명", "소비_이상치", "소비_최대항목", "소비_최대항목_비중"]].merge(spend_dong, on="행정동_코드")
    
    total_seoul = int(m["지출_총금액"].sum())
    outlier_df = m[m["소비_이상치"]].sort_values(by="지출_총금액", ascending=False)
    outlier_sum = int(outlier_df["지출_총금액"].sum())
    normal_sum = total_seoul - outlier_sum
    
    outlier_ratio = round(outlier_sum / total_seoul * 100, 2)
    normal_ratio = round(normal_sum / total_seoul * 100, 2)
    
    details = []
    for _, r in outlier_df.iterrows():
        details.append({
            "행정동_코드": int(r["행정동_코드"]),
            "행정동_명": str(r["행정동_명"]),
            "지출_총금액_원": int(r["지출_총금액"]),
            "지출_조원": round(r["지출_총금액"] / 1e12, 2),
            "서울_비중_pct": round(r["지출_총금액"] / total_seoul * 100, 2),
            "소비_최대항목": str(r["소비_최대항목"]),
            "소비_최대항목_비중_pct": float(r["소비_최대항목_비중"])
        })
        
    summary = {
        "서울_총지출_원": total_seoul,
        "서울_총지출_조원": round(total_seoul / 1e12, 2),
        "이상치_8개동_지출합계_원": outlier_sum,
        "이상치_8개동_지출합계_조원": round(outlier_sum / 1e12, 2),
        "이상치_8개동_지출비중_pct": outlier_ratio,
        "정상_417개동_지출합계_원": normal_sum,
        "정상_417개동_지출합계_조원": round(normal_sum / 1e12, 2),
        "정상_417개동_지출비중_pct": normal_ratio,
        "이상치_8개동_세부내역": details
    }
    
    with open(STAGE1_DATA_DIR / "spending_outlier_dong_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        
    pd.DataFrame(details).to_csv(STAGE1_DATA_DIR / "spending_outlier_dong_summary.csv", index=False, encoding="utf-8-sig")
    return summary

def check_trade_area_readiness():
    """6. 상권 특성 데이터 준비도 코드로 직접 계산 (파일별 분리, 행수, 빠진 상권, 빠진 상권분기 칸수, 컬럼별 0값, 결측치)"""
    print(">>> 6. 상권 특성 데이터 준비도 코드로 계산 중...")
    area = pd.read_csv(RAW_DIR / "상권" / "OA-15560_영역_상권.csv", encoding="utf-8-sig")
    master_markets = set(area["상권_코드"].unique())
    n_master = len(master_markets) # 1650
    total_slots = n_master * 4     # 6600
    
    pop = pd.read_csv(RAW_DIR / "상권" / "OA-15584_상주인구_상권.csv", encoding="utf-8-sig")
    work = pd.read_csv(RAW_DIR / "상권" / "OA-15569_직장인구_상권.csv", encoding="utf-8-sig")
    flow = pd.read_csv(RAW_DIR / "상권" / "OA-15568_길단위인구_상권.csv", encoding="utf-8-sig")
    sales = pd.read_csv(RAW_DIR / "상권" / "OA-15572_추정매출_상권.csv", encoding="utf-8-sig")
    stores = pd.read_csv(RAW_DIR / "상권" / "OA-15577_점포_상권.csv", encoding="utf-8-sig")
    change = pd.read_csv(RAW_DIR / "상권" / "OA-15576_상권변화지표_상권.csv", encoding="utf-8-sig")
    spend = pd.read_csv(RAW_DIR / "OA-22166_소비_행정동.csv", encoding="utf-8-sig")
    dong_master = pd.read_csv(PROCESSED_DIR / "행정동_마스터.csv", encoding="utf-8-sig")
    
    # 1. 상주인구 (OA-15584)
    missing_pop = len(master_markets - set(pop["상권_코드"].unique()))
    pop_slots = len(pop.groupby(["상권_코드", "기준_년분기_코드"]))
    missing_pop_slots = total_slots - pop_slots
    pop_zero_cnt = int((pop["총_상주인구_수"] == 0).sum())
    
    # 2. 직장인구 (OA-15569)
    missing_work = len(master_markets - set(work["상권_코드"].unique()))
    work_slots = len(work.groupby(["상권_코드", "기준_년분기_코드"]))
    missing_work_slots = total_slots - work_slots
    work_zero_cnt = int((work["총_직장_인구_수"] == 0).sum())
    
    # 3. 유동인구 (OA-15568 길단위)
    missing_flow = len(master_markets - set(flow["상권_코드"].unique()))
    flow_slots = len(flow.groupby(["상권_코드", "기준_년분기_코드"]))
    missing_flow_slots = total_slots - flow_slots
    flow_zero_cnt = int((flow["총_유동인구_수"] == 0).sum())
    
    # 4. 추정매출 (OA-15572 객단가/매출변화)
    missing_sales = len(master_markets - set(sales["상권_코드"].unique()))
    sales_slots = len(sales.groupby(["상권_코드", "기준_년분기_코드"]))
    missing_sales_slots = total_slots - sales_slots
    sales_zero_amt = int((sales["당월_매출_금액"] == 0).sum())
    sales_zero_cnt = int((sales["당월_매출_건수"] == 0).sum())
    
    # 5. 점포 (OA-15577 프랜차이즈/경쟁/개폐업)
    missing_stores = len(master_markets - set(stores["상권_코드"].unique()))
    stores_slots = len(stores.groupby(["상권_코드", "기준_년분기_코드"]))
    missing_stores_slots = total_slots - stores_slots
    stores_zero_tot = int((stores["전체_점포_수"] == 0).sum())
    stores_zero_fran = int((stores["프랜차이즈_점포_수"] == 0).sum())
    stores_zero_open = int((stores["개업_점포_수"] == 0).sum())
    stores_zero_close = int((stores["폐업_점포_수"] == 0).sum())
    stores_zero_open_rate = int((stores["개업_율"] == 0).sum())
    stores_zero_close_rate = int((stores["폐업_률"] == 0).sum())
    
    # 6. 상권영역 (OA-15560)
    missing_area = len(master_markets - set(area["상권_코드"].unique()))
    area_zero_size = int((area["영역_면적"] == 0).sum())
    
    # 7. 상권변화지표 (OA-15576)
    missing_change = len(master_markets - set(change["상권_코드"].unique()))
    change_slots = len(change.groupby(["상권_코드", "기준_년분기_코드"]))
    missing_change_slots = total_slots - change_slots
    change_zero_op = int((change["운영_영업_개월_평균"] == 0).sum())
    change_zero_cl = int((change["폐업_영업_개월_평균"] == 0).sum())
    change_zero_str = f"운영_영업_개월_평균={change_zero_op:,}건, 폐업_영업_개월_평균={change_zero_cl:,}건"
    
    # 8. 소비 행정동 (OA-22166)
    master_dongs = set(dong_master["행정동_코드"].unique())
    n_master_dongs = len(master_dongs) # 425
    dong_total_slots = n_master_dongs * 4 # 1700
    spend_slots = len(spend.groupby(["행정동_코드", "기준_년분기_코드"]))
    missing_spend_slots = dong_total_slots - spend_slots # 0
    spend_zero_amt = int((spend["지출_총금액"] == 0).sum())
    spend_nulls = int(spend["지출_총금액"].isna().sum())
    
    # 소비 파일에 없는 행정동의 상권 수 계산
    spend_dongs = set(spend["행정동_코드"].unique())
    area_dongs = set(area["행정동_코드"].unique())
    dongs_not_in_spend = area_dongs - spend_dongs
    markets_in_missing_dongs = int(area["행정동_코드"].isin(dongs_not_in_spend).sum()) # 0
    
    readiness_items = [
        {
            "상권_특성_항목": "고객 구성 (상주인구)",
            "계산가능_여부": "필요한 컬럼이 있어 계산할 수 있음",
            "대응_원천파일": "OA-15584_상주인구_상권.csv",
            "파일_행수": len(pop),
            "빠진_상권수": str(missing_pop),
            "빠진_상권분기_칸수": str(missing_pop_slots),
            "주요컬럼_0값_건수": f"총_상주인구_수={pop_zero_cnt:,}건",
            "결측치_수": int(pop["총_상주인구_수"].isna().sum()),
            "활용가능_컬럼": "총_상주인구_수, 남성/여성_상주인구_수, 연령대별_상주인구_수",
            "한계점_및_주의사항": "4개 분기 수치가 동일하여 계절별 인구 변동 반영 제한"
        },
        {
            "상권_특성_항목": "고객 구성 (직장인구)",
            "계산가능_여부": "필요한 컬럼이 있어 계산할 수 있음",
            "대응_원천파일": "OA-15569_직장인구_상권.csv",
            "파일_행수": len(work),
            "빠진_상권수": str(missing_work),
            "빠진_상권분기_칸수": str(missing_work_slots),
            "주요컬럼_0값_건수": f"총_직장_인구_수={work_zero_cnt:,}건",
            "결측치_수": int(work["총_직장_인구_수"].isna().sum()),
            "활용가능_컬럼": "총_직장_인구_수, 남성/여성_직장_인구_수, 연령대별_직장_인구_수",
            "한계점_및_주의사항": "4개 분기 수치가 동일하여 계절별 직장인 변화 파악 불가"
        },
        {
            "상권_특성_항목": "고객 구성 (유동인구)",
            "계산가능_여부": "필요한 컬럼이 있어 계산할 수 있음",
            "대응_원천파일": "OA-15568_길단위인구_상권.csv",
            "파일_행수": len(flow),
            "빠진_상권수": str(missing_flow),
            "빠진_상권분기_칸수": str(missing_flow_slots),
            "주요컬럼_0값_건수": f"총_유동인구_수={flow_zero_cnt:,}건",
            "결측치_수": int(flow["총_유동인구_수"].isna().sum()),
            "활용가능_컬럼": "총_유동인구_수, 시간대별_유동인구_수, 요일별_유동인구_수",
            "한계점_및_주의사항": f"2025년 2~4분기 중 일부 상권 미집계 칸({missing_flow_slots}칸) 존재"
        },
        {
            "상권_특성_항목": "객단가",
            "계산가능_여부": "필요한 컬럼이 있어 계산할 수 있음",
            "대응_원천파일": "OA-15572_추정매출_상권.csv",
            "파일_행수": len(sales),
            "빠진_상권수": str(missing_sales),
            "빠진_상권분기_칸수": str(missing_sales_slots),
            "주요컬럼_0값_건수": f"당월_매출_금액={sales_zero_amt:,}건, 당월_매출_건수={sales_zero_cnt:,}건",
            "결측치_수": int(sales["당월_매출_금액"].isna().sum() + sales["당월_매출_건수"].isna().sum()),
            "활용가능_컬럼": "당월_매출_금액, 당월_매출_건수 (매출금액 ÷ 매출건수)",
            "한계점_및_주의사항": "업종별 단가 편차가 커 상권 전체 단순평균보다 업종별 표준화 선행 필요"
        },
        {
            "상권_특성_항목": "프랜차이즈 비율",
            "계산가능_여부": "필요한 컬럼이 있어 계산할 수 있음",
            "대응_원천파일": "OA-15577_점포_상권.csv",
            "파일_행수": len(stores),
            "빠진_상권수": str(missing_stores),
            "빠진_상권분기_칸수": str(missing_stores_slots),
            "주요컬럼_0값_건수": f"프랜차이즈_점포_수={stores_zero_fran:,}건, 전체_점포_수={stores_zero_tot:,}건",
            "결측치_수": int(stores["전체_점포_수"].isna().sum() + stores["프랜차이즈_점포_수"].isna().sum()),
            "활용가능_컬럼": "프랜차이즈_점포_수, 전체_점포_수 (프랜차이즈 합 ÷ 전체 점포 합)",
            "한계점_및_주의사항": "행별 비율의 단순평균 왜곡 방지를 위해 점포 수 합계로 재계산 필수"
        },
        {
            "상권_특성_항목": "매출 변화",
            "계산가능_여부": "필요한 컬럼이 있어 계산할 수 있음",
            "대응_원천파일": "OA-15572_추정매출_상권.csv",
            "파일_행수": len(sales),
            "빠진_상권수": str(missing_sales),
            "빠진_상권분기_칸수": str(missing_sales_slots),
            "주요컬럼_0값_건수": f"당월_매출_금액={sales_zero_amt:,}건",
            "결측치_수": int(sales["당월_매출_금액"].isna().sum()),
            "활용가능_컬럼": "기준_년분기_코드 (20251~20254), 당월_매출_금액",
            "한계점_및_주의사항": "2025년 4개 분기 자료로 계절 요인과 추세 성장의 분리가 제한적임"
        },
        {
            "상권_특성_항목": "경쟁 (점포 밀집도)",
            "계산가능_여부": "필요한 컬럼이 있어 계산할 수 있음",
            "대응_원천파일": "OA-15577_점포_상권.csv",
            "파일_행수": len(stores),
            "빠진_상권수": str(missing_stores),
            "빠진_상권분기_칸수": str(missing_stores_slots),
            "주요컬럼_0값_건수": f"전체_점포_수={stores_zero_tot:,}건",
            "결측치_수": int(stores["전체_점포_수"].isna().sum()),
            "활용가능_컬럼": "전체_점포_수 (상권 내 업종별 점포 집적도 산출)",
            "한계점_및_주의사항": "상권 내 점포 밀집도 지표이며 상권 경계 외부 인접 점포는 미포함"
        },
        {
            "상권_특성_항목": "경쟁 (상권 영역)",
            "계산가능_여부": "필요한 컬럼이 있어 계산할 수 있음",
            "대응_원천파일": "OA-15560_영역_상권.csv",
            "파일_행수": len(area),
            "빠진_상권수": str(missing_area),
            "빠진_상권분기_칸수": "0",
            "주요컬럼_0값_건수": f"영역_면적={area_zero_size:,}건",
            "결측치_수": int(area["영역_면적"].isna().sum()),
            "활용가능_컬럼": "영역_면적 (점포 수 ÷ 영역면적으로 점포밀도 산출)",
            "한계점_및_주의사항": "단일 연도 스냅샷이며 상권 경계 외부 인접 시설 미포함"
        },
        {
            "상권_특성_항목": "개폐업 수준",
            "계산가능_여부": "필요한 컬럼이 있어 계산할 수 있음",
            "대응_원천파일": "OA-15577_점포_상권.csv",
            "파일_행수": len(stores),
            "빠진_상권수": str(missing_stores),
            "빠진_상권분기_칸수": str(missing_stores_slots),
            "주요컬럼_0값_건수": f"개업_점포_수={stores_zero_open:,}건, 폐업_점포_수={stores_zero_close:,}건, 개업_율={stores_zero_open_rate:,}건, 폐업_률={stores_zero_close_rate:,}건",
            "결측치_수": int(stores["개업_점포_수"].isna().sum() + stores["폐업_점포_수"].isna().sum()),
            "활용가능_컬럼": "개업_점포_수, 폐업_점포_수, 개업_율, 폐업_률",
            "한계점_및_주의사항": "상권×업종 집계 데이터로 개별 점포의 개폐업 이력은 포함되지 않음"
        },
        {
            "상권_특성_항목": "상권 변화 지표",
            "계산가능_여부": "필요한 컬럼이 있어 계산할 수 있음",
            "대응_원천파일": "OA-15576_상권변화지표_상권.csv",
            "파일_행수": len(change),
            "빠진_상권수": str(missing_change),
            "빠진_상권분기_칸수": str(missing_change_slots),
            "주요컬럼_0값_건수": change_zero_str,
            "결측치_수": int(change["상권_변화_지표_명"].isna().sum()),
            "활용가능_컬럼": "상권_변화_지표_명, 운영_영업_개월_평균, 폐업_영업_개월_평균",
            "한계점_및_주의사항": "상권 단위 집계 지표로 평균 개월 수만 제공"
        },
        {
            "상권_특성_항목": "소비 수준",
            "계산가능_여부": "필요한 컬럼이 있어 계산할 수 있음",
            "대응_원천파일": "OA-22166_소비_행정동.csv",
            "파일_행수": len(spend),
            "빠진_상권수": "해당 없음",
            "빠진_상권분기_칸수": "해당 없음",
            "주요컬럼_0값_건수": f"지출_총금액={spend_zero_amt:,}건",
            "결측치_수": spend_nulls,
            "활용가능_컬럼": "행정동 지출_총금액, 항목별_지출금액",
            "한계점_및_주의사항": f"행정동 {n_master_dongs}개 전 분기 집계 완료(빈칸 {missing_spend_slots}칸). 소비 데이터 미수집 행정동에 속한 상권 수는 {markets_in_missing_dongs}개임 (상권 공간 매핑 연계 필요)"
        },
        {
            "상권_특성_항목": "임대료 · 보증금",
            "계산가능_여부": "데이터 없음",
            "대응_원천파일": "데이터 없음",
            "파일_행수": 0,
            "빠진_상권수": str(n_master),
            "빠진_상권분기_칸수": str(total_slots),
            "주요컬럼_0값_건수": "데이터 없음",
            "결측치_수": 0,
            "활용가능_컬럼": "데이터 없음",
            "한계점_및_주의사항": "원천 데이터 미제공으로 외부 공공 임대 시세 연계 없이는 산출 불가"
        }
    ]
    
    df_readiness = pd.DataFrame(readiness_items)
    df_readiness.to_csv(STAGE1_DATA_DIR / "trade_area_readiness_table.csv", index=False, encoding="utf-8-sig")
    with open(STAGE1_DATA_DIR / "trade_area_readiness.json", "w", encoding="utf-8") as f:
        json.dump(readiness_items, f, ensure_ascii=False, indent=2)
    return df_readiness

def generate_visualizations(sbiz, m, df_ind):
    """차트 생성 및 images/eda_stage1/ 저장 (파이차트 절대 미사용, seed 고정 재현성 보장)"""
    print(">>> 7. 시각화 차트 이미지 생성 중...")
    np.random.seed(42)
    
    # 1. 자치구별 점포 수 가로 막대 차트
    plt.figure(figsize=(10, 8))
    gu_order = sbiz["시군구명"].value_counts()
    sns.barplot(x=gu_order.values, y=gu_order.index, hue=gu_order.index, palette="viridis", legend=False)
    plt.title("자치구별 소상공인 점포 수 현황 (2025-12-31 시점)", fontsize=14, fontweight="bold")
    plt.xlabel("점포 수 (개)")
    plt.ylabel("자치구명")
    plt.tight_layout()
    plt.savefig(IMAGES_DIR / "01_자치구별_점포수_분포.png", dpi=200)
    plt.close()
    
    # 2. 층분류별 점포 수 막대 차트 (파이차트 대신 세로 막대그래프)
    plt.figure(figsize=(9, 5))
    floor_order = sbiz["층분류"].value_counts()
    bars = plt.bar(floor_order.index, floor_order.values, color="#3498db")
    for bar in bars:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., h + 2000, f"{h:,}건", ha='center', va='bottom', fontsize=10)
    plt.title("소상공인 점포 층분류별 분포 (2025-12-31 시점)", fontsize=14, fontweight="bold")
    plt.xlabel("층 분류")
    plt.ylabel("점포 수 (건)")
    plt.ylim(0, max(floor_order.values) * 1.15)
    plt.tight_layout()
    plt.savefig(IMAGES_DIR / "02_층분류별_점포수_막대.png", dpi=200)
    plt.close()
    
    # 3. 62개 업종 기준 상권 점포 수 vs 매출 산점도 및 회귀선 (민감도 분석 비교)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 전체 상권 (62개 업종 점포수)
    sns.regplot(data=m, x="점포수_62업종", y="당월_매출_금액", ax=ax1, seed=42,
                scatter_kws={"alpha": 0.4, "color": "#2980b9"}, line_kws={"color": "#e74c3c"})
    ax1.set_title("전체 상권: 62개 업종 점포 수 vs 추정매출액 (2025Q4)", fontsize=13, fontweight="bold")
    ax1.set_xlabel("상권 내 62개 업종 점포 수 (개)")
    ax1.set_ylabel("추정매출액 (원)")
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{x/1e8:,.0f}억"))
    
    # 민감도: 상위 1% 제외
    q99 = m["당월_매출_금액"].quantile(0.99)
    m_sub = m[m["당월_매출_금액"] <= q99]
    sns.regplot(data=m_sub, x="점포수_62업종", y="당월_매출_금액", ax=ax2, seed=42,
                scatter_kws={"alpha": 0.4, "color": "#27ae60"}, line_kws={"color": "#e67e22"})
    ax2.set_title("민감도 분석: 상위 1% 이상치 제외 상권 (2025Q4)", fontsize=13, fontweight="bold")
    ax2.set_xlabel("상권 내 62개 업종 점포 수 (개)")
    ax2.set_ylabel("추정매출액 (원)")
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{x/1e8:,.0f}억"))
    
    plt.tight_layout()
    plt.savefig(IMAGES_DIR / "03_상권_점포수_매출_상관및민감도.png", dpi=200)
    plt.close()
    
    # 4. 상권 1곳 집중도 상위 10개 업종 가로 막대 차트
    plt.figure(figsize=(10, 6))
    top10_conc = df_ind.sort_values(by="1위상권_집중도_pct", ascending=False).head(10)
    bars = plt.barh(top10_conc["업종명"][::-1], top10_conc["1위상권_집중도_pct"][::-1], color="#e74c3c")
    for bar in bars:
        w = bar.get_width()
        plt.text(w + 1, bar.get_y() + bar.get_height()/2., f"{w:.1f}%", ha='left', va='center', fontsize=10)
    plt.title("상권 1곳 집중도 상위 10개 업종 (특화 상권 쏠림도, 2025Q4)", fontsize=13, fontweight="bold")
    plt.xlabel("1위 상권 매출 비중 (%)")
    plt.xlim(0, 100)
    plt.tight_layout()
    plt.savefig(IMAGES_DIR / "04_업종별_단일상권_집중도_Top10.png", dpi=200)
    plt.close()
    
    print(">>> 모든 차트 이미지 생성 완료!")

def main():
    t_start = time.time()
    print("=== [SpotFit Stage 1] 데이터 프로파일링 및 기본 EDA 시작 ===")
    
    df_prof = profile_files()
    sbiz, sbiz_quality = analyze_sbiz_quality()
    stats = calculate_descriptive_stats(sbiz)
    cross_sum, gu_cat, zone_cat, floor_cat, lq_df, df_gu_top_lq = analyze_cross_tabulations(sbiz)
    sales_sum, df_ind, m = analyze_trade_area_sales_stores()
    spending_outliers = analyze_spending_outliers()
    trade_readiness = check_trade_area_readiness()
    generate_visualizations(sbiz, m, df_ind)
    
    elapsed = round(time.time() - t_start, 2)
    print(f"=== [SpotFit Stage 1] 집계 및 분석 완료! (소요 시간: {elapsed}초) ===")

if __name__ == "__main__":
    main()
