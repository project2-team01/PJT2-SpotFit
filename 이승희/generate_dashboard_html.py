# -*- coding: utf-8 -*-
"""대시보드 HTML 생성기:
- 서울 외 지역 회색 미니멀 마스크 & 서울 내부 스포트라이트
- 서울 전체 맞춤 fitBounds
- Leaflet MarkerCluster 및 다차원 클러스터링 그룹(업종별/권역별) 선택 기능
"""
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_DIR / "report_latest"

JSON_FILE = REPORT_DIR / "semas_profile_data.json"
GEO_FILE = REPORT_DIR / "seoul_gu_borders.json"

with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

with open(GEO_FILE, "r", encoding="utf-8") as f:
    seoul_geo = json.load(f)

json_str = json.dumps(data, ensure_ascii=False)
geo_str = json.dumps(seoul_geo, ensure_ascii=False)

html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SpotFit | 소상공인진흥공단 서울 상가데이터 EDA 대시보드 (2025Q4)</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Chart.js CDN -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <!-- Leaflet CSS & JS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <!-- Leaflet MarkerCluster CSS & JS -->
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
      height: 540px;
      border-radius: 0.75rem;
      z-index: 10;
      background: #e2e8f0;
      border: 1px solid #cbd5e1;
    }}
    /* Custom Cluster Badge Styles */
    .marker-cluster-small {{
      background-color: rgba(59, 130, 246, 0.25) !important;
    }}
    .marker-cluster-small div {{
      background-color: #2563eb !important;
      color: #ffffff !important;
      font-weight: 700;
    }}
    .marker-cluster-medium {{
      background-color: rgba(124, 58, 237, 0.25) !important;
    }}
    .marker-cluster-medium div {{
      background-color: #7c3aed !important;
      color: #ffffff !important;
      font-weight: 700;
    }}
    .marker-cluster-large {{
      background-color: rgba(225, 29, 72, 0.25) !important;
    }}
    .marker-cluster-large div {{
      background-color: #e11d48 !important;
      color: #ffffff !important;
      font-weight: 700;
    }}
    /* Scrollbar */
    ::-webkit-scrollbar {{
      width: 8px;
      height: 8px;
    }}
    ::-webkit-scrollbar-track {{
      background: #f1f5f9;
    }}
    ::-webkit-scrollbar-thumb {{
      background: #cbd5e1;
      border-radius: 4px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
      background: #94a3b8;
    }}
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-50">

  <!-- Header -->
  <header class="border-b border-slate-200 bg-white/95 sticky top-0 z-50 backdrop-blur-md shadow-xs">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold text-xl shadow-md shadow-blue-500/20">
          <i class="fa-solid fa-chart-pie"></i>
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            SpotFit 상권 분석 <span class="text-xs px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 font-semibold border border-blue-200">SEMAS 2025Q4</span>
          </h1>
          <p class="text-xs text-slate-500">소상공인시장진흥공단 서울시 상가(상권) 원본 데이터 정밀 프로파일링 & 공간 클러스터 EDA</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          무결성 검증 완료 (534,978건)
        </span>
        <button onclick="window.print()" class="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-medium text-slate-700 border border-slate-200 transition flex items-center gap-1.5 cursor-pointer">
          <i class="fa-solid fa-print"></i> 리포트 인쇄/PDF
        </button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

    <!-- KPI Summary Grid -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      <!-- KPI 1 -->
      <div class="stat-card p-5">
        <div class="flex items-center justify-between text-slate-500 text-sm mb-2">
          <span class="font-medium">총 점포 수 (모집단)</span>
          <div class="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
            <i class="fa-solid fa-store"></i>
          </div>
        </div>
        <div class="text-3xl font-extrabold text-slate-900 tracking-tight" id="kpi-total-stores">534,978</div>
        <div class="mt-2 text-xs text-slate-500 flex items-center gap-1.5">
          <span class="text-emerald-600 font-semibold">100% 고유</span> (식별번호 중복 0건)
        </div>
      </div>

      <!-- KPI 2 -->
      <div class="stat-card p-5">
        <div class="flex items-center justify-between text-slate-500 text-sm mb-2">
          <span class="font-medium">최다 밀집 자치구</span>
          <div class="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <i class="fa-solid fa-location-dot"></i>
          </div>
        </div>
        <div class="text-3xl font-extrabold text-slate-900 tracking-tight" id="kpi-top-gu">강남구</div>
        <div class="mt-2 text-xs text-slate-500 flex items-center gap-1.5">
          <span class="text-indigo-600 font-semibold">64,123개</span> (서울 전체의 12.0%)
        </div>
      </div>

      <!-- KPI 3 -->
      <div class="stat-card p-5">
        <div class="flex items-center justify-between text-slate-500 text-sm mb-2">
          <span class="font-medium">음식 업종 점포 수</span>
          <div class="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
            <i class="fa-solid fa-utensils"></i>
          </div>
        </div>
        <div class="text-3xl font-extrabold text-slate-900 tracking-tight" id="kpi-food-stores">135,884</div>
        <div class="mt-2 text-xs text-slate-500 flex items-center gap-1.5">
          <span class="text-amber-600 font-semibold">점유율 1위 (25.4%)</span> / 소매 20.9%
        </div>
      </div>

      <!-- KPI 4 -->
      <div class="stat-card p-5">
        <div class="flex items-center justify-between text-slate-500 text-sm mb-2">
          <span class="font-medium">커피/카페 등록 점포</span>
          <div class="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
            <i class="fa-solid fa-mug-hot"></i>
          </div>
        </div>
        <div class="text-3xl font-extrabold text-slate-900 tracking-tight" id="kpi-cafe-stores">26,274</div>
        <div class="mt-2 text-xs text-slate-500 flex items-center gap-1.5">
          <span class="text-rose-600 font-semibold">강남·마포·서초</span> 중심 초밀집
        </div>
      </div>
    </section>

    <!-- Map Section (Featured Interactive Focus) -->
    <section class="stat-card p-6 border-blue-200 shadow-md">
      <div class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-100 gap-4 mb-4">
        <div>
          <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold mb-1 border border-blue-200">
            <i class="fa-solid fa-map-location-dot"></i> 미니멀 포커스 맵 & 클러스터링
          </div>
          <h2 class="text-lg font-bold text-slate-900 flex items-center gap-2">
            서울시 상권 공간 분포 & 클러스터링 맵
          </h2>
          <p class="text-xs text-slate-500 mt-0.5">
            서울 외 지역을 심플한 회색 톤으로 최소화하여 <strong>서울시 상권에만 시각적 집중(Spotlight)</strong>을 부여했습니다.
          </p>
        </div>
        
        <!-- Controls & Reset -->
        <div class="flex items-center gap-2">
          <button onclick="resetSeoulView()" class="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 border border-slate-300 shadow-2xs flex items-center gap-1.5 transition cursor-pointer">
            <i class="fa-solid fa-arrows-rotate text-blue-600"></i> 서울 전체 뷰 복원
          </button>
        </div>
      </div>

      <!-- Cluster Group Filter Toolbar -->
      <div class="bg-slate-50 p-3.5 rounded-xl border border-slate-200 mb-4 space-y-3">
        <!-- 업종별 클러스터 그룹 선택 -->
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-xs font-bold text-slate-600 flex items-center gap-1 min-w-[90px]">
            <i class="fa-solid fa-layer-group text-blue-600"></i> 업종 그룹:
          </span>
          <div class="flex flex-wrap gap-1.5" id="industryFilterGroup">
            <button onclick="setIndustryFilter('ALL')" data-cat="ALL" class="filter-btn active px-3 py-1 rounded-full text-xs font-semibold bg-blue-600 text-white shadow-2xs transition">
              전체 업종 (1,200)
            </button>
            <button onclick="setIndustryFilter('음식')" data-cat="음식" class="filter-btn px-3 py-1 rounded-full text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-300 transition">
              <span class="inline-block w-2 h-2 rounded-full bg-rose-500 mr-1"></span> 음식
            </button>
            <button onclick="setIndustryFilter('소매')" data-cat="소매" class="filter-btn px-3 py-1 rounded-full text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 transition">
              <span class="inline-block w-2 h-2 rounded-full bg-blue-500 mr-1"></span> 소매
            </button>
            <button onclick="setIndustryFilter('과학·기술')" data-cat="과학·기술" class="filter-btn px-3 py-1 rounded-full text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:bg-purple-50 hover:text-purple-700 hover:border-purple-300 transition">
              <span class="inline-block w-2 h-2 rounded-full bg-purple-500 mr-1"></span> 과학·기술
            </button>
            <button onclick="setIndustryFilter('수리·개인')" data-cat="수리·개인" class="filter-btn px-3 py-1 rounded-full text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:bg-amber-50 hover:text-amber-700 hover:border-amber-300 transition">
              <span class="inline-block w-2 h-2 rounded-full bg-amber-500 mr-1"></span> 수리·개인
            </button>
            <button onclick="setIndustryFilter('교육')" data-cat="교육" class="filter-btn px-3 py-1 rounded-full text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-300 transition">
              <span class="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1"></span> 교육
            </button>
            <button onclick="setIndustryFilter('CAFE')" data-cat="CAFE" class="filter-btn px-3 py-1 rounded-full text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:bg-pink-50 hover:text-pink-700 hover:border-pink-300 transition">
              <span class="inline-block w-2 h-2 rounded-full bg-pink-500 mr-1"></span> 카페/커피 특화
            </button>
          </div>
        </div>

        <!-- 권역별 클러스터 그룹 선택 -->
        <div class="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200/60">
          <span class="text-xs font-bold text-slate-600 flex items-center gap-1 min-w-[90px]">
            <i class="fa-solid fa-compass text-indigo-600"></i> 서울 권역:
          </span>
          <div class="flex flex-wrap gap-1.5" id="regionFilterGroup">
            <button onclick="setRegionFilter('ALL')" data-region="ALL" class="region-btn active px-2.5 py-0.5 rounded-md text-xs font-semibold bg-slate-800 text-white shadow-2xs transition">
              서울 전역
            </button>
            <button onclick="setRegionFilter('동남권')" data-region="동남권" class="region-btn px-2.5 py-0.5 rounded-md text-xs font-medium bg-white text-slate-600 border border-slate-200 hover:bg-slate-100 transition">
              동남권 (강남/서초/송파/강동)
            </button>
            <button onclick="setRegionFilter('서북권')" data-region="서북권" class="region-btn px-2.5 py-0.5 rounded-md text-xs font-medium bg-white text-slate-600 border border-slate-200 hover:bg-slate-100 transition">
              서북권 (마포/서대문/은평)
            </button>
            <button onclick="setRegionFilter('도심권')" data-region="도심권" class="region-btn px-2.5 py-0.5 rounded-md text-xs font-medium bg-white text-slate-600 border border-slate-200 hover:bg-slate-100 transition">
              도심권 (종로/중구/용산)
            </button>
            <button onclick="setRegionFilter('서남권')" data-region="서남권" class="region-btn px-2.5 py-0.5 rounded-md text-xs font-medium bg-white text-slate-600 border border-slate-200 hover:bg-slate-100 transition">
              서남권 (영등포/구로/관악 등)
            </button>
            <button onclick="setRegionFilter('동북권')" data-region="동북권" class="region-btn px-2.5 py-0.5 rounded-md text-xs font-medium bg-white text-slate-600 border border-slate-200 hover:bg-slate-100 transition">
              동북권 (성동/동대문/노원 등)
            </button>
          </div>
        </div>
      </div>

      <!-- Leaflet Map Container -->
      <div id="map"></div>

      <!-- Map Legend & Guide -->
      <div class="flex flex-wrap items-center justify-between text-xs text-slate-500 mt-3.5 pt-3 border-t border-slate-100 gap-2">
        <div class="flex items-center gap-4">
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-rose-500 inline-block border border-white shadow-2xs"></span> 음식</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-blue-500 inline-block border border-white shadow-2xs"></span> 소매</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-purple-500 inline-block border border-white shadow-2xs"></span> 과학·기술</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-amber-500 inline-block border border-white shadow-2xs"></span> 수리·개인</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-emerald-500 inline-block border border-white shadow-2xs"></span> 교육/기타</span>
        </div>
        <div class="text-slate-400">
          💡 <span class="font-medium text-slate-600">클러스터 숫자 원형</span>을 클릭하시면 해당 지역 상권으로 즉시 확대 분해됩니다.
        </div>
      </div>
    </section>

    <!-- Charts Row 1: Gu Ranking & Macro Industry Breakdown -->
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Gu Ranking Chart -->
      <div class="stat-card p-6 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-ranking-star text-indigo-600"></i> 서울시 25개 자치구별 점포 수 분포
            </h3>
            <span class="text-xs text-slate-500 font-medium">단위: 개</span>
          </div>
          <div class="relative h-80">
            <canvas id="guRankingChart"></canvas>
          </div>
        </div>
        <p class="text-[11px] text-slate-500 mt-3 pt-3 border-t border-slate-100">
          강남 3구(강남·송파·서초)와 마포·영등포 등 상업 및 업무 밀집 지구에 전체 점포의 36.8%가 집중되어 있습니다.
        </p>
      </div>

      <!-- Macro Industry Doughnut Chart -->
      <div class="stat-card p-6 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-chart-pie text-pink-600"></i> 상권 업종 대분류(10대) 구성비
            </h3>
            <span class="text-xs text-slate-500 font-medium">비율 (%)</span>
          </div>
          <div class="relative h-80">
            <canvas id="macroIndustryChart"></canvas>
          </div>
        </div>
        <p class="text-[11px] text-slate-500 mt-3 pt-3 border-t border-slate-100">
          '음식(25.4%)'과 '소매(20.9%)'가 과반을 차지하며, '과학·기술(17.4%)' 및 '수리·개인(9.6%)'이 그 뒤를 잇습니다.
        </p>
      </div>
    </section>

    <!-- Charts Row 2: Sub-Industries & Major Franchise Brands -->
    <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Sub Industry Top 12 -->
      <div class="stat-card p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-list-check text-blue-600"></i> 세부 업종(소분류) TOP 12 등록 현황
          </h3>
          <span class="text-xs text-slate-500 font-medium">단위: 개</span>
        </div>
        <div class="relative h-80">
          <canvas id="subIndustryChart"></canvas>
        </div>
      </div>

      <!-- Brand Presence Chart -->
      <div class="stat-card p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-tags text-emerald-600"></i> 주요 프랜차이즈 브랜드 서울 등록 매장 수
          </h3>
          <span class="text-xs text-slate-500 font-medium">상호명 키워드 매칭</span>
        </div>
        <div class="relative h-80">
          <canvas id="brandChart"></canvas>
        </div>
      </div>
    </section>

    <!-- Special Focus: Coffee / Cafe Startup Hotspot -->
    <section class="stat-card p-6">
      <div class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-100 gap-4 mb-6">
        <div>
          <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-700 text-xs font-semibold mb-1 border border-rose-200">
            <i class="fa-solid fa-fire"></i> 창업 관심 1순위 집중 분석
          </div>
          <h2 class="text-lg font-bold text-slate-900">커피전문점 / 카페 상권 밀집도 & 격전지 분석</h2>
          <p class="text-xs text-slate-500">총 26,274개 카페 데이터 기반 자치구별 분포 및 과밀 상권 도출</p>
        </div>
        <div class="text-right">
          <div class="text-xs font-semibold text-slate-500">서울시 평균 카페 점유율</div>
          <div class="text-2xl font-extrabold text-rose-600">4.91%</div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2 relative h-72">
          <canvas id="cafeGuChart"></canvas>
        </div>
        <div class="overflow-hidden rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <div class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3 flex items-center justify-between">
            <span>카페 밀집 TOP 8 행정동</span>
            <span class="text-rose-600">등록 점포수</span>
          </div>
          <div class="space-y-2 text-xs" id="cafeDongList"></div>
        </div>
      </div>
    </section>

    <!-- Industry Diversity Ranking (Shannon Index) -->
    <section class="stat-card p-6">
      <div class="mb-4">
        <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-shapes text-violet-600"></i> 자치구별 업종 다양성 지수 (Shannon Diversity Index)
        </h3>
        <p class="text-xs text-slate-500 mt-1">지수가 높을수록 특정 업종 쏠림 없이 다양한 생활밀착형 서비스가 균형 있게 입점해 있음을 의미합니다.</p>
      </div>
      <div class="relative h-64">
        <canvas id="diversityChart"></canvas>
      </div>
    </section>

  </main>

  <!-- Footer -->
  <footer class="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
    <p>SpotFit 상권 분석 프로젝트 | Data: 소상공인시장진흥공단 서울시 상가(상권)정보 2025Q4 (2025-12-31 기준)</p>
    <p class="mt-1 text-slate-400">Generated at 2026-10-31 · Internal Report Mode (No Git Commit)</p>
  </footer>

  <!-- Embedded Data & Chart Rendering Scripts -->
  <script>
    const data = {json_str};
    const seoulGeoData = {geo_str};

    // 권역 정의
    const REGION_MAP = {{
      '강남구': '동남권', '서초구': '동남권', '송파구': '동남권', '강동구': '동남권',
      '종로구': '도심권', '중구': '도심권', '용산구': '도심권',
      '마포구': '서북권', '서대문구': '서북권', '은평구': '서북권',
      '영등포구': '서남권', '구로구': '서남권', '금천구': '서남권', '동작구': '서남권', '관악구': '서남권', '강서구': '서남권', '양천구': '서남권',
      '성동구': '동북권', '광진구': '동북권', '동대문구': '동북권', '중랑구': '동북권', '성북구': '동북권', '강북구': '동북권', '도봉구': '동북권', '노원구': '동북권'
    }};

    // Global Chart.js Light Mode Defaults
    Chart.defaults.color = '#64748b';
    Chart.defaults.font.family = 'Pretendard, -apple-system, sans-serif';

    // 1. Gu Ranking Chart
    const guLabels = Object.keys(data.gu_counts);
    const guValues = Object.values(data.gu_counts);
    new Chart(document.getElementById('guRankingChart'), {{
      type: 'bar',
      data: {{
        labels: guLabels,
        datasets: [{{
          label: '등록 점포 수',
          data: guValues,
          backgroundColor: guValues.map((v, i) => i < 3 ? '#4f46e5' : '#3b82f6'),
          borderRadius: 4
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              afterLabel: function(ctx) {{
                const pct = ((ctx.raw / data.dataset_info.total_stores) * 100).toFixed(2);
                return `비중: ${{pct}}%`;
              }}
            }}
          }}
        }},
        scales: {{
          x: {{
            grid: {{ display: false }},
            ticks: {{ color: '#64748b', font: {{ size: 10 }} }}
          }},
          y: {{
            grid: {{ color: '#f1f5f9' }},
            ticks: {{ color: '#64748b' }}
          }}
        }}
      }}
    }});

    // 2. Macro Industry Chart
    const macroLabels = Object.keys(data.macro_counts);
    const macroValues = Object.values(data.macro_counts);
    const macroColors = [
      '#f43f5e', '#3b82f6', '#8b5cf6', '#f59e0b', '#10b981',
      '#06b6d4', '#ec4899', '#64748b', '#84cc16', '#a855f7'
    ];
    new Chart(document.getElementById('macroIndustryChart'), {{
      type: 'doughnut',
      data: {{
        labels: macroLabels,
        datasets: [{{
          data: macroValues,
          backgroundColor: macroColors,
          borderWidth: 2,
          borderColor: '#ffffff'
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'right',
            labels: {{ color: '#334155', boxWidth: 12, font: {{ size: 11 }} }}
          }},
          tooltip: {{
            callbacks: {{
              label: function(ctx) {{
                const val = ctx.raw;
                const pct = ((val / data.dataset_info.total_stores) * 100).toFixed(1);
                return ` ${{ctx.label}}: ${{val.toLocaleString()}}개 (${{pct}}%)`;
              }}
            }}
          }}
        }},
        cutout: '65%'
      }}
    }});

    // 3. Sub Industry TOP 12 Chart
    const subEntries = Object.entries(data.sub_counts).slice(0, 12);
    new Chart(document.getElementById('subIndustryChart'), {{
      type: 'bar',
      data: {{
        labels: subEntries.map(e => e[0]),
        datasets: [{{
          label: '점포 수',
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
          x: {{ grid: {{ color: '#f1f5f9' }}, ticks: {{ color: '#64748b' }} }},
          y: {{ grid: {{ display: false }}, ticks: {{ color: '#334155', font: {{ size: 11, weight: '500' }} }} }}
        }}
      }}
    }});

    // 4. Brand Counts Chart
    const brandEntries = Object.entries(data.brand_counts).slice(0, 10);
    new Chart(document.getElementById('brandChart'), {{
      type: 'bar',
      data: {{
        labels: brandEntries.map(e => e[0]),
        datasets: [{{
          label: '매장 수',
          data: brandEntries.map(e => e[1]),
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
          x: {{ grid: {{ color: '#f1f5f9' }}, ticks: {{ color: '#64748b' }} }},
          y: {{ grid: {{ display: false }}, ticks: {{ color: '#334155', font: {{ size: 11, weight: '500' }} }} }}
        }}
      }}
    }});

    // 5. Cafe Gu Chart & Dong list
    const cafeGuLabels = Object.keys(data.cafe_gu_counts);
    const cafeGuValues = Object.values(data.cafe_gu_counts);
    new Chart(document.getElementById('cafeGuChart'), {{
      type: 'bar',
      data: {{
        labels: cafeGuLabels,
        datasets: [{{
          label: '카페 등록 수',
          data: cafeGuValues,
          backgroundColor: '#e11d48',
          borderRadius: 4
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#64748b', font: {{ size: 10 }} }} }},
          y: {{ grid: {{ color: '#f1f5f9' }}, ticks: {{ color: '#64748b' }} }}
        }}
      }}
    }});

    const cafeDongContainer = document.getElementById('cafeDongList');
    const cafeDongEntries = Object.entries(data.cafe_dong_counts).slice(0, 8);
    cafeDongEntries.forEach(([dong, cnt], idx) => {{
      const div = document.createElement('div');
      div.className = 'flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200 shadow-2xs';
      div.innerHTML = `
        <span class="text-slate-800 font-medium">
          <span class="text-slate-400 mr-2 font-mono">${{idx + 1}}</span>${{dong}}
        </span>
        <span class="font-bold text-rose-600 font-mono">${{cnt.toLocaleString()}}개</span>
      `;
      cafeDongContainer.appendChild(div);
    }});

    // 6. Diversity Chart
    const divEntries = Object.entries(data.gu_diversity);
    new Chart(document.getElementById('diversityChart'), {{
      type: 'line',
      data: {{
        labels: divEntries.map(e => e[0]),
        datasets: [{{
          label: 'Shannon 다양성 지수',
          data: divEntries.map(e => e[1]),
          borderColor: '#7c3aed',
          backgroundColor: 'rgba(124, 58, 237, 0.08)',
          fill: true,
          tension: 0.3,
          pointBackgroundColor: '#6d28d9',
          pointRadius: 4
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{ grid: {{ display: false }}, ticks: {{ color: '#64748b', font: {{ size: 10 }} }} }},
          y: {{ min: 4.4, max: 4.75, grid: {{ color: '#f1f5f9' }}, ticks: {{ color: '#64748b' }} }}
        }}
      }}
    }});

    // ==========================================
    // 7. Interactive Minimalist Focused Map Setup
    // ==========================================
    // 서울시 바운딩박스 정의
    const SEOUL_BOUNDS = L.latLngBounds([37.428, 126.764], [37.701, 127.183]);

    // 미니멀한 Esri Light Gray Base (잡다한 도로/텍스트가 없는 최적의 모노톤 배경)
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

    // 초기 위치: 서울 전체가 시원하게 화면에 꽉 차도록 fitBounds
    function resetSeoulView() {{
      map.fitBounds(SEOUL_BOUNDS, {{ padding: [20, 20] }});
    }}
    resetSeoulView();

    // ------------------------------------------
    // A. 서울시 외곽 반전 마스크 (Seoul Spotlight Mask)
    // ------------------------------------------
    // 서울 외곽 지역을 연한 회색 음영으로 덮어 서울시만 스포트라이트를 주는 효과
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

    // 전 세계를 덮는 큰 외곽 사각형
    const worldOuterRing = [
      [-90, -180],
      [-90, 180],
      [90, 180],
      [90, -180]
    ];

    // 서울 외곽 마스크 폴리곤 레이어 (서울 외 지역을 깔끔한 단색 회색으로 차분하게 마스킹)
    const maskPolygon = L.polygon([worldOuterRing, ...seoulCoordinatesRings], {{
      color: 'transparent',
      fillColor: '#94a3b8',
      fillOpacity: 0.35,
      interactive: false
    }}).addTo(map);

    // ------------------------------------------
    // B. 서울시 25개 자치구 폴리곤 레이어 (순백색 하이라이트)
    // ------------------------------------------
    const guGeoLayer = L.geoJSON(seoulGeoData, {{
      style: function(feature) {{
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
        const storeCount = data.gu_counts[guName] ? data.gu_counts[guName].toLocaleString() : 0;
        
        layer.on({{
          mouseover: function(e) {{
            const target = e.target;
            target.setStyle({{
              fillColor: '#eff6ff',
              fillOpacity: 0.95,
              color: '#3b82f6',
              weight: 2,
              dashArray: ''
            }});
            target.bringToFront();
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

    // ------------------------------------------
    // C. 클러스터링 그룹 및 마커 생성 (MarkerCluster)
    // ------------------------------------------
    let currentIndustryFilter = 'ALL';
    let currentRegionFilter = 'ALL';

    // Leaflet MarkerCluster Group 생성
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
        if (sub.includes('커피') || sub.includes('카페') || name.includes('카페') || name.includes('커피')) {{
          return '#ec4899'; // 카페: 핑크
        }}
        return '#e11d48'; // 일반 음식: 로즈 레드
      }}
      if (cat === '소매') return '#2563eb';      // 소매: 블루
      if (cat === '과학·기술') return '#7c3aed';  // 과학기술: 퍼플
      if (cat === '수리·개인') return '#d97706';  // 수리개인: 앰버
      if (cat === '교육') return '#059669';      // 교육: 에메랄드
      return '#0284c7'; // 기타: 시안
    }}

    function updateClusterGroup() {{
      clusterGroup.clearLayers();
      const newMarkers = [];

      data.map_points_sample.forEach(pt => {{
        // 1. 업종 필터 검사
        let matchIndustry = false;
        if (currentIndustryFilter === 'ALL') {{
          matchIndustry = true;
        }} else if (currentIndustryFilter === 'CAFE') {{
          matchIndustry = pt.cat_sub.includes('커피') || pt.cat_sub.includes('카페') || pt.name.includes('카페') || pt.name.includes('커피');
        }} else {{
          matchIndustry = (pt.cat_macro === currentIndustryFilter);
        }}

        // 2. 권역 필터 검사
        let matchRegion = false;
        if (currentRegionFilter === 'ALL') {{
          matchRegion = true;
        }} else {{
          const ptRegion = REGION_MAP[pt.gu] || '기타';
          matchRegion = (ptRegion === currentRegionFilter);
        }}

        if (!matchIndustry || !matchRegion) return;

        const color = getColorByMacro(pt.cat_macro, pt.cat_sub, pt.name);
        const marker = L.circleMarker([pt.lat, pt.lng], {{
          radius: 6,
          fillColor: color,
          color: '#ffffff',
          weight: 1.5,
          opacity: 1,
          fillOpacity: 0.9
        }});

        marker.bindPopup(`
          <div style="font-family: Pretendard, sans-serif; color: #0f172a; padding: 4px; min-width: 150px;">
            <div style="font-weight: 700; font-size: 13px; color: #0f172a; line-height: 1.3;">${{pt.name}}</div>
            <div style="font-size: 11px; color: #64748b; margin-top: 3px;">
              ${{pt.gu}} ${{pt.dong}} <span style="color: #94a3b8;">|</span> ${{pt.floor}}층
            </div>
            <div style="margin-top: 6px; display: inline-flex; align-items: center; gap: 4px; padding: 2px 7px; background: #eff6ff; color: #1d4ed8; border-radius: 4px; font-size: 10px; font-weight: 600; border: 1px solid #bfdbfe;">
              ${{pt.cat_macro}} > ${{pt.cat_sub}}
            </div>
          </div>
        `);

        newMarkers.push(marker);
      }});

      clusterGroup.addLayers(newMarkers);
    }}

    // 업종 필터 변경 핸들러
    function setIndustryFilter(cat) {{
      currentIndustryFilter = cat;
      document.querySelectorAll('#industryFilterGroup .filter-btn').forEach(btn => {{
        if (btn.getAttribute('data-cat') === cat) {{
          btn.className = 'filter-btn active px-3 py-1 rounded-full text-xs font-semibold bg-blue-600 text-white shadow-2xs transition';
        }} else {{
          btn.className = 'filter-btn px-3 py-1 rounded-full text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:bg-slate-100 transition';
        }}
      }});
      updateClusterGroup();
    }}

    // 권역 필터 변경 핸들러
    function setRegionFilter(region) {{
      currentRegionFilter = region;
      document.querySelectorAll('#regionFilterGroup .region-btn').forEach(btn => {{
        if (btn.getAttribute('data-region') === region) {{
          btn.className = 'region-btn active px-2.5 py-0.5 rounded-md text-xs font-semibold bg-slate-800 text-white shadow-2xs transition';
        }} else {{
          btn.className = 'region-btn px-2.5 py-0.5 rounded-md text-xs font-medium bg-white text-slate-600 border border-slate-200 hover:bg-slate-100 transition';
        }}
      }});
      updateClusterGroup();
    }}

    // 초기 마커 렌더링
    updateClusterGroup();
  </script>
</body>
</html>
"""

out_html1 = REPORT_DIR / "index.html"
out_html2 = REPORT_DIR / "semas_eda_dashboard.html"

with open(out_html1, "w", encoding="utf-8") as f:
    f.write(html_content)

with open(out_html2, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Successfully generated focused minimalist map with clustering:\n- {out_html1}\n- {out_html2}")
