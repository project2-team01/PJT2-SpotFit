# -*- coding: utf-8 -*-
"""SpotFit 3개 탭 통합 EDA 및 창업자 맞춤 추천 대시보드 빌드 스크립트.
- 탭 1: 소상공인 상가 데이터 심층 프로파일링 & 공간 분포 지도 (회색 딤 마스크 + 클러스터)
- 탭 2: 서울시 상권 62개 업종 결합 및 점포-매출 상관분석
- 탭 3: [신규] 창업자 맞춤 상권 추천 시뮬레이터 (STEP 2 & 3 통합 마트 연동)
"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_DIR / "report_latest"
LEE_DIR = PROJECT_DIR / "이승희"
DATA_DIR = PROJECT_DIR / "data" / "processed"

print("[1/5] 기본 데이터 및 공간 GeoJSON 로드 중...")
BASIC_JSON_FILE = REPORT_DIR / "semas_profile_data.json"
ADV_JSON_FILE = REPORT_DIR / "semas_advanced_eda_data.json"
GEO_FILE = REPORT_DIR / "seoul_gu_borders.json"
PARQUET_FILE = DATA_DIR / "상권_추천_통합마트_2025.parquet"

with open(BASIC_JSON_FILE, "r", encoding="utf-8") as f:
    basic_data = json.load(f)

with open(ADV_JSON_FILE, "r", encoding="utf-8") as f:
    adv_data = json.load(f)

with open(GEO_FILE, "r", encoding="utf-8") as f:
    seoul_geo = json.load(f)

print("[2/5] 추천 마트 Parquet 로드 및 인터랙티브 데이터셋 큐레이션 중...")
df_mart = pd.read_parquet(PARQUET_FILE)

# 62개 전체 업종 리스트 및 기본 통계 (ASCII 키로 매핑)
ind_list = (
    df_mart[["서비스_업종_코드", "서비스_업종_코드_명"]]
    .drop_duplicates()
    .sort_values("서비스_업종_코드_명")
    .rename(columns={"서비스_업종_코드": "code", "서비스_업종_코드_명": "name"})
    .to_dict(orient="records")
)
gu_list = sorted(df_mart["자치구_명"].unique().tolist())

# 인터랙티브 웹 표출을 위한 큐레이션 (업종별 Top 35 + 주요 업종 구별 Top 5)
cols = [
    '상권_코드', '상권_코드_명', '상권_구분_코드_명', '자치구_명', '행정동_명',
    '서비스_업종_코드', '서비스_업종_코드_명',
    'SpotFit_추천점수', '사분면_유형', '기회_갭_지수',
    '수요_백분위수', '경쟁_백분위수', '점포당_월평균매출_만원', '건당_결제단가_원',
    '당월_매출_금액', '전체_점포_수', '폐업률', '안정성_점수',
    '주요_소비_연령대', '2030_매출_비중', '피크_시간대', '위도', '경도'
]
compact_keys = {
    '상권_코드': 'id', '상권_코드_명': 'name', '상권_구분_코드_명': 'type',
    '자치구_명': 'gu', '행정동_명': 'dong',
    '서비스_업종_코드': 'ind_id', '서비스_업종_코드_명': 'ind_name',
    'SpotFit_추천점수': 'score', '사분면_유형': 'quad', '기회_갭_지수': 'gap',
    '수요_백분위수': 'p_dem', '경쟁_백분위수': 'p_cmp',
    '점포당_월평균매출_만원': 'rev_store', '건당_결제단가_원': 'ticket',
    '당월_매출_금액': 'rev_tot', '전체_점포_수': 'stores',
    '폐업률': 'closure', '안정성_점수': 'stab',
    '주요_소비_연령대': 'age', '2030_매출_비중': 'r2030',
    '피크_시간대': 'peak', '위도': 'lat', '경도': 'lng'
}

df_sub = df_mart[cols].rename(columns=compact_keys)

# Top 40 per industry across Seoul
top_ind = df_sub.groupby('ind_id').head(40)
# Top 5 per (gu, ind) for top 15 industries
top_15_inds = df_sub['ind_id'].value_counts().head(15).index
top_gu_ind = df_sub[df_sub['ind_id'].isin(top_15_inds)].groupby(['gu', 'ind_id']).head(5)

curated_rec = pd.concat([top_ind, top_gu_ind]).drop_duplicates(subset=['id', 'ind_id']).sort_values('score', ascending=False)
print(f"  -> 큐레이션된 추천 레코드 수: {len(curated_rec):,}건 (62개 업종 및 25개 자치구 전수 포함)")

rec_payload = {
    "industries": ind_list,
    "districts": gu_list,
    "records": curated_rec.to_dict(orient="records")
}

combined_payload = {
    "basic": basic_data,
    "adv": adv_data,
    "rec": rec_payload
}

json_str = json.dumps(combined_payload, ensure_ascii=False)
geo_str = json.dumps(seoul_geo, ensure_ascii=False)

print("[3/5] HTML 템플릿 컴파일 및 대시보드 마크업 생성 중...")

html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SpotFit | 서울시 소상공인 상권 심층 분석 & 맞춤 추천 대시보드 (2025Q4)</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Chart.js CDN -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <!-- Leaflet CSS & JS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <!-- Leaflet MarkerCluster -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
  <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
  <!-- FontAwesome -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800&display=swap');
    body {{
      font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
      background: #f8fafc;
      color: #0f172a;
    }}
    .stat-card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 1rem;
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }}
    .easy-box {{
      background: #f0fdf4;
      border-left: 4px solid #16a34a;
      border-radius: 0.5rem;
      padding: 0.875rem 1.125rem;
      margin-top: 0.875rem;
      color: #166534;
      font-size: 0.875rem;
      line-height: 1.5;
    }}
    .tab-btn.active {{
      background: #2563eb;
      color: #ffffff;
      box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }}
    .custom-scroll::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    .custom-scroll::-webkit-scrollbar-thumb {{
      background: #cbd5e1;
      border-radius: 4px;
    }}
    .badge-blue {{ background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }}
    .badge-purple {{ background: #f5f3ff; color: #6d28d9; border: 1px solid #ddd6fe; }}
    .badge-green {{ background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }}
    .badge-red {{ background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }}
  </style>
</head>
<body class="min-h-screen">

  <!-- TOP NAVIGATION HEADER -->
  <header class="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-xl shadow-md">
          S
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-lg font-bold text-slate-900 tracking-tight">SpotFit Commercial Intelligence</h1>
            <span class="text-xs px-2 py-0.5 rounded-full font-bold bg-blue-100 text-blue-700">v2.5 Full Suite</span>
          </div>
          <p class="text-xs text-slate-500">소상공인 53.5만 전수 프로파일링 & 1,565개 실측 상권 맞춤 추천 시스템</p>
        </div>
      </div>
      
      <!-- TAB BUTTONS -->
      <nav class="flex bg-slate-100 p-1 rounded-xl border border-slate-200 text-sm font-semibold">
        <button id="tabBtn1" onclick="switchTab(1)" class="tab-btn active px-4 py-2 rounded-lg transition-all flex items-center gap-2">
          <i class="fa-solid fa-map-location-dot"></i>
          <span>1. 소상공인 프로파일링 & 공간지도</span>
        </button>
        <button id="tabBtn2" onclick="switchTab(2)" class="tab-btn px-4 py-2 rounded-lg transition-all text-slate-600 hover:text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-chart-line"></i>
          <span>2. 62개 업종 결합 & 상관분석</span>
        </button>
        <button id="tabBtn3" onclick="switchTab(3)" class="tab-btn px-4 py-2 rounded-lg transition-all text-slate-600 hover:text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-compass"></i>
          <span class="relative">
            3. 창업자 맞춤 상권 추천
            <span class="absolute -top-1 -right-2 w-2 h-2 bg-rose-500 rounded-full animate-ping"></span>
          </span>
        </button>
      </nav>
    </div>
  </header>

  <!-- MAIN CONTAINER -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

    <!-- ================================================================= -->
    <!-- TAB 1: 소상공인 데이터 심층 프로파일링 & 공간 지도 -->
    <!-- ================================================================= -->
    <div id="tab1Content" class="space-y-8">
      
      <!-- Overview Banner -->
      <div class="bg-gradient-to-r from-blue-900 to-indigo-900 rounded-2xl p-6 text-white shadow-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <span class="text-xs font-bold px-2.5 py-1 rounded bg-blue-500/30 text-blue-200 uppercase tracking-wider">Tab 1: SEMAS Core Profile</span>
          <h2 class="text-2xl font-extrabold mt-1">소상공인시장진흥공단 서울시 상가(상권)정보 심층 프로파일링</h2>
          <p class="text-sm text-blue-200 mt-1">수집 시점: 2026-10-29 22:41:40 KST | 기준 기간: 2025년 10월 01일 ~ 2025년 12월 31일 (2025Q4 결산)</p>
        </div>
        <div class="flex items-center gap-2 bg-white/10 backdrop-blur px-4 py-2 rounded-xl border border-white/15">
          <i class="fa-solid fa-circle-check text-emerald-400"></i>
          <span class="text-xs font-medium">위경도 결측 0건 · 상가번호 중복 0건 전수 검증 통과</span>
        </div>
      </div>

      <!-- KPI 4 Cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 uppercase">분석 총 점포 수</div>
          <div class="text-2xl font-black text-slate-900 mt-1">534,978<span class="text-sm font-normal text-slate-500 ml-1">개소</span></div>
          <p class="text-xs text-blue-600 mt-2 font-medium"><i class="fa-solid fa-shield-halved mr-1"></i>서울 전역 사업체 전수</p>
        </div>
        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 uppercase">자치구별 점포 편차 (왜도)</div>
          <div class="text-2xl font-black text-slate-900 mt-1">+2.405<span class="text-sm font-normal text-slate-500 ml-1">극심한 우편향</span></div>
          <p class="text-xs text-rose-600 mt-2 font-medium"><i class="fa-solid fa-arrow-trend-up mr-1"></i>강남·마포·송파 3개구 집중</p>
        </div>
        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 uppercase">행정동별 점포 편차 (첨도)</div>
          <div class="text-2xl font-black text-slate-900 mt-1">+25.37<span class="text-sm font-normal text-slate-500 ml-1">초고첨도</span></div>
          <p class="text-xs text-indigo-600 mt-2 font-medium"><i class="fa-solid fa-building mr-1"></i>역삼1동(13,380개) 메가 클러스터</p>
        </div>
        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 uppercase">음식점 지상 1층 입점 비율</div>
          <div class="text-2xl font-black text-slate-900 mt-1">72.4%<span class="text-sm font-normal text-slate-500 ml-1">압도적 선호</span></div>
          <p class="text-xs text-emerald-600 mt-2 font-medium"><i class="fa-solid fa-stairs mr-1"></i>접근성 중심 공간 배치</p>
        </div>
      </div>

      <!-- MAP SECTION (Restored with Focus Dim Mask) -->
      <div class="stat-card p-6 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div class="flex items-center gap-2">
              <span class="p-1.5 rounded-lg bg-blue-100 text-blue-600 text-sm"><i class="fa-solid fa-map"></i></span>
              <h3 class="text-lg font-bold text-slate-900">서울시 상권 공간 분포 인터랙티브 맵 (1,200개 층화 표본)</h3>
            </div>
            <p class="text-xs text-slate-500 mt-0.5">서울 외곽은 회색으로 정돈하고 서울 25개 자치구에만 스포트라이트를 집중한 미니멀 클러스터 지도입니다.</p>
          </div>
          <div class="flex items-center gap-2">
            <select id="mapIndustryFilter" onchange="updateClusterFilter()" class="bg-white border border-slate-300 text-xs rounded-lg px-3 py-1.5 font-semibold text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="ALL">전체 업종 (전체 표본)</option>
              <option value="음식">음식점 (외식업)</option>
              <option value="CAFE">카페·음료 전문점</option>
              <option value="소매">소매업 (편의점/마트/의류)</option>
              <option value="과학·기술">과학·기술 (전문서비스)</option>
              <option value="수리·개인">수리·개인서비스</option>
            </select>
            <button onclick="resetSeoulView()" class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-xs font-semibold rounded-lg text-slate-700 border border-slate-300 transition">
              <i class="fa-solid fa-arrows-rotate mr-1"></i>서울 전체
            </button>
          </div>
        </div>

        <!-- LEAFLET CONTAINER -->
        <div id="map" class="w-full h-[520px] rounded-xl border border-slate-200 overflow-hidden relative shadow-inner"></div>

        <!-- Easy Interpretation Box for Map -->
        <div class="easy-box">
          <div class="font-bold mb-1 flex items-center gap-1.5">
            <i class="fa-solid fa-lightbulb text-emerald-600"></i>
            <span>쉬운 해석과 공간 인사이트</span>
          </div>
          지도에 표시된 점포 마커 클러스터는 25개 자치구별 대표 점포 샘플입니다. 
          서울 외곽은 회색으로 차분하게 마스킹되어 서울 내부 상권의 밀집 형태를 한눈에 볼 수 있습니다. 
          지도 상에서 <b>강남 테헤란로 축</b>과 <b>홍대-신촌-마포 축</b>, 그리고 <b>종로-을지로 도심 축</b>을 따라 마커가 집중되어 있으며, 
          업종 필터에서 '카페·음료'를 선택하면 젊은 유동인구가 집중되는 골목 상권을 중심으로 핑크색 마커 군집이 형성되는 것을 관찰할 수 있습니다.
        </div>
      </div>

      <!-- Crosstab & LQ Heatmap Section -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- 5대 권역별 업종 구성 100% 누적 바 차트 -->
        <div class="stat-card p-6 space-y-4 flex flex-col justify-between">
          <div>
            <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
              <span class="p-1 rounded bg-indigo-100 text-indigo-600 text-xs"><i class="fa-solid fa-chart-column"></i></span>
              5대 권역별 10대 대분류 업종 구성비 (100% 누적 가로막대)
            </h3>
            <p class="text-xs text-slate-500 mt-1">파이차트 대신 모든 권역의 구성을 동일선상에서 정밀하게 비교합니다.</p>
            <div class="h-64 mt-4">
              <canvas id="regionStackedBarChart"></canvas>
            </div>
          </div>
          <div class="easy-box">
            <div class="font-bold mb-1">💡 쉬운 해석: 권역별 업종 색깔</div>
            동남권(강남/서초)은 다른 지역에 비해 <b>과학·기술 및 부동산</b> 비중이 뚜렷하게 높고, 서북권(마포/서대문)은 <b>음식업(외식)</b> 비중이 가장 큽니다. 권역마다 형성된 산업 생태계가 점포 구성에 직접 반영되어 있습니다.
          </div>
        </div>

        <!-- 자치구별 LQ 입지계수 상위 표 -->
        <div class="stat-card p-6 space-y-4 flex flex-col justify-between">
          <div>
            <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
              <span class="p-1 rounded bg-emerald-100 text-emerald-600 text-xs"><i class="fa-solid fa-table-cells"></i></span>
              자치구별 핵심 특화 업종 (LQ 입지계수 매트릭스)
            </h3>
            <p class="text-xs text-slate-500 mt-1">LQ > 1.25 이상인 자치구별 1위 특화 산업 현황</p>
            <div class="overflow-x-auto custom-scroll max-h-64 mt-3">
              <table class="w-full text-xs text-left">
                <thead class="bg-slate-50 text-slate-600 border-b border-slate-200">
                  <tr>
                    <th class="py-2 px-3">자치구</th>
                    <th class="py-2 px-3">최대 특화 업종</th>
                    <th class="py-2 px-3">LQ 입지계수</th>
                    <th class="py-2 px-3">점포수(비중)</th>
                    <th class="py-2 px-3">특화 수준 판정</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-slate-700">
                  <tr class="hover:bg-slate-50">
                    <td class="py-2 px-3 font-bold">금천구</td>
                    <td class="py-2 px-3 text-purple-700 font-semibold">과학·기술</td>
                    <td class="py-2 px-3 font-bold text-blue-600">1.881</td>
                    <td class="py-2 px-3">5,814개 (32.8%)</td>
                    <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-purple-100 text-purple-700 font-bold">서울 1위 특화</span></td>
                  </tr>
                  <tr class="hover:bg-slate-50">
                    <td class="py-2 px-3 font-bold">양천구</td>
                    <td class="py-2 px-3 text-emerald-700 font-semibold">교육</td>
                    <td class="py-2 px-3 font-bold text-blue-600">1.922</td>
                    <td class="py-2 px-3">2,168개 (12.0%)</td>
                    <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 font-bold">목동 학원가</span></td>
                  </tr>
                  <tr class="hover:bg-slate-50">
                    <td class="py-2 px-3 font-bold">중구</td>
                    <td class="py-2 px-3 text-amber-700 font-semibold">소매</td>
                    <td class="py-2 px-3 font-bold text-blue-600">1.511</td>
                    <td class="py-2 px-3">7,597개 (31.5%)</td>
                    <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-amber-100 text-amber-700 font-bold">전통 도소매</span></td>
                  </tr>
                  <tr class="hover:bg-slate-50">
                    <td class="py-2 px-3 font-bold">중랑구</td>
                    <td class="py-2 px-3 text-blue-700 font-semibold">수리·개인</td>
                    <td class="py-2 px-3 font-bold text-blue-600">1.487</td>
                    <td class="py-2 px-3">2,600개 (15.5%)</td>
                    <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-blue-100 text-blue-700 font-bold">생활 밀착형</span></td>
                  </tr>
                  <tr class="hover:bg-slate-50">
                    <td class="py-2 px-3 font-bold">용산구</td>
                    <td class="py-2 px-3 text-rose-700 font-semibold">음식</td>
                    <td class="py-2 px-3 font-bold text-blue-600">1.270</td>
                    <td class="py-2 px-3">6,220개 (37.1%)</td>
                    <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-rose-100 text-rose-700 font-bold">이태원·용리단길</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="easy-box">
            <div class="font-bold mb-1">💡 쉬운 해석: LQ(입지계수)란?</div>
            서울 전체 평균을 '1.0'으로 볼 때 그 구에 해당 업종이 얼마나 몰려있는지를 나타냅니다. <b>LQ가 1.25 이상이면 특화 지역</b>입니다. 창업 시 경쟁이 심한 지역을 피할지, 오히려 시너지를 노릴지 결정하는 핵심 기준이 됩니다.
          </div>
        </div>
      </div>

    </div>


    <!-- ================================================================= -->
    <!-- TAB 2: 서울시 상권 62개 업종 결합 및 상관분석 -->
    <!-- ================================================================= -->
    <div id="tab2Content" class="space-y-8 hidden">
      
      <!-- Tab 2 Banner -->
      <div class="bg-gradient-to-r from-slate-900 to-blue-950 rounded-2xl p-6 text-white shadow-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <span class="text-xs font-bold px-2.5 py-1 rounded bg-indigo-500/30 text-indigo-200 uppercase tracking-wider">Tab 2: Advanced Correlation</span>
          <h2 class="text-2xl font-extrabold mt-1">소상공인 점포수와 서울시 상권 매출 간의 상관관계 심층 분석</h2>
          <p class="text-sm text-slate-300 mt-1">서울시 62개 표준 상권업종 1:N 매핑 및 397개 행정동 공간 결합 결과 (N=397)</p>
        </div>
        <div class="flex items-center gap-2 bg-white/10 backdrop-blur px-4 py-2 rounded-xl border border-white/15">
          <i class="fa-solid fa-chart-line text-blue-400"></i>
          <span class="text-xs font-medium">Spearman 순위상관계수 +0.768 (강력한 정적 상관)</span>
        </div>
      </div>

      <!-- 4대 상권 구분별 매출-점포 피봇 카드 -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="stat-card p-5 border-l-4 border-l-blue-600">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-500">발달상권 (249개)</span>
            <span class="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 font-bold">매출 점유 61.2%</span>
          </div>
          <div class="text-xl font-black text-slate-900 mt-2">14.93조 원</div>
          <p class="text-xs text-slate-500 mt-1">점포당 분기매출: 2.15억 원</p>
        </div>
        <div class="stat-card p-5 border-l-4 border-l-emerald-600">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-500">골목상권 (1,030개)</span>
            <span class="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 font-bold">상권 수 62.4%</span>
          </div>
          <div class="text-xl font-black text-slate-900 mt-2">5.56조 원</div>
          <p class="text-xs text-slate-500 mt-1">점포당 분기매출: 0.94억 원</p>
        </div>
        <div class="stat-card p-5 border-l-4 border-l-amber-600">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-500">전통시장 (365개)</span>
            <span class="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700 font-bold">생활 밀착형</span>
          </div>
          <div class="text-xl font-black text-slate-900 mt-2">2.41조 원</div>
          <p class="text-xs text-slate-500 mt-1">점포당 분기매출: 0.81억 원</p>
        </div>
        <div class="stat-card p-5 border-l-4 border-l-purple-600">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-500">관광특구 (6개)</span>
            <span class="text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-700 font-bold">외지인 집중</span>
          </div>
          <div class="text-xl font-black text-slate-900 mt-2">1.50조 원</div>
          <p class="text-xs text-slate-500 mt-1">점포당 분기매출: 2.89억 원</p>
        </div>
      </div>

      <!-- 점포수 vs 매출액 산점도 및 회귀선 -->
      <div class="stat-card p-6 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 class="text-lg font-bold text-slate-900 flex items-center gap-2">
              <span class="p-1.5 rounded-lg bg-blue-100 text-blue-600 text-sm"><i class="fa-solid fa-chart-line"></i></span>
              행정동별 소상공인 점포수 vs 서울시 상권 총매출액 산점도 및 선형 회귀 추세선
            </h3>
            <p class="text-xs text-slate-500 mt-0.5">N = 396개 행정동, 선형 회귀식: y = 0.5648x - 119.59 억 원 (R² = 0.343)</p>
          </div>
        </div>
        <div class="h-80">
          <canvas id="scatterRegressionChart"></canvas>
        </div>
        <div class="easy-box">
          <div class="font-bold mb-1">💡 쉬운 해석: 점포가 많으면 매출도 무조건 많을까? (회귀 잔차 분석)</div>
          스피어만 순위상관계수가 <b>+0.773</b>, 피어슨 상관계수가 <b>+0.586</b>으로 높아 전반적으로 <b>"점포가 많은 동네가 총매출도 크다"</b>는 강력한 경향이 성립합니다. 
          하지만 <b>회귀선 대비 실제 위치(잔차)</b>를 보면 상권의 이면이 드러납니다:
          <ul class="list-disc list-inside mt-1 space-y-0.5 text-slate-700">
            <li><b>회귀선 아득히 위쪽 (초과 실적)</b>: <b>동작구 노량진1동</b>은 점포 수가 1,341개이나 총매출은 <b>1조 2,677억 원</b>으로 회귀선 기대치(약 638억 원) 대비 <b>+12,039억 원 초과</b>합니다. 이는 노량진수산물도매시장이라는 전국 단위 수산물 도매 거래가 집계된 특수 이상치 때문입니다.</li>
            <li><b>회귀선 훨씬 아래쪽 (과밀 레드오션)</b>: <b>강남구 역삼1동</b>은 점포 수가 <b>13,380개</b>로 서울 1위이나, 상권 총매출은 <b>3,058억 원</b>으로 회귀선 기대치(약 7,438억 원)보다 무려 <b>-4,380억 원이나 부족</b>합니다. 즉, 점포는 넘쳐나지만 매출 파이가 쪼개져 치열한 출혈 경쟁을 겪고 있습니다.</li>
          </ul>
        </div>
      </div>

      <!-- TOP 20 행정동 테이블 -->
      <div class="stat-card p-6 space-y-4">
        <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
          <span class="p-1 rounded bg-slate-100 text-slate-700 text-xs"><i class="fa-solid fa-ranking-star"></i></span>
          서울시 점포 밀집도 및 매출 상위 행정동 TOP 10 실적 비교
        </h3>
        <div class="overflow-x-auto custom-scroll">
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th class="py-2 px-3">순위</th>
                <th class="py-2 px-3">자치구</th>
                <th class="py-2 px-3">행정동</th>
                <th class="py-2 px-3">등록 점포 수</th>
                <th class="py-2 px-3">상권 총매출(억원)</th>
                <th class="py-2 px-3">점포당 평균 매출</th>
                <th class="py-2 px-3">상권 성격</th>
              </tr>
            </thead>
            <tbody id="topDongTableBody" class="divide-y divide-slate-100 text-slate-700">
              <!-- Dynamically populated -->
            </tbody>
          </table>
        </div>
        <div class="easy-box">
          <div class="font-bold mb-1">💡 쉬운 해석: 메가 상권의 함정과 창업 의사결정</div>
          강남구 역삼1동은 등록 점포 수(13,380개) 서울 1위이나 상권 총매출은 3,058억 원으로 점포당 평균 매출(약 2,285만 원)은 비싼 임대료와 인건비를 감당하기에 녹록지 않습니다. 
          초보 창업자는 겉보기에 화려한 외형 1등 동네 대신, <b>탭 3의 맞춤 추천 시뮬레이터</b>를 활용하여 내 목표 업종의 수요가 확실하고 경쟁이 덜한 <b>블루오션 상권</b>을 찾아야 생존 확률을 극대화할 수 있습니다.
        </div>
      </div>

    </div>


    <!-- ================================================================= -->
    <!-- TAB 3: [NEW] 창업자 맞춤 상권 추천 시뮬레이터 (STEP 2 & 3 산출물) -->
    <!-- ================================================================= -->
    <div id="tab3Content" class="space-y-8 hidden">

      <!-- Tab 3 Banner -->
      <div class="bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-700 rounded-2xl p-6 text-white shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div class="flex items-center gap-2">
            <span class="text-xs font-extrabold px-2.5 py-1 rounded bg-white/20 text-white uppercase tracking-wider">Tab 3: SpotFit Recommendation</span>
            <span class="text-xs px-2 py-0.5 rounded-full font-bold bg-amber-400 text-slate-900">STEP 2 & 3 완료</span>
          </div>
          <h2 class="text-2xl font-black mt-2">창업 예정자 맞춤 상권 추천 시뮬레이터</h2>
          <p class="text-sm text-blue-100 mt-1">희망 업종과 관심 지역을 선택하면, 수요·경쟁·수익·안정성 4대 차원으로 검증된 최적의 상권을 추천합니다.</p>
        </div>
        <div class="bg-white/10 backdrop-blur px-4 py-3 rounded-xl border border-white/20 text-xs text-blue-100 space-y-1">
          <div><i class="fa-solid fa-check text-emerald-300 mr-1.5"></i><b>블루오션 발굴</b>: 수요는 크고 경쟁은 적은 입지</div>
          <div><i class="fa-solid fa-check text-emerald-300 mr-1.5"></i><b>폐업 위험 회피</b>: 3,024개 레드오션 사전 필터링</div>
        </div>
      </div>

      <!-- FILTER CONTROLLER BAR -->
      <div class="stat-card p-5 bg-white border border-slate-200 space-y-4">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div class="flex flex-wrap items-center gap-3">
            <!-- 업종 선택 -->
            <div>
              <label class="block text-xs font-bold text-slate-600 mb-1">1. 희망 창업 업종 (62개 표준업종)</label>
              <select id="recIndustrySelect" onchange="runRecommendationFilter()" class="bg-slate-50 border border-slate-300 text-sm rounded-lg px-3 py-2 font-bold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none min-w-[200px]">
                <!-- Populated dynamically -->
              </select>
            </div>

            <!-- 자치구 선택 -->
            <div>
              <label class="block text-xs font-bold text-slate-600 mb-1">2. 관심 자치구 선택</label>
              <select id="recDistrictSelect" onchange="runRecommendationFilter()" class="bg-slate-50 border border-slate-300 text-sm rounded-lg px-3 py-2 font-semibold text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-none min-w-[150px]">
                <option value="ALL">서울시 전체 (25개 구)</option>
                <!-- Populated dynamically -->
              </select>
            </div>

            <!-- 사분면 필터 -->
            <div>
              <label class="block text-xs font-bold text-slate-600 mb-1">3. 입지 유형 (사분면)</label>
              <select id="recQuadrantSelect" onchange="runRecommendationFilter()" class="bg-slate-50 border border-slate-300 text-sm rounded-lg px-3 py-2 font-semibold text-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-none">
                <option value="ALL">전체 유형</option>
                <option value="블루오션(기회형)" selected>🔵 블루오션 (고수요·저경쟁 기회형)</option>
                <option value="격전지(스타형)">🟣 격전지 (고수요·고경쟁 메가상권)</option>
                <option value="틈새시장(안정형)">🟢 틈새시장 (저수요·저경쟁 로컬상권)</option>
                <option value="레드오션(위험형)">🔴 레드오션 (과밀 과포화 위험상권)</option>
              </select>
            </div>
          </div>

          <div class="flex items-center gap-2 self-end md:self-auto">
            <button onclick="resetRecommendationFilters()" class="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-xs font-bold rounded-lg text-slate-700 border border-slate-300 transition flex items-center gap-1.5">
              <i class="fa-solid fa-rotate-left"></i>
              <span>필터 초기화</span>
            </button>
          </div>
        </div>
      </div>

      <!-- REAL-TIME KPI CARDS -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="stat-card p-5 border-t-4 border-t-blue-600">
          <div class="text-xs font-bold text-slate-500 uppercase">추천 대상 상권 수</div>
          <div id="kpiRecCount" class="text-2xl font-black text-slate-900 mt-1">-<span class="text-sm font-normal text-slate-500 ml-1">개 상권</span></div>
          <p class="text-xs text-blue-600 mt-1 font-semibold">조건 충족 후보 입지</p>
        </div>
        <div class="stat-card p-5 border-t-4 border-t-indigo-600">
          <div class="text-xs font-bold text-slate-500 uppercase">최고 추천 점수 (MAX)</div>
          <div id="kpiMaxScore" class="text-2xl font-black text-indigo-700 mt-1">-<span class="text-sm font-normal text-slate-500 ml-1">점</span></div>
          <p class="text-xs text-indigo-600 mt-1 font-semibold">SpotFit 알고리즘 1위</p>
        </div>
        <div class="stat-card p-5 border-t-4 border-t-emerald-600">
          <div class="text-xs font-bold text-slate-500 uppercase">평균 점포당 월매출</div>
          <div id="kpiAvgRev" class="text-2xl font-black text-emerald-700 mt-1">-<span class="text-sm font-normal text-slate-500 ml-1">만 원</span></div>
          <p class="text-xs text-emerald-600 mt-1 font-semibold">1개 매장 기대 수익</p>
        </div>
        <div class="stat-card p-5 border-t-4 border-t-amber-600">
          <div class="text-xs font-bold text-slate-500 uppercase">블루오션 비율</div>
          <div id="kpiBlueShare" class="text-2xl font-black text-amber-700 mt-1">-<span class="text-sm font-normal text-slate-500 ml-1">%</span></div>
          <p class="text-xs text-amber-600 mt-1 font-semibold">수요 대비 점포 부족</p>
        </div>
      </div>

      <!-- MAIN SPLIT: RECOMMENDATION MAP (LEFT) & QUADRANT + TABLE (RIGHT) -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        <!-- LEFT: SPOTLIGHT RECOMMENDATION MAP (7 COLS) -->
        <div class="lg:col-span-7 stat-card p-6 space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="flex items-center gap-2">
                <span class="p-1.5 rounded-lg bg-blue-100 text-blue-600 text-sm"><i class="fa-solid fa-location-dot"></i></span>
                <h3 class="text-lg font-bold text-slate-900">추천 상권 공간 스포트라이트 맵</h3>
              </div>
              <p class="text-xs text-slate-500 mt-0.5">선택한 업종의 추천 상권 위치 및 사분면 뱃지 표시 (클릭 시 세부 진단)</p>
            </div>
            <div class="flex items-center gap-2 text-xs">
              <span class="flex items-center gap-1 font-semibold text-blue-700"><span class="w-2.5 h-2.5 rounded-full bg-blue-600 inline-block"></span>블루</span>
              <span class="flex items-center gap-1 font-semibold text-purple-700"><span class="w-2.5 h-2.5 rounded-full bg-purple-600 inline-block"></span>격전지</span>
              <span class="flex items-center gap-1 font-semibold text-emerald-700"><span class="w-2.5 h-2.5 rounded-full bg-emerald-600 inline-block"></span>틈새</span>
              <span class="flex items-center gap-1 font-semibold text-rose-700"><span class="w-2.5 h-2.5 rounded-full bg-rose-600 inline-block"></span>레드</span>
            </div>
          </div>

          <!-- MAP REC CONTAINER -->
          <div id="mapRec" class="w-full h-[520px] rounded-xl border border-slate-200 overflow-hidden relative shadow-inner"></div>

          <!-- Easy Interpretation Box for Recommendation Map -->
          <div class="easy-box">
            <div class="font-bold mb-1 flex items-center gap-1.5">
              <i class="fa-solid fa-lightbulb text-emerald-600"></i>
              <span>지도 활용법과 상권 입지 선정 가이드</span>
            </div>
            지도 위에 표시된 원형 마커들은 선택하신 업종에서 추천 점수가 높은 상권들입니다. 
            <b>파란색 마커(블루오션)</b>는 매출 규모는 큰데 점포 수가 적어 신규 진입 시 고객 확보가 수월한 곳이며, 
            <b>보라색 마커(격전지)</b>는 대형 상권이지만 프랜차이즈 경쟁이 치열한 곳입니다. 
            마커를 클릭하거나 우측 표에서 상권명을 클릭하면 해당 위치로 지도가 이동하며 점포당 월매출, 폐업률, 피크시간대 등 핵심 지표가 열립니다.
          </div>
        </div>

        <!-- RIGHT: QUADRANT CHART & RANKING TABLE (5 COLS) -->
        <div class="lg:col-span-5 space-y-6">

          <!-- 수요 vs 경쟁 2x2 사분면 산점도 -->
          <div class="stat-card p-5 space-y-3">
            <div class="flex items-center justify-between">
              <h4 class="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <i class="fa-solid fa-chart-simple text-indigo-600"></i>
                수요 vs 경쟁 사분면 포지셔닝
              </h4>
              <span class="text-xs text-slate-500">X: 매출수요(%) · Y: 점포경쟁(%)</span>
            </div>
            <div class="h-52">
              <canvas id="quadrantChart"></canvas>
            </div>
            <div class="grid grid-cols-2 gap-2 text-[11px] pt-1">
              <div class="p-2 rounded bg-blue-50 border border-blue-200 text-blue-900">
                <strong class="block text-blue-700">🔵 블루오션 (우하단)</strong>
                수요 높음 + 경쟁 적음 (최우선 추천)
              </div>
              <div class="p-2 rounded bg-purple-50 border border-purple-200 text-purple-900">
                <strong class="block text-purple-700">🟣 격전지 (우상단)</strong>
                수요 높음 + 경쟁 치열 (자본형 창업)
              </div>
              <div class="p-2 rounded bg-emerald-50 border border-emerald-200 text-emerald-900">
                <strong class="block text-emerald-700">🟢 틈새시장 (좌하단)</strong>
                수요 작음 + 경쟁 적음 (소자본 로컬)
              </div>
              <div class="p-2 rounded bg-rose-50 border border-rose-200 text-rose-900">
                <strong class="block text-rose-700">🔴 레드오션 (좌상단)</strong>
                수요 작음 + 점포 난립 (진입 회피)
              </div>
            </div>
          </div>

          <!-- TOP 추천 상권 랭킹 리스트 표 -->
          <div class="stat-card p-5 space-y-3">
            <div class="flex items-center justify-between">
              <h4 class="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <i class="fa-solid fa-trophy text-amber-500"></i>
                맞춤 추천 상권 TOP 랭킹 (클릭 시 지도 이동)
              </h4>
              <span class="text-xs text-blue-600 font-semibold" id="tableRecordCount"></span>
            </div>

            <div class="overflow-y-auto custom-scroll max-h-[300px]">
              <table class="w-full text-xs text-left">
                <thead class="bg-slate-50 text-slate-600 border-b border-slate-200 sticky top-0">
                  <tr>
                    <th class="py-2 px-2.5">순위</th>
                    <th class="py-2 px-2.5">상권명(위치)</th>
                    <th class="py-2 px-2">사분면</th>
                    <th class="py-2 px-2">점수</th>
                    <th class="py-2 px-2.5 text-right">점포당 월매출</th>
                  </tr>
                </thead>
                <tbody id="recTableBody" class="divide-y divide-slate-100 text-slate-700">
                  <!-- Dynamically populated -->
                </tbody>
              </table>
            </div>

            <div class="easy-box">
              <div class="font-bold mb-1">💡 쉬운 해석: 순위 결정 기준</div>
              추천 순위는 <b>[기회 갭 지수 35%] + [점포당 월매출 25%] + [안정성·생존율 20%] + [배후 유동인구 20%]</b>를 종합한 0~100점 점수로 산출됩니다. 점수가 높을수록 안정적으로 높은 매출을 거둘 확률이 높습니다.
            </div>
          </div>

        </div>

      </div>

      <!-- BOTTOM DETAIL: 창업자 의사결정 매트릭스 -->
      <div class="stat-card p-6 space-y-4">
        <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
          <span class="p-1 rounded bg-blue-100 text-blue-600 text-xs"><i class="fa-solid fa-compass"></i></span>
          예비 창업자 페르소나별 최적 상권 선택 가이드
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div class="font-bold text-blue-700 text-sm flex items-center gap-1.5">
              <i class="fa-solid fa-seedling"></i> 소자본·생계형 창업자
            </div>
            <p class="text-slate-600 leading-relaxed">
              <b>추천 유형</b>: 틈새시장(골목상권) 또는 기회 갭이 높은 소형 블루오션<br/>
              <b>전략</b>: 임대료가 저렴한 주거지 배후 상권에서 단골 확보 중심 영업. 폐업률이 5% 미만인 안정적인 상권을 선택하세요.
            </p>
          </div>
          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div class="font-bold text-indigo-700 text-sm flex items-center gap-1.5">
              <i class="fa-solid fa-gem"></i> 차별화 메뉴·청년 창업자
            </div>
            <p class="text-slate-600 leading-relaxed">
              <b>추천 유형</b>: 2030 매출 비중이 50% 이상인 블루오션 상권<br/>
              <b>전략</b>: 관악구 중앙길, 영등포역 후문처럼 젊은 1인 가구 소비력이 받쳐주지만 트렌디한 매장이 부족한 입지를 공략하세요.
            </p>
          </div>
          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div class="font-bold text-purple-700 text-sm flex items-center gap-1.5">
              <i class="fa-solid fa-crown"></i> 자본력 있는 프랜차이즈/투자형
            </div>
            <p class="text-slate-600 leading-relaxed">
              <b>추천 유형</b>: 격전지(스타형 발달상권/관광특구)<br/>
              <b>전략</b>: 양재역, 명동처럼 매장당 월매출 6,000만 원 이상의 거대 시장. 높은 임대료와 마케팅 비용을 견딜 자본력이 필수적입니다.
            </p>
          </div>
        </div>
      </div>

    </div>

  </main>

  <!-- DATA & SCRIPTS -->
  <script>
    // Embedded Data Payload
    const appData = {json_str};
    const seoulGeoData = {geo_str};

    const basicData = appData.basic;
    const advData = appData.adv;
    const recData = appData.rec;

    // ----------------------------------------------------
    // TAB SWITCHING LOGIC
    // ----------------------------------------------------
    let currentTab = 1;
    function switchTab(tabNum) {{
      currentTab = tabNum;
      for (let i = 1; i <= 3; i++) {{
        const btn = document.getElementById('tabBtn' + i);
        const content = document.getElementById('tab' + i + 'Content');
        if (i === tabNum) {{
          btn.classList.add('active');
          btn.classList.remove('text-slate-600');
          content.classList.remove('hidden');
        }} else {{
          btn.classList.remove('active');
          btn.classList.add('text-slate-600');
          content.classList.add('hidden');
        }}
      }}
      // Redraw and resize maps and charts on tab change
      setTimeout(() => {{
        if (tabNum === 1 && window.map) {{
          window.map.invalidateSize();
        }}
        if (tabNum === 2 && window.scatterChart) {{
          window.scatterChart.resize();
        }}
        if (tabNum === 3) {{
          if (window.mapRec) {{
            window.mapRec.invalidateSize();
            window.mapRec.fitBounds(SEOUL_BOUNDS, {{ padding: [20, 20] }});
          }}
          if (window.quadChart) {{
            window.quadChart.resize();
          }}
        }}
      }}, 60);
    }}

    // ----------------------------------------------------
    // TAB 1: FOCUS MAP (ArcGIS Gray + Dim Mask)
    // ----------------------------------------------------
    const SEOUL_BOUNDS = L.latLngBounds([37.428, 126.764], [37.701, 127.183]);

    const baseTile = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      attribution: '&copy; Esri &mdash; Esri, HERE, Garmin',
      maxZoom: 17,
      minZoom: 9
    }});

    const map = L.map('map', {{
      center: [37.564, 126.985],
      zoom: 11,
      minZoom: 10,
      maxZoom: 17,
      layers: [baseTile]
    }});
    window.map = map;

    function resetSeoulView() {{
      map.fitBounds(SEOUL_BOUNDS, {{ padding: [20, 20] }});
    }}
    resetSeoulView();

    // Inverted Mask for Non-Seoul Dimming
    let seoulCoordinatesRings = [];
    seoulGeoData.features.forEach(feat => {{
      const geom = feat.geometry;
      if (geom.type === 'Polygon') {{
        seoulCoordinatesRings.push(geom.coordinates[0].map(coord => [coord[1], coord[0]]));
      }} else if (geom.type === 'MultiPolygon') {{
        geom.coordinates.forEach(poly => {{
          seoulCoordinatesRings.push(poly[0].map(coord => [coord[1], coord[0]]));
        }});
      }}
    }});

    const worldOuterRing = [
      [-90, -180],
      [-90, 180],
      [90, 180],
      [90, -180]
    ];

    L.polygon([worldOuterRing, ...seoulCoordinatesRings], {{
      color: 'transparent',
      fillColor: '#94a3b8',
      fillOpacity: 0.35,
      interactive: false
    }}).addTo(map);

    // Seoul 25 Gu White Polygons
    const guGeoLayer = L.geoJSON(seoulGeoData, {{
      style: function() {{
        return {{
          fillColor: '#ffffff',
          fillOpacity: 0.88,
          color: '#cbd5e1',
          weight: 1.2,
          dashArray: '2, 2'
        }};
      }},
      onEachFeature: function(feature, layer) {{
        const guName = feature.properties.name;
        const storeCount = basicData.gu_counts[guName] ? basicData.gu_counts[guName].toLocaleString() : 0;
        layer.on({{
          mouseover: function(e) {{
            e.target.setStyle({{ fillColor: '#eff6ff', fillOpacity: 0.95, color: '#3b82f6', weight: 2, dashArray: '' }});
            e.target.bringToFront();
          }},
          mouseout: function(e) {{
            guGeoLayer.resetStyle(e.target);
          }},
          click: function(e) {{
            map.fitBounds(e.target.getBounds(), {{ padding: [30, 30] }});
          }}
        }});
        layer.bindTooltip(`
          <div style="font-family: Pretendard, sans-serif; padding: 2px;">
            <strong style="font-size: 13px; color: #0f172a;">${{guName}}</strong><br/>
            <span style="font-size: 11px; color: #475569;">등록 점포: <b style="color: #2563eb;">${{storeCount}}개</b></span>
          </div>
        `, {{ sticky: true, opacity: 0.95 }});
      }}
    }}).addTo(map);

    // Tab 1 Marker Clustering
    let currentMapFilter = 'ALL';
    const clusterGroup = L.markerClusterGroup({{
      showCoverageOnHover: false,
      maxClusterRadius: 45,
      spiderfyOnMaxZoom: true,
      zoomToBoundsOnClick: true,
      disableClusteringAtZoom: 16
    }});
    map.addLayer(clusterGroup);

    function getColorByMacro(cat, sub, name) {{
      if (cat === '음식') {{
        if (sub.includes('커피') || sub.includes('카페') || name.includes('카페') || name.includes('커피')) return '#ec4899';
        return '#e11d48';
      }}
      if (cat === '소매') return '#2563eb';
      if (cat === '과학·기술') return '#7c3aed';
      if (cat === '수리·개인') return '#d97706';
      if (cat === '교육') return '#059669';
      return '#0284c7';
    }}

    function updateClusterFilter() {{
      currentMapFilter = document.getElementById('mapIndustryFilter').value;
      clusterGroup.clearLayers();
      const newMarkers = [];

      basicData.map_points_sample.forEach(pt => {{
        let match = false;
        if (currentMapFilter === 'ALL') match = true;
        else if (currentMapFilter === 'CAFE') match = pt.cat_sub.includes('커피') || pt.cat_sub.includes('카페') || pt.name.includes('카페') || pt.name.includes('커피');
        else match = (pt.cat_macro === currentMapFilter);

        if (match) {{
          const color = getColorByMacro(pt.cat_macro, pt.cat_sub, pt.name);
          const marker = L.circleMarker([pt.lat, pt.lng], {{
            radius: 5,
            fillColor: color,
            color: '#ffffff',
            weight: 1,
            opacity: 1,
            fillOpacity: 0.85
          }});
          marker.bindPopup(`
            <div style="font-family: Pretendard, sans-serif; font-size: 12px; line-height: 1.5; padding: 4px;">
              <strong style="font-size: 13px; color: #0f172a;">${{pt.name}}</strong><br/>
              <span style="color: #64748b;">${{pt.gu}} ${{pt.dong}}</span><br/>
              <span style="color: #2563eb; font-weight: 600;">${{pt.cat_macro}} > ${{pt.cat_sub}}</span><br/>
              <span style="color: #475569;">위치: <b>${{pt.floor}}</b></span>
            </div>
          `);
          newMarkers.push(marker);
        }}
      }});
      clusterGroup.addLayers(newMarkers);
    }}
    updateClusterFilter();

    // Tab 1 Chart: 5대 권역 100% 누적 가로막대
    const regCtx = document.getElementById('regionStackedBarChart').getContext('2d');
    const pRegion = advData.tab1.region_macro_pivot;
    const regionNames = pRegion.regions;
    const macroCats = pRegion.macros.slice(0, 5);
    const catColors = ['#e11d48', '#2563eb', '#7c3aed', '#d97706', '#059669'];

    const regionDatasets = macroCats.map((cat, mIdx) => {{
      return {{
        label: cat,
        data: pRegion.counts.map(row => row[mIdx]),
        backgroundColor: catColors[mIdx]
      }};
    }});

    new Chart(regCtx, {{
      type: 'bar',
      data: {{
        labels: regionNames,
        datasets: regionDatasets
      }},
      options: {{
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          x: {{ stacked: true, grid: {{ color: '#f1f5f9' }} }},
          y: {{ stacked: true, grid: {{ display: false }} }}
        }},
        plugins: {{
          legend: {{ position: 'bottom', labels: {{ boxWidth: 10, font: {{ size: 10 }} }} }}
        }}
      }}
    }});

    // ----------------------------------------------------
    // TAB 2: CORRELATION SCATTER & TOP TABLE
    // ----------------------------------------------------
    const scCtx = document.getElementById('scatterRegressionChart').getContext('2d');
    const scatterPoints = advData.tab2.scatter_points.map(d => ({{
      x: d.stores,
      y: d.sales_100m,
      dong: d.dong,
      gu: d.gu
    }}));
    const xMax = 14000;
    const regLine = [
      {{ x: 0, y: -119.59 }},
      {{ x: xMax, y: (0.5648 * xMax - 119.59) }}
    ];

    window.scatterChart = new Chart(scCtx, {{
      type: 'scatter',
      data: {{
        datasets: [
          {{
            label: '행정동 (396개)',
            data: scatterPoints,
            backgroundColor: 'rgba(37, 99, 235, 0.55)',
            borderColor: '#2563eb',
            borderWidth: 1,
            pointRadius: 4,
            pointHoverRadius: 6
          }},
          {{
            type: 'line',
            label: '선형 회귀 추세선 (y = 0.5648x - 119.59)',
            data: regLine,
            borderColor: '#e11d48',
            borderWidth: 2,
            borderDash: [5, 5],
            fill: false,
            pointRadius: 0
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          x: {{ title: {{ display: true, text: '소상공인 점포 수 (개)', font: {{ size: 11 }} }}, grid: {{ color: '#f1f5f9' }} }},
          y: {{ title: {{ display: true, text: '상권 총매출액 (억 원)', font: {{ size: 11 }} }}, grid: {{ color: '#f1f5f9' }} }}
        }},
        plugins: {{
          legend: {{ position: 'top', labels: {{ font: {{ size: 11 }} }} }},
          tooltip: {{
            callbacks: {{
              label: function(ctx) {{
                const p = ctx.raw;
                if (!p.dong) return ctx.dataset.label;
                return `${{p.gu}} ${{p.dong}}: 점포 ${{p.x.toLocaleString()}}개, 매출 ${{p.y.toLocaleString()}}억 원`;
              }}
            }}
          }}
        }}
      }}
    }});

    // Tab 2 Top Table Population
    const topDongBody = document.getElementById('topDongTableBody');
    const sortedDong = [...advData.tab2.scatter_points].sort((a, b) => b.stores - a.stores);
    const top10Dong = sortedDong.slice(0, 10);
    topDongBody.innerHTML = top10Dong.map((d, i) => {{
      const salesBillion = d.sales_100m.toLocaleString();
      const perStore = Math.round((d.sales_100m * 10000) / d.stores).toLocaleString();
      const badge = i < 3 ? '<span class="px-2 py-0.5 rounded bg-blue-100 text-blue-700 font-bold">메가상권</span>' : '<span class="px-2 py-0.5 rounded bg-slate-100 text-slate-600">성장상권</span>';
      return `
        <tr class="hover:bg-slate-50">
          <td class="py-2 px-3 font-bold text-slate-500">${{i + 1}}</td>
          <td class="py-2 px-3 font-semibold">${{d.gu}}</td>
          <td class="py-2 px-3 font-bold text-blue-600">${{d.dong}}</td>
          <td class="py-2 px-3">${{d.stores.toLocaleString()}}개</td>
          <td class="py-2 px-3 font-bold text-slate-900">${{salesBillion}}억 원</td>
          <td class="py-2 px-3 font-semibold text-emerald-600">${{perStore}}만 원</td>
          <td class="py-2 px-3">${{badge}}</td>
        </tr>
      `;
    }}).join('');


    // ----------------------------------------------------
    // TAB 3: RECOMMENDATION ENGINE & SIMULATOR
    // ----------------------------------------------------
    // Populate Industry Select (62 standard industries)
    const indSelect = document.getElementById('recIndustrySelect');
    recData.industries.forEach(item => {{
      const opt = document.createElement('option');
      opt.value = item.code;
      opt.textContent = item.name;
      if (item.code === 'CS100010') opt.selected = true; // Coffee default
      indSelect.appendChild(opt);
    }});

    // Populate District Select (25 Gus)
    const distSelect = document.getElementById('recDistrictSelect');
    recData.districts.forEach(gu => {{
      const opt = document.createElement('option');
      opt.value = gu;
      opt.textContent = gu;
      distSelect.appendChild(opt);
    }});

    // Initialize Recommendation Map
    const mapRec = L.map('mapRec', {{
      center: [37.564, 126.985],
      zoom: 11,
      minZoom: 10,
      maxZoom: 17,
      layers: [
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
          attribution: '&copy; Esri',
          maxZoom: 17,
          minZoom: 9
        }})
      ]
    }});
    window.mapRec = mapRec;
    mapRec.fitBounds(SEOUL_BOUNDS, {{ padding: [20, 20] }});

    // Dim mask for mapRec
    L.polygon([worldOuterRing, ...seoulCoordinatesRings], {{
      color: 'transparent',
      fillColor: '#94a3b8',
      fillOpacity: 0.35,
      interactive: false
    }}).addTo(mapRec);

    // Seoul 25 Gu Borders for mapRec
    L.geoJSON(seoulGeoData, {{
      style: function() {{
        return {{
          fillColor: '#ffffff',
          fillOpacity: 0.88,
          color: '#cbd5e1',
          weight: 1.2,
          dashArray: '2, 2'
        }};
      }}
    }}).addTo(mapRec);

    // Rec Marker Layer Group
    const recMarkerGroup = L.layerGroup().addTo(mapRec);
    let markerLookup = {{}};

    // Rec Quadrant Scatter Chart
    let quadChart = null;
    const quadCtx = document.getElementById('quadrantChart').getContext('2d');

    function getQuadColor(quad) {{
      if (quad.includes('블루오션')) return '#2563eb';
      if (quad.includes('격전지')) return '#7c3aed';
      if (quad.includes('틈새시장')) return '#059669';
      return '#e11d48';
    }}

    function getQuadBadgeClass(quad) {{
      if (quad.includes('블루오션')) return 'badge-blue';
      if (quad.includes('격전지')) return 'badge-purple';
      if (quad.includes('틈새시장')) return 'badge-green';
      return 'badge-red';
    }}

    function runRecommendationFilter() {{
      const selInd = document.getElementById('recIndustrySelect').value;
      const selGu = document.getElementById('recDistrictSelect').value;
      const selQuad = document.getElementById('recQuadrantSelect').value;

      // Filter records
      let filtered = recData.records.filter(r => r.ind_id === selInd);
      if (selGu !== 'ALL') {{
        filtered = filtered.filter(r => r.gu === selGu);
      }}
      if (selQuad !== 'ALL') {{
        filtered = filtered.filter(r => r.quad === selQuad);
      }}

      // Update KPIs
      const recCount = filtered.length;
      document.getElementById('kpiRecCount').innerHTML = `${{recCount.toLocaleString()}}<span class="text-sm font-normal text-slate-500 ml-1">개 상권</span>`;
      
      if (recCount > 0) {{
        const maxScore = Math.max(...filtered.map(r => r.score));
        const avgRev = Math.round(filtered.reduce((acc, r) => acc + r.rev_store, 0) / recCount);
        const blueCount = filtered.filter(r => r.quad.includes('블루오션')).length;
        const blueShare = Math.round((blueCount / recCount) * 100);

        document.getElementById('kpiMaxScore').innerHTML = `${{maxScore.toFixed(1)}}<span class="text-sm font-normal text-slate-500 ml-1">점</span>`;
        document.getElementById('kpiAvgRev').innerHTML = `${{avgRev.toLocaleString()}}<span class="text-sm font-normal text-slate-500 ml-1">만 원</span>`;
        document.getElementById('kpiBlueShare').innerHTML = `${{blueShare}}<span class="text-sm font-normal text-slate-500 ml-1">%</span>`;
      }} else {{
        document.getElementById('kpiMaxScore').innerHTML = `-<span class="text-sm font-normal text-slate-500 ml-1">점</span>`;
        document.getElementById('kpiAvgRev').innerHTML = `-<span class="text-sm font-normal text-slate-500 ml-1">만 원</span>`;
        document.getElementById('kpiBlueShare').innerHTML = `-<span class="text-sm font-normal text-slate-500 ml-1">%</span>`;
      }}

      // Update Map Markers
      recMarkerGroup.clearLayers();
      markerLookup = {{}};

      filtered.forEach(r => {{
        if (!r.lat || !r.lng) return;
        const color = getQuadColor(r.quad);
        const badgeClass = getQuadBadgeClass(r.quad);

        const marker = L.circleMarker([r.lat, r.lng], {{
          radius: 7,
          fillColor: color,
          color: '#ffffff',
          weight: 1.5,
          opacity: 1,
          fillOpacity: 0.9
        }});

        marker.bindTooltip(`
          <div style="font-family: Pretendard, sans-serif; padding: 2px;">
            <strong style="font-size: 13px; color: #0f172a;">${{r.name}}</strong><br/>
            <span style="font-size: 11px; color: #475569;">${{r.gu}} ${{r.dong}} | <b style="color: ${{color}};">${{r.score}}점</b></span>
          </div>
        `, {{ sticky: true, opacity: 0.95 }});

        marker.bindPopup(`
          <div style="font-family: Pretendard, sans-serif; font-size: 12px; line-height: 1.5; padding: 4px; min-width: 200px;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 6px;">
              <strong style="font-size: 13px; color: #0f172a;">${{r.name}}</strong>
              <span class="${{badgeClass}}" style="font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: bold;">${{r.quad}}</span>
            </div>
            <div style="color: #475569; space-y: 2px;">
              <div>📍 위치: <b>${{r.gu}} ${{r.dong}}</b> (${{r.type}})</div>
              <div>⭐ SpotFit 점수: <b style="color: #2563eb; font-size: 13px;">${{r.score}}점</b> (기회갭: ${{r.gap > 0 ? '+' : ''}}${{r.gap}})</div>
              <div>💰 점포당 월매출: <b>${{r.rev_store.toLocaleString()}}만 원</b></div>
              <div>🏪 점포 수: <b>${{r.stores}}개</b> (폐업률: ${{r.closure}}%)</div>
              <div>👥 주 고객: <b>${{r.age}}</b> (2030비중 ${{r.r2030}}%)</div>
              <div>⏰ 피크시간: <b>${{r.peak}}</b></div>
            </div>
          </div>
        `);

        recMarkerGroup.addLayer(marker);
        markerLookup[r.id] = marker;
      }});

      // Update Ranking Table
      const tableBody = document.getElementById('recTableBody');
      document.getElementById('tableRecordCount').textContent = `검색 결과: ${{filtered.length}}건`;

      if (filtered.length === 0) {{
        tableBody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-400">조건에 부합하는 상권이 없습니다. 다른 자치구나 사분면을 선택해 보세요.</td></tr>`;
      }} else {{
        tableBody.innerHTML = filtered.slice(0, 30).map((r, idx) => {{
          const badgeClass = getQuadBadgeClass(r.quad);
          const scorePercent = Math.min(100, Math.max(0, r.score));
          return `
            <tr onclick="focusRecMarker('${{r.id}}', ${{r.lat}}, ${{r.lng}})" class="hover:bg-blue-50/70 cursor-pointer transition">
              <td class="py-2 px-2.5 font-bold text-slate-400">${{idx + 1}}</td>
              <td class="py-2 px-2.5">
                <div class="font-bold text-slate-900">${{r.name}}</div>
                <div class="text-[10px] text-slate-400">${{r.gu}} ${{r.dong}}</div>
              </td>
              <td class="py-2 px-2">
                <span class="text-[10px] px-1.5 py-0.5 rounded font-bold ${{badgeClass}}">${{r.quad.split('(')[0]}}</span>
              </td>
              <td class="py-2 px-2 font-bold text-blue-600">
                ${{r.score}}
              </td>
              <td class="py-2 px-2.5 text-right font-semibold text-slate-800">
                ${{r.rev_store.toLocaleString()}}만
              </td>
            </tr>
          `;
        }}).join('');
      }}

      // Update Quadrant Chart
      const quadPoints = filtered.map(r => ({{
        x: r.p_dem,
        y: r.p_cmp,
        name: r.name,
        score: r.score,
        rev: r.rev_store,
        quad: r.quad
      }}));

      if (quadChart) {{
        quadChart.destroy();
      }}

      quadChart = new Chart(quadCtx, {{
        type: 'scatter',
        data: {{
          datasets: [{{
            label: '상권 포지션',
            data: quadPoints,
            backgroundColor: function(context) {{
              const item = context.raw;
              if (!item) return '#2563eb';
              return getQuadColor(item.quad);
            }},
            pointRadius: 5,
            pointHoverRadius: 8
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            x: {{
              min: 0,
              max: 100,
              title: {{ display: true, text: '수요 백분위 (%)', font: {{ size: 10 }} }},
              grid: {{ color: '#f1f5f9' }}
            }},
            y: {{
              min: 0,
              max: 100,
              title: {{ display: true, text: '경쟁 백분위 (%)', font: {{ size: 10 }} }},
              grid: {{ color: '#f1f5f9' }}
            }}
          }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                label: function(ctx) {{
                  const p = ctx.raw;
                  return `${{p.name}}: 점수 ${{p.score}}점 (월매출 ${{p.rev.toLocaleString()}}만 원)`;
                }}
              }}
            }}
          }}
        }}
      }});
    }}

    function focusRecMarker(id, lat, lng) {{
      if (lat && lng) {{
        mapRec.setView([lat, lng], 15, {{ animate: true }});
        if (markerLookup[id]) {{
          markerLookup[id].openPopup();
        }}
      }}
    }}

    function resetRecommendationFilters() {{
      document.getElementById('recIndustrySelect').value = 'CS100010';
      document.getElementById('recDistrictSelect').value = 'ALL';
      document.getElementById('recQuadrantSelect').value = 'ALL';
      runRecommendationFilter();
      mapRec.fitBounds(SEOUL_BOUNDS, {{ padding: [20, 20] }});
    }}

    // Initial Trigger for Tab 3
    runRecommendationFilter();
  </script>
</body>
</html>
"""

print("[4/5] 생성된 통합 대시보드 파일 배포 중...")
# Save to report_latest and 이승희
for target_dir in [REPORT_DIR, LEE_DIR]:
    idx_path = target_dir / "index.html"
    dash_path = target_dir / "semas_eda_dashboard.html"
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(dash_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  -> 저장 완료: {idx_path}")

print("=" * 70)
print("🎉 [3개 탭 대시보드 빌드 성공!]")
print("=" * 70)
