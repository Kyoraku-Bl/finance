"""Exhaustive conjunction search over the candidate pool with IS/OOS validation."""
import numpy as np, pandas as pd, itertools, sys
pool = pd.read_parquet("research/data/pool.parquet")
pool["bias_up"] = pool.entry > pool.pdc
pool["bias_ok"] = np.where(pool.side==1, pool.entry>pool.pdc, pool.entry<pool.pdc)
pool["yr"] = pd.to_datetime(pool.date).dt.year
# --- realism floors: no micro-stops that 1-min bars cannot resolve, real gaps only ---
pool = pool[(pool.risk>=8) & (pool.gap_t>=4)].copy()
print("pool after realism floors:", len(pool))
IS_MAX = "2022-12-31"; OOS_MIN = "2023-01-01"
pool["is_is"] = pool.date <= IS_MAX

CONDS = {
 "side_long":      "side==1",
 "side_short":     "side==-1",
 "lvl_on":         "level in ('on_h','on_l')",
 "lvl_pm":         "level in ('pm_h','pm_l')",
 "lvl_pd":         "level in ('pdh','pdl')",
 "lvl_on_h":       "level=='on_h'",
 "lvl_on_l":       "level=='on_l'",
 "edge":           "emode=='edge'",
 "fifty":          "emode=='fifty'",
 "swing":          "smode=='swing'",
 "gapstop":        "smode=='gap'",
 "t<=590":         "entry_t<=590",
 "t<=600":         "entry_t<=600",
 "t>=590":         "entry_t>=590",
 "risk<=8":        "risk<=8",
 "risk<=10":       "risk<=10",
 "risk<=12":       "risk<=12",
 "risk<=16":       "risk<=16",
 "risk>=8":        "risk>=8",
 "risk>=10":       "risk>=10",
 "risk>=12":       "risk>=12",
 "risk>=12":       "risk>=12",
 "gap>=4":         "gap_t>=4",
 "gap>=8":         "gap_t>=8",
 "gap>=12":        "gap_t>=12",
 "gap<=6":         "gap_t<=6",
 "disp>=0.3":      "disp>=0.3",
 "disp>=0.6":      "disp>=0.6",
 "disp<=0.4":      "disp<=0.4",
 "rej>=0.5":       "rej>=0.5",
 "rej>=0.7":       "rej>=0.7",
 "wait<=1":        "wait<=1",
 "wait<=2":        "wait<=2",
 "bias":           "bias_ok",
 "retr_deep":      "retr>=0.5",
}
keys=list(CONDS)
rows=[]
def measure(mask, label):
    d = pool[mask].sort_values("entry_t").drop_duplicates("date", keep="first")
    if len(d)<40: return None
    a=d[d.is_is]; b=d[~d.is_is]
    if len(a)<50 or len(b)<50: return None
    return dict(label=label, n=len(d), win=round(100*(d.R>0).mean(),1), exp=round(d.R.mean(),3),
                n_is=len(a), w_is=round(100*(a.R>0).mean(),1), e_is=round(a.R.mean(),3),
                n_oos=len(b), w_oos=round(100*(b.R>0).mean(),1), e_oos=round(b.R.mean(),3),
                tp=round(100*(d.outcome=='target').mean(),1), medrisk=round(d.risk.median(),1))

base = np.ones(len(pool), bool)
for r in (1,2,3):
    for combo in itertools.combinations(keys, r):
        mask = base.copy()
        for k in combo: mask &= pool.eval(CONDS[k]).to_numpy()
        if mask.sum()<60: continue
        m = measure(mask, "+".join(combo))
        if m: rows.append(m)
res = pd.DataFrame(rows)
res["minw"] = res[["w_is","w_oos"]].min(axis=1)
res.to_csv("research/out/search_conjunctions.csv", index=False)
print(len(res), "combinations evaluated")
print(res.sort_values("minw", ascending=False).head(30).to_string())
