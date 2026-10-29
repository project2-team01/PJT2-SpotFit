"""2026-10-17 EDA 재계산. 원본/전처리 파일을 변경하지 않고 표를 stdout에 출력한다.

실행: python3 김지영/eda_1017.py
필요 라이브러리: pandas, numpy. Excel은 표준 라이브러리로 값을 읽는다.
소비 집중 동을 유지하며, 로그 회귀는 자치구 단위 교차검증으로 진단한다.
"""
from pathlib import Path
import hashlib
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
K, Q = "행정동_코드", "기준_년분기_코드"
INPUTS = set()


def read(name):
    p = ROOT / "data" / name
    INPUTS.add(p)
    return pd.read_csv(p, encoding="utf-8-sig", low_memory=False)


def show(title, data):
    print("\n### " + title)
    if isinstance(data, (pd.DataFrame, pd.Series)):
        print(data.to_string(float_format=lambda x: f"{x:,.5f}"))
    else:
        print(data)


def rho(a, b):
    d = pd.concat([a, b], axis=1).dropna()
    return len(d), d.iloc[:, 0].rank().corr(d.iloc[:, 1].rank())


def excel_values(path):
    """첫 시트의 값을 셀 주소로 복원하고 수식·오류가 있으면 검토를 요청한다."""
    INPUTS.add(path)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as z:
        strings = ["".join(si.itertext()) for si in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        records, header = [], None
        for _, row in ET.iterparse(z.open("xl/worksheets/sheet1.xml"), events=("end",)):
            if row.tag != ns + "row":
                continue
            cells = {}
            for c in row.findall(ns + "c"):
                assert c.find(ns + "f") is None, "수식 셀은 별도 검토 필요"
                assert c.get("t") != "e", "Excel 오류 셀"
                pos = 0
                for letter in c.get("r").rstrip("0123456789"):
                    pos = pos * 26 + ord(letter) - 64
                v = c.find(ns + "v")
                value = None if v is None else v.text
                if c.get("t") == "s" and value is not None:
                    value = strings[int(value)]
                elif c.get("t") == "inlineStr":
                    value = "".join(t.text or "" for t in c.iter(ns + "t"))
                elif value is not None:
                    value = float(value)
                cells[pos] = value
            if header is None:
                header = {i: v for i, v in cells.items() if v is not None}
            else:
                records.append([cells.get(i) for i in header])
            row.clear()
    return pd.DataFrame(records, columns=list(header.values()))


def main():
    m = read("processed/행정동_마스터.csv").set_index(K)
    p = read("processed/행정동_분기.csv")
    t = read("processed/상권_업종_분기.csv")
    mapping = read("processed/업종_공통그룹.csv")
    c = read("raw/OA-22166_소비_행정동.csv")
    s = read("raw/상권/OA-15572_추정매출_상권.csv")
    st = read("raw/상권/OA-15577_점포_상권.csv")
    area = read("raw/상권/OA-15560_영역_상권.csv")
    cats = [x for x in c if x.endswith("_지출_총금액")]
    assert m.index.is_unique and len(m) == 425
    assert not p.duplicated([K, Q]).any() and len(p) == 1700
    assert not t.duplicated([Q, "상권_코드", "서비스_업종_코드"]).any()
    assert not mapping.duplicated(["원본출처", "원본코드"]).any()
    assert set(p[Q]) == {20251, 20252, 20253, 20254}
    assert (c[cats].sum(axis=1) == c["지출_총금액"]).all()
    raw_index = c.set_index([K, Q])
    processed_index = p.set_index([K, Q]).reindex(raw_index.index)
    assert np.array_equal(raw_index[["지출_총금액"] + cats], processed_index[["지출_총금액"] + cats])
    y = c.groupby(K)[["지출_총금액"] + cats].sum().join(m.drop(columns="소비_연간_지출_총금액"))
    assert np.array_equal(y["지출_총금액"], m["소비_연간_지출_총금액"].reindex(y.index))
    share = y[cats].div(y["지출_총금액"], axis=0)
    assert ((share.max(axis=1) >= .9) == y["소비_이상치"]).all()
    y["총_유동인구_수"] = p.groupby(K)["총_유동인구_수"].mean()
    show("shape", [(name, d.shape) for name, d in [("master", m.reset_index()), ("panel", p), ("trade", t), ("mapping", mapping)]])
    show("missing master", m.isna().sum()[lambda z: z > 0])
    show("missing panel", p.isna().sum()[lambda z: z > 0])
    show("negative consumption", c.loc[(c[cats] < 0).any(axis=1), [Q, K, "행정동_코드_명"] + cats])
    show("annual summary (억 원)", (y["지출_총금액"] / 1e8).describe(percentiles=[.25, .5, .75, .95, .99]))
    v = np.sort(y["지출_총금액"].to_numpy(dtype=float)); n = len(v)
    show("concentration", {"total_trillion": v.sum() / 1e12, "gini": (2 * np.dot(np.arange(1,n+1), v)/(n*v.sum())-(n+1)/n),
         "top5_pct": 100 * v[-5:].sum()/v.sum(), "top21_pct": 100*v[-21:].sum()/v.sum(),
         "flag_pct": 100*y.loc[y["소비_이상치"], "지출_총금액"].sum()/v.sum()})
    show("annual top10", y.nlargest(10,"지출_총금액")[["행정동_명", "지출_총금액", "소비_최대항목", "소비_최대항목_비중", "소비_이상치"]])
    show("flag8", y[y["소비_이상치"]][["행정동_명","지출_총금액","소비_최대항목","소비_최대항목_비중"]].sort_values("지출_총금액",ascending=False))
    group = y.groupby("소비_이상치")["지출_총금액"].agg(["size", "sum", "mean", "median"])
    show("flag groups", group)
    mix = pd.DataFrame({"서울합계비중": y[cats].sum()/y["지출_총금액"].sum()*100,
                        "동별비중중앙값": share.median()*100})
    for flag in [False, True]:
        z = y[y["소비_이상치"] == flag]
        mix[str(flag)+"그룹합계비중"] = z[cats].sum()/z["지출_총금액"].sum()*100
    show("composition", mix)
    predictors = ["총_상주인구_수", "총_직장_인구_수", "총_유동인구_수", "집객시설_수", "은행_수", "지하철_역_수", "아파트_평균_시가", "자치구_평균소득월액"]
    show("correlations annual", pd.DataFrame([(x,*rho(y["지출_총금액"],y[x])) for x in predictors],columns=["변수","n","rho"]))
    q = c.merge(m[["소비_이상치"]], left_on=K, right_index=True).groupby([Q,"소비_이상치"])["지출_총금액"].sum().unstack()
    q.columns = ["비표시동_지출", "표시동_지출"]
    q["전체지출"] = q.sum(axis=1)
    q["추정매출"] = s.groupby(Q)["당월_매출_금액"].sum()
    for label,d in [("100업종",st),("62업종",t)]:
        g = d.groupby(Q)[["전체_점포_수","개업_점포_수","폐업_점포_수"]].sum()
        q[label+"_점포"] = g["전체_점포_수"]
        q[label+"_개업률"] = g["개업_점포_수"]/g["전체_점포_수"]*100
        q[label+"_폐업률"] = g["폐업_점포_수"]/g["전체_점포_수"]*100
    show("quarter", q)
    show("Q4 vs Q1 pct", (q.iloc[-1]/q.iloc[0]-1)*100)
    show("Q1Q4 contribution", (q.iloc[-1]-q.iloc[0])[["비표시동_지출","표시동_지출"]]/(q.iloc[-1]-q.iloc[0])["전체지출"]*100)

    coverage = t.groupby("공통그룹").agg(rows=("상권_코드","size"), observed=("당월_매출_금액","count"),sales=("당월_매출_금액","sum"), stores=("전체_점포_수","sum"), opens=("개업_점포_수","sum"),closes=("폐업_점포_수","sum"))
    coverage["observed_pct"] = coverage.observed/coverage.rows*100
    coverage["sales_pct"] = coverage.sales/s["당월_매출_금액"].sum()*100
    coverage["open_pct"] = coverage.opens/coverage.stores*100
    coverage["close_pct"] = coverage.closes/coverage.stores*100
    show("sales coverage and group turnover", coverage.sort_values("sales",ascending=False))
    show("sales missing", {"missing":int(t["당월_매출_금액"].isna().sum()),"pct":100*t["당월_매출_금액"].isna().mean()})
    cg = t.groupby([K,Q,"공통그룹"])["당월_매출_금액"].agg(["size","count"])
    show("all missing dong-quarter-group", cg[cg["count"]==0].groupby("공통그룹").size())
    dg = t.groupby([K,Q])["당월_매출_금액"].agg(["size","count"])
    show("all missing dong-quarter", dg[dg["count"]==0])
    # 분석용 메모리에서만 결측을 복원. 원본/공용 산출물에는 쓰지 않는다.
    observed_sales = t.groupby([K,Q])["당월_매출_금액"].sum(min_count=1)
    p_checked = p.set_index([K,Q]).copy()
    p_checked["상권_매출_금액"] = observed_sales.reindex(p_checked.index)
    show("analysis-view missing sales", int(p_checked["상권_매출_금액"].isna().sum()))
    raw_sales = s.merge(area[["상권_코드",K]], on="상권_코드", validate="many_to_one").groupby([K,Q])["당월_매출_금액"].sum()
    assert np.array_equal(raw_sales, p_checked["상권_매출_금액"].reindex(raw_sales.index))
    show("all missing group count", int((cg["count"]==0).sum()))
    show("rate extremes", {"open_gt100":int((st["개업_율"]>100).sum()),"close_gt100":int((st["폐업_률"]>100).sum()), "max_close":st["폐업_률"].max(),"zero_denominator":int((st["전체_점포_수"]==0).sum())})
    for label,d in [("100업종",st),("62업종",t)]:
        show(label+" pooled rates", {"open":100*d["개업_점포_수"].sum()/d["전체_점포_수"].sum(),"close":100*d["폐업_점포_수"].sum()/d["전체_점포_수"].sum()})
    for prefix in ["시간대_", "연령대_", "요일"]:
        cc=[x for x in s if x.endswith("_매출_금액") and (x.startswith(prefix) if prefix!="요일" else "요일_" in x)]
        show("sales mix "+prefix, s[cc].sum()/s[cc].sum().sum()*100)
    show("gender coverage pct", 100*s[["남성_매출_금액","여성_매출_금액"]].sum().sum()/s["당월_매출_금액"].sum())
    tc=[x for x in s if x.startswith("시간대_") and x.endswith("매출_건수")]
    dif=s["당월_매출_건수"]-s[tc].sum(axis=1)
    show("time count discrepancy",s.loc[dif!=0,[Q,"상권_코드_명","서비스_업종_코드_명","당월_매출_건수"]].assign(차이=dif[dif!=0]))
    ch=read("raw/상권/OA-15576_상권변화지표_상권.csv")
    show("Q4 change labels",ch.loc[ch[Q]==20254,"상권_변화_지표_명"].value_counts())

    # 연간 동 1개당 1행. 8개 집중 동 전부 유지. 직장인구 결측 11개만 complete-case 제외.
    xs=["총_상주인구_수","총_직장_인구_수","총_유동인구_수","집객시설_수"]
    model=y.dropna(subset=xs).copy()
    X=np.column_stack([np.ones(len(model)),np.log1p(model[xs].to_numpy())])
    target=np.log(model["지출_총금액"].to_numpy())
    beta=np.linalg.lstsq(X,target,rcond=None)[0]
    fitted=X@beta; pred=np.zeros(len(model)); baseline=np.zeros(len(model))
    for gu in model["자치구_코드"].unique():
        test=(model["자치구_코드"].to_numpy()==gu); train=~test
        pred[test]=X[test]@np.linalg.lstsq(X[train],target[train],rcond=None)[0]
        baseline[test]=target[train].mean()
    ss=((target-target.mean())**2).sum()
    model["OOF_실제_기준값_배수"]=np.exp(target-pred)
    show("model",{"n":len(model),"flag_n":int(model["소비_이상치"].sum()),"train_log_r2":1-((target-fitted)**2).sum()/ss,"OOF_log_r2":1-((target-pred)**2).sum()/ss,"OOF_baseline_log_r2":1-((target-baseline)**2).sum()/ss,"OOF_log_MAE":abs(target-pred).mean(),"OOF_median_multiplicative_error":np.exp(np.median(abs(target-pred)))})
    mc=["행정동_명","소비_이상치","OOF_실제_기준값_배수"]
    show("OOF top10",model.nlargest(10,mc[-1])[mc]);show("OOF bottom10",model.nsmallest(10,mc[-1])[mc])

    skt_stats=[]
    for month in ["03","06","09","12"]:
        x=excel_values(ROOT/"data"/"raw"/"living"/f"통신정보_2025.{month}.xlsx")
        key=["행정동코드","성별","연령대"]
        assert not x.duplicated(key).any()
        for col in ["SNS 사용횟수","유튜브 사용일수","넷플릭스 사용일수","배달 서비스 사용일수","쇼핑 서비스 사용일수","금융 서비스 사용일수"]:
            a=pd.to_numeric(x[col])
            skt_stats.append([month,col,len(x),a.min(),a.max(),int((a<0).sum()),int((a>31).sum())])
        if month=="12":
            x["연령대"]=pd.to_numeric(x["연령대"])
            metrics=["배달 서비스 사용일수","쇼핑 서비스 사용일수","금융 서비스 사용일수"]
            age=pd.DataFrame({col:(x.assign(w=x[col]*x["총인구수"]).groupby("연령대")["w"].sum()/x.groupby("연령대")["총인구수"].sum()) for col in metrics})
            show("SKT age Dec",age)
    show("SKT raw ranges",pd.DataFrame(skt_stats,columns=["month","metric","n","min","max","negative","gt31"]))
    sk=p[p[Q]==20254].merge(m[["자치구_명"]],left_on=K,right_index=True)
    skg=sk.groupby("자치구_명")[["SKT_1인가구수","SKT_총인구"]].sum(min_count=1)
    show("SKT Dec household ratio",(100*skg["SKT_1인가구수"]/skg["SKT_총인구"]).sort_values())
    show("stores snapshot gu",m.groupby("자치구_명")["점포_202512_전체"].sum().sort_values(ascending=False))
    show("stores snapshot category",m[[z for z in m if z.startswith("점포_202512_")]].sum())
    nps=read("raw/국민연금_시군구_평균소득월액_2025.csv")
    show("NPS Seoul",nps[nps["시군구"].str.startswith("서울")].sort_values("평균소득월액",ascending=False))
    nt=read("raw/naver_trend/naver_trend_10categories_monthly.csv").set_index("period")
    show("Naver own mean peak",pd.DataFrame({"최고월":nt.idxmax(),"자기평균대비_pct":100*(nt.max()/nt.mean()-1)}))
    ntg=read("raw/naver_trend/naver_trend_25gu_top5_monthly.csv")
    show("Naver zero",{"count":int((ntg["검색지수"]==0).sum()),"keywords":ntg.loc[ntg["검색지수"]==0,"키워드"].nunique()})
    for name in ["OA-22163_아파트_행정동.csv","OA-22169_집객시설_행정동.csv","OA-22183_상주인구_행정동.csv","OA-22184_직장인구_행정동.csv"]:
        d=read("raw/"+name)
        measures=[z for z in d if z not in [Q,K,"행정동_코드_명"]]
        assert not (d.groupby(K)[measures].nunique(dropna=False)>1).any().any()
    gu=read("raw/OA-22167_소비_자치구.csv").rename(columns={K:"구코드"}).set_index([Q,"구코드"])
    dong_totals=c.assign(구코드=c[K]//1000).groupby([Q,"구코드"])[["지출_총금액"]+cats].sum()
    assert np.array_equal(dong_totals,gu.reindex(dong_totals.index)[dong_totals.columns])
    for suffix in ["금액","건수"]:
        day_cols=[z for z in s if "요일_" in z and z.endswith("매출_"+suffix)]
        assert (s["당월_매출_"+suffix] == s[day_cols].sum(axis=1)).all()
    show("검증", "소비 원천-전처리 일치, 연간 플래그 일치, 동-구 합계 일치, 관측 매출 합계 일치, 고정변수 분기 동일, 매출 요일 합계 일치")
    show("input sha256", "\n".join(f"{path.relative_to(ROOT)}  {hashlib.sha256(path.read_bytes()).hexdigest()}" for path in sorted(INPUTS)))


if __name__ == "__main__":
    main()
