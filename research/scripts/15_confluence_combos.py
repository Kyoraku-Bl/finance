import numpy as np, pandas as pd, itertools
pd.set_option("display.width",250)
P = pd.read_parquet("research/data/pool_mtf.parquet")
C3  = ["c3_body","c3_struct","c3_dir","c3_engulf","c3_close_ok"]
C15 = ["c15_premium","c15_dev_dir"]
def ev(mask,label,r=2.0):
    d=P[mask]
    if len(d)<60: return None
    a,b=d[d.is_is],d[~d.is_is]
    if len(a)<25 or len(b)<25: return None
    w,R=f"w{r:g}",f"R{r:g}"
    yrs=d.groupby("year")[R].apply(lambda x:100*(x>0).mean())
    return dict(label=label,n=len(d),win=round(100*d[w].mean(),1),Rpt=round(d[R].mean(),3),
        PF=round(d[R][d[R]>0].sum()/abs(d[R][d[R]<=0].sum()),2),
        w_is=round(100*a[w].mean(),1),w_oos=round(100*b[w].mean(),1),
        minYr=round(yrs.min(),1),yrs_pos=int((d.groupby("year")[R].sum()>0).sum()))
rows=[]
base=np.ones(len(P),bool)
for r3 in range(0,4):
    for m3 in itertools.combinations(C3,r3):
        for r15 in range(0,3):
            for m15 in itertools.combinations(C15,r15):
                if r3+r15==0: continue
                mask=base.copy()
                for c in m3: mask &= (P[c]==1).to_numpy()
                for c in m15: mask &= (P[c]==1).to_numpy()
                if mask.sum()<120: continue
                lab=("3m:"+("+".join(x.replace("c3_","") for x in m3)) if m3 else "")+ \
                    ("|15m:"+("+".join(x.replace("c15_","") for x in m15)) if m15 else "")
                e=ev(mask,lab)
                if e: rows.append(e)
R=pd.DataFrame(rows)
R["minW"]=R[["w_is","w_oos"]].min(axis=1)
R.to_csv("research/out/confluence_combos.csv",index=False)
print(f"{len(R)} combos\n")
print("TOP by min(IS,OOS) win% at 1:2  (n>=120)")
print(R.sort_values(["minW","n"],ascending=False).head(22).to_string(index=False))
print("\nTOP by n (most trades) among those with minW>=52")
print(R[R.minW>=52].sort_values("n",ascending=False).head(15).to_string(index=False))
print("\nKey single/paired results of interest:")
for lab in ["3m:body|15m:dev_dir","3m:body|15m:premium","15m:dev_dir","15m:premium",
            "3m:body|15m:dev_dir+premium","3m:struct+body|15m:dev_dir+premium",
            "3m:body+struct+dir|15m:dev_dir+premium"]:
    q=R[R.label==lab]
    if len(q): print(q.to_string(index=False))
