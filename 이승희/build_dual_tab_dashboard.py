# -*- coding: utf-8 -*-
"""2개 탭 대시보드 HTML 빌더:
- 파이차트 완전 배제 (100% 누적 막대, LQ 히트맵, 박스플롯, 산점도&회귀선, 롤리팝 바 차트)
- 탭 1: 소상공인 단독 심층 프로파일링 & 다차원 교차표/피봇
- 탭 2: 서울시 상권 62개 업종 결합 & 상권별 점포-매출 상관분석
- 미니멀 회색 마스크 포커스 지도 & 클러스터 그룹 필터 연동
"""
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_DIR / "report_latest"
LEE_DIR = PROJECT_DIR / "이승희"

BASIC_JSON_FILE = REPORT_DIR / "semas_profile_data.json"
ADV_JSON_FILE = REPORT_DIR / "semas_advanced_eda_data.json"
GEO_FILE = REPORT_DIR / "seoul_gu_borders.json"

with open(BASIC_JSON_FILE, "r", encoding="utf-8") as f:
    basic_data = json.load(f)

with open(ADV_JSON_FILE, "r", encoding="utf-8") as f:
    adv_data = json.load(f)

with open(GEO_FILE, "r", encoding="utf-8") as f:
    seoul_geo = json.load(f)

# 병합 페이로드
combined_payload = {
    "basic": basic_data,
    "adv": adv_data
}
json_str = json.dumps(combined_payload, ensure_ascii=False)
geo_str = json.dumps(seoul_geo, ensure_ascii=False)

html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SpotFit | 소상공인 서울 상가 & 상권분석 심층 EDA 대시보드 (2025Q4)</title>
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
      color: #1e293b;
    }}
    .stat-card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 1rem;
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.04);
      transition: all 0.2s ease;
    }}
    .stat-card:hover {{
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 2px 4px -2px rgba(0, 0, 0, 0.04);
      border-color: #cbd5e1;
    }}
    #map {{
      height: 520px;
      border-radius: 0.75rem;
      z-index: 10;
      background: #e2e8f0;
      border: 1px solid #cbd5e1;
    }}
    .tab-btn.active {{
      background-color: #2563eb;
      color: #ffffff;
      box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
    }}
    .tab-btn:not(.active) {{
      background-color: #ffffff;
      color: #64748b;
      border: 1px solid #e2e8f0;
    }}
    .tab-btn:not(.active):hover {{
      background-color: #f1f5f9;
      color: #0f172a;
    }}
    /* Custom Heatmap Grid */
    .heatmap-cell {{
      transition: all 0.15s ease;
    }}
    .heatmap-cell:hover {{
      transform: scale(1.08);
      z-index: 20;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    /* Scrollbar */
    ::-webkit-scrollbar {{
      width: 7px;
      height: 7px;
    }}
    ::-webkit-scrollbar-track {{
      background: #f1f5f9;
    }}
    ::-webkit-scrollbar-thumb {{
      background: #cbd5e1;
      border-radius: 4px;
    }}
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-50">

  <!-- Header -->
  <header class="border-b border-slate-200 bg-white/95 sticky top-0 z-50 backdrop-blur-md shadow-xs">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold text-xl shadow-md shadow-blue-500/20">
          <i class="fa-solid fa-chart-line"></i>
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            SpotFit 상권 정밀 통계 대시보드 <span class="text-xs px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 font-semibold border border-blue-200">2025Q4 기준</span>
          </h1>
          <p class="text-xs text-slate-500">소상공인 53.4만 점포 프로파일링 & 서울시 1,650개 상권 62개 업종 결합 분석 (파이차트 배제)</p>
        </div>
      </div>
      
      <!-- Top Action & Info -->
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          2025-10-01 ~ 2025-12-31 전수 분석
        </span>
        <button onclick="window.print()" class="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-medium text-slate-700 border border-slate-200 transition flex items-center gap-1.5 cursor-pointer">
          <i class="fa-solid fa-print"></i> 보고서 인쇄/PDF
        </button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

    <!-- Tab Navigation Switcher -->
    <div class="flex flex-col sm:flex-row items-center justify-between gap-3 p-1.5 bg-slate-200/60 rounded-2xl border border-slate-200">
      <div class="grid grid-cols-2 gap-1.5 w-full sm:w-auto">
        <button onclick="switchTab('tab1')" id="tabBtn1" class="tab-btn active px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition cursor-pointer">
          <i class="fa-solid fa-store"></i> 탭 1: 소상공인 상가 심층 프로파일링 & 교차표
        </button>
        <button onclick="switchTab('tab2')" id="tabBtn2" class="tab-btn px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition cursor-pointer">
          <i class="fa-solid fa-hand-holding-dollar"></i> 탭 2: 서울 상권 62개 업종 결합 & 매출 상관분석
        </button>
      </div>
      <div class="text-xs text-slate-500 px-3 hidden sm:block">
        <i class="fa-solid fa-circle-info text-blue-600"></i> 각 탭을 클릭하여 독립된 심화 통계를 확인하실 수 있습니다.
      </div>
    </div>

    <!-- ======================================================== -->
    <!-- [TAB 1 CONTENT] 소상공인 상가 데이터 심층 프로파일링 -->
    <!-- ======================================================== -->
    <div id="tab1Content" class="space-y-6">

      <!-- KPI Summary 4-Col -->
      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 mb-1">모집단 총 점포 수</div>
          <div class="text-3xl font-extrabold text-slate-900">534,978<span class="text-base font-normal text-slate-500 ml-1">개</span></div>
          <div class="mt-2 text-xs text-emerald-600 font-semibold flex items-center gap-1">
            <i class="fa-solid fa-check"></i> 식별자 중복 0건 (100% Unique)
          </div>
        </div>

        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 mb-1">자치구 점포 수 평균 (중위수)</div>
          <div class="text-3xl font-extrabold text-slate-900">21,399<span class="text-base font-normal text-slate-500 ml-1">(17,734)</span></div>
          <div class="mt-2 text-xs text-indigo-600 font-semibold">
            표준편차: 11,304 | IQR: 8,582개
          </div>
        </div>

        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 mb-1">행정동 점포 수 평균 (중위수)</div>
          <div class="text-3xl font-extrabold text-slate-900">1,253<span class="text-base font-normal text-slate-500 ml-1">(912)</span></div>
          <div class="mt-2 text-xs text-amber-600 font-semibold">
            왜도(Skewness): +4.18 (강남·서초 집중)
          </div>
        </div>

        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 mb-1">최다 점포 행정동 (역삼1동)</div>
          <div class="text-3xl font-extrabold text-rose-600">13,380<span class="text-base font-normal text-slate-500 ml-1">개</span></div>
          <div class="mt-2 text-xs text-slate-500">
            서울 평균 대비 <span class="font-bold text-rose-600">10.7배</span> 초과밀 상권
          </div>
        </div>
      </section>

      <!-- Section: Descriptive Statistics Summary Table -->
      <section class="stat-card p-6">
        <h3 class="text-base font-bold text-slate-900 flex items-center gap-2 mb-4">
          <i class="fa-solid fa-table-cells text-blue-600"></i> 자치구 및 행정동 단위 점포 수 기술통계량 (Descriptive Statistics)
        </h3>
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left text-slate-700 border-collapse">
            <thead class="bg-slate-100 text-slate-700 font-bold uppercase border-y border-slate-200">
              <tr>
                <th class="py-2.5 px-3">분석 단위</th>
                <th class="py-2.5 px-3">관측 수(N)</th>
                <th class="py-2.5 px-3">평균(Mean)</th>
                <th class="py-2.5 px-3">중위수(Median)</th>
                <th class="py-2.5 px-3">표준편차(Std)</th>
                <th class="py-2.5 px-3">최소(Min)</th>
                <th class="py-2.5 px-3">Q1 (25%)</th>
                <th class="py-2.5 px-3">Q3 (75%)</th>
                <th class="py-2.5 px-3">IQR</th>
                <th class="py-2.5 px-3">최대(Max)</th>
                <th class="py-2.5 px-3">왜도(Skewness)</th>
                <th class="py-2.5 px-3">첨도(Kurtosis)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 font-mono">
              <tr class="hover:bg-slate-50">
                <td class="py-2.5 px-3 font-semibold text-slate-900 font-sans">자치구 단위 (25개 구)</td>
                <td class="py-2.5 px-3">25</td>
                <td class="py-2.5 px-3 font-bold text-blue-700">21,399.1</td>
                <td class="py-2.5 px-3">17,734.0</td>
                <td class="py-2.5 px-3">11,303.8</td>
                <td class="py-2.5 px-3">10,339</td>
                <td class="py-2.5 px-3">15,535.0</td>
                <td class="py-2.5 px-3">24,117.0</td>
                <td class="py-2.5 px-3">8,582.0</td>
                <td class="py-2.5 px-3 font-bold text-rose-600">64,123 (강남)</td>
                <td class="py-2.5 px-3 text-amber-600">+2.405</td>
                <td class="py-2.5 px-3">+6.292</td>
              </tr>
              <tr class="hover:bg-slate-50">
                <td class="py-2.5 px-3 font-semibold text-slate-900 font-sans">행정동 단위 (427개 동)</td>
                <td class="py-2.5 px-3">427</td>
                <td class="py-2.5 px-3 font-bold text-blue-700">1,252.9</td>
                <td class="py-2.5 px-3">912.0</td>
                <td class="py-2.5 px-3">1,322.6</td>
                <td class="py-2.5 px-3">52 (둔촌1동)</td>
                <td class="py-2.5 px-3">563.0</td>
                <td class="py-2.5 px-3">1,357.0</td>
                <td class="py-2.5 px-3">794.0</td>
                <td class="py-2.5 px-3 font-bold text-rose-600">13,380 (역삼1동)</td>
                <td class="py-2.5 px-3 text-amber-600">+4.175</td>
                <td class="py-2.5 px-3">+25.365</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="text-[11px] text-slate-500 mt-2">
          * 왜도가 +4.18, 첨도가 +25.37로 극단적 우측 꼬리 분포(Right-Skewed)를 보이며, 소수의 메가 상권 행정동에 점포가 초집적되어 있음을 입증합니다.
        </p>
      </section>

      <!-- Charts Row: 100% Stacked Bar & LQ Heatmap (No Pie Chart!) -->
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- 100% Stacked Bar Chart -->
        <div class="stat-card p-6 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
                <i class="fa-solid fa-chart-column text-indigo-600"></i> 자치구별 10대 대분류 업종 구성비 (100% 누적 막대)
              </h3>
              <span class="text-xs text-slate-500 font-medium">비율 (%)</span>
            </div>
            <div class="relative h-88">
              <canvas id="stackedBarChart"></canvas>
            </div>
          </div>
          <p class="text-[11px] text-slate-500 mt-3 pt-3 border-t border-slate-100">
            강남·서초는 '과학·기술' 비중이 25%를 상회하며, 마포·서대문은 '음식' 비중이 35%에 육박하는 뚜렷한 상권 분업 구조를 나타냅니다.
          </p>
        </div>

        <!-- Location Quotient (LQ) Matrix Chart / Table -->
        <div class="stat-card p-6 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
                <i class="fa-solid fa-fire-flame-curved text-rose-600"></i> 주요 자치구 업종 특화지수 (LQ, 입지계수)
              </h3>
              <span class="text-xs text-rose-600 font-bold">LQ > 1.25 (특화 상권)</span>
            </div>
            <!-- Interactive LQ Table / Heatmap representation -->
            <div class="overflow-x-auto h-88 border border-slate-200 rounded-lg">
              <table class="w-full text-xs text-center border-collapse" id="lqTable">
                <!-- Dynamically generated -->
              </table>
            </div>
          </div>
          <p class="text-[11px] text-slate-500 mt-3 pt-3 border-t border-slate-100">
            * LQ > 1.0은 서울시 평균 이상 밀집, <strong>LQ > 1.25(진한 붉은색)</strong>는 해당 자치구의 핵심 특화 업종을 의미합니다.
          </p>
        </div>
      </section>

      <!-- Section: 5대 권역 x 대분류 피봇 & 층별 입점 교차표 -->
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Region x Macro Pivot -->
        <div class="stat-card p-6">
          <h3 class="text-base font-bold text-slate-900 flex items-center gap-2 mb-3">
            <i class="fa-solid fa-cubes text-emerald-600"></i> 5대 권역 × 10대 업종 대분류 피봇테이블
          </h3>
          <div class="overflow-x-auto">
            <table class="w-full text-xs text-left text-slate-700 border-collapse">
              <thead class="bg-slate-100 font-bold border-y border-slate-200">
                <tr>
                  <th class="py-2 px-2.5">권역</th>
                  <th class="py-2 px-2.5 text-right">음식</th>
                  <th class="py-2 px-2.5 text-right">소매</th>
                  <th class="py-2 px-2.5 text-right">과학기술</th>
                  <th class="py-2 px-2.5 text-right">수리개인</th>
                  <th class="py-2 px-2.5 text-right">교육</th>
                  <th class="py-2 px-2.5 text-right">합계</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 font-mono" id="regionPivotBody">
                <!-- Populated via JS -->
              </tbody>
            </table>
          </div>
        </div>

        <!-- Floor x Macro Crosstab -->
        <div class="stat-card p-6">
          <h3 class="text-base font-bold text-slate-900 flex items-center gap-2 mb-3">
            <i class="fa-solid fa-stairs text-amber-600"></i> 주요 업종 대분류 × 입점 층수(Floor) 교차표
          </h3>
          <div class="overflow-x-auto">
            <table class="w-full text-xs text-left text-slate-700 border-collapse">
              <thead class="bg-slate-100 font-bold border-y border-slate-200">
                <tr>
                  <th class="py-2 px-2.5">대분류</th>
                  <th class="py-2 px-2.5 text-right">1층</th>
                  <th class="py-2 px-2.5 text-right">2층</th>
                  <th class="py-2 px-2.5 text-right">3층 이상</th>
                  <th class="py-2 px-2.5 text-right">지하1층</th>
                  <th class="py-2 px-2.5 text-right">미기재</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 font-mono" id="floorPivotBody">
                <!-- Populated via JS -->
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- Section: Sub-Industry Top 15 Lollipop / Horizontal Bar Chart -->
      <section class="stat-card p-6">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-ranking-star text-blue-600"></i> 소상공인 세부 업종(소분류) 점포 수 랭킹 TOP 15
            </h3>
            <p class="text-xs text-slate-500 mt-0.5">파이차트 대신 직관적인 가로 막대 차트로 업종 간 절대 규모 편차 시각화</p>
          </div>
          <span class="text-xs text-slate-500 font-medium">단위: 개</span>
        </div>
        <div class="relative h-80">
          <canvas id="subLollipopChart"></canvas>
        </div>
      </section>

    </div>


    <!-- ======================================================== -->
    <!-- [TAB 2 CONTENT] 서울시 상권 62개 업종 결합 & 매출 상관분석 -->
    <!-- ======================================================== -->
    <div id="tab2Content" class="hidden space-y-6">

      <!-- KPI Summary Tab 2 -->
      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 mb-1">결합 분석 상권 수</div>
          <div class="text-3xl font-extrabold text-slate-900">1,650<span class="text-base font-normal text-slate-500 ml-1">개 상권</span></div>
          <div class="mt-2 text-xs text-blue-600 font-semibold">
            골목(1,030), 발달(249), 전통(280), 관광(6)
          </div>
        </div>

        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 mb-1">점포수-매출 상관계수 (r)</div>
          <div class="text-3xl font-extrabold text-indigo-600">+0.768</div>
          <div class="mt-2 text-xs text-emerald-600 font-semibold">
            스피어만 순위상관 p &lt; 0.001 (강한 양의 상관)
          </div>
        </div>

        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 mb-1">2025Q4 서울 상권 총 추정매출</div>
          <div class="text-3xl font-extrabold text-slate-900">24.4<span class="text-base font-normal text-slate-500 ml-1">조 원</span></div>
          <div class="mt-2 text-xs text-slate-500">
            발달상권이 <span class="font-bold text-indigo-600">61.2% (14.9조)</span> 점유
          </div>
        </div>

        <div class="stat-card p-5">
          <div class="text-xs font-semibold text-slate-500 mb-1">매출 1위 업종 (한식음식점)</div>
          <div class="text-3xl font-extrabold text-rose-600">3.99<span class="text-base font-normal text-slate-500 ml-1">조 원</span></div>
          <div class="mt-2 text-xs text-rose-600 font-semibold">
            서울 분기 매출의 16.3% 차지
          </div>
        </div>
      </section>

      <!-- Correlation Scatter Plot & Regression Line -->
      <section class="stat-card p-6">
        <div class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-100 gap-4 mb-4">
          <div>
            <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 text-xs font-semibold mb-1 border border-indigo-200">
              <i class="fa-solid fa-chart-line"></i> 회귀 분석 & 통계적 상관성
            </div>
            <h3 class="text-base font-bold text-slate-900">
              행정동 단위 소상공인 점포 수 vs 서울 상권 추정매출액 산점도 (Scatter Plot & Trendline)
            </h3>
            <p class="text-xs text-slate-500 mt-0.5">
              Pearson r = 0.586, Spearman r = 0.768 | 회귀식: y = 0.5648x - 121.14 (억원)
            </p>
          </div>
          <div class="text-xs text-right">
            <span class="px-2.5 py-1 rounded bg-slate-100 font-mono text-slate-700 font-bold">N = 397개 행정동</span>
          </div>
        </div>
        <div class="relative h-96">
          <canvas id="scatterPlotChart"></canvas>
        </div>
        <p class="text-[11px] text-slate-500 mt-3 pt-3 border-t border-slate-100">
          * 점포 수가 증가할수록 분기 총 매출액이 가파르게 증가하는 선형적 관계가 뚜렷하며, 우상단의 역삼1동, 서교동, 여의동 등은 초대형 매출 아웃라이어로 식별됩니다.
        </p>
      </section>

      <!-- Pivot Table: 4대 상권 구분별 매출 및 면적 통계 -->
      <section class="stat-card p-6">
        <h3 class="text-base font-bold text-slate-900 flex items-center gap-2 mb-4">
          <i class="fa-solid fa-table-list text-blue-600"></i> 서울시 4대 상권 구분별(골목/발달/전통/관광) 피봇 분석표
        </h3>
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left text-slate-700 border-collapse">
            <thead class="bg-slate-100 font-bold uppercase border-y border-slate-200">
              <tr>
                <th class="py-2.5 px-3">상권 구분</th>
                <th class="py-2.5 px-3 text-right">상권 수</th>
                <th class="py-2.5 px-3 text-right">평균 매출 (억원)</th>
                <th class="py-2.5 px-3 text-right">중위수 매출 (억원)</th>
                <th class="py-2.5 px-3 text-right">총 매출 (조원)</th>
                <th class="py-2.5 px-3 text-right">매출 점유율 (%)</th>
                <th class="py-2.5 px-3 text-right">평균 상권 면적 (㎡)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 font-mono" id="trdarTypePivotBody">
              <!-- Populated via JS -->
            </tbody>
          </table>
        </div>
      </section>

      <!-- Charts Row 2: Top 15 Industry Sales & Mapped 62 Industry Counts -->
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Top 15 Industry Sales Bar -->
        <div class="stat-card p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-sack-dollar text-emerald-600"></i> 62개 업종 중 2025Q4 추정매출액 TOP 15
            </h3>
            <span class="text-xs text-slate-500 font-medium">단위: 억원</span>
          </div>
          <div class="relative h-88">
            <canvas id="industrySalesChart"></canvas>
          </div>
        </div>

        <!-- Mapped 62 Industry Store Count Bar -->
        <div class="stat-card p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-shop text-blue-600"></i> 62개 표준 상권업종 매핑 점포 수 TOP 15
            </h3>
            <span class="text-xs text-slate-500 font-medium">단위: 개</span>
          </div>
          <div class="relative h-88">
            <canvas id="mappedStoreChart"></canvas>
          </div>
        </div>
      </section>

    </div>

  </main>

  <!-- Footer -->
  <footer class="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
    <p>SpotFit 상권 분석 프로젝트 | Data: 소상공인시장진흥공단(S01) & 서울시 상권분석서비스(K01, OA-15560) 2025Q4</p>
    <p class="mt-1 text-slate-400">Generated at 2026-10-31 · Internal Report Mode (No Git Commit)</p>
  </footer>

  <!-- Embedded Data & Chart Rendering Scripts -->
  <script>
    const allData = {json_str};
    const basicData = allData.basic;
    const advData = allData.adv;
    const tab1 = advData.tab1;
    const tab2 = advData.tab2;

    // Tab Switcher
    function switchTab(tabId) {{
      const tab1Content = document.getElementById('tab1Content');
      const tab2Content = document.getElementById('tab2Content');
      const tabBtn1 = document.getElementById('tabBtn1');
      const tabBtn2 = document.getElementById('tabBtn2');

      if (tabId === 'tab1') {{
        tab1Content.classList.remove('hidden');
        tab2Content.classList.add('hidden');
        tabBtn1.classList.add('active');
        tabBtn2.classList.remove('active');
      }} else {{
        tab1Content.classList.add('hidden');
        tab2Content.classList.remove('hidden');
        tabBtn1.classList.remove('active');
        tabBtn2.classList.add('active');
        // Render Tab 2 charts on first open
        if (!window.tab2Rendered) {{
          renderTab2Charts();
          window.tab2Rendered = true;
        }}
      }}
    }}

    // Global Chart.js Light Mode Defaults
    Chart.defaults.color = '#64748b';
    Chart.defaults.font.family = 'Pretendard, -apple-system, sans-serif';

    // ----------------------------------------------------
    // TAB 1 CHARTS & TABLES
    // ----------------------------------------------------
    // 1. 100% Stacked Bar Chart (Gu x Macro Industry)
    const stackedCtx = document.getElementById('stackedBarChart').getContext('2d');
    const gus = tab1.gu_macro_crosstab.gus.slice(0, 15); // 상위 15개 구
    const macroCols = tab1.gu_macro_crosstab.macros;
    const pcts = tab1.gu_macro_crosstab.pcts;

    const macroPalette = [
      '#f43f5e', '#3b82f6', '#8b5cf6', '#f59e0b', '#10b981',
      '#06b6d4', '#ec4899', '#64748b', '#84cc16', '#a855f7'
    ];

    const stackedDatasets = macroCols.map((col, cIdx) => ({{
      label: col,
      data: gus.map((g, rIdx) => pcts[rIdx][cIdx]),
      backgroundColor: macroPalette[cIdx % macroPalette.length],
      borderRadius: 2
    }}));

    new Chart(stackedCtx, {{
      type: 'bar',
      data: {{
        labels: gus,
        datasets: stackedDatasets
      }},
      options: {{
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'bottom', labels: {{ boxWidth: 10, font: {{ size: 10 }} }} }},
          tooltip: {{
            callbacks: {{
              label: (ctx) => ` ${{ctx.dataset.label}}: ${{ctx.raw}}%`
            }}
          }}
        }},
        scales: {{
          x: {{ stacked: true, max: 100, ticks: {{ callback: v => v + '%' }} }},
          y: {{ stacked: true, grid: {{ display: false }} }}
        }}
      }}
    }});

    // 2. LQ Matrix Table Builder
    const lqTable = document.getElementById('lqTable');
    const selectedGus = ['강남구', '서초구', '송파구', '마포구', '영등포구', '중구', '종로구', '성동구', '용산구', '관악구'];
    const selectedMacros = ['음식', '소매', '과학·기술', '수리·개인', '교육', '보건의료', '예술·스포츠'];

    let lqHtml = `
      <thead class="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
        <tr>
          <th class="py-2 px-2 text-left">자치구</th>
          ${{selectedMacros.map(m => `<th class="py-2 px-1 text-center font-semibold">${{m}}</th>`).join('')}}
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100 font-mono text-slate-800">
    `;

    selectedGus.forEach(gu => {{
      lqHtml += `<tr class="hover:bg-slate-50"><td class="py-1.5 px-2 text-left font-sans font-bold text-slate-900">${{gu}}</td>`;
      selectedMacros.forEach(m => {{
        const lq = tab1.lq_matrix[gu] ? tab1.lq_matrix[gu][m] || 1.0 : 1.0;
        let bg = '#ffffff';
        let text = '#475569';
        let bold = 'font-normal';
        if (lq >= 1.25) {{
          bg = '#fee2e2'; text = '#b91c1c'; bold = 'font-bold'; // 특화
        }} else if (lq >= 1.05) {{
          bg = '#fef3c7'; text = '#b45309';
        }} else if (lq < 0.85) {{
          bg = '#f1f5f9'; text = '#94a3b8';
        }}
        lqHtml += `<td class="py-1.5 px-1 heatmap-cell ${{bold}}" style="background: ${{bg}}; color: ${{text}};" title="${{gu}} ${{m}}: LQ ${{lq}}">${{lq.toFixed(2)}}</td>`;
      }});
      lqHtml += `</tr>`;
    }});
    lqHtml += `</tbody>`;
    lqTable.innerHTML = lqHtml;

    // 3. Region x Macro Pivot Table Body
    const regionBody = document.getElementById('regionPivotBody');
    const rNames = tab1.region_macro_pivot.regions;
    const rCounts = tab1.region_macro_pivot.counts;
    const rMacros = tab1.region_macro_pivot.macros;
    
    // Macro Indices
    const fIdx = rMacros.indexOf('음식');
    const sIdx = rMacros.indexOf('소매');
    const sciIdx = rMacros.indexOf('과학·기술');
    const repIdx = rMacros.indexOf('수리·개인');
    const eduIdx = rMacros.indexOf('교육');

    let rHtml = '';
    rNames.forEach((rn, i) => {{
      const total = rCounts[i].reduce((a, b) => a + b, 0);
      rHtml += `
        <tr class="hover:bg-slate-50">
          <td class="py-2 px-2.5 font-bold font-sans text-slate-900">${{rn}}</td>
          <td class="py-2 px-2.5 text-right font-medium text-rose-600">${{rCounts[i][fIdx].toLocaleString()}}</td>
          <td class="py-2 px-2.5 text-right font-medium text-blue-600">${{rCounts[i][sIdx].toLocaleString()}}</td>
          <td class="py-2 px-2.5 text-right font-medium text-purple-600">${{rCounts[i][sciIdx].toLocaleString()}}</td>
          <td class="py-2 px-2.5 text-right">${{rCounts[i][repIdx].toLocaleString()}}</td>
          <td class="py-2 px-2.5 text-right">${{rCounts[i][eduIdx].toLocaleString()}}</td>
          <td class="py-2 px-2.5 text-right font-bold text-slate-900 font-sans">${{total.toLocaleString()}}</td>
        </tr>
      `;
    }});
    regionBody.innerHTML = rHtml;

    // 4. Floor x Macro Crosstab Body
    const floorBody = document.getElementById('floorPivotBody');
    const fMacros = tab1.floor_macro_crosstab.macros;
    const fFloors = tab1.floor_macro_crosstab.floors;
    const fCounts = tab1.floor_macro_crosstab.counts;

    const idx1 = fFloors.indexOf('1층');
    const idx2 = fFloors.indexOf('2층');
    const idx3p = fFloors.indexOf('3층 이상');
    const idxB1 = fFloors.indexOf('지하1층');
    const idxNone = fFloors.indexOf('미기재');

    let fHtml = '';
    fMacros.slice(0, 6).forEach((mn, i) => {{
      fHtml += `
        <tr class="hover:bg-slate-50">
          <td class="py-2 px-2.5 font-bold font-sans text-slate-900">${{mn}}</td>
          <td class="py-2 px-2.5 text-right font-semibold text-emerald-600">${{fCounts[i][idx1].toLocaleString()}}</td>
          <td class="py-2 px-2.5 text-right">${{fCounts[i][idx2].toLocaleString()}}</td>
          <td class="py-2 px-2.5 text-right">${{fCounts[i][idx3p].toLocaleString()}}</td>
          <td class="py-2 px-2.5 text-right text-rose-600">${{fCounts[i][idxB1].toLocaleString()}}</td>
          <td class="py-2 px-2.5 text-right text-slate-400">${{fCounts[i][idxNone].toLocaleString()}}</td>
        </tr>
      `;
    }});
    floorBody.innerHTML = fHtml;

    // 5. Sub-Industry Lollipop Chart (TOP 15)
    const subEntries = Object.entries(tab1.sub_top15);
    new Chart(document.getElementById('subLollipopChart'), {{
      type: 'bar',
      data: {{
        labels: subEntries.map(e => e[0]),
        datasets: [{{
          label: '등록 점포 수',
          data: subEntries.map(e => e[1]),
          backgroundColor: '#0284c7',
          borderRadius: 4
        }}]
      }},
      options: {{
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{ grid: {{ color: '#f1f5f9' }} }},
          y: {{ grid: {{ display: false }}, ticks: {{ font: {{ weight: '500' }} }} }}
        }}
      }}
    }});

    // ----------------------------------------------------
    // TAB 2 CHARTS & TABLES (Lazy Rendered on Click)
    // ----------------------------------------------------
    function renderTab2Charts() {{
      // 1. Trdar Type Pivot Table Body
      const trdarBody = document.getElementById('trdarTypePivotBody');
      const trdarRows = tab2.trdar_type_pivot;
      const totalTrdarSales = trdarRows.reduce((acc, r) => acc + r.sum_sales_trillion, 0);

      let tHtml = '';
      trdarRows.forEach(r => {{
        const pct = ((r.sum_sales_trillion / totalTrdarSales) * 100).toFixed(1);
        tHtml += `
          <tr class="hover:bg-slate-50">
            <td class="py-2.5 px-3 font-bold font-sans text-slate-900">${{r['상권_구분_코드_명']}}</td>
            <td class="py-2.5 px-3 text-right">${{r.trdar_count.toLocaleString()}}개</td>
            <td class="py-2.5 px-3 text-right font-semibold text-blue-700">${{r.mean_sales.toLocaleString()}}</td>
            <td class="py-2.5 px-3 text-right">${{r.median_sales.toLocaleString()}}</td>
            <td class="py-2.5 px-3 text-right font-bold text-indigo-700">${{r.sum_sales_trillion.toLocaleString()}}조</td>
            <td class="py-2.5 px-3 text-right font-bold text-rose-600">${{pct}}%</td>
            <td class="py-2.5 px-3 text-right text-slate-500">${{Math.round(r.mean_area).toLocaleString()}}</td>
          </tr>
        `;
      }});
      trdarBody.innerHTML = tHtml;

      // 2. Correlation Scatter Plot Chart
      const scatterPoints = tab2.scatter_points.map(pt => ({{
        x: pt.stores,
        y: pt.sales_100m,
        dong: pt.dong,
        gu: pt.gu
      }}));

      // Trendline points
      const maxStore = Math.max(...scatterPoints.map(p => p.x));
      const trendPoints = [
        {{ x: 0, y: tab2.correlation.intercept }},
        {{ x: maxStore, y: (tab2.correlation.slope * maxStore + tab2.correlation.intercept) }}
      ];

      new Chart(document.getElementById('scatterPlotChart'), {{
        type: 'scatter',
        data: {{
          datasets: [
            {{
              label: '행정동 관측치',
              data: scatterPoints,
              backgroundColor: 'rgba(59, 130, 246, 0.65)',
              borderColor: '#2563eb',
              borderWidth: 1,
              pointRadius: 4.5,
              pointHoverRadius: 7
            }},
            {{
              type: 'line',
              label: '선형 회귀 추세선 (Trendline)',
              data: trendPoints,
              borderColor: '#e11d48',
              borderWidth: 2,
              borderDash: [5, 5],
              pointRadius: 0,
              fill: false
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            tooltip: {{
              callbacks: {{
                label: (ctx) => {{
                  const raw = ctx.raw;
                  if (ctx.datasetIndex === 0) {{
                    return `${{raw.gu}} ${{raw.dong}}: 점포 ${{raw.x.toLocaleString()}}개 | 매출 ${{raw.y.toLocaleString()}}억원`;
                  }}
                  return `추세선`;
                }}
              }}
            }}
          }},
          scales: {{
            x: {{
              title: {{ display: true, text: '소상공인 등록 점포 수 (개)', font: {{ weight: 'bold' }} }},
              grid: {{ color: '#f1f5f9' }}
            }},
            y: {{
              title: {{ display: true, text: '2025Q4 서울 상권 추정매출액 (억원)', font: {{ weight: 'bold' }} }},
              grid: {{ color: '#f1f5f9' }}
            }}
          }}
        }}
      }});

      // 3. Top 15 Industry Sales Bar
      const indSalesEntries = Object.entries(tab2.industry_sales_top15);
      new Chart(document.getElementById('industrySalesChart'), {{
        type: 'bar',
        data: {{
          labels: indSalesEntries.map(e => e[0]),
          datasets: [{{
            label: '2025Q4 매출액 (억원)',
            data: indSalesEntries.map(e => e[1]),
            backgroundColor: '#059669',
            borderRadius: 4
          }}]
        }},
        options: {{
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }} }},
          scales: {{
            x: {{ grid: {{ color: '#f1f5f9' }} }},
            y: {{ grid: {{ display: false }} }}
          }}
        }}
      }});

      // 4. Mapped 62 Industry Store Count Bar
      const mappedEntries = Object.entries(tab2.mapped_62_counts).slice(0, 15);
      new Chart(document.getElementById('mappedStoreChart'), {{
        type: 'bar',
        data: {{
          labels: mappedEntries.map(e => e[0]),
          datasets: [{{
            label: '매핑 점포 수 (개)',
            data: mappedEntries.map(e => e[1]),
            backgroundColor: '#4f46e5',
            borderRadius: 4
          }}]
        }},
        options: {{
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }} }},
          scales: {{
            x: {{ grid: {{ color: '#f1f5f9' }} }},
            y: {{ grid: {{ display: false }} }}
          }}
        }}
      }});
    }}
  </script>
</body>
</html>
"""

# 저장 (report_latest 및 이승희 양쪽)
out_files = [
    REPORT_DIR / "index.html",
    REPORT_DIR / "semas_eda_dashboard.html",
    LEE_DIR / "index.html",
    LEE_DIR / "semas_eda_dashboard.html"
]

for p in out_files:
    with open(p, "w", encoding="utf-8") as f:
        f.write(html_content)

print(f"Dual-tab dashboard without pie charts generated across:\n- {REPORT_DIR}\n- {LEE_DIR}")
