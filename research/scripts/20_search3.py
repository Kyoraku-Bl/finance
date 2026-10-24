"""Search a SIMPLE, robust rule for: 09:45-12:00 NY, stop >= 10 pts, 1:2 target.
Candidates = structural cuts (entry time, stop width) x candlestick confluences on 3m / 15m / 1h.
Ranked by MIN(in-sample, out-of-sample) win rate at 1:2."""
import itertools, numpy as np, pandas as pd, sys
sys.path.insert(0,"research/scripts")

P = pd.read_parquet("research/data/pool_mtf3.parquet")
F3 = ["c3_body","c3_struct","c3_close_ok","c3_engulf","c3_dir","c3_inside"]
F15= ["c15_premium","c15_dev_dir","c15_prev_dir","c15_engulf","c15_body","c15_wick",
      "c15_close_beyond","c15_prev_clv"]
F60= ["c60_dir","c60_body","c60_engulf","c60_struct","c60_close_beyond","c60_two_dir",
      "c60_premium","c60_dev_dir"]
FEATS=F3+F15+F60
for f in FEATS: P[f]=P[f].fillna(0).astype(int)

CUTS = {
  "any time":      np.ones(len(P), bool),
  "entry<=10:15":  (P.entry_t<=615).values,
  "entry<=10:30":  (P.entry_t<=630).values,
  "entry<=11:00":  (P.entry_t<=660).values,
  "entry>=10:30":  (P.entry_t>=630).values,
}
RISKS = {
  "any stop":      np.ones(len(P), bool),
  "stop<=12":      (P.risk<=12).values,
  "stop<=15":      (P.risk<=15).values,
  "stop 10-15":    ((P.risk>=10)&(P.risk<=15)).values,
  "stop 10-12":    ((P.risk>=10)&(P.risk<=12)).values,
}
BASES = {}
for cn,cm in CUTS.items():
    for rn,rm in RISKS.items():
        if cn=="any time" and rn=="any stop": continue
        BASES[f"{cn} | {rn}"] = cm & rm
BASES["no structural cut"] = np.ones(len(P), bool)

def stats(mask, n_feat=0):
    d=P[mask]; a=d[d.is_is]; b=d[~d.is_is]
    if len(a)<25 or len(b)<25: return None
    return dict(n=len(d), n_is=len(a), n_oos=len(b),
                is_w=100*a.w2.mean(), oos_w=100*b.w2.mean(),
                is_R=a.R2.mean(), oos_R=b.R2.mean())

rows=[]
for bn,bm in BASES.items():
    s=stats(bm)
    if s: rows.append(dict(base=bn, combo="(none)", size=0, **s))
for size in (1,2,3):
    for combo in itertools.combinations(FEATS,size):
        m=np.ones(len(P),bool)
        for f in combo: m &= (P[f].values==1)
        for bn,bm in BASES.items():
            s=stats(bm&m)
            if s: rows.append(dict(base=bn, combo="+".join(combo), size=size, **s))
R=pd.DataFrame(rows)
R["min_w"]=R[["is_w","oos_w"]].min(axis=1)
R=R.round(3)
R.to_csv("research/out/mtf3_combos.csv",index=False)
print(f"evaluated {len(R)} rules on pool n={len(P)}\n")
print("=== top 30 by MIN(IS,OOS) win% @1:2 (n>=60, IS>=30, OOS>=30) ===")
t=R[(R.n>=60)&(R.n_is>=30)&(R.n_oos>=30)].sort_values(["min_w","n"],ascending=[False,False])
print(t.head(30)[["base","combo","n","n_is","n_oos","is_w","oos_w","min_w","is_R","oos_R"]].to_string(index=False))
print("\n=== best per structural base (min_w), n>=60 ===")
g=R[(R.n>=60)&(R.n_is>=30)&(R.n_oos>=30)].sort_values("min_w",ascending=False).groupby("base").head(1)
print(g.sort_values("min_w",ascending=False)[["base","combo","n","is_w","oos_w","min_w"]].to_string(index=False))
