import numpy as np, pandas as pd, sys
sys.path.insert(0,"research/scripts")
from final_mtf import select, RRS, RR_LABEL, CONF
pd.set_option("display.width",260)
P = pd.read_parquet("research/data/pool_mtf.parquet")
P["dt"]=pd.to_datetime(P.date); P["year"]=P.dt.dt.year
P["is_is"]=P.date<="2022-12-31"

def summ(d,label):
    out=dict(config=label,n=len(d),py=round(len(d)/6.8,0))
    for r in RRS:
        w,R=f"w{r:g}",f"R{r:g}"
        gp,gl=d[R][d[R]>0].sum(),abs(d[R][d[R]<=0].sum())
        out[f"w{int(round(r*100))}"]=round(100*d[w].mean(),1)
        out[f"R{int(round(r*100))}"]=round(d[R].mean(),3)
        out[f"PF{int(round(r*100))}"]=round(gp/gl,2) if gl else np.nan
    a,b=d[d.is_is],d[~d.is_is]
    out["w2_is"]=round(100*a["w2"].mean(),1); out["w2_oos"]=round(100*b["w2"].mean(),1)
    yrs=d.groupby("year")["R2"].apply(lambda x:100*(x>0).mean())
    out["minYr_w2"]=round(yrs.loc[yrs.index>=2020].min(),1)
    out["yrs+"]=int((d.groupby("year")["R2"].sum()>0).sum())
    return out

cfgs=[]
for mc in (0,1,2,3):
    for mpd in (1,2,99):
        for ra in (None, 0.08):
            d=select(P,min_conf=mc,max_per_day=mpd)
            if ra is not None: d=d[d.risk_atr<=ra]
            if len(d)<60: continue
            cfgs.append(summ(d, f"conf>={mc} max{mpd}/day" + (f" risk_atr<={ra:.0%}" if ra else "")))
T=pd.DataFrame(cfgs)
T.to_csv("research/out/mtf_configs.csv",index=False)
print("=== config comparison (win% at each R:R + R/trade at 1:2) ===")
print(T[["config","n","py","w200","w150","w100","w75","w67","w50","R200","PF200","w2_is","w2_oos","minYr_w2","yrs+"]].to_string(index=False))
