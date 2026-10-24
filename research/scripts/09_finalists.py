import numpy as np, pandas as pd
A=pd.read_parquet("research/data/pool2b.parquet"); A["fam"]="A"
D4=pd.read_parquet("research/data/pool4.parquet"); D=D4[D4.fam=="D"].copy()
keep=["date","side","level","entry_t","risk","entry","stop","gap_t","disp","emode","smode","wait",
      "outcome","R","atr_day","tgt_over_atr","pdc","on_h","on_l","pm_h","pm_l","pdh","pdl","fam","bars","mfe"]
for d in (A,D):
    for c in keep:
        if c not in d: d[c]=np.nan
P=pd.concat([A[keep],D[keep]],ignore_index=True)
P["is_is"]=P.date<="2022-12-31"
P["dt"]=pd.to_datetime(P.date); P["year"]=P.dt.dt.year; P["month"]=P.dt.dt.month; P["dow"]=P.dt.dt.dayofweek

RULES={
 "R1 FVG-sweep scalp (A: gapstop, disp>=.3, t<=615, tgt<=10%)":
    "fam=='A' and smode=='gap' and disp>=0.3 and entry_t<=615 and tgt_over_atr<=0.10",
 "R2 FVG-sweep scalp wide (A: gapstop, t<=615, tgt<=10%)":
    "fam=='A' and smode=='gap' and entry_t<=615 and tgt_over_atr<=0.10",
 "R3 IFVG long (D: long, t<=600, tgt<=15%)":
    "fam=='D' and side==1 and entry_t<=600 and tgt_over_atr<=0.15",
 "R4 IFVG any (D: t<=600, tgt<=10%)":
    "fam=='D' and entry_t<=600 and tgt_over_atr<=0.10",
 "R5 IFVG any (D: t<=615, tgt<=10%)":
    "fam=='D' and entry_t<=615 and tgt_over_atr<=0.10",
 "R6 plain sweep+FVG (A: edge/swing, no filters)":
    "fam=='A' and emode=='edge' and smode=='swing'",
}
def show(rule):
    d=P.query(rule).sort_values("entry_t").drop_duplicates("date")
    a,b=d[d.is_is],d[~d.is_is]
    w=lambda x:100*(x.R>0).mean()
    print(f"\n{rule}\n  n={len(d)} ({len(d)/6.8:.0f}/yr) win={w(d):.1f}% exp={d.R.mean():+.3f}R "
          f"PF={d.R[d.R>0].sum()/abs(d.R[d.R<=0].sum()):.2f} medrisk={d.risk.median():.1f}pt | "
          f"IS n={len(a)} w={w(a):.1f}% | OOS n={len(b)} w={w(b):.1f}%")
    yr=d.groupby("year").R.agg(n="size",win=lambda x:round(100*(x>0).mean(),1),R="sum")
    print("  "+yr.to_string().replace("\n","\n  "))

for k in RULES:
    print("="*70); print(k); show(RULES[k])
