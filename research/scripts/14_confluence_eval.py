import numpy as np, pandas as pd, itertools, sys
pd.set_option("display.width",220)
P = pd.read_parquet("research/data/pool_mtf.parquet")
F3 = ["c3_close_ok","c3_engulf","c3_dir","c3_reject","c3_body","c3_struct","c3_inside"]
F15= ["c15_prev_dir","c15_engulf","c15_body","c15_wick","c15_close_beyond","c15_premium","c15_dev_dir","c15_sweep"]

def ev(mask, label, r=2.0):
    d = P[mask]
    if len(d) < 40: return None
    a, b = d[d.is_is], d[~d.is_is]
    w = f"w{r:g}"; R = f"R{r:g}"
    if len(a) < 25 or len(b) < 25: return None
    yrs = d.groupby("year")[R].apply(lambda x: 100*(x>0).mean())
    return dict(label=label, n=len(d), win=round(100*d[w].mean(),1),
                Rpt=round(d[R].mean(),3), PF=round(d[R][d[R]>0].sum()/abs(d[R][d[R]<=0].sum()),2),
                w_is=round(100*a[w].mean(),1), n_is=len(a), w_oos=round(100*b[w].mean(),1), n_oos=len(b),
                minYr=round(yrs.min(),1), yrs_pos=int((d.groupby("year")[R].sum()>0).sum()))

print("="*110)
print("POOL BASELINE (IFVG + volume + speed filters, no target-size filter)")
print(pd.DataFrame([ev(np.ones(len(P),bool),"ALL")]).to_string(index=False))
print("\n"+"="*110)
print("SINGLE 3-MINUTE CONFLUENCES  (win% at 1:2, and the same filtered out = 'absent')")
rows=[]
for f in F3+["c3_clv"]:
    if f=="c3_clv":
        m1 = P.c3_clv >= 0.5; m0 = P.c3_clv < 0.5
    else:
        m1 = P[f]==1; m0 = P[f]==0
    rows.append(ev(m1, f"{f}=YES")); rows.append(ev(m0, f"{f}=no"))
print(pd.DataFrame([r for r in rows if r]).to_string(index=False))
print("\n"+"="*110)
print("SINGLE 15-MINUTE CONFLUENCES")
rows=[]
for f in F15:
    rows.append(ev(P[f]==1, f"{f}=YES")); rows.append(ev(P[f]==0, f"{f}=no"))
print(pd.DataFrame([r for r in rows if r]).to_string(index=False))
