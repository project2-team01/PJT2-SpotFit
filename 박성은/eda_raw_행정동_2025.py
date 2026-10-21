"""2025 Q4 dong and trade-area-by-industry EDA from repository raw CSVs."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from eda_final_industry_groups import classification_frame


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
FIGURES = Path(__file__).resolve().parent / "eda_figures"
FIGURES.mkdir(exist_ok=True)
TABLES = Path(__file__).resolve().parent / "eda_tables"
TABLES.mkdir(exist_ok=True)


def read(path: str) -> pd.DataFrame:
    return pd.read_csv(
        RAW / path,
        encoding="utf-8-sig",
        dtype={"상권_코드": str, "행정동_코드": str, "서비스_업종_코드": str},
    )


def q4(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[frame["기준_년분기_코드"] == 20254].copy()


def concentration_band(share: float) -> str:
    """A review flag for category concentration, not a data-error label."""
    if share >= .90:
        return "90% 이상"
    if share >= .70:
        return "70~90% 미만"
    return "70% 미만"


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = Path("C:/Windows/Fonts/malgun.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def concentration_chart(shares: dict[str, float]) -> None:
    im = Image.new("RGB", (1150, 635), "#ffffff")
    d = ImageDraw.Draw(im)
    title, body, small = font(28), font(20), font(16)
    d.text((55, 30), "Q4 행정동 지출: 상위 5개 동 집중도", fill="#17243a", font=title)
    d.text((55, 78), "지표마다 상위 5개 동이 해당 지표의 서울 합계에서 차지하는 비중", fill="#566579", font=small)
    rows = [("전체 지출", shares["total"], "#2b6cb0"),
            ("여가·문화 지출", shares["leisure"], "#8558ad"),
            ("교통·여가·기타 제외", shares["exclude3"], "#bd7a37"),
            ("음식 + 식료품", shares["food_grocery"], "#527b95"),
            ("음식 지출", shares["food"], "#2c9672")]
    for i, (label, share, color) in enumerate(rows):
        y = 138 + i * 88
        d.text((55, y + 10), label, fill="#17243a", font=body)
        d.rounded_rectangle((300, y, 960, y + 42), radius=8, fill="#edf1f5")
        d.rounded_rectangle((300, y, 300 + 660 * share, y + 42), radius=8, fill=color)
        d.text((982, y + 8), f"{share:.1%}", fill="#17243a", font=body)
    d.text((55, 590), "세 항목 제외는 대안 지표일 뿐 정제된 실제 소비를 뜻하지 않음", fill="#64748b", font=small)
    im.save(FIGURES / "Q4_행정동_지출집중도.png")


def concentration_location_chart(frame: pd.DataFrame) -> None:
    """Locate the 24 Q4 category-concentrated dongs using source centroids."""
    im = Image.new("RGB", (2050, 1080), "#ffffff")
    d = ImageDraw.Draw(im)
    title, body, small = font(35), font(21), font(17)
    d.text((65, 30), "Q4 한 항목에 지출이 집중된 24개 행정동", fill="#17243a", font=title)
    d.text((65, 82), "원천 대표 좌표 · 주황 70~90% 미만 15개 · 빨강 90% 이상 9개", fill="#566579", font=small)
    left, right, top, bottom = 75, 1040, 170, 890
    d.rounded_rectangle((left, top, right, bottom), radius=15, fill="#f8fafc", outline="#d9e2ec", width=2)
    xmin, xmax = frame["엑스좌표_값"].min(), frame["엑스좌표_값"].max()
    ymin, ymax = frame["와이좌표_값"].min(), frame["와이좌표_값"].max()

    def xy(row: pd.Series) -> tuple[float, float]:
        x = left + 40 + (row["엑스좌표_값"] - xmin) / (xmax - xmin) * (right - left - 80)
        y = top + 40 + (ymax - row["와이좌표_값"]) / (ymax - ymin) * (bottom - top - 80)
        return x, y

    for _, row in frame.iterrows():
        x, y = xy(row)
        if row["Q4_집중구간"] == "90% 이상":
            color, radius = "#b63838", 9
        elif row["Q4_집중구간"] == "70~90% 미만":
            color, radius = "#d58b35", 7
        else:
            color, radius = "#b8c5d2", 3
        d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color,
                  outline="#ffffff" if radius > 3 else color, width=2 if radius > 3 else 1)

    flagged = frame.loc[frame["Q4_집중구간"] != "70% 미만"].sort_values(
        ["Q4_최대항목비중", "행정동_코드"], ascending=[False, True]
    )
    assert len(flagged) == 24
    for n, (_, row) in enumerate(flagged.iterrows()):
        column, line = divmod(n, 12)
        x, y = 1090 + column * 470, 180 + line * 65
        color = "#b63838" if row["Q4_집중구간"] == "90% 이상" else "#d58b35"
        d.ellipse((x, y + 7, x + 15, y + 22), fill=color)
        name = row["행정동_코드_명"].replace("?", "·")
        category = row["Q4_최대지출항목"].replace("_", "·")
        d.text((x + 22, y), f"{name} {row['Q4_최대항목비중']:.1%}", fill="#17243a", font=body)
        d.text((x + 22, y + 29), category, fill="#64748b", font=small)
    d.text((75, 945), "점의 위치는 행정동 대표 좌표입니다. 행정동 경계나 가맹점 위치를 뜻하지 않습니다.", fill="#566579", font=small)
    d.text((75, 978), "집중도는 해당 동의 최대 지출 항목 ÷ 전체 지출입니다. 높은 집중도는 오류나 특정 기업의 원인을 입증하지 않습니다.", fill="#566579", font=small)
    im.save(FIGURES / "Q4_행정동_고집중_위치도.png")


def food_coffee_chart(frame: pd.DataFrame, rho: float, rho_other: float) -> None:
    im = Image.new("RGB", (1100, 660), "#ffffff")
    d = ImageDraw.Draw(im)
    title, body, small = font(25), font(17), font(14)
    d.text((70, 25), "행정동 음식 지출과 커피·음료 상권 매출", fill="#17243a", font=title)
    d.text((70, 64), f"2025 Q4 · 전체 {len(frame)}개 동 ρ={rho:.3f} · 집중도 70% 미만만 ρ={rho_other:.3f}", fill="#566579", font=small)
    left, right, top, bottom = 110, 1010, 115, 535
    d.rectangle((left, top, right, bottom), outline="#a9b8ca", width=2)
    x_values = frame["음식_지출_총금액"].map(lambda n: math.log10(n + 1))
    y_values = frame["coffee_sales"].map(lambda n: math.log10(n + 1))
    x_min, x_max = math.floor(x_values.min()), math.ceil(x_values.max())
    y_min, y_max = math.floor(y_values.min()), math.ceil(y_values.max())

    def xy(x: float, y: float) -> tuple[int, int]:
        px = left + (math.log10(x + 1) - x_min) / (x_max - x_min) * (right - left)
        py = bottom - (math.log10(y + 1) - y_min) / (y_max - y_min) * (bottom - top)
        return int(px), int(py)

    for exponent in range(x_min, x_max + 1):
        x, _ = xy(10 ** exponent, 10 ** y_min)
        d.line((x, top, x, bottom), fill="#edf1f5")
        d.text((x - 17, bottom + 8), f"10^{exponent}", fill="#64748b", font=small)
    for exponent in range(y_min, y_max + 1):
        _, y = xy(10 ** x_min, 10 ** exponent)
        d.line((left, y, right, y), fill="#edf1f5")
        d.text((48, y - 9), f"10^{exponent}", fill="#64748b", font=small)
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for row in frame.itertuples():
        x, y = xy(row.음식_지출_총금액, row.coffee_sales)
        radius = min(15, 3 + math.sqrt(row.coffee_shops) / 2)
        flagged = row.Q4_집중구간 != "70% 미만"
        od.ellipse((x - radius, y - radius, x + radius, y + radius),
                   fill=(213, 139, 53, 190) if flagged else (43, 108, 176, 110),
                   outline=(143, 71, 20, 240) if flagged else None, width=2 if flagged else 1)
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(im)
    d.text((310, 575), "행정동 음식 지출 (원, 로그 눈금)", fill="#17243a", font=body)
    d.text((110, 610), "세로축: 커피·음료 상권 추정매출 (원, 로그) · 주황 원: 한 소비 항목이 70% 이상인 동", fill="#566579", font=small)
    im.save(FIGURES / "Q4_행정동_음식지출_커피매출.png")


def profile_chart(frame: pd.DataFrame) -> None:
    im = Image.new("RGB", (1100, 700), "#ffffff")
    d = ImageDraw.Draw(im)
    title, body, small = font(27), font(20), font(16)
    d.text((55, 25), "행정동 4가지 생활권 프로필", fill="#17243a", font=title)
    d.text((55, 67), "2025 Q4 · 서울 동끼리 비교한 상대적인 특징 · 11개 동은 직장인구 자료 없음", fill="#566579", font=small)
    cards = [
        ("일터·2030", 50, 115, "#2b6cb0", "역삼1동 · 여의동"),
        ("일터·전연령", 560, 115, "#7057a3", "대치1동 · 도곡1동"),
        ("생활·2030", 50, 375, "#2c9672", "신촌동 · 신림동"),
        ("생활·전연령", 560, 375, "#bd7a37", "삼양동 · 망우본동"),
    ]
    for name, x, y, color, examples in cards:
        group = frame.loc[frame["생활권_프로필"] == name]
        d.rounded_rectangle((x, y, x + 490, y + 230), radius=18, fill="#f6f8fb", outline="#d9e2ec", width=2)
        d.rounded_rectangle((x, y, x + 12, y + 230), radius=5, fill=color)
        d.text((x + 28, y + 19), name, fill=color, font=title)
        d.text((x + 30, y + 67), f"{len(group)}개 동", fill="#17243a", font=body)
        d.text((x + 30, y + 106), f"음식·식료품 지출 중 음식: {group['음식_식료품중_음식비중'].median():.1%}", fill="#334155", font=small)
        d.text((x + 30, y + 137), f"주말 하루 유동 / 평일 하루 유동: {group['주말_평일_하루유동비'].median():.2f}배", fill="#334155", font=small)
        d.text((x + 30, y + 174), f"예: {examples}", fill="#566579", font=small)
    d.text((55, 640), "프로필은 추천 결과가 아닙니다. 실제 창업 판단에는 업종별 점포 수·매출·현장 확인이 더 필요합니다.", fill="#566579", font=small)
    im.save(FIGURES / "Q4_행정동_생활권_4유형.png")


PROFILE_COLORS = {
    "일터·2030": ("#2b6cb0", "#dcecf9"),
    "일터·전연령": ("#7057a3", "#ece5f6"),
    "생활·2030": ("#2c9672", "#dbf3e9"),
    "생활·전연령": ("#bd7a37", "#faecd9"),
    "직장인구 자료 없음": ("#64748b", "#e7ebf0"),
}


def all_dong_grid(frame: pd.DataFrame) -> None:
    """Show every dong by name; rows are districts, not map coordinates."""
    groups = list(frame.sort_values(["자치구_명", "행정동_코드_명"]).groupby("자치구_명", sort=True))
    assert len(groups) == 25 and sum(len(group) for _, group in groups) == 425
    assert max(len(group) for _, group in groups) <= 27
    width, height = 3400, 2050
    im = Image.new("RGB", (width, height), "#ffffff")
    d = ImageDraw.Draw(im)
    d.text((64, 35), "서울 425개 행정동의 생활권 유형", fill="#17243a", font=font(39))
    d.text((65, 95), "2025 Q4 · 자치구별 가나다순 · 각 칸은 행정동 1개 · 칸의 위치는 실제 지도상의 위치가 아님", fill="#566579", font=font(22))
    legend_x = 65
    for name, (dark, light) in PROFILE_COLORS.items():
        count = int((frame["생활권_프로필"] == name).sum())
        d.rounded_rectangle((legend_x, 142, legend_x + 28, 170), radius=5, fill=light, outline=dark, width=2)
        label = f"{name} {count}개"
        d.text((legend_x + 38, 142), label, fill="#334155", font=font(21))
        legend_x += 38 + d.textbbox((0, 0), label, font=font(21))[2] + 57
    d.ellipse((legend_x + 8, 150, legend_x + 20, 162), fill="#17243a")
    d.text((legend_x + 31, 142), "기준값 근처 76개", fill="#334155", font=font(21))

    left, step, tile_w, tile_h = 195, 115, 109, 46
    for row_no, (district_name, group) in enumerate(groups):
        y = 205 + row_no * 69
        if row_no % 2 == 0:
            d.rectangle((43, y - 7, width - 43, y + 55), fill="#f8fafc")
        d.text((62, y + 6), district_name, fill="#17243a", font=font(24))
        d.text((153, y + 13), f"{len(group)}", fill="#64748b", font=font(18))
        for col_no, item in enumerate(group.itertuples()):
            x = left + col_no * step
            dark, light = PROFILE_COLORS[item.생활권_프로필]
            d.rounded_rectangle((x, y, x + tile_w, y + tile_h), radius=7, fill=light, outline=dark, width=2)
            label = item.행정동_코드_명.replace("?", "·")
            single = font(16)
            if d.textbbox((0, 0), label, font=single)[2] <= tile_w - 9:
                text_w = d.textbbox((0, 0), label, font=single)[2]
                d.text((x + (tile_w - text_w) / 2, y + 10), label, fill="#17243a", font=single)
            else:
                half = (len(label) + 1) // 2
                two_line = font(14)
                for line_no, piece in enumerate((label[:half], label[half:])):
                    text_w = d.textbbox((0, 0), piece, font=two_line)[2]
                    d.text((x + (tile_w - text_w) / 2, y + 3 + line_no * 20), piece, fill="#17243a", font=two_line)
            if item.유형_경계 == "중앙값 근처":
                d.ellipse((x + tile_w - 12, y + 4, x + tile_w - 4, y + 12), fill="#17243a")
    d.text((64, height - 85), "직장인구 자료가 없는 11개 동도 회색 칸으로 포함. 동별 실제 수치와 코드는 함께 제공한 CSV에서 확인.", fill="#566579", font=font(20))
    d.text((64, height - 51), "이 유형은 동네의 상대적인 특징이며 팀의 금융 MBTI 또는 창업 추천 결과가 아님.", fill="#566579", font=font(20))
    im.save(FIGURES / "Q4_425개_행정동_유형격자.png")


def all_dong_scatter(frame: pd.DataFrame, work_cut: float, young_cut: float) -> None:
    """Plot all 414 complete dongs; state the 11 missing worker observations."""
    im = Image.new("RGB", (1500, 920), "#ffffff")
    d = ImageDraw.Draw(im)
    title, body, small = font(31), font(21), font(17)
    d.text((70, 28), "행정동은 두 기준에서 어디에 놓일까?", fill="#17243a", font=title)
    d.text((70, 75), "2025 Q4 · 점 1개 = 행정동 1개 · 직장인구가 있는 414개 동", fill="#566579", font=small)
    left, right, top, bottom = 145, 1120, 170, 765
    x_min, x_max, y_min, y_max = -5.0, 2.0, 10.0, 70.0

    def xy(work_ratio: float, young_ratio: float) -> tuple[float, float]:
        x = left + (math.log10(work_ratio) - x_min) / (x_max - x_min) * (right - left)
        y = bottom - (young_ratio * 100 - y_min) / (y_max - y_min) * (bottom - top)
        return x, y

    for exponent in range(-5, 3):
        x = left + (exponent - x_min) / (x_max - x_min) * (right - left)
        d.line((x, top, x, bottom), fill="#e8edf3", width=2)
        tick = f"{10 ** exponent:.{-exponent}f}" if exponent < 0 else str(10 ** exponent)
        tick_w = d.textbbox((0, 0), tick, font=small)[2]
        d.text((x - tick_w / 2, bottom + 12), tick, fill="#64748b", font=small)
    for value in range(10, 71, 10):
        y = bottom - (value - y_min) / (y_max - y_min) * (bottom - top)
        d.line((left, y, right, y), fill="#e8edf3", width=2)
        d.text((83, y - 10), f"{value}%", fill="#64748b", font=small)
    cut_x, cut_y = xy(work_cut, young_cut)
    d.line((cut_x, top, cut_x, bottom), fill="#334155", width=3)
    d.line((left, cut_y, right, cut_y), fill="#334155", width=3)
    d.text((cut_x + 9, top + 7), f"서울 동 중앙값 {work_cut:.3f}", fill="#334155", font=small)
    d.text((left + 10, cut_y - 30), f"2030 중앙값 {young_cut:.1%}", fill="#334155", font=small)
    d.rectangle((left, top, right, bottom), outline="#a9b8ca", width=2)

    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for _, row in frame.loc[frame["직장_상주_비"].notna()].iterrows():
        x, y = xy(row["직장_상주_비"], row["2030_유동비중"])
        dark = PROFILE_COLORS[row["생활권_프로필"]][0]
        rgb = tuple(bytes.fromhex(dark[1:]))
        od.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(*rgb, 150), outline=(*rgb, 230), width=2)
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(im)
    for name, dx, dy in (("역삼1동", 12, -23), ("대치1동", 12, 7),
                         ("신림동", -70, -28), ("삼양동", -45, 15)):
        row = frame.loc[frame["행정동_코드_명"] == name].iloc[0]
        x, y = xy(row["직장_상주_비"], row["2030_유동비중"])
        d.ellipse((x - 10, y - 10, x + 10, y + 10), outline="#17243a", width=3)
        d.text((x + dx, y + dy), name, fill="#17243a", font=small)

    d.text((375, 810), "직장인구 / 상주인구 (로그 눈금)", fill="#17243a", font=body)
    d.text((70, 855), "세로축: 오가는 사람 중 20·30대 비율. 직장인구가 없는 11개 동은 점을 찍지 않았으며 격자 그림에는 포함.", fill="#566579", font=small)
    d.text((1160, 178), "유형별 동 수", fill="#17243a", font=body)
    for index, (name, (dark, _)) in enumerate(PROFILE_COLORS.items()):
        y = 235 + index * 73
        d.ellipse((1165, y + 2, 1187, y + 24), fill=dark)
        d.text((1198, y - 2), name, fill="#334155", font=font(18))
        count = int((frame["생활권_프로필"] == name).sum())
        d.text((1198, y + 27), f"{count}개 동", fill="#64748b", font=small)
    d.text((1160, 640), "선은 서울 동의 중앙값", fill="#566579", font=small)
    d.text((1160, 671), "두 축 모두 상대 비교", fill="#566579", font=small)
    d.text((1160, 702), "추천 점수 아님", fill="#566579", font=small)
    im.save(FIGURES / "Q4_행정동_두기준_분포.png")


dong_area = read("OA-22160_영역_행정동.csv")
consumption = read("OA-22166_소비_행정동.csv")
category_columns = [col for col in consumption if col.endswith("_지출_총금액")]
assert len(category_columns) == 10
assert (consumption[category_columns].sum(axis=1) == consumption["지출_총금액"]).all()
district_consumption = read("OA-22167_소비_자치구.csv")
dong_foot = read("OA-22178_길단위인구_행정동.csv")
dong_resident = read("OA-22183_상주인구_행정동.csv")
dong_worker = read("OA-22184_직장인구_행정동.csv")
trade_area = read("상권/OA-15560_영역_상권.csv")
trade_sales = read("상권/OA-15572_추정매출_상권.csv")
trade_stores = read("상권/OA-15577_점포_상권.csv")
trade_foot = read("상권/OA-15568_길단위인구_상권.csv")

assert dong_area["행정동_코드"].is_unique
assert trade_area["상권_코드"].is_unique
assert trade_area["행정동_코드"].isin(dong_area["행정동_코드"]).all()

consumption_q4 = q4(consumption)
assert len(consumption_q4) == 425 and consumption_q4["행정동_코드"].is_unique
assert consumption.groupby("행정동_코드")["기준_년분기_코드"].nunique().eq(4).all()
dong = consumption_q4[["행정동_코드", "행정동_코드_명", "지출_총금액"] + category_columns].copy()
dong["Q4_최대지출항목"] = dong[category_columns].idxmax(axis=1).str.removesuffix("_지출_총금액")
dong["Q4_최대항목비중"] = dong[category_columns].max(axis=1) / dong["지출_총금액"]
dong["Q4_집중구간"] = dong["Q4_최대항목비중"].map(concentration_band)
dong["교통_여가_기타제외_지출_총금액"] = dong["지출_총금액"] - dong[[
    "교통_지출_총금액", "여가_문화_지출_총금액", "기타_지출_총금액"
]].sum(axis=1)
dong["음식_식료품_지출_총금액"] = dong["음식_지출_총금액"] + dong["식료품_지출_총금액"]

# Annual shares use the sum of the four quarters, not the mean of percentages.
annual = consumption.groupby("행정동_코드", as_index=False)[["지출_총금액"] + category_columns].sum()
annual["연간_최대지출항목"] = annual[category_columns].idxmax(axis=1).str.removesuffix("_지출_총금액")
annual["연간_최대항목비중"] = annual[category_columns].max(axis=1) / annual["지출_총금액"]
annual["연간_집중구간"] = annual["연간_최대항목비중"].map(concentration_band)
annual = annual[["행정동_코드", "지출_총금액", "연간_최대지출항목", "연간_최대항목비중", "연간_집중구간"]].rename(
    columns={"지출_총금액": "2025_연간_지출_총금액"}
)
quarterly = consumption[["행정동_코드", "기준_년분기_코드", "지출_총금액"] + category_columns].copy()
quarterly["최대항목비중"] = quarterly[category_columns].max(axis=1) / quarterly["지출_총금액"]
quarterly["최대지출항목"] = quarterly[category_columns].idxmax(axis=1)
persistence = quarterly.groupby("행정동_코드").agg(
    집중70_분기수=("최대항목비중", lambda s: int((s >= .70).sum())),
    최대항목_종류수=("최대지출항목", "nunique"),
).reset_index()
dong = dong.merge(annual, on="행정동_코드", validate="one_to_one")
dong = dong.merge(persistence, on="행정동_코드", validate="one_to_one")
iqr_q1, iqr_q3 = dong["지출_총금액"].quantile([.25, .75])
iqr_limit = iqr_q3 + 1.5 * (iqr_q3 - iqr_q1)
dong["Q4_전체지출_IQR상단초과"] = dong["지출_총금액"] > iqr_limit
assert (dong["연간_집중구간"] == "70~90% 미만").sum() == 16
assert (dong["연간_집중구간"] == "90% 이상").sum() == 8
assert (dong["Q4_집중구간"] == "70~90% 미만").sum() == 15
assert (dong["Q4_집중구간"] == "90% 이상").sum() == 9
assert set(dong.loc[dong["연간_최대항목비중"] >= .70, "행정동_코드"]) == set(
    dong.loc[dong["Q4_최대항목비중"] >= .70, "행정동_코드"]
)
annual_flagged = dong.loc[dong["연간_최대항목비중"] >= .70]
assert annual_flagged["집중70_분기수"].eq(4).all()
assert annual_flagged["최대항목_종류수"].eq(1).all()
dong_foot_q4 = q4(dong_foot)
foot_columns = ["행정동_코드", "총_유동인구_수", "연령대_20_유동인구_수", "연령대_30_유동인구_수"] + [
    f"{day}_유동인구_수" for day in ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일")
]
dong = dong.merge(dong_foot_q4[foot_columns], on="행정동_코드", how="left", validate="one_to_one")
for frame, column in ((dong_resident, "총_상주인구_수"),
                      (dong_worker, "총_직장_인구_수")):
    dong = dong.merge(q4(frame)[["행정동_코드", column]], on="행정동_코드",
                      how="left", validate="one_to_one")

trade_area_counts = trade_area.groupby("행정동_코드")["상권_코드"].nunique().rename("trade_area_count")
dong = dong.merge(trade_area_counts, on="행정동_코드", how="left", validate="one_to_one")
district = q4(district_consumption)[["행정동_코드", "행정동_코드_명"]].rename(
    columns={"행정동_코드": "자치구_코드", "행정동_코드_명": "자치구_명"}
)
dong["자치구_코드"] = dong["행정동_코드"].str[:5]
dong = dong.merge(district, on="자치구_코드", how="left", validate="many_to_one")
assert dong["자치구_명"].notna().all()

# These are two transparent, relative descriptors of a dong, not the team's
# official financial MBTI or an independently validated recommendation label.
dong["직장_상주_비"] = dong["총_직장_인구_수"] / dong["총_상주인구_수"].replace(0, float("nan"))
dong["2030_유동비중"] = (
    dong["연령대_20_유동인구_수"] + dong["연령대_30_유동인구_수"]
) / dong["총_유동인구_수"].replace(0, float("nan"))
weekday_columns = [f"{day}_유동인구_수" for day in ("월요일", "화요일", "수요일", "목요일", "금요일")]
weekend_columns = [f"{day}_유동인구_수" for day in ("토요일", "일요일")]
dong["평일_하루평균_유동"] = dong[weekday_columns].sum(axis=1) / 5
dong["주말_하루평균_유동"] = dong[weekend_columns].sum(axis=1) / 2
dong["주말_평일_하루유동비"] = dong["주말_하루평균_유동"] / dong["평일_하루평균_유동"].replace(0, float("nan"))
dong["음식_식료품중_음식비중"] = dong["음식_지출_총금액"] / (
    dong["음식_지출_총금액"] + dong["식료품_지출_총금액"]
).replace(0, float("nan"))
work_cut = dong["직장_상주_비"].median()
young_cut = dong["2030_유동비중"].median()
has_work = dong["직장_상주_비"].notna()
work_high = dong["직장_상주_비"] >= work_cut
young_high = dong["2030_유동비중"] >= young_cut
dong["생활권_프로필"] = "직장인구 자료 없음"
dong.loc[has_work & work_high & young_high, "생활권_프로필"] = "일터·2030"
dong.loc[has_work & work_high & ~young_high, "생활권_프로필"] = "일터·전연령"
dong.loc[has_work & ~work_high & young_high, "생활권_프로필"] = "생활·2030"
dong.loc[has_work & ~work_high & ~young_high, "생활권_프로필"] = "생활·전연령"
work_rank = dong["직장_상주_비"].rank(pct=True)
young_rank = dong["2030_유동비중"].rank(pct=True)
dong["유형_경계"] = ""
dong.loc[has_work & (work_rank.between(.45, .55) | young_rank.between(.45, .55)), "유형_경계"] = "중앙값 근처"
profile_chart(dong)
all_dong_grid(dong)
all_dong_scatter(dong, work_cut, young_cut)

profile_output = dong[["자치구_명", "행정동_코드", "행정동_코드_명", "생활권_프로필", "유형_경계",
                       "총_직장_인구_수", "총_상주인구_수", "직장_상주_비", "총_유동인구_수",
                       "2030_유동비중", "주말_평일_하루유동비", "음식_지출_총금액",
                       "식료품_지출_총금액", "음식_식료품중_음식비중", "trade_area_count",
                       "지출_총금액", "Q4_최대지출항목", "Q4_최대항목비중", "Q4_집중구간",
                       "연간_최대항목비중", "연간_집중구간"]].copy()
profile_output["행정동_코드_명"] = profile_output["행정동_코드_명"].str.replace("?", "·", regex=False)
profile_output = profile_output.rename(columns={"행정동_코드_명": "행정동_명", "trade_area_count": "배정된_상권_수"})
profile_output["2030_유동비중"] *= 100
profile_output["음식_식료품중_음식비중"] *= 100
profile_output["Q4_최대항목비중"] *= 100
profile_output["연간_최대항목비중"] *= 100
profile_output = profile_output.rename(columns={"2030_유동비중": "2030_유동비중_퍼센트",
                                         "음식_식료품중_음식비중": "음식_식료품중_음식비중_퍼센트",
                                         "지출_총금액": "Q4_지출_총금액_원",
                                         "Q4_최대항목비중": "Q4_최대항목비중_퍼센트",
                                         "연간_최대항목비중": "연간_최대항목비중_퍼센트"})
profile_output["총_직장_인구_수"] = profile_output["총_직장_인구_수"].astype("Int64")
profile_output["배정된_상권_수"] = profile_output["배정된_상권_수"].astype("Int64")
profile_output.sort_values(["자치구_명", "행정동_명"]).to_csv(
    TABLES / "Q4_행정동_생활권_프로필.csv", index=False, encoding="utf-8-sig", float_format="%.4f"
)

sensitivity_output = dong[["자치구_명", "행정동_코드", "행정동_코드_명", "지출_총금액"] + category_columns + [
    "Q4_최대지출항목", "Q4_최대항목비중", "Q4_집중구간", "Q4_전체지출_IQR상단초과",
    "교통_여가_기타제외_지출_총금액", "음식_식료품_지출_총금액",
    "2025_연간_지출_총금액", "연간_최대지출항목", "연간_최대항목비중", "연간_집중구간",
    "집중70_분기수", "최대항목_종류수",
]].copy()
sensitivity_output["행정동_코드_명"] = sensitivity_output["행정동_코드_명"].str.replace("?", "·", regex=False)
sensitivity_output["Q4_최대항목비중"] *= 100
sensitivity_output["연간_최대항목비중"] *= 100
sensitivity_output = sensitivity_output.rename(columns={
    "행정동_코드_명": "행정동_명", "지출_총금액": "Q4_지출_총금액_원",
    "Q4_최대항목비중": "Q4_최대항목비중_퍼센트", "연간_최대항목비중": "연간_최대항목비중_퍼센트",
})
sensitivity_output.sort_values(["자치구_명", "행정동_명"]).to_csv(
    TABLES / "Q4_행정동_지출_민감도.csv", index=False, encoding="utf-8-sig", float_format="%.4f"
)
concentration_location_chart(dong.merge(
    dong_area[["행정동_코드", "엑스좌표_값", "와이좌표_값"]],
    on="행정동_코드", validate="one_to_one",
))

foot_q1 = dong_foot.loc[dong_foot["기준_년분기_코드"] == 20251].copy()
foot_q1["2030_유동비중_Q1"] = (
    foot_q1["연령대_20_유동인구_수"] + foot_q1["연령대_30_유동인구_수"]
) / foot_q1["총_유동인구_수"].replace(0, float("nan"))
stability = dong[["행정동_코드", "2030_유동비중", "직장_상주_비"]].merge(
    foot_q1[["행정동_코드", "2030_유동비중_Q1"]], on="행정동_코드", validate="one_to_one"
).dropna(subset=["직장_상주_비"])
changed_youth_label = int(((stability["2030_유동비중"] >= young_cut) !=
                           (stability["2030_유동비중_Q1"] >= young_cut)).sum())
keys = ["기준_년분기_코드", "상권_코드", "서비스_업종_코드"]
panel = q4(trade_sales).merge(
    q4(trade_stores)[keys + ["전체_점포_수", "폐업_점포_수"]], on=keys,
    validate="one_to_one",
).merge(
    trade_area[["상권_코드", "행정동_코드"]], on="상권_코드", validate="many_to_one",
).merge(
    q4(trade_foot)[["상권_코드", "총_유동인구_수"]], on="상권_코드",
    how="left", validate="many_to_one",
)
assert len(panel) == len(q4(trade_sales))
assert panel["행정동_코드"].notna().all()

# Apply the team's final 62-industry grouping to observed sales before any
# 행정동-level aggregation. No-sales combinations remain absent rather than 0.
classification = classification_frame(panel[["서비스_업종_코드", "서비스_업종_코드_명"]])
group_panel = panel.merge(classification, on=["서비스_업종_코드", "서비스_업종_코드_명"], validate="many_to_one")
assert len(group_panel) == len(panel)
dong_group = group_panel.groupby(
    ["행정동_코드", "공통_그룹", "소비_항목", "분석_포함"], as_index=False
).agg(
    관측_상권_수=("상권_코드", "nunique"), 관측_업종_수=("서비스_업종_코드", "nunique"),
    관측_점포_수=("전체_점포_수", "sum"), 폐업_점포_수=("폐업_점포_수", "sum"),
    추정매출_원=("당월_매출_금액", "sum"),
)
dong_group = dong_group.merge(
    dong[["행정동_코드", "행정동_코드_명", "자치구_명"]],
    on="행정동_코드", how="left", validate="many_to_one",
)
assert dong_group["행정동_코드_명"].notna().all()
assert dong_group["추정매출_원"].sum() == panel["당월_매출_금액"].sum()
dong_group["행정동_명"] = dong_group["행정동_코드_명"].str.replace("?", "·", regex=False)
dong_group[["자치구_명", "행정동_코드", "행정동_명", "공통_그룹", "소비_항목", "분석_포함",
            "관측_상권_수", "관측_업종_수", "관측_점포_수", "폐업_점포_수", "추정매출_원"]].sort_values(
    ["자치구_명", "행정동_명", "공통_그룹", "소비_항목"]
).to_csv(TABLES / "Q4_행정동_최종분류_추정매출.csv", index=False, encoding="utf-8-sig")

dong_industry = panel.groupby(
    ["행정동_코드", "서비스_업종_코드", "서비스_업종_코드_명"], as_index=False
).agg(
    trade_sales=("당월_매출_금액", "sum"),
    trade_shops=("전체_점포_수", "sum"),
    trade_closures=("폐업_점포_수", "sum"),
    trade_areas=("상권_코드", "nunique"),
)
# Dong foot traffic is joined once per dong, after the industry aggregation.
# Summing the same foot-traffic row over industry rows would multiply it.
dong_industry = dong_industry.merge(
    dong[["행정동_코드", "음식_지출_총금액", "총_유동인구_수", "Q4_집중구간"]],
    on="행정동_코드", validate="many_to_one",
)

shares = {
    "total": dong["지출_총금액"].nlargest(5).sum() / dong["지출_총금액"].sum(),
    "leisure": dong["여가_문화_지출_총금액"].nlargest(5).sum() / dong["여가_문화_지출_총금액"].sum(),
    "exclude3": dong["교통_여가_기타제외_지출_총금액"].nlargest(5).sum() / dong["교통_여가_기타제외_지출_총금액"].sum(),
    "food_grocery": dong["음식_식료품_지출_총금액"].nlargest(5).sum() / dong["음식_식료품_지출_총금액"].sum(),
    "food": dong["음식_지출_총금액"].nlargest(5).sum() / dong["음식_지출_총금액"].sum(),
}
concentration_chart(shares)

coffee = dong_industry.loc[dong_industry["서비스_업종_코드_명"] == "커피-음료"].rename(
    columns={"trade_sales": "coffee_sales", "trade_shops": "coffee_shops"}
)
coffee_rho = coffee[["음식_지출_총금액", "coffee_sales"]].corr(method="spearman").iloc[0, 1]
coffee_other = coffee.loc[coffee["Q4_집중구간"] == "70% 미만"]
coffee_other_rho = coffee_other[["음식_지출_총금액", "coffee_sales"]].corr(method="spearman").iloc[0, 1]
food_coffee_chart(coffee, coffee_rho, coffee_other_rho)
coffee_dong = dong.merge(
    coffee[["행정동_코드", "coffee_sales", "coffee_shops"]],
    on="행정동_코드", how="left", validate="one_to_one",
)
food_q25, food_q75 = dong["음식_지출_총금액"].quantile([.25, .75])
selected = {}
trade_selected = {}
for name in ("한식음식점", "커피-음료", "호프-간이주점"):
    group = dong_industry.loc[dong_industry["서비스_업종_코드_명"] == name]
    trade_group = panel.loc[panel["서비스_업종_코드_명"] == name]
    selected[name] = {
        "dongs_with_sales": len(group),
        "median_shops_among_observed": round(group["trade_shops"].median(), 1),
        "food_spend_vs_sales_spearman": round(group[["음식_지출_총금액", "trade_sales"]].corr(method="spearman").iloc[0, 1], 4),
        "foot_vs_sales_spearman": round(group[["총_유동인구_수", "trade_sales"]].corr(method="spearman").iloc[0, 1], 4),
    }
    trade_selected[name] = {
        "trade_areas_with_sales": len(trade_group),
        "median_shops": round(trade_group["전체_점포_수"].median(), 1),
        "foot_missing": int(trade_group["총_유동인구_수"].isna().sum()),
        "foot_vs_sales_spearman": round(trade_group[["총_유동인구_수", "당월_매출_금액"]].corr(method="spearman").iloc[0, 1], 4),
        "shops_vs_sales_spearman": round(trade_group[["전체_점포_수", "당월_매출_금액"]].corr(method="spearman").iloc[0, 1], 4),
    }

top_total = consumption_q4.nlargest(5, "지출_총금액")
flagged_q4 = dong.loc[dong["Q4_집중구간"] != "70% 미만"]
flagged_annual = dong.loc[dong["연간_집중구간"] != "70% 미만"]
assert len(flagged_q4) == len(flagged_annual) == 24
summary = {
    "source_rows": {"dong_area": len(dong_area), "consumption": len(consumption),
                    "district_consumption": len(district_consumption),
                    "dong_foot": len(dong_foot), "dong_resident": len(dong_resident),
                    "dong_worker": len(dong_worker)},
    "q4_dong_profiles": {
        "work_per_resident_median_cut": round(work_cut, 4),
        "young_foot_share_median_cut": round(young_cut, 4),
        "work_vs_young_spearman": round(dong[["직장_상주_비", "2030_유동비중"]].corr(method="spearman").iloc[0, 1], 4),
        "near_either_cut": int((dong["유형_경계"] != "").sum()),
        "q1_vs_q4_young_label_changed_of_complete": changed_youth_label,
        "complete_dongs": int(has_work.sum()),
        "types": {
            name: {"dongs": len(group), "work_per_resident_median": round(group["직장_상주_비"].median(), 4),
                   "young_foot_share_median": round(group["2030_유동비중"].median(), 4),
                   "food_spend_100m_krw_median": round(group["음식_지출_총금액"].median() / 1e8, 2),
                   "food_share_of_food_plus_groceries_median": round(group["음식_식료품중_음식비중"].median(), 4),
                   "weekend_vs_weekday_daily_foot_median": round(group["주말_평일_하루유동비"].median(), 4)}
            for name, group in dong.loc[has_work].groupby("생활권_프로필")
        },
    },
    "q4_dong": {"total": len(dong), "foot_available": int(dong["총_유동인구_수"].notna().sum()),
                "resident_available": int(dong["총_상주인구_수"].notna().sum()),
                "worker_available": int(dong["총_직장_인구_수"].notna().sum()),
                "trade_area_dongs": int(dong["trade_area_count"].notna().sum()),
                "total_spend_trillion_krw": round(dong["지출_총금액"].sum() / 1e12, 4),
                "median_total_spend_100m_krw": round(dong["지출_총금액"].median() / 1e8, 2),
                "food_spend_trillion_krw": round(dong["음식_지출_총금액"].sum() / 1e12, 4),
                "median_food_spend_100m_krw": round(dong["음식_지출_총금액"].median() / 1e8, 2),
                "leisure_share_of_total": round(dong["여가_문화_지출_총금액"].sum() / dong["지출_총금액"].sum(), 4),
                "food_share_of_total": round(dong["음식_지출_총금액"].sum() / dong["지출_총금액"].sum(), 4),
                "top5_shares": {k: round(v, 4) for k, v in shares.items()},
                "food_vs_foot_spearman": round(dong[["음식_지출_총금액", "총_유동인구_수"]].corr(method="spearman").iloc[0, 1], 4),
                "category_sum_mismatch_rows": int((consumption_q4[category_columns].sum(axis=1) != consumption_q4["지출_총금액"]).sum())},
    "q4_concentration": {
        "annual_70_to_90": int((dong["연간_집중구간"] == "70~90% 미만").sum()),
        "annual_90_plus": int((dong["연간_집중구간"] == "90% 이상").sum()),
        "q4_70_to_90": int((dong["Q4_집중구간"] == "70~90% 미만").sum()),
        "q4_90_plus": int((dong["Q4_집중구간"] == "90% 이상").sum()),
        "q4_70_plus_share_of_total": round(flagged_q4["지출_총금액"].sum() / dong["지출_총금액"].sum(), 4),
        "q4_70_plus_share_of_food": round(flagged_q4["음식_지출_총금액"].sum() / dong["음식_지출_총금액"].sum(), 4),
        "q4_90_plus_share_of_total": round(dong.loc[dong["Q4_집중구간"] == "90% 이상", "지출_총금액"].sum() / dong["지출_총금액"].sum(), 4),
        "q4_total_iqr_upper_100m_krw": round(iqr_limit / 1e8, 2),
        "q4_total_iqr_above_count": int(dong["Q4_전체지출_IQR상단초과"].sum()),
        "q4_iqr_and_category_70_overlap": int(flagged_q4["Q4_전체지출_IQR상단초과"].sum()),
        "annual_flagged_70_all_four_quarters": int((flagged_annual["집중70_분기수"] == 4).sum()),
        "annual_flagged_same_category_all_four_quarters": int((flagged_annual["최대항목_종류수"] == 1).sum()),
        "metrics": {
            label: {"sum_trillion_krw": round(dong[col].sum() / 1e12, 4),
                    "median_100m_krw": round(dong[col].median() / 1e8, 2),
                    "top5_share": round(shares[label], 4),
                    "top5_names": dong.nlargest(5, col)["행정동_코드_명"].str.replace("?", "·", regex=False).tolist()}
            for label, col in (("total", "지출_총금액"),
                               ("exclude3", "교통_여가_기타제외_지출_총금액"),
                               ("food_grocery", "음식_식료품_지출_총금액"),
                               ("food", "음식_지출_총금액"))
        },
    },
    "top5_total_spend_dongs": [
        {"name": row["행정동_코드_명"], "total_trillion_krw": round(row["지출_총금액"] / 1e12, 3),
         "leisure_share": round(row["여가_문화_지출_총금액"] / row["지출_총금액"], 4)}
        for _, row in top_total.iterrows()
    ],
    "top5_food_spend_dongs": [
        {"name": row["행정동_코드_명"], "food_100m_krw": round(row["음식_지출_총금액"] / 1e8, 1)}
        for _, row in consumption_q4.nlargest(5, "음식_지출_총금액").iterrows()
    ],
    "q4_trade_panel": {"rows": len(panel), "trade_areas": panel["상권_코드"].nunique(),
                       "dongs_with_sales": panel["행정동_코드"].nunique(),
                       "dong_industry_rows": len(dong_industry),
                       "trade_foot_missing_rows": int(panel["총_유동인구_수"].isna().sum())},
    "industry_dong_examples": selected,
    "industry_trade_area_examples": trade_selected,
    "coffee_food_quartiles": {
        label: {"dongs": len(group), "coffee_sales_observed": int(group["coffee_sales"].notna().sum()),
                "median_shops_when_observed": round(group["coffee_shops"].median(), 1)}
        for label, group in (("low_food", coffee_dong.loc[coffee_dong["음식_지출_총금액"] <= food_q25]),
                             ("high_food", coffee_dong.loc[coffee_dong["음식_지출_총금액"] >= food_q75]))
    },
    "coffee": {"food_spend_vs_sales_spearman": round(coffee_rho, 4),
               "food_spend_vs_sales_spearman_below70": round(coffee_other_rho, 4),
               "below70_dongs_with_coffee_sales": len(coffee_other),
               "food_spend_vs_shops_spearman": round(coffee[["음식_지출_총금액", "coffee_shops"]].corr(method="spearman").iloc[0, 1], 4),
               "dongs_with_at_least_10_shops": int((coffee["coffee_shops"] >= 10).sum()),
               "median_sales_per_shop_krw_at_least_10": round((coffee.loc[coffee["coffee_shops"] >= 10, "coffee_sales"] /
                                                                 coffee.loc[coffee["coffee_shops"] >= 10, "coffee_shops"]).median())},
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
