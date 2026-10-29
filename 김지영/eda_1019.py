"""2026-10-19 EDA: 공통그룹 · 소비_이상치 열을 붙인 분석용 보기로 재계산하고 그림을 만든다.

실행: python3 김지영/eda_1019.py   (저장소 루트에서, pandas·numpy·matplotlib 필요)
입력: data/processed/ 공용 표 4개 (먼저 scripts/build_processed_2025.py 실행)
결과: 표는 stdout, 그림은 김지영/eda_1019_figures/*.png  ->  김지영/eda_1019.md 에서 사용
원본·공용 파일은 바꾸지 않는다. 열 붙이기와 매출 결측 복원은 메모리에서만 한다.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = Path(__file__).resolve().parent / "eda_1019_figures"
K, Q, FLAG = "행정동_코드", "기준_년분기_코드", "소비_이상치"
SALES = "당월_매출_금액"
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", None)

# ── 스타일 (eda_processed_2025.py 와 같음) ─────────────────────────
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, GRAY = "#e1e0d9", "#c3c2b7", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"   # 주황 = 소비_이상치(표시 동)에만 쓴다
plt.rcParams.update({
    "font.family": "AppleGothic", "axes.unicode_minus": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": False, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 13, "axes.titlesize": 19, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "axes.titlelocation": "left", "axes.titlepad": 16,
})
SHARED = ["여가·오락", "외식", "의료", "생활용품", "식료품", "의류·잡화", "생활서비스", "유흥", "교육", "교통"]


def read(name):
    return pd.read_csv(PROC / name, encoding="utf-8-sig", low_memory=False)


def show(title, data):
    print("\n### " + title)
    if isinstance(data, (pd.DataFrame, pd.Series)):
        print(data.to_string(float_format=lambda x: f"{x:,.3f}"))
    else:
        print(data)


def flag_cols(df, prefix=""):
    """소비_이상치 False/True 열 이름을 읽기 쉽게 바꾼다."""
    return df.rename(columns={False: prefix + "비표시", True: prefix + "표시"})


def save(fig, name):
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    print("saved", name)


def subtitle(ax, text):
    ax.set_title(ax.get_title(loc="left"), loc="left", pad=38)
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK2, fontsize=13, va="bottom")


def hgrid(ax, axis="x"):
    ax.grid(True, axis=axis)
    ax.set_axisbelow(True)


# ── 분석용 보기: 공통그룹 + 소비_이상치 열 붙이기 ───────────────────
def build_views():
    master, panel, trade, mapping = (read(f) for f in
                                     ["행정동_마스터.csv", "행정동_분기.csv", "상권_업종_분기.csv", "업종_공통그룹.csv"])
    flags = master[[K, "행정동_명", FLAG, "소비_최대항목", "소비_최대항목_비중"]]

    # 상권 × 업종 × 분기: 공통그룹은 이미 있음, 소비_이상치를 동 코드로 붙인다
    trade_v = trade.merge(flags[[K, FLAG]], on=K, how="left", validate="many_to_one")

    # 소비 10개 항목을 세로로 펴고 공통그룹·소비_이상치를 붙인다
    items = mapping[mapping["원본출처"] == "소비_항목"]
    cons_v = (panel.melt(id_vars=[K, Q], value_vars=list(items["원본코드"]), var_name="원본코드", value_name="지출")
                   .merge(items[["원본코드", "원본분류", "공통그룹"]], on="원본코드", how="left", validate="many_to_one")
                   .merge(flags[[K, FLAG]], on=K, how="left", validate="many_to_one"))

    # 동 × 분기: 소비_이상치를 붙이고, 매출이 전부 결측인 칸은 0이 아니라 NaN으로 다시 모은다
    observed = trade.groupby([K, Q])[SALES].sum(min_count=1).rename("상권_매출_금액_관측").reset_index()
    panel_v = (panel.merge(flags[[K, FLAG]], on=K, how="left", validate="many_to_one")
                    .merge(observed, on=[K, Q], how="left", validate="one_to_one"))

    checks = {
        "trade_v 행": len(trade_v), "trade_v 이상치 결측": int(trade_v[FLAG].isna().sum()),
        "cons_v 행": len(cons_v), "cons_v 공통그룹 결측": int(cons_v["공통그룹"].isna().sum()),
        "panel_v 행": len(panel_v),
        "공용 표에서 0이지만 실제로는 매출 미관측인 동·분기": int(((panel_v["상권_매출_금액"] == 0)
                                                  & panel_v["상권_매출_금액_관측"].isna()).sum()),
    }
    assert checks["trade_v 이상치 결측"] == 0 and checks["cons_v 공통그룹 결측"] == 0
    assert len(cons_v) == len(panel) * len(items)
    return master.set_index(K), panel_v, trade_v, cons_v, checks


# ── 표 계산 ─────────────────────────────────────────────────────
def compute(master, panel_v, trade_v, cons_v):
    flag = master[FLAG]
    r = {}

    # 1. 소비: 공통그룹 × 소비_이상치
    c = flag_cols(cons_v.groupby(["공통그룹", FLAG])["지출"].sum().unstack()) / 1e12
    c["합계"] = c.sum(axis=1)
    c["표시동_몫%"] = c["표시"] / c["합계"] * 100
    c["비표시_구성%"] = c["비표시"] / c["비표시"].sum() * 100
    c["표시_구성%"] = c["표시"] / c["표시"].sum() * 100
    year_c = cons_v.groupby([K, "공통그룹"])["지출"].sum().unstack()
    share = year_c.div(year_c.sum(axis=1), axis=0) * 100
    c["비표시_동중앙값%"] = share[~flag.reindex(share.index)].median()
    c["표시_동중앙값%"] = share[flag.reindex(share.index)].median()
    r["cons"] = c.sort_values("합계", ascending=False)

    # 2. 상권 매출·점포 (관측된 매출만, min_count=1)
    s = flag_cols(trade_v.groupby(["공통그룹", FLAG])[SALES].sum(min_count=1).unstack()) / 1e12
    s["합계"] = s.sum(axis=1)
    s["표시동_몫%"] = s["표시"] / s["합계"] * 100
    s["비표시_구성%"] = s["비표시"] / s["비표시"].sum() * 100
    s["표시_구성%"] = s["표시"] / s["표시"].sum() * 100
    obs = trade_v.assign(관측=trade_v[SALES].notna()).groupby(["공통그룹", FLAG])["관측"].mean().unstack() * 100
    s = s.join(flag_cols(obs, "관측률_"))
    q4 = trade_v[trade_v[Q] == 20254]
    stores = flag_cols(q4.groupby(["공통그룹", FLAG])["전체_점포_수"].sum().unstack())
    r["sales"] = s.join((stores / stores.sum() * 100).add_prefix("점포구성%_")).sort_values("합계", ascending=False)
    r["flag_share"] = {
        "지출": c["표시"].sum() / c["합계"].sum() * 100,
        "상권 매출": s["표시"].sum() / s["합계"].sum() * 100,
        "점포 (4분기)": q4.loc[q4[FLAG], "전체_점포_수"].sum() / q4["전체_점포_수"].sum() * 100,
    }

    # 3. 같은 그룹끼리 동 순위 상관 (전체 / 비표시 동만 따로)
    year_s = trade_v.groupby([K, "공통그룹"])[SALES].sum(min_count=1).unstack()
    rows = []
    for g in year_c.columns:
        d = pd.concat([year_c[g], year_s[g]], axis=1, keys=["c", "s"]).dropna()
        nf = d[~flag.reindex(d.index)]
        rows.append([g, len(d), d["c"].corr(d["s"], method="spearman"), len(nf), nf["c"].corr(nf["s"], method="spearman")])
    r["rho"] = (pd.DataFrame(rows, columns=["공통그룹", "동수", "rho_전체", "동수_비표시", "rho_비표시"])
                  .set_index("공통그룹").sort_values("rho_전체", ascending=False))

    # 4. 1분기 → 4분기 변화 (%)
    cq = cons_v.groupby(["공통그룹", FLAG, Q])["지출"].sum().unstack()
    sq = trade_v.groupby(["공통그룹", FLAG, Q])[SALES].sum(min_count=1).unstack()
    r["change"] = flag_cols(((cq[20254] / cq[20251] - 1) * 100).unstack(), "소비_").join(
        flag_cols(((sq[20254] / sq[20251] - 1) * 100).unstack(), "매출_"), how="outer")

    # 5. 개업·폐업률 (분기 합 ÷ 점포-분기 합)
    oc = trade_v.groupby(["공통그룹", FLAG])[["전체_점포_수", "개업_점포_수", "폐업_점포_수"]].sum()
    r["rates"] = pd.DataFrame({"개업률": oc["개업_점포_수"] / oc["전체_점포_수"] * 100,
                               "폐업률": oc["폐업_점포_수"] / oc["전체_점포_수"] * 100}).unstack()
    tot = trade_v.groupby(FLAG)[["전체_점포_수", "개업_점포_수", "폐업_점포_수"]].sum()
    r["rates_total"] = tot[["개업_점포_수", "폐업_점포_수"]].div(tot["전체_점포_수"], axis=0) * 100

    # 6. 공통그룹별 소비 갭 (eda_1017 과 같은 4개 변수 로그 회귀, 학습 R²)
    X0 = pd.DataFrame({"상주": master["총_상주인구_수"], "직장": master["총_직장_인구_수"],
                       "유동": panel_v.groupby(K)["총_유동인구_수"].mean(), "집객": master["집객시설_수"]})
    rows, ratios = [], {}
    for g in list(year_c.columns) + ["전체"]:
        y = year_c.sum(axis=1) if g == "전체" else year_c[g]
        d = X0.join(y.rename("y")).dropna()
        nonpos = int((d["y"] <= 0).sum())
        d = d[d["y"] > 0]
        A = np.column_stack([np.ones(len(d))] + [np.log1p(d[col]) for col in X0.columns])
        t = np.log(d["y"])
        e = t - A @ np.linalg.lstsq(A, t, rcond=None)[0]
        ratio = pd.Series(np.exp(e), index=d.index).sort_values(ascending=False)
        ratios[g] = ratio
        rows.append([g, len(d), nonpos, 1 - (e ** 2).sum() / ((t - t.mean()) ** 2).sum(),
                     int(flag.reindex(ratio.index[:10]).sum())])
    r["gap"] = pd.DataFrame(rows, columns=["대상", "동수", "0이하_제외", "학습R2", "TOP10중_표시동"]).set_index("대상")
    r["gap_ratio"] = ratios
    return r


def print_tables(r, master, trade_v, cons_v, checks):
    name, flag = master["행정동_명"], master[FLAG]
    show("보기 점검", checks)
    show("이상치 동의 상권", {"상권 수": trade_v.loc[trade_v[FLAG], "상권_코드"].nunique(),
                         "전체 상권": trade_v["상권_코드"].nunique()})
    show("음수 지출 (공통그룹 표시)", cons_v[cons_v["지출"] < 0].merge(master[["행정동_명"]], left_on=K, right_index=True))
    cg = trade_v.groupby([K, Q, "공통그룹"])[SALES].count()
    show("매출이 전부 결측인 동·분기·그룹 조합", int((cg == 0).sum()))
    show("소비 (조 원, %) 공통그룹 × 소비_이상치", r["cons"])
    show("상권 매출 (조 원, %) 공통그룹 × 소비_이상치", r["sales"])
    show("표시동 몫 요약", r["flag_share"])
    show("같은 그룹 순위 상관", r["rho"])
    show("Q1→Q4 변화 (%)", r["change"])
    show("개업·폐업률 (%)", r["rates"])
    show("개업·폐업률 합계 (%)", r["rates_total"])
    show("공통그룹별 갭 모델", r["gap"])
    show("공통그룹별 갭 TOP5", pd.Series({
        g: ", ".join(f"{name[i]} ×{v:.1f}{'(표시)' if flag[i] else ''}" for i, v in ratio.head(5).items())
        for g, ratio in r["gap_ratio"].items()}))


# ── 그림 ────────────────────────────────────────────────────────
def fig_columns(checks):
    cards = [
        ("상권_업종_분기", f"{checks['trade_v 행']:,}행", ["상권_코드", "업종", "매출", "점포"], True, "원래 있음"),
        ("소비 보기", f"{checks['cons_v 행']:,}행", ["행정동_코드", "분기", "항목", "지출"], True, "새로 붙임"),
        ("행정동_분기", f"{checks['panel_v 행']:,}행", ["행정동_코드", "분기", "소비", "상권 매출"], False, ""),
    ]
    fig, ax = plt.subplots(figsize=(13, 5.6))
    ax.set_xlim(0, 13); ax.set_ylim(0, 5.2); ax.axis("off")
    for i, (title, n, cols, has_group, group_note) in enumerate(cards):
        x = 0.2 + i * 4.3
        ax.add_patch(FancyBboxPatch((x, 0.5), 4.0, 3.9, boxstyle="round,pad=0,rounding_size=0.15",
                                    fc="white", ec=AXIS, lw=1.2))
        ax.text(x + 0.25, 3.95, title, fontsize=16, weight="bold", color=INK, va="center")
        ax.text(x + 3.75, 3.95, n, fontsize=12, color=INK2, va="center", ha="right")
        for j, col in enumerate(cols):
            ax.add_patch(FancyBboxPatch((x + 0.25, 3.15 - j * 0.42), 3.5, 0.32, boxstyle="round,pad=0,rounding_size=0.06",
                                        fc=GRID, ec="none"))
            ax.text(x + 0.4, 3.31 - j * 0.42, col, fontsize=11, color=INK2, va="center")
        y = 1.3
        if has_group:
            ax.add_patch(FancyBboxPatch((x + 0.25, y), 3.5, 0.36, boxstyle="round,pad=0,rounding_size=0.06", fc=BLUE, ec="none"))
            ax.text(x + 0.4, y + 0.18, "공통그룹", fontsize=12, color="white", weight="bold", va="center")
            ax.text(x + 3.6, y + 0.18, group_note, fontsize=10, color="white", va="center", ha="right")
        ax.add_patch(FancyBboxPatch((x + 0.25, 0.75), 3.5, 0.36, boxstyle="round,pad=0,rounding_size=0.06", fc=ORANGE, ec="none"))
        ax.text(x + 0.4, 0.93, "소비_이상치", fontsize=12, color="white", weight="bold", va="center")
        ax.text(x + 3.6, 0.93, "새로 붙임", fontsize=10, color="white", va="center", ha="right")
    ax.set_title("표 3개에 같은 열 두 개를 붙였어요")
    subtitle(ax, "파랑 = 업종·소비 항목을 묶은 12개 그룹 · 주황 = 한 항목이 90% 넘는 동 8곳의 이름표")
    save(fig, "01_two_columns.png")


def fig_flag_share(r):
    d = r["flag_share"]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    for i, (label, v) in enumerate(list(d.items())[::-1]):
        ax.barh(i, v, color=ORANGE, height=0.55)
        ax.barh(i, 100 - v, left=v + 0.4, color=GRAY, height=0.55)
        ax.text(v + 1.2 if v < 20 else v / 2, i, f"8곳 {v:.1f}%", va="center", ha="left" if v < 20 else "center",
                fontsize=13, weight="bold", color=INK if v < 20 else "white")
        ax.text(99, i, f"나머지 417곳 {100 - v:.1f}%", va="center", ha="right", fontsize=12, color=INK)
    ax.set_yticks(range(len(d))); ax.set_yticklabels(list(d)[::-1], fontsize=14, color=INK)
    ax.set_xlim(0, 100); ax.set_xticks([]); ax.spines["bottom"].set_visible(False)
    ax.set_title("이름표 동 8곳: 지출은 절반, 가게 매출은 7%")
    subtitle(ax, "같은 8곳인데 무엇으로 재느냐에 따라 몫이 크게 달라요 · 2025년")
    save(fig, "02_flag_share.png")


def fig_flag_mix(r):
    c, s = r["cons"]["표시_구성%"], r["sales"]["표시_구성%"]
    groups = SHARED
    y = np.arange(len(groups))[::-1]; h = 0.38
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.barh(y + h / 2 + 0.02, [c[g] for g in groups], height=h, color=BLUE, label="지출 (소비 데이터)")
    ax.barh(y - h / 2 - 0.02, [s[g] for g in groups], height=h, color=AQUA, label="동네 가게 매출 (상권 데이터)")
    for yi, g in zip(y, groups):
        ax.text(c[g] + 0.8, yi + h / 2 + 0.02, f"{c[g]:.1f}%", va="center", fontsize=10.5, color=INK)
        ax.text(s[g] + 0.8, yi - h / 2 - 0.02, f"{s[g]:.1f}%", va="center", fontsize=10.5, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels(groups, fontsize=13, color=INK)
    ax.set_xlim(0, 105); ax.set_xlabel("이름표 동 8곳 안에서의 구성 비중 (%)"); hgrid(ax)
    ax.legend(loc="lower right", frameon=False, fontsize=12)
    ax.set_title("같은 8곳, 다른 지갑: 지출은 여가·오락, 가게 매출은 외식·의료")
    subtitle(ax, "여가·오락이 지출에서는 93.6%인데, 같은 동 가게 매출에서는 1.7%예요")
    save(fig, "03_flag_mix.png")


def fig_share_by_group(r):
    v = r["cons"]["표시동_몫%"].reindex(SHARED).sort_values()
    fig, ax = plt.subplots(figsize=(12, 6.6))
    ax.barh(range(len(v)), v.values, color=ORANGE, height=0.6)
    ax.barh(range(len(v)), 100 - v.values, left=v.values + 0.4, color=GRAY, height=0.6)
    for i, val in enumerate(v.values):
        ax.text(val + 1.2, i, f"{val:.1f}%", va="center", fontsize=12, color=INK, weight="bold" if val > 10 else "normal")
    ax.set_yticks(range(len(v))); ax.set_yticklabels(v.index, fontsize=13, color=INK)
    ax.set_xlim(0, 100); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels(["0", "25", "50", "75", "100%"])
    ax.set_title("그룹마다 이름표 동의 몫이 달라요")
    subtitle(ax, "각 소비 그룹의 서울 합계 중 이름표 동 8곳(주황)이 차지하는 몫 · 여가·오락·식료품·생활서비스만 10%를 넘어요")
    save(fig, "04_flag_share_by_group.png")


def fig_rho(r):
    d = r["rho"].sort_values("rho_전체")
    fig, ax = plt.subplots(figsize=(12, 6.8))
    y = np.arange(len(d))
    ax.hlines(y, d[["rho_전체", "rho_비표시"]].min(axis=1), d[["rho_전체", "rho_비표시"]].max(axis=1), color=AXIS, lw=2)
    ax.scatter(d["rho_비표시"], y, s=120, facecolor=SURFACE, edgecolor=MUTED, linewidth=2, zorder=3, label="이름표 동을 나눠서 (비표시 동만)")
    ax.scatter(d["rho_전체"], y, s=90, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=4, label="전체")
    for yi, (g, row) in zip(y, d.iterrows()):
        ax.text(max(row["rho_전체"], row["rho_비표시"]) + 0.02, yi, f"{row['rho_전체']:.2f}", va="center", fontsize=12, color=INK)
    ax.set_yticks(y); ax.set_yticklabels(d.index, fontsize=13, color=INK)
    ax.set_xlim(0, 1); hgrid(ax)
    ax.set_xlabel("같은 그룹의 동별 '지출'과 '가게 매출' 순위 상관 (Spearman ρ)")
    ax.legend(loc="lower right", frameon=False, fontsize=12)
    ax.set_title("이름표 동을 나눠 봐도 순위 상관은 거의 그대로예요")
    subtitle(ax, "두 점이 거의 겹쳐요 · 교통은 두 데이터가 담는 범위가 달라 0.2로 낮아요")
    save(fig, "05_rank_corr.png")


def fig_change(r):
    groups = ["의류·잡화", "교통", "외식", "여가·오락", "의료", "교육"]
    ch = r["change"].reindex(groups)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.4), sharey=True, gridspec_kw=dict(wspace=0.08))
    y = np.arange(len(groups))[::-1]; h = 0.36
    for ax, (prefix, title) in zip(axes, [("소비_", "지출 (소비 데이터)"), ("매출_", "동네 가게 매출 (상권 데이터)")]):
        a, b = ch[prefix + "비표시"], ch[prefix + "표시"]
        ax.barh(y + h / 2 + 0.02, a, height=h, color=BLUE, label="나머지 417곳")
        ax.barh(y - h / 2 - 0.02, b, height=h, color=ORANGE, label="이름표 동 8곳")
        for yi, va, vb in zip(y, a, b):
            for val, off in [(va, h / 2 + 0.02), (vb, -h / 2 - 0.02)]:
                ax.text(val + (0.8 if val >= 0 else -0.8), yi + off, f"{val:+.0f}%", va="center",
                        ha="left" if val >= 0 else "right", fontsize=10.5, color=INK)
        ax.axvline(0, color=AXIS, lw=1.2); hgrid(ax)
        ax.set_xlim(-22, 45); ax.set_title(title, fontsize=15)
    axes[0].set_yticks(y); axes[0].set_yticklabels(groups, fontsize=13, color=INK)
    axes[1].legend(loc="lower right", frameon=False, fontsize=12)
    fig.suptitle("1분기 → 4분기: 이름표 동의 여가·오락은 지출 +17%, 가게 매출 -5%",
                 x=0.125, ha="left", fontsize=19, weight="bold", color=INK, y=1.03)
    save(fig, "06_quarter_change.png")


def fig_turnover(r):
    rt = r["rates"]
    net = pd.DataFrame({f: rt[("개업률", f)] - rt[("폐업률", f)] for f in [False, True]}).sort_values(False)
    fig, ax = plt.subplots(figsize=(12, 7.4))
    y = np.arange(len(net))
    ax.hlines(y, net.min(axis=1), net.max(axis=1), color=AXIS, lw=2)
    ax.scatter(net[False], y, s=100, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3, label="나머지 417곳의 상권")
    ax.scatter(net[True], y, s=100, color=ORANGE, edgecolor=SURFACE, linewidth=2, zorder=4, label="이름표 동 8곳의 상권 (32곳)")
    ax.axvline(0, color=INK2, lw=1.2)
    ax.text(0.08, len(net) - 0.4, "열리는 가게가 더 많음 →", fontsize=11, color=INK2)
    ax.text(-0.08, len(net) - 0.4, "← 닫히는 가게가 더 많음", fontsize=11, color=INK2, ha="right")
    ax.set_yticks(y); ax.set_yticklabels(net.index, fontsize=13, color=INK)
    ax.set_ylim(-0.7, len(net) + 0.2); hgrid(ax)
    ax.set_xlabel("개업률 - 폐업률 (%p, 분기 평균)")
    ax.legend(loc="upper left", frameon=False, fontsize=12)
    tot = r["rates_total"]
    ax.set_title("이름표 동 상권도 대부분 닫히는 가게가 더 많아요")
    subtitle(ax, f"62개 업종 전체: 나머지 {tot.loc[False, '개업_점포_수']:.2f}% 열림 / {tot.loc[False, '폐업_점포_수']:.2f}% 닫힘, "
                 f"이름표 동 {tot.loc[True, '개업_점포_수']:.2f}% / {tot.loc[True, '폐업_점포_수']:.2f}%")
    save(fig, "07_turnover.png")


def fig_gap_r2(r):
    g = r["gap"].drop("전체").sort_values("학습R2")
    total = r["gap"].loc["전체"]
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.barh(range(len(g)), g["학습R2"], color=BLUE, height=0.6)
    for i, (name, row) in enumerate(g.iterrows()):
        ax.text(row["학습R2"] + 0.01, i, f"{row['학습R2']:.2f}", va="center", fontsize=12, color=INK)
        n = int(row["TOP10중_표시동"])
        ax.scatter(0.80, i, s=150 if n else 60, color=ORANGE if n else GRID, zorder=3)
        ax.text(0.83, i, f"이름표 {n}곳" if n else "이름표 없음", va="center", fontsize=12, color=INK)
    ax.axvline(total["학습R2"], color=INK2, lw=1.2)
    ax.text(total["학습R2"] + 0.008, -0.75, f"전체 지출 {total['학습R2']:.2f} (TOP10 중 이름표 {int(total['TOP10중_표시동'])}곳)",
            fontsize=10.5, color=INK2, va="center")
    ax.set_ylim(-1.1, len(g) + 0.3)
    ax.set_yticks(range(len(g))); ax.set_yticklabels(g.index, fontsize=13, color=INK)
    ax.set_xlim(0, 0.98); ax.set_xticks([0, 0.2, 0.4, 0.6]); hgrid(ax)
    ax.set_xlabel("모델 설명력 (학습 R², 로그 회귀)")
    ax.text(0.80, len(g) - 0.1, "갭 TOP10 안의", fontsize=11, color=INK2, ha="center")
    ax.set_title("그룹별 소비 갭: 외식이 가장 잘 맞아요")
    subtitle(ax, "상주·직장·유동인구·집객시설로 그룹별 '기대 지출'을 만든 결과 · 오른쪽은 갭 상위 10곳 중 이름표 동 수")
    save(fig, "08_group_gap_r2.png")


def fig_gap_top(r, master):
    name, flag = master["행정동_명"], master[FLAG]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.6), gridspec_kw=dict(wspace=0.45))
    for ax, (g, title) in zip(axes, [("전체", "전체 지출로 잰 갭"), ("외식", "외식(음식) 지출로 잰 갭")]):
        top = r["gap_ratio"][g].head(10)[::-1]
        cols = [ORANGE if flag[i] else BLUE for i in top.index]
        ax.barh(range(len(top)), top.values, color=cols, height=0.62)
        for i, v in enumerate(top.values):
            ax.text(v * 1.02, i, f"×{v:.1f}" if v < 10 else f"×{v:.0f}", va="center", fontsize=11.5, color=INK)
        ax.set_yticks(range(len(top))); ax.set_yticklabels([name[i] for i in top.index], fontsize=12.5, color=INK)
        ax.set_xlim(0, top.max() * 1.22); ax.set_xticks([]); ax.spines["bottom"].set_visible(False)
        ax.set_title(title, fontsize=15)
    axes[0].barh([0], [0], color=ORANGE, label="이름표 동"); axes[0].barh([0], [0], color=BLUE, label="그 밖의 동")
    axes[0].legend(loc="lower right", frameon=False, fontsize=11)
    fig.suptitle("갭 TOP10: 전체 지출은 이름표 동이 절반, 외식은 한 곳도 없어요",
                 x=0.125, ha="left", fontsize=19, weight="bold", color=INK, y=1.08)
    fig.text(0.125, 1.005, "실제 지출 ÷ 모델 기준값 · 막대 길이는 두 그림이 서로 다른 눈금이에요", fontsize=13, color=INK2)
    save(fig, "09_gap_top10.png")


def main():
    OUT.mkdir(exist_ok=True)
    master, panel_v, trade_v, cons_v, checks = build_views()
    r = compute(master, panel_v, trade_v, cons_v)
    print_tables(r, master, trade_v, cons_v, checks)
    fig_columns(checks)
    fig_flag_share(r)
    fig_flag_mix(r)
    fig_share_by_group(r)
    fig_rho(r)
    fig_change(r)
    fig_turnover(r)
    fig_gap_r2(r)
    fig_gap_top(r, master)


if __name__ == "__main__":
    main()
