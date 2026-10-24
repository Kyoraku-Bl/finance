"""
MORNING IFVG + 3-min / 15-min candle confluences  (final rule, max 2 trades/day)

Base setup (unchanged from the 1-min version):
  09:30-10:00 NY, any 1-min FVG (>=4 ticks) that a 1-min candle CLOSES through
  (IFVG) within 10 candles; the inverting candle's volume <= 1.2x the morning median.
  Entry = limit at the far edge of the inverted gap, stop = 2 ticks beyond the other edge.

NEW - confluences (all strictly causal, only completed candles):
  15m  P : "premium/discount" - at the moment of the fill, price must be in the
           upper half of the 15-min candle that is forming (short) / lower half (long).
  3m   M : "momentum candle"  - the last COMPLETED 3-min candle is in the trade
           direction with a body >= 50% of its range.
  3m   S : "structure"        - the last COMPLETED 3-min candle takes out the previous
           candle's high (short) / low (long), i.e. lower-high + lower-low / HH+HL.
  3m   C : "close beyond"     - the last completed 3-min candle closes beyond the gap edge.
  3m   E : "engulfing"        - the last completed 3-min candle engulfs the previous one
           against the gap.

  min_conf = how many of {M,S,C,E} must be present. P is always required.
  At most MAX_TRADES_PER_DAY fills per session (first come, first served).
"""
import numpy as np, pandas as pd, sys
sys.path.insert(0,"research/scripts")
from lib import COST_PTS

RRS = (2.0, 1.5, 1.0, 0.75, 2/3, 0.5)
RR_LABEL = {2.0:"1:2", 1.5:"1:1.5", 1.0:"1:1", 0.75:"1:0.75", 2/3:"1:0.67", 0.5:"1:0.5"}
MAX_TRADES_PER_DAY = 2
CONF = ["c3_body","c3_struct","c3_close_ok","c3_engulf"]

def select(P, min_conf=2, require_premium=True, max_per_day=MAX_TRADES_PER_DAY,
           sequential=False):
    """sequential=True -> a new trade may only start after the previous one is closed."""
    d = P.copy()
    d["score"] = d[CONF].sum(axis=1)
    if require_premium:
        d = d[d.c15_premium == 1]
    d = d[d.score >= min_conf]
    d = d.sort_values(["date","entry_t"]).reset_index(drop=True)
    keep = []
    for date, g in d.groupby("date", sort=True):
        used = 0; busy_until = -1
        for idx, row in g.iterrows():
            if used >= max_per_day: break
            if sequential and row["entry_i"] < busy_until: continue
            keep.append(idx); used += 1
            busy_until = row.get("xbar2", row["entry_i"])
    d = d.loc[keep].copy()
    d["trade_no"] = d.groupby("date").cumcount() + 1
    return d

def rr_table(d, by=None):
    """win% / R per trade / PF for every R:R, optionally grouped"""
    def one(g):
        out = {}
        for r in RRS:
            w, R = g[f"w{r:g}"], g[f"R{r:g}"]
            gp, gl = R[R>0].sum(), abs(R[R<=0].sum())
            out[f"win% {RR_LABEL[r]}"] = round(100*w.mean(),1)
            out[f"PF {RR_LABEL[r]}"] = round(gp/gl,2) if gl else np.nan
        out["n"] = len(g)
        for r in RRS:
            out[f"R/tr {RR_LABEL[r]}"] = round(g[f"R{r:g}"].mean(),3)
        return pd.Series(out)
    if by is None: return one(d).to_frame().T
    return d.groupby(by).apply(one, include_groups=False)

if __name__ == "__main__":
    P = pd.read_parquet("research/data/pool_mtf.parquet")
    for mc in (0,1,2,3):
        d = select(P, min_conf=mc)
        t = rr_table(d).iloc[0]
        print(f"min_conf={mc}  n={int(t.n):4d} ({t.n/6.8:4.0f}/yr)  "
              + "  ".join(f"{RR_LABEL[r]}={t['win% '+RR_LABEL[r]]:.1f}%" for r in RRS))
