"""Every number for the final wide-stop rule -> research/out/mtf3_*.csv + trade log parquet."""
import pandas as pd, numpy as np, sys, pickle
sys.path.insert(0,"research/scripts")
from final_mtf3 import rule, table, RRS, RR_LABEL, CONF3
from lib import COST_PTS

MONTHS=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
DOW=["Mon","Tue","Wed","Thu","Fri"]
RRL=[RR_LABEL[r] for r in RRS]

P=pd.read_parquet("research/data/pool_mtf3.parquet")
d=rule(P, stop_max=20.0)
d["year"]=d.date.str[:4]; d["month"]=pd.to_datetime(d.date).dt.month
d["dow"]=pd.to_datetime(d.date).dt.day_of_week
d=d.sort_values(["date","entry_t"]).reset_index(drop=True)
d["cum_R2"]=d.R2.cumsum()

def m(g):
    out=dict(trades=len(g))
    for r in RRS:
        w,R=g[f"w{r:g}"],g[f"R{r:g}"]
        gp,gl=R[R>0].sum(),abs(R[R<=0].sum())
        out[f"win%_{RR_LABEL[r]}"]=round(100*w.mean(),1)
        out[f"R_{RR_LABEL[r]}"]=round(R.mean(),3)
        out[f"PF_{RR_LABEL[r]}"]=round(gp/gl,2) if gl else np.nan
    return pd.Series(out)

# ---- 1 summary ----
SUMMARY=table(d)
SUMMARY["usd_total_1NQ"]=[round(((d[f"R{r:g}"]*d.risk)*20-5).sum(),0) for r in RRS]
SUMMARY["usd_total_1MNQ"]=[round(((d[f"R{r:g}"]*d.risk)*2-1.24).sum(),0) for r in RRS]

# ---- 2 by year ----
BY_YEAR=pd.DataFrame({f"win%_{RR_LABEL[r]}":d.groupby("year")[f"w{r:g}"].mean().mul(100).round(1) for r in RRS})
BY_YEAR.insert(0,"trades",d.groupby("year").size())
BY_YEAR.insert(1,"total_R_1:2",d.groupby("year")["R2"].sum().round(1))
RY=pd.DataFrame({RR_LABEL[r]:d.groupby("year")[f"R{r:g}"].sum().round(1) for r in RRS})
# ---- 3 other breakdowns ----
BY_MONTH=pd.DataFrame({f"win%_{RR_LABEL[r]}":d.groupby("month")[f"w{r:g}"].mean().mul(100).round(1) for r in RRS})
BY_MONTH.insert(0,"trades",d.groupby("month").size())
BY_MONTH.index.name="month"
BY_MONTH.index=[MONTHS[i-1] for i in BY_MONTH.index]
BY_DOW=pd.DataFrame({f"win%_{RR_LABEL[r]}":d.groupby("dow")[f"w{r:g}"].mean().mul(100).round(1) for r in RRS})
BY_DOW.insert(0,"trades",d.groupby("dow").size())
BY_DOW.index=[DOW[i] for i in BY_DOW.index]; BY_DOW.index.name="weekday"
BY_SIDE=pd.DataFrame({f"win%_{RR_LABEL[r]}":d.groupby("side")[f"w{r:g}"].mean().mul(100).round(1) for r in RRS})
BY_SIDE.insert(0,"trades",d.groupby("side").size())
BY_SIDE.index=["SHORT" if i==-1 else "LONG" for i in BY_SIDE.index]; BY_SIDE.index.name="direction"
d["entry_half"]=d.entry_t.map(lambda t:f"{int(t)//60:02d}:{int(t)%60//15*15:02d}")
BY_TIME=pd.DataFrame({f"win%_{RR_LABEL[r]}":d.groupby("entry_half")[f"w{r:g}"].mean().mul(100).round(1) for r in RRS})
BY_TIME.insert(0,"trades",d.groupby("entry_half").size()); BY_TIME.index.name="entry_time"
d["stop_bucket"]=pd.cut(d.risk,[10,12,15,17,20],include_lowest=True).astype(str)
BY_STOP=pd.DataFrame({f"win%_{RR_LABEL[r]}":d.groupby("stop_bucket")[f"w{r:g}"].mean().mul(100).round(1) for r in RRS})
BY_STOP.insert(0,"trades",d.groupby("stop_bucket").size()); BY_STOP.index.name="stop_size"

# ---- 4 IS / OOS ----
def half(g,label):
    s=m(g); s["period"]=label; s["trades"]=len(g); return s
SPLIT=pd.DataFrame([half(d[d.is_is],"2019-2022 IN-SAMPLE"), half(d[~d.is_is],"2023-2026 OUT-OF-SAMPLE")])
SPLIT=SPLIT[["period","trades"]+[c for c in SPLIT.columns if c not in ("period","trades")]]

# ---- 5 confluences (measured on the structural base, BEFORE the 2-of-3 filter) ----
for c in CONF3: P[c]=P[c].fillna(0).astype(int)
B=P[(P.setup_t<=600)&(P.risk<=20)&(P.entry_t<=12*60)].copy()
B["score"]=B[CONF3].sum(axis=1)
CONF=[]
CONF.append(dict(condition="no confluence required (structural filters only)", trades=len(B),
                 win_pct_1to2=round(100*B.w2.mean(),1), R_1to2=round(B.R2.mean(),3)))
for c,name in [("c3_body","3m: big body on the last completed 3-min candle"),
               ("c15_premium","15m: price on the premium/discount side of the forming 15-min candle"),
               ("al_open","1h: price on the trade side of the 09:30 open (1-hour candle direction)")]:
    g=B[B[c]==1]
    CONF.append(dict(condition=f"with {name}", trades=len(g),
                     win_pct_1to2=round(100*g.w2.mean(),1), R_1to2=round(g.R2.mean(),3)))
for k,lab in [(1,"at least 1 of the 3"),(2,"at least 2 of the 3  <-- THE RULE"),(3,"all 3 of 3")]:
    g=B[B.score>=k]
    CONF.append(dict(condition=lab, trades=len(g), win_pct_1to2=round(100*g.w2.mean(),1),
                     R_1to2=round(g.R2.mean(),3)))
CONF=pd.DataFrame(CONF)

# ---- 6 sensitivity ----
SENS=[]
for sm in (12,13,15,17,20,25,30):
    g=rule(P,stop_max=float(sm))
    SENS.append(dict(stop_range=f"10-{sm} pts", trades=len(g), per_year=round(len(g)/6.8,1),
        win_pct_1to2=round(100*g.w2.mean(),1), R_1to2=round(g.R2.mean(),3),
        is_win=round(100*g[g.is_is].w2.mean(),1), oos_win=round(100*g[~g.is_is].w2.mean(),1)))
for s0,lab in [(600,"inversion by 10:00 (used)"),(615,"inversion by 10:15"),(630,"inversion by 10:30")]:
    g=rule(P,stop_max=20.0,setup_end=s0)
    SENS.append(dict(stop_range=lab, trades=len(g), per_year=round(len(g)/6.8,1),
        win_pct_1to2=round(100*g.w2.mean(),1), R_1to2=round(g.R2.mean(),3),
        is_win=round(100*g[g.is_is].w2.mean(),1), oos_win=round(100*g[~g.is_is].w2.mean(),1)))
SENS=pd.DataFrame(SENS)

# ---- 7 gross vs net + cost ----
GROSS=[]
for r in RRS:
    gw=np.where(d[f"w{r:g}"]==1, r, -1.0); net=d[f"R{r:g}"]
    GROSS.append(dict(RR=RR_LABEL[r], win_pct=round(100*d[f"w{r:g}"].mean(),1),
        gross_R=round(gw.mean(),3), cost_R=round((net-gw).mean(),3), net_R=round(net.mean(),3),
        gross_total_R=round(gw.sum(),1), net_total_R=round(net.sum(),1)))
GROSS=pd.DataFrame(GROSS)
COSTS=[]
for c in (0,0.5,1.0,1.5,2.0,3.0):
    row=dict(round_trip_cost_pts=c)
    for r in RRS:
        gw=np.where(d[f"w{r:g}"]==1, r, -1.0); row[RR_LABEL[r]]=round((gw-c/d.risk).mean(),3)
    COSTS.append(row)
COSTS=pd.DataFrame(COSTS)

# ---- 8 stats ----
cumR=d.R2.cumsum(); dd=(cumR-cumR.cummax()).min()
streak=best_streak=0
for w in d.w2:
    streak = streak+1 if w==0 else 0
    best_streak=max(best_streak,streak)
STATS=pd.DataFrame([
 dict(metric="trades",value=len(d)),
 dict(metric="trading days used",value=d.date.nunique()),
 dict(metric="trades per year",value=round(len(d)/6.8,1)),
 dict(metric="period",value=f"{d.date.min()} to {d.date.max()}"),
 dict(metric="median stop (1R, points)",value=round(d.risk.median(),2)),
 dict(metric="average stop (1R, points)",value=round(d.risk.mean(),2)),
 dict(metric="average time in trade (minutes)",value=round((d.exit_t2-d.entry_i*0+d.xbar2*0).pipe(lambda x:(d["exit_t2"]-d.entry_t).mean()),1)),
 dict(metric="max drawdown (R, at 1:2)",value=round(dd,2)),
 dict(metric="longest losing streak (at 1:2)",value=int(best_streak)),
 dict(metric="total R at 1:2",value=round(d.R2.sum(),1)),
 dict(metric="largest win (points)",value=round((d.R2*d.risk).max(),1)),
 dict(metric="largest loss (points)",value=round((d.R2*d.risk).min(),1)),
 dict(metric="trades taken on 2-signal days",value=int((d.groupby('date').size()==2).sum())),
])

EQ=pd.DataFrame({RR_LABEL[r]:d[f"R{r:g}"].cumsum().round(2) for r in RRS})
EQ.insert(0,"trade",np.arange(1,len(d)+1)); EQ.insert(1,"date",d.date)

LOG=pd.DataFrame({
 "date":d.date, "weekday":d.dow.map(dict(enumerate(DOW))), "direction":d.side.map({1:"LONG",-1:"SHORT"}),
 "trade_no_of_day":d.trade_no, "inversion_time":d.setup_t.map(lambda t:f"{int(t)//60:02d}:{int(t)%60:02d}"),
 "entry_time":d.entry_t.map(lambda t:f"{int(t)//60:02d}:{int(t)%60:02d}"),
 "gap_size_pts":(d.gap_t/4).round(2),
 "entry":d.entry.round(2), "stop":d.stop.round(2), "stop_size_pts_1R":d.risk.round(2),
 "target_1to2":(d.entry+2*(d.entry-d.stop)).where(d.side==1,(d.entry-2*(d.stop-d.entry))).round(2),
 "conf_3m_body":d.c3_body, "conf_15m_premium":d.c15_premium, "conf_1h_direction":d.al_open,
 "confluences_count":d.score,
})
for r in RRS:
    LOG[f"result_1:{r:g}".replace("1:2","1:2").replace("1:1.5","1:1.5").replace("1:1","1:1")
        .replace("1:0.75","1:0.75").replace("1:0.667","1:0.67").replace("1:0.5","1:0.5")] = \
        np.where(d[f"w{r:g}"]==1,"WIN","LOSS")
for r in RRS:
    LOG[f"pts_net_1:{r:g}".replace("1:2","1:2").replace("1:1","1:1").replace("1:0.667","1:0.67")] = \
        ((d[f"R{r:g}"]*d.risk)).round(2)
LOG["R_net_1to2"]=d.R2.round(3)
LOG["cum_R_1to2"]=d.cum_R2.round(1)

for name,df in [("SUMMARY",SUMMARY),("BY_YEAR",BY_YEAR.reset_index()),("YEAR_R",RY.reset_index()),
                ("BY_MONTH",BY_MONTH.reset_index()),("BY_DOW",BY_DOW.reset_index()),
                ("BY_SIDE",BY_SIDE.reset_index()),("BY_TIME",BY_TIME.reset_index()),
                ("BY_STOP",BY_STOP.reset_index()),("SPLIT",SPLIT.reset_index(drop=True)),
                ("CONFLUENCE",CONF),("SENS",SENS),("GROSS",GROSS),("COSTS",COSTS),
                ("STATS",STATS),("LOG",LOG),("EQUITY",EQ)]:
    df.to_csv(f"research/out/mtf3_{name}.csv",index=False)
d.to_parquet("research/data/trades_mtf3.parquet")
pd.set_option("display.width",250)
print(f"trades={len(d)} days={d.date.nunique()} ({len(d)/6.8:.1f}/yr)")
print("\n=== by R:R ==="); print(SUMMARY[["RR","trades","wins","win_pct","R_per_trade","total_R","profit_factor","pts_per_trade","usd_per_trade_1NQ"]].to_string(index=False))
print("\n=== by year ==="); print(BY_YEAR.to_string())
print("\n=== total R by year ==="); print(RY.to_string())
print("\n=== IS/OOS ==="); print(SPLIT[["period","trades","win%_1:2","R_1:2","PF_1:2"]].to_string(index=False))
print("\n=== confluences ==="); print(CONF.to_string(index=False))
print("\n=== sensitivity ==="); print(SENS.to_string(index=False))
print("\n=== by weekday ==="); print(BY_DOW.to_string())
print("\n=== by side ==="); print(BY_SIDE.to_string())
print("\n=== by entry time ==="); print(BY_TIME.to_string())
print("\n=== by stop size ==="); print(BY_STOP.to_string())
print("\n=== by month ==="); print(BY_MONTH.to_string())
print("\n=== stats ==="); print(STATS.to_string(index=False))
print("\n=== costs ==="); print(COSTS.to_string(index=False))
