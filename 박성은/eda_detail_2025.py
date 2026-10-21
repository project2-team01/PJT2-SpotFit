"""Reproduce Q4 2025 industry and six-age-band EDA from repository raw CSVs."""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from eda_final_industry_groups import GROUPS, classification_frame


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = Path(__file__).resolve().parent
FIGURES = OUT / "eda_figures"
TABLES = OUT / "eda_tables"
FIGURES.mkdir(exist_ok=True)
TABLES.mkdir(exist_ok=True)
Q4 = 20254
AGES = ("10", "20", "30", "40", "50", "60_이상")
AGE_LABELS = ("10", "20", "30", "40", "50", "60+")
AGE_COLORS = ("#96a9c2", "#3f83c5", "#36a4a0", "#8cb767", "#e7a548", "#aa78aa")


def read(path: str, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_csv(
        RAW / path, encoding="utf-8-sig", usecols=columns,
        dtype={"상권_코드": str, "행정동_코드": str, "서비스_업종_코드": str},
    )


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = Path("C:/Windows/Fonts/malgun.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def food_time_chart(frame: pd.DataFrame) -> None:
    food = frame.loc[frame["공통_그룹"] == "외식"].sort_values("추정매출_원", ascending=False)
    assert len(food) == 9
    im = Image.new("RGB", (1800, 890), "white")
    d = ImageDraw.Draw(im)
    title, head, body, small = font(34), font(20), font(20), font(16)
    d.text((65, 28), "외식 9개 업종의 매출 시간대", fill="#17243a", font=title)
    d.text((65, 78), "2025 Q4 · 각 시간대 금액 ÷ 해당 업종의 관측 추정매출 합계", fill="#566579", font=small)
    for x, label in ((65, "업종"), (255, "상권"), (350, "점포"), (535, "점심 11~14시"),
                     (1025, "저녁 17~24시"), (1515, "점포당 비교 매출")):
        d.text((x, 140), label, fill="#334155", font=head)
    d.text((1540, 173), "(백만 원)", fill="#64748b", font=small)
    d.line((65, 204, 1735, 204), fill="#cbd5e1", width=2)
    for i, row in enumerate(food.itertuples(index=False)):
        y = 220 + i * 59
        if i % 2 == 0:
            d.rectangle((60, y - 3, 1740, y + 50), fill="#f8fafc")
        d.text((65, y + 8), row.업종_명.replace("-", "·"), fill="#17243a", font=body)
        d.text((255, y + 8), f"{row.관측_상권_수:,}", fill="#334155", font=body)
        d.text((350, y + 8), f"{row.관측_점포_수:,}", fill="#334155", font=body)
        for x, value, color in ((535, row.점심_매출비중_퍼센트, "#3182bd"),
                                (1025, row.저녁_매출비중_퍼센트, "#d37a3e")):
            d.rounded_rectangle((x, y + 13, x + 290, y + 34), radius=5, fill="#e8edf3")
            d.rounded_rectangle((x, y + 13, x + 290 * value / 100, y + 34), radius=5, fill=color)
            d.text((x + 305, y + 7), f"{value:.1f}%", fill="#334155", font=body)
        d.text((1575, y + 8), f"{row.점포당_매출_원_비교용 / 1e6:.1f}", fill="#334155", font=body)
    d.text((65, 835), "점포당 비교 매출 = 관측 업종 매출 합계 / 같은 행의 점포 수 합계. 개별 가게 매출이나 순이익이 아님.", fill="#566579", font=small)
    im.save(FIGURES / "Q4_외식_9업종_시간대.png")


def final_group_chart(frame: pd.DataFrame) -> None:
    """Show all supplied rows, including the separately flagged ecommerce row."""
    im = Image.new("RGB", (1750, 1120), "white")
    d = ImageDraw.Draw(im)
    title, head, body, small = font(35), font(21), font(19), font(16)
    d.text((65, 25), "최종 분류별 Q4 관측 추정매출", fill="#17243a", font=title)
    d.text((65, 76), "61개 분석 업종 + 전자상거래업 1개 별도 표시 · 서울 상권 업종별 매출 합계", fill="#566579", font=small)
    for x, label in ((65, "공통 그룹"), (290, "소비 항목"), (580, "업종 수"), (775, "추정매출 규모"), (1465, "매출액")):
        d.text((x, 125), label, fill="#334155", font=head)
    d.line((65, 165, 1680, 165), fill="#cbd5e1", width=2)
    maximum = frame["추정매출_원"].max()
    for i, (_, row) in enumerate(frame.iterrows()):
        y = 180 + i * 61
        if i % 2 == 0:
            d.rectangle((60, y - 2, 1685, y + 54), fill="#f8fafc")
        color = "#94a3b8" if not row["분석_포함"] else "#218c80"
        d.text((65, y + 10), row["공통_그룹"], fill="#17243a", font=body)
        d.text((290, y + 10), row["소비_항목"], fill="#334155", font=body)
        d.text((603, y + 10), str(row["업종_수"]), fill="#334155", font=body)
        d.rounded_rectangle((775, y + 16, 1395, y + 37), radius=5, fill="#e8edf3")
        width = max(3, 620 * row["추정매출_원"] / maximum)
        d.rounded_rectangle((775, y + 16, 775 + width, y + 37), radius=5, fill=color)
        d.text((1465, y + 10), f"{row['추정매출_원'] / 1e12:.3f}조", fill="#334155", font=body)
    d.text((65, 1070), "출처: OA-15572 추정매출·OA-15577 점포 (2025 Q4). 그룹 매출은 창업 수익성 순위가 아닙니다.", fill="#566579", font=small)
    im.save(FIGURES / "Q4_최종분류_그룹별_추정매출.png")


def age_mix_chart(city_shares: dict[str, list[float]], dong: pd.DataFrame) -> None:
    examples = ["신촌동", "역삼1동", "신림동", "삼양동"]
    rows = [("서울 유동인구", city_shares["유동"]),
            ("서울 상주인구", city_shares["상주"]),
            ("서울 직장인구", city_shares["직장"])]
    for name in examples:
        item = dong.loc[dong["행정동_명"] == name]
        assert len(item) == 1
        rows.append((f"{name} 유동인구", [float(item.iloc[0][f"유동_{age}_비중_퍼센트"]) for age in AGES]))
    im = Image.new("RGB", (1500, 760), "white")
    d = ImageDraw.Draw(im)
    title, body, small = font(32), font(21), font(16)
    d.text((65, 28), "연령 6개 구간을 나누어 보면", fill="#17243a", font=title)
    d.text((65, 75), "2025 Q4 · 서울 값은 각 동의 인구 수를 합산한 뒤 연령별 비중을 계산", fill="#566579", font=small)
    legend_x = 270
    for label, color in zip(AGE_LABELS, AGE_COLORS):
        d.rectangle((legend_x, 128, legend_x + 22, 150), fill=color)
        d.text((legend_x + 30, 125), label, fill="#334155", font=body)
        legend_x += 135
    for i, (label, shares) in enumerate(rows):
        y = 200 + i * 65
        if i == 3:
            d.line((65, y - 11, 1430, y - 11), fill="#cbd5e1", width=2)
        d.text((65, y + 8), label, fill="#17243a", font=body)
        x = 290
        for value, color in zip(shares, AGE_COLORS):
            width = 1030 * value / 100
            d.rectangle((x, y, x + width, y + 39), fill=color)
            if width >= 55:
                d.text((x + max(3, width / 2 - 19), y + 8), f"{value:.0f}%", fill="#17243a", font=small)
            x += width
    d.text((65, 692), "동별 전체 연령 비중과 실제 인구 수는 Q4_행정동_연령_6구간.csv에서 확인할 수 있습니다.", fill="#566579", font=small)
    im.save(FIGURES / "Q4_연령_6구간_구성비.png")


def share_color(value: float, maximum: float) -> tuple[int, int, int]:
    low, high = (225, 236, 248), (30, 83, 153)
    t = max(0.0, min(1.0, value / maximum))
    return tuple(round(a + (b - a) * t) for a, b in zip(low, high))


def age_location_chart(dong: pd.DataFrame) -> None:
    """Map all 425 source centroids; avoid mismatched 2025-12-31 polygons."""
    im = Image.new("RGB", (2200, 1050), "white")
    d = ImageDraw.Draw(im)
    title, body, small = font(37), font(23), font(18)
    d.text((70, 30), "행정동 위치별 20대·30대 유동 비중", fill="#17243a", font=title)
    d.text((70, 85), "2025 Q4 · 점 1개 = 행정동 1개 · 425개 동의 원천 대표 좌표 사용 · 색이 짙을수록 비중이 높음", fill="#566579", font=small)
    xmin, xmax = dong["엑스좌표_값"].min(), dong["엑스좌표_값"].max()
    ymin, ymax = dong["와이좌표_값"].min(), dong["와이좌표_값"].max()
    settings = [("20", 50.0, 65), ("30", 30.0, 1130)]
    for age, limit, left in settings:
        top, width, height = 210, 965, 630
        d.rounded_rectangle((left, 155, left + width, 850), radius=16, fill="#f8fafc", outline="#d9e2ec", width=2)
        d.text((left + 26, 171), f"{age}대 비중", fill="#17243a", font=font(29))
        d.text((left + 415, 179), f"서울 동 중앙값 {dong[f'유동_{age}_비중_퍼센트'].median():.1f}%", fill="#566579", font=small)
        xpad, ypad = 55, 22
        for _, row in dong.sort_values(f"유동_{age}_비중_퍼센트").iterrows():
            x = left + xpad + (row["엑스좌표_값"] - xmin) / (xmax - xmin) * (width - 2 * xpad)
            y = top + ypad + (ymax - row["와이좌표_값"]) / (ymax - ymin) * (height - 2 * ypad)
            c = share_color(row[f"유동_{age}_비중_퍼센트"], limit)
            d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=c, outline="#31506e", width=1)
        legend_y = 873
        for i in range(190):
            c = share_color(i / 189 * limit, limit)
            d.rectangle((left + 27 + i * 4, legend_y, left + 30 + i * 4, legend_y + 17), fill=c)
        d.text((left + 27, legend_y + 24), "0%", fill="#566579", font=small)
        d.text((left + 726, legend_y + 24), f"{limit:.0f}%", fill="#566579", font=small)
        top_three = dong.nlargest(3, f"유동_{age}_비중_퍼센트")
        examples = ", ".join(f"{r['행정동_명']} {r[f'유동_{age}_비중_퍼센트']:.1f}%" for _, r in top_three.iterrows())
        d.text((left + 27, 933), f"높은 동: {examples}", fill="#334155", font=small)
    d.text((70, 1004), "점의 위치는 동의 대표 좌표이며 동 경계나 실제 방문 위치를 뜻하지 않습니다. 정확한 동별 수치는 연령 결과표 참조.", fill="#566579", font=small)
    im.save(FIGURES / "Q4_행정동_20대30대_유동비중_위치도.png")


def age_hover_map(dong: pd.DataFrame) -> None:
    """Standalone SVG: hovering any of the 425 points exposes its exact values."""
    xmin, xmax = dong["엑스좌표_값"].min(), dong["엑스좌표_값"].max()
    ymin, ymax = dong["와이좌표_값"].min(), dong["와이좌표_값"].max()
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1450 740" role="img" aria-label="425개 행정동 20대와 30대 유동 비중 지도">',
        '<rect width="1450" height="740" fill="white"/>',
        '<text x="42" y="49" font-size="29" font-family="Malgun Gothic,sans-serif" fill="#17243a">행정동별 연령 비중: 점에 마우스를 올려 수치 확인</text>',
        '<text x="42" y="82" font-size="15" font-family="Malgun Gothic,sans-serif" fill="#566579">2025 Q4 · 원천 대표 좌표의 위치도 · 동 경계 지도 아님</text>',
    ]
    for age, limit, left in (("20", 50.0, 40), ("30", 30.0, 755)):
        parts.append(f'<rect x="{left}" y="110" width="655" height="550" rx="12" fill="#f8fafc" stroke="#d9e2ec"/>')
        parts.append(f'<text x="{left+22}" y="144" font-size="23" font-family="Malgun Gothic,sans-serif" fill="#17243a">{age}대 유동 비중</text>')
        for _, row in dong.sort_values(f"유동_{age}_비중_퍼센트").iterrows():
            x = left + 35 + (row["엑스좌표_값"] - xmin) / (xmax - xmin) * 585
            y = 170 + (ymax - row["와이좌표_값"]) / (ymax - ymin) * 430
            color = "#%02x%02x%02x" % share_color(row[f"유동_{age}_비중_퍼센트"], limit)
            age_text = ", ".join(f"{a.replace('_이상','+')} {row[f'유동_{a}_비중_퍼센트']:.1f}%" for a in AGES)
            tip = (f"{row['자치구_명']} {row['행정동_명']} ({row['행정동_코드']})\n"
                   f"유동인구 {int(row['유동_전체_인구_수']):,}명\n{age_text}")
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.4" fill="{color}" stroke="#31506e" stroke-width="0.6"><title>{escape(tip)}</title></circle>')
        parts.append(f'<text x="{left+24}" y="636" font-size="15" font-family="Malgun Gothic,sans-serif" fill="#566579">색 눈금 0~{limit:.0f}% · 마우스를 점 위에 올리면 동별 6개 연령 비중 표시</text>')
    parts.append('<text x="42" y="705" font-size="15" font-family="Malgun Gothic,sans-serif" fill="#566579">직장인구 자료가 없는 동도 유동인구 값이 있으면 표시했습니다. 원천 코드로 결과표와 연결합니다.</text>')
    parts.append('</svg>')
    (FIGURES / "Q4_행정동_연령_점별값.svg").write_text("\n".join(parts), encoding="utf-8")


sales_cols = ["기준_년분기_코드", "상권_코드", "서비스_업종_코드", "서비스_업종_코드_명",
              "당월_매출_금액", "주중_매출_금액", "시간대_11~14_매출_금액",
              "시간대_17~21_매출_금액", "시간대_21~24_매출_금액"]
sales = read("상권/OA-15572_추정매출_상권.csv", sales_cols)
stores = read("상권/OA-15577_점포_상권.csv",
              ["기준_년분기_코드", "상권_코드", "서비스_업종_코드", "전체_점포_수"])
keys = ["기준_년분기_코드", "상권_코드", "서비스_업종_코드"]
sales_q4, stores_q4 = (x.loc[x["기준_년분기_코드"] == Q4].copy() for x in (sales, stores))
panel = sales_q4.merge(stores_q4, on=keys, how="left", validate="one_to_one", indicator=True)
assert len(panel) == 21333 and (panel["_merge"] == "both").all()
assert not panel.duplicated(keys).any()
assert not panel["전체_점포_수"].isna().any()
assert panel["서비스_업종_코드"].nunique() == 62
assert stores_q4["서비스_업종_코드"].nunique() == 100

industry = panel.groupby(["서비스_업종_코드", "서비스_업종_코드_명"], as_index=False).agg(
    관측_상권_수=("상권_코드", "nunique"),
    관측_점포_수=("전체_점포_수", "sum"),
    추정매출_원=("당월_매출_금액", "sum"),
    평일_매출_원=("주중_매출_금액", "sum"),
    점심_매출_원=("시간대_11~14_매출_금액", "sum"),
    저녁_17_21_매출_원=("시간대_17~21_매출_금액", "sum"),
    저녁_21_24_매출_원=("시간대_21~24_매출_금액", "sum"),
)
industry["업종_구분"] = industry["서비스_업종_코드"].str[:3].map(
    {"CS1": "음식·음료", "CS2": "서비스", "CS3": "소매"}
)
assert industry["업종_구분"].value_counts().to_dict() == {"소매": 31, "서비스": 21, "음식·음료": 10}
industry["업종_명"] = industry["서비스_업종_코드_명"]
classification = classification_frame(industry)
classification.to_csv(TABLES / "Q4_최종_업종_소비항목_분류표.csv", index=False, encoding="utf-8-sig")
industry = industry.merge(classification, on=["서비스_업종_코드", "서비스_업종_코드_명"], validate="one_to_one")
assert industry["분석_포함"].sum() == 61
assert industry.loc[~industry["분석_포함"], "업종_명"].tolist() == ["전자상거래업"]
industry["점포당_매출_원_비교용"] = industry["추정매출_원"] / industry["관측_점포_수"].replace(0, float("nan"))
industry["평일_매출비중_퍼센트"] = industry["평일_매출_원"] / industry["추정매출_원"] * 100
industry["점심_매출비중_퍼센트"] = industry["점심_매출_원"] / industry["추정매출_원"] * 100
industry["저녁_매출비중_퍼센트"] = (
    industry["저녁_17_21_매출_원"] + industry["저녁_21_24_매출_원"]
) / industry["추정매출_원"] * 100
industry = industry.sort_values(["공통_그룹", "소비_항목", "추정매출_원"], ascending=[True, True, False])
industry_out = industry[["서비스_업종_코드", "업종_구분", "공통_그룹", "소비_항목", "분석_포함", "업종_명", "관측_상권_수", "관측_점포_수",
                         "추정매출_원", "점포당_매출_원_비교용", "평일_매출비중_퍼센트",
                         "점심_매출비중_퍼센트", "저녁_매출비중_퍼센트"]].copy()
industry_out.to_csv(TABLES / "Q4_62개_업종_현황.csv", index=False, encoding="utf-8-sig", float_format="%.2f")
food_time_chart(industry)
group_panel = panel.merge(classification, on=["서비스_업종_코드", "서비스_업종_코드_명"], validate="many_to_one")
group_summary = group_panel.groupby(["공통_그룹", "소비_항목", "분석_포함"], as_index=False).agg(
    관측_상권_수=("상권_코드", "nunique"), 관측_점포_수=("전체_점포_수", "sum"),
    추정매출_원=("당월_매출_금액", "sum"),
)
group_counts = classification.groupby(["공통_그룹", "소비_항목", "분석_포함"], as_index=False).size().rename(columns={"size": "업종_수"})
group_summary = group_summary.merge(group_counts, on=["공통_그룹", "소비_항목", "분석_포함"], validate="one_to_one")
group_order = {(group, item): i for i, (group, item, _) in enumerate(GROUPS)}
group_summary["분류_순서"] = [group_order[(group, item)] for group, item in zip(group_summary["공통_그룹"], group_summary["소비_항목"])]
group_summary = group_summary.sort_values("분류_순서")
assert group_summary["업종_수"].tolist() == [len(items) for _, _, items in GROUPS]
assert group_summary["추정매출_원"].sum() == panel["당월_매출_금액"].sum()
group_summary["전체62_매출비중_퍼센트"] = group_summary["추정매출_원"] / group_summary["추정매출_원"].sum() * 100
group_summary.to_csv(TABLES / "Q4_최종분류_그룹별_현황.csv", index=False, encoding="utf-8-sig", float_format="%.2f")
final_group_chart(group_summary)

area = read("OA-22160_영역_행정동.csv")
foot = read("OA-22178_길단위인구_행정동.csv")
resident = read("OA-22183_상주인구_행정동.csv")
worker = read("OA-22184_직장인구_행정동.csv")
district = read("OA-22167_소비_자치구.csv")
assert area["행정동_코드"].is_unique and len(area) == 425
age_sets = [
    ("유동", foot, "총_유동인구_수", "유동인구_수"),
    ("상주", resident, "총_상주인구_수", "상주인구_수"),
    ("직장", worker, "총_직장_인구_수", "직장_인구_수"),
]
dong = area[["행정동_코드", "행정동_명", "엑스좌표_값", "와이좌표_값"]].copy()
city_shares: dict[str, list[float]] = {}
age_quality: dict[str, dict[str, int]] = {}
for label, source, total, suffix in age_sets:
    q = source.loc[source["기준_년분기_코드"] == Q4].copy()
    assert q["행정동_코드"].is_unique
    age_cols = [f"연령대_{age}_{suffix}" for age in AGES]
    diff = q[age_cols].sum(axis=1) - q[total]
    age_quality[label] = {"q4_dongs": len(q), "sum_mismatch_dongs": int((diff != 0).sum()),
                          "max_abs_people": int(diff.abs().max())}
    city_shares[label] = [q[column].sum() / q[total].sum() * 100 for column in age_cols]
    keep = q[["행정동_코드", total] + age_cols].rename(
        columns={total: f"{label}_전체_인구_수", **{col: f"{label}_{age}_인구_수" for col, age in zip(age_cols, AGES)}}
    )
    dong = dong.merge(keep, on="행정동_코드", how="left", validate="one_to_one")
    for age in AGES:
        dong[f"{label}_{age}_비중_퍼센트"] = dong[f"{label}_{age}_인구_수"] / dong[f"{label}_전체_인구_수"].replace(0, float("nan")) * 100
dong["자치구_코드"] = dong["행정동_코드"].str[:5]
district_q4 = district.loc[district["기준_년분기_코드"] == Q4,
                           ["행정동_코드", "행정동_코드_명"]].rename(
    columns={"행정동_코드": "자치구_코드", "행정동_코드_명": "자치구_명"}
)
dong = dong.merge(district_q4, on="자치구_코드", how="left", validate="many_to_one")
assert len(dong) == 425 and dong["자치구_명"].notna().all()
assert dong["유동_전체_인구_수"].notna().all() and dong["상주_전체_인구_수"].notna().all()
assert dong["직장_전체_인구_수"].isna().sum() == 11
assert age_quality["유동"]["max_abs_people"] <= 4
assert age_quality["상주"]["sum_mismatch_dongs"] == 0
assert age_quality["직장"]["sum_mismatch_dongs"] == 0
dong["행정동_명"] = dong["행정동_명"].str.replace("?", "·", regex=False)
age_output = dong[["자치구_명", "행정동_코드", "행정동_명", "엑스좌표_값", "와이좌표_값"] +
                  [col for col in dong if col.endswith("_인구_수") or col.endswith("_비중_퍼센트")]].copy()
for column in age_output.columns:
    if column.endswith("_인구_수"):
        age_output[column] = age_output[column].astype("Int64")
age_output.sort_values(["자치구_명", "행정동_명"]).to_csv(
    TABLES / "Q4_행정동_연령_6구간.csv", index=False, encoding="utf-8-sig", float_format="%.3f"
)
age_mix_chart(city_shares, dong)
age_location_chart(dong)
age_hover_map(dong)

geo = json.loads((RAW / "geo" / "HangJeongDong_ver20251231.geojson").read_text(encoding="utf-8-sig"))
seoul_polygons = [feature for feature in geo["features"] if feature["properties"].get("sido") == "11"]
polygon_codes = {feature["properties"]["adm_cd2"][:8] for feature in seoul_polygons}
source_codes = set(dong["행정동_코드"])
boundary_check = {
    "source_dongs": len(source_codes), "seoul_polygons": len(seoul_polygons),
    "direct_code_matches": len(source_codes & polygon_codes),
    "unmatched_source_dongs": dong.loc[dong["행정동_코드"].isin(source_codes - polygon_codes),
                                       ["행정동_코드", "행정동_명"]].to_dict("records"),
}
assert boundary_check["direct_code_matches"] == 422

summary = {
    "q4_sales_industries": len(industry),
    "q4_store_industries": stores_q4["서비스_업종_코드"].nunique(),
    "q4_sales_rows": len(panel),
    "industry_groups": industry["업종_구분"].value_counts().to_dict(),
    "final_group_counts": {row.소비_항목: int(row.업종_수) for row in group_summary.itertuples(index=False)},
    "included_sales_trillion_krw": round(group_summary.loc[group_summary["분석_포함"], "추정매출_원"].sum() / 1e12, 4),
    "excluded_ecommerce_sales_trillion_krw": round(group_summary.loc[~group_summary["분석_포함"], "추정매출_원"].sum() / 1e12, 4),
    "external_food_9": industry.loc[industry["공통_그룹"] == "외식", [
        "업종_명", "관측_상권_수", "관측_점포_수", "추정매출_원",
        "점심_매출비중_퍼센트", "저녁_매출비중_퍼센트"
    ]].sort_values("추정매출_원", ascending=False).round(2).to_dict("records"),
    "pub_1": industry.loc[industry["소비_항목"] == "주점", [
        "업종_명", "관측_상권_수", "관측_점포_수", "추정매출_원",
        "점심_매출비중_퍼센트", "저녁_매출비중_퍼센트"
    ]].round(2).to_dict("records"),
    "age_quality": age_quality,
    "city_age_shares_percent": {k: [round(x, 2) for x in v] for k, v in city_shares.items()},
    "age_map_dongs": len(dong),
    "boundary_check": boundary_check,
    "age_map_20_top3": dong.nlargest(3, "유동_20_비중_퍼센트")[["행정동_명", "유동_20_비중_퍼센트"]].round(2).to_dict("records"),
    "age_map_30_top3": dong.nlargest(3, "유동_30_비중_퍼센트")[["행정동_명", "유동_30_비중_퍼센트"]].round(2).to_dict("records"),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
