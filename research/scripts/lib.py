"""Shared helpers: data loading, pattern primitives, trade simulation."""
import numpy as np, pandas as pd

TICK = 0.25          # MNQ / NQ tick size (points)
COST_PTS = 1.0       # round-trip cost: 1 tick spread + 3 ticks commission/slippage
WIN_START = 9*60+30  # 09:30 ET
WIN_END   = 11*60+30 # 11:30 ET
DEADLINE  = 15*60+55 # flat by 15:55 ET if neither target nor stop hit

def load(path="research/data/mnq_1m.parquet"):
    df = pd.read_parquet(path)
    df = df.sort_values("ts").reset_index(drop=True)
    df["mod"] = df.ts.dt.hour*60 + df.ts.dt.minute
    return df

def sessions(df):
    """list of (date, dict of arrays) for bars 09:30 -> 15:59 of each session"""
    d = df[(df["mod"] >= WIN_START) & (df["mod"] <= DEADLINE)]
    out = []
    for date, g in d.groupby("date", sort=True):
        if len(g) < 60:
            continue
        out.append((date, dict(o=g.open.to_numpy(float), h=g.high.to_numpy(float),
                               l=g.low.to_numpy(float), c=g.close.to_numpy(float),
                               v=g.volume.to_numpy(float), mod=g["mod"].to_numpy(int),
                               ts=g.ts.to_numpy())))
    return out

def premarket_levels(df, date):
    """levels strictly before 09:30 on `date` (uses only past/known data)"""
    day = df[(df.date == date)]
    pre = day[day["mod"] < WIN_START]
    on  = day[(day["mod"] >= 18*60) | (day["mod"] < WIN_START)]  # 18:00 prev -> 09:29
    r = {}
    if len(on):  r["on_h"], r["on_l"] = on.high.max(), on.low.min()
    pm = pre[pre["mod"] >= 8*60]
    if len(pm):  r["pm_h"], r["pm_l"] = pm.high.max(), pm.low.min()
    if len(pre): r["pre_h"], r["pre_l"] = pre.high.max(), pre.low.min()
    return r

def prev_day_rth(df, date):
    prev = df[df.date < date]
    if prev.empty: return None
    pdte = prev.date.max()
    g = prev[(prev.date == pdte) & (prev["mod"] < 16*60+1) & (prev["mod"] >= WIN_START)]
    if len(g) < 30: return None
    return dict(pdh=g.high.max(), pdl=g.low.min(), pdc=g.close.iloc[-1])

def atr(h, l, c, n=14):
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    a = pd.Series(tr).rolling(n, min_periods=3).mean().to_numpy()
    return np.concatenate([[np.nan], a])

def fvgs(o, h, l, c, min_gap, i0=0, i1=None):
    """all 3-bar fair value gaps; returns list of (idx_of_3rd_bar, side, lo, hi)"""
    i1 = len(h) if i1 is None else i1
    out = []
    for i in range(max(i0, 2), i1):
        if l[i] > h[i-2] + min_gap:      # bullish gap
            out.append((i, 1, h[i-2], l[i]))
        if h[i] < l[i-2] - min_gap:      # bearish gap
            out.append((i, -1, h[i], l[i-2]))
    return out

def simulate(o, h, l, c, mod, entry_i, entry, stop, side, deadline=DEADLINE,
             entry_mode="limit"):
    """Walk forward from bar entry_i. Returns (outcome, exit_price, bars_held, exit_i, mfe_r)"""
    risk = (entry - stop) * side
    if risk <= 0: return None
    target = entry + 2*risk*side
    # entry fill
    if entry_mode == "limit":
        if side == 1 and l[entry_i] > entry: return None
        if side == -1 and h[entry_i] < entry: return None
    mfe = 0.0
    for j in range(entry_i, len(h)):
        if mod[j] > deadline: break
        # NOTE: on the entry bar only the adverse extreme counts (worst-case intra-bar
        # path). No same-bar target credit -> no look-ahead inside a 1-min candle.
        if side == 1:
            mfe = max(mfe, (h[j]-entry)/risk)
            if l[j] <= stop:   return ("stop", stop, j-entry_i, j, mfe)
            if j > entry_i and h[j] >= target: return ("target", target, j-entry_i, j, mfe)
        else:
            mfe = max(mfe, (entry-l[j])/risk)
            if h[j] >= stop:   return ("stop", stop, j-entry_i, j, mfe)
            if j > entry_i and l[j] <= target: return ("target", target, j-entry_i, j, mfe)
    j = min(len(h)-1, np.searchsorted(mod, deadline, side="right")-1)
    return ("time", c[j], j-entry_i, j, mfe)

def trade_R(outcome, exit_price, entry, stop, side):
    risk = (entry-stop)*side
    if outcome == "target": gross = 2.0
    elif outcome == "stop": gross = -1.0
    else: gross = (exit_price-entry)*side/risk
    return gross - COST_PTS/risk
