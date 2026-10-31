"""data/raw 원천 데이터 기본 EDA.

data/raw 아래 모든 원천 데이터(행정동·자치구·상권 상권분석서비스, 생활데이터, 재현데이터,
국민연금 소득, 네이버 트렌드, 행정동 경계)를 읽어 구조·품질·분포·관계를 점검한다.
그래프는 이승희/eda_basic_figures/ 에, 요약표는 이승희/eda_basic_tables/ 에 저장한다.
보고서: 이승희/기본_EDA_보고서.md

실행: uv run --no-project --with pandas,matplotlib,openpyxl python 이승희/eda_raw_basic_2025.py   (저장소 루트에서)
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUT_DIR = Path(__file__).resolve().parent / "eda_basic_tables"
IMG_DIR = Path(__file__).resolve().parent / "eda_basic_figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)

sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

# ── 차트 스타일 (dataviz 기본 팔레트) ─────────────────────────────
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
plt.rcParams.update({
    "font.family": "Malgun Gothic", "axes.unicode_minus": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold",
    "axes.titlesize": 12, "figure.dpi": 110, "savefig.dpi": 130, "savefig.bbox": "tight",
})

QUARTERS = [20251, 20252, 20253, 20254]
Q_LABEL = {20251: "Q1", 20252: "Q2", 20253: "Q3", 20254: "Q4"}


def log_axis(ax, axis="x") -> None:
    """로그축 눈금을 mathtext(10^n) 대신 천단위 콤마 숫자로 표시."""
    from matplotlib.ticker import FuncFormatter
    getattr(ax, f"{axis}axis").set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else f"{v:g}"))


def read(rel: str) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / rel, encoding="utf-8-sig", low_memory=False)


def save(fig, name: str) -> None:
    fig.savefig(IMG_DIR / name)
    plt.close(fig)
    print(f"  [img] 이승희/eda_basic_figures/{name}")


def table(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT_DIR / name, encoding="utf-8-sig", index=False)
    print(f"  [csv] 이승희/eda_basic_tables/{name}")


def eok(x):  # 원 → 억원
    return x / 1e8


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ══════════════════════════════════════════════════════════════════
# 1. 데이터 인벤토리
# ══════════════════════════════════════════════════════════════════
section("1. 데이터 인벤토리")

D = {
    "영역_행정동": read("OA-22160_영역_행정동.csv"),
    "아파트_행정동": read("OA-22163_아파트_행정동.csv"),
    "아파트_자치구": read("OA-22164_아파트_자치구.csv"),
    "소비_행정동": read("OA-22166_소비_행정동.csv"),
    "소비_자치구": read("OA-22167_소비_자치구.csv"),
    "집객시설_행정동": read("OA-22169_집객시설_행정동.csv"),
    "길단위인구_행정동": read("OA-22178_길단위인구_행정동.csv"),
    "상주인구_자치구": read("OA-22182_상주인구_자치구.csv"),
    "상주인구_행정동": read("OA-22183_상주인구_행정동.csv"),
    "직장인구_행정동": read("OA-22184_직장인구_행정동.csv"),
    "영역_상권": read("상권/OA-15560_영역_상권.csv"),
    "길단위인구_상권": read("상권/OA-15568_길단위인구_상권.csv"),
    "직장인구_상권": read("상권/OA-15569_직장인구_상권.csv"),
    "추정매출_상권": read("상권/OA-15572_추정매출_상권.csv"),
    "상권변화지표_상권": read("상권/OA-15576_상권변화지표_상권.csv"),
    "점포_상권": read("상권/OA-15577_점포_상권.csv"),
    "집객시설_상권": read("상권/OA-15580_집객시설_상권.csv"),
    "상주인구_상권": read("상권/OA-15584_상주인구_상권.csv"),
    "국민연금_소득": read("국민연금_시군구_평균소득월액_2025.csv"),
    "재현_금융생활": read("bigdata_campus/seoul_lifestyle_금융생활_재현데이터_sample1000.csv"),
    "재현_소비이동": read("bigdata_campus/seoul_lifestyle_소비이동패턴_재현데이터_sample1000.csv"),
    "네이버_10개분야": read("naver_trend/naver_trend_10categories_monthly.csv"),
    "네이버_자치구TOP5": read("naver_trend/naver_trend_25gu_top5_monthly.csv"),
    "네이버_자치구특화": read("naver_trend/naver_trend_gu_targeted_monthly.csv"),
}
LIVING = {}
for kind in ["통신정보", "관심집단"]:
    for m in ["03", "06", "09", "12"]:
        df = pd.read_excel(RAW_DIR / "living" / f"{kind}_2025.{m}.xlsx").copy()
        LIVING[f"{kind}_2025.{m}"] = df.assign(기준월=f"2025-{m}")
D["생활_통신정보"] = pd.concat([v for k, v in LIVING.items() if k.startswith("통신")], ignore_index=True)
D["생활_관심집단"] = pd.concat([v for k, v in LIVING.items() if k.startswith("관심")], ignore_index=True)


def unit_key(df: pd.DataFrame) -> str:
    for k in ["상권_코드", "행정동_코드", "자치구_코드", "행정동코드", "시군구", "자치구명", "자치구"]:
        if k in df:
            return k
    return "-"


def period_of(df: pd.DataFrame) -> str:
    for k in ["기준_년분기_코드", "period", "기준년월", "기준월"]:
        if k in df:
            v = sorted(df[k].astype(str).unique())
            return f"{v[0]}~{v[-1]} ({len(v)})"
    return "-"


inv = []
for name, df in D.items():
    key = unit_key(df)
    inv.append({
        "데이터": name, "행수": len(df), "열수": df.shape[1], "기간(개수)": period_of(df),
        "키": key, "키_고유수": df[key].nunique() if key != "-" else np.nan,
        "결측셀_비율(%)": round(df.isna().to_numpy().mean() * 100, 2),
        "결측있는_열수": int((df.isna().sum() > 0).sum()),
        "완전중복행": int(df.duplicated().sum()),
    })
inv = pd.DataFrame(inv)
print(inv.to_string(index=False))
table(inv, "01_데이터_인벤토리.csv")

geo = json.loads((RAW_DIR / "geo" / "HangJeongDong_ver20251231.geojson").read_text(encoding="utf-8"))
geo_props = pd.DataFrame([f["properties"] for f in geo["features"]])
geo_seoul = geo_props[geo_props["sido"] == "11"].copy()
geo_seoul["행정동_코드"] = geo_seoul["adm_cd2"].str[:8].astype(int)
print(f"\nGeoJSON: 전국 {len(geo_props)}개 행정동, 서울 {len(geo_seoul)}개, 속성={list(geo_props.columns)}")

manifest = read("MANIFEST.csv")
missing_files = [f for f in manifest["파일"] if not (RAW_DIR / f).exists()]
print("MANIFEST에 있으나 실제 없는 파일:", missing_files)

# ══════════════════════════════════════════════════════════════════
# 2. 데이터 품질 점검
# ══════════════════════════════════════════════════════════════════
section("2. 데이터 품질 점검")

# 2-1. 결측 패턴
miss_rows = []
for name in ["아파트_행정동", "집객시설_행정동", "집객시설_상권", "재현_금융생활", "재현_소비이동"]:
    na = D[name].isna().mean()
    for col, r in na[na > 0].items():
        miss_rows.append({"데이터": name, "컬럼": col, "결측률(%)": round(r * 100, 1)})
miss = pd.DataFrame(miss_rows).sort_values(["데이터", "결측률(%)"], ascending=[True, False])
table(miss, "02_결측_컬럼.csv")
print(miss.groupby("데이터")["결측률(%)"].agg(["count", "min", "max"]))

# 집객시설: 결측 = 0개 인지 검증 (집객시설_수 = 하위 시설 합?)
fac = D["집객시설_행정동"]
fac_cols = [c for c in fac.columns if c.endswith("_수") and c != "집객시설_수"]
fac_sum = fac[fac_cols].fillna(0).sum(axis=1)
gap = fac["집객시설_수"] - fac_sum
print(f"집객시설_수 == 하위 19종 합(결측=0) 일치율: {(gap == 0).mean():.3f} / 집객시설_수 - 하위합: "
      f"min {gap.min():.0f}, 중앙값 {gap.median():.0f}, max {gap.max():.0f} → 집객시설_수는 하위 19종 외 시설도 포함")

fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
for ax, name in zip(axes, ["집객시설_행정동", "아파트_행정동"]):
    s = D[name].isna().mean().mul(100)
    s = s[s > 0].sort_values()
    ax.barh([c.replace("아파트_", "").replace("_세대_수", "") for c in s.index], s.values, color=C[0], height=0.7)
    for y, v in enumerate(s.values):
        ax.text(v + 1, y, f"{v:.0f}%", va="center", fontsize=8, color=INK2)
    ax.set_xlim(0, 112)
    ax.set_title(f"{name}: 컬럼별 결측률")
    ax.set_xlabel("결측률 (%)")
    ax.grid(axis="y", visible=False)
fig.suptitle("결측은 대부분 '해당 시설/세대 없음(0)'을 빈칸으로 둔 것", fontsize=11, color=INK2, y=0.995)
fig.tight_layout()
save(fig, "01_결측률_집객시설_아파트.png")

# 2-2. 키 커버리지 (행정동)
dong_master = set(D["영역_행정동"]["행정동_코드"])
cov = []
for name in ["아파트_행정동", "소비_행정동", "집객시설_행정동", "길단위인구_행정동", "상주인구_행정동", "직장인구_행정동"]:
    s = set(D[name]["행정동_코드"])
    cov.append({"데이터": name, "행정동수": len(s), "영역(425)에 없음": len(s - dong_master),
                "영역 대비 누락": len(dong_master - s),
                "누락_예시": ", ".join(D["영역_행정동"].set_index("행정동_코드").loc[sorted(dong_master - s), "행정동_명"].head(6))})
s = set(geo_seoul["행정동_코드"])
cov.append({"데이터": "GeoJSON(서울)", "행정동수": len(s), "영역(425)에 없음": len(s - dong_master),
            "영역 대비 누락": len(dong_master - s),
            "누락_예시": ", ".join(geo_seoul.loc[geo_seoul["행정동_코드"].isin(s - dong_master), "adm_nm"].str.split().str[-1])})
liv_codes = D["생활_통신정보"]["행정동코드"].unique()
cov.append({"데이터": "생활_통신정보(통계청 7자리 코드)", "행정동수": len(liv_codes), "영역(425)에 없음": np.nan,
            "영역 대비 누락": 425 - len(liv_codes), "누락_예시": "코드체계 다름 → GeoJSON adm_cd로 매핑 필요"})
cov = pd.DataFrame(cov)
print(cov.to_string(index=False))
table(cov, "03_행정동_키_커버리지.csv")

# GeoJSON adm_cd(7자리 앞) ↔ 생활데이터 행정동코드 매핑 가능 여부
geo_seoul["통계청7"] = geo_seoul["adm_cd"].str[:7].astype(int)
liv_match = np.isin(liv_codes, geo_seoul["통계청7"]).mean()
print(f"생활데이터 7자리 코드 → GeoJSON adm_cd 매칭률: {liv_match:.3f}")

# 2-3. 상권 키 커버리지
tr_master = set(D["영역_상권"]["상권_코드"])
tcov = []
for name in ["길단위인구_상권", "직장인구_상권", "추정매출_상권", "상권변화지표_상권", "점포_상권", "집객시설_상권", "상주인구_상권"]:
    df = D[name]
    per_q = df.groupby("기준_년분기_코드")["상권_코드"].nunique()
    tcov.append({"데이터": name, "상권수(전체)": df["상권_코드"].nunique(),
                 **{Q_LABEL[q]: per_q.get(q, 0) for q in QUARTERS},
                 "영역(1650) 대비 누락": len(tr_master - set(df["상권_코드"]))})
tcov = pd.DataFrame(tcov)
print(tcov.to_string(index=False))
table(tcov, "04_상권_키_커버리지.csv")

# 2-4. 집계 정합성: 행정동 합 vs 자치구
cons = D["소비_행정동"].assign(자치구_코드=lambda d: d["행정동_코드"] // 1000)
cons_gu = cons.groupby(["기준_년분기_코드", "자치구_코드"])["지출_총금액"].sum()
gu = D["소비_자치구"].set_index(["기준_년분기_코드", "행정동_코드"])["지출_총금액"]
gu.index.names = cons_gu.index.names
ratio = (cons_gu / gu).describe()
print(f"\n소비: 행정동 합 / 자치구 값 비율 → mean {ratio['mean']:.3f}, min {ratio['min']:.3f}, max {ratio['max']:.3f}")
pop = D["상주인구_행정동"].assign(자치구_코드=lambda d: d["행정동_코드"] // 1000)
pop_gu = pop.groupby(["기준_년분기_코드", "자치구_코드"])["총_상주인구_수"].sum()
pg = D["상주인구_자치구"].set_index(["기준_년분기_코드", "자치구_코드"])["총_상주인구_수"]
pr = (pop_gu / pg).describe()
print(f"상주인구: 행정동 합 / 자치구 값 비율 → mean {pr['mean']:.4f}, min {pr['min']:.4f}, max {pr['max']:.4f}")

# 소비 항목 합 = 지출_총금액 ?
cat_cols = [c for c in D["소비_행정동"].columns if c.endswith("_지출_총금액")]
cs = D["소비_행정동"][cat_cols].sum(axis=1)
print(f"소비 항목 10개 합 == 지출_총금액 일치율: {(cs == D['소비_행정동']['지출_총금액']).mean():.3f}")

# 추정매출 내부 정합성
sales = D["추정매출_상권"]
chk = {
    "주중+주말=당월": (sales["주중_매출_금액"] + sales["주말_매출_금액"] - sales["당월_매출_금액"]).abs().le(1).mean(),
    "남+여=당월": (sales["남성_매출_금액"] + sales["여성_매출_금액"] - sales["당월_매출_금액"]).abs().le(1).mean(),
    "연령합=당월": (sales.filter(regex=r"^연령대_.*_매출_금액$").sum(axis=1) - sales["당월_매출_금액"]).abs().le(1).mean(),
    "시간대합=당월": (sales.filter(regex=r"^시간대_.*_매출_금액$").sum(axis=1) - sales["당월_매출_금액"]).abs().le(1).mean(),
    "요일합=당월": (sales.filter(regex=r"^.요일_매출_금액$").sum(axis=1) - sales["당월_매출_금액"]).abs().le(1).mean(),
}
chk["연령합=성별합"] = (sales.filter(regex=r"^연령대_.*_매출_금액$").sum(axis=1)
                      - sales["남성_매출_금액"] - sales["여성_매출_금액"]).abs().le(1).mean()
for k, v in chk.items():
    print(f"추정매출 {k} 일치율(±1원): {v:.3f}")
g_cov = (sales["남성_매출_금액"].sum() + sales["여성_매출_금액"].sum()) / sales["당월_매출_금액"].sum()
print(f"성별 구분된 매출 / 전체 매출: {g_cov:.1%} → 나머지는 성별·연령 미상(법인카드 등으로 추정)")
print(f"추정매출 당월_매출_금액 ≤ 0 행: {(sales['당월_매출_금액'] <= 0).sum()}")
bad_cols = [c for c in sales.columns if "시간대_건수" in c]
print("추정매출 컬럼명 이상:", bad_cols)

# 이름 깨짐('?')
for name, col in [("영역_행정동", "행정동_명"), ("영역_상권", "상권_코드_명")]:
    q = D[name][D[name][col].str.contains(r"\?", regex=True)][col]
    print(f"{name}.{col} 에 '?' 포함: {len(q)}건 예) {list(q.head(5))}")

# 생활데이터 특이값
tel = D["생활_통신정보"]
neg_cols = [c for c in tel.select_dtypes("number").columns if (tel[c] < 0).any()]
print("생활_통신정보 음수 포함 컬럼:", neg_cols)
same_q = [b for b in [c for c in tel.columns if c.endswith("사용일수")]
          if all((tel[f"{b}: 4분위수, {p}%"] == tel[b]).all() for p in [25, 50, 75])]
print("평균=사분위수 모두 동일한 지표:", same_q)
print(f"생활데이터 행 구성: {tel.groupby('기준월').size().to_dict()} / 성별 {sorted(tel['성별'].unique())} / 연령대 {sorted(tel['연령대'].unique())}")

# ══════════════════════════════════════════════════════════════════
# 3. 행정동 단위
# ══════════════════════════════════════════════════════════════════
section("3. 행정동 단위 (소비·인구·시설)")

cons_y = D["소비_행정동"].groupby(["행정동_코드", "행정동_코드_명"])[["지출_총금액", *cat_cols]].sum().reset_index()
cons_y["자치구"] = cons_y["행정동_코드"].floordiv(1000).map(D["소비_자치구"].drop_duplicates("행정동_코드").set_index("행정동_코드")["행정동_코드_명"])
desc = eok(cons_y["지출_총금액"]).describe(percentiles=[.1, .25, .5, .75, .9, .99])
print("행정동 2025 연간 지출총액(억원):\n", desc.round(1).to_string())
top = cons_y.nlargest(15, "지출_총금액")[["자치구", "행정동_코드_명", "지출_총금액"]]
bottom = cons_y.nsmallest(8, "지출_총금액")[["자치구", "행정동_코드_명", "지출_총금액"]]
print("TOP15:\n", top.assign(억원=lambda d: eok(d["지출_총금액"]).round(0)).drop(columns="지출_총금액").to_string(index=False))
print("BOTTOM8:\n", bottom.assign(억원=lambda d: eok(d["지출_총금액"]).round(1)).drop(columns="지출_총금액").to_string(index=False))
table(cons_y.sort_values("지출_총금액", ascending=False), "05_행정동_연간소비_2025.csv")

fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), gridspec_kw={"width_ratios": [1, 1.1]})
ax = axes[0]
v = eok(cons_y["지출_총금액"])
bins = np.logspace(np.log10(v.min()), np.log10(v.max()), 40)
ax.hist(v, bins=bins, color=C[0], edgecolor=SURFACE, linewidth=1.5)
ax.set_xscale("log")
log_axis(ax)
ax.axvline(v.median(), color=INK2, ls="--", lw=1)
ax.text(v.median() * 1.08, ax.get_ylim()[1] * 0.92, f"중앙값 {v.median():,.0f}억", color=INK2, fontsize=9)
ax.set_title("행정동별 연간 지출총액 분포 (로그축)")
ax.set_xlabel("2025 연간 지출총액 (억원, log)")
ax.set_ylabel("행정동 수")
ax = axes[1]
t = top.iloc[::-1]
ax.barh(t["자치구"] + " " + t["행정동_코드_명"], eok(t["지출_총금액"]), color=C[0], height=0.7)
ax.set_title("연간 지출총액 상위 15개 행정동")
ax.set_xlabel("억원")
ax.grid(axis="y", visible=False)
fig.tight_layout()
save(fig, "02_행정동_소비총액_분포.png")

# 행정동별 항목 비중
dong_share = cons_y[cat_cols].div(cons_y["지출_총금액"], axis=0) * 100
dong_share.columns = dong_share.columns.str.replace("_지출_총금액", "")
top5_share = cons_y["지출_총금액"].nlargest(5).sum() / cons_y["지출_총금액"].sum()
print(f"지출 상위 5개 행정동이 서울 전체 지출의 {top5_share:.1%} 차지")
# 이상치: 연간 1조원 이상이면서 여가_문화 비중 80% 이상인 동 (온라인·플랫폼 결제가 가맹점 소재지에 집계된 것으로 추정)
outlier = cons_y.loc[(cons_y["지출_총금액"] >= 1e12) & (dong_share["여가_문화"] >= 80), "행정동_코드_명"].tolist()
out_mask = cons_y["행정동_코드_명"].isin(outlier)
print(f"여가_문화 쏠림 이상치 동: {outlier} → 전체 지출의 {cons_y.loc[out_mask, '지출_총금액'].sum() / cons_y['지출_총금액'].sum():.1%}")
print("이상치 동의 항목 비중(%):\n", dong_share[out_mask].set_axis(outlier).round(1).T.to_string())


def cat_share(df):
    s = df[cat_cols].sum() / df["지출_총금액"].sum() * 100
    s.index = s.index.str.replace("_지출_총금액", "")
    return s


share_ex = cat_share(cons_y[~out_mask]).sort_values()
share = cat_share(cons_y).reindex(share_ex.index)
print("서울 전체 소비 항목 비중(%) [전체 / 이상치 동 제외]:\n",
      pd.DataFrame({"전체": share, "이상치제외": share_ex}).sort_values("이상치제외", ascending=False).round(1).to_string())
print("행정동별 항목 비중 분포(%):\n", dong_share.describe().T[["mean", "std", "min", "50%", "max"]].round(1).to_string())

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
ax = axes[0]
yy = np.arange(len(share))
ax.barh(yy + 0.19, share.values, height=0.36, color=C[1], label="전체 425개 동")
ax.barh(yy - 0.19, share_ex.values, height=0.36, color=C[0], label=f"이상치 {len(outlier)}개 동 제외")
for y, (a, b) in enumerate(zip(share.values, share_ex.values)):
    ax.text(a + 0.6, y + 0.19, f"{a:.1f}%", va="center", fontsize=8, color=INK2)
    ax.text(b + 0.6, y - 0.19, f"{b:.1f}%", va="center", fontsize=8, color=INK2)
ax.set_yticks(yy, share.index)
ax.set_xlim(0, 72)
ax.set_title("서울 소비 항목 비중 (2025) — 이상치 동 포함/제외")
ax.set_xlabel("%")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", visible=False)
ax = axes[1]
order = share_ex.index
bp = ax.boxplot([dong_share[c] for c in order], orientation="horizontal", tick_labels=list(order), widths=0.55,
                patch_artist=True, flierprops=dict(marker="o", markersize=3, markerfacecolor=C[1], markeredgecolor="none", alpha=.6),
                medianprops=dict(color=INK, lw=1.5))
for b in bp["boxes"]:
    b.set(facecolor=BLUE_RAMP[1], edgecolor=C[0])
ax.set_title("행정동별 항목 비중의 편차")
ax.set_xlabel("행정동 내 비중 (%)")
ax.grid(axis="y", visible=False)
fig.tight_layout()
save(fig, "03_소비항목_비중.png")

# 인구·시설 패널 (2025 Q4 스냅샷 + 소비 연간)
q4 = 20254
panel = (D["영역_행정동"][["행정동_코드", "행정동_명", "영역_면적"]]
         .merge(cons_y[["행정동_코드", "지출_총금액"]], on="행정동_코드", how="left"))
for name, col, new in [("상주인구_행정동", "총_상주인구_수", "상주인구"), ("상주인구_행정동", "총_가구_수", "가구수"),
                       ("직장인구_행정동", "총_직장_인구_수", "직장인구"), ("길단위인구_행정동", "총_유동인구_수", "유동인구"),
                       ("집객시설_행정동", "집객시설_수", "집객시설수"), ("아파트_행정동", "아파트_단지_수", "아파트단지수"),
                       ("아파트_행정동", "아파트_평균_시가", "아파트평균시가")]:
    s = D[name].query("기준_년분기_코드 == @q4").set_index("행정동_코드")[col].rename(new)
    panel = panel.merge(s, left_on="행정동_코드", right_index=True, how="left")
panel = panel.rename(columns={"지출_총금액": "연간지출총액"})
panel["1인당지출(만원)"] = panel["연간지출총액"] / panel["상주인구"] / 1e4
table(panel, "06_행정동_지표패널_2025Q4.csv")
print("행정동 패널 기술통계:\n", panel.drop(columns=["행정동_코드", "행정동_명"]).describe().T.round(0).to_string())

fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
for ax, col, color in zip(axes, ["상주인구", "직장인구", "유동인구"], C[:3]):
    v = panel[col].dropna()
    v = v[v > 0]
    bins = np.logspace(np.log10(v.min()), np.log10(v.max()), 35)
    ax.hist(v, bins=bins, color=color, edgecolor=SURFACE, linewidth=1.2)
    ax.set_xscale("log")
    log_axis(ax)
    ax.set_title(f"{col} (중앙값 {v.median():,.0f}명)")
    ax.set_xlabel("명, log")
axes[0].set_ylabel("행정동 수")
fig.suptitle("행정동별 인구 분포 (2025 Q4) — 직장·유동인구는 꼬리가 훨씬 길다", fontsize=11, color=INK2)
fig.tight_layout()
save(fig, "04_행정동_인구분포.png")

corr_cols = ["연간지출총액", "상주인구", "가구수", "직장인구", "유동인구", "집객시설수", "아파트단지수", "아파트평균시가", "영역_면적"]
corr = panel[corr_cols].corr(method="spearman")
table(corr.round(3).reset_index(names="변수"), "07_행정동_지표_스피어만상관.csv")
print("지출총액과의 스피어만 상관:\n", corr["연간지출총액"].sort_values(ascending=False).round(2).to_string())

from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

div = LinearSegmentedColormap.from_list("div", ["#e34948", "#f0efec", "#2a78d6"])
fig, ax = plt.subplots(figsize=(8.4, 7))
im = ax.imshow(corr.values, cmap=div, vmin=-1, vmax=1)
ax.set_xticks(range(len(corr_cols)), corr_cols, rotation=45, ha="right")
ax.set_yticks(range(len(corr_cols)), corr_cols)
ax.grid(False)
for i in range(len(corr_cols)):
    for j in range(len(corr_cols)):
        ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=8,
                color="white" if abs(corr.values[i, j]) > 0.6 else INK)
fig.colorbar(im, ax=ax, shrink=0.8, label="Spearman ρ")
ax.set_title("행정동 지표 간 순위상관 (2025 Q4, 지출은 연간)")
fig.tight_layout()
save(fig, "05_행정동_지표_상관.png")

fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), sharey=True)
for ax, col, color in zip(axes, ["상주인구", "직장인구", "유동인구"], C[:3]):
    d = panel[[col, "연간지출총액"]].dropna()
    d = d[(d[col] > 0) & (d["연간지출총액"] > 0)]
    ax.scatter(d[col], eok(d["연간지출총액"]), s=12, color=color, alpha=.55, edgecolors="none")
    ax.set_xscale("log")
    log_axis(ax)
    ax.set_yscale("log")
    log_axis(ax, "y")
    ax.set_title(f"{col} vs 지출 (ρ={corr.loc[col, '연간지출총액']:.2f})")
    ax.set_xlabel(f"{col} (명, log)")
axes[0].set_ylabel("연간 지출총액 (억원, log)")
fig.tight_layout()
save(fig, "06_인구와_소비_산점도.png")

# ══════════════════════════════════════════════════════════════════
# 4. 분기 추이
# ══════════════════════════════════════════════════════════════════
section("4. 분기 추이 (2025 Q1~Q4)")
trend = pd.DataFrame({
    "소비(행정동 지출총액)": D["소비_행정동"].groupby("기준_년분기_코드")["지출_총금액"].sum(),
    "상권 추정매출": D["추정매출_상권"].groupby("기준_년분기_코드")["당월_매출_금액"].sum(),
    "유동인구": D["길단위인구_행정동"].groupby("기준_년분기_코드")["총_유동인구_수"].sum(),
    "상주인구": D["상주인구_행정동"].groupby("기준_년분기_코드")["총_상주인구_수"].sum(),
    "직장인구": D["직장인구_행정동"].groupby("기준_년분기_코드")["총_직장_인구_수"].sum(),
    "상권 점포수": D["점포_상권"].groupby("기준_년분기_코드")["전체_점포_수"].sum(),
})
idx = trend / trend.iloc[0] * 100
print("원값:\n", trend.to_string())
print("Q1=100 지수:\n", idx.round(1).to_string())
table(trend.reset_index().merge(idx.add_suffix("_지수(Q1=100)").reset_index()), "08_분기추이.csv")

fig, ax = plt.subplots(figsize=(9.5, 5))
x = [Q_LABEL[q] for q in idx.index]
for i, col in enumerate(idx.columns):
    ax.plot(x, idx[col], marker="o", ms=6, lw=2, color=C[i], label=col)
# 끝값 라벨: 값이 겹치는 계열은 한 줄로 묶어서 표시
end = idx.iloc[-1].round(1)
for val, cols in end.groupby(end).groups.items():
    names = "·".join(c.replace("(행정동 지출총액)", "") for c in cols)
    ax.annotate(f"{names} {val:.1f}", (3, val), xytext=(8, 0), textcoords="offset points", va="center", fontsize=8.5, color=INK2)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.set_xlim(-0.2, 4.4)
ax.set_title("서울 전체 지표의 분기 추이 (2025 Q1 = 100)")
ax.set_ylabel("지수")
ax.legend(loc="upper left", fontsize=8.5, frameon=False, ncol=2)
fig.tight_layout()
save(fig, "07_분기추이_지수.png")

# ══════════════════════════════════════════════════════════════════
# 5. 자치구 단위
# ══════════════════════════════════════════════════════════════════
section("5. 자치구 단위 (소비·소득·아파트)")
gu_c = D["소비_자치구"].groupby(["행정동_코드", "행정동_코드_명"])["지출_총금액"].sum().reset_index()
gu_c.columns = ["자치구_코드", "자치구", "연간지출총액"]
gu_p = D["상주인구_자치구"].query("기준_년분기_코드 == @q4")[["자치구_코드", "총_상주인구_수"]]
inc = D["국민연금_소득"]
inc = inc[inc["시군구"].str.startswith("서울특별시")].assign(자치구=lambda d: d["시군구"].str.replace("서울특별시", ""))
apt = D["아파트_자치구"].query("기준_년분기_코드 == @q4")[["자치구_코드", "아파트_평균_시가"]]
gu_t = gu_c.merge(gu_p, on="자치구_코드").merge(inc[["자치구", "평균소득월액"]], on="자치구", how="left").merge(apt, on="자치구_코드")
gu_t["1인당지출(만원)"] = gu_t["연간지출총액"] / gu_t["총_상주인구_수"] / 1e4
ex_gu = cons_y[~out_mask].groupby(cons_y["행정동_코드"] // 1000)["지출_총금액"].sum().rename("지출_이상치제외")
gu_t = gu_t.merge(ex_gu, left_on="자치구_코드", right_index=True)
PC = "1인당지출_이상치제외(만원)"
gu_t[PC] = gu_t["지출_이상치제외"] / gu_t["총_상주인구_수"] / 1e4
gu_t = gu_t.sort_values("연간지출총액", ascending=False)
print(gu_t.assign(지출억=lambda d: eok(d["연간지출총액"]).round(0)).drop(columns="연간지출총액").round(1).to_string(index=False))
print("자치구 간 스피어만 상관:\n", gu_t[["1인당지출(만원)", PC, "평균소득월액", "아파트_평균_시가", "총_상주인구_수"]].corr("spearman").round(2).to_string())
nat = D["국민연금_소득"]["평균소득월액"]
print(f"국민연금 평균소득월액: 전국 {len(nat)}개 시군구 중앙값 {nat.median():,.0f}원, 서울 25개 중앙값 {inc['평균소득월액'].median():,.0f}원")
table(gu_t, "09_자치구_소비_소득_2025.csv")

fig, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1, 1.15]})
ax = axes[0]
g = gu_t.sort_values(PC)
ax.barh(g["자치구"], g[PC], color=C[0], height=0.7)
ax.set_title(f"자치구별 상주인구 1인당 연간 지출 (이상치 {len(outlier)}개 동 제외)")
ax.set_xlabel("만원 / 인")
ax.grid(axis="y", visible=False)
ax = axes[1]
ax.scatter(gu_t["평균소득월액"] / 1e4, gu_t[PC], s=40, color=C[0], edgecolors=SURFACE, linewidths=1.5)
# 하위 군집은 라벨이 겹치므로 1인당 지출 상위 8개 + 소득 최저 2개 구만 직접 라벨
lab_gu = set(gu_t.nlargest(8, PC)["자치구"]) | set(gu_t.nsmallest(2, "평균소득월액")["자치구"])
for _, r in gu_t[gu_t["자치구"].isin(lab_gu)].iterrows():
    ax.annotate(r["자치구"], (r["평균소득월액"] / 1e4, r[PC]), xytext=(4, 3), textcoords="offset points", fontsize=8, color=INK2)
rho = gu_t[["평균소득월액", PC]].corr("spearman").iloc[0, 1]
ax.set_title(f"국민연금 평균소득월액 vs 1인당 지출 (ρ={rho:.2f})")
ax.set_xlabel("평균소득월액 (만원, 2025-12)")
ax.set_ylabel("1인당 연간 지출 (만원)")
fig.tight_layout()
save(fig, "08_자치구_1인당소비_소득.png")

# ══════════════════════════════════════════════════════════════════
# 6. 상권 단위
# ══════════════════════════════════════════════════════════════════
section("6. 상권 단위 (영역·매출·점포·변화지표)")
area = D["영역_상권"]
print("상권 구분별 개수:\n", area["상권_구분_코드_명"].value_counts().to_string())
print("상권 면적(㎡) 구분별 중앙값:\n", area.groupby("상권_구분_코드_명")["영역_면적"].median().to_string())

sales["대분류"] = sales["서비스_업종_코드"].str[:4].map({"CS10": "외식업", "CS20": "서비스업", "CS30": "소매업"})
tr_y = sales.groupby(["상권_코드", "상권_코드_명", "상권_구분_코드_명"])["당월_매출_금액"].sum().reset_index(name="연간매출")
print("상권별 연간매출(억원) 분포:\n", eok(tr_y["연간매출"]).describe(percentiles=[.1, .5, .9, .99]).round(1).to_string())
print("상권 구분별 상권당 연간매출 중앙값(억원):\n", tr_y.groupby("상권_구분_코드_명")["연간매출"].median().pipe(eok).round(1).to_string())
top_share = tr_y["연간매출"].nlargest(int(len(tr_y) * 0.1)).sum() / tr_y["연간매출"].sum()
print(f"상위 10% 상권 매출 점유율: {top_share:.1%}")
print("매출 상위 10 상권:\n", tr_y.nlargest(10, "연간매출").assign(억원=lambda d: eok(d["연간매출"]).round(0)).drop(columns=["상권_코드", "연간매출"]).to_string(index=False))
table(tr_y.sort_values("연간매출", ascending=False), "10_상권별_연간매출_2025.csv")

gb = sales.groupby("상권_구분_코드_명")["당월_매출_금액"].sum()
cnt = area["상권_구분_코드_명"].value_counts()
kind_t = pd.DataFrame({"상권수": cnt, "상권수_비중(%)": cnt / cnt.sum() * 100, "매출_비중(%)": gb / gb.sum() * 100}).round(1)
print(kind_t.to_string())

fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
ax = axes[0]
kinds = kind_t.sort_values("매출_비중(%)").index
yy = np.arange(len(kinds))
ax.barh(yy + 0.19, kind_t.loc[kinds, "상권수_비중(%)"], height=0.36, color=C[0], label="상권 수 비중")
ax.barh(yy - 0.19, kind_t.loc[kinds, "매출_비중(%)"], height=0.36, color=C[1], label="매출 비중")
for y, k in enumerate(kinds):
    ax.text(kind_t.loc[k, "상권수_비중(%)"] + 1, y + 0.19, f"{kind_t.loc[k, '상권수_비중(%)']:.0f}%", va="center", fontsize=8.5, color=INK2)
    ax.text(kind_t.loc[k, "매출_비중(%)"] + 1, y - 0.19, f"{kind_t.loc[k, '매출_비중(%)']:.0f}%", va="center", fontsize=8.5, color=INK2)
ax.set_yticks(yy, kinds)
ax.set_title("상권 구분별 개수 비중 vs 매출 비중")
ax.set_xlabel("%")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", visible=False)
ax = axes[1]
v = eok(tr_y["연간매출"])
v = v[v > 0]
bins = np.logspace(np.log10(v.min()), np.log10(v.max()), 40)
ax.hist(v, bins=bins, color=C[0], edgecolor=SURFACE, linewidth=1.2)
ax.set_xscale("log")
log_axis(ax)
ax.axvline(v.median(), color=INK2, ls="--", lw=1)
ax.text(v.median() * 1.1, ax.get_ylim()[1] * 0.92, f"중앙값 {v.median():,.0f}억", color=INK2, fontsize=9)
ax.set_title(f"상권별 연간 추정매출 분포 (상위 10% 상권이 {top_share:.0%} 차지)")
ax.set_xlabel("억원, log")
ax.set_ylabel("상권 수")
fig.tight_layout()
save(fig, "09_상권구분_매출분포.png")

ind = sales.groupby(["서비스_업종_코드_명", "대분류"]).agg(매출=("당월_매출_금액", "sum"), 건수=("당월_매출_건수", "sum")).reset_index()
ind["객단가(원)"] = ind["매출"] / ind["건수"]
ind["매출비중(%)"] = ind["매출"] / ind["매출"].sum() * 100
ind = ind.sort_values("매출", ascending=False)
print("대분류 매출 비중(%):\n", (sales.groupby("대분류")["당월_매출_금액"].sum() / sales["당월_매출_금액"].sum() * 100).round(1).to_string())
print("업종 매출 TOP15:\n", ind.head(15).round({"매출비중(%)": 1, "객단가(원)": 0}).drop(columns=["매출", "건수"]).to_string(index=False))
table(ind, "11_업종별_매출_2025.csv")

CAT3 = {"외식업": C[0], "서비스업": C[1], "소매업": C[2]}
fig, ax = plt.subplots(figsize=(10, 7))
t = ind.head(20).iloc[::-1]
ax.barh(t["서비스_업종_코드_명"], eok(t["매출"]) / 1e4, color=[CAT3[k] for k in t["대분류"]], height=0.72)
for y, (_, r) in enumerate(t.iterrows()):
    ax.text(eok(r["매출"]) / 1e4 + 0.05, y, f"{r['매출비중(%)']:.1f}%", va="center", fontsize=8.5, color=INK2)
from matplotlib.patches import Patch  # noqa: E402

ax.legend(handles=[Patch(color=c, label=k) for k, c in CAT3.items()], frameon=False, loc="lower right")
ax.set_title("업종별 연간 추정매출 상위 20 (2025, 라벨=전체 매출 대비 비중)")
ax.set_xlabel("조원")
ax.grid(axis="y", visible=False)
fig.tight_layout()
save(fig, "10_업종별_매출_TOP20.png")

# 요일·시간대·성별·연령
day_cols = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
day = pd.Series({d[0]: sales[f"{d}_매출_금액"].sum() for d in day_cols})
day = day / day.sum() * 100
tcols = [c for c in sales.columns if c.startswith("시간대_") and c.endswith("_매출_금액")]
tod = sales[tcols].sum()
tod.index = [c.split("_")[1] for c in tcols]
tod = tod / tod.sum() * 100
age_cols = [c for c in sales.columns if c.startswith("연령대_") and c.endswith("_매출_금액")]
age = sales[age_cols].sum()
age.index = [c.split("_")[1] + ("+" if "이상" in c else "대") for c in age_cols]
age = age / age.sum() * 100
male = sales["남성_매출_금액"].sum() / (sales["남성_매출_금액"].sum() + sales["여성_매출_금액"].sum()) * 100
wk = sales["주말_매출_금액"].sum() / sales["당월_매출_금액"].sum() * 100
print("요일 비중(%):", day.round(1).to_dict())
print("시간대 비중(%):", tod.round(1).to_dict())
print("연령 비중(%):", age.round(1).to_dict())
print(f"남성 매출 비중 {male:.1f}%, 주말 매출 비중 {wk:.1f}% (주말=2/7 일 → 균등 시 28.6%)")
by_kind_wk = sales.groupby("대분류")[["주말_매출_금액", "당월_매출_금액"]].sum()
print("대분류별 주말 비중(%):", (by_kind_wk["주말_매출_금액"] / by_kind_wk["당월_매출_금액"] * 100).round(1).to_dict())

fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
for ax, s, title in zip(axes, [day, tod, age], ["요일별 매출 비중", "시간대별 매출 비중", "연령대별 매출 비중"]):
    ax.bar(s.index, s.values, color=C[0], width=0.68)
    for xx, val in enumerate(s.values):
        ax.text(xx, val + 0.4, f"{val:.1f}", ha="center", fontsize=8.5, color=INK2)
    ax.set_title(title)
    ax.set_ylabel("%")
    ax.grid(axis="x", visible=False)
axes[0].axhline(100 / 7, color=INK2, ls=":", lw=1)
axes[0].text(6.4, 100 / 7 + 0.3, "균등", fontsize=8, color=INK2, ha="right")
fig.suptitle(f"상권 추정매출 구성 (2025 전체) — 남성 {male:.0f}% / 여성 {100 - male:.0f}%", fontsize=11, color=INK2)
fig.tight_layout()
save(fig, "11_매출_요일_시간대_연령.png")

# 상권변화지표
chg = D["상권변화지표_상권"]
print("상권변화지표 코드-명:", chg.drop_duplicates("상권_변화_지표").set_index("상권_변화_지표")["상권_변화_지표_명"].to_dict())
chg4 = chg.query("기준_년분기_코드 == @q4")
ct = pd.crosstab(chg4["상권_구분_코드_명"], chg4["상권_변화_지표_명"], normalize="index") * 100
print("구분별 변화지표 비중(%, Q4):\n", ct.round(1).to_string())
trans = chg.pivot_table(index="상권_코드", columns="기준_년분기_코드", values="상권_변화_지표", aggfunc="first")
stay = (trans[20251] == trans[20254]).mean()
print(f"Q1→Q4 변화지표 유지율: {stay:.1%}")
print("운영/폐업 영업개월 평균(서울):", chg4[["서울_운영_영업_개월_평균", "서울_폐업_영업_개월_평균"]].iloc[0].to_dict())

order_ = [c for c in ["다이나믹", "상권확장", "상권축소", "정체"] if c in ct.columns]
fig, ax = plt.subplots(figsize=(10, 3.8))
left = np.zeros(len(ct))
for i, c in enumerate(order_):
    ax.barh(ct.index, ct[c], left=left, color=C[i], height=0.6, label=c, edgecolor=SURFACE, linewidth=2)
    for y, (l, w) in enumerate(zip(left, ct[c])):
        if w >= 6:
            ax.text(l + w / 2, y, f"{w:.0f}%", ha="center", va="center", fontsize=8.5, color="white")
    left += ct[c].values
ax.set_xlim(0, 100)
ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.15))
ax.set_title("상권 구분별 상권변화지표 구성 (2025 Q4)")
ax.grid(False)
fig.tight_layout()
save(fig, "12_상권변화지표.png")

# 점포 개·폐업
st = D["점포_상권"]
st4 = st.query("기준_년분기_코드 == @q4")
st_ind = st4.groupby("서비스_업종_코드_명")[["전체_점포_수", "프랜차이즈_점포_수"]].sum()
st_y = st.groupby("서비스_업종_코드_명")[["개업_점포_수", "폐업_점포_수"]].sum()
st_ind = st_ind.join(st_y)
avg_stock = st.groupby("서비스_업종_코드_명")["전체_점포_수"].sum() / 4
st_ind["연간개업률(%)"] = st_ind["개업_점포_수"] / avg_stock * 100
st_ind["연간폐업률(%)"] = st_ind["폐업_점포_수"] / avg_stock * 100
st_ind["순증률(%p)"] = st_ind["연간개업률(%)"] - st_ind["연간폐업률(%)"]
st_ind["프랜차이즈비중(%)"] = st_ind["프랜차이즈_점포_수"] / st_ind["전체_점포_수"] * 100
st_ind = st_ind.sort_values("전체_점포_수", ascending=False).reset_index()
tot_open = st["개업_점포_수"].sum() / (st["전체_점포_수"].sum() / 4) * 100
tot_close = st["폐업_점포_수"].sum() / (st["전체_점포_수"].sum() / 4) * 100
print(f"상권 점포 Q4 {st4['전체_점포_수'].sum():,}개, 연간 개업률 {tot_open:.1f}%, 폐업률 {tot_close:.1f}%")
print("점포 수 상위 15 업종:\n", st_ind.head(15).drop(columns=["프랜차이즈_점포_수", "개업_점포_수", "폐업_점포_수"]).round(1).to_string(index=False))
table(st_ind, "12_업종별_점포_개폐업_2025.csv")

fig, ax = plt.subplots(figsize=(10, 7.5))
t = st_ind.head(20).iloc[::-1].reset_index(drop=True)
for y, r in t.iterrows():
    ax.plot([r["연간폐업률(%)"], r["연간개업률(%)"]], [y, y], color=GRID, lw=2.5, zorder=1)
ax.scatter(t["연간개업률(%)"], t.index, s=55, color=C[0], label="연간 개업률", zorder=2, edgecolors=SURFACE, linewidths=1.5)
ax.scatter(t["연간폐업률(%)"], t.index, s=55, color=C[1], label="연간 폐업률", zorder=2, edgecolors=SURFACE, linewidths=1.5)
ax.set_yticks(t.index, [f"{n} ({s:,})" for n, s in zip(t["서비스_업종_코드_명"], t["전체_점포_수"])])
ax.set_xlabel("% (분기 개·폐업 점포 합 / 연평균 점포 수)")
ax.set_title("점포 수 상위 20개 업종의 개업률·폐업률 (2025, 괄호=Q4 점포 수)")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", visible=False)
fig.tight_layout()
save(fig, "13_업종별_개폐업률.png")

# ══════════════════════════════════════════════════════════════════
# 7. 생활데이터 (서울시 × SKT)
# ══════════════════════════════════════════════════════════════════
section("7. 생활데이터 (통신정보·관심집단)")
tel12 = tel.query("기준월 == '2025-12'")
age_t = tel12.groupby("연령대").agg(총인구=("총인구수", "sum"), 일인가구=("1인가구수", "sum"))
age_t["1인가구비율(%)"] = age_t["일인가구"] / age_t["총인구"] * 100
w = tel12["총인구수"]
metrics = ["배달 서비스 사용일수", "쇼핑 서비스 사용일수", "금융 서비스 사용일수", "평일 총 이동 횟수", "휴일 총 이동 횟수 평균",
           "평균 출근 소요시간 평균", "데이터 사용량", "최근 3개월 내 요금 연체 비율"]
age_m = tel12.groupby("연령대").apply(lambda g: pd.Series({m: np.average(g[m], weights=g["총인구수"]) for m in metrics}), include_groups=False)
print("연령대별 인구·1인가구(2025-12):\n", age_t.round(1).to_string())
print("연령대별 주요 지표(인구가중):\n", age_m.round(1).to_string())
print(f"생활데이터 총인구(2025-12) 합: {w.sum():,.0f} — 20세 이상 집계")
table(age_t.join(age_m).round(2).reset_index(), "13_생활데이터_연령대별_2025-12.csv")
stab = tel.groupby("기준월")["총인구수"].sum()
print("기준월별 총인구 합:", stab.round(0).to_dict())

dong_liv = tel12.groupby(["행정동코드", "자치구", "행정동"]).apply(
    lambda g: pd.Series({"총인구": g["총인구수"].sum(), "1인가구비율(%)": g["1인가구수"].sum() / g["총인구수"].sum() * 100,
                         "배달사용일수": np.average(g["배달 서비스 사용일수"], weights=g["총인구수"])}), include_groups=False).reset_index()
print("행정동 1인가구비율 분포:\n", dong_liv["1인가구비율(%)"].describe().round(1).to_string())
print("1인가구비율 상위 8 행정동:\n", dong_liv.nlargest(8, "1인가구비율(%)").round(1).to_string(index=False))
print(f"행정동 1인가구비율 vs 배달사용일수 스피어만: {dong_liv[['1인가구비율(%)', '배달사용일수']].corr('spearman').iloc[0, 1]:.2f}")

fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
lab = [str(a) for a in age_t.index]
ax = axes[0]
ax.bar(lab, age_t["1인가구비율(%)"], color=C[0], width=0.7)
ax.set_title("연령대별 1인가구 비율")
ax.set_ylabel("%")
ax.set_xlabel("연령대(5세 단위 시작연령)")
ax.grid(axis="x", visible=False)
ax = axes[1]
ax.plot(lab, age_m["배달 서비스 사용일수"], marker="o", lw=2, color=C[0], label="배달")
ax.plot(lab, age_m["금융 서비스 사용일수"] / 10, marker="o", lw=2, color=C[1], label="금융 (÷10)")
ax.plot(lab, age_m["쇼핑 서비스 사용일수"] / 10, marker="o", lw=2, color=C[2], label="쇼핑 (÷10)")
ax.set_title("연령대별 앱 서비스 사용일수 (인구가중)")
ax.set_xlabel("연령대")
ax.legend(frameon=False, fontsize=8.5)
ax = axes[2]
ax.scatter(dong_liv["1인가구비율(%)"], dong_liv["배달사용일수"], s=12, color=C[0], alpha=.6, edgecolors="none")
rr = dong_liv[["1인가구비율(%)", "배달사용일수"]].corr("spearman").iloc[0, 1]
ax.set_title(f"행정동 1인가구 비율 vs 배달 사용일수 (ρ={rr:.2f})")
ax.set_xlabel("1인가구 비율 (%)")
ax.set_ylabel("배달 서비스 사용일수")
fig.tight_layout()
save(fig, "14_생활데이터_연령_1인가구.png")

grp = D["생활_관심집단"].query("기준월 == '2025-12'")
gcols = [c for c in grp.columns if "집단" in c]
gshare = (grp[gcols].sum() / grp["총인구"].sum() * 100).sort_values(ascending=False)
print("관심집단 인구 비중(%, 2025-12):\n", gshare.round(1).to_string())

# ══════════════════════════════════════════════════════════════════
# 8. 재현데이터 (빅데이터캠퍼스 sample 1,000)
# ══════════════════════════════════════════════════════════════════
section("8. 재현데이터 (금융생활·소비이동패턴)")
for name in ["재현_금융생활", "재현_소비이동"]:
    df = D[name]
    birth = pd.to_numeric(df["생년월일"].astype(str).str[:4], errors="coerce")
    print(f"[{name}] 생년월일 예: {df['생년월일'].head(3).tolist()} → 출생연도 범위 {birth.min()}~{birth.max()}")
    print("  성별:", df["성별"].value_counts().to_dict(), "| 직업군:", df["직업군"].value_counts().head(6).to_dict())
    print("  자치구 표본수 min/max:", df["자치구명"].value_counts().agg(["min", "max"]).to_dict())
    print(df[["추정연소득", "총자산평가금액", "카드소비금액"]].describe().round(0).to_string())
fin = D["재현_금융생활"].copy()
fin["연령"] = 2025 - pd.to_numeric(fin["생년월일"].astype(str).str[:4], errors="coerce")
fin["연령대"] = (fin["연령"] // 10 * 10).clip(upper=70)
mv = D["재현_소비이동"]
share_cols = [c for c in mv.columns if c.startswith("가맹점분류_이용비중")]
print("소비이동 가맹점분류_이용비중 합 분포:", mv[share_cols].sum(axis=1).describe().round(2).to_dict())
print("소비이동 결측 33개 컬럼 공통 결측 여부(이동/통신 블록):", mv[["평일_이동_총횟수", "평균_통화량"]].isna().all(axis=1).mean().round(3))

fig, axes = plt.subplots(1, 3, figsize=(15, 4.3))
ax = axes[0]
v = fin["추정연소득"].dropna()
ax.hist(v / 1e4 if v.median() > 1e5 else v, bins=40, color=C[0], edgecolor=SURFACE, linewidth=1.2)
ax.set_title(f"추정연소득 분포 (중앙값 {v.median():,.0f})")
ax.set_xlabel("추정연소득 (원자료 값, 단위 미기재 — 천원 추정)")
ax.set_ylabel("인원")
ax = axes[1]
v = fin["카드소비금액"].dropna()
v = v[v > 0]
ax.hist(v, bins=np.logspace(np.log10(v.min()), np.log10(v.max()), 40), color=C[1], edgecolor=SURFACE, linewidth=1.2)
ax.set_xscale("log")
log_axis(ax)
ax.set_title(f"카드소비금액 분포 (0 값 {int((fin['카드소비금액'] == 0).sum())}명 제외)")
ax.set_xlabel("원자료 값 (단위 미기재), log")
ax = axes[2]
ag = fin.groupby("연령대")[["추정연소득", "카드소비금액"]].median()
ag = ag / ag.max() * 100
ax.plot(ag.index.astype(int).astype(str), ag["추정연소득"], marker="o", lw=2, color=C[0], label="추정연소득 중앙값")
ax.plot(ag.index.astype(int).astype(str), ag["카드소비금액"], marker="o", lw=2, color=C[1], label="카드소비 중앙값")
ax.set_title("연령대별 소득·카드소비 (각 최대=100)")
ax.set_xlabel("연령대 (70=70세 이상)")
ax.legend(frameon=False, fontsize=8.5)
fig.tight_layout()
save(fig, "15_재현데이터_소득_소비.png")

# ══════════════════════════════════════════════════════════════════
# 9. 네이버 검색 트렌드
# ══════════════════════════════════════════════════════════════════
section("9. 네이버 검색 트렌드 (2025 월별)")
nv = D["네이버_10개분야"].set_index("period")
print("10개 분야 연평균 검색지수:\n", nv.mean().sort_values(ascending=False).round(1).to_string())
print("변동계수(CV):\n", (nv.std() / nv.mean()).sort_values(ascending=False).round(2).to_string())
nt = D["네이버_자치구TOP5"]
kw = nt.groupby(["자치구", "키워드"])["검색지수"].mean().reset_index()
print("자치구별 키워드 평균 검색지수 최고:\n", kw.loc[kw.groupby("자치구")["검색지수"].idxmax()].round(1).to_string(index=False))
print("네이버 자치구 TOP5 그룹 내 최대값=100 여부:", (nt.groupby("자치구")["검색지수"].max().round(3) == 100).mean())
# 키워드 유형 분류(단순 키워드 매칭)
rules = {"맛집/카페/술집": "맛집|카페|술집|브런치|이자카야|빵집|포장마차|곱창|떡볶이|파전|순대|회센터|라운지",
         "병원": "병원|의료원|피부과", "쇼핑": "백화점|아울렛|몰|쇼핑|코스트코|이마트|시장|타임스퀘어|디큐브|엔터식스|팝업",
         "학원/교육": "학원|어학원|스터디"}
kw_u = pd.Series(nt["키워드"].unique())
kw_type = kw_u.apply(lambda k: next((t for t, p in rules.items() if pd.Series([k]).str.contains(p).iloc[0]), "명소/여가"))
print("125개 키워드 유형:", kw_type.value_counts().to_dict())

cats = nv.mean().sort_values(ascending=False).index
fig, axes = plt.subplots(2, 5, figsize=(16, 5.6), sharex=True)
months = [p[5:7] for p in nv.index]
for ax, c in zip(axes.flat, cats):
    ax.plot(months, nv[c], lw=2, color=C[0])
    ax.fill_between(months, nv[c], alpha=0.08, color=C[0])
    ax.set_title(c.replace("_검색지수", ""), fontsize=10)
    ax.set_ylim(0, max(nv[c].max() * 1.15, 10))
    ax.tick_params(labelsize=7.5)
    ax.set_xticks(months[::2])
fig.suptitle("소비 10개 분야 네이버 검색지수 월별 추이 (2025, 분야별 y축 다름)", fontsize=12)
fig.supxlabel("월", fontsize=9, color=INK2)
fig.tight_layout()
save(fig, "16_네이버_분야별_검색추이.png")

print("\n완료.")
