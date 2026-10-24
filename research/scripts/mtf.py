"""
Multi-timeframe helpers: 3-minute and 15-minute candles derived from the 1-minute
session arrays, plus candle-only confluence features that are strictly causal
(a feature at bar k may only use data available at the close of bar k).
"""
import numpy as np
from lib import TICK

def tf_from_1m(s, minutes):
    """Aggregate a session's 1-min arrays into `minutes`-minute candles anchored to 09:30.
    Returns arrays of open/high/low/close, the 1-min index where each candle starts,
    and the 1-min index of each candle's last available bar."""
    m = s["mod"]; o,h,l,c = s["o"],s["h"],s["l"],s["c"]
    start = m[0]
    bucket = (m - start) // minutes
    O,H,L,C,S,E = [],[],[],[],[],[]
    for b in np.unique(bucket):
        idx = np.where(bucket == b)[0]
        O.append(o[idx[0]]); H.append(h[idx].max()); L.append(l[idx].min())
        C.append(c[idx[-1]]); S.append(idx[0]); E.append(idx[-1])
    return dict(o=np.array(O),h=np.array(H),l=np.array(L),c=np.array(C),
                i0=np.array(S), i1=np.array(E), minutes=minutes)

def candle_feats(o,h,l,c):
    """Candle shape features for one candle (vectorised over candle index)."""
    rng = h - l
    rng = np.where(rng == 0, np.nan, rng)
    body = c - o
    return dict(rng=rng, body=body, up=(c > o).astype(int), dn=(c < o).astype(int),
                body_pct=np.abs(body)/rng,
                up_wick=(h - np.maximum(o,c))/rng,
                dn_wick=(np.minimum(o,c) - l)/rng,
                clv=(c - l)/rng)          # close location value 0..1

def completed_upto(tf, k1m):
    """index of the last COMPLETED candle in tf as of 1-min bar k1m, or -1."""
    return int(np.searchsorted(tf["i1"], k1m-1, side="left")) - 1

def developing(tf, k1m):
    """index of the candle currently forming at 1-min bar k1m"""
    i = int(np.searchsorted(tf["i0"], k1m, side="right")) - 1
    return i if 0 <= i < len(tf["i0"]) else -1
