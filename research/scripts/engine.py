"""Grid-search engine for sweep -> FVG patterns on MNQ 1-min bars."""
import numpy as np, pandas as pd, pickle, sys
sys.path.insert(0,"research/scripts"); from lib import *

SESS = pickle.load(open("research/data/sessions.pkl","rb"))
for s in SESS:
    s["atr"] = atr(s["h"], s["l"], s["c"], 14)
    s["medv"] = np.nanmedian(s["v"][:30]) if len(s["v"]) else np.nan

DEF = dict(level="all", cut=11*60+30, entry_cut=11*60+30, buf=2.0, max_wait=8, min_gap=4,
           entry="edge", stop="swing", min_r=6, max_r=100, disp=0.0, rej=0.0,
           side=None, volf=0.0, bias=False, rr=2.0, bos=False, first_only=True,
           gap_fresh=True, on_dir="any")

def _lv(lv, kind):
    L=[]; H=[]
    if kind in ("on","all") and lv.get("on_l") is not None:
        L.append(("on_l",lv["on_l"])); H.append(("on_h",lv["on_h"]))
    if kind in ("pm","all") and lv.get("pm_l") is not None:
        L.append(("pm_l",lv["pm_l"])); H.append(("pm_h",lv["pm_h"]))
    if kind in ("pd","all") and lv.get("pdl") is not None:
        L.append(("pdl",lv["pdl"])); H.append(("pdh",lv["pdh"]))
    return L,H

def detect(s, P):
    o,h,l,c,m,v,A = s["o"],s["h"],s["l"],s["c"],s["mod"],s["v"],s["atr"]; lv=s["lv"]
    n=len(h); buf=P["buf"]*TICK
    ci = int(np.searchsorted(m, P["cut"], side="right"))
    Ls,Hs = _lv(lv,P["level"])
    cands=[]
    # ---------------- LONG ----------------
    if P["side"] in (None,1,"long"):
        for lname,L in Ls:
            if L is None: continue
            for i in range(1, min(ci, n-3)):
                if A[i]!=A[i]: continue
                if not (l[i] < L and c[i] > L): continue
                if (c[i]-l[i]) < P["rej"]*(h[i]-l[i]): continue
                if P["volf"]>0 and v[i] < P["volf"]*s["medv"]: continue
                sl = l[i]
                for j in range(i+1, min(i+P["max_wait"], n-2)):
                    if l[j] <= sl - buf: break
                    if A[j]==A[j] and P["disp"]>0 and (c[j]-o[j]) < P["disp"]*A[j]: continue
                    if l[j] > h[j-2] + P["min_gap"]*TICK:
                        glo, ghi = h[j-2], l[j]
                        entry = ghi if P["entry"]=="edge" else (glo+ghi)/2
                        stop = (sl if P["stop"]=="swing" else glo) - buf
                        r = entry-stop
                        if r < P["min_r"]*TICK or r > P["max_r"]*TICK: break
                        if P["bias"] and lv.get("pdc") is not None and entry < lv["pdc"]: break
                        sw_hi = h[i:j+1].max() if j>i else h[j]
                        for k in range(j+1, n):
                            if m[k] > P["entry_cut"]: break
                            if l[k] <= stop: break
                            if P["bos"] and h[k] >= sw_hi: break
                            if l[k] <= entry:
                                cands.append(dict(side=1, entry_i=k, entry=entry, stop=stop,
                                                  level=lname, sweep_i=i, fvg_i=j, stop_bar=j+1))
                                break
                        break
    # ---------------- SHORT ----------------
    if P["side"] in (None,-1,"short"):
        for hname,H in Hs:
            if H is None: continue
            for i in range(1, min(ci, n-3)):
                if A[i]!=A[i]: continue
                if not (h[i] > H and c[i] < H): continue
                if (h[i]-c[i]) < P["rej"]*(h[i]-l[i]): continue
                if P["volf"]>0 and v[i] < P["volf"]*s["medv"]: continue
                sh = h[i]
                for j in range(i+1, min(i+P["max_wait"], n-2)):
                    if h[j] >= sh + buf: break
                    if A[j]==A[j] and P["disp"]>0 and (o[j]-c[j]) < P["disp"]*A[j]: continue
                    if h[j] < l[j-2] - P["min_gap"]*TICK:
                        ghi, glo = l[j-2], h[j]
                        entry = glo if P["entry"]=="edge" else (glo+ghi)/2
                        stop = (sh if P["stop"]=="swing" else ghi) + buf
                        r = stop-entry
                        if r < P["min_r"]*TICK or r > P["max_r"]*TICK: break
                        if P["bias"] and lv.get("pdc") is not None and entry > lv["pdc"]: break
                        sw_lo = l[i:j+1].min() if j>i else l[j]
                        for k in range(j+1, n):
                            if m[k] > P["entry_cut"]: break
                            if h[k] >= stop: break
                            if P["bos"] and l[k] <= sw_lo: break
                            if h[k] >= entry:
                                cands.append(dict(side=-1, entry_i=k, entry=entry, stop=stop,
                                                  level=hname, sweep_i=i, fvg_i=j, stop_bar=j+1))
                                break
                        break
    if not cands: return None
    return cands[0] if P["first_only"] else cands

def run(P, sess=None, min_bars_hold=0, collect=True):
    P = {**DEF, **P}; rows=[]
    sess = SESS if sess is None else sess
    for s in sess:
        t = detect(s,P)
        if t is None or isinstance(t,list): continue
        sim = simulate(s["o"],s["h"],s["l"],s["c"],s["mod"], t["entry_i"],t["entry"],t["stop"],
                       t["side"], deadline=DEADLINE)
        if sim is None: continue
        out,px,bh,ei,mfe = sim
        gross = 2.0 if out=="target" else (-1.0 if out=="stop" else (px-t["entry"])*t["side"]/((t["entry"]-t["stop"])*t["side"]))
        risk = (t["entry"]-t["stop"])*t["side"]
        rows.append(dict(date=s["date"], **{k:t[k] for k in ("side","entry","stop","level","sweep_i","fvg_i","entry_i")},
                         outcome=out, bars=bh, mfe=mfe, risk_pts=risk,
                         R=gross - COST_PTS/risk, gross=gross,
                         sweep_t=s["mod"][t["sweep_i"]], entry_t=s["mod"][t["entry_i"]]))
    return pd.DataFrame(rows)

def stats(tr,label=""):
    if len(tr)==0: return dict(label=label,n=0)
    w=tr.R>0; gp=tr.R[w].sum(); gl=abs(tr.R[~w].sum())
    return dict(label=label,n=len(tr),win=round(100*w.mean(),1),R=round(tr.R.sum(),1),
                exp=round(tr.R.mean(),3),pf=round(gp/gl,2) if gl else np.inf,
                medrisk=round(tr.risk_pts.median(),1),
                tp=round(100*(tr.outcome=="target").mean(),1),
                sl=round(100*(tr.outcome=="stop").mean(),1),
                to=round(100*(tr.outcome=="time").mean(),1),
                period=f"{tr.date.min()}..{tr.date.max()}", trades_y=round(len(tr)/max(1,pd.to_datetime(tr.date).dt.year.nunique()),0))
