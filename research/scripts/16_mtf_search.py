import numpy as np, pandas as pd, itertools
pd.set_option("display.width",250)
P = pd.read_parquet("research/data/pool_mtf.parquet")
C3  = ["c3_body","c3_struct","c3_dir","c3_close_ok","c3_engulf"]
C15 = ["c15_premium","c15_prev_clv","c15_two_dir","c15_prev_dir","c15_close_beyond"]
RISK= [None, 0.05, 0.04, 0.035]
def ev(mask,label,r=2.0):
    d=P[mask]
    if len(d)<80: return None
    a,b=d[d.is_is],d[~d.is_is]
    if len(a)<30 or len(b)<30: return None
    w,R=f"w{r:g}",f"R{r:g}"
    yrs=d.groupby("year")[R].apply(lambda x:100*(x>0).mean())
    return dict(label=label,n=len(d),win=round(100*d[w].mean(),1),Rpt=round(d[R].mean(),3),
        PF=round(d[R][d[R]>0].sum()/abs(d[R][d[R]<=0].sum()),2),
        w_is=round(100*a[w].mean(),1),w_oos=round(100*b[w].mean(),1),
        minYr=round(yrs.min(),1),yrs_pos=int((d.groupby("year")[R].sum()>0).sum()),
        py=round(len(d)/6.8,0))
rows=[]
for rr in RISK:
    for r3 in (0,1,2):
        for m3 in itertools.combinations(C3,r3):
            for r15 in (0,1,2):
                for m15 in itertools.combinations(C15,r15):
                    if r3+r15==0: continue
                    mask=np.ones(len(P),bool)
                    if rr is not None: mask &= (P.risk_atr<=rr).to_numpy()
                    for c_ in m3: mask &= (P[c_]==1).to_numpy()
                    for c_ in m15: mask &= (P[c_]==1).to_numpy()
                    if mask.sum()<110: continue
                    lab=(f"risk<={rr:.0%}|" if rr else "")+ \
                        ("3m:"+("+".join(x.replace("c3_","") for x in m3)) if m3 else "")+ \
                        ("|15m:"+("+".join(x.replace("c15_","") for x in m15)) if m15 else "")
                    e=ev(mask,lab)
                    if e: rows.append(e)
R=pd.DataFrame(rows); R["minW"]=R[["w_is","w_oos"]].min(axis=1)
R.to_csv("research/out/mtf_combos.csv",index=False)
print(len(R),"combos with n>=110\n")
print("TOP by min(IS,OOS):")
print(R.sort_values(["minW","n"],ascending=False).head(20).to_string(index=False))
print("\n3m alone / 15m alone (no risk filter):")
print(R[R.label.str.match(r"^(3m:|15m:|\|15m:)") & (R.n>=180)].sort_values("minW",ascending=False).head(12).to_string(index=False))
