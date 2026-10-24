import numpy as np, pandas as pd, sys, json
sys.path.insert(0,"research/scripts")
from final_rule import build, backtest, find
from lib import load
pd.set_option("display.width",200)

df=load(); sess=build(df)
tr=backtest(sess)
tr.to_parquet("research/data/trades_final.parquet")
tr["year"]=tr.dt.dt.year; tr["month"]=tr.dt.dt.month; tr["dow"]=tr.dt.dt.day_of_week

def block(d):
    if len(d)==0: return dict(n=0)
    w=d.R>0; gp=d.R[w].sum(); gl=abs(d.R[~w].sum())
    return dict(n=len(d), wins=int(w.sum()), losses=int((~w).sum()),
                win_rate=round(100*w.mean(),2),
                tp=round(100*(d.outcome=="target").mean(),2),
                sl=round(100*(d.outcome=="stop").mean(),2),
                time_exit=round(100*(d.outcome=="time").mean(),2),
                total_R=round(d.R.sum(),2), avg_R=round(d.R.mean(),3),
                pf=round(gp/gl,3) if gl else np.nan,
                avg_pts=round(d.pnl_pts.mean(),2), total_pts=round(d.pnl_pts.sum(),1),
                med_risk=round(d.risk.median(),2), med_bars=round(d.bars.median(),1),
                usd_1contract=round(d.pnl_usd_1MNQ.sum(),0))
out={}
out["overall"]=block(tr)
out["by_year"]={int(y):block(g) for y,g in tr.groupby("year")}
out["by_month"]={int(m):block(g) for m,g in tr.groupby("month")}
out["by_dow"]={int(d):block(g) for d,g in tr.groupby("dow")}
out["by_side"]={"long":block(tr[tr.side==1]),"short":block(tr[tr.side==-1])}
out["by_entry_hour"]={int(k):block(g) for k,g in tr.groupby(tr.entry_t//60)}
out["by_hold"]={"<=5min":block(tr[tr.bars<=5]),"6-15":block(tr[tr.bars.between(6,15)]),
                "16-30":block(tr[tr.bars.between(16,30)]),">30":block(tr[tr.bars>30])}
out["is_oos"]={"2019-2022":block(tr[tr.dt<="2022-12-31"]),"2023-2026":block(tr[tr.dt>"2022-12-31"])}
out["by_gap_size"]={"1.0-1.75pt":block(tr[tr.gap_t<=7]),"1.75-3pt":block(tr[tr.gap_t.between(8,12)]),
                    ">3pt":block(tr[tr.gap_t>12])}
out["by_risk"]={"<=8pt":block(tr[tr.risk<=8]),"8-12pt":block(tr[tr.risk.between(8,12)]),
                "12-20pt":block(tr[tr.risk.between(12,20)]),">20pt":block(tr[tr.risk>20])}
out["by_invlag"]={"1-3":block(tr[tr.inv_lag<=3]),"4-6":block(tr[tr.inv_lag.between(4,6)]),
                  "7-10":block(tr[tr.inv_lag.between(7,10)])}
json.dump(out, open("research/out/metrics.json","w"), indent=2)

print("="*100); print("OVERALL"); print(json.dumps(out["overall"],indent=1))
for k in ["by_year","by_month","by_dow","by_side","is_oos","by_entry_hour","by_hold","by_gap_size","by_risk","by_invlag"]:
    print("\n===",k,"===")
    print(pd.DataFrame(out[k]).T.to_string())
# year x month matrix of win-rate and trade count
m=tr.pivot_table(index="year",columns="month",values="R",aggfunc=lambda x:round(100*(x>0).mean(),1))
cnt=tr.pivot_table(index="year",columns="month",values="R",aggfunc="size")
m.to_csv("research/out/win_by_year_month.csv"); cnt.to_csv("research/out/trades_by_year_month.csv")
print("\n=== win-rate %, year x month ==="); print(m.to_string())
print("\n=== trades, year x month ==="); print(cnt.fillna(0).astype(int).to_string())
print("\nexit hour distribution:"); print(tr.groupby(tr.exit_t//60).size().to_string())
print("\navg points per trade by side:"); print(tr.groupby("side").pnl_pts.describe().to_string())
