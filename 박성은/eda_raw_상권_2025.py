"""2025 Seoul trade-area raw CSV EDA. Run from any directory with pandas and Pillow."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from eda_final_industry_groups import classification_frame


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "상권"
FIGURES = Path(__file__).resolve().parent / "eda_figures"
FIGURES.mkdir(exist_ok=True)


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(
        RAW / name,
        encoding="utf-8-sig",
        dtype={"상권_코드": str, "서비스_업종_코드": str},
    )


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = Path("C:/Windows/Fonts/malgun.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def quarter_chart(values: pd.Series) -> None:
    im = Image.new("RGB", (1000, 520), "#ffffff")
    d = ImageDraw.Draw(im)
    title, body, small = font(26), font(20), font(15)
    d.text((65, 30), "2025년 분기별 상권 추정매출 합계", fill="#17243a", font=title)
    d.text((65, 72), "단위: 조 원 · 2025년 원천 추정매출 CSV의 상권·업종 행 합산", fill="#566579", font=small)
    max_value = max(values) / 1e12 * 1.12
    left, bottom, height = 95, 430, 300
    for tick in (0, 5, 10, 15, 20, 25):
        y = bottom - tick / max_value * height
        d.line((left, y, 930, y), fill="#e4e9ef", width=1)
        d.text((50, y - 10), str(tick), fill="#64748b", font=small)
    for i, (quarter, amount) in enumerate(values.items()):
        x = 140 + i * 205
        h = amount / 1e12 / max_value * height
        d.rounded_rectangle((x, bottom - h, x + 105, bottom), radius=8, fill="#2b6cb0")
        d.text((x + 20, bottom - h - 31), f"{amount / 1e12:.2f}", fill="#17243a", font=body)
        d.text((x + 32, bottom + 12), f"Q{str(quarter)[-1]}", fill="#17243a", font=body)
    im.save(FIGURES / "2025_분기별_추정매출.png")


def proxy_chart(frame: pd.DataFrame, weekday_cut: float, worker_cut: float) -> None:
    im = Image.new("RGB", (1100, 650), "#ffffff")
    d = ImageDraw.Draw(im)
    title, body, small = font(25), font(17), font(14)
    d.text((70, 25), "2025 Q4 상권: 직장인구 밀도와 평일 매출 비중", fill="#17243a", font=title)
    d.text((70, 65), f"점 하나 = 상권 하나 (결측 제외 {len(frame):,}개) · 기준선 = 각 지표 중앙값", fill="#566579", font=small)
    left, right, top, bottom = 105, 1010, 110, 550
    d.rectangle((left, top, right, bottom), outline="#a9b8ca", width=2)
    x_min, x_max, y_min, y_max = -1.0, 4.8, 0.30, 1.0

    def xy(workers: float, weekday: float) -> tuple[int, int]:
        x = left + (math.log10(workers + 1) - x_min) / (x_max - x_min) * (right - left)
        y = bottom - (weekday - y_min) / (y_max - y_min) * (bottom - top)
        return int(x), int(y)

    for n in (0, 1, 10, 100, 1000, 10000):
        x, _ = xy(n, y_min)
        if left <= x <= right:
            d.line((x, top, x, bottom), fill="#edf1f5")
            d.text((x - 14, bottom + 7), str(n), fill="#64748b", font=small)
    for share in (0.4, 0.6, 0.8, 1.0):
        _, y = xy(0, share)
        d.line((left, y, right, y), fill="#edf1f5")
        d.text((50, y - 9), f"{share:.0%}", fill="#64748b", font=small)
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    colors = {"골목상권": (43, 108, 176, 105), "발달상권": (218, 105, 48, 130),
              "전통시장": (57, 150, 110, 115), "관광특구": (135, 83, 165, 150)}
    for row in frame.itertuples():
        x, y = xy(row.workers_ha, row.weekday_share)
        if left <= x <= right and top <= y <= bottom:
            od.ellipse((x - 3, y - 3, x + 3, y + 3), fill=colors[row.상권_구분_코드_명])
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(im)
    x_cut, y_cut = xy(worker_cut, weekday_cut)
    d.line((x_cut, top, x_cut, bottom), fill="#45546b", width=2, joint="curve")
    d.line((left, y_cut, right, y_cut), fill="#45546b", width=2, joint="curve")
    d.text((110, 588), "직장인구 / ha (로그 눈금, +1 변환)", fill="#17243a", font=body)
    legend = [("골목상권", "#2b6cb0"), ("발달상권", "#da6930"), ("전통시장", "#39966e"), ("관광특구", "#8753a5")]
    for i, (label, color) in enumerate(legend):
        x = 600 + (i % 2) * 190
        y = 581 + (i // 2) * 25
        d.ellipse((x, y + 3, x + 11, y + 14), fill=color)
        d.text((x + 17, y), label, fill="#17243a", font=small)
    im.save(FIGURES / "Q4_평일매출_직장밀도.png")


area = read("OA-15560_영역_상권.csv")
sales = read("OA-15572_추정매출_상권.csv")
stores = read("OA-15577_점포_상권.csv")
foot = read("OA-15568_길단위인구_상권.csv")
workers = read("OA-15569_직장인구_상권.csv")
residents = read("OA-15584_상주인구_상권.csv")
q4 = sales.loc[sales["기준_년분기_코드"] == 20254].copy()
final_classification = classification_frame(q4[["서비스_업종_코드", "서비스_업종_코드_명"]]).set_index("서비스_업종_코드_명")
quarter_totals = sales.groupby("기준_년분기_코드")["당월_매출_금액"].sum().sort_index()
quarter_chart(quarter_totals)

area_q4 = q4.groupby("상권_코드", as_index=False).agg(
    sales=("당월_매출_금액", "sum"), transactions=("당월_매출_건수", "sum"),
    weekday_sales=("주중_매출_금액", "sum"),
)
area_q4["weekday_share"] = area_q4["weekday_sales"] / area_q4["sales"]
area_q4["ticket"] = area_q4["sales"] / area_q4["transactions"]
area_q4 = area_q4.merge(
    area[["상권_코드", "상권_구분_코드_명", "영역_면적"]], on="상권_코드", validate="one_to_one"
)
for source, column in ((foot, "총_유동인구_수"), (workers, "총_직장_인구_수"),
                       (residents, "총_상주인구_수")):
    area_q4 = area_q4.merge(
        source.loc[source["기준_년분기_코드"] == 20254, ["상권_코드", column]],
        on="상권_코드", how="left", validate="one_to_one",
    )
area_q4["workers_ha"] = area_q4["총_직장_인구_수"] * 10000 / area_q4["영역_면적"]
complete = area_q4.dropna(subset=["workers_ha", "weekday_share"])
weekday_cut = complete["weekday_share"].median()
worker_cut = complete["workers_ha"].median()
proxy_chart(complete, weekday_cut, worker_cut)

foot_q4 = foot.loc[foot["기준_년분기_코드"] == 20254].copy()
weekday_columns = [f"{day}_유동인구_수" for day in ("월요일", "화요일", "수요일", "목요일", "금요일")]
foot_q4["foot_weekday_share"] = foot_q4[weekday_columns].sum(axis=1) / foot_q4["총_유동인구_수"].replace(0, float("nan"))
area_q4 = area_q4.merge(
    foot_q4[["상권_코드", "foot_weekday_share"]], on="상권_코드", how="left", validate="one_to_one"
)
area_q4["proxy_group"] = "mixed"
area_q4.loc[(area_q4["weekday_share"] >= weekday_cut) & (area_q4["workers_ha"] >= worker_cut), "proxy_group"] = "both_high"
area_q4.loc[(area_q4["weekday_share"] < weekday_cut) & (area_q4["workers_ha"] < worker_cut), "proxy_group"] = "both_low"
area_q4.loc[area_q4["workers_ha"].isna(), "proxy_group"] = "missing_workers"

join_keys = ["기준_년분기_코드", "상권_코드", "서비스_업종_코드"]
joined = sales[join_keys].merge(
    stores[join_keys + ["전체_점포_수"]], on=join_keys, how="left", validate="one_to_one", indicator=True
)
industry_q4 = q4.merge(
    stores.loc[stores["기준_년분기_코드"] == 20254, join_keys + ["전체_점포_수"]],
    on=join_keys, validate="one_to_one",
)
industry_q4 = industry_q4.groupby("서비스_업종_코드_명").agg(
    areas=("상권_코드", "nunique"), sales=("당월_매출_금액", "sum"), shops=("전체_점포_수", "sum")
)
common = sales.groupby(["상권_코드", "기준_년분기_코드"])["당월_매출_금액"].sum().unstack()
common = common.dropna()
age_columns = [f"연령대_{age}_매출_금액" for age in ("10", "20", "30", "40", "50", "60_이상")]
age_total = q4[age_columns].sum(axis=1)

summary = {
    "source_rows": {"area": len(area), "sales": len(sales), "stores": len(stores),
                    "foot": len(foot), "workers": len(workers), "residents": len(residents)},
    "quarters_trillion_krw": {str(k): round(v / 1e12, 4) for k, v in quarter_totals.items()},
    "quarter_sales_rows": {str(k): int(v) for k, v in sales["기준_년분기_코드"].value_counts().sort_index().items()},
    "quarter_sales_areas": {str(k): int(v) for k, v in sales.groupby("기준_년분기_코드")["상권_코드"].nunique().items()},
    "q4": {"industry_rows": len(q4), "areas": len(area_q4), "sales_trillion_krw": round(area_q4.sales.sum() / 1e12, 4),
           "median_area_sales_100m_krw": round(area_q4.sales.median() / 1e8, 2),
           "p90_area_sales_100m_krw": round(area_q4.sales.quantile(.9) / 1e8, 2),
           "p99_area_sales_100m_krw": round(area_q4.sales.quantile(.99) / 1e8, 2),
           "top_16_area_sales_share": round(area_q4.sales.nlargest(16).sum() / area_q4.sales.sum(), 4),
           "missing_foot": int(area_q4["총_유동인구_수"].isna().sum()),
           "missing_workers": int(area_q4["총_직장_인구_수"].isna().sum()),
           "missing_residents": int(area_q4["총_상주인구_수"].isna().sum())},
    "q4_type_medians": {
        name: {"areas": len(group), "sales_100m_krw": round(group["sales"].median() / 1e8, 2),
               "ticket_krw": round(group["ticket"].median()),
               "weekday_share": round(group["weekday_share"].median(), 4),
               "workers_per_ha": round(group["workers_ha"].median(), 2)}
        for name, group in area_q4.groupby("상권_구분_코드_명")
    },
    "q4_selected_industries": {
        name: {"common_group": final_classification.loc[name, "공통_그룹"],
               "consumption_item": final_classification.loc[name, "소비_항목"],
               "areas": int(industry_q4.loc[name, "areas"]),
               "sales_trillion_krw": round(industry_q4.loc[name, "sales"] / 1e12, 4),
               "shops": int(industry_q4.loc[name, "shops"]),
               "sales_per_shop_krw": round(industry_q4.loc[name, "sales"] / industry_q4.loc[name, "shops"])}
        for name in ("한식음식점", "호프-간이주점", "커피-음료")
    },
    "same_area_4_quarters": len(common),
    "same_area_q4_vs_q1_median_change": round((common[20254] / common[20251] - 1).median(), 4),
    "same_area_q4_vs_q1_positive": int((common[20254] > common[20251]).sum()),
    "store_join_matched": int((joined["_merge"] == "both").sum()),
    "store_join_total": len(joined),
    "age_sum_mismatch_q4_rows": int((age_total != q4["당월_매출_금액"]).sum()),
    "age_sum_net_gap_share": round((q4["당월_매출_금액"] - age_total).sum() / q4["당월_매출_금액"].sum(), 4),
    "age_sum_exceeds_total_q4_rows": int((age_total > q4["당월_매출_금액"]).sum()),
    "weekday_plus_weekend_mismatch_q4_rows": int((q4["주중_매출_금액"] + q4["주말_매출_금액"] != q4["당월_매출_금액"]).sum()),
    "weekday_worker_spearman": round(complete[["weekday_share", "workers_ha"]].corr(method="spearman").iloc[0, 1], 4),
    "weekday_median": round(weekday_cut, 4),
    "workers_per_ha_median": round(worker_cut, 2),
    "proxy_groups": {
        name: {"areas": len(group), "foot_weekday_share_median": round(group["foot_weekday_share"].median(), 4),
               "resident_median": round(group["총_상주인구_수"].median())}
        for name, group in area_q4.groupby("proxy_group")
    },
    "static_population_all_four_quarters": {
        name: {"areas": int(source["상권_코드"].nunique()),
               "identical": int((source.groupby("상권_코드")[column].nunique() == 1).sum())}
        for name, source, column in (("workers", workers, "총_직장_인구_수"),
                                     ("residents", residents, "총_상주인구_수"))
    },
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
