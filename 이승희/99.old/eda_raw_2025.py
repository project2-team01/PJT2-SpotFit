"""SpotFit 기본 EDA: 창업 성향 MBTI 대시보드를 위한 데이터 점검 (2025년 원천 데이터)

대시보드 흐름(창업자 검사 → 3글자 유형 → 같은 유형 상권 추천 + 소비 잠재력 + 업종 정보)에 맞춰
상권 3축 지표(L/V, E/P, S/G)를 만들 수 있는지, 8유형이 고르게 나뉘는지, 솔루션 재료가 있는지 살핀다.
그래프는 이승희/eda_figures/ 에, 요약표는 이승희/eda_tables/ 에 저장한다. 보고서: 이승희/SpotFit_EDA_보고서.md (0~9장)

실행: uv run --no-project --with pandas,matplotlib,openpyxl,scikit-learn python 이승희/eda_raw_2025.py   (저장소 루트에서)
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
TRADE_DIR = RAW_DIR / "상권"
TABLE_DIR = Path(__file__).resolve().parent / "eda_tables"
IMAGES_DIR = Path(__file__).resolve().parent / "eda_figures"

# 색상: 계열 1개는 파랑 하나, 강조는 주황, 배경은 회색. 크기(진하기)는 파랑 한 계열.
BLUE, ORANGE = "#2a78d6", "#eb6834"
GRAY, LIGHT_GRAY = "#c3c2b7", "#e6e5e0"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
DIV_CMAP = LinearSegmentedColormap.from_list("div", [ORANGE, "#f0efec", BLUE])

TRADE_TYPES = ["골목상권", "발달상권", "전통시장", "관광특구"]
MBTI_ORDER = ["LES", "LEG", "LPS", "LPG", "VES", "VEG", "VPS", "VPG"]
MBTI_NAME = {"LES": "동네 단골형", "LEG": "생활 성장형", "LPS": "동네 취향형", "LPG": "취향 확장형",
             "VES": "실속 유동형", "VEG": "유동 성장형", "VPS": "목적 방문형", "VPG": "트렌드 성장형"}
# 금융_MBTI.md 의 추천 창업 아이템을 상권분석서비스 업종 이름에 대응시킨 후보 업종
CANDIDATE_BIZ = ["반찬가게", "세탁소", "한식음식점", "슈퍼마켓", "제과점", "커피-음료", "분식전문점",
                 "패스트푸드점", "양식음식점", "일식음식점", "호프-간이주점", "화장품"]
# 소비 데이터에서 결제 주소 효과로 값이 비정상적으로 큰 동 (여가·문화 결제가 몰림)
OUTLIER_DONG = ["소공동", "구로3동", "문래동", "역삼1동"]


def setup_style():
    plt.rcParams.update({
        "font.family": "Malgun Gothic",
        "axes.unicode_minus": False,
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK2,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK,
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "legend.frameon": False,
    })


def read(path):
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    for col in ("행정동_코드_명", "상권_코드_명"):
        if col in df:
            # 원본에서 가운뎃점(·)이 ?로 들어간 이름을 바로잡는다 (예: 종로1?2?3?4가동)
            df[col] = df[col].str.replace("?", "·", regex=False)
    return df


def save(fig, name):
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMAGES_DIR / name)
    plt.close(fig)
    print("그림 저장:", f"이승희/eda_figures/{name}")


def save_table(df, name):
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLE_DIR / name, encoding="utf-8-sig")
    print("표 저장:", f"이승희/eda_tables/{name}")


def caption(fig, text, y=-0.035):
    fig.text(0.01, y, text, ha="left", va="top", fontsize=9, color=INK2)


def pct_rank(s):
    """0~100 백분위 순위. 값 크기 대신 순서만 쓰므로 극단값에 흔들리지 않는다."""
    return s.rank(pct=True) * 100


def bar_labels(ax, values, fmt="{:.1f}", horizontal=False, pad=0.0):
    for i, v in enumerate(values):
        if horizontal:
            ax.text(v + pad, i, fmt.format(v), va="center", fontsize=8.5, color=INK2)
        else:
            ax.text(i, v + pad, fmt.format(v), ha="center", fontsize=8.5, color=INK2)


# ================================================================ 데이터 읽기

def load_trade():
    """상권 단위 원천 데이터를 읽는다."""
    return {
        "area": read(TRADE_DIR / "OA-15560_영역_상권.csv"),
        "resident": read(TRADE_DIR / "OA-15584_상주인구_상권.csv"),
        "worker": read(TRADE_DIR / "OA-15569_직장인구_상권.csv"),
        "flow": read(TRADE_DIR / "OA-15568_길단위인구_상권.csv"),
        "sales": read(TRADE_DIR / "OA-15572_추정매출_상권.csv"),
        "stores": read(TRADE_DIR / "OA-15577_점포_상권.csv"),
        "change": read(TRADE_DIR / "OA-15576_상권변화지표_상권.csv"),
    }


# ================================================================ 0. 데이터 준비도

def table_readiness(t):
    area = t["area"]
    rows = {
        "상권 수 (영역)": area["상권_코드"].nunique(),
        "상주인구가 있는 상권": t["resident"]["상권_코드"].nunique(),
        "직장인구가 있는 상권": t["worker"]["상권_코드"].nunique(),
        "유동인구가 있는 상권": t["flow"]["상권_코드"].nunique(),
        "2025년 1분기 매출이 있는 상권": t["sales"].query("기준_년분기_코드 == 20251")["상권_코드"].nunique(),
        "2025년 4분기 매출이 있는 상권": t["sales"].query("기준_년분기_코드 == 20254")["상권_코드"].nunique(),
        "점포 정보가 있는 상권": t["stores"]["상권_코드"].nunique(),
        "상권이 하나라도 있는 행정동 (전체 425)": area["행정동_코드"].nunique(),
    }
    static = {}
    for key, col in [("resident", "총_상주인구_수"), ("worker", "총_직장_인구_수"), ("flow", "총_유동인구_수")]:
        static[key] = (t[key].groupby("상권_코드")[col].nunique() == 1).mean() * 100
    s = pd.Series(rows, name="개수").to_frame()
    save_table(s, "00_상권데이터_준비도.csv")
    return s, static


# ================================================================ 1. 상권 3축 지표

def build_axes(t):
    """상권마다 L/V, E/P, S/G 점수(0~100)를 만든다. 중앙값보다 크면 V, P, G 쪽."""
    area = t["area"].set_index("상권_코드")
    d = area[["상권_코드_명", "상권_구분_코드_명", "자치구_코드_명", "행정동_코드", "행정동_코드_명", "엑스좌표_값", "와이좌표_값"]].copy()

    # L/V: 사는 사람 대비 일하는 사람·지나가는 사람이 얼마나 많은가 (상주·직장인구는 분기마다 같아 4분기 값 사용)
    res = t["resident"].query("기준_년분기_코드 == 20254").set_index("상권_코드")["총_상주인구_수"]
    wrk = t["worker"].query("기준_년분기_코드 == 20254").set_index("상권_코드")["총_직장_인구_수"]
    flw = t["flow"].groupby("상권_코드")["총_유동인구_수"].mean()
    d["상주인구"], d["직장인구"], d["유동인구_분기평균"] = res, wrk, flw
    d["직장_상주_배율"] = d["직장인구"] / d["상주인구"]
    d["유동_상주_배율"] = d["유동인구_분기평균"] / d["상주인구"]
    d["V점수"] = (pct_rank(d["직장_상주_배율"]) + pct_rank(d["유동_상주_배율"])) / 2

    # E/P: 같은 업종끼리 비교한 객단가 순위를 매출 비중으로 평균 + 프랜차이즈 비율(참고)
    s = t["sales"].groupby(["상권_코드", "서비스_업종_코드_명"])[["당월_매출_금액", "당월_매출_건수"]].sum().reset_index()
    s["객단가"] = s["당월_매출_금액"] / s["당월_매출_건수"]
    big = s.groupby("서비스_업종_코드_명")["상권_코드"].transform("nunique") >= 50
    s = s[big].copy()
    s["업종내_객단가_순위"] = s.groupby("서비스_업종_코드_명")["객단가"].rank(pct=True) * 100
    d["P점수"] = s.groupby("상권_코드").apply(
        lambda x: np.average(x["업종내_객단가_순위"], weights=x["당월_매출_금액"]), include_groups=False)
    st4 = t["stores"].query("기준_년분기_코드 == 20254").groupby("상권_코드")[["프랜차이즈_점포_수", "전체_점포_수"]].sum()
    d["프랜차이즈_비율"] = st4["프랜차이즈_점포_수"] / st4["전체_점포_수"] * 100
    tot = t["sales"].groupby("상권_코드")[["당월_매출_금액", "주말_매출_금액"]].sum()
    d["주말_매출_비중"] = tot["주말_매출_금액"] / tot["당월_매출_금액"] * 100
    d["연매출_억"] = tot["당월_매출_금액"] / 1e8

    # S/G: 1분기 → 4분기 매출 증감률(같은 상권 비교) + 1년 개업률
    q = t["sales"].groupby(["상권_코드", "기준_년분기_코드"])["당월_매출_금액"].sum().unstack()
    d["매출_증감률"] = (q[20254] / q[20251] - 1) * 100
    st = t["stores"].groupby("상권_코드").agg(개업=("개업_점포_수", "sum"), 점포=("전체_점포_수", "sum"))
    d["개업률"] = st["개업"] / (st["점포"] / 4) * 100
    d["G점수"] = (pct_rank(d["매출_증감률"]) + pct_rank(d["개업률"])) / 2
    d["상권변화지표"] = t["change"].query("기준_년분기_코드 == 20254").set_index("상권_코드")["상권_변화_지표_명"]

    ok = d[["V점수", "P점수", "G점수"]].notna().all(axis=1)
    d.loc[ok, "유형"] = (np.where(d.loc[ok, "V점수"] > d.loc[ok, "V점수"].median(), "V", "L")
                       + np.where(d.loc[ok, "P점수"] > d.loc[ok, "P점수"].median(), "P", "E")
                       + np.where(d.loc[ok, "G점수"] > d.loc[ok, "G점수"].median(), "G", "S"))
    save_table(d.round(2), "상권_MBTI_지표_2025.csv")
    return d, s


def fig_lv(d):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.1, 1]})
    ax = axes[0]
    x = np.log10(d["직장_상주_배율"].dropna())
    ax.hist(x, bins=45, color=BLUE, edgecolor="white", linewidth=0.5)
    med = x.median()
    ax.axvline(med, color=INK, linewidth=1)
    ax.text(med + 0.05, ax.get_ylim()[1] * 0.92, f"중앙값 {10 ** med:.2f}배", fontsize=9, color=INK)
    ticks = [0.01, 0.1, 1, 10, 100]
    ax.set_xticks(np.log10(ticks), ["0.01배", "0.1배", "1배", "10배", "100배"])
    ax.set_xlabel("일하는 사람 ÷ 사는 사람 (10배씩 커지는 눈금)")
    ax.set_ylabel("상권 수")
    ax.set_title("① 상권별 '일하는 사람 ÷ 사는 사람'")

    ax = axes[1]
    data = [d.loc[d["상권_구분_코드_명"] == k, "V점수"].dropna() for k in TRADE_TYPES]
    bp = ax.boxplot(data, orientation="horizontal", patch_artist=True, widths=0.55, medianprops={"color": INK, "linewidth": 1.5},
                    whiskerprops={"color": INK2}, capprops={"color": INK2},
                    flierprops={"marker": "o", "markersize": 3, "markerfacecolor": GRAY, "markeredgecolor": "none"})
    for patch in bp["boxes"]:
        patch.set_facecolor("#9ec5f4")
        patch.set_edgecolor(BLUE)
    ax.set_yticks(range(1, 5), [f"{k} ({len(v)}곳)" for k, v in zip(TRADE_TYPES, data)])
    ax.invert_yaxis()
    ax.axvline(d["V점수"].median(), color=INK, linewidth=1)
    ax.set_xlabel("V 점수 (0~100)    ← L 생활형 · 중앙값 · V 방문형 →")
    ax.set_title("② 상권 종류별 V 점수")
    ax.grid(axis="y", visible=False)
    caption(fig, "V 점수 = '직장인구 ÷ 상주인구'와 '유동인구 ÷ 상주인구'의 백분위 순위 평균. 자료: 상권 상주·직장·길단위인구(OA-15584·15569·15568), 2025년")
    save(fig, "01_LV_생활형_방문형.png")


def fig_lv_check(d):
    x = d.dropna(subset=["V점수", "주말_매출_비중"])
    rho = x[["V점수", "주말_매출_비중"]].corr(method="spearman").iloc[0, 1]
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.scatter(x["V점수"], x["주말_매출_비중"], s=12, color=BLUE, alpha=0.35, edgecolor="none")
    bins = pd.cut(x["V점수"], np.arange(0, 101, 10))
    m = x.groupby(bins, observed=True)["주말_매출_비중"].median()
    ax.plot([b.mid for b in m.index], m.values, color=ORANGE, linewidth=2.2, marker="o", markersize=6, label="10점 구간별 중앙값")
    ax.axhline(2 / 7 * 100, color=INK2, linewidth=0.8)
    ax.text(99, 57, "가는 선 = 매일 똑같이 팔면 28.6%", fontsize=8.5, color=INK2, ha="right")
    ax.set_ylim(0, 60)
    ax.set_xlabel("V 점수 (클수록 방문객 중심)")
    ax.set_ylabel("주말 매출 비중 (%)")
    ax.set_title(f"V 점수가 높은 상권은 주말에 덜 팔까? (순위 상관계수 = {rho:.2f})")
    ax.legend(loc="upper left")
    caption(fig, "점 하나 = 상권 하나. 주말 비중이 60%를 넘는 일부 상권은 그림 밖. 자료: 추정매출(OA-15572), 2025년 합계")
    save(fig, "02_LV_검증_주말매출.png")
    return rho


def fig_ep_reason(s):
    g = s.groupby("서비스_업종_코드_명")[["당월_매출_금액", "당월_매출_건수"]].sum()
    g["객단가"] = g["당월_매출_금액"] / g["당월_매출_건수"]
    pick = ["편의점", "커피-음료", "제과점", "분식전문점", "패스트푸드점", "한식음식점", "반찬가게",
            "호프-간이주점", "일식음식점", "양식음식점", "화장품", "미용실", "일반의류", "일반교습학원", "시계및귀금속"]
    g = g.loc[[p for p in pick if p in g.index], "객단가"].sort_values() / 1e4
    within = s[s["서비스_업종_코드_명"].isin(g.index)].groupby("서비스_업종_코드_명")["객단가"].quantile([0.1, 0.9]).unstack() / 1e4

    fig, ax = plt.subplots(figsize=(9, 6.5))
    y = np.arange(len(g))
    for i, k in enumerate(g.index):
        ax.plot([within.loc[k, 0.1], within.loc[k, 0.9]], [i, i], color="#9ec5f4", linewidth=5, solid_capstyle="round")
    ax.scatter(g.values, y, color=BLUE, s=40, zorder=3)
    ax.set_xscale("log")
    ax.set_xticks([0.5, 1, 2, 5, 10, 20, 50, 100], ["5천", "1만", "2만", "5만", "10만", "20만", "50만", "100만"])
    ax.set_yticks(y, g.index)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("객단가 (원, 10배씩 커지는 눈금)")
    ax.set_title("업종마다 객단가가 100배 넘게 다르다")
    ax.legend(handles=[plt.Line2D([], [], color=BLUE, marker="o", linestyle="", label="서울 전체 객단가"),
                       plt.Line2D([], [], color="#9ec5f4", linewidth=5, label="상권별 객단가 (하위 10% ~ 상위 10%)")], loc="lower right")
    caption(fig, "객단가 = 매출 금액 ÷ 매출 건수. 자료: 추정매출(OA-15572), 2025년 합계")
    save(fig, "03_EP_업종별_객단가.png")
    return g


def fig_ep(d):
    x = d.dropna(subset=["P점수", "프랜차이즈_비율"])
    rho = x[["P점수", "프랜차이즈_비율"]].corr(method="spearman").iloc[0, 1]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    ax = axes[0]
    ax.hist(d["P점수"].dropna(), bins=40, color=BLUE, edgecolor="white", linewidth=0.5)
    med = d["P점수"].median()
    ax.axvline(med, color=INK, linewidth=1)
    ax.text(med + 1, ax.get_ylim()[1] * 0.92, f"중앙값 {med:.0f}", fontsize=9, color=INK,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    ax.set_xlabel("P 점수 (0~100, 같은 업종 안에서 객단가가 높을수록 큼)")
    ax.set_ylabel("상권 수")
    ax.set_title("① 상권별 P 점수 분포")
    ax = axes[1]
    meds = [d.loc[d["상권_구분_코드_명"] == k, "P점수"].median() for k in TRADE_TYPES]
    ax.barh(TRADE_TYPES, meds, color=BLUE, height=0.55)
    ax.invert_yaxis()
    ax.axvline(50, color=INK2, linewidth=0.8)
    bar_labels(ax, meds, "{:.0f}", horizontal=True, pad=0.8)
    ax.set_xlim(0, 80)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("P 점수 중앙값")
    ax.set_title(f"② 상권 종류별 P 점수 (프랜차이즈 비율과 상관 {rho:.2f})")
    caption(fig, "P 점수 = 업종마다 '서울 상권 중 몇 등 객단가인가'를 구해 매출 비중으로 평균. 50개 이상 상권에 있는 업종만 사용. 자료: OA-15572·15577, 2025년")
    save(fig, "04_EP_실속형_프리미엄형.png")
    return rho


def fig_sg(d):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    ax = axes[0]
    ax.hist(d["매출_증감률"].dropna().clip(-60, 100), bins=50, color=BLUE, edgecolor="white", linewidth=0.5)
    med = d["매출_증감률"].median()
    ax.axvline(0, color=INK2, linewidth=0.8)
    ax.axvline(med, color=INK, linewidth=1)
    ax.text(med + 2, ax.get_ylim()[1] * 0.92, f"중앙값 {med:+.1f}%", fontsize=9, color=INK)
    ax.set_xlabel("1분기 → 4분기 매출 증감률 (%, -60~100%로 자름)")
    ax.set_ylabel("상권 수")
    ax.set_title("① 상권별 매출 증감률")
    ax = axes[1]
    order = ["상권확장", "다이나믹", "정체", "상권축소"]
    m = d.groupby("상권변화지표")["G점수"].median().reindex(order)
    n = d.groupby("상권변화지표")["G점수"].count().reindex(order)
    colors = [BLUE if k in ("상권확장", "다이나믹") else GRAY for k in order]
    ax.bar(order, m.values, color=colors, width=0.6)
    ax.axhline(50, color=INK2, linewidth=0.8)
    for i, (v, c) in enumerate(zip(m.values, n.values)):
        ax.text(i, v - 9, f"{v:.0f}\n({c}곳)", ha="center", va="top", fontsize=9,
                color="white" if colors[i] == BLUE else INK)
    ax.set_ylim(0, 75)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("G 점수 중앙값")
    ax.set_title("② 서울시 상권변화지표별 G 점수")
    caption(fig, "G 점수 = '매출 증감률'과 '1년 개업률'의 백분위 순위 평균. 오른쪽: 서울시 상권변화지표(2025년 4분기)와 G 점수가 같은 방향인지 확인. 자료: OA-15572·15577·15576")
    save(fig, "05_SG_안정형_성장형.png")
    return m


def fig_axes_corr(d):
    cols = {"V점수": "V 점수", "직장_상주_배율": "직장÷상주", "주말_매출_비중": "주말 매출 비중",
            "P점수": "P 점수", "프랜차이즈_비율": "프랜차이즈 비율", "G점수": "G 점수",
            "매출_증감률": "매출 증감률", "개업률": "개업률", "연매출_억": "상권 매출 규모"}
    c = d[list(cols)].rename(columns=cols).corr(method="spearman")
    fig, ax = plt.subplots(figsize=(8.5, 7))
    im = ax.imshow(c.values, cmap=DIV_CMAP, vmin=-1, vmax=1)
    ax.set_xticks(range(len(c)), c.columns, rotation=40, ha="right")
    ax.set_yticks(range(len(c)), c.index)
    ax.grid(False)
    for i in range(len(c)):
        for j in range(len(c)):
            v = c.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8.5, color="white" if abs(v) > 0.6 else INK)
    for k in (2.5, 4.5, 7.5):
        ax.axhline(k, color="white", linewidth=3)
        ax.axvline(k, color="white", linewidth=3)
    fig.colorbar(im, ax=ax, shrink=0.8, label="같이 움직이는 정도 (-1 ~ +1)")
    ax.set_title("세 축과 재료 지표끼리의 순위 상관계수")
    caption(fig, "흰 선으로 L/V 묶음, E/P 묶음, S/G 묶음, 상권 규모를 나눔. V·P·G 점수끼리는 0에 가까울수록 서로 독립적이라 8유형이 고르게 나뉨")
    save(fig, "06_세축_상관관계.png")
    save_table(c.round(2), "06_세축_상관관계.csv")
    return c


def fig_types(d):
    x = d.dropna(subset=["유형"])
    cnt = x["유형"].value_counts().reindex(MBTI_ORDER)
    cross = pd.crosstab(x["유형"], x["상권_구분_코드_명"]).reindex(index=MBTI_ORDER, columns=TRADE_TYPES).fillna(0).astype(int)
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.bar([f"{k}\n{MBTI_NAME[k]}" for k in cnt.index], cnt.values, color=BLUE, width=0.62)
    ax.axhline(len(x) / 8, color=INK2, linewidth=0.8)
    ax.text(-0.45, cnt.max() * 1.18, f"가는 선 = 똑같이 나누면 {len(x) / 8:.0f}곳", fontsize=8.5, color=INK2)
    for i, v in enumerate(cnt.values):
        ax.text(i, v - 45, f"{v}곳\n({v / len(x) * 100:.0f}%)", ha="center", va="top", fontsize=9, color="white")
    ax.set_ylim(0, cnt.max() * 1.25)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("상권 수")
    ax.set_title(f"세 축을 중앙값으로 나누면: 상권 {len(x):,}곳의 8유형 분포")
    caption(fig, "각 축의 점수가 서울 상권 중앙값보다 크면 V·P·G, 작으면 L·E·S. 세 점수가 모두 있는 상권만 사용")
    save(fig, "07_8유형_상권분포.png")
    save_table(cross.assign(합계=cross.sum(axis=1)), "07_8유형_상권종류_교차표.csv")
    return cnt, cross


def fig_type_maps(d):
    x = d.dropna(subset=["유형"])
    fig, axes = plt.subplots(2, 4, figsize=(17, 6.6))
    fig.subplots_adjust(hspace=0.12, wspace=0.02)
    for ax, k in zip(axes.flat, MBTI_ORDER):
        on = x["유형"] == k
        ax.scatter(x.loc[~on, "엑스좌표_값"], x.loc[~on, "와이좌표_값"], s=4, color=LIGHT_GRAY, edgecolor="none")
        ax.scatter(x.loc[on, "엑스좌표_값"], x.loc[on, "와이좌표_값"], s=9, color=BLUE, edgecolor="none")
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{k} {MBTI_NAME[k]} ({on.sum()}곳)", fontsize=11.5)
    fig.suptitle("8유형 상권은 서울 어디에 있을까?", x=0.01, ha="left", fontsize=15, fontweight="bold", y=1.0)
    caption(fig, "점 하나 = 상권 하나 (상권 중심 좌표). 파랑 = 해당 유형, 회색 = 나머지 상권")
    save(fig, "08_8유형_지도.png")


def fig_type_biz(d, s):
    """유형별 특화 업종: (그 유형 안의 업종 매출 비중) ÷ (서울 전체 업종 매출 비중)."""
    x = s.merge(d[["유형"]], left_on="상권_코드", right_index=True).dropna(subset=["유형"])
    share = x.pivot_table(index="유형", columns="서비스_업종_코드_명", values="당월_매출_금액", aggfunc="sum").fillna(0)
    share = share.div(share.sum(axis=1), axis=0)
    total = x.groupby("서비스_업종_코드_명")["당월_매출_금액"].sum()
    total = total / total.sum()
    lq = (share / total).reindex(index=MBTI_ORDER)
    big = total[total > 0.005].index
    top = {k: ", ".join(f"{b}({v:.1f})" for b, v in lq.loc[k, big].nlargest(4).items()) for k in MBTI_ORDER}
    sub = lq[CANDIDATE_BIZ]

    fig, ax = plt.subplots(figsize=(12, 5.4))
    im = ax.imshow(np.log2(sub.values), cmap=DIV_CMAP, vmin=-1.5, vmax=1.5, aspect="auto")
    ax.set_xticks(range(sub.shape[1]), sub.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(sub)), [f"{k} {MBTI_NAME[k]}" for k in sub.index])
    ax.grid(False)
    for i in range(sub.shape[0]):
        for j in range(sub.shape[1]):
            v = sub.values[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=8.5, color="white" if abs(np.log2(v)) > 1 else INK)
    cb = fig.colorbar(im, ax=ax, shrink=0.85, ticks=[-1.5, -1, 0, 1, 1.5])
    cb.ax.set_yticklabels(["0.35배", "0.5배", "1배 (서울 평균)", "2배", "2.8배"])
    ax.set_title("유형별로 어떤 업종 매출이 서울 평균보다 많을까? (특화 지수)")
    caption(fig, "특화 지수 = 그 유형 상권 안에서 업종이 차지하는 매출 비중 ÷ 서울 전체에서의 비중. 1보다 크면(파랑) 그 유형에 몰린 업종. 업종은 금융_MBTI.md 추천 아이템에 대응하는 후보")
    save(fig, "09_유형별_특화업종.png")
    save_table(lq.T.round(2), "09_유형별_업종_특화지수.csv")
    return sub, top


def fig_biz_cards(t):
    s = t["sales"].groupby("서비스_업종_코드_명")[["당월_매출_금액", "당월_매출_건수"]].sum()
    st = t["stores"].groupby("서비스_업종_코드_명").agg(개업=("개업_점포_수", "sum"), 폐업=("폐업_점포_수", "sum"), 점포합=("전체_점포_수", "sum"))
    st4 = t["stores"].query("기준_년분기_코드 == 20254").groupby("서비스_업종_코드_명")[["전체_점포_수", "프랜차이즈_점포_수"]].sum()
    c = pd.DataFrame({
        "점포_수": st4["전체_점포_수"],
        "객단가_원": s["당월_매출_금액"] / s["당월_매출_건수"],
        "개업률": st["개업"] / (st["점포합"] / 4) * 100,
        "폐업률": st["폐업"] / (st["점포합"] / 4) * 100,
        "프랜차이즈_비율": st4["프랜차이즈_점포_수"] / st4["전체_점포_수"] * 100,
    }).loc[CANDIDATE_BIZ]
    c["순증가율"] = c["개업률"] - c["폐업률"]
    c = c.sort_values("순증가율")

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), sharey=True)
    y = np.arange(len(c))
    ax = axes[0]
    ax.barh(y, c["객단가_원"] / 1e4, color=BLUE, height=0.6)
    bar_labels(ax, c["객단가_원"] / 1e4, "{:.1f}만", horizontal=True, pad=0.2)
    ax.set_title("① 객단가")
    ax.set_xlabel("만 원")
    ax.set_xlim(0, (c["객단가_원"] / 1e4).max() * 1.3)
    ax = axes[1]
    ax.barh(y - 0.17, c["개업률"], height=0.32, color=BLUE, label="개업률")
    ax.barh(y + 0.17, c["폐업률"], height=0.32, color=ORANGE, label="폐업률")
    ax.set_title("② 1년 개업률 · 폐업률")
    ax.set_xlabel("%")
    ax.legend(loc="lower right")
    ax = axes[2]
    colors = [BLUE if v >= 0 else ORANGE for v in c["순증가율"]]
    ax.barh(y, c["순증가율"], color=colors, height=0.6)
    ax.axvline(0, color=INK2, linewidth=0.8)
    for i, v in enumerate(c["순증가율"]):
        ax.text(v + (0.3 if v >= 0 else -0.3), i, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=8.5, color=INK2)
    ax.set_title("③ 순증가율 (개업률 - 폐업률)")
    ax.set_xlabel("%p")
    ax.set_xlim(c["순증가율"].min() * 1.5, max(c["순증가율"].max() * 1.6, 3))
    for a in axes:
        a.grid(axis="y", visible=False)
    axes[0].set_yticks(y, c.index)
    caption(fig, "후보 업종 = 금융_MBTI.md 추천 창업 아이템에 대응하는 업종. 자료: 추정매출(OA-15572)·점포(OA-15577), 2025년")
    save(fig, "10_후보업종_카드.png")
    save_table(c.round(1), "10_후보업종_카드.csv")
    return c


# ================================================================ 2. 창업자(사용자) 쪽

def fig_founder():
    b = read(RAW_DIR / "bigdata_campus" / "seoul_lifestyle_금융생활_재현데이터_sample1000.csv")
    b["나이"] = 2025 - b["생년월일"]
    b["그룹"] = np.where(b["사업자여부"] == 1, "사업자", "비사업자")
    rate = b.groupby("그룹").agg(대출_있음=("대출여부", "mean"), 집_있음=("주택보유여부", "mean"),
                                차_있음=("차량보유", lambda x: (x >= 1).mean())) * 100
    med = b.groupby("그룹").agg(나이_중앙값=("나이", "median"), 소득백분위_중앙값=("추정연소득_백분위", "median"), 사람수=("나이", "size"))

    group = pd.read_excel(RAW_DIR / "living" / "관심집단_2025.12.xlsx", usecols=["연령대", "총인구", "재정상태에 대한 관심집단"])
    g = group.groupby("연령대")[["재정상태에 대한 관심집단", "총인구"]].sum()
    fin = g["재정상태에 대한 관심집단"] / g["총인구"] * 100

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6), gridspec_kw={"width_ratios": [1, 1, 1.3]})
    ax = axes[0]
    for grp, c, a in [("비사업자", GRAY, 0.6), ("사업자", BLUE, 0.75)]:
        ages = b.loc[b["그룹"] == grp, "나이"]
        ax.hist(ages, bins=np.arange(10, 105, 5), density=True, alpha=a, color=c,
                label=f"{grp} ({len(ages)}명, 중앙값 {ages.median():.0f}세)")
    ax.set_xlabel("나이 (2025년 기준)")
    ax.set_ylabel("비율")
    ax.set_yticks([])
    ax.set_title("① 사업자와 비사업자의 나이")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.35)
    ax.legend(loc="upper left", fontsize=8.5)
    ax.grid(axis="x", visible=False)

    ax = axes[1]
    x = np.arange(3)
    for i, (grp, c) in enumerate([("비사업자", GRAY), ("사업자", BLUE)]):
        vals = rate.loc[grp, ["대출_있음", "집_있음", "차_있음"]].values
        ax.bar(x + (i - 0.5) * 0.36, vals, width=0.34, color=c, label=grp)
        for xi, v in zip(x, vals):
            ax.text(xi + (i - 0.5) * 0.36, v + 0.8, f"{v:.0f}%", ha="center", fontsize=8.5, color=INK2)
    ax.set_xticks(x, ["대출 있음", "집 있음", "차 있음"])
    ax.set_ylim(0, rate.values.max() * 1.3)
    ax.grid(axis="x", visible=False)
    ax.set_title("② 금융 상태 비교")
    ax.legend(loc="upper right")

    ax = axes[2]
    colors = [ORANGE if v == fin.max() else BLUE for v in fin.values]
    ax.bar([f"{a}~" for a in fin.index], fin.values, color=colors, width=0.65)
    bar_labels(ax, fin.values, "{:.1f}", pad=0.05)
    ax.grid(axis="x", visible=False)
    ax.set_xlabel("나이 (5살 단위)")
    ax.set_ylabel("인구 중 비율 (%)")
    ax.set_title("③ '재정 상태에 관심이 많은 집단' 비율")
    caption(fig, "①② 빅데이터캠퍼스 금융생활 재현데이터(가상 1,000명, 사업자 87명) / ③ 서울시×SKT 생활데이터 관심집단(2025년 12월). 20세 미만은 ③ 자료에 없음")
    save(fig, "11_창업자_데이터.png")
    return rate.round(1), med, fin.round(1)


# ================================================================ 3. 소비 잠재력 미리보기 (행정동)

def potential_table():
    """행정동별 생활소비, 기대 소비, 실제 ÷ 기대를 계산한다."""
    spend = read(RAW_DIR / "OA-22166_소비_행정동.csv")
    res = read(RAW_DIR / "OA-22183_상주인구_행정동.csv")
    wrk = read(RAW_DIR / "OA-22184_직장인구_행정동.csv")
    flw = read(RAW_DIR / "OA-22178_길단위인구_행정동.csv")
    fac = read(RAW_DIR / "OA-22169_집객시설_행정동.csv").fillna(0)
    key = ["행정동_코드", "행정동_코드_명"]
    s = spend.groupby(key)[["지출_총금액", "여가_문화_지출_총금액", "기타_지출_총금액"]].sum()
    d = pd.DataFrame({
        "생활소비": s["지출_총금액"] - s["여가_문화_지출_총금액"] - s["기타_지출_총금액"],
        "상주인구": res.groupby(key)["총_상주인구_수"].mean(),
        "직장인구": wrk.groupby(key)["총_직장_인구_수"].mean(),
        "유동인구": flw.groupby(key)["총_유동인구_수"].mean(),
        "집객시설": fac.groupby(key)["집객시설_수"].mean(),
    }).dropna()
    d = d[d["생활소비"] > 0]
    feats = ["상주인구", "직장인구", "유동인구", "집객시설"]
    X = np.column_stack([np.ones(len(d))] + [np.log10(d[c] + 1) for c in feats])
    y = np.log10(d["생활소비"])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    d["기대소비"] = 10 ** pred
    d["실제_나누기_기대"] = d["생활소비"] / d["기대소비"]
    return d.reset_index(), r2, dict(zip(["상수"] + feats, coef.round(3)))


def fig_potential():
    d, r2, coef = potential_table()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    ax = axes[0]
    under = d["실제_나누기_기대"] < 0.5
    over = d["실제_나누기_기대"] > 2
    mid = ~(under | over)
    ax.scatter(d.loc[mid, "기대소비"] / 1e8, d.loc[mid, "생활소비"] / 1e8, s=16, color=GRAY, alpha=0.7, edgecolor="none", label="기대와 비슷 (0.5~2배)")
    ax.scatter(d.loc[under, "기대소비"] / 1e8, d.loc[under, "생활소비"] / 1e8, s=24, color=BLUE, edgecolor="white", linewidth=0.5, label=f"기대의 절반 미만 ({under.sum()}곳)")
    ax.scatter(d.loc[over, "기대소비"] / 1e8, d.loc[over, "생활소비"] / 1e8, s=24, color=ORANGE, edgecolor="white", linewidth=0.5, label=f"기대의 2배 초과 ({over.sum()}곳)")
    lo = d[["기대소비", "생활소비"]].min().min() / 1e8 * 0.8
    hi = d[["기대소비", "생활소비"]].max().max() / 1e8 * 1.2
    ax.plot([lo, hi], [lo, hi], color=INK2, linewidth=0.8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("기대 생활소비 (억 원, 10배씩 커지는 눈금)")
    ax.set_ylabel("실제 생활소비 (억 원)")
    ax.set_title(f"① 실제 vs 기대 (설명력 R² = {r2:.2f})")
    ax.legend(loc="upper left", fontsize=8.5)

    ax = axes[1]
    bins = [0, 0.5, 0.8, 1.25, 2, np.inf]
    labels = ["절반 미만", "0.5~0.8배", "0.8~1.25배", "1.25~2배", "2배 초과"]
    cnt = pd.cut(d["실제_나누기_기대"], bins, labels=labels).value_counts().reindex(labels)
    ax.bar(labels, cnt.values, color=[BLUE, "#9ec5f4", GRAY, "#f4b49a", ORANGE], width=0.65)
    bar_labels(ax, cnt.values, "{:.0f}곳", pad=3)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("행정동 수")
    ax.set_ylim(0, cnt.max() * 1.15)
    ax.set_title("② 실제 ÷ 기대: 몇 배일까?")
    ax.text(0, cnt.max() * 1.02, "← 덜 쓰는 동 (성장 여지?)", fontsize=9, color=BLUE)
    ax.text(4.3, cnt.max() * 1.02, "더 쓰는 동 →", fontsize=9, color=ORANGE, ha="right")
    caption(fig, "생활소비 = 전체 지출 - 여가·문화 - 기타 (결제 주소 효과가 큰 두 항목 제외). 기대소비 = 상주·직장·유동인구·집객시설로 만든 단순 회귀식. 자료: 행정동 소비·인구·집객시설, 2025년")
    save(fig, "12_소비잠재력_미리보기.png")
    out = d.set_index("행정동_코드_명")[["생활소비", "기대소비", "실제_나누기_기대", "상주인구", "직장인구"]]
    save_table(out.sort_values("실제_나누기_기대").round(2), "12_행정동_소비잠재력.csv")
    return r2, coef, out, cnt


# ================================================================ 실행

def main():
    setup_style()
    t = load_trade()

    print("\n## 0. 데이터 준비도")
    ready, static = table_readiness(t)
    print(ready.to_string(), "\n분기마다 값이 같은 상권 비율(%):", {k: round(v, 1) for k, v in static.items()})

    print("\n## 1. 상권 3축")
    d, s = build_axes(t)
    print(d[["직장_상주_배율", "유동_상주_배율", "V점수", "P점수", "프랜차이즈_비율", "매출_증감률", "개업률", "G점수", "주말_매출_비중"]].describe().round(2).to_string())
    print("V점수 중앙값 by 상권구분:", d.groupby("상권_구분_코드_명")["V점수"].median().round(1).to_dict())
    print("P점수 중앙값 by 상권구분:", d.groupby("상권_구분_코드_명")["P점수"].median().round(1).to_dict())
    print("유형 부여 상권 수:", d["유형"].notna().sum())
    fig_lv(d)
    print("V-주말비중 rho:", round(fig_lv_check(d), 2))
    print(fig_ep_reason(s).round(1).to_string())
    print("P-프랜차이즈 rho:", round(fig_ep(d), 2))
    print(fig_sg(d).round(1).to_string())
    print(fig_axes_corr(d).round(2).to_string())

    print("\n## 2. 8유형")
    cnt, cross = fig_types(d)
    print(cnt.to_string(), "\n", cross.to_string())
    fig_type_maps(d)
    for k in MBTI_ORDER:
        print(k, "자치구 TOP3:", d[d["유형"] == k]["자치구_코드_명"].value_counts().head(3).to_dict(),
              "| 매출 큰 상권:", d[d["유형"] == k].nlargest(3, "연매출_억")["상권_코드_명"].tolist())
    sub, top = fig_type_biz(d, s)
    print(sub.round(2).to_string())
    for k, v in top.items():
        print(k, "특화 TOP4:", v)
    print(fig_biz_cards(t).round(1).to_string())

    print("\n## 3. 창업자 쪽")
    rate, med, fin = fig_founder()
    print(rate.to_string(), "\n", med.to_string(), "\n", fin.to_string())

    print("\n## 4. 소비 잠재력")
    r2, coef, out, cnt = fig_potential()
    print("R2", round(r2, 3), coef, "\n", cnt.to_string())
    print("기대보다 적게:", out.nsmallest(8, "실제_나누기_기대")["실제_나누기_기대"].round(2).to_dict())
    print("기대보다 많이:", out.nlargest(8, "실제_나누기_기대")["실제_나누기_기대"].round(2).to_dict())
    print("특이 4개 동:", out[out.index.isin(OUTLIER_DONG)]["실제_나누기_기대"].round(2).to_dict())


if __name__ == "__main__":
    main()
