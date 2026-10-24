"""Pick the final simple rule on the best structural base, then report all 6 R:R."""
import itertools, numpy as np, pandas as pd, sys
sys.path.insert(0,"research/scripts")
from mtf3_signals import RRS
P=pd.read_parquet("research/data/pool_mtf3.parquet")
F3=["c3_body","c3_struct","c3_close_ok","c3_engulf","c3_dir","c3_inside","c3_reject"]
F15=["c15_premium","c15_dev_dir","c15_prev_dir","c15_engulf","c15_body","c15_wick","c15_close_beyond","c15_prev_clv"]
F60=["c60_dir","c60_body","c60_engulf","c60_struct","c60_close_beyond","c60_two_dir","c60_premium","c60_dev_dir"]
FX=["al_open","or_dir","or_break","or_inside","al_pdc"]
FEATS=F3+F15+F60+FX
for f in FEATS: P[f]=P[f].fillna(0).astype(int)

BASE = (P.setup_t<=600)&(P.entry_t<=630)&(P.risk<=15)
print(f"base (setup<=10:00, entry<=10:30, stop 10-15): n={BASE.sum()}, "
      f"IS {100*P[BASE&P.is_is].w2.mean():.1f}%  OOS {100*P[BASE&~P.is_is].w2.mean():.1f}%")

rows=[]
for size in (1,2,3):
    for combo in itertools.combinations(FEATS,size):
        m=BASE.values.copy()
        for f in combo: m &= (P[f].values==1)
        d=P[m]; a=d[d.is_is]; b=d[~d.is_is]
        if len(a)<20 or len(b)<20 or len(d)<45: continue
        rows.append(dict(combo="+".join(combo),size=size,n=len(d),n_is=len(a),n_oos=len(b),
                         is_w=round(100*a.w2.mean(),1),oos_w=round(100*b.w2.mean(),1),
                         min_w=round(min(100*a.w2.mean(),100*b.w2.mean()),1),
                         is_R=round(a.R2.mean(),3),oos_R=round(b.R2.mean(),3)))
R=pd.DataFrame(rows).sort_values(["min_w","n"],ascending=[False,False])
R.to_csv("research/out/mtf3_final_search.csv",index=False)
print(f"\nevaluated {len(R)} filtered rules\n=== top 20 by MIN(IS,OOS) ===")
print(R.head(20).to_string(index=False))
print("\n=== highest OOS with IS>=55, n>=60 ===")
print(R[(R.is_w>=55)&(R.n>=60)].sort_values("oos_w",ascending=False).head(12).to_string(index=False))
