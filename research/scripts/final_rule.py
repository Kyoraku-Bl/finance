"""
MORNING IFVG RECLAIM  —  final rule, clean standalone implementation.

Data : CME MNQ (Micro E-mini Nasdaq-100) 1-minute candles, 2019-05 -> 2026-02,
       New-York local time, bars labelled with their OPEN time.
Rule : trade only between 09:30 and 10:15 New York.
       1. Find any 3-candle FVG on the 1-min chart (gap >= 4 ticks = 1.00 pt).
       2. Wait until a 1-min candle CLOSES through the far side of that gap
          -> the FVG is now "inverted" (IFVG).
       3. First pullback into the inverted gap  -> limit entry at the gap edge.
       4. Stop = 2 ticks beyond the gap's other edge.  Target = 2 x risk.
       5. Quality filters:
            Q1  2R target <= 8% of the average daily range of the last 5 sessions
            Q2  volume of the inversion candle <= 1.2 x the morning median volume
            Q3  inversion must happen within 10 candles of the gap
       6. One trade per day (the first qualifying one). Flat by 15:55 if neither
          target nor stop is hit.
Costs: 1.00 point round trip (spread + commission + slippage) charged to every trade.
"""
import numpy as np, pandas as pd, sys
sys.path.insert(0, "research/scripts")
from lib import load, atr, TICK, COST_PTS, simulate

WIN_OPEN  = 9*60+30    # 09:30
SETUP_END = 10*60+0    # 10:00  last moment a setup may trigger (entry must be before this)
GAP_MIN_T = 4          # ticks
Q1_TGT    = 0.08
Q2_VOL    = 1.2
Q3_LAG    = 10
MIN_RISK  = 4.0        # points (16 ticks) - execution sanity floor
MAX_RISK  = 120.0

def build(df):
    df = df.sort_values("ts").reset_index(drop=True)
    df["mod"] = df.ts.dt.hour*60 + df.ts.dt.minute
    # session date = date of the next 09:30 bar
    op = np.sort(df[df["mod"]==WIN_OPEN].ts.dt.normalize().drop_duplicates().to_numpy())
    ix = np.searchsorted(op, df.ts.to_numpy(), side="left")
    ok = ix < len(op)
    df = df[ok].copy(); df["sess"] = op[ix[ok]]
    sess = []
    for s, g in df.groupby("sess", sort=True):
        g = g[(g["mod"]>=WIN_OPEN) & (g["mod"]<=15*60+55)]
        if len(g) < 60: continue
        sess.append(dict(date=s, o=g.open.to_numpy(float), h=g.high.to_numpy(float),
                         l=g.low.to_numpy(float), c=g.close.to_numpy(float),
                         v=g.volume.to_numpy(float), mod=g["mod"].to_numpy(int),
                         ts=g.ts.to_numpy()))
    # average daily range of the previous 5 sessions (lookahead-free)
    rng = np.array([s["h"].max()-s["l"].min() if len(s["h"]) else np.nan for s in sess])
    for i, s in enumerate(sess):
        s["atr_day"] = np.nanmean(rng[max(0,i-5):i]) if i > 0 else np.nan
    return sess

def find(s, q1=True, q2=True, q3=True, both_sides=True, setup_end=SETUP_END):
    o,h,l,c,m,v = s["o"],s["h"],s["l"],s["c"],s["mod"],s["v"]
    n = len(h); medv = np.nanmedian(v[:20])
    gaps = []
    for j in range(2, n-2):
        if m[j] > setup_end: break
        if l[j] > h[j-2] + 1*TICK: gs, lo, hi = 1, h[j-2], l[j]      # bullish gap
        elif h[j] < l[j-2] - 1*TICK: gs, lo, hi = -1, h[j], l[j-2]    # bearish gap
        else: continue
        if (hi-lo)/TICK >= GAP_MIN_T: gaps.append((j, gs, lo, hi))
    for (j, gs, lo, hi) in gaps:                      # earliest gap first
        side = -gs                                    # inverted gap -> trade the other way
        if not both_sides and side != 1: continue
        inv = None
        for u in range(j+1, n):
            if m[u] > setup_end: break
            if side == -1 and c[u] < lo: inv = u; break
            if side ==  1 and c[u] > hi: inv = u; break
        if inv is None: continue
        if q3 and (inv - j) > Q3_LAG: continue
        entry = lo if side == -1 else hi
        stop  = (hi if side == -1 else lo) + 2*TICK*side
        risk  = (entry - stop) * side
        if risk < MIN_RISK or risk > MAX_RISK: continue
        if q1 and 2*risk / s["atr_day"] > Q1_TGT: continue
        if q2 and medv > 0 and v[inv] > Q2_VOL*medv: continue
        for k in range(inv+1, n):
            if m[k] > 11*60+30: break
            if (l[k] <= stop) if side == 1 else (h[k] >= stop): break
            if (l[k] <= entry) if side == 1 else (h[k] >= entry):
                return dict(date=s["date"], side=side, gap_i=j, inv_i=inv, entry_i=k,
                            entry=entry, stop=stop, risk=risk,
                            atr_day=s["atr_day"], gap_t=(hi-lo)/TICK,
                            inv_lag=inv-j, vol_ratio=v[inv]/medv if medv>0 else np.nan,
                            setup_t=m[inv], entry_t=m[k], gap_lo=lo, gap_hi=hi)
    return None

def backtest(sess, **kw):
    rows=[]
    for s in sess:
        if kw.get("require_atr", True) and not (s["atr_day"] == s["atr_day"]): continue
        t = find(s, **kw)
        if t is None: continue
        sim = simulate(s["o"],s["h"],s["l"],s["c"],s["mod"], t["entry_i"], t["entry"], t["stop"], t["side"])
        if sim is None: continue
        res, px, bh, ei, mfe = sim
        gross = 2.0 if res=="target" else (-1.0 if res=="stop" else (px-t["entry"])*t["side"]/t["risk"])
        rows.append({**t, "outcome":res, "exit":px, "bars":bh, "mfe":mfe,
                     "R":gross - COST_PTS/t["risk"], "gross_R":gross,
                     "exit_t":s["mod"][ei], "pnl_pts":(px-t["entry"])*t["side"],
                     "pnl_usd_1MNQ":(px-t["entry"])*t["side"]*2 - 1.24,   # $2/pt, ~$1.24 RT commission
                     "pnl_usd_1NQ":(px-t["entry"])*t["side"]*20 - 5.0})    # $20/pt, ~$5 RT commission
    tr = pd.DataFrame(rows)
    tr["dt"] = pd.to_datetime(tr.date)
    tr["year"], tr["month"], tr["dow"] = tr.dt.dt.year, tr.dt.dt.month, tr.dt.dt.day_of_week
    return tr

if __name__ == "__main__":
    df = load(); sess = build(df)
    print(f"sessions: {len(sess)}  {sess[0]['date'].date()} -> {sess[-1]['date'].date()}")
    variants = {
      "raw (no filters)":      dict(q1=False,q2=False,q3=False),
      "Q1 target-size only":   dict(q2=False,q3=False),
      "Q1+Q2":                 dict(q3=False),
      "Q1+Q3":                 dict(q2=False),
      "ALL (Q1+Q2+Q3)":        {},
      "ALL, long only":        dict(both_sides=False),
    }
    for name, kw in variants.items():
        tr = backtest(sess, **kw); tr.to_csv(f"research/out/trades_{name.split()[0].replace('(','')}.csv", index=False)
        w = 100*(tr.R>0).mean(); pf = tr.R[tr.R>0].sum()/abs(tr.R[tr.R<=0].sum())
        print(f"{name:22s} n={len(tr):4d} ({len(tr)/6.8:5.1f}/yr) win={w:5.1f}% exp={tr.R.mean():+.3f}R "
              f"PF={pf:4.2f} medrisk={tr.risk.median():5.1f}pt  pts/trade={tr.pnl_pts.mean():+5.2f}")
    tr = backtest(sess); tr.to_parquet("research/data/trades_final.parquet")
