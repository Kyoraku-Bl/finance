import numpy as np, pandas as pd
pool = pd.read_parquet("research/data/pool.parquet")
pool["year"]=pd.to_datetime(pool.date).dt.year
pool["bias_up"]=pool.entry>pool.pdc

def sel(f, first=True):
    d = pool.query(f) if isinstance(f,str) else pool[f]
    if first:
        d = d.sort_values("entry_t").drop_duplicates("date", keep="first")
    return d

def st(d, label=""):
    if len(d)==0: return dict(label=label,n=0)
    w=d.R>0; gp=d.R[w].sum(); gl=abs(d.R[~w].sum())
    return dict(label=label,n=len(d),win=round(100*w.mean(),1),exp=round(d.R.mean(),3),
                pf=round(gp/gl,2) if gl else np.nan, medrisk=round(d.risk.median(),1),
                tp=round(100*(d.outcome=='target').mean(),1), sl=round(100*(d.outcome=='stop').mean(),1))

base = "emode=='edge' and smode=='swing' and wait<=8"
if __name__=="__main__":
    print(st(sel(base),"BASE sweep+FVG (edge/swing)"))
    print()
    for feat,q in [("side",None),("level",None)]:
        for v in pool[feat].unique():
            f = base + (f" and side=={v}" if feat=="side" else f" and level=='{v}'")
            print(st(sel(f), f"{feat}={v}"))
    print()
    for col,bins in [("entry_t",[570,580,590,600,615,630,645,660,675,690]),
                     ("gap_t",[0,2,4,6,10,16,30]),
                     ("disp",[0,0.5,0.8,1.2,1.8,3]),
                     ("rej",[0,0.3,0.5,0.65,0.8]),
                     ("risk",[0,5,8,12,18,25,40]),
                     ("volr",[0,0.5,1,2,4,10]),
                     ("wait",[0,1,2,3,5,8]),
                     ("gap_atr",[0,0.05,0.1,0.2,0.4]),
                     ("mfe",None)]:
        if bins is None: continue
        d=sel(base+" and "+" and ".join(["1==1"]))
        d["b"]=pd.cut(d[col],bins)
        g=d.groupby("b",observed=True).apply(lambda x: pd.Series(dict(n=len(x),win=round(100*(x.R>0).mean(),1),exp=round(x.R.mean(),3))),include_groups=False)
        print(f"--- {col} ---"); print(g.to_string())
