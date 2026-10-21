import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
import json

# Setup Korean font
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "processed" / "eda_reclassified"
IMG_DIR = BASE_DIR / "images" / "eda_reclassified"
IMG_DIR.mkdir(parents=True, exist_ok=True)

print("Generating EDA Reclassified charts...")

# 1. Common Group Sales & Stores
df1 = pd.read_csv(DATA_DIR / "01_공통그룹별_상권매출_점포현황.csv", encoding="utf-8-sig")

fig, ax1 = plt.subplots(figsize=(12, 6))
bars = ax1.bar(df1["공통_그룹"], df1["연간매출(조원)"], color="#4A90E2", alpha=0.85, label="연간 매출액(조원)")
ax1.set_ylabel("연간 매출액 (조 원)", color="#4A90E2", fontsize=12, fontweight="bold")
ax1.set_xticklabels(df1["공통_그룹"], rotation=30, ha="right", fontsize=10)
ax1.grid(axis='y', linestyle='--', alpha=0.4)

ax2 = ax1.twinx()
lines = ax2.plot(df1["공통_그룹"], df1["점포_수"] / 1000, color="#E94E77", marker="o", linewidth=2.5, markersize=7, label="점포 수(천 개)")
ax2.set_ylabel("점포 수 (천 개)", color="#E94E77", fontsize=12, fontweight="bold")

# Annotate bars
for bar in bars:
    y = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, y + 0.3, f"{y:.1f}조", ha='center', va='bottom', fontsize=9, fontweight="bold")

plt.title("2025년 12개 공통 그룹별 서울 상권 추정매출 및 점포 수 현황", fontsize=14, fontweight="bold", pad=15)
fig.tight_layout()
plt.savefig(IMG_DIR / "01_공통그룹별_상권매출_점포수.png", dpi=200)
plt.close()

# 2. Store Net Change (순증감)
fig, ax = plt.subplots(figsize=(11, 5.5))
colors = ["#2ECC71" if x > 0 else "#E74C3C" for x in df1["순증감_점포수"]]
bars = ax.barh(df1["공통_그룹"], df1["순증감_점포수"], color=colors, alpha=0.85)

ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
ax.set_xlabel("2025년 점포 수 순증감 (개업 - 폐업)", fontsize=11, fontweight="bold")
ax.grid(axis='x', linestyle='--', alpha=0.4)

for bar in bars:
    w = bar.get_width()
    ha = 'left' if w > 0 else 'right'
    offset = 50 if w > 0 else -50
    ax.text(w + offset, bar.get_y() + bar.get_height()/2, f"{w:+d}개", ha=ha, va='center', fontsize=9, fontweight="bold")

plt.title("2025년 공통 그룹별 점포 수 순증감 (성장 업종 vs 감소 업종)", fontsize=13, fontweight="bold", pad=12)
ax.invert_yaxis()
fig.tight_layout()
plt.savefig(IMG_DIR / "02_공통그룹별_점포순증감.png", dpi=200)
plt.close()

# 3. Two-Track Comparison Chart
df3 = pd.read_csv(DATA_DIR / "03_투트랙_비교_요약.csv", encoding="utf-8-sig")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Donut chart for spend share
labels = ['특수 허브 상권군 (24개동)\n76.3%', '일반 상권군 (401개동)\n23.7%']
sizes = [76.3, 23.7]
ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=['#F39C12', '#3498DB'], explode=(0.08, 0),
        textprops={'fontsize': 10, 'fontweight': 'bold'}, wedgeprops=dict(width=0.4, edgecolor='w'))
ax1.set_title("서울 전체 카드 지출액 점유율 비교\n(24개동이 76.3% 차지)", fontsize=12, fontweight="bold")

# Bar chart for Offline Sales vs Online Distorted Share
groups = ["일반 상권군 (401개동)", "특수 허브 상권군 (24개동)"]
offline_sales_median = [207.1, 1232.3] # 억원
bar_c = ax2.bar(groups, offline_sales_median, color=['#3498DB', '#F39C12'], alpha=0.85, width=0.5)
ax2.set_ylabel("행정동당 실제 상권 외식매출 중앙값 (억 원)", fontsize=11, fontweight="bold")
ax2.grid(axis='y', linestyle='--', alpha=0.4)

for b in bar_c:
    y = b.get_height()
    ax2.text(b.get_x() + b.get_width()/2, y + 20, f"{y:,.1f}억 원", ha='center', va='bottom', fontsize=10, fontweight="bold")

ax2.set_title("실제 오프라인 상권 외식매출 중앙값 비교\n(특수 상권군이 일반동의 6배 규모)", fontsize=12, fontweight="bold")

fig.tight_layout()
plt.savefig(IMG_DIR / "03_투트랙_분포비교.png", dpi=200)
plt.close()

# 4. Top Opportunity Dongs by Sector
with open(DATA_DIR / "04_일반상권_공통그룹별_유망동.json", encoding="utf-8") as f:
    opp_dict = json.load(f)

fig, axes = plt.subplots(2, 2, figsize=(13, 9))
key_sectors = [("외식", axes[0, 0], "#E67E22"), ("식료품", axes[0, 1], "#27AE60"),
               ("교육", axes[1, 0], "#2980B9"), ("생활용품", axes[1, 1], "#8E44AD")]

for sector, ax, col in key_sectors:
    items = opp_dict[sector]
    names = [it["행정동_코드_명"] for it in items][::-1]
    gaps = [it[f"소비갭_{sector}"] / 1e8 for it in items][::-1] # 억원
    
    b = ax.barh(names, gaps, color=col, alpha=0.85)
    ax.set_title(f"[{sector}] 일반상권 소비 갭(초과수요) TOP 5", fontsize=11, fontweight="bold")
    ax.set_xlabel("소비 갭 (배후소비 - 상권매출, 억 원)", fontsize=9)
    ax.grid(axis='x', linestyle='--', alpha=0.4)
    
    for bar in b:
        w = bar.get_width()
        ax.text(w + max(gaps)*0.02, bar.get_y() + bar.get_height()/2, f"{w:,.0f}억", ha='left', va='center', fontsize=9, fontweight="bold")

fig.tight_layout()
plt.savefig(IMG_DIR / "04_일반상권_업종별_소비갭_TOP5.png", dpi=200)
plt.close()

print("All 4 charts generated successfully!")
