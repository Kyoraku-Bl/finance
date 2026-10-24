import numpy as np, pandas as pd, itertools
P=pd.read_parquet("research/data/pool6.parquet")
C={"long":"side==1","short":"side==-1","edge":"emode=='edge'","fifty":"emode=='fifty'",
 "t<=590":"entry_t<=590","t<=600":"entry_t<=600","t<=615":"entry_t<=615","t<=630":"entry_t<=630",
 "tgt<=0.08":"tgt_over_atr<=0.08","tgt<=0.10":"tgt_over_atr<=0.10","tgt<=0.12":"tgt_over_atr<=0.12","tgt<=0.15":"tgt_over_atr<=0.15",
 "risk<=20":"risk<=20","risk<=25":"risk<=25","risk<=30":"risk<=30",
 "lag<=3":"inv_lag<=3","lag<=5":"inv_lag<=5","lag<=10":"inv_lag<=10",
 "gap>=6":"gap_t>=6","gap>=10":"gap_t>=10","gap<=20":"gap_t<=20",
 "vol<=1":"vol_inv<=1","vwap_near":"vs_vwap.between(-1,0)",
 "prior0":"prior==0","ema":"(side==1)&(ema_up==1) | (side==-1)&(ema_up==0)",
}
keys=list(C); rows=[]
def meas(mask,label):
    d=P[mask].sort_values("entry_t").drop_duplicates("date")
    a,b=d[d.is_is],d[~d.is_is]
    if len(d)<120 or len(a)<45 or len(b)<45: return None
    w=lambda x:round(100*(x.R>0).mean(),1)
    yr=d.groupby("year").apply(lambda x:100*(x.R>0).mean(),include_groups=False)
    return dict(label=label,n=len(d),win=round(100*(d.R>0).mean(),1),exp=round(d.R.mean(),3),
        n_is=len(a),w_is=w(a),n_oos=len(b),w_oos=w(b),medrisk=round(d.risk.median(),1),
        py=round(len(d)/6.8,1),pf=round(d.R[d.R>0].sum()/abs(d.R[d.R<=0].sum()),2),
        worst_y=round(yr.min(),1),yrs_pos=int((d.groupby("year").R.sum()>0).sum()))
base=np.ones(len(P),bool)
for r in (1,2,3,4):
    for combo in itertools.combinations(keys,r):
        mask=base.copy()
        for k in combo: mask&=P.eval(C[k]).fillna(False).to_numpy()
        if mask.sum()<150: continue
        m=meas(mask,"+".join(combo))
        if m: rows.append(m)
res=pd.DataFrame(rows); res["minw"]=res[["w_is","w_oos"]].min(axis=1)
res.to_csv("research/out/search_ifvg.csv",index=False)
print(len(res),"combos")
print(res.sort_values(["minw","n"],ascending=False).head(25).to_string())
