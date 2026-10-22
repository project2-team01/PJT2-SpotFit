"""Reproduce the nine-industry dining detail in the Park 2025 Q4 EDA.

The team-approved industry names stay intact. A market is assigned to its
source administrative dong; missing sales rows are never filled with zero.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from eda_final_industry_groups import GROUPS


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "상권"
OUT = Path(__file__).resolve().parent
TABLES = OUT / "eda_tables"
FIGURES = OUT / "eda_figures"
TABLES.mkdir(exist_ok=True)
FIGURES.mkdir(exist_ok=True)
FOOD = GROUPS[0][2]
Q4 = 20254
TIME = (
    ("00~06", "시간대_00~06_매출_금액"),
    ("06~11", "시간대_06~11_매출_금액"),
    ("11~14", "시간대_11~14_매출_금액"),
    ("14~17", "시간대_14~17_매출_금액"),
    ("17~21", "시간대_17~21_매출_금액"),
    ("21~24", "시간대_21~24_매출_금액"),
)


def source(filename: str, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_csv(
        RAW / filename, encoding="utf-8-sig", usecols=columns,
        dtype={"상권_코드": str, "행정동_코드": str, "서비스_업종_코드": str},
    )


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = Path("C:/Windows/Fonts/malgun.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def time_chart(profile: pd.DataFrame) -> None:
    """Show all six non-overlapping time windows, weighted by sales."""
    image = Image.new("RGB", (1550, 820), "white")
    draw = ImageDraw.Draw(image)
    title, label, small = font(31), font(21), font(17)
    draw.text((55, 30), "외식 9개 업종: 하루 중 언제 매출이 잡히나", fill="#17243a", font=title)
    draw.text((55, 78), "2025 Q4 · 각 칸 = 해당 시간대 추정매출 / 업종 Q4 추정매출 · 진할수록 비중이 큼", fill="#566579", font=small)
    left, top, cell_w, cell_h = 260, 170, 176, 56
    for i, (name, _) in enumerate(TIME):
        draw.text((left + i * cell_w + 40, 135), name, fill="#334155", font=label)
    for i, (_, row) in enumerate(profile.iterrows()):
        y = top + i * 62
        draw.text((55, y + 15), row["업종_명"].replace("-", "·"), fill="#17243a", font=label)
        for j, (name, _) in enumerate(TIME):
            value = row[f"시간대_{name}_비중_퍼센트"]
            strength = min(value / 60.0, 1.0)
            low, high = (231, 242, 247), (26, 113, 137)
            color = tuple(round(a + (b - a) * strength) for a, b in zip(low, high))
            x = left + j * cell_w
            draw.rounded_rectangle((x, y, x + cell_w - 9, y + cell_h), radius=8, fill=color)
            draw.text((x + 43, y + 14), f"{value:.1f}%", fill="white" if strength >= .57 else "#17243a", font=label)
    draw.text((55, 756), "시간대 합계는 업종별 총매출과 일치합니다. 시간대는 영업시간이나 개별 가게 매출을 뜻하지 않습니다.", fill="#566579", font=small)
    image.save(FIGURES / "Q4_외식_9업종_6개시간대.png")


def main() -> None:
    age_cols = [f"연령대_{age}_매출_금액" for age in ("10", "20", "30", "40", "50", "60_이상")]
    sales_cols = ["기준_년분기_코드", "상권_코드", "서비스_업종_코드", "서비스_업종_코드_명",
                  "당월_매출_금액", "당월_매출_건수", "주중_매출_금액", "주말_매출_금액"] + [col for _, col in TIME] + age_cols
    store_cols = ["기준_년분기_코드", "상권_코드", "서비스_업종_코드", "전체_점포_수"]
    area_cols = ["상권_코드", "상권_코드_명", "자치구_코드_명", "행정동_코드", "행정동_코드_명"]
    sales = source("OA-15572_추정매출_상권.csv", sales_cols)
    stores = source("OA-15577_점포_상권.csv", store_cols)
    area = source("OA-15560_영역_상권.csv", area_cols)
    assert area["상권_코드"].is_unique
    assert len(FOOD) == 9
    q4 = sales.loc[(sales["기준_년분기_코드"] == Q4) & sales["서비스_업종_코드_명"].isin(FOOD)].copy()
    q4_store = stores.loc[stores["기준_년분기_코드"] == Q4].copy()
    keys = ["기준_년분기_코드", "상권_코드", "서비스_업종_코드"]
    panel = q4.merge(q4_store, on=keys, how="left", validate="one_to_one", indicator=True)
    assert (panel["_merge"] == "both").all() and panel["전체_점포_수"].notna().all()
    panel = panel.drop(columns="_merge").merge(area, on="상권_코드", how="left", validate="many_to_one")
    assert panel["행정동_코드"].notna().all()
    assert panel["서비스_업종_코드_명"].nunique() == 9
    assert (panel["주중_매출_금액"] + panel["주말_매출_금액"] == panel["당월_매출_금액"]).all()
    assert (panel[[col for _, col in TIME]].sum(axis=1) == panel["당월_매출_금액"]).all()
    assert (panel["당월_매출_건수"] > 0).all()
    assert (panel["전체_점포_수"] > 0).all()
    age_mismatch_rows = int((panel[age_cols].sum(axis=1) != panel["당월_매출_금액"]).sum())

    food_total = int(panel["당월_매출_금액"].sum())
    profile = panel.groupby(["서비스_업종_코드", "서비스_업종_코드_명"], as_index=False).agg(
        관측_상권_수=("상권_코드", "nunique"),
        점포_수_합계=("전체_점포_수", "sum"),
        추정매출_원=("당월_매출_금액", "sum"),
        매출_건수=("당월_매출_건수", "sum"),
        주말_매출_원=("주말_매출_금액", "sum"),
        **{f"시간대_{name}_매출_원": (col, "sum") for name, col in TIME},
    ).rename(columns={"서비스_업종_코드_명": "업종_명"})
    profile["외식_매출비중_퍼센트"] = profile["추정매출_원"] / food_total * 100
    profile["건당_매출_원"] = profile["추정매출_원"] / profile["매출_건수"]
    profile["주말_매출비중_퍼센트"] = profile["주말_매출_원"] / profile["추정매출_원"] * 100
    profile["점포당_비교매출_원"] = profile["추정매출_원"] / profile["점포_수_합계"]
    for name, _ in TIME:
        profile[f"시간대_{name}_비중_퍼센트"] = profile[f"시간대_{name}_매출_원"] / profile["추정매출_원"] * 100

    panel["상권_점포당_비교매출_원"] = panel["당월_매출_금액"] / panel["전체_점포_수"]
    medians = panel.groupby("서비스_업종_코드", as_index=False)["상권_점포당_비교매출_원"].median().rename(
        columns={"상권_점포당_비교매출_원": "상권별_점포당_비교매출_중앙값_원"}
    )
    profile = profile.merge(medians, on="서비스_업종_코드", validate="one_to_one")

    dong = panel.groupby(["행정동_코드", "행정동_코드_명", "자치구_코드_명", "서비스_업종_코드", "서비스_업종_코드_명"], as_index=False).agg(
        관측_상권_수=("상권_코드", "nunique"), 점포_수_합계=("전체_점포_수", "sum"),
        추정매출_원=("당월_매출_금액", "sum"),
    ).rename(columns={"서비스_업종_코드_명": "업종_명", "행정동_코드_명": "행정동_명", "자치구_코드_명": "자치구_명"})
    dong["행정동_명"] = dong["행정동_명"].str.replace("?", "·", regex=False)
    dong_totals = dong.groupby("행정동_코드", as_index=False)["추정매출_원"].sum().rename(columns={"추정매출_원": "동_외식9업종_추정매출_원"})
    dong = dong.merge(dong_totals, on="행정동_코드", validate="many_to_one")
    dong["동_외식9업종_중_업종비중_퍼센트"] = dong["추정매출_원"] / dong["동_외식9업종_추정매출_원"] * 100
    dong["점포당_비교매출_원"] = dong["추정매출_원"] / dong["점포_수_합계"]
    assert int(dong["추정매출_원"].sum()) == food_total
    assert dong.groupby("행정동_코드")["동_외식9업종_추정매출_원"].first().sum() == food_total

    concentration = dong.groupby("서비스_업종_코드").agg(관측_행정동_수=("행정동_코드", "nunique"))
    top5 = dong.sort_values("추정매출_원", ascending=False).groupby("서비스_업종_코드").head(5).groupby("서비스_업종_코드")["추정매출_원"].sum()
    concentration["상위5개동_매출_원"] = top5
    profile = profile.merge(concentration.reset_index(), on="서비스_업종_코드", validate="one_to_one")
    profile["상위5개동_매출비중_퍼센트"] = profile["상위5개동_매출_원"] / profile["추정매출_원"] * 100
    profile = profile.sort_values("추정매출_원", ascending=False)
    assert len(profile) == 9 and profile["추정매출_원"].sum() == food_total
    assert len(set(profile["업종_명"]) ^ set(FOOD)) == 0

    profile.to_csv(TABLES / "Q4_외식_9업종_세부지표.csv", index=False, encoding="utf-8-sig", float_format="%.2f")
    dong.sort_values(["자치구_명", "행정동_명", "업종_명"]).to_csv(
        TABLES / "Q4_행정동_외식_9업종.csv", index=False, encoding="utf-8-sig", float_format="%.2f"
    )
    time_chart(profile)
    summary = {
        "q4_rows": len(panel), "markets": int(panel["상권_코드"].nunique()),
        "dongs": int(dong["행정동_코드"].nunique()), "dong_industry_pairs": len(dong),
        "age_sales_sum_mismatch_rows": age_mismatch_rows,
        "total_100m_krw": round(food_total / 1e8, 1),
        "dong_food_sales_median_100m_krw": round(dong_totals["동_외식9업종_추정매출_원"].median() / 1e8, 1),
        "industries": profile[["업종_명", "외식_매출비중_퍼센트", "건당_매출_원", "주말_매출비중_퍼센트",
                               "상권별_점포당_비교매출_중앙값_원", "관측_행정동_수", "상위5개동_매출비중_퍼센트"]].round(2).to_dict("records"),
        "top_dongs_by_food": dong_totals.nlargest(5, "동_외식9업종_추정매출_원").merge(
            dong[["행정동_코드", "자치구_명", "행정동_명"]].drop_duplicates("행정동_코드"), on="행정동_코드"
        ).to_dict("records"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
