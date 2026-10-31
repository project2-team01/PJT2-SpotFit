"""SpotFit 기본 EDA 신뢰도 점검: 보고서 12장의 숫자를 다시 계산한다.

- 상권 유형이 지표 정의를 조금 바꿔도 유지되는지 (민감도)
- 동네 유형 군집이 시드·표본·개수를 바꿔도 유지되는지 (안정성)
- 소비 잠재력 식에서 어떤 재료가 중요한지 (표준화 계수)
- 점포 수 흐름, 매출 합계, 아파트 시세 수준, 결측 대체

실행: uv run --no-project --with pandas,matplotlib,openpyxl,scikit-learn python 이승희/eda_check_2025.py   (저장소 루트에서)
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

import eda_dong_2025 as ed
import eda_raw_2025 as eb


def above_median(v):
    return v > v.median()


def check_trade_types(t):
    d, s = eb.build_axes(t)
    x = d.dropna(subset=["유형"])
    print("## 1. 상권 유형 민감도 (지표를 바꿨을 때 같은 글자가 나오는 비율)")
    alts = [("L/V: 직장÷상주만 사용", x["V점수"], eb.pct_rank(x["직장_상주_배율"])),
            ("L/V: 유동÷상주만 사용", x["V점수"], eb.pct_rank(x["유동_상주_배율"])),
            ("S/G: 매출 증감률만 사용", x["G점수"], eb.pct_rank(x["매출_증감률"])),
            ("S/G: 개업률만 사용", x["G점수"], eb.pct_rank(x["개업률"])),
            ("E/P: 매출 가중 대신 단순 평균", x["P점수"], s.groupby("상권_코드")["업종내_객단가_순위"].mean().reindex(x.index))]
    for name, base, alt in alts:
        print(f"  {name}: {(above_median(base) == above_median(alt)).mean() * 100:.1f}%")
    near = pd.concat([(x[c] - x[c].median()).abs() < 5 for c in ["V점수", "P점수", "G점수"]], axis=1).any(axis=1)
    print(f"  세 축 중 하나라도 중앙값 ±5점 안에 있는 상권: {near.mean() * 100:.1f}%")
    n_biz = s.groupby("상권_코드")["서비스_업종_코드_명"].nunique().reindex(x.index)
    print(f"  P 점수에 쓰인 업종 수 중앙값 {n_biz.median():.0f}개, 3개 이하인 상권 {(n_biz <= 3).sum()}곳")


def check_dong_clusters():
    _, codes = ed.load_geo()
    d = ed.build_dong_features(codes)
    X = d[list(ed.FEATURES)].copy()
    for c in ed.LOG_FEATURES:
        X[c] = np.log10(X[c].clip(lower=1e-3))
    missing = {c: d.loc[X[c].isna(), "행정동_코드_명"].tolist() for c in X if X[c].isna().any()}
    X = X.fillna(X.median())
    Z = (X - X.mean()) / X.std()
    base = KMeans(ed.N_TYPES, n_init=20, random_state=0).fit_predict(Z)
    print("\n## 2. 동네 유형 안정성 (ARI: 1 = 완전히 같은 묶음, 0 = 우연 수준)")
    print("  시드만 바꿈:", [round(adjusted_rand_score(base, KMeans(ed.N_TYPES, n_init=20, random_state=r).fit_predict(Z)), 2) for r in range(1, 5)])
    print("  개수 4개 / 6개로 바꿈:", [round(adjusted_rand_score(base, KMeans(k, n_init=20, random_state=0).fit_predict(Z)), 2) for k in (4, 6)])
    rng = np.random.default_rng(0)
    aris = []
    for i in range(20):
        idx = rng.choice(len(Z), int(len(Z) * 0.8), replace=False)
        aris.append(adjusted_rand_score(base, KMeans(ed.N_TYPES, n_init=10, random_state=i).fit(Z.iloc[idx]).predict(Z)))
    print(f"  80% 표본으로 20번: 중앙값 {np.median(aris):.2f}, 가장 낮음 {min(aris):.2f}")
    print("  중앙값으로 채운 동:", missing)
    apt = d.dropna(subset=["아파트_시세"]).groupby("자치구")["아파트_시세"].median() / 1e8
    print("  자치구별 아파트 시세 중앙값(억) 상위:", apt.sort_values().tail(3).round(1).to_dict())


def check_potential():
    p, r2, coef = eb.potential_table()
    feats = ["상주인구", "직장인구", "유동인구", "집객시설"]
    X = pd.DataFrame({c: np.log10(p[c] + 1) for c in feats})
    y = np.log10(p["생활소비"])
    Z = (X - X.mean()) / X.std()
    beta = np.linalg.lstsq(np.column_stack([np.ones(len(Z)), Z]), (y - y.mean()) / y.std(), rcond=None)[0][1:]
    print("\n## 3. 소비 잠재력 식")
    print(f"  R² {r2:.2f} / 표준화 계수:", dict(zip(feats, beta.round(2))))
    print("  재료 하나와의 상관:", {c: round(np.corrcoef(X[c], y)[0, 1], 2) for c in feats})


def check_market(t):
    print("\n## 4. 시장 흐름")
    st = t["stores"].groupby("기준_년분기_코드")[["전체_점포_수", "개업_점포_수", "폐업_점포_수"]].sum()
    print(st.to_string())
    sales = t["sales"].groupby("기준_년분기_코드")["당월_매출_금액"].sum() / 1e12
    print("  분기별 상권 매출 합계(조 원):", sales.round(2).to_dict())


def main():
    t = eb.load_trade()
    check_trade_types(t)
    check_dong_clusters()
    check_potential()
    check_market(t)


if __name__ == "__main__":
    main()
