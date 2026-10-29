"""공용 전처리 표(data/processed) 기준 EDA 그림 생성 스크립트.

먼저: python scripts/build_processed_2025.py   (data/processed/ 표 4개 만들기)
실행: python 김지영/eda_processed_2025.py      (저장소 루트에서, pandas·matplotlib 필요)
결과: 김지영/eda_processed_figures/*.png  ->  김지영/EDA_processed_2025.md 에서 사용
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter, LogLocator

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = Path(__file__).resolve().parent / "eda_processed_figures"
OUT.mkdir(exist_ok=True)

# ── 스타일 (dataviz 기본 팔레트, eda_raw_2025.py 와 같음) ─────────────
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, GRAY = "#e1e0d9", "#c3c2b7", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"   # 주황 = 소비_이상치 이름표에만 쓴다
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SEQ = LinearSegmentedColormap.from_list("seq", BLUE_RAMP)

plt.rcParams.update({
    "font.family": "AppleGothic", "axes.unicode_minus": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": False, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 13, "axes.titlesize": 19, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "axes.titlelocation": "left", "axes.titlepad": 16,
})
HALO = [pe.withStroke(linewidth=3.5, foreground=SURFACE)]


def read(name):
    return pd.read_csv(PROC / name, encoding="utf-8-sig", low_memory=False)


def save(fig, name):
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    print("saved", name)


def subtitle(ax, text):
    ax.set_title(ax.get_title(loc="left"), loc="left", pad=38)
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK2, fontsize=13, va="bottom")


def plain_log(ax, axes="xy"):
    fmt = FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else f"{v:g}")
    for a in axes:
        axis = ax.xaxis if a == "x" else ax.yaxis
        axis.set_major_locator(LogLocator(base=10))
        axis.set_major_formatter(fmt)


def hgrid(ax, axis="y"):
    ax.grid(True, axis=axis)
    ax.set_axisbelow(True)


K, Q = "행정동_코드", "기준_년분기_코드"
master = read("행정동_마스터.csv")
panel = read("행정동_분기.csv")
trade = read("상권_업종_분기.csv")
mapping = read("업종_공통그룹.csv")

FLAG = master.set_index(K)["소비_이상치"]
NAME = master.set_index(K)["행정동_명"]
YEAR = panel.groupby(K).sum(numeric_only=True).drop(columns=Q)   # 2025년 합계
CONS_GROUP = mapping[mapping["원본출처"] == "소비_항목"].set_index("원본코드")["공통그룹"]
GROUP_ORDER = ["외식", "식료품", "의료", "의류·잡화", "생활용품", "교육", "유흥", "여가·오락",
               "생활서비스", "교통", "숙박", "부동산", "연결 안 함"]


def sales_col(group):
    return "상권_매출_" + group.replace(" ", "")


# ── 01. 공용 표 4개 ─────────────────────────────────────────
def fig_tables():
    boxes = [
        (0.3, 3.3, "행정동_마스터", f"{len(master)}행", "동마다 한 줄 · 잘 안 바뀌는 값\n코드 4종 · 인구 · 시설 · 소득 · 이름표"),
        (6.9, 3.3, "행정동_분기", f"{len(panel):,}행", "동 × 4분기 · 바뀌는 값\n소비 · 유동인구 · 상권 매출 · SKT"),
        (0.3, 0.3, "업종_공통그룹", f"{len(mapping)}행", "62개 업종 + 소비 10개 항목\n→ 공통 그룹 12개"),
        (6.9, 0.3, "상권_업종_분기", f"{len(trade):,}행", "상권 × 업종 × 분기\n매출 · 점포 · 개업 · 폐업"),
    ]
    fig, ax = plt.subplots(figsize=(13, 6.6))
    ax.set_xlim(0, 13); ax.set_ylim(0, 5.9); ax.axis("off")
    for x, y, name, n, desc in boxes:
        ax.add_patch(FancyBboxPatch((x, y), 5.8, 2.2, boxstyle="round,pad=0,rounding_size=0.15",
                                    fc="white", ec=AXIS, lw=1.2))
        ax.add_patch(FancyBboxPatch((x, y + 1.55), 5.8, 0.65, boxstyle="round,pad=0,rounding_size=0.15",
                                    fc=BLUE, ec="none"))
        ax.text(x + 0.25, y + 1.87, name, color="white", fontsize=16, weight="bold", va="center")
        ax.text(x + 5.55, y + 1.87, n, color="white", fontsize=13, va="center", ha="right")
        ax.text(x + 0.25, y + 0.8, desc, color=INK, fontsize=13, va="center", linespacing=1.6)
    links = [((6.1, 4.4), (6.9, 4.4), "행정동_코드"), ((3.2, 2.5), (3.2, 3.3), "공통그룹"),
             ((6.9, 1.4), (6.1, 1.4), "공통그룹"), ((9.8, 2.5), (9.8, 3.3), "행정동_코드 + 분기")]
    for (x0, y0), (x1, y1), lab in links:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="<->", color=MUTED, lw=1.6))
        ax.text((x0 + x1) / 2 + (0.12 if x0 == x1 else 0), (y0 + y1) / 2 + (0 if x0 == x1 else 0.2),
                lab, fontsize=11, color=INK2, ha="left" if x0 == x1 else "center", va="center")
    ax.set_title("이번 EDA는 원본 35개 대신 공용 표 4개로 했어요")
    save(fig, "01_processed_tables.png")


# ── 02. 이름표 붙은 8곳: 분포 ─────────────────────────────────
def fig_hist():
    v = YEAR["지출_총금액"] / 1e8
    bins = np.logspace(np.log10(v.min()), np.log10(v.max()), 36)
    fig, ax = plt.subplots(figsize=(12, 6.4))
    ax.hist([v[~FLAG.reindex(v.index)], v[FLAG.reindex(v.index)]], bins=bins, stacked=True,
            color=[BLUE, ORANGE], label=["나머지 417곳", "소비_이상치 8곳"], rwidth=0.88)
    ax.set_xscale("log"); hgrid(ax)
    ax.set_xlabel("2025년 지출_총금액 (억 원, 로그 눈금)"); ax.set_ylabel("동 수")
    for code, off in zip(v[FLAG.reindex(v.index)].sort_values().index[-3:], [(-70, 50), (-15, 80), (30, 50)]):
        ax.annotate(NAME[code], (v[code], 1), xytext=off, textcoords="offset points", ha="center",
                    fontsize=11, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=1))
    ax.set_ylim(0, 72)
    ax.axvline(v.median(), color=INK2, lw=1)
    ax.text(v.median() * 1.1, 68, f"중앙값 {v.median():.0f}억", color=INK2, fontsize=12, va="center")
    plain_log(ax, "x")
    ax.legend(loc="upper right", frameon=False, fontsize=12)
    ax.set_title("이름표 붙은 8곳은 분포의 오른쪽 끝에 있어요")
    subtitle(ax, "값은 그대로 두고 이름표로 구분만 해요 · 425개 동")
    save(fig, "02_spending_with_tags.png")


# ── 03. 이름표 붙은 8곳: 지도 ─────────────────────────────────
def load_polys():
    gj = json.loads((RAW / "geo" / "HangJeongDong_ver20251231.geojson").read_text(encoding="utf-8"))
    by_new = {}
    for f in gj["features"]:
        p = f["properties"]
        if p["sido"] != "11":
            continue
        g = f["geometry"]
        parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        by_new.setdefault(int(p["adm_cd2"][:8]), []).extend(np.array(pt[0]) for pt in parts)
    # 마스터의 경계_코드로 쪼개진 동을 옛 동으로 묶는다
    return {row[K]: sum((by_new[int(c)] for c in str(row["경계_코드"]).split(",")), [])
            for _, row in master.iterrows()}


def fig_map():
    polys = load_polys()
    v = YEAR["지출_총금액"] / 1e8
    norm = LogNorm(v.min(), v.max())
    fig, ax = plt.subplots(figsize=(12, 9.4))
    verts, cols, tagged = [], [], []
    for code, rings in polys.items():
        for ring in rings:
            verts.append(ring)
            cols.append(SEQ(norm(v[code])))
            if FLAG[code]:
                tagged.append(ring)
    ax.add_collection(PolyCollection(verts, facecolors=cols, edgecolors=SURFACE, linewidths=0.4))
    ax.add_collection(PolyCollection(tagged, facecolors="none", edgecolors=ORANGE, linewidths=2.6))
    ax.autoscale_view(); ax.set_aspect(1 / np.cos(np.deg2rad(37.55))); ax.axis("off")
    offsets = {"소공동": (10, 70), "을지로동": (70, 45), "용산2가동": (60, -50), "염리동": (-60, 55),
               "문래동": (-80, 35), "구로3동": (-80, -40), "서초2동": (40, -60), "도곡2동": (60, -30)}
    for code in FLAG[FLAG].index:
        ring = max(polys[code], key=len)
        ax.annotate(NAME[code], (ring[:, 0].mean(), ring[:, 1].mean()), xytext=offsets[NAME[code]],
                    textcoords="offset points", fontsize=12, weight="bold", color=INK, path_effects=HALO,
                    arrowprops=dict(arrowstyle="-", color=ORANGE, lw=1.4))
    sm = plt.cm.ScalarMappable(norm=norm, cmap=SEQ)
    cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.035, pad=0.02, aspect=40)
    cb.set_label("2025년 지출_총금액 (억 원, 로그 눈금) · 주황 테두리 = 소비_이상치", color=INK2)
    cb.outline.set_visible(False)
    ax.set_title("8곳은 도심·업무지구에 흩어져 있어요")
    save(fig, "03_map_tags.png")


# ── 04. 공통 그룹: 두 데이터에서 몇 등? ───────────────────────────
def group_shares():
    med = {g: (YEAR[c] / YEAR["지출_총금액"]).median() * 100 for c, g in CONS_GROUP.items()}
    sales = trade.groupby("공통그룹")["당월_매출_금액"].sum()
    return pd.DataFrame({"소비": pd.Series(med), "매출": sales / sales.sum() * 100}).dropna()


def fig_slope():
    d = group_shares()
    rank_c = d["소비"].rank(ascending=False).astype(int)
    rank_s = d["매출"].rank(ascending=False).astype(int)
    fig, ax = plt.subplots(figsize=(11, 8))
    for g in d.index:
        moved = abs(rank_c[g] - rank_s[g]) >= 3
        col, lw = (BLUE, 2.6) if moved else (GRAY, 1.6)
        ax.plot([0, 1], [rank_c[g], rank_s[g]], color=col, lw=lw, marker="o", ms=9, mec=SURFACE, mew=2)
        ax.text(-0.04, rank_c[g], f"{g}  {d.loc[g, '소비']:.0f}%", ha="right", va="center", fontsize=13,
                color=INK, weight="bold" if moved else "normal")
        ax.text(1.04, rank_s[g], f"{d.loc[g, '매출']:.0f}%  {g}", ha="left", va="center", fontsize=13,
                color=INK, weight="bold" if moved else "normal")
    ax.set_ylim(len(d) + 0.6, -0.9); ax.set_xlim(-0.55, 1.55); ax.axis("off")
    ax.text(0, -0.3, "소비 데이터\n보통 동의 비중", ha="center", va="center", fontsize=13, color=INK2)
    ax.text(1, -0.3, "상권 매출 데이터\n서울 전체 비중", ha="center", va="center", fontsize=13, color=INK2)
    ax.set_title("같은 그룹, 두 데이터에서의 순위")
    subtitle(ax, "파란 선 = 순위가 3계단 이상 달라진 그룹 · 금액이 아니라 순위만 비교해요")
    save(fig, "04_group_rank_slope.png")


# ── 05. 같은 그룹끼리 동 순위가 비슷한가 ─────────────────────────
def group_rho():
    has = YEAR["상권_매출_금액"] > 0
    rho = {g: YEAR.loc[has, c].corr(YEAR.loc[has, sales_col(g)], method="spearman") for c, g in CONS_GROUP.items()}
    return pd.Series(rho).sort_values(), int(has.sum())


def fig_rho():
    rho, n = group_rho()
    fig, ax = plt.subplots(figsize=(12, 6.6))
    ax.barh(range(len(rho)), rho.values, color=BLUE, height=0.62)
    for i, val in enumerate(rho.values):
        ax.text(val + 0.012, i, f"{val:.2f}", va="center", fontsize=12, color=INK)
    ax.set_yticks(range(len(rho))); ax.set_yticklabels(rho.index, fontsize=13, color=INK)
    ax.set_xlim(0, 1); hgrid(ax, "x")
    ax.set_xlabel(f"동별 '소비 항목 금액'과 '상권 매출 금액'의 순위 상관 (Spearman ρ, 상권이 있는 {n}개 동)")
    ax.set_title("같은 그룹이면, 많이 쓰는 동이 매출도 많아요")
    subtitle(ax, "1에 가까울수록 두 데이터가 같은 동을 상위로 뽑아요 · 외식이 가장 비슷해요")
    save(fig, "05_group_rank_corr.png")


def fig_eatout():
    has = YEAR["상권_매출_금액"] > 0
    x = YEAR.loc[has, "음식_지출_총금액"] / 1e8
    y = YEAR.loc[has, sales_col("외식")] / 1e8
    rho = x.corr(y, method="spearman")   # 그림 05와 같은 동 집합
    keep = (x > 0) & (y > 0)              # 로그 축이라 0인 동은 그림에서만 뺀다
    x, y = x[keep], y[keep]
    f = FLAG.reindex(x.index)
    fig, ax = plt.subplots(figsize=(11, 8))
    ax.scatter(x[~f], y[~f], s=36, color=BLUE, alpha=0.6, edgecolor=SURFACE, linewidth=1, label="나머지 동")
    ax.scatter(x[f], y[f], s=110, color=ORANGE, edgecolor=SURFACE, linewidth=2, label="소비_이상치", zorder=3)
    for code in x[f].index:
        ax.annotate(NAME[code], (x[code], y[code]), xytext=(8, 6), textcoords="offset points",
                    fontsize=11, color=INK, path_effects=HALO)
    ax.set_xscale("log"); ax.set_yscale("log"); hgrid(ax, "both"); plain_log(ax)
    ax.set_xlabel("소비 데이터: 음식 지출 (억 원, 로그)"); ax.set_ylabel("상권 매출 데이터: 외식 매출 (억 원, 로그)")
    ax.legend(loc="upper left", frameon=False, fontsize=12)
    ax.set_title(f"외식: 두 데이터가 같은 동을 가리켜요 (순위 상관 {rho:.2f})")
    subtitle(ax, "이상치 8곳도 외식만 보면 다른 동과 같은 띠 안에 있어요")
    save(fig, "06_eatout_scatter.png")


# ── 07~09. 상권: 공통 그룹으로 ──────────────────────────────
def fig_sales_stores():
    sales = trade.groupby("공통그룹")["당월_매출_금액"].sum()
    stores = trade[trade[Q] == 20254].groupby("공통그룹")["전체_점포_수"].sum()
    d = pd.DataFrame({"매출": sales / sales.sum() * 100, "점포": stores / stores.sum() * 100}).reindex(GROUP_ORDER[::-1])
    y = np.arange(len(d)); h = 0.38
    fig, ax = plt.subplots(figsize=(12, 8.4))
    ax.barh(y + h / 2 + 0.02, d["매출"], height=h, color=BLUE, label="매출 비중 (2025년 합계)")
    ax.barh(y - h / 2 - 0.02, d["점포"], height=h, color=AQUA, label="점포 비중 (2025년 4분기)")
    for yi, g in zip(y, d.index):
        ax.text(d.loc[g, "매출"] + 0.3, yi + h / 2 + 0.02, f"{d.loc[g, '매출']:.1f}%", va="center", fontsize=10, color=INK)
        ax.text(d.loc[g, "점포"] + 0.3, yi - h / 2 - 0.02, f"{d.loc[g, '점포']:.1f}%", va="center", fontsize=10, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels(d.index, fontsize=13, color=INK)
    ax.set_xlabel("상권 전체에서 차지하는 비중 (%)"); hgrid(ax, "x")
    ax.legend(loc="lower right", frameon=False, fontsize=12)
    ax.set_title("식료품·의료는 가게 수보다 매출이 커요")
    subtitle(ax, "매출 막대가 점포 막대보다 길면 가게 하나가 버는 돈이 큰 그룹이에요 · 62개 업종 기준")
    save(fig, "07_group_sales_stores.png")


def fig_open_close():
    g = trade.groupby("공통그룹")[["개업_점포_수", "폐업_점포_수"]].sum()
    stores = trade.groupby(["공통그룹", Q])["전체_점포_수"].sum().groupby("공통그룹").mean()
    g["개업률"] = g["개업_점포_수"] / stores / 4 * 100
    g["폐업률"] = g["폐업_점포_수"] / stores / 4 * 100
    fig, ax = plt.subplots(figsize=(11, 8.4))
    grow = g["개업률"] > g["폐업률"]
    for mask, col, lbl in [(grow, BLUE, "열리는 곳이 더 많은 그룹"), (~grow, GRAY, "닫히는 곳이 더 많은 그룹")]:
        ax.scatter(g.loc[mask, "개업률"], g.loc[mask, "폐업률"], s=stores[mask] / 120, color=col,
                   edgecolor=SURFACE, linewidth=2, alpha=0.9, label=lbl)
    lim = 5.6
    ax.plot([0, lim], [0, lim], color=AXIS, lw=1.2)
    ax.text(4.6, 4.85, "열림 = 닫힘", color=MUTED, fontsize=11, rotation=37)
    offsets = {"외식": (14, 6), "유흥": (10, 8), "연결 안 함": (10, 0), "부동산": (10, 0), "숙박": (8, 8),
               "의류·잡화": (10, 4), "여가·오락": (10, -14), "생활서비스": (10, -12), "의료": (10, -10),
               "교육": (-44, 8), "식료품": (12, -14)}
    for name, row in g.iterrows():
        ax.annotate(name, (row["개업률"], row["폐업률"]), xytext=offsets.get(name, (8, 4)),
                    textcoords="offset points", fontsize=12, color=INK, path_effects=HALO)
    ax.set_xlim(0, lim); ax.set_ylim(0, lim); hgrid(ax, "both")
    ax.set_xlabel("개업률 (%, 분기 평균)"); ax.set_ylabel("폐업률 (%, 분기 평균)")
    lg = ax.legend(loc="lower right", frameon=False, fontsize=12)
    for h_ in getattr(lg, "legend_handles", None) or lg.legendHandles:
        h_.set_sizes([90])
    ax.set_title("의료·생활서비스·여가·숙박만 가게가 늘었어요")
    subtitle(ax, "점 크기 = 점포 수 · 개업·폐업 점포 수 합 ÷ 분기 평균 점포 수 ÷ 4")
    save(fig, "08_group_open_close.png")


def fig_quarter_change():
    qq = trade.groupby(["공통그룹", Q])["당월_매출_금액"].sum().unstack()
    ch = ((qq[20254] / qq[20251] - 1) * 100).sort_values()
    fig, ax = plt.subplots(figsize=(12, 7))
    cols = [BLUE if v >= 0 else GRAY for v in ch.values]
    ax.barh(range(len(ch)), ch.values, color=cols, height=0.62)
    for i, v in enumerate(ch.values):
        ax.text(v + (0.5 if v >= 0 else -0.5), i, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right",
                fontsize=12, color=INK)
    ax.axvline(0, color=AXIS, lw=1.2)
    ax.set_yticks(range(len(ch))); ax.set_yticklabels(ch.index, fontsize=13, color=INK)
    ax.set_xlim(ch.min() - 6, ch.max() + 6); hgrid(ax, "x")
    ax.set_xlabel("상권 매출 변화 (2025년 1분기 → 4분기, %)")
    ax.set_title("1분기 → 4분기, 의류·잡화 매출이 가장 많이 늘었어요")
    subtitle(ax, "1년치 데이터라 계절 효과일 수 있어요 (4분기 = 겨울옷·연말)")
    save(fig, "09_group_quarter_change.png")


# ── 10. 소비 갭 맛보기, 이름표와 함께 ───────────────────────────
def gap_model():
    m = master.set_index(K)
    d = pd.DataFrame({
        "지출": YEAR["지출_총금액"],
        "상주": m["총_상주인구_수"], "직장": m["총_직장_인구_수"],
        "유동": panel.groupby(K)["총_유동인구_수"].mean(), "집객": m["집객시설_수"],
    }).dropna()
    X = np.column_stack([np.ones(len(d))] + [np.log1p(d[c]) for c in ["상주", "직장", "유동", "집객"]])
    y = np.log(d["지출"])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    out = pd.DataFrame({"실제": d["지출"], "기대": np.exp(pred)})
    out["실제/기대"] = out["실제"] / out["기대"]
    return out, r2


def fig_gap():
    g, r2 = gap_model()
    f = FLAG.reindex(g.index)
    fig, ax = plt.subplots(figsize=(11, 8.4))
    ax.scatter(g.loc[~f, "기대"] / 1e8, g.loc[~f, "실제"] / 1e8, s=34, color=BLUE, alpha=0.6,
               edgecolor=SURFACE, linewidth=1, label="나머지 동")
    ax.scatter(g.loc[f, "기대"] / 1e8, g.loc[f, "실제"] / 1e8, s=110, color=ORANGE, edgecolor=SURFACE,
               linewidth=2, label="소비_이상치", zorder=3)
    offsets = {"소공동": (10, 2), "을지로동": (-100, 14), "서초2동": (10, 8), "구로3동": (-112, -6), "문래동": (10, -12)}
    for code in g[f].index:
        ax.annotate(f"{NAME[code]} ×{g.loc[code, '실제/기대']:.0f}", (g.loc[code, "기대"] / 1e8, g.loc[code, "실제"] / 1e8),
                    xytext=offsets.get(NAME[code], (8, 4)), textcoords="offset points", fontsize=11, color=INK,
                    path_effects=HALO)
    lo = min(g["기대"].min(), g["실제"].min()) / 1e8 * 0.7
    hi = max(g["기대"].max(), g["실제"].max()) / 1e8 * 1.4
    ax.plot([lo, hi], [lo, hi], color=INK2, lw=1.2)
    ax.text(lo * 2.2, lo * 1.3, "실제 = 기대", color=INK2, fontsize=11, rotation=45)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); hgrid(ax, "both")
    plain_log(ax)
    ax.set_xlabel("기대 지출 (억 원, 로그)"); ax.set_ylabel("실제 지출 (억 원, 로그)")
    ax.legend(loc="upper left", frameon=False, fontsize=12)
    ax.set_title("선 위로 멀리 떨어진 점 = 기대보다 훨씬 많이 쓴 동")
    subtitle(ax, f"간단한 로그 회귀(상주·직장·유동인구·집객시설, R²={r2:.2f}) · 이상치도 빼지 않고 이름표로 구분")
    save(fig, "10_gap_with_tags.png")
    top = g.sort_values("실제/기대", ascending=False).head(10)
    print("gap top10:", [(NAME[c], round(v, 1), bool(FLAG[c])) for c, v in top["실제/기대"].items()], "R2", round(r2, 3))


if __name__ == "__main__":
    for fn in [fig_tables, fig_hist, fig_map, fig_slope, fig_rho, fig_eatout, fig_sales_stores,
               fig_open_close, fig_quarter_change, fig_gap]:
        fn()
