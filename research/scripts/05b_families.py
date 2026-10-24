"""Other pattern families: B = sweep+momentum entry, C = FVG-only, E = opening-drive pullback,
   D = inverted FVG (IFVG). Same 2R / conservative intra-bar rules."""
import numpy as np, pandas as pd, pickle, sys
sys.path.insert(0,"research/scripts"); from lib import *

SESS = pickle.load(open("research/data/sessions.pkl","rb"))
for s in SESS:
    s["atr"]=atr(s["h"],s["l"],s["c"],14)
    s["ema20"]=pd.Series(s["c"]).ewm(span=20,adjust=False).mean().to_numpy()
LVK=[("on_l","on_h"),("pm_l","pm_h"),("pdl","pdh")]

def finish(s,k,entry,stop,side,extra):
    o,h,l,c,m=s["o"],s["h"],s["l"],s["c"],s["mod"]
    risk=(entry-stop)*side
    if risk<=0: return None
    sim=simulate(o,h,l,c,m,k,entry,stop,side)
    if sim is None: return None
    res,px,bh,ei,mfe=sim
    gross=2.0 if res=="target" else (-1.0 if res=="stop" else (px-entry)*side/risk)
    return dict(date=s["date"],side=side,entry_t=m[k],risk=round(risk,2),entry=entry,stop=stop,
                outcome=res,R=round(gross-COST_PTS/risk,4),gross=gross,mfe=mfe,bars=bh,**extra)

def gen(s, drive_end=30):
    o,h,l,c,m,v,A=s["o"],s["h"],s["l"],s["c"],s["mod"],s["v"],s["atr"]; lv=s["lv"]; n=len(h)
    out=[]
    # ---------- family B: sweep + momentum entry (next bar open) ----------
    for lname,hname in LVK:
        for side,(L,nm) in ((1,(lv.get(lname),lname)),(-1,(lv.get(hname),hname))):
            if L is None or L!=L: continue
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
                k=i+1; entry=o[k]; stop=ext-2*TICK*side
                risk=(entry-stop)*side
                if not (8<=risk<=120): continue
                if (l[k]<=stop) if side==1 else (h[k]>=stop): continue
                t=finish(s,k,entry,stop,side,dict(fam="B",level=nm,sweep_t=m[i],wait=0,nb=0,
                    rej=round(rej,2),sweep_depth=round((L-ext)*side/TICK,1),atr=A[i],disp=0,gap_t=0,
                    emode="mkt",smode="swing",pdc=lv.get("pdc"),on_h=lv.get("on_h"),on_l=lv.get("on_l"),
                    pm_h=lv.get("pm_h"),pm_l=lv.get("pm_l"),pdh=lv.get("pdh"),pdl=lv.get("pdl"),
                    ema_up=int(c[i]>s["ema20"][i]),first_touch=int(np.all(l[:i]>L-1*TICK) if side==1 else np.all(h[:i]<L+1*TICK))))
                if t: out.append(t)
                break
    # ---------- families C (fvg only) and E (opening-drive pullback) ----------
    de = np.searchsorted(m, 570+drive_end, side="right")
    drive = 0
    if len(c)>de: drive = int(c[de-1] > o[0]) - int(c[de-1] < o[0])
    for side in (1,-1):
        for j in range(2,n-2):
            if m[j]>11*60+20: break
            if A[j]!=A[j] or A[j]<=0: continue
            if side==1 and l[j]>h[j-2]+1*TICK:   glo,ghi=h[j-2],l[j]
            elif side==-1 and h[j]<l[j-2]-1*TICK: ghi,glo=l[j-2],h[j]
            else: continue
            gap_t=(ghi-glo)/TICK
            if gap_t<4: continue
            disp=abs(c[j]-o[j])/A[j]
            for emode,entry in (("edge",ghi if side==1 else glo),("fifty",(glo+ghi)/2)):
                stop=(glo if side==1 else ghi)-2*TICK*side
                risk=(entry-stop)*side
                if not (8<=risk<=120): continue
                for k in range(j+1,n):
                    if m[k]>11*60+30: break
                    if (l[k]<=stop) if side==1 else (h[k]>=stop): break
                    if (l[k]<=entry) if side==1 else (h[k]>=entry):
                        base=dict(level="none",sweep_t=m[j],wait=0,nb=k-j,rej=np.nan,disp=round(disp,2),
                                  gap_t=gap_t,emode=emode,smode="gap",sweep_depth=0,atr=A[j],
                                  pdc=lv.get("pdc"),on_h=lv.get("on_h"),on_l=lv.get("on_l"),
                                  pm_h=lv.get("pm_h"),pm_l=lv.get("pm_l"),pdh=lv.get("pdh"),pdl=lv.get("pdl"),
                                  ema_up=int(c[j]>s["ema20"][j]),first_touch=1)
                        t=finish(s,k,entry,stop,side,{**base,"fam":"C"})
                        if t: out.append(t)
                        if m[j]>570+drive_end and drive!=0 and side==drive:
                            t=finish(s,k,entry,stop,side,{**base,"fam":"E"})
                            if t: out.append(t)
                        break
            # only first FVG of each side is kept to keep pool tidy
            break
    return out

rows=[]
for s in SESS:
    for de in (15,30,60):
        for r in gen(s,de):
            r["drive_end"]=de; rows.append(r)
pool=pd.DataFrame(rows)
print("pool3", len(pool)); print(pool.fam.value_counts().to_dict())
pool.to_parquet("research/data/pool3.parquet")
