import numpy as np, pandas as pd, itertools
A=pd.read_parquet("research/data/pool2b.parquet"); A["fam"]="A"
D4=pd.read_parquet("research/data/pool4.parquet"); D=D4[D4.fam=="D"].copy()
keep=["date","side","level","entry_t","risk","entry","stop","gap_t","disp","emode","smode","wait",
      "outcome","R","gross","atr_day","tgt_over_atr","risk_over_atr","pdc","on_h","on_l","pm_h","pm_l","pdh","pdl","fam"]
for d in (A,D):
    for c in keep:
        if c not in d: d[c]=np.nan
P=pd.concat([A[keep],D[keep]],ignore_index=True)
P["bias_ok"]=np.where(P.side==1,P.entry>P.pdc,P.entry<P.pdc)
P["is_is"]=P.date<="2022-12-31"
P["t_ge_585"]=P.entry_t>=585
hi=np.vstack([P.on_h,P.pm_h,P.pdh]).T.astype(float); lo=np.vstack([P.on_l,P.pm_l,P.pdl]).T.astype(float)
E=P.entry.values[:,None]
hi=np.where(np.isnan(hi)|(hi<=E),np.inf,hi); lo=np.where(np.isnan(lo)|(lo>=E),-np.inf,lo)
P["blockers"]=(np.where(P.side.values==1,
     ((hi<E+2*P.risk.values[:,None])).sum(1),
     ((lo>E-2*P.risk.values[:,None])).sum(1)))
C={"fA":"fam=='A'","fD":"fam=='D'","edge":"emode=='edge'","fifty":"emode=='fifty'",
 "swing":"smode=='swing'","gapstop":"smode=='gap'","long":"side==1","short":"side==-1",
 "lvl_on_h":"level=='on_h'","lvl_on_l":"level=='on_l'","lvl_pm_h":"level=='pm_h'","lvl_pm_l":"level=='pm_l'",
 "lvl_pdh":"level=='pdh'","lvl_pdl":"level=='pdl'","lvl_none":"level=='none'",
 "tgt<=0.10":"tgt_over_atr<=0.10","tgt<=0.12":"tgt_over_atr<=0.12","tgt<=0.15":"tgt_over_atr<=0.15",
 "t<=590":"entry_t<=590","t<=600":"entry_t<=600","t<=615":"entry_t<=615","t<=630":"entry_t<=630",
 "t>=585":"t_ge_585","risk<=16":"risk<=16","risk>=10":"risk>=10","risk>=12":"risk>=12",
 "gap>=8":"gap_t>=8","gap>=16":"gap_t>=16","disp>=0.3":"disp>=0.3","wait<=2":"wait<=2","wait<=1":"wait<=1",
 "no_block":"blockers==0","bias":"bias_ok"}
keys=list(C); rows=[]
def measure(mask,label):
    d=P[mask].sort_values("entry_t").drop_duplicates("date")
    a,b=d[d.is_is],d[~d.is_is]
    if len(d)<140 or len(a)<50 or len(b)<50: return None
    w=lambda x: round(100*(x.R>0).mean(),1)
    return dict(label=label,n=len(d),win=round(100*(d.R>0).mean(),1),exp=round(d.R.mean(),3),
        n_is=len(a),w_is=w(a),n_oos=len(b),w_oos=w(b),medrisk=round(d.risk.median(),1),
        py=round(len(d)/6.8,1),
        worst_y=round(100*min(d.groupby(pd.to_datetime(d.date).dt.year).apply(lambda x:(x.R>0).mean(),include_groups=False)),1),
        pf=round(d.R[d.R>0].sum()/abs(d.R[d.R<=0].sum()),2))
base=np.ones(len(P),bool)
for r in (1,2,3,4):
    for combo in itertools.combinations(keys,r):
        mask=base.copy()
        for k in combo: mask&=P.eval(C[k]).to_numpy()
        if mask.sum()<250: continue
        m=measure(mask,"+".join(combo))
        if m: rows.append(m)
res=pd.DataFrame(rows); res["minw"]=res[["w_is","w_oos"]].min(axis=1)
res.to_csv("research/out/search_final.csv",index=False)
print(len(res),"combos")
print(res.sort_values(["minw","n"],ascending=False).head(30).to_string())
