"""All metrics for the multi-timeframe rule, exported to CSV + Excel."""
import numpy as np, pandas as pd, sys, json
sys.path.insert(0,"research/scripts")
from final_mtf import select, RRS, RR_LABEL, CONF
pd.set_option("display.width",260)

MONTHS=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
DOW=["Mon","Tue","Wed","Thu","Fri"]
RRL=[RR_LABEL[r] for r in RRS]

P = pd.read_parquet("research/data/pool_mtf.parquet")
P["dt"]=pd.to_datetime(P.date); P["year"]=P.dt.dt.year; P["month"]=P.dt.dt.month; P["dow"]=P.dt.dt.day_of_week
P["is_is"]=P.date<="2022-12-31"

# ---------------- the primary rule ----------------
TR = select(P, min_conf=2, max_per_day=2, sequential=True)
TR = TR.sort_values(["date","entry_t"]).reset_index(drop=True)
TR["cum_R2"] = TR["R2"].cumsum()
TR["hhmm"]=TR.entry_t.map(lambda m:f"{int(m)//60:02d}:{int(m)%60:02d}")
TR["exit_hhmm"]=TR.exit_t2.map(lambda m:f"{int(m)//60:02d}:{int(m)%60:02d}")
TR["direction"]=TR.side.map({1:"LONG",-1:"SHORT"})
for r in RRS:
    TR[f"pts{r:g}"]=(TR[f"R{r:g}"]+1e-12)*0  # placeholder replaced below
TR["tgt_pts_2"]=2*TR.risk; TR["stop_pts"]=TR.risk

def metrics(g, rr):
    w,R=f"w{rr:g}",f"R{rr:g}"
    n=len(g); wins=int(g[w].sum()); gp=g[R][g[R]>0].sum(); gl=abs(g[R][g[R]<=0].sum())
    return pd.Series({"trades":n,"wins":wins,"losses":n-wins,"win_rate_%":round(100*g[w].mean(),2),
        "R_per_trade":round(g[R].mean(),3),"total_R":round(g[R].sum(),2),
        "profit_factor":round(gp/gl,2) if gl else np.nan,
        "expectancy_gross_R":round(g[R].mean()+ (1.0/g.risk.mean()),3)})

# ---------------- 1. summary at every R:R ----------------
rows=[]
for r in RRS:
    m=metrics(TR,r)
    rows.append(dict(RR=RR_LABEL[r], reward_to_risk=r, trades=int(m.trades), wins=int(m.wins),
        losses=int(m.losses), win_rate_pct=m["win_rate_%"], breakeven_win_pct=round(100/(1+r),1),
        edge_pp=round(m["win_rate_%"]-100/(1+r),1),
        R_per_trade=m.R_per_trade, total_R=m.total_R, profit_factor=m.profit_factor,
        avg_pts_per_trade=round((TR[f"R{r:g}"]*TR.risk).mean(),2),
        total_pts=round((TR[f"R{r:g}"]*TR.risk).sum(),1),
        usd_per_trade_1MNQ=round((TR[f"R{r:g}"]*TR.risk*2-1.24).mean(),2),
        usd_total_1MNQ=round((TR[f"R{r:g}"]*TR.risk*2-1.24).sum(),0),
        usd_per_trade_1NQ=round((TR[f"R{r:g}"]*TR.risk*20-5).mean(),2),
        usd_total_1NQ=round((TR[f"R{r:g}"]*TR.risk*20-5).sum(),0)))
SUMMARY=pd.DataFrame(rows)

# ---------------- 2. win% by year x RR (the headline ask) ----------------
def win_by(by, label):
    out={}
    for r in RRS:
        s=TR.groupby(by)[f"w{r:g}"].apply(lambda x: round(100*x.mean(),1))
        out[RR_LABEL[r]]=s
    d=pd.DataFrame(out)
    d.insert(0,"trades",TR.groupby(by).size())
    return d
BY_YEAR=win_by("year",  "year")
# add R-total per year
RY=pd.DataFrame({RR_LABEL[r]:TR.groupby("year")[f"R{r:g}"].sum().round(1) for r in RRS})
BY_YEAR_R = RY
BY_YEAR.insert(1,"total_R@1:2", RY["1:2"])
BY_MONTH=win_by("month","month"); BY_MONTH.index=[MONTHS[i-1] for i in BY_MONTH.index]
BY_MONTH_R=pd.DataFrame({RR_LABEL[r]:TR.groupby("month")[f"R{r:g}"].sum().round(1) for r in RRS})
BY_MONTH_R.index=[MONTHS[i-1] for i in BY_MONTH_R.index]
BY_DOW=win_by("dow","dow"); BY_DOW.index=[DOW[i] for i in BY_DOW.index]
BY_SIDE=win_by("side","side"); BY_SIDE.index=["SHORT" if i==-1 else "LONG" for i in BY_SIDE.index]
TR["bucket"]=TR.entry_t.apply(lambda t:f"{int(t)//60:02d}:{int(t)%60//15*15:02d}")
BY_TIME=win_by("bucket","bucket")

# ---------------- 3. IS/OOS ----------------
IS=pd.DataFrame({rr: metrics(TR[TR.is_is],r) for rr,r in zip(RRL,RRS)}).T
OOS=pd.DataFrame({rr: metrics(TR[~TR.is_is],r) for rr,r in zip(RRL,RRS)}).T
SPLIT=pd.concat([IS.assign(period="2019-2022 in-sample"),OOS.assign(period="2023-2026 out-of-sample")])

# ---------------- 4. config comparison ----------------
cfg=[]
for mc in (0,1,2,3):
    d=select(P,min_conf=mc,max_per_day=2,sequential=True)
    row=dict(min_confluences=mc, trades=len(d), per_year=round(len(d)/6.8,0))
    for r in RRS: row[f"win%_{RR_LABEL[r]}"]=round(100*d[f"w{r:g}"].mean(),1)
    row["R_per_trade@1:2"]=round(d["R2"].mean(),3)
    row["PF@1:2"]=round(d["R2"][d["R2"]>0].sum()/abs(d["R2"][d["R2"]<=0].sum()),2)
    row["IS_win%_1:2"]=round(100*d[d.is_is]["w2"].mean(),1)
    row["OOS_win%_1:2"]=round(100*d[~d.is_is]["w2"].mean(),1)
    row["positive_years"]=int((d.groupby("year")["R2"].sum()>0).sum())
    cfg.append(row)
CONFIGS=pd.DataFrame(cfg)

# ---------------- 5. confluence study (each confluence alone, on the premium-filtered pool) ----------------
base = P[P.c15_premium==1]
cs=[]
cs.append(dict(confluence="(none - premium filter only)",
               signals=len(base), win_pct_1to2=round(100*base.w2.mean(),1),
               R_1to2=round(base.R2.mean(),3),
               win_pct_1to1=round(100*base.w1.mean(),1)))
for c in CONF+["c3_dir"]:
    d=base[base[c]==1]
    cs.append(dict(confluence=c.replace("c3_","3-min "), signals=len(d),
                   win_pct_1to2=round(100*d.w2.mean(),1), R_1to2=round(d.R2.mean(),3),
                   win_pct_1to1=round(100*d.w1.mean(),1)))
d=base[(base[["c3_body","c3_struct","c3_close_ok","c3_engulf"]].sum(axis=1)>=2)]
cs.append(dict(confluence=">=2 of the four (THE RULE)", signals=len(d),
               win_pct_1to2=round(100*d.w2.mean(),1), R_1to2=round(d.R2.mean(),3),
               win_pct_1to1=round(100*d.w1.mean(),1)))
CONFLUENCE=pd.DataFrame(cs)

# ---------------- 6. trade log ----------------
LOG=pd.DataFrame({
 "date":TR.date, "weekday":TR.dow.map(dict(enumerate(DOW))), "direction":TR.direction,
 "trade_no_of_day":TR.trade_no, "setup_time":TR.setup_t.map(lambda m:f"{int(m)//60:02d}:{int(m)%60:02d}"),
 "entry_time":TR.hhmm, "exit_time_@1:2":TR.exit_hhmm,
 "gap_size_ticks":TR.gap_t, "entry":TR.entry, "stop":TR.stop, "stop_size_pts_1R":TR.risk,
 "target_@1:2":(TR.entry+2*TR.risk*TR.side).round(2),
 "confluences":TR[["c3_body","c3_struct","c3_close_ok","c3_engulf"]].apply(
     lambda r:",".join([n for n,v in zip(["momentum","structure","close-beyond","engulf"],r) if v]),axis=1),
 "conv_15m_premium":TR.c15_premium,
})
for r in RRS:
    LOG[f"outcome_1:{r:g}".replace("1:2.0","1:2").replace("1:1.5","1:1.5").replace("1:1.0","1:1")
        .replace("1:0.75","1:0.75").replace("1:0.667","1:0.67").replace("1:0.5","1:0.5")] = \
        np.where(TR[f"w{r:g}"]==1,"WIN","LOSS")
for r in RRS:
    LOG[f"pts_net_1:{r:g}".replace("1:2.0","1:2").replace("1:1.0","1:1").replace("1:0.667","1:0.67")] = \
        (TR[f"R{r:g}"]*TR.risk).round(2)
LOG["R_net_@1:2"]=TR.R2.round(3)
LOG["cum_R_@1:2"]=TR.cum_R2.round(2)

# ---------------- 7. equity curves ----------------
EQ=pd.DataFrame({RR_LABEL[r]:TR[f"R{r:g}"].cumsum().round(2) for r in RRS})
EQ.insert(0,"trade",np.arange(1,len(TR)+1)); EQ.insert(1,"date",TR.date)

# ---------------- save ----------------
out={}
for name,df in [("SUMMARY",SUMMARY),("BY_YEAR",BY_YEAR.reset_index()),("BY_MONTH",BY_MONTH.reset_index()),
                ("BY_DOW",BY_DOW.reset_index()),("BY_SIDE",BY_SIDE.reset_index()),
                ("BY_TIME",BY_TIME.reset_index()),("SPLIT",SPLIT.reset_index()),
                ("CONFIGS",CONFIGS),("CONFLUENCE",CONFLUENCE),("LOG",LOG),("EQUITY",EQ),
                ("YEAR_R",BY_YEAR_R.reset_index()),("MONTH_R",BY_MONTH_R.reset_index())]:
    df.to_csv(f"research/out/mtf_{name}.csv",index=False); out[name]=df
TR.to_parquet("research/data/trades_mtf.parquet")
print("PRIMARY RULE  (15m premium + >=2 of 4 3-min confluences, max 2 trades/day)")
print(f"trades={len(TR)}  ({len(TR)/6.8:.0f}/yr)  days={TR.date.nunique()}")
print("\n=== summary by R:R ===")
print(SUMMARY[["RR","trades","win_rate_pct","breakeven_win_pct","edge_pp","R_per_trade","total_R","profit_factor","avg_pts_per_trade","usd_per_trade_1MNQ"]].to_string(index=False))
print("\n=== win% by YEAR x R:R ===");  print(BY_YEAR.to_string())
print("\n=== total R by YEAR x R:R ==="); print(BY_YEAR_R.to_string())
print("\n=== win% by MONTH x R:R ==="); print(BY_MONTH.to_string())
print("\n=== win% by WEEKDAY x R:R ==="); print(BY_DOW.to_string())
print("\n=== win% by SIDE x R:R ==="); print(BY_SIDE.to_string())
print("\n=== in-sample vs out-of-sample ==="); print(SPLIT[["period","trades","win_rate_%","R_per_trade","profit_factor"]].to_string())
print("\n=== config comparison ==="); print(CONFIGS.to_string(index=False))
print("\n=== confluence study ==="); print(CONFLUENCE.to_string(index=False))

# ---------------- 8. gross vs net, and cost sensitivity ----------------
def gross_R(rr):
    return np.where(TR[f"w{rr:g}"]==1, rr, np.where(TR[f"outcome_{rr:g}"]=="stop" if f"outcome_{rr:g}" in TR else True, 0,0))
GROSS=[]
for r in RRS:
    gw = np.where(TR[f"w{r:g}"]==1, r, -1.0)          # gross (no cost) R per trade
    net = TR[f"R{r:g}"]                                 # net of 1 pt
    GROSS.append(dict(RR=RR_LABEL[r], win_rate_pct=round(100*TR[f"w{r:g}"].mean(),1),
        gross_R_per_trade=round(gw.mean(),3), cost_R_per_trade=round((net-gw).mean(),3),
        net_R_per_trade=round(net.mean(),3),
        gross_total_R=round(gw.sum(),1), net_total_R=round(net.sum(),1)))
GROSS=pd.DataFrame(GROSS)

COSTS=[]
for c in (0.0,0.5,1.0,1.5,2.0,3.0):
    row=dict(round_trip_cost_pts=c)
    for r in RRS:
        gw = np.where(TR[f"w{r:g}"]==1, r, -1.0)
        netR = gw - c/TR.risk
        row[f"R_per_trade_{RR_LABEL[r]}"]=round(netR.mean(),3)
        row[f"total_R_{RR_LABEL[r]}"]=round(netR.sum(),1)
    COSTS.append(row)
COSTS=pd.DataFrame(COSTS)

# trades per day distribution
tpd=TR.groupby("date").size().value_counts().sort_index()
TPD=pd.DataFrame({"trades_in_that_day":tpd.index,"number_of_days":tpd.values})
BASELINE={"raw IFVG signals (all)":len(P), "raw win% @1:2":round(100*P.w2.mean(),1)}
TR.to_csv("research/out/mtf_PRIMARY.csv",index=False)
GROSS.to_csv("research/out/mtf_GROSS.csv",index=False)
COSTS.to_csv("research/out/mtf_COSTS.csv",index=False)
TPD.to_csv("research/out/mtf_TRADES_PER_DAY.csv",index=False)
print("\n=== gross vs net (win% unchanged, the cost eats low-R:R targets) ===")
print(GROSS.to_string(index=False))
print("\n=== cost sensitivity (R per trade) ==="); print(COSTS.to_string(index=False))
print("\n=== trades per day ==="); print(TPD.to_string(index=False))
