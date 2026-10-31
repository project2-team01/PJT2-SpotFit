"""SpotFit 동네별 상권 EDA: 서울 행정동의 특징으로 동네 유형을 나누고, 유형마다 상권이 어떻게 다른지 본다.

동네 특징(인구·연령·1인가구·집값·시설·유동 패턴) → 동네 유형 5가지(K-평균 군집)
→ 유형별 상권 구성, 상권 MBTI, 업종, 매출 시간대·연령, 개업·폐업, 소비 잠재력.
그래프는 이승희/eda_figures/ 에, 요약표는 이승희/eda_tables/ 에 저장한다. 보고서: 이승희/SpotFit_EDA_보고서.md (10장)

실행: uv run --no-project --with pandas,matplotlib,openpyxl,scikit-learn python 이승희/eda_dong_2025.py   (저장소 루트에서)
"""
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch, Polygon
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from eda_raw_2025 import (BLUE, DIV_CMAP, GRAY, INK, INK2, LIGHT_GRAY, MBTI_NAME, MBTI_ORDER, ORANGE, RAW_DIR,
                       TRADE_TYPES, bar_labels, build_axes, caption, load_trade, potential_table, read, save,
                       save_table, setup_style)

SEQ_CMAP = LinearSegmentedColormap.from_list("seq_blue", ["#f4f8fd", "#9ec5f4", "#3987e5", "#184f95", "#0d366b"])
# 상권 종류 4개에 쓰는 범주 색 (검증된 기본 팔레트 1~4번 순서)
TRADE_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]

FEATURES = {
    "인구밀도": "인구 밀도",
    "직장_상주": "일하는 사람 ÷ 사는 사람",
    "2030_비중": "20·30대 비중",
    "60이상_비중": "60대 이상 비중",
    "1인가구_비율": "1인가구 비율",
    "아파트_시세": "아파트 시세",
    "집객시설_밀도": "집객시설 밀도",
    "야간_유동비": "밤 유동인구 (낮 대비)",
    "주말_유동비": "주말 유동인구 (평일 대비)",
}
LOG_FEATURES = ["인구밀도", "직장_상주", "아파트_시세", "집객시설_밀도"]
N_TYPES = 5
DONG_ORDER = ["도심 업무지구", "청년·1인가구 동네", "고가 아파트 가족 동네", "어르신 많은 주거지", "한적한 외곽 주거지"]
KEY = ["행정동_코드", "행정동_코드_명"]


# ================================================================ 동네 특징

def load_geo():
    """행정동 경계와 코드 대응표 (상권분석 8자리 코드 ↔ SKT 생활데이터 7자리 코드)."""
    g = json.loads((RAW_DIR / "geo" / "HangJeongDong_ver20251231.geojson").read_text(encoding="utf-8"))
    shapes, rows = [], []
    for f in g["features"]:
        p = f["properties"]
        if p["sido"] != "11":
            continue
        code = int(p["adm_cd2"][:8])
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        shapes.append((code, [np.array(poly[0]) for poly in polys]))
        rows.append({"행정동_코드": code, "SKT_코드": int(p["adm_cd"][:7]), "자치구": p["sggnm"]})
    return shapes, pd.DataFrame(rows).drop_duplicates("행정동_코드").set_index("행정동_코드")


def build_dong_features(codes):
    res = read(RAW_DIR / "OA-22183_상주인구_행정동.csv").groupby(KEY).mean(numeric_only=True)
    wrk = read(RAW_DIR / "OA-22184_직장인구_행정동.csv").groupby(KEY)["총_직장_인구_수"].mean()
    flw = read(RAW_DIR / "OA-22178_길단위인구_행정동.csv").groupby(KEY).sum(numeric_only=True)
    fac = read(RAW_DIR / "OA-22169_집객시설_행정동.csv").fillna(0).groupby(KEY).mean(numeric_only=True)
    apt = read(RAW_DIR / "OA-22163_아파트_행정동.csv").fillna(0).groupby(KEY).mean(numeric_only=True)
    area = read(RAW_DIR / "OA-22160_영역_행정동.csv").set_index("행정동_코드")["영역_면적"] / 1e6

    d = pd.DataFrame(index=res.index)
    code = d.index.get_level_values(0)
    km2 = area.reindex(code).values
    d["상주인구"] = res["총_상주인구_수"]
    d["인구밀도"] = res["총_상주인구_수"] / km2
    d["직장_상주"] = wrk.reindex(d.index) / res["총_상주인구_수"]
    d["2030_비중"] = (res["연령대_20_상주인구_수"] + res["연령대_30_상주인구_수"]) / res["총_상주인구_수"] * 100
    d["60이상_비중"] = res["연령대_60_이상_상주인구_수"] / res["총_상주인구_수"] * 100
    # 아파트 비율은 쓰지 않는다: 상주인구 파일의 아파트_가구_수는 모두 0이고, 아파트 파일의 세대 수는 실제보다 크게 적다
    d["아파트_시세"] = apt["아파트_평균_시가"].reindex(d.index).replace(0, np.nan)
    d["집객시설_밀도"] = fac["집객시설_수"] / km2
    hours = {"00_06": 6, "06_11": 5, "11_14": 3, "14_17": 3, "17_21": 4, "21_24": 3}
    per_hour = {k: flw[f"시간대_{k}_유동인구_수"] / h for k, h in hours.items()}
    d["야간_유동비"] = (per_hour["21_24"] + per_hour["00_06"]) / (per_hour["11_14"] + per_hour["14_17"])
    weekday = flw[[f"{x}요일_유동인구_수" for x in "월화수목금"]].sum(axis=1) / 5
    d["주말_유동비"] = (flw["토요일_유동인구_수"] + flw["일요일_유동인구_수"]) / 2 / weekday

    skt = pd.read_excel(RAW_DIR / "living" / "관심집단_2025.12.xlsx", usecols=["행정동코드", "총인구", "1인가구수"]).groupby("행정동코드").sum()
    skt_code = codes["SKT_코드"].reindex(code).values
    single = (skt["1인가구수"] / skt["총인구"] * 100)
    d["1인가구_비율"] = single.reindex(skt_code).values
    d["자치구"] = codes["자치구"].reindex(code).values
    return d.reset_index()


def cluster_dongs(d):
    X = d[list(FEATURES)].copy()
    for c in LOG_FEATURES:
        X[c] = np.log10(X[c].clip(lower=1e-3))
    missing = X.isna().sum()
    X = X.fillna(X.median())
    Z = (X - X.mean()) / X.std()
    sil = {}
    for k in range(3, 9):
        sil[k] = silhouette_score(Z, KMeans(k, n_init=20, random_state=0).fit_predict(Z))
    km = KMeans(N_TYPES, n_init=20, random_state=0).fit(Z)
    prof = Z.groupby(km.labels_).mean()

    # 군집 번호에 이름 붙이기: 가장 뚜렷한 특징 순서대로 하나씩 배정
    rules = [("도심 업무지구", "직장_상주", 1), ("한적한 외곽 주거지", "집객시설_밀도", -1),
             ("청년·1인가구 동네", "2030_비중", 1), ("고가 아파트 가족 동네", "아파트_시세", 1)]
    names, left = {}, set(prof.index)
    for name, col, sign in rules:
        best = (prof.loc[list(left), col] * sign).idxmax()
        names[best] = name
        left.remove(best)
    names[left.pop()] = "어르신 많은 주거지"
    d["동네유형"] = pd.Series(km.labels_).map(names).values
    zprof = Z.assign(동네유형=d["동네유형"].values).groupby("동네유형").mean().reindex(DONG_ORDER)
    return d, zprof, sil, missing


# ================================================================ 그림

def fig_profile(d, zprof):
    med = d.groupby("동네유형")[list(FEATURES)].median().reindex(DONG_ORDER)
    cnt = d["동네유형"].value_counts().reindex(DONG_ORDER)
    fmt = {"인구밀도": lambda v: f"{v / 1e4:.1f}만", "직장_상주": lambda v: f"{v:.2f}배", "아파트_시세": lambda v: f"{v / 1e8:.1f}억",
           "집객시설_밀도": lambda v: f"{v:.0f}", "야간_유동비": lambda v: f"{v:.2f}", "주말_유동비": lambda v: f"{v:.2f}"}
    fig, ax = plt.subplots(figsize=(13, 4.6))
    im = ax.imshow(zprof.values, cmap=DIV_CMAP, vmin=-2, vmax=2, aspect="auto")
    ax.set_xticks(range(len(FEATURES)), [v.replace(" ÷ ", "\n÷ ").replace(" (", "\n(") for v in FEATURES.values()], fontsize=9)
    ax.set_yticks(range(len(zprof)), [f"{n} ({cnt[n]}개 동)" for n in zprof.index])
    ax.grid(False)
    for i, n in enumerate(zprof.index):
        for j, c in enumerate(FEATURES):
            v = med.loc[n, c]
            txt = fmt.get(c, lambda x: f"{x:.0f}%")(v)
            ax.text(j, i, txt, ha="center", va="center", fontsize=8.5, color="white" if abs(zprof.loc[n, c]) > 1.1 else INK)
    cb = fig.colorbar(im, ax=ax, shrink=0.85, ticks=[-2, -1, 0, 1, 2])
    cb.ax.set_yticklabels(["서울 평균보다 훨씬 낮음", "낮음", "서울 평균", "높음", "훨씬 높음"])
    ax.set_title("5가지 동네 유형의 특징 (칸 안 숫자 = 유형의 중앙값)")
    caption(fig, "색 = 서울 평균과 비교한 정도(표준점수). 인구 밀도는 1km²당 사람 수, 집객시설 밀도는 1km²당 시설 수. "
                 "밤 유동인구 = (21~06시) ÷ (11~17시) 1시간당 비율. 자료: 행정동 상주·직장·길단위인구, 아파트, 집객시설, SKT 관심집단(2025년)", y=-0.06)
    save(fig, "13_동네유형_프로필.png")
    save_table(med.round(2).assign(동_수=cnt), "13_동네유형_특징_중앙값.csv")
    return med, cnt


def fig_dong_maps(d, shapes):
    typ = d.set_index("행정동_코드")["동네유형"]
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.4))
    axes.flat[-1].axis("off")
    for ax, name in zip(axes.flat, DONG_ORDER):
        patches, colors = [], []
        for code, rings in shapes:
            on = typ.get(code) == name
            for ring in rings:
                patches.append(Polygon(ring, closed=True))
                colors.append(BLUE if on else LIGHT_GRAY)
        ax.add_collection(PatchCollection(patches, facecolor=colors, edgecolor="white", linewidth=0.3))
        ax.autoscale_view()
        ax.set_aspect(1.25)
        ax.axis("off")
        ex = d[d["동네유형"] == name].nlargest(3, "상주인구")["행정동_코드_명"].tolist()
        ax.set_title(f"{name} ({(typ == name).sum()}개 동)\n예: {', '.join(ex)}", fontsize=11.5)
    fig.subplots_adjust(hspace=0.15, wspace=0.02)
    fig.suptitle("동네 유형은 서울 어디에 있을까?", x=0.01, ha="left", fontsize=15, fontweight="bold", y=0.98)
    caption(fig, "파랑 = 해당 유형의 행정동, 회색 = 나머지. 예시는 그 유형에서 사는 사람이 가장 많은 동 3곳")
    save(fig, "14_동네유형_지도.png")


def trade_by_dong(d, axes_df):
    """상권 지표에 동네 유형을 붙인다 (상권이 속한 행정동 기준)."""
    t = axes_df.merge(d[["행정동_코드", "동네유형"]], on="행정동_코드", how="left")
    return t


def fig_trade_mix(d, t):
    per = t.groupby("동네유형").size().reindex(DONG_ORDER) / (d.groupby("동네유형")["상주인구"].sum().reindex(DONG_ORDER) / 1e4)
    mix = pd.crosstab(t["동네유형"], t["상권_구분_코드_명"], normalize="index").reindex(index=DONG_ORDER, columns=TRADE_TYPES).fillna(0) * 100
    no_trade = d.groupby("동네유형").apply(lambda x: (~x["행정동_코드"].isin(t["행정동_코드"])).sum(), include_groups=False).reindex(DONG_ORDER)

    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1, 1.4]})
    ax = axes[0]
    y = np.arange(len(DONG_ORDER))
    ax.barh(y, per.values, color=BLUE, height=0.6)
    bar_labels(ax, per.values, "{:.1f}곳", horizontal=True, pad=0.05)
    ax.set_yticks(y, DONG_ORDER)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, per.max() * 1.25)
    ax.set_xlabel("사는 사람 1만 명당 상권 수")
    ax.set_title("① 상권이 얼마나 많을까?")

    ax = axes[1]
    left = np.zeros(len(DONG_ORDER))
    for k, c in zip(TRADE_TYPES, TRADE_COLORS):
        v = mix[k].values
        ax.barh(y, v, left=left, color=c, height=0.6, label=k, edgecolor="white", linewidth=1.5)
        for i, (l, w) in enumerate(zip(left, v)):
            if w >= 7:
                ax.text(l + w / 2, i, f"{w:.0f}%", ha="center", va="center", fontsize=8.5, color="white")
        left += v
    ax.set_yticks(y, [""] * len(y))
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.grid(False)
    ax.set_xlabel("상권 종류 비중 (%)")
    ax.set_title("② 어떤 종류의 상권일까?")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.14))
    caption(fig, "상권은 상권 영역 파일에 적힌 행정동 기준으로 동네 유형에 붙임. 자료: 상권 영역(OA-15560), 행정동 상주인구(OA-22183)")
    save(fig, "15_동네유형별_상권구성.png")
    save_table(mix.round(1).assign(만명당_상권수=per.round(2), 상권없는_동=no_trade), "15_동네유형별_상권구성.csv")
    return per, mix, no_trade


def fig_trade_mbti(t):
    x = t.dropna(subset=["유형", "동네유형"])
    share = pd.crosstab(x["동네유형"], x["유형"], normalize="index").reindex(index=DONG_ORDER, columns=MBTI_ORDER) * 100
    fig, ax = plt.subplots(figsize=(13, 4.8))
    im = ax.imshow(share.values, cmap=SEQ_CMAP, vmin=0, vmax=50, aspect="auto")
    ax.set_xticks(range(8), [f"{k}\n{MBTI_NAME[k]}" for k in MBTI_ORDER])
    ax.set_yticks(range(len(DONG_ORDER)), DONG_ORDER)
    ax.grid(False)
    for i in range(share.shape[0]):
        for j in range(share.shape[1]):
            v = share.values[i, j]
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=9, color="white" if v > 28 else INK)
    fig.colorbar(im, ax=ax, shrink=0.85, label="동네 유형 안 상권 비중 (%)")
    ax.set_title("동네 유형마다 어떤 상권 MBTI가 많을까? (한 줄을 더하면 100%)")
    caption(fig, "상권 MBTI는 5장(상권 3축 점수)에서 붙인 3글자 유형. 12.5%보다 크면 그 동네에 많이 몰린 상권 유형")
    save(fig, "16_동네유형별_상권MBTI.png")
    save_table(share.round(1), "16_동네유형별_상권MBTI.csv")
    return share


def fig_dong_biz(t, sales):
    s = sales.groupby(["상권_코드", "서비스_업종_코드_명"])["당월_매출_금액"].sum().reset_index()
    s = s.merge(t[["상권_코드", "동네유형"]], left_on="상권_코드", right_on="상권_코드").dropna(subset=["동네유형"])
    share = s.pivot_table(index="동네유형", columns="서비스_업종_코드_명", values="당월_매출_금액", aggfunc="sum").fillna(0)
    share = share.div(share.sum(axis=1), axis=0)
    total = s.groupby("서비스_업종_코드_명")["당월_매출_금액"].sum()
    total = total / total.sum()
    lq = (share / total).reindex(DONG_ORDER)
    pick = ["한식음식점", "일반의류", "일반의원", "의약품", "슈퍼마켓", "편의점", "반찬가게", "청과상", "육류판매",
            "일반교습학원", "커피-음료", "제과점", "분식전문점", "양식음식점", "일식음식점", "호프-간이주점", "화장품", "미용실"]
    sub = lq[pick]
    top = {n: ", ".join(f"{b}({v:.1f})" for b, v in lq.loc[n, total[total > 0.004].index].nlargest(5).items()) for n in DONG_ORDER}

    fig, ax = plt.subplots(figsize=(15, 4.8))
    im = ax.imshow(np.log2(sub.values), cmap=DIV_CMAP, vmin=-1.5, vmax=1.5, aspect="auto")
    ax.set_xticks(range(len(pick)), pick, rotation=35, ha="right")
    ax.set_yticks(range(len(DONG_ORDER)), DONG_ORDER)
    ax.grid(False)
    for i in range(sub.shape[0]):
        for j in range(sub.shape[1]):
            v = sub.values[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=8.5, color="white" if abs(np.log2(v)) > 1 else INK)
    cb = fig.colorbar(im, ax=ax, shrink=0.85, ticks=[-1.5, -1, 0, 1, 1.5])
    cb.ax.set_yticklabels(["0.35배", "0.5배", "1배 (서울 평균)", "2배", "2.8배"])
    ax.set_title("동네 유형별 업종 특화 지수: 어떤 동네에서 어떤 업종이 잘 팔릴까?")
    caption(fig, "특화 지수 = 동네 유형 안 상권에서 업종이 차지하는 매출 비중 ÷ 서울 전체 비중. 파랑(1보다 큼) = 그 동네에 몰린 업종. 자료: 추정매출(OA-15572), 2025년", y=-0.12)
    save(fig, "17_동네유형별_업종특화.png")
    save_table(lq.T.round(2), "17_동네유형별_업종_특화지수.csv")
    return sub, top


def fig_sales_pattern(t, sales):
    s = sales.merge(t[["상권_코드", "동네유형"]], on="상권_코드").dropna(subset=["동네유형"])
    g = s.groupby("동네유형")
    hours = {"00~06": 6, "06~11": 5, "11~14": 3, "14~17": 3, "17~21": 4, "21~24": 3}
    tm = pd.DataFrame({f"{k}시": g[f"시간대_{k}_매출_금액"].sum() / h for k, h in hours.items()}).reindex(DONG_ORDER)
    tm = tm.div(tm.sum(axis=1), axis=0) * 100
    ages = {"10": "10대", "20": "20대", "30": "30대", "40": "40대", "50": "50대", "60_이상": "60대+"}
    ag = pd.DataFrame({lab: g[f"연령대_{a}_매출_금액"].sum() for a, lab in ages.items()}).reindex(DONG_ORDER)
    ag = ag.div(ag.sum(axis=1), axis=0) * 100
    wk = (g["주말_매출_금액"].sum() / g["당월_매출_금액"].sum() * 100).reindex(DONG_ORDER)

    fig, axes = plt.subplots(1, 3, figsize=(18, 4.6), gridspec_kw={"width_ratios": [1.25, 1.15, 0.7]})
    for ax, df, title, vmax, thr in [(axes[0], tm, "① 시간대별 매출 비중 (1시간당, %)", 32, 12),
                                     (axes[1], ag, "② 손님 연령대별 매출 비중 (%)", 30, 12)]:
        im = ax.imshow(df.values, cmap=SEQ_CMAP, vmin=0, vmax=vmax, aspect="auto")
        ax.set_xticks(range(df.shape[1]), df.columns)
        ax.set_yticks(range(len(df)), DONG_ORDER if ax is axes[0] else [""] * len(df))
        ax.grid(False)
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                v = df.values[i, j]
                ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=8.5, color="white" if v > thr else INK)
        ax.set_title(title)
    ax = axes[2]
    y = np.arange(len(DONG_ORDER))
    ax.barh(y, wk.values, color=BLUE, height=0.6)
    ax.axvline(2 / 7 * 100, color=INK, linewidth=1)
    for i, v in enumerate(wk.values):
        ax.text(v - 0.6, i, f"{v:.1f}%", va="center", ha="right", fontsize=8.5, color="white")
    ax.set_yticks(y, [""] * len(y))
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 32)
    ax.set_xlabel("주말 매출 비중 (%), 세로선 = 28.6%")
    ax.set_title("③ 주말 매출 비중")
    caption(fig, "자료: 추정매출(OA-15572), 2025년 합계. ①은 시간대 길이(3~6시간)가 달라 1시간당 값으로 맞춘 뒤 비중을 계산")
    save(fig, "18_동네유형별_매출패턴.png")
    return tm, ag, wk


def fig_startup_metrics(d, t, stores, pot):
    st = stores.merge(t[["상권_코드", "동네유형"]], on="상권_코드").dropna(subset=["동네유형"])
    g = st.groupby("동네유형").agg(개업=("개업_점포_수", "sum"), 폐업=("폐업_점포_수", "sum"), 점포=("전체_점포_수", "sum"))
    rate = pd.DataFrame({"개업률": g["개업"] / (g["점포"] / 4) * 100, "폐업률": g["폐업"] / (g["점포"] / 4) * 100}).reindex(DONG_ORDER)
    pm = t.groupby("동네유형")[["P점수", "G점수"]].median().reindex(DONG_ORDER)
    p = pot.merge(d[["행정동_코드", "동네유형"]], on="행정동_코드")
    pr = p.groupby("동네유형")["실제_나누기_기대"].median().reindex(DONG_ORDER)

    fig, axes = plt.subplots(1, 3, figsize=(17, 4.6), sharey=True)
    y = np.arange(len(DONG_ORDER))
    ax = axes[0]
    ax.barh(y - 0.17, rate["개업률"], height=0.32, color=BLUE, label="개업률")
    ax.barh(y + 0.17, rate["폐업률"], height=0.32, color=ORANGE, label="폐업률")
    for i, (o, c) in enumerate(zip(rate["개업률"], rate["폐업률"])):
        ax.text(o + 0.15, i - 0.17, f"{o:.1f}", va="center", fontsize=8, color=INK2)
        ax.text(c + 0.15, i + 0.17, f"{c:.1f}", va="center", fontsize=8, color=INK2)
    ax.set_yticks(y, DONG_ORDER)
    ax.invert_yaxis()
    ax.set_xlim(0, rate.values.max() * 1.2)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
    ax.set_title("① 1년 개업률 · 폐업률")
    ax = axes[1]
    ax.barh(y - 0.17, pm["P점수"], height=0.32, color=BLUE, label="P 점수 (프리미엄)")
    ax.barh(y + 0.17, pm["G점수"], height=0.32, color=ORANGE, label="G 점수 (성장)")
    ax.axvline(50, color=INK2, linewidth=0.8)
    for i, (a, b) in enumerate(zip(pm["P점수"], pm["G점수"])):
        ax.text(a + 0.8, i - 0.17, f"{a:.0f}", va="center", fontsize=8, color=INK2)
        ax.text(b + 0.8, i + 0.17, f"{b:.0f}", va="center", fontsize=8, color=INK2)
    ax.set_xlim(0, 85)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
    ax.set_title("② 상권 P · G 점수 (세로선 50 = 서울 상권 가운데)")
    ax = axes[2]
    colors = [BLUE if v < 1 else ORANGE for v in pr.values]
    ax.barh(y, pr.values, color=colors, height=0.6)
    ax.axvline(1, color=INK, linewidth=1)
    for i, v in enumerate(pr.values):
        ax.text(max(v, 1) + 0.03, i, f"{v:.2f}배", va="center", fontsize=8.5, color=INK2)
    ax.set_xlim(0, max(pr.max() * 1.3, 1.3))
    ax.set_xlabel("생활소비 실제 ÷ 기대 (중앙값)")
    ax.set_title("③ 소비 잠재력 (1보다 작으면 덜 씀)")
    for a in axes:
        a.grid(axis="y", visible=False)
    caption(fig, "자료: 점포(OA-15577), 상권 3축 점수(5장), 행정동 소비 잠재력(9장). 2025년", y=-0.1)
    save(fig, "19_동네유형별_창업지표.png")
    out = rate.join(pm).join(pr.rename("실제_나누기_기대"))
    save_table(out.round(2), "19_동네유형별_창업지표.csv")
    return out


def fig_feature_vs_biz(d, t, sales):
    s = sales.merge(t[["상권_코드", "행정동_코드"]], on="상권_코드")
    by = s.pivot_table(index="행정동_코드", columns="서비스_업종_코드_명", values="당월_매출_금액", aggfunc="sum").fillna(0)
    share = by.div(by.sum(axis=1), axis=0) * 100
    x = d.set_index("행정동_코드").join(share, how="inner")
    x = x[by.sum(axis=1).reindex(x.index) > 50e8]  # 1년 상권 매출 50억 원 이상인 동만 (값이 너무 작은 동 제외)
    x["의원·약국"] = x["일반의원"] + x["의약품"]
    x["P점수_동"] = t.groupby("행정동_코드")["P점수"].median()
    panels = [("2030_비중", "커피-음료", "20·30대 비중 (%)", "커피-음료 매출 비중 (%)", "① 젊은 동네일수록 커피를 더 살까?"),
              ("60이상_비중", "의원·약국", "60대 이상 비중 (%)", "의원·약국 매출 비중 (%)", "② 어르신이 많으면 병원·약국 매출이 클까?"),
              ("1인가구_비율", "편의점", "1인가구 비율 (%)", "편의점 매출 비중 (%)", "③ 혼자 사는 사람이 많으면 편의점이 클까?"),
              ("아파트_시세", "P점수_동", "아파트 시세 (억 원)", "상권 P 점수 중앙값", "④ 집값 비싼 동네 상권은 프리미엄일까?")]
    fig, axes = plt.subplots(1, 4, figsize=(19, 4.6))
    rhos = {}
    for ax, (fx, fy, xl, yl, title) in zip(axes, panels):
        z = x[[fx, fy]].dropna()
        xv = z[fx] / 1e8 if fx == "아파트_시세" else z[fx]
        rho = z.corr(method="spearman").iloc[0, 1]
        rhos[title] = rho
        ax.scatter(xv, z[fy], s=14, color=BLUE, alpha=0.5, edgecolor="none")
        if fx == "아파트_시세":
            ax.set_xscale("log")
            ax.set_xticks([1, 2, 5, 10, 20], ["1억", "2억", "5억", "10억", "20억"])
        if fy != "P점수_동":
            ax.set_ylim(0, z[fy].quantile(0.98) * 1.15)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_title(f"{title}\n순위 상관계수 = {rho:.2f}", fontsize=11.5)
    caption(fig, "점 하나 = 행정동 하나 (그 동에 속한 상권들의 1년 매출이 50억 원 이상인 동만). 자료: 추정매출(OA-15572), 행정동 상주인구·아파트, SKT 관심집단, 2025년")
    save(fig, "20_동네특징과_업종매출.png")
    return rhos, len(x)


# ================================================================ 실행

def main():
    setup_style()
    shapes, codes = load_geo()
    d = build_dong_features(codes)
    d, zprof, sil, missing = cluster_dongs(d)
    print("## 동네 특징 결측:", missing[missing > 0].to_dict())
    print("실루엣:", {k: round(v, 3) for k, v in sil.items()})
    med, cnt = fig_profile(d, zprof)
    print(med.round(2).to_string(), "\n", cnt.to_string())
    print(zprof.round(2).to_string())
    for n in DONG_ORDER:
        print(n, "자치구 TOP3:", d[d["동네유형"] == n]["자치구"].value_counts().head(3).to_dict())
    fig_dong_maps(d, shapes)
    save_table(d.set_index("행정동_코드").round(3), "행정동_동네유형_2025.csv")

    t_raw = load_trade()
    axes_df, _ = build_axes(t_raw)
    t = trade_by_dong(d, axes_df.reset_index())
    per, mix, no_trade = fig_trade_mix(d, t)
    print("\n## 상권 구성\n", mix.round(1).assign(만명당=per.round(2), 상권없는동=no_trade).to_string())
    print(fig_trade_mbti(t).round(1).to_string())
    sub, top = fig_dong_biz(t, t_raw["sales"])
    print(sub.round(2).to_string())
    for n, v in top.items():
        print(n, "특화 TOP5:", v)
    tm, ag, wk = fig_sales_pattern(t, t_raw["sales"])
    print(tm.round(1).to_string(), "\n", ag.round(1).to_string(), "\n", wk.round(1).to_string())
    pot, _, _ = potential_table()
    print(fig_startup_metrics(d, t, t_raw["stores"], pot).round(2).to_string())
    rhos, n = fig_feature_vs_biz(d, t, t_raw["sales"])
    print("관계 (동 수", n, "):", {k: round(v, 2) for k, v in rhos.items()})


if __name__ == "__main__":
    main()
