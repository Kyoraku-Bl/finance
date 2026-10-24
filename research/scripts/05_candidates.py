"""Candidate pool: sweep->FVG families with rich, look-ahead-free features."""
import numpy as np, pandas as pd, pickle, sys
sys.path.insert(0,"research/scripts"); from lib import *

SESS = pickle.load(open("research/data/sessions.pkl","rb"))
for s in SESS:
    s["atr"]=atr(s["h"],s["l"],s["c"],14)
    s["ema20"]=pd.Series(s["c"]).ewm(span=20,adjust=False).mean().to_numpy()

LVK=[("on_l","on_h"),("pm_l","pm_h"),("pdl","pdh")]

def feats(s,i,j,k,lv,side):
    o,h,l,c,v,m,A = s["o"],s["h"],s["l"],s["c"],s["v"],s["mod"],s["atr"]
    # was this level already traded through earlier in the session?
    pre_h=h[:i]; pre_l=l[:i]
    lvl = lv["_lvl"]
    first_touch = bool(np.all(pre_l > lvl - 1*TICK)) if side==1 else bool(np.all(pre_h < lvl + 1*TICK))
    return dict(first_touch=int(first_touch),
                sess_rng_atr=(h[:i+1].max()-l[:i+1].min())/A[i] if A[i]>0 else np.nan,
                ema_up=int(c[i] > s["ema20"][i]),
                gap_open_atr=abs(o[0]-lv.get("pdc",o[0]))/A[0] if A[0]>0 else np.nan,
                don_atr=(lv.get("on_h",np.nan)-lv.get("on_l",np.nan))/A[i] if lv.get("on_h")==lv.get("on_h") else np.nan,
                pdr_atr=(lv.get("pdh",np.nan)-lv.get("pdl",np.nan))/A[i] if lv.get("pdh")==lv.get("pdh") else np.nan,
                dow=np.datetime64(s["date"]).astype("datetime64[D]").astype(int)%7)

def gen(s, max_wait, types=("A",)):
    o,h,l,c,m,v,A = s["o"],s["h"],s["l"],s["c"],s["mod"],s["v"],s["atr"]; lv=s["lv"]
    n=len(h); out=[]
    for lname,hname in LVK:
        for side,(L,nm) in ((1,(lv.get(lname),lname)),(-1,(lv.get(hname),hname))):
            if L is None or L!=L: continue
            for i in range(1, n-3):
                if m[i] > 11*60+25: break
                if A[i]!=A[i] or A[i]<=0: continue
                rng=h[i]-l[i]
                if side==1:
                    if not (l[i] < L and c[i] > L): continue
                    ext,rej=l[i],(c[i]-l[i])/rng if rng>0 else 0
                else:
                    if not (h[i] > L and c[i] < L): continue
                    ext,rej=h[i],(h[i]-c[i])/rng if rng>0 else 0
                lvx = dict(lv); lvx["_lvl"]=L
                F = feats(s,i,i,i,lvx,side)
                sweep_depth=(L-ext)*side/TICK
                for j in range(i+1, min(i+max_wait, n-2)):
                    if side==1 and l[j] <= ext - 1*TICK: break
                    if side==-1 and h[j] >= ext + 1*TICK: break
                    if side==1 and l[j] > h[j-2] + 1*TICK:   glo,ghi=h[j-2],l[j]
                    elif side==-1 and h[j] < l[j-2] - 1*TICK: ghi,glo=l[j-2],h[j]
                    else: continue
                    gap_t=(ghi-glo)/TICK
                    disp=abs(c[j]-o[j])/A[j]
                    opts=[]
                    if "A" in types:
                        opts += [("edge", ghi if side==1 else glo, "swing"),
                                 ("edge", ghi if side==1 else glo, "gap"),
                                 ("fifty",(glo+ghi)/2, "swing"),
                                 ("fifty",(glo+ghi)/2, "gap")]
                    for emode,entry,smode in opts:
                        stop = (ext if smode=="swing" else (glo if side==1 else ghi)) - 2*TICK*side
                        risk=(entry-stop)*side
                        if risk < 8 or risk > 120: continue
                        if gap_t < 4: continue
                        for k in range(j+1, n):
                            if m[k] > 11*60+30: break
                            if (l[k] <= stop) if side==1 else (h[k] >= stop): break
                            if (l[k] <= entry) if side==1 else (h[k] >= entry):
                                sim=simulate(o,h,l,c,m,k,entry,stop,side)
                                if sim is None: break
                                res,px,bh,ei,mfe=sim
                                gross = 2.0 if res=="target" else (-1.0 if res=="stop" else (px-entry)*side/risk)
                                out.append(dict(fam="A",date=s["date"],side=side,level=nm,
                                    entry_t=m[k],sweep_t=m[i],fvg_t=m[j],wait=j-i,nb=k-j,
                                    rej=round(rej,2),disp=round(disp,2),gap_t=gap_t,
                                    gap_atr=(ghi-glo)/A[j],risk=round(risk,2),emode=emode,smode=smode,
                                    retr=round(((ghi-entry) if side==1 else (entry-glo))/(ghi-glo),2),
                                    sweep_depth=round(sweep_depth,1),atr=A[i],
                                    ext=ext,entry=entry,stop=stop,pdc=lv.get("pdc"),
                                    on_h=lv.get("on_h"),on_l=lv.get("on_l"),
                                    pm_h=lv.get("pm_h"),pm_l=lv.get("pm_l"),
                                    pdh=lv.get("pdh"),pdl=lv.get("pdl"),
                                    outcome=res,R=round(gross-COST_PTS/risk,4),gross=gross,mfe=mfe,bars=bh,
                                    **F))
                                break
                    break
    return out

rows=[]
for mw in (2,3,5,8,15):
    for s in SESS: rows += gen(s,mw)
pool=pd.DataFrame(rows); pool["year"]=pd.to_datetime(pool.date).dt.year
print("pool", len(pool)); pool.to_parquet("research/data/pool2.parquet")
