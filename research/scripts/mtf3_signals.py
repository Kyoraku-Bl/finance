"""
IFVG pool for the "wide stop / 4-hour window" study.

Differences from mtf_signals.py:
  * entry window 09:45 - 12:00 New York (instead of 09:30-11:30)
  * stop distance is ALWAYS >= 10 index points (structural stop kept: 2 ticks
    beyond the far edge of the inverted gap, so only gaps >= ~10 pts qualify)
  * adds 1-HOUR candle confluences (the 1h candles are anchored at 09:30, so they
    are 09:30-10:29, 10:30-11:29, 11:30-12:29)
All features are candlestick shapes only - no volume, no ATR, no moving averages -
and strictly causal: at the entry bar k they use only candles completed at or
before k, plus the entry price itself.
"""
import numpy as np, pandas as pd, pickle, sys
sys.path.insert(0, "research/scripts")
from lib import TICK, COST_PTS, atr, load, DEADLINE
from mtf import tf_from_1m, candle_feats, completed_upto, developing
from mtf_signals import simulate_rrs, features_3m_15m

RRS = (2.0, 1.5, 1.0, 0.75, 2/3, 0.5)
ENTRY_START, SCAN_END = 9*60+45, 12*60
SETUP_END = 12*60
GAP_MIN_T, Q2_VOL, Q3_LAG = 4, 1.2, 10
MIN_STOP_PTS = 10.0
MAX_STOP_PTS = 120.0


def features_1h(s, k, side, entry):
    """Candle-only 1-hour confluences at 1-min bar k."""
    t60 = s["t60"]; f60 = s["f60"]
    f = {}
    b60 = completed_upto(t60, k)
    if b60 >= 1:
        prev_c = t60["c"][b60-1]
        f["c60_dir"] = int(f60["dn"][b60] == 1 if side == -1 else f60["up"][b60] == 1)
        f["c60_body"] = int(np.nan_to_num(f60["body_pct"][b60]) >= 0.5)
        f["c60_engulf"] = int((t60["o"][b60] >= prev_c and t60["c"][b60] <= t60["o"][b60-1]) if side == -1
                              else (t60["o"][b60] <= prev_c and t60["c"][b60] >= t60["o"][b60-1]))
        f["c60_struct"] = int((t60["h"][b60] < t60["h"][b60-1] and t60["l"][b60] < t60["l"][b60-1]) if side == -1
                              else (t60["h"][b60] > t60["h"][b60-1] and t60["l"][b60] > t60["l"][b60-1]))
        f["c60_close_beyond"] = int((t60["c"][b60] < t60["l"][b60-1]) if side == -1
                                    else (t60["c"][b60] > t60["h"][b60-1]))
        f["c60_clv"] = float(f60["clv"][b60]) if side == -1 else float(1 - f60["clv"][b60])
        # is the trade direction the same as the last completed 1h candle's body?
        f["c60_two_dir"] = int((f60["dn"][b60] == 1 and f60["dn"][b60-1] == 1) if side == -1
                               else (f60["up"][b60] == 1 and f60["up"][b60-1] == 1))
    d60 = developing(t60, k)
    if d60 >= 0:
        # CAUSAL: forming candle's range up to (not including) the entry bar + entry price
        j0 = t60["i0"][d60]
        seg_l = s["l"][j0:k] if k > j0 else np.array([])
        seg_h = s["h"][j0:k] if k > j0 else np.array([])
        lo_d = min(seg_l.min(), entry) if len(seg_l) else min(t60["o"][d60], entry)
        hi_d = max(seg_h.max(), entry) if len(seg_h) else max(t60["o"][d60], entry)
        mid = (lo_d + hi_d) / 2
        f["c60_premium"] = int((entry >= mid) if side == -1 else (entry <= mid))
        f["c60_dev_dir"] = int((entry < t60["o"][d60]) if side == -1 else (entry > t60["o"][d60]))
        f["c60_pos"] = float((entry - lo_d) / (hi_d - lo_d)) if hi_d > lo_d else 0.5
    names = ("c60_dir", "c60_body", "c60_engulf", "c60_struct", "c60_close_beyond",
             "c60_two_dir", "c60_premium", "c60_dev_dir")
    base = {n: 0 for n in names}
    base["c60_clv"] = np.nan
    base["c60_pos"] = np.nan
    base.update(f)
    return base


def features_extra(s, k, side, entry):
    """Session-structure candle facts: the 09:30 open, the first 15-min candle
    (the 'opening range', complete at 09:45), and the previous day's close.
    All of these are known before any trade in the 09:45-12:00 window."""
    f = {}
    op = s["o"][0]
    f["al_open"] = int((entry > op) if side == 1 else (entry < op))
    b15 = completed_upto(s["t15"], k)
    if b15 >= 0:
        t15 = s["t15"]
        f["or_dir"] = int((t15["c"][0] > t15["o"][0]) if side == 1 else (t15["c"][0] < t15["o"][0]))
        f["or_break"] = int((entry > t15["h"][0]) if side == 1 else (entry < t15["l"][0]))
        f["or_inside"] = int((t15["l"][0] <= entry <= t15["h"][0]))
    pdc = s.get("lv", {}).get("pdc")
    if pdc is not None and pdc == pdc:
        f["al_pdc"] = int((entry > pdc) if side == 1 else (entry < pdc))
    names = ("al_open", "or_dir", "or_break", "or_inside", "al_pdc")
    base = {n: 0 for n in names}
    base.update(f)
    return base


def session_signals(s):
    o, h, l, c, m, v = s["o"], s["h"], s["l"], s["c"], s["mod"], s["v"]
    n = len(h)
    medv = np.nanmedian(v[:20])
    gaps = []
    for j in range(2, n-2):
        if m[j] > SETUP_END: break
        if l[j] > h[j-2] + TICK: gaps.append((j, 1, h[j-2], l[j]))
        elif h[j] < l[j-2] - TICK: gaps.append((j, -1, h[j], l[j-2]))
    out = []
    for (j, gs, lo, hi) in gaps:
        if (hi - lo) / TICK < GAP_MIN_T: continue
        side = -gs
        inv = None
        for u in range(j+1, n):
            if m[u] > SCAN_END: break
            if side == -1 and c[u] < lo: inv = u; break
            if side == 1 and c[u] > hi: inv = u; break
        if inv is None or (inv - j) > Q3_LAG: continue
        entry = lo if side == -1 else hi
        stop = (hi if side == -1 else lo) + 2 * TICK * side
        risk = (entry - stop) * side
        if not (MIN_STOP_PTS <= risk <= MAX_STOP_PTS): continue     # <-- >= 10 points
        if medv > 0 and v[inv] > Q2_VOL * medv: continue
        for k in range(inv+1, n):
            if m[k] > SCAN_END: break
            if m[k] < ENTRY_START: continue                          # <-- entry window
            if (l[k] <= stop) if side == 1 else (h[k] >= stop): break
            if (l[k] <= entry) if side == 1 else (h[k] >= entry):
                sim = simulate_rrs(o, h, l, c, m, k, entry, stop, side, rrs=RRS)
                if sim is None: break
                out.append(dict(date=s["date"], side=side, gap_i=j, inv_i=inv, entry_i=k,
                                exit_t2=m[min(sim[("xbar", 2.0)], len(m)-1)],
                                gap_lo=lo, gap_hi=hi, gap_t=(hi-lo)/TICK, entry=entry, stop=stop,
                                risk=risk, inv_lag=inv-j,
                                vol_ratio=v[inv]/medv if medv > 0 else np.nan,
                                atr_day=s["atr_day"], setup_t=m[inv], entry_t=m[k],
                                **features_3m_15m(s, k, side, lo, hi, entry),
                                **features_1h(s, k, side, entry),
                                **features_extra(s, k, side, entry),
                                gap_dir=gs,
                                **{f"{k2[0]}{k2[1]:g}" if isinstance(k2, tuple) else k2: v2
                                   for k2, v2 in sim.items() if k2 != "risk"}))
                break
    return out


def build_pool(sess):
    import numpy as np
    for s in sess:
        a = atr(s["h"], s["l"], s["c"], 14)
        s["atr_day"] = float(np.nanmean(a))
        s["t3"] = tf_from_1m(s, 3); s["t15"] = tf_from_1m(s, 15); s["t60"] = tf_from_1m(s, 60)
        s["f3"] = candle_feats(s["t3"]["o"], s["t3"]["h"], s["t3"]["l"], s["t3"]["c"])
        s["f15"] = candle_feats(s["t15"]["o"], s["t15"]["h"], s["t15"]["l"], s["t15"]["c"])
        s["f60"] = candle_feats(s["t60"]["o"], s["t60"]["h"], s["t60"]["l"], s["t60"]["c"])
    rows = []
    for s in sess:
        rows += session_signals(s)
    P = pd.DataFrame(rows)
    P["dt"] = pd.to_datetime(P.date); P["year"] = P.dt.dt.year
    P["month"] = P.dt.dt.month; P["dow"] = P.dt.dt.day_of_week
    P["is_is"] = P.date <= "2022-12-31"
    return P


if __name__ == "__main__":
    sess = pickle.load(open("research/data/sessions.pkl", "rb"))
    P = build_pool(sess)
    P.to_parquet("research/data/pool_mtf3.parquet")
    print("signals:", len(P), "| days:", P.date.nunique(),
          "| per day:", round(len(P)/P.date.nunique(), 2))
    print("stop pts: min", P.risk.min(), "median", round(P.risk.median(), 2),
          "max", P.risk.max())
    print("\nper year:"); print(P.groupby("year").size().to_string())
    print("\nentry hour split:"); print(P.entry_t.map(lambda t: f"{t//60:02d}").value_counts().sort_index().to_string())
    print("\nraw win rate at each R:R (all signals, no confluences):")
    for r in RRS:
        w, R = P[f"w{r:g}"], P[f"R{r:g}"]
        print(f" 1:{r:<5.2f} n={len(P)} win={100*w.mean():5.1f}%  R/tr={R.mean():+.3f}  "
              f"PF={R[R>0].sum()/abs(R[R<=0].sum()):.2f}")
