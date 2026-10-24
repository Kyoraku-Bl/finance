import numpy as np, pandas as pd, itertools
pool = pd.read_parquet("research/data/pool2b.parquet")
C={
 "edge":"emode=='edge'","fifty":"emode=='fifty'","swing":"smode=='swing'","gapstop":"smode=='gap'",
 "long":"side==1","short":"side==-1",
 "lvl_on":"level in ('on_h','on_l')","lvl_pm":"level in ('pm_h','pm_l')","lvl_pd":"level in ('pdh','pdl')",
 "lvl_on_h":"level=='on_h'","lvl_on_l":"level=='on_l'","lvl_pm_h":"level=='pm_h'","lvl_pm_l":"level=='pm_l'",
 "lvl_pdh":"level=='pdh'","lvl_pdl":"level=='pdl'",
 "t>=585":"entry_t>=585","t>=595":"entry_t>=595","t<=600":"entry_t<=600","t<=615":"entry_t<=615","t<=630":"entry_t<=630",
 "risk<=12":"risk<=12","risk<=16":"risk<=16","risk<=20":"risk<=20","risk>=10":"risk>=10",
 "gap>=8":"gap_t>=8","gap>=12":"gap_t>=12","gap>=16":"gap_t>=16",
 "disp>=0.3":"disp>=0.3","disp>=0.6":"disp>=0.6","rej>=0.5":"rej>=0.5","rej>=0.7":"rej>=0.7",
 "wait<=1":"wait<=1","wait<=2":"wait<=2",
 "no_block":"blockers==0","room>=3":"room_R>=3","room>=4":"room_R>=4",
 "1st":"first_touch==1","ema":"ema_ok","bias":"bias_ok",
 "gap_atr>=0.1":"gap_atr>=0.10","gap_atr>=0.2":"gap_atr>=0.20",
}
keys=list(C); rows=[]
def measure(mask,label):
    d=pool[mask].sort_values("entry_t").drop_duplicates("date",keep="first")
    a=d[d.is_is]; b=d[~d.is_is]
    if len(a)<50 or len(b)<50 or len(d)<120: return None
    w=lambda x: round(100*(x.R>0).mean(),1)
    yrs=d.groupby("year").R.agg(["size","mean"])
    return dict(label=label,n=len(d),win=round(100*(d.R>0).mean(),1),exp=round(d.R.mean(),3),
        n_is=len(a),w_is=w(a),n_oos=len(b),w_oos=w(b),medrisk=round(d.risk.median(),1),
        py=round(len(d)/6.8,1), worst_y=round(100*min(d.groupby("year").apply(lambda x:(x.R>0).mean(),include_groups=False)),1))
base=np.ones(len(pool),bool)
for r in (1,2,3):
    for combo in itertools.combinations(keys,r):
        mask=base.copy()
        for k in combo: mask&=pool.eval(C[k]).to_numpy()
        if mask.sum()<200: continue
        m=measure(mask,"+".join(combo))
        if m: rows.append(m)
res=pd.DataFrame(rows); res["minw"]=res[["w_is","w_oos"]].min(axis=1)
res.to_csv("research/out/search_pool2b.csv",index=False)
print(len(res),"combos")
top=res.sort_values(["minw","n"],ascending=False).head(35)
print(top.to_string())
