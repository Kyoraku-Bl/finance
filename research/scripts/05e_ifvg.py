"""Family D refined: IFVG with rich, lookahead-free context features."""
import numpy as np, pandas as pd, pickle, sys
sys.path.insert(0,"research/scripts"); from lib import *
SESS=pickle.load(open("research/data/sessions.pkl","rb"))
for s in SESS:
    s["atr"]=atr(s["h"],s["l"],s["c"],14)
    s["ema20"]=pd.Series(s["c"]).ewm(adjust=False,span=20).mean().to_numpy()
    s["vwap"]=np.cumsum(s["c"]*s["v"])/np.maximum(np.cumsum(s["v"]),1)

def gen(s):
    o,h,l,c,m,v,A=s["o"],s["h"],s["l"],s["c"],s["mod"],s["v"],s["atr"]; lv=s["lv"]; n=len(h); out=[]
    medv=np.nanmedian(v[:20]) if len(v) else np.nan
    gaps=[]
    for j in range(2,n-2):
        if m[j]>11*60+15: break
        if A[j]!=A[j] or A[j]<=0: continue
        if l[j]>h[j-2]+1*TICK: gaps.append((j,1,h[j-2],l[j]))
        elif h[j]<l[j-2]-1*TICK: gaps.append((j,-1,h[j],l[j-2]))
    seen={1:0,-1:0}
    for (j,gs,lo,hi) in sorted(gaps,key=lambda x:x[0]):
        gt=(hi-lo)/TICK; side=-gs
        if gt<4: continue
        inv=None
        for u in range(j+1,n):
            if m[u]>11*60+20: break
            if side==-1 and c[u]<lo: inv=u; break
            if side==1 and c[u]>hi: inv=u; break
        prior=seen[side]; seen[side]+=1
        if inv is None: continue
        for emode,en in (("edge",(lo if side==-1 else hi)),("fifty",(lo+hi)/2)):
            stop=(hi if side==-1 else lo)+2*TICK*side
            risk=(en-stop)*side
            if not (8<=risk<=120): continue
            for k in range(inv+1,n):
                if m[k]>11*60+40: break
                if (l[k]<=stop) if side==1 else (h[k]>=stop): break
                if (l[k]<=en) if side==1 else (h[k]>=en):
                    sim=simulate(o,h,l,c,m,k,en,stop,side)
                    if sim is None: break
                    res,px,bh,ei,mfe=sim
                    g=2.0 if res=="target" else (-1.0 if res=="stop" else (px-en)*side/risk)
                    out.append(dict(date=s["date"],side=side,entry_t=m[k],entry=t[k] if False else en,stop=stop,
                        risk=round(risk,2),gap_t=gt,gap_atr=(hi-lo)/A[j],inv_lag=inv-j,wait=k-inv,
                        nb=k-inv,prior=prior,emode=emode,outcome=res,R=round(g-COST_PTS/risk,4),
                        bars=bh,mfe=mfe,atr=A[j],atr_day=np.nan,
                        gap_lo=lo,gap_hi=hi,inv_t=m[inv],
                        vol_inv=v[inv]/medv if medv else np.nan,
                        dist_open=(en-o[0])/A[j], vs_vwap=(en-s["vwap"][inv])/A[j],
                        ema_up=int(c[inv]>s["ema20"][inv]),
                        disp=abs(c[j]-o[j])/A[j], dow=int(np.datetime64(s["date"]).astype("datetime64[D]").astype(int)%7),
                        **{k2:lv.get(k2) for k2 in ("pdc","on_h","on_l","pm_h","pm_l","pdh","pdl")}))
                    break
    return out
rows=[]
for s in SESS: rows+=gen(s)
P=pd.DataFrame(rows)
# prior-day range normaliser (lookahead-free)
import pickle
S=SESS
rng=pd.DataFrame([dict(date=x["date"],rth=(x["h"].max()-x["l"].min()) if len(x["h"]) else np.nan) for x in S])
rng["atr_day"]=rng.rth.shift(1).rolling(5,min_periods=2).mean()
P=P.drop(columns=["atr_day"]).merge(rng[["date","atr_day"]],on="date",how="left")
P["tgt_over_atr"]=2*P.risk/P.atr_day
P["dt"]=pd.to_datetime(P.date); P["year"]=P.dt.dt.year
P["is_is"]=P.date<="2022-12-31"
print("pool6",len(P)); P.to_parquet("research/data/pool6.parquet")
def rep(d,lbl):
    d=d.sort_values("entry_t").drop_duplicates("date")
    if len(d)<40: return
    a,b=d[d.is_is],d[~d.is_is]
    f=lambda x:f"n={len(x):4d} w={100*(x.R>0).mean():5.1f}% e={x.R.mean():+.3f}"
    print(f"{lbl:40s} ALL {f(d)} | IS {f(a)} | OOS {f(b)}")
for em in ["edge","fifty"]:
    for sd in [1,-1]:
        rep(P[(P.emode==em)&(P.side==sd)],f"{em} side={sd}")
    rep(P[P.emode==em],f"{em} all")
print("--- prior (how many earlier IFVGs same side today) ---")
for pr in [0,1,2]:
    rep(P[(P.prior==pr)&(P.emode=="edge")],f"edge prior={pr}")
print("--- inv_lag ---")
for lo,hi in [(1,3),(4,10),(11,30),(31,999)]:
    rep(P[(P.emode=="edge")&(P.inv_lag.between(lo,hi))],f"edge inv_lag {lo}-{hi}")
print("--- gap_atr ---")
for lo,hi in [(0,0.1),(0.1,0.2),(0.2,0.4),(0.4,9)]:
    rep(P[(P.emode=="edge")&(P.gap_atr.between(lo,hi))],f"edge gap_atr {lo}-{hi}")
print("--- vol_inv ---")
for lo,hi in [(0,1),(1,2),(2,99)]:
    rep(P[(P.emode=="edge")&(P.vol_inv.between(lo,hi))],f"edge vol_inv {lo}-{hi}")
print("--- vs_vwap ---")
for lo,hi in [(-99,-1),(-1,0),(0,1),(1,99)]:
    rep(P[(P.emode=="edge")&(P.vs_vwap.between(lo,hi))],f"edge vs_vwap {lo}-{hi}")
