"""
All IFVG setups per session, with 3-minute and 15-minute candle-only confluences,
and outcomes at several R:R targets (one simulation pass per trade).
Strictly causal: every confluence at entry bar k uses only 1/3/15-min candles that
are complete at the close of bar k.
"""
import numpy as np, pandas as pd, pickle, sys
sys.path.insert(0,"research/scripts")
from lib import TICK, COST_PTS, atr, DEADLINE
from mtf import tf_from_1m, candle_feats, completed_upto, developing

RRS = (2.0, 1.5, 1.0, 0.75, 2/3, 0.5)
WIN_OPEN, SETUP_END, SCAN_END = 9*60+30, 10*60+0, 11*60+30
GAP_MIN_T, Q2_VOL, Q3_LAG = 4, 1.2, 10

def simulate_rrs(o,h,l,c,mod, k, entry, stop, side, rrs=RRS, deadline=DEADLINE):
    risk = (entry-stop)*side
    if risk <= 0: return None
    tgts = {r: entry + r*risk*side for r in rrs}
    stop_bar = None; time_bar = None
    for j in range(k, len(h)):
        if mod[j] > deadline: time_bar = min(j, len(h)-1); break
        adverse = (l[j] <= stop) if side == 1 else (h[j] >= stop)
        if adverse: stop_bar = j; break
    out = dict(stop_bar=stop_bar)
    for r in rrs:
        tb = None
        for j in range(k+1, len(h)):          # never credit the entry bar
            if mod[j] > deadline: break
            if stop_bar is not None and j >= stop_bar: break
            if (h[j] >= tgts[r]) if side == 1 else (l[j] <= tgts[r]):
                tb = j; break
        out[("tbar", r)] = tb
    # resolve
    last = len(h)-1
    for r in rrs:
        tb = out[("tbar", r)]
        if tb is not None and (stop_bar is None or tb < stop_bar):
            out[("R", r)] = r - COST_PTS/risk; out[("w", r)] = 1; out[("xbar", r)] = tb
        elif stop_bar is not None:
            out[("R", r)] = -1.0 - COST_PTS/risk; out[("w", r)] = 0; out[("xbar", r)] = stop_bar
        else:
            j = time_bar if time_bar is not None else last
            out[("R", r)] = (c[j]-entry)*side/risk - COST_PTS/risk
            out[("w", r)] = int(c[j] > entry) if side == 1 else int(c[j] < entry)
            out[("xbar", r)] = j
    out["risk"] = risk
    return out

def features_3m_15m(s, k, side, gap_lo, gap_hi, entry):
    t3, t15 = s["t3"], s["t15"]
    f = {}
    a3 = completed_upto(t3, k)
    if a3 >= 1:
        f3 = s["f3"]
        prev_c = t3["c"][a3-1]
        f["c3_close_ok"] = int((t3["c"][a3] < gap_lo) if side == -1 else (t3["c"][a3] > gap_hi))
        f["c3_engulf"] = int((t3["o"][a3] >= prev_c and t3["c"][a3] <= t3["o"][a3-1]) if side == -1
                             else (t3["o"][a3] <= prev_c and t3["c"][a3] >= t3["o"][a3-1]))
        f["c3_dir"] = int(f3["dn"][a3] == 1 if side == -1 else f3["up"][a3] == 1)
        f["c3_reject"] = int((f3["up_wick"][a3] >= 0.5) if side == -1 else (f3["dn_wick"][a3] >= 0.5))
        f["c3_body"] = int(np.nan_to_num(f3["body_pct"][a3]) >= 0.5)
        f["c3_struct"] = int((t3["h"][a3] < t3["h"][a3-1] and t3["l"][a3] < t3["l"][a3-1]) if side == -1
                             else (t3["h"][a3] > t3["h"][a3-1] and t3["l"][a3] > t3["l"][a3-1]))
        f["c3_inside"] = int(t3["h"][a3] <= t3["h"][a3-1] and t3["l"][a3] >= t3["l"][a3-1])
        f["c3_clv"] = float(f3["clv"][a3]) if side == -1 else float(1-f3["clv"][a3])
    b15 = completed_upto(t15, k); d15 = developing(t15, k)
    if b15 >= 1:
        f15 = s["f15"]
        prev_c = t15["c"][b15-1]
        f["c15_prev_dir"] = int(f15["dn"][b15] == 1 if side == -1 else f15["up"][b15] == 1)
        f["c15_engulf"] = int((t15["o"][b15] >= prev_c and t15["c"][b15] <= t15["o"][b15-1]) if side == -1
                              else (t15["o"][b15] <= prev_c and t15["c"][b15] >= t15["o"][b15-1]))
        f["c15_body"] = int(np.nan_to_num(f15["body_pct"][b15]) >= 0.5 and
                            ((t15["c"][b15] < t15["o"][b15]) if side == -1 else (t15["c"][b15] > t15["o"][b15])))
        f["c15_wick"] = int((f15["up_wick"][b15] >= 0.4) if side == -1 else (f15["dn_wick"][b15] >= 0.4))
        f["c15_close_beyond"] = int((t15["c"][b15] < t15["l"][b15-1]) if side == -1
                                    else (t15["c"][b15] > t15["h"][b15-1]))
        f["c15_prev_clv"] = int((f15["clv"][b15] <= 0.4) if side == -1 else (f15["clv"][b15] >= 0.6))
        f["c15_two_dir"] = int((f15["dn"][b15] == 1 and f15["dn"][b15-1] == 1) if side == -1
                               else (f15["up"][b15] == 1 and f15["up"][b15-1] == 1))
    if d15 >= 0:
        # CAUSAL: only bars strictly BEFORE the entry bar, plus the entry price itself,
        # because a limit fill happens inside bar k and bar k's close is not known yet.
        j0 = t15["i0"][d15]
        seg_l = s["l"][j0:k] if k > j0 else np.array([])
        seg_h = s["h"][j0:k] if k > j0 else np.array([])
        lo_d = min(seg_l.min(), entry) if len(seg_l) else min(t15["o"][d15], entry)
        hi_d = max(seg_h.max(), entry) if len(seg_h) else max(t15["o"][d15], entry)
        mid = (lo_d+hi_d)/2
        f["c15_premium"] = int((entry >= mid) if side == -1 else (entry <= mid))
        # direction of the 15-min candle AT THE MOMENT OF THE FILL
        f["c15_dev_dir"] = int((entry < t15["o"][d15]) if side == -1 else (entry > t15["o"][d15]))
        if b15 >= 1:
            f["c15_sweep"] = int((hi_d > t15["h"][b15]) if side == -1 else (lo_d < t15["l"][b15]))
    return {**{k2: 0 for k2 in ("c3_close_ok","c3_engulf","c3_dir","c3_reject","c3_body","c3_struct",
                                "c3_inside","c15_prev_dir","c15_engulf","c15_body","c15_wick",
                                "c15_close_beyond","c15_premium","c15_dev_dir","c15_sweep","c15_prev_clv","c15_two_dir")}, **f,
            "c3_clv": f.get("c3_clv", np.nan)}

def session_signals(s, setups_end=SETUP_END):
    o,h,l,c,m,v = s["o"],s["h"],s["l"],s["c"],s["mod"],s["v"]
    n = len(h); medv = np.nanmedian(v[:20])
    if not (s.get("atr_day") == s.get("atr_day")): return []
    gaps = []
    for j in range(2, n-2):
        if m[j] > setups_end: break
        if l[j] > h[j-2] + 1*TICK: gaps.append((j, 1, h[j-2], l[j]))
        elif h[j] < l[j-2] - 1*TICK: gaps.append((j, -1, h[j], l[j-2]))
    out = []
    for (j, gs, lo, hi) in gaps:
        if (hi-lo)/TICK < GAP_MIN_T: continue
        side = -gs
        inv = None
        for u in range(j+1, n):
            if m[u] > setups_end: break
            if side == -1 and c[u] < lo: inv = u; break
            if side == 1 and c[u] > hi: inv = u; break
        if inv is None or (inv-j) > Q3_LAG: continue
        entry = lo if side == -1 else hi
        stop  = (hi if side == -1 else lo) + 2*TICK*side
        risk  = (entry-stop)*side
        if not (4.0 <= risk <= 120.0): continue
        if medv > 0 and v[inv] > Q2_VOL*medv: continue
        for k in range(inv+1, n):
            if m[k] > SCAN_END: break
            if (l[k] <= stop) if side == 1 else (h[k] >= stop): break
            if (l[k] <= entry) if side == 1 else (h[k] >= entry):
                sim = simulate_rrs(o,h,l,c,m,k,entry,stop,side)
                if sim is None: break
                out.append(dict(date=s["date"], side=side, gap_i=j, inv_i=inv, entry_i=k, exit_t2=m[min(sim[("xbar",2.0)],len(m)-1)],
                                gap_lo=lo, gap_hi=hi, gap_t=(hi-lo)/TICK, entry=entry, stop=stop,
                                risk=risk, inv_lag=inv-j, vol_ratio=v[inv]/medv if medv>0 else np.nan,
                                atr_day=s["atr_day"], setup_t=m[inv], entry_t=m[k],
                                **features_3m_15m(s,k,side,lo,hi,entry),
                                **{f"{k2[0]}{k2[1]:g}" if isinstance(k2,tuple) else k2: v2
                                   for k2,v2 in sim.items() if k2!="risk"}))
                break
    return out

def build_pool(sess):
    for s in sess:
        s["atr"] = atr(s["h"],s["l"],s["c"],14)
        s["t3"] = tf_from_1m(s,3); s["t15"] = tf_from_1m(s,15)
        s["f3"] = candle_feats(s["t3"]["o"],s["t3"]["h"],s["t3"]["l"],s["t3"]["c"])
        s["f15"] = candle_feats(s["t15"]["o"],s["t15"]["h"],s["t15"]["l"],s["t15"]["c"])
    rows=[]
    for s in sess: rows += session_signals(s)
    P = pd.DataFrame(rows)
    P["dt"] = pd.to_datetime(P.date); P["year"] = P.dt.dt.year; P["month"] = P.dt.dt.month
    P["dow"] = P.dt.dt.day_of_week
    P["risk_atr"] = P.risk/P.atr_day
    P["is_is"] = P.date <= "2022-12-31"
    return P

if __name__ == "__main__":
    from lib import load
    from final_rule import build
    sess = build(load())
    P = build_pool(sess)
    P.to_parquet("research/data/pool_mtf.parquet")
    print("signals:", len(P), "| days:", P.date.nunique(), "| per day:", round(len(P)/P.date.nunique(),2))
    print("per year:"); print(P.groupby("year").size().to_string())
    print("\nwin rate at each R:R (raw signals, no extra filters):")
    for r in RRS:
        wr, Rr = P[f"w{r:g}"], P[f"R{r:g}"]
        print(f" 1:{r:.2f}  n={len(P)}  win={100*wr.mean():5.1f}%  R/tr={Rr.mean():+.3f}  "
              f"PF={Rr[Rr>0].sum()/abs(Rr[Rr<=0].sum()):.2f}")
