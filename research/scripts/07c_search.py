import numpy as np, pandas as pd, itertools
pool = pd.read_parquet("research/data/pool2.parquet")
risk = pool.risk
tgt = pool.entry + 2*risk*pool.side
# ---- "room to target": are there untapped HTF levels between entry and target? ----
def blockers(row):
    lv = [row.on_h,row.pm_h,row.pdh] if row.side==1 else [row.on_l,row.pm_l,row.pdl]
    L,H = sorted([row.entry,row.tgt])
    return sum(1 for x in lv if x==x and L < x < H)
pool["tgt"]=tgt
pool["blockers"]=pool.apply(blockers,axis=1)
hi = np.vstack([pool.on_h.values,pool.pm_h.values,pool.pdh.values]).T.astype(float)
lo = np.vstack([pool.on_l.values,pool.pm_l.values,pool.pdl.values]).T.astype(float)
E = pool.entry.values[:,None]
hi = np.where(np.isnan(hi)|(hi<=E), np.inf, hi); lo = np.where(np.isnan(lo)|(lo>=E), -np.inf, lo)
nearest = np.where(pool.side.values==1, hi.min(axis=1)-pool.entry.values, pool.entry.values-lo.max(axis=1))
pool["room_R"]=nearest/risk.values
pool["bias_ok"]=np.where(pool.side==1, pool.entry>pool.pdc, pool.entry<pool.pdc)
pool["ema_ok"]=np.where(pool.side==1, pool.ema_up==1, pool.ema_up==0)
pool["is_is"]=pool.date<="2022-12-31"
pool.to_parquet("research/data/pool2b.parquet")
print("blockers distribution:", pool.blockers.value_counts().to_dict())
print("win by blockers (base: edge/swing all):")
b=pool[(pool.emode=="edge")&(pool.smode=="swing")]
print(b.groupby("blockers").R.agg(n="size",win=lambda x: round(100*(x>0).mean(),1),exp="mean").to_string())
