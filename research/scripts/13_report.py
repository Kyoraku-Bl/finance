import numpy as np, pandas as pd, sys, json
sys.path.insert(0,"research/scripts")
import lib, final_rule as F
from lib import load
from final_rule import build, backtest

df=load(); S=build(df); tr=backtest(S)
tr["dt"]=pd.to_datetime(tr.date); tr["year"]=tr.dt.dt.year; tr["month"]=tr.dt.dt.month
tr["dow"]=tr.dt.dt.day_of_week
tr.to_csv("research/out/trades_final.csv",index=False)

L=[]
def w(s=""): L.append(s)
def tbl(d, title):
    w(f"**{title}**\n")
    w(d.to_markdown(floatfmt=".2f")); w()

def agg(g):
    n=len(g); wins=int((g.R>0).sum()); gp=g.R[g.R>0].sum(); gl=abs(g.R[g.R<=0].sum())
    return pd.Series(dict(trades=n, wins=wins, losses=n-wins, win_pct=100*wins/n,
        total_R=g.R.sum(), R_per_trade=g.R.mean(), PF=gp/gl if gl else np.nan,
        pts_per_trade=g.pnl_pts.mean(), total_pts=g.pnl_pts.sum(),
        usd_1MNQ=g.pnl_usd_1MNQ.sum(), usd_1NQ=g.pnl_usd_1NQ.sum(), med_stop_pts=g.risk.median()))

w("# THE MORNING IFVG — Nasdaq-100 futures, 1-minute candles\n")
w(f"Data: CME MNQ 1-min OHLCV, {tr.dt.min().date()} to {tr.dt.max().date()} · "
  f"{len(S)} sessions · times are New York (UTC-4/-5), bars labelled with their open time.\n")
tot=agg(tr)
w(f"**Headline:** {int(tot.trades)} trades · {tot.win_pct:.1f}% win rate at 1:2 R:R · "
  f"{tot.R_per_trade:+.3f} R per trade · profit factor {tot.PF:.2f} · "
  f"{tot.pts_per_trade:+.2f} index points per trade after costs.\n")
w("---\n")

# 1. overall
w("## 1. Overall metrics\n")
rows=pd.DataFrame({"value":{
 "Trades":int(tot.trades),"Wins":int(tot.wins),"Losses":int(tot.losses),
 "Win rate %":round(tot.win_pct,2),
 "Hit target (2R) %":round(100*(tr.outcome=="target").mean(),2),
 "Hit stop (-1R) %":round(100*(tr.outcome=="stop").mean(),2),
 "Time exits %":round(100*(tr.outcome=="time").mean(),2),
 "Total R":round(tot.total_R,2),"R per trade":round(tot.R_per_trade,3),
 "Profit factor":round(tot.PF,3),
 "Gross profit (R)":round(tr.R[tr.R>0].sum(),2),"Gross loss (R)":round(tr.R[tr.R<=0].sum(),2),
 "Avg points/trade (net of 1pt cost)":round(tot.pts_per_trade,2),
 "Total points (net)":round(tot.total_pts,1),
 "USD per trade — 1 MNQ (micro, $2/pt, $1.24 comm)":round(tr.pnl_usd_1MNQ.mean(),2),
 "USD per trade — 1 NQ (mini, $20/pt, $5 comm)":round(tr.pnl_usd_1NQ.mean(),2),
 "Total USD — 1 MNQ contract":round(tot.usd_1MNQ,0),
 "Total USD — 1 NQ contract":round(tr.pnl_usd_1NQ.sum(),0),
 "Median stop (points)":round(tot.med_stop_pts,2),
 "Median stop (ticks)":round(tot.med_stop_pts*4,0),
 "Median time in trade (min)":round(tr.bars.median(),1),
 "Trades per year (full years)":round(len(tr)/6.8,1),
 "Max drawdown (R)":round((tr.R.cumsum()-tr.R.cumsum().cummax()).min(),2),
 "Longest losing streak":int(max((len(list(g)) for k,g in __import__("itertools").groupby((tr.R>0)) if not k), default=0)),
 "Best trade (R)":round(tr.R.max(),2),
 "Worst trade (R)":round(tr.R.min(),2),
}})
tbl(rows,"Headline numbers")

# 2. years
w("## 2. Year by year\n")
y=tr.groupby("year").apply(agg,include_groups=False)
y["trades_per_month"]=(y.trades/12).round(2)
tbl(y.round(2),"Per calendar year")
# 3. months
w("## 3. Month by month (all years pooled)\n")
m=tr.groupby("month").apply(agg,include_groups=False)
m.index=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][:len(m)]
tbl(m.round(2),"Per calendar month")
w("### Year x month: R produced\n")
pm=tr.pivot_table(index="year",columns="month",values="R",aggfunc="sum").round(1)
tbl(pm.fillna(0),"Total R")
w("### Year x month: win rate % (trades in brackets)\n")
wr=tr.pivot_table(index="year",columns="month",values="R",aggfunc=lambda x:100*(x>0).mean()).round(0)
cn=tr.pivot_table(index="year",columns="month",values="R",aggfunc="size")
comb=wr.astype(object)
for i in comb.index:
    for c in comb.columns:
        if pd.notna(wr.loc[i,c]): comb.loc[i,c]=f"{wr.loc[i,c]:.0f}% ({int(cn.loc[i,c])})"
tbl(comb.fillna("—"),"win rate (n)")
# 4. dow
w("## 4. Day of week\n")
d=tr.groupby("dow").apply(agg,include_groups=False)
d.index=["Monday","Tuesday","Wednesday","Thursday","Friday"][:len(d)]
tbl(d.round(2),"Per weekday")
# 5. time of day
w("## 5. Time of day (New York)\n")
b=tr.copy(); b["bucket"]=b.entry_t.apply(lambda t:f"{int(t)//60:02d}:{int(t)%60//15*15:02d}")
t=tb=b.groupby("bucket").apply(agg,include_groups=False)
tbl(t.round(2),"By 15-minute entry bucket")
w("### By how long the trade lasted\n")
h=tr.copy()
h["hold"]=pd.cut(h.bars,[-1,0,2,5,15,1000],labels=["same candle","1-2 min","3-5 min","6-15 min",">15 min"])
tbl(h.groupby("hold",observed=True).apply(agg,include_groups=False).round(2),"Hold time")
# 6. side/size buckets
w("## 6. Direction, stop size, gap size\n")
sd=tr.groupby(tr.side.map({1:"long",-1:"short"})).apply(agg,include_groups=False)
tbl(sd.round(2),"Long vs short")
kk=pd.cut(tr.risk,[3,6,8,10,13,20,200],labels=["4-6 pt","6-8 pt","8-10 pt","10-13 pt","13-20 pt","20+ pt"])
tbl(tr.groupby(kk,observed=True).apply(agg,include_groups=False).round(2),"By stop size (1R in points)")
gg=pd.cut(tr.gap_t,[3,6,10,16,30,500],labels=["4-6 t","6-10 t","10-16 t","16-30 t","30+ t"])
tbl(tr.groupby(gg,observed=True).apply(agg,include_groups=False).round(2),"By gap size (ticks)")
# 7. IS/OOS
w("## 7. In-sample vs out-of-sample (split 2022-12-31)\n")
iso=tr.copy(); iso["period"]=np.where(iso.dt<="2022-12-31","2019-2022 (in-sample)","2023-2026 (out-of-sample)")
tbl(iso.groupby("period").apply(agg,include_groups=False).round(2),"Split")
w("---\n")
# 8. robustness
w("## 8. Robustness checks\n")
w("### 8a. Filter ablation (same rule, filters switched off)\n")
rows=[]
for name,kw in [("No filters at all",dict(q1=False,q2=False,q3=False)),
                ("Only target-size filter (Q1)",dict(q2=False,q3=False)),
                ("Q1 + inversion-volume (Q2)",dict(q3=False)),
                ("Q1 + inversion-speed (Q3)",dict(q2=False)),
                ("ALL THREE (the rule)",dict())]:
    t_=backtest(S,**kw); a=agg(t_)
    rows.append(dict(variant=name,trades=a.trades,win_pct=round(a.win_pct,1),
                     R_per_trade=round(a.R_per_trade,3),PF=round(a.PF,2),
                     usd_1MNQ=round(a.usd_1MNQ,0)))
tbl(pd.DataFrame(rows).set_index("variant"),"Ablation")
w("### 8b. Sensitivity to the target-size cut-off (Q1 threshold, × average daily range)\n")
rows=[]
for q in (0.06,0.07,0.08,0.10,0.12,0.15):
    F.Q1_TGT=q; t_=backtest(S,q2=True,q3=True); a=agg(t_)
    rows.append(dict(threshold=f"{q:.0%} of daily range",trades=a.trades,win_pct=round(a.win_pct,1),
                     R_per_trade=round(a.R_per_trade,3),PF=round(a.PF,2)))
F.Q1_TGT=0.08
tbl(pd.DataFrame(rows).set_index("threshold"),"Target-size threshold")
w("### 8c. Sensitivity to the inversion-volume cut-off (Q2)\n")
rows=[]
for v in (0.8,1.0,1.2,1.5,2.0,99):
    F.Q2_VOL=v; t_=backtest(S,q1=True,q3=True); a=agg(t_)
    rows.append(dict(threshold=("no filter" if v==99 else f"{v:.1f}× median volume"),trades=a.trades,
                     win_pct=round(a.win_pct,1),R_per_trade=round(a.R_per_trade,3),PF=round(a.PF,2)))
F.Q2_VOL=1.2
tbl(pd.DataFrame(rows).set_index("threshold"),"Inversion-volume threshold")
w("### 8d. Sensitivity to the setup cut-off time\n")
rows=[]
for se in (600,615,630,690):
    t_=backtest(S,setup_end=se); a=agg(t_)
    rows.append(dict(last_setup=f"{se//60:02d}:{se%60:02d}",trades=a.trades,win_pct=round(a.win_pct,1),
                     R_per_trade=round(a.R_per_trade,3),PF=round(a.PF,2)))
tbl(pd.DataFrame(rows).set_index("last_setup"),"Setup cut-off")
w("### 8e. Cost sensitivity (round-trip cost per trade)\n")
rows=[]
for c in (0.0,0.5,1.0,2.0,3.0):
    lib.COST_PTS=c; F.COST_PTS=c
    t_=backtest(S); a=agg(t_)
    rows.append(dict(cost_pts=c,trades=a.trades,win_pct=round(a.win_pct,1),
                     R_per_trade=round(a.R_per_trade,3),PF=round(a.PF,2),pts_per_trade=round(a.pts_per_trade,2)))
lib.COST_PTS=1.0; F.COST_PTS=1.0
tbl(pd.DataFrame(rows).set_index("cost_pts"),"Costs")
w("### 8f. What a different target does (same entries, fixed R multiple)\n")
from lib import simulate, DEADLINE
alltr=[]
for s in S:
    t=F.find(s)
    if t is None: continue
    for rr in (1.0,1.5,2.0,2.5,3.0):
        risk=t["risk"]; tgt=t["entry"]+rr*risk*t["side"]
        res="time"; px=s["c"][min(len(s["h"])-1,t["entry_i"])]
        out=None
        for j in range(t["entry_i"],len(s["h"])):
            if s["mod"][j]>DEADLINE: break
            stop_hit=(s["l"][j]<=t["stop"]) if t["side"]==1 else (s["h"][j]>=t["stop"])
            tgt_hit=(s["h"][j]>=tgt) if t["side"]==1 else (s["l"][j]<=tgt)
            if stop_hit: out=("stop",t["stop"]); break
            if j>t["entry_i"] and tgt_hit: out=("target",tgt); break
        if out is None:
            j=min(len(s["h"])-1,len(s["h"])-1); px=s["c"][j]; out=("time",px)
        g=rr if out[0]=="target" else (-1.0 if out[0]=="stop" else (out[1]-t["entry"])*t["side"]/risk)
        alltr.append(dict(date=t["date"],rr=rr,win=out[0]=="target",R=g-lib.COST_PTS/risk))
T=pd.DataFrame(alltr)
rows=[]
for rr,g in T.groupby("rr"):
    rows.append(dict(R_multiple=f"1:{rr:g}",trades=len(g),win_pct=round(100*g.win.mean(),1),
                     R_per_trade=round(g.R.mean(),3),PF=round(g.R[g.R>0].sum()/abs(g.R[g.R<=0].sum()),2)))
tbl(pd.DataFrame(rows).set_index("R_multiple"),"Target multiples (same 318 trades)")
w("---\n")
w("## 9. Every trade\n")
w(f"Full trade-by-trade log: `research/out/trades_final.csv` ({len(tr)} rows).\n")
cols=["date","side","entry_t","entry","stop","risk","outcome","bars","pnl_pts","R","gap_t","inv_lag"]
tt=tr[cols].copy(); tt["side"]=tt.side.map({1:"L",-1:"S"})
tt["entry_t"]=tt.entry_t.map(lambda m:f"{int(m)//60:02d}:{int(m)%60:02d}")
w("First 25 rows:\n")
tt2=tt.head(25).copy()
tt2["date"]=tt2.date.astype(str).str[:10]
w(tt2.to_markdown(index=False,floatfmt=".2f"))
open("research/out/report_tables.md","w").write("\n".join(L))
print("report tables written:", len(L), "lines")
print("\n".join(L[:40]))
