"""
FINAL RULE  --  "wide-stop morning IFVG, 09:45-12:00 NY"

1. SETUP (1-min): a 1-min FVG (candle1.high < candle3.low, or candle1.low > candle3.high)
   at least 4 ticks tall, formed between 09:30 and 10:00.
2. FAILURE: a 1-min candle CLOSES fully through the far side of that gap (it becomes an
   inverted gap) within 10 candles, and that candle's volume is <= 1.2x the median volume
   of the first 20 one-minute bars of the session.
3. STOP WIDTH: the gap must be 10 to 15 index points tall. Entry is the limit at the far
   edge, the stop is 2 ticks beyond the other edge, so 1R is always >= 10 points
   (that is the "never less than 10 points" rule).
4. CONFIRMATIONS (candles only, at least 2 of these 3 must be true):
     3-min : the last COMPLETED 3-minute candle has a body >= 50% of its range
             (the gap was broken decisively, not by a doji)
     15-min: at the fill, price is in the upper half of the 15-minute candle that is
             still forming for a short, the lower half for a long (sell premium / buy discount)
     1-hour: at the fill, price is on the trade's side of the 1-hour candle's open,
             which is the 09:30 open (i.e. trade WITH the morning's direction)
5. ENTRY: limit order at the gap edge, filled between 09:45 and 12:00 NY.
   Max 2 trades per day.
6. TARGET: hard R:R, no trailing; flat at 15:55 if neither level is hit.
"""
import numpy as np, pandas as pd, sys
sys.path.insert(0,"research/scripts")
from mtf3_signals import RRS
from lib import COST_PTS

RR_LABEL = {2.0:"1:2",1.5:"1:1.5",1.0:"1:1",0.75:"1:0.75",2/3:"1:0.67",0.5:"1:0.5"}
CONF3 = ["c3_body","c15_premium","al_open"]
CONF_NAME = {"c3_body":"3m big body","c15_premium":"15m premium side","al_open":"1h direction"}
MAX_PER_DAY = 2

def rule(P, min_of_3=2, setup_end=600, stop_max=15.0, entry_end=12*60, max_per_day=MAX_PER_DAY):
    d = P.copy()
    d["score"] = d[CONF3].fillna(0).sum(axis=1)
    d = d[(d.score >= min_of_3) & (d.setup_t <= setup_end) &
          (d.risk <= stop_max) & (d.entry_t <= entry_end)]
    d = d.sort_values(["date","entry_t"]).reset_index(drop=True)
    keep = []
    for _, g in d.groupby("date", sort=True):
        for idx in g.index[:max_per_day]: keep.append(idx)
    d = d.loc[keep].copy()
    d["trade_no"] = d.groupby("date").cumcount() + 1
    d["is_is"] = d.date <= "2022-12-31"
    return d

def table(d):
    rows = []
    for r in RRS:
        w, R = d[f"w{r:g}"], d[f"R{r:g}"]
        pts = R * d.risk
        gp, gl = R[R>0].sum(), abs(R[R<=0].sum())
        rows.append(dict(RR=RR_LABEL[r], trades=len(d), wins=int(w.sum()),
            win_pct=round(100*w.mean(),1), breakeven_pct=round(100/(1+r),1),
            edge_pp=round(100*w.mean()-100/(1+r),1),
            R_per_trade=round(R.mean(),3), total_R=round(R.sum(),1),
            profit_factor=round(gp/gl,2) if gl else np.nan,
            pts_per_trade=round(pts.mean(),2), total_pts=round(pts.sum(),1),
            usd_per_trade_1NQ=round((pts*20-5).mean(),2),
            usd_per_trade_1MNQ=round((pts*2-1.24).mean(),2)))
    return pd.DataFrame(rows)

if __name__ == "__main__":
    P = pd.read_parquet("research/data/pool_mtf3.parquet")
    d = rule(P)
    print(f"trades={len(d)}  days={d.date.nunique()}  ({len(d)/6.8:.1f}/yr)")
    print(table(d).to_string(index=False))
