#!/usr/bin/env python3
"""SpotFit 공용 전처리 표 만들기 (2025년분)

data/PREPROCESSING.md 의 규칙대로 data/raw/ 를 정리해 data/processed/ 에 표 4개를 만든다.
  업종_공통그룹.csv     상권 62개 업종·소비 10개 항목 → 공통 그룹 (7장)
  행정동_마스터.csv     425개 동 × 키·고정 값·소비 이상치 플래그 (2장, 4.1절, 6장)
  행정동_분기.csv       425개 동 × 2025Q1~Q4, 분기마다 바뀌는 값 (3장, 4.2절)
  상권_업종_분기.csv    상권 × 62개 업종 × 분기, 매출·점포·개폐업 수 (5장)

사용법 (pandas, openpyxl 필요):
  python scripts/build_processed_2025.py
  uv run --no-project --with pandas,openpyxl python scripts/build_processed_2025.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
K, Q = "행정동_코드", "기준_년분기_코드"
QUARTERS = [20251, 20252, 20253, 20254]

# ── 규칙 (data/PREPROCESSING.md) ─────────────────────────────────────
NEW_TO_OLD = {11230515: 11230536, 11230533: 11230536,   # 신설동·용두동 → 용신동
              11740525: 11740520, 11740526: 11740520,   # 상일1·2동 → 상일동
              11680675: 11680740}                       # 개포3동 → 일원2동
MONTH_TO_Q = {"03": 20251, "06": 20252, "09": 20253, "12": 20254}
OUTLIER_SHARE = 0.9   # 한 항목이 동 지출의 90% 이상이면 소비 이상치
GROUPS = {
    "외식": ["한식음식점", "중식음식점", "일식음식점", "양식음식점", "제과점", "패스트푸드점",
             "치킨전문점", "분식전문점", "커피-음료"],
    "유흥": ["호프-간이주점"],
    "식료품": ["슈퍼마켓", "편의점", "미곡판매", "육류판매", "수산물판매", "청과상", "반찬가게"],
    "의료": ["일반의원", "치과의원", "한의원", "의약품", "의료기기"],
    "교육": ["일반교습학원", "외국어학원", "예술학원"],
    "의류·잡화": ["일반의류", "신발", "가방", "안경", "시계및귀금속", "섬유제품"],
    "생활용품": ["화장품", "가구", "가전제품", "철물점", "인테리어", "조명용품", "문구", "화초",
                 "애완동물", "컴퓨터및주변장치판매", "핸드폰"],
    "여가·오락": ["PC방", "노래방", "당구장", "골프연습장", "스포츠클럽", "스포츠 강습", "서적",
                  "완구", "운동/경기용품"],
    "숙박": ["여관"],
    "생활서비스": ["미용실", "네일숍", "피부관리실", "세탁소", "가전제품수리"],
    "부동산": ["부동산중개업"],
    "교통": ["자동차수리", "자동차미용", "자전거 및 기타운송장비"],
    "연결 안 함": ["전자상거래업"],
}
CONS_GROUP = {"음식": "외식", "유흥": "유흥", "식료품": "식료품", "의료비": "의료", "교육": "교육",
              "의류_신발": "의류·잡화", "생활용품": "생활용품", "여가_문화": "여가·오락",
              "기타": "생활서비스", "교통": "교통"}
SKT_METRICS = {"배달 서비스 사용일수": "SKT_배달_사용일수",
               "쇼핑 서비스 사용일수": "SKT_쇼핑_사용일수",
               "금융 서비스 사용일수": "SKT_금융_사용일수"}


def read(name, **kw):
    return pd.read_csv(RAW / name, encoding="utf-8-sig", low_memory=False, **kw)


def fix_name(s):
    return s.str.replace("?", "·", regex=False)


def latest(df):
    """4개 분기 값이 같은 파일은 Q4 한 장만 쓴다 (3장)."""
    return df[df[Q] == df[Q].max()].drop(columns=Q)


def cons_col(item):
    return f"{item}_지출_총금액"


# ── 업종 공통 그룹 ────────────────────────────────────────────────────
def build_mapping(sales):
    to_group = {name: g for g, names in GROUPS.items() for name in names}
    trade = sales[["서비스_업종_코드", "서비스_업종_코드_명"]].drop_duplicates().sort_values("서비스_업종_코드")
    missing = set(trade["서비스_업종_코드_명"]) - set(to_group)
    assert not missing, f"공통 그룹이 없는 업종: {missing}"
    trade = trade.rename(columns={"서비스_업종_코드": "원본코드", "서비스_업종_코드_명": "원본분류"})
    trade.insert(0, "원본출처", "상권_업종")
    trade["공통그룹"] = trade["원본분류"].map(to_group)
    cons = pd.DataFrame({"원본출처": "소비_항목", "원본코드": [cons_col(i) for i in CONS_GROUP],
                         "원본분류": [i.replace("_", "·") for i in CONS_GROUP],
                         "공통그룹": list(CONS_GROUP.values())})
    return pd.concat([trade, cons], ignore_index=True)


# ── 상권 × 업종 × 분기 ────────────────────────────────────────────────
def build_trade(sales, mapping):
    stores = read("상권/OA-15577_점포_상권.csv")
    area = read("상권/OA-15560_영역_상권.csv")
    key = [Q, "상권_코드", "서비스_업종_코드"]
    stores = stores[stores["서비스_업종_코드"].isin(sales["서비스_업종_코드"])]   # 62개 업종 기준 (5장)
    t = stores[key + ["전체_점포_수", "일반_점포_수", "프랜차이즈_점포_수", "개업_점포_수", "폐업_점포_수"]].merge(
        sales[key + ["당월_매출_금액", "당월_매출_건수"]], on=key, how="outer")
    # 점포도 매출도 개폐업도 없는 칸은 버린다
    count_cols = ["전체_점포_수", "개업_점포_수", "폐업_점포_수"]
    t = t[(t[count_cols].fillna(0).sum(axis=1) > 0) | t["당월_매출_금액"].notna()]
    area = area[["상권_코드", "상권_코드_명", "상권_구분_코드_명", K]].copy()
    area["상권_코드_명"] = fix_name(area["상권_코드_명"])
    groups = mapping[mapping["원본출처"] == "상권_업종"]
    t = (t.merge(area, on="상권_코드", how="left")
          .merge(groups[["원본코드", "원본분류", "공통그룹"]].rename(
              columns={"원본코드": "서비스_업종_코드", "원본분류": "서비스_업종_코드_명"}),
              on="서비스_업종_코드", how="left"))
    cols = [Q, "상권_코드", "상권_코드_명", "상권_구분_코드_명", K, "서비스_업종_코드", "서비스_업종_코드_명",
            "공통그룹", "당월_매출_금액", "당월_매출_건수", "전체_점포_수", "일반_점포_수",
            "프랜차이즈_점포_수", "개업_점포_수", "폐업_점포_수"]
    return t[cols].sort_values(key).reset_index(drop=True)


# ── 행정동 마스터 ────────────────────────────────────────────────────
def load_geo():
    gj = json.loads((RAW / "geo" / "HangJeongDong_ver20251231.geojson").read_text(encoding="utf-8"))
    rows = [(int(p["adm_cd2"][:8]), int(p["sgg"]), p["sggnm"])
            for p in (f["properties"] for f in gj["features"]) if p["sido"] == "11"]
    return pd.DataFrame(rows, columns=["경계_코드", "자치구_코드", "자치구_명"])


def skt_key(master):
    """SKT 7자리 코드는 자치구 + 행정동 이름으로 붙인다 (2.3절)."""
    t = pd.read_excel(RAW / "living" / "통신정보_2025.12.xlsx", usecols=["행정동코드", "자치구", "행정동"])
    t = (t.drop_duplicates()
          .rename(columns={"자치구": "자치구_명", "행정동": "행정동_명", "행정동코드": "SKT_코드"}))
    return master[[K, "자치구_명", "행정동_명"]].merge(t, on=["자치구_명", "행정동_명"], how="left")


def build_master(cons):
    geo = load_geo()
    geo[K] = geo["경계_코드"].replace(NEW_TO_OLD)
    bounds = geo.groupby(K)["경계_코드"].apply(lambda s: ",".join(str(c) for c in sorted(s)))
    gu = geo.drop_duplicates("자치구_코드").set_index("자치구_코드")["자치구_명"]

    m = read("OA-22160_영역_행정동.csv")[[K, "행정동_명", "영역_면적"]]
    m["행정동_명"] = fix_name(m["행정동_명"])
    m["자치구_코드"] = m[K] // 1000
    m["자치구_명"] = m["자치구_코드"].map(gu)
    keys = skt_key(m).set_index(K)["SKT_코드"]
    m["SKT_코드"] = m[K].map(keys).astype("Int64")
    m["경계_코드"] = m[K].map(bounds)
    m["면적_km2"] = (m.pop("영역_면적") / 1e6).round(4)

    res = latest(read("OA-22183_상주인구_행정동.csv"))
    res_cols = ["총_상주인구_수", "남성_상주인구_수", "여성_상주인구_수"] + \
               [c for c in res.columns if c.startswith("연령대_")] + ["총_가구_수"]
    wrk = latest(read("OA-22184_직장인구_행정동.csv"))[[K, "총_직장_인구_수"]]
    apt = latest(read("OA-22163_아파트_행정동.csv"))[[K, "아파트_단지_수", "아파트_평균_시가"]]
    fac = latest(read("OA-22169_집객시설_행정동.csv")).drop(columns="행정동_코드_명").fillna(0)
    fac = fac.astype({c: "int64" for c in fac.columns if c != K})
    m = (m.merge(res[[K] + res_cols], on=K, how="left")
          .merge(wrk, on=K, how="left")          # 직장인구 없는 11개 동은 NaN (2.5절)
          .merge(apt, on=K, how="left")          # 둔촌1동은 NaN
          .merge(fac, on=K, how="left"))

    nps = read("국민연금_시군구_평균소득월액_2025.csv")
    nps = nps[nps["시군구"].str.startswith("서울특별시")]
    m["자치구_평균소득월액"] = m["자치구_명"].map(
        nps.set_index(nps["시군구"].str.replace("서울특별시", "", regex=False))["평균소득월액"])

    sbiz = read("소상공인_상가정보_서울.csv", usecols=["행정동코드", "상권업종대분류명"])
    sbiz[K] = sbiz["행정동코드"].replace(NEW_TO_OLD)
    counts = sbiz.groupby([K, "상권업종대분류명"]).size().unstack(fill_value=0)
    counts.columns = [f"점포_202512_{c}" for c in counts.columns]
    counts.insert(0, "점포_202512_전체", counts.sum(axis=1))
    m = m.merge(counts.reset_index(), on=K, how="left")

    area = read("상권/OA-15560_영역_상권.csv")
    m["상권_수"] = m[K].map(area.groupby(K).size()).fillna(0).astype("int64")

    # 소비 이상치 (6장): 2025년 합계에서 한 항목이 90% 이상. 값은 그대로 두고 이름표만 붙인다
    items = list(CONS_GROUP)
    year = cons.groupby(K)[["지출_총금액"] + [cons_col(i) for i in items]].sum()
    share = year[[cons_col(i) for i in items]].div(year["지출_총금액"], axis=0)
    flag = pd.DataFrame({
        "소비_연간_지출_총금액": year["지출_총금액"],
        "소비_최대항목": share.idxmax(axis=1).str.replace("_지출_총금액", "", regex=False).str.replace("_", "·", regex=False),
        "소비_최대항목_비중": (share.max(axis=1) * 100).round(1),
        "소비_이상치": share.max(axis=1) >= OUTLIER_SHARE,
    })
    return m.merge(flag.reset_index(), on=K, how="left")


# ── 행정동 × 분기 ────────────────────────────────────────────────────
def skt_quarters(master):
    names = master.set_index(["자치구_명", "행정동_명"])[K]
    frames = []
    for month, quarter in MONTH_TO_Q.items():
        t = pd.read_excel(RAW / "living" / f"통신정보_2025.{month}.xlsx",
                          usecols=["자치구", "행정동", "총인구수", "1인가구수"] + list(SKT_METRICS))
        for col in SKT_METRICS:            # 성 × 연령 칸을 인구로 가중평균 (4.3절)
            t[col] = t[col] * t["총인구수"]
        g = t.groupby(["자치구", "행정동"]).sum(numeric_only=True)
        for col, new in SKT_METRICS.items():
            g[new] = (g.pop(col) / g["총인구수"]).round(2)
        g["SKT_1인가구_비율"] = (g["1인가구수"] / g["총인구수"] * 100).round(2)
        g = g.rename(columns={"총인구수": "SKT_총인구", "1인가구수": "SKT_1인가구수"})
        g.index = g.index.map(lambda ix: names.get(ix))
        g = g[g.index.notna()]
        g.index = g.index.astype("int64")
        g.index.name = K
        frames.append(g.reset_index().assign(**{Q: quarter}))
    return pd.concat(frames, ignore_index=True)


def build_quarter(master, cons, trade):
    p = pd.MultiIndex.from_product([master[K], QUARTERS], names=[K, Q]).to_frame(index=False)
    p = p.merge(master[[K, "행정동_명"]], on=K)

    c = cons[[K, Q, "지출_총금액"] + [cons_col(i) for i in CONS_GROUP]]
    flow = read("OA-22178_길단위인구_행정동.csv")[[K, Q, "총_유동인구_수"]]

    t = trade.dropna(subset=[K])
    agg = t.groupby([K, Q])[["당월_매출_금액", "당월_매출_건수", "전체_점포_수", "개업_점포_수", "폐업_점포_수"]].sum()
    agg.columns = ["상권_매출_금액", "상권_매출_건수", "상권_점포_수", "상권_개업_점포_수", "상권_폐업_점포_수"]
    by_group = t.pivot_table(index=[K, Q], columns="공통그룹", values="당월_매출_금액", aggfunc="sum", fill_value=0)
    by_group = by_group[[g for g in GROUPS if g in by_group.columns]]
    by_group.columns = [f"상권_매출_{g.replace(' ', '')}" for g in by_group.columns]

    p = (p.merge(c, on=[K, Q], how="left")
          .merge(flow, on=[K, Q], how="left")
          .merge(agg.join(by_group).reset_index(), on=[K, Q], how="left")   # 상권이 없는 26개 동은 NaN
          .merge(skt_quarters(master), on=[K, Q], how="left"))             # 항동은 NaN
    return p


# ── 실행 ────────────────────────────────────────────────────────────
def check(mapping, master, quarter, trade):
    assert mapping[mapping["원본출처"] == "상권_업종"].shape[0] == 62
    assert len(master) == 425 and master[K].is_unique
    assert master["자치구_명"].notna().all() and master["경계_코드"].notna().all()
    assert master["SKT_코드"].isna().sum() == 1, "SKT에 없는 동은 항동 하나여야 한다"
    assert master["점포_202512_전체"].notna().all()
    assert len(quarter) == 1700 and not quarter.duplicated([K, Q]).any()
    assert quarter["지출_총금액"].notna().all()
    assert trade[K].notna().all() and trade["공통그룹"].notna().all()


def save(df, name):
    path = OUT / name
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  {name:<22} {len(df):>8,}행 × {df.shape[1]:>3}열  {path.stat().st_size / 2**20:5.1f}MB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"원천: {RAW}\n저장: {OUT}\n")
    cons = read("OA-22166_소비_행정동.csv")
    sales = read("상권/OA-15572_추정매출_상권.csv")
    mapping = build_mapping(sales)
    trade = build_trade(sales, mapping)
    master = build_master(cons)
    quarter = build_quarter(master, cons, trade)
    check(mapping, master, quarter, trade)

    save(mapping, "업종_공통그룹.csv")
    save(master, "행정동_마스터.csv")
    save(quarter, "행정동_분기.csv")
    save(trade, "상권_업종_분기.csv")
    out = master[master["소비_이상치"]]
    print(f"\n소비 이상치 동 {len(out)}곳: " + ", ".join(
        f"{n}({i} {s:.0f}%)" for n, i, s in zip(out["행정동_명"], out["소비_최대항목"], out["소비_최대항목_비중"])))


if __name__ == "__main__":
    main()
