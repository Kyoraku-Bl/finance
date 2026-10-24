"""Pattern family A: liquidity sweep of a pre-known level -> displacement FVG -> retest."""
import numpy as np, pandas as pd, itertools, sys
sys.path.insert(0, "research/scripts")
from lib import *

df = load()
SESS = sessions(df)
# precompute reference levels once
REF = {}
for date, s in SESS:
    r = premarket_levels(df, date)
    p = prev_day_rth(df, date)
    if p: r.update(pdh=p["pdh"], pdl=p["pdl"], pdc=p["pdc"])
    REF[date] = r
print("sessions", len(SESS))

def levels_for(r, kind):
    if kind == "on":  return [("on_l", r.get("on_l"))], [("on_h", r.get("on_h"))]
    if kind == "pm":  return [("pm_l", r.get("pm_l"))], [("pm_h", r.get("pm_h"))]
    if kind == "pd":  return [("pdl", r.get("pdl"))], [("pdh", r.get("pdh"))]
    if kind == "all":
        lows  = [("on_l", r.get("on_l")), ("pm_l", r.get("pm_l")), ("pdl", r.get("pdl"))]
        highs = [("on_h", r.get("on_h")), ("pm_h", r.get("pm_h")), ("pdh", r.get("pdh"))]
        return [x for x in lows if x[1] is not None], [x for x in highs if x[1] is not None]
    raise ValueError(kind)

def find_trade(date, s, p):
    o,h,l,c,mod = s["o"],s["h"],s["l"],s["c"],s["mod"]
    A = atr(h,l,c,14)
    buf = p["buf"]*TICK
    lows, highs = levels_for(REF[date], p["level"])
    n = len(h)
    # restrict to 09:30 -> p["cut"]
    ci = np.searchsorted(mod, p["cut"], side="right")
    best = None
    # ---------- long: sweep a low, bullish FVG ----------
    for lname, L in lows:
        if L is None: continue
        for i in range(1, min(ci, n-3)):
            # bar i takes out the level and closes back above it (stop run)
            if not (l[i] < L - buf*0.0 and c[i] > L): continue
            if A[i] != A[i] or (h[i]-l[i]) < p["min_range"]*A[i]: continue
            sl = l[i]
            # bullish FVG formed within the next max_bars bars
            for j in range(i+1, min(i+p["max_wait"], n-2)):
                if l[j] <= sl - buf:      # sweep low violated -> invalid
                    break
                if l[j] > h[j-2] + p["min_gap"]*TICK:
                    gap_lo, gap_hi = h[j-2], l[j]
                    entry = gap_hi if p["entry"] == "edge" else (gap_lo+gap_hi)/2
                    stop = (sl if p["stop"] == "swing" else gap_lo) - buf
                    if entry - stop < p["min_r"]*TICK or entry - stop > p["max_r"]*TICK:
                        break
                    # need price to actually come back to the entry level, entry at bar > j
                    for k in range(j+1, n):
                        if mod[k] > WIN_END: break
                        if l[k] <= stop: break                    # invalidated before entry
                        if l[k] <= entry:
                            best = dict(date=date, side=1, entry_i=k, entry=entry, stop=stop,
                                        level=lname, setup_min=mod[j], sweep_min=mod[i])
                            break
                    break
            if best: break
        if best: break
    # ---------- short: sweep a high, bearish FVG ----------
    if best is None:
        for hname, H in highs:
            if H is None: continue
            for i in range(1, min(ci, n-3)):
                if not (h[i] > H and c[i] < H): continue
                if A[i] != A[i] or (h[i]-l[i]) < p["min_range"]*A[i]: continue
                sh = h[i]
                for j in range(i+1, min(i+p["max_wait"], n-2)):
                    if h[j] >= sh + buf: break
                    if h[j] < l[j-2] - p["min_gap"]*TICK:
                        gap_hi, gap_lo = l[j-2], h[j]
                        entry = gap_lo if p["entry"] == "edge" else (gap_lo+gap_hi)/2
                        stop = (sh if p["stop"] == "swing" else gap_hi) + buf
                        if entry_stop := stop - entry: pass
                        if stop - entry < p["min_r"]*TICK or stop - entry > p["max_r"]*TICK: break
                        for k in range(j+1, n):
                            if mod[k] > WIN_END: break
                            if h[k] >= stop: break
                            if h[k] >= entry:
                                best = dict(date=date, side=-1, entry_i=k, entry=entry, stop=stop,
                                            level=hname, setup_min=mod[j], sweep_min=mod[i])
                                break
                        break
                if best: break
            if best: break
    return best

def run(p, sess=SESS, verbose=False):
    rows=[]
    for date,s in sess:
        if date not in REF: continue
        t=find_trade(date,s,p)
        if not t: continue
        o,h,l,c,mod=s["o"],s["h"],s["l"],s["c"],s["mod"]
        sim=simulate(o,h,l,c,mod,t["entry_i"],t["entry"],t["stop"],t["side"])
        if sim is None: continue
        out,px,bh,ei,mfe=sim
        rows.append({**t, "outcome":out,"exit":px,"bars":bh,"mfe":mfe,
                     "R":trade_R(out,px,t["entry"],t["stop"],t["side"]),
                     "risk_pts": (t["entry"]-t["stop"])*t["side"]})
    return pd.DataFrame(rows)

def stats(tr, label=""):
    if len(tr)==0: return dict(label=label,n=0)
    w=(tr.R>0).mean(); pf = tr.R[tr.R>0].sum()/abs(tr.R[tr.R<=0].sum()) if (tr.R<=0).any() else np.inf
    pf = tr.R[tr.R>0].sum()/abs(tr.R[tr.R<=0].sum()) if (tr.R<=0).any() else np.inf
    return dict(label=label, n=len(tr), win=round(100*w,1), R=round(tr.R.sum(),1),
                exp=round(tr.R.mean(),3), pf=round(pf,2), risk=round(tr.risk_pts.median(),1),
                tp=round(100*(tr.outcome=="target").mean(),1), sl=round(100*(tr.outcome=="stop").mean(),1))
