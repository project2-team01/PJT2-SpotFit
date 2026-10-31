# -*- coding: utf-8 -*-
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_DIR / "report_latest"

# 1. 서울 행정동에서 자치구 단위 GeoJSON 피처 컬렉션 생성
raw_geo = PROJECT_DIR / "data" / "raw" / "geo" / "HangJeongDong_ver20251231.geojson"
with open(raw_geo, "r", encoding="utf-8") as f:
    geo_data = json.load(f)

# 서울(sido == '11') 피처들 모으기
seoul_dongs = [f for f in geo_data["features"] if f["properties"].get("sido") == "11"]

# 좌표 4자리 반올림 함수
def round_coords(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], 4), round(c[1], 4)]
    return [round_coords(sub) for sub in c]

# 자치구별 MultiPolygon 수집
gu_geoms = {}
for feat in seoul_dongs:
    gu_name = feat["properties"].get("sggnm")
    if gu_name not in gu_geoms:
        gu_geoms[gu_name] = []
    
    geom = feat["geometry"]
    coords = round_coords(geom["coordinates"])
    if geom["type"] == "Polygon":
        gu_geoms[gu_name].append(coords)
    elif geom["type"] == "MultiPolygon":
        for poly in coords:
            gu_geoms[gu_name].append(poly)

gu_features = []
for gu_name, polys in gu_geoms.items():
    gu_features.append({
        "type": "Feature",
        "properties": {"name": gu_name},
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": polys
        }
    })

seoul_geojson = {
    "type": "FeatureCollection",
    "features": gu_features
}

out_geo_path = REPORT_DIR / "seoul_gu_borders.json"
with open(out_geo_path, "w", encoding="utf-8") as f:
    json.dump(seoul_geojson, f, ensure_ascii=False)

print(f"Generated Seoul Gu GeoJSON ({len(gu_features)} districts): {out_geo_path}")

