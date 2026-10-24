"""Family AD: sweep of a pre-known level + the FVG left by the sweep gets inverted (IFVG).
   side=-1: sweep a high, bullish gap printed on the sweep leg, price closes back below it,
            sell the retest of that inverted gap. Mirror for longs."""
import numpy as np, pandas as pd, pickle, sys
sys.path.insert(0,"research/scripts"); from lib import *
SESS=pickle.load(open("research/data/sessions.pkl","rb"))
for s in SESS:
    s["atr"]=atr(s["h"],s["l"],s["c"],14)
    s["ema20"]=pd.Series(s["c"]).ewm(adjust=False,span=20).mean().to_numpy()
LVK=[("on_l","on_h"),("pm_l","pm_h"),("pdl","pdh")]

def fin(s,k,entry,stop,side,extra):
    o,h,l,c,m=s["o"],s["h"],s["l"],s["c"],s["mod"]; risk=(entry-stop)*side
    if risk<=0: return None
    sim=simulate(o,h,l,c,m,k,entry,stop,side)
    if sim is None: return None
    res,px,bh,ei,mfe=sim
    g=2.0 if res=="target" else (-1.0 if res=="stop" else (px-entry)*side/risk)
    return dict(date=s["date"],side=side,entry_t=m[k],risk=round(risk,2),entry=entry,stop=stop,
                outcome=res,R=round(g-COST_PTS/risk,4),gross=g,mfe=mfe,bars=bh,**extra)

def gen(s, max_gap_look=6, inv_deadline=11*60+10):
    o,h,l,c,m,v,A=s["o"],s["h"],s["l"],s["c"],s["mod"],s["v"],s["atr"]; lv=s["lv"]; n=len(h); out=[]
    for lname,hname in LVK:
        for side,(L,nm) in ((1,(lv.get(lname),lname)),(-1,(lv.get(hname),hname))):
            if L is None or L!=L: continue
            best_done=False
            for i in range(2,n-3):
                if m[i]>11*60+20 or best_done: break
                if A[i]!=A[i] or A[i]<=0: continue
                rng=h[i]-l[i]
                if side==1:
                    if not (l[i]<L and c[i]>L): continue
                    ext,rej=l[i],(c[i]-l[i])/rng if rng>0 else 0
                else:
                    if not (h[i]>L and c[i]<L): continue
                    ext,rej=h[i],(h[i]-c[i])/rng if rng>0 else 0
                # the gap created on the sweep leg (a gap AGAINST the reversal: bullish gap above a swept high)
                for j in range(max(2,i-2), min(i+max_gap_look, n-2)):
                    if side==-1:
                        if not (l[j] > h[j-2] + 1*TICK): continue
                        glo,ghi = h[j-2], l[j]
                        if not (glo >= L - 2*TICK): continue      # gap sits above/at the swept level
                    else:
                        if not (h[j] < l[j-2] - 1*TICK): continue
                        ghi,glo = l[j-2], h[j]
                        if not (ghi <= L + 2*TICK): continue
                    gt=(ghi-glo)/TICK
                    if gt<4: continue
                    inv=None
                    for u in range(j+1, n):
                        if m[u]>inv_deadline: break
                        if side==-1 and c[u]<glo: inv=u; break
                        if side==1  and c[u]>ghi: inv=u; break
                    if inv is None: continue
                    for emode,entry in (("edge",glo if side==-1 else ghi),("fifty",(glo+ghi)/2)):
                        for smode in ("sweep","gap"):
                            stop=(max(ext,ghi) if side==-1 else min(ext,glo)) if smode=="sweep" \
                                 else (ghi if side==-1 else glo)
                            stop=stop+2*TICK*side
                            risk=(entry-stop)*side
                            if not (8<=risk<=120): continue
                            for k in range(inv+1,n):
                                if m[k]>11*60+30: break
                                if (l[k]<=stop) if side==1 else (h[k]>=stop): break
                                if (l[k]<=entry) if side==1 else (h[k]>=entry):
                                    t=fin(s,k,entry,stop,side,dict(fam="AD",level=nm,sweep_t=m[i],gap_t=gt,
                                        wait=k-inv,nb=k-inv,rej=round(rej,2),
                                        disp=round(abs(c[j]-o[j])/A[j],2) if A[j]>0 else np.nan,
                                        emode=emode,smode=smode,sweep_depth=round((L-ext)*side/TICK,1),
                                        inv_lag=u-j,atr=A[i],pdc=lv.get("pdc"),on_h=lv.get("on_h"),
                                        on_l=lv.get("on_l"),pm_h=lv.get("pm_h"),pm_l=lv.get("pm_l"),
                                        pdh=lv.get("pdh"),pdl=lv.get("pdl"),ema_up=int(c[i]>s["ema20"][i]),
                                        first_touch=int(np.all(l[:i]>L-1*TICK) if side==1 else np.all(h[:i]<L+1*TICK))))
                                    if t: out.append(t)
                                    break
                    best_done=True
                    break
    return out

rows=[]
for s in SESS: rows+=gen(s)
p=pd.DataFrame(rows); p["year"]=pd.to_datetime(p.date).dt.year
print("pool5",len(p)); p.to_parquet("research/data/pool5.parquet")
p["is_is"]=p.date<="2022-12-31"
def rep(d,lbl):
    d=d.sort_values("entry_t").drop_duplicates("date")
    if len(d)<40: return
    a,b=d[d.is_is],d[~d.is_is]
    f=lambda x:f"n={len(x):4d} w={100*(x.R>0).mean():5.1f}% e={x.R.mean():+.3f}"
    print(f"{lbl:30s} ALL {f(d)} | IS {f(a)} | OOS {f(b)}")
for lv in ["all","on_h","on_l","pm_h","pm_l","pdh","pdl"]:
    q=p if lv=="all" else p[p.level==lv]
    for em in ["edge","fifty"]:
        for sm in ["sweep","gap"]:
            rep(q[(q.emode==em)&(q.smode==sm)], f"{lv} {em}/{sm}")
