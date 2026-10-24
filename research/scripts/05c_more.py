"""A2 = repeated level sweeps (2nd+ attempt) ; D = IFVG (inverted FVG)."""
import numpy as np, pandas as pd, pickle, sys
sys.path.insert(0,"research/scripts"); from lib import *
SESS=pickle.load(open("research/data/sessions.pkl","rb"))
for s in SESS:
    s["atr"]=atr(s["h"],s["l"],s["c"],14)
    s["ema20"]=pd.Series(s["c"]).ewm(span=20,adjust=False).mean().to_numpy()
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

def gen_a2(s,max_wait=8):
    o,h,l,c,m,v,A=s["o"],s["h"],s["l"],s["c"],s["mod"],s["v"],s["atr"]; lv=s["lv"]; n=len(h); out=[]
    for lname,hname in LVK:
        for side,(L,nm) in ((1,(lv.get(lname),lname)),(-1,(lv.get(hname),hname))):
            if L is None or L!=L: continue
            cnt=0; used=[]
            for i in range(1,n-3):
                if m[i]>11*60+20: break
                if A[i]!=A[i] or A[i]<=0: continue
                rng=h[i]-l[i]
                if side==1:
                    if not (l[i]<L and c[i]>L): continue
                    ext,rej=l[i],(c[i]-l[i])/rng if rng>0 else 0
                else:
                    if not (h[i]>L and c[i]<L): continue
                    ext,rej=h[i],(h[i]-c[i])/rng if rng>0 else 0
                prior=cnt; cnt+=1
                if prior>=3: break
                for j in range(i+1,min(i+max_wait,n-2)):
                    if side==1 and l[j]<=ext-1*TICK: break
                    if side==-1 and h[j]>=ext+1*TICK: break
                    if side==1 and l[j]>h[j-2]+1*TICK: glo,ghi=h[j-2],l[j]
                    elif side==-1 and h[j]<l[j-2]-1*TICK: ghi,glo=l[j-2],h[j]
                    else: continue
                    for emode,entry in (("edge",ghi if side==1 else glo),("fifty",(glo+ghi)/2)):
                        for smode in ("gap","swing"):
                            stop=(ext if smode=="swing" else (glo if side==1 else ghi))-2*TICK*side
                            risk=(entry-stop)*side
                            if not (8<=risk<=120) or (ghi-glo)/TICK<4: continue
                            for k in range(j+1,n):
                                if m[k]>11*60+30: break
                                if (l[k]<=stop) if side==1 else (h[k]>=stop): break
                                if (l[k]<=entry) if side==1 else (h[k]>=entry):
                                    t=fin(s,k,entry,stop,side,dict(fam="A2",level=nm,sweep_t=m[i],wait=j-i,
                                        nb=k-j,rej=round(rej,2),disp=round(abs(c[j]-o[j])/A[j],2),
                                        gap_t=(ghi-glo)/TICK,emode=emode,smode=smode,sweep_depth=round((L-ext)*side/TICK,1),
                                        prior_sweeps=prior,atr=A[i],pdc=lv.get("pdc"),
                                        on_h=lv.get("on_h"),on_l=lv.get("on_l"),pm_h=lv.get("pm_h"),pm_l=lv.get("pm_l"),
                                        pdh=lv.get("pdh"),pdl=lv.get("pdl"),ema_up=int(c[i]>s["ema20"][i]),first_touch=int(prior==0)))
                                    if t: out.append(t)
                                    break
                    break
    return out

def gen_d(s):
    """IFVG: a FVG that gets closed through, then retested from the other side."""
    o,h,l,c,m,v,A=s["o"],s["h"],s["l"],s["c"],s["mod"],s["v"],s["atr"]; n=len(h); out=[]
    gaps=[]
    for j in range(2,n-2):
        if m[j]>11*60+15: break
        if A[j]!=A[j] or A[j]<=0: continue
        if l[j]>h[j-2]+1*TICK: gaps.append((j,1,h[j-2],l[j]))
        elif h[j]<l[j-2]-1*TICK: gaps.append((j,-1,h[j],l[j-2]))
    for (j,gs,lo,hi) in gaps:
        if (hi-lo)/TICK<4: continue
        side=-gs   # bullish gap inverted -> short
        inv=None
        for u in range(j+1,n):
            if m[u]>11*60+20: break
            if side==-1 and c[u]<lo: inv=u; break
            if side==1 and c[u]>hi: inv=u; break
        if inv is None: continue
        entry=(lo if side==-1 else hi)
        entry2=(lo+hi)/2
        for emode,en in (("edge",entry),("fifty",entry2)):
            stop=(hi if side==-1 else lo)+2*TICK*side
            risk=(en-stop)*side
            if not (8<=risk<=120): continue
            for k in range(inv+1,n):
                if m[k]>11*60+40: break
                if (l[k]<=stop) if side==1 else (h[k]>=stop): break
                if (l[k]<=en) if side==1 else (h[k]>=en):
                    t=fin(s,k,en,stop,side,dict(fam="D",level="none",sweep_t=m[j],wait=inv-j,nb=k-inv,
                        rej=np.nan,disp=round(abs(c[j]-o[j])/A[j],2),gap_t=(hi-lo)/TICK,emode=emode,
                        smode="gap",sweep_depth=0,prior_sweeps=0,atr=A[j],pdc=s["lv"].get("pdc"),
                        on_h=s["lv"].get("on_h"),on_l=s["lv"].get("on_l"),pm_h=s["lv"].get("pm_h"),
                        pm_l=s["lv"].get("pm_l"),pdh=s["lv"].get("pdh"),pdl=s["lv"].get("pdl"),
                        ema_up=int(c[inv]>s["ema20"][inv]),first_touch=1))
                    if t: out.append(t)
                    break
    return out

rows=[]
for s in SESS:
    rows+=gen_a2(s); rows+=gen_d(s)
pool=pd.DataFrame(rows); pool["year"]=pd.to_datetime(pool.date).dt.year
print("pool4",len(pool), pool.fam.value_counts().to_dict())
pool.to_parquet("research/data/pool4.parquet")
