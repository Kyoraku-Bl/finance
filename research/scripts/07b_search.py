import numpy as np, pandas as pd, itertools
pool = pd.read_parquet("research/data/pool2.parquet")
pool["bias_ok"]=np.where(pool.side==1, pool.entry>pool.pdc, pool.entry<pool.pdc)
pool["ema_ok"]=np.where(pool.side==1, pool.ema_up==1, pool.ema_up==0)
pool["is_is"]=pool.date<="2022-12-31"

C={
 "edge":"emode=='edge'","fifty":"emode=='fifty'","swing":"smode=='swing'","gapstop":"smode=='gap'",
 "long":"side==1","short":"side==-1",
 "lvl_on":"level in ('on_h','on_l')","lvl_pm":"level in ('pm_h','pm_l')","lvl_pd":"level in ('pdh','pdl')",
 "lvl_on_h":"level=='on_h'","lvl_on_l":"level=='on_l'","lvl_pm_h":"level=='pm_h'","lvl_pm_l":"level=='pm_l'",
 "lvl_pdh":"level=='pdh'","lvl_pdl":"level=='pdl'",
 "t<=590":"entry_t<=590","t<=600":"entry_t<=600","t<=630":"entry_t<=630","t>=590":"entry_t>=590",
 "risk<=10":"risk<=10","risk<=12":"risk<=12","risk<=16":"risk<=16","risk>=10":"risk>=10","risk>=12":"risk>=12",
 "gap>=8":"gap_t>=8","gap>=12":"gap_t>=12","gap>=16":"gap_t>=16","gap<=8":"gap_t<=8","gap<=12":"gap_t<=12",
 "disp>=0.3":"disp>=0.3","disp>=0.6":"disp>=0.6","disp<=0.4":"disp<=0.4",
 "rej>=0.5":"rej>=0.5","rej>=0.7":"rej>=0.7","rej<=0.5":"rej<=0.5",
 "wait<=1":"wait<=1","wait<=2":"wait<=2","wait<=4":"wait<=4",
 "bias":"bias_ok","ema":"ema_ok",
 "1st":"first_touch==1","rng>=1":"sess_rng_atr>=1.0","rng<=0.6":"sess_rng_atr<=0.6",
 "sweep>=4":"sweep_depth>=4","sweep>=8":"sweep_depth>=8","sweep<=8":"sweep_depth<=8",
 "gaplvl<=0.5":"gap_open_atr<=0.5","gaplvl>=0.5":"gap_open_atr>=0.5",
 "gap_atr>=0.1":"gap_atr>=0.10","gap_atr>=0.2":"gap_atr>=0.20",
}
keys=list(C); rows=[]
def measure(mask,label):
    d=pool[mask].sort_values("entry_t").drop_duplicates("date",keep="first")
    a=d[d.is_is]; b=d[~d.is_is]
    if len(a)<60 or len(b)<50: return None
    def w(x): return round(100*(x.R>0).mean(),1)
    return dict(label=label,n=len(d),win=round(100*(d.R>0).mean(),1),exp=round(d.R.mean(),3),
        n_is=len(a),w_is=w(a),e_is=round(a.R.mean(),3),n_oos=len(b),w_oos=w(b),e_oos=round(b.R.mean(),3),
        medrisk=round(d.risk.median(),1),py=round(len(d)/6.8,1))
base=np.ones(len(pool),bool)
for r in (1,2,3):
    for combo in itertools.combinations(keys,r):
        mask=base.copy()
        for k in combo: mask&=pool.eval(C[k]).to_numpy()
        if mask.sum()<150: continue
        m=measure(mask,"+".join(combo))
        if m: rows.append(m)
res=pd.DataFrame(rows); res["minw"]=res[["w_is","w_oos"]].min(axis=1)
res=res[res.n>=120]
res.to_csv("research/out/search_pool2.csv",index=False)
print(len(res),"combos; top by min(IS,OOS) win%")
print(res.sort_values("minw",ascending=False).head(25).to_string())
