"""Build the deliverable workbook: research/out/IFVG_MTF_NQ.xlsx"""
import pandas as pd, numpy as np, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT="research/out/IFVG_MTF_NQ.xlsx"
C=lambda n: pd.read_csv(f"research/out/mtf_{n}.csv")
SUMMARY, BY_YEAR, BY_MONTH = C("SUMMARY"), C("BY_YEAR"), C("BY_MONTH")
BY_DOW, BY_SIDE, BY_TIME   = C("BY_DOW"), C("BY_SIDE"), C("BY_TIME")
SPLIT, CONFIGS, CONFLUENCE = C("SPLIT"), C("CONFIGS"), C("CONFLUENCE")
LOG, EQUITY, GROSS, COSTS   = C("LOG"), C("EQUITY"), C("GROSS"), C("COSTS")
YEAR_R, MONTH_R, TPD        = C("YEAR_R"), C("MONTH_R"), C("TRADES_PER_DAY")

TITLE_F=Font(bold=True,size=14,color="1F3864")
SUB_F=Font(italic=True,size=9,color="555555")
HEAD_F=Font(bold=True,color="FFFFFF",size=10)
HEAD_FILL=PatternFill("solid",fgColor="1F3864")
ALT_FILL=PatternFill("solid",fgColor="EEF2FA")
GOOD_FILL=PatternFill("solid",fgColor="D6F0E0")
BAD_FILL=PatternFill("solid",fgColor="FADBDB")
thin=Side(style="thin",color="D0D0D0")
BORDER=Border(left=thin,right=thin,top=thin,bottom=thin)

wb=Workbook(); wb.remove(wb.active)

def sheet(name, df, title, subtitle="", widths=None, pct_cols=(), r_cols=(), stoplight=None, freeze="A4"):
    ws=wb.create_sheet(name[:31])
    ws["A1"]=title; ws["A1"].font=TITLE_F
    if subtitle: ws["A2"]=subtitle; ws["A2"].font=SUB_F
    r0=4
    for j,col in enumerate(df.columns,start=1):
        cell=ws.cell(row=r0,column=j,value=str(col))
        cell.font=HEAD_F; cell.fill=HEAD_FILL; cell.border=BORDER
        cell.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
    for i,row in df.iterrows():
        rr=r0+1+i
        for j,col in enumerate(df.columns,start=1):
            v=row[col]
            if isinstance(v,(np.floating,float)) and (np.isnan(v) if isinstance(v,float) else False): v=None
            if isinstance(v,(np.integer,)): v=int(v)
            if isinstance(v,(np.floating,)): v=float(v)
            cell=ws.cell(row=rr,column=j,value=v)
            cell.border=BORDER
            if i%2==1: cell.fill=ALT_FILL
            if col in pct_cols: cell.number_format="0.0"
            elif col in r_cols: cell.number_format="+0.00;-0.00"
            else: cell.number_format="General"
            if stoplight and col in stoplight:
                try: val=float(v)
                except: val=None
                if val is not None:
                    cell.fill = GOOD_FILL if val>=stoplight[col] else BAD_FILL
    for j,col in enumerate(df.columns,start=1):
        L=get_column_letter(j)
        w = (widths or {}).get(col)
        if w is None:
            m=max([len(str(col))]+[len(f"{v}") for v in df[col].head(200)])
            w=min(max(9,m+2),34)
        ws.column_dimensions[L].width=w
    ws.freeze_panes=freeze
    ws.row_dimensions[r0].height=30
    return ws

# ---------------- 0. README ----------------
ws=wb.create_sheet("README")
lines=[
 ("THE MORNING IFVG + 3-MIN / 15-MIN CONFLUENCES","title"),
 ("Nasdaq-100 futures (MNQ / NQ) · 1-minute candles · 09:30-10:00 New York · max 2 trades per day","sub"),
 ("","" ),
 ("WHAT THIS WORKBOOK IS","h"),
 ("Every number in this workbook comes from a backtest of one rule over 1,493 sessions of CME MNQ 1-minute data,",""),
 ("May 2019 to Feb 2026. All times are New York. Every result is AFTER a 1.00 point round-trip cost",""),
 ("(1 tick spread + 3 ticks commission/slippage) charged to every single trade.",""),
 ("","" ),
 ("THE RULE IN ONE PARAGRAPH","h"),
 ("1. Find a 1-minute Fair Value Gap (FVG): candle1.high < candle3.low (bullish hole) or candle1.low > candle3.high",""),
 ("   (bearish hole). Minimum size 4 ticks.",""),
 ("2. Wait for a candle to CLOSE fully through the far side of that hole - the hole is now an IFVG (inverted gap).",""),
 ("   This must happen within 10 candles of the hole forming. The inverting candle's volume must be <= 1.2x the",""),
 ("   median volume of the first 20 candles of the session.",""),
 ("3. The 15-MINUTE confluence: at the moment your limit order fills, price must be in the UPPER half of the",""),
 ("   15-minute candle that is still forming (for a short) or the LOWER half (for a long). Sell premium / buy discount.",""),
 ("4. At least TWO of these four 3-MINUTE confluences must be true on the last COMPLETED 3-minute candle:",""),
 ("      momentum  - the 3-min candle is in your direction with a body >= 50% of its range",""),
 ("      structure - it makes a lower high AND lower low (short) / higher high AND higher low (long)",""),
 ("      close-beyond - it closes beyond the edge of the inverted gap",""),
 ("      engulf    - it engulfs the previous 3-min candle (open above/below the previous close, close beyond)",""),
 ("5. Entry = limit at the edge of the inverted gap. Stop = 2 ticks beyond the other edge. Target = your chosen R:R.",""),
 ("6. At most 2 trades per day, and a new trade only starts after the previous one is closed.",""),
 ("","" ),
 ("THE MOST IMPORTANT SHEETS","h"),
 ("WinRate_By_Year     -> win rate at 1:2, 1:1.5, 1:1, 1:0.75, 1:0.67, 1:0.5 for every year (green >= 50%)",""),
 ("Summary_By_RR       -> headline metrics for each R:R target",""),
 ("Gross_vs_Net        -> why the 1:0.5 and 1:0.67 targets barely work: cost eats them",""),
 ("Confluence_Study    -> what each individual 1-min / 3-min / 15-min confluence is worth",""),
 ("Trade_Log           -> all 159 trades, with the WIN/LOSS outcome at every R:R",""),
 ("","" ),
 ("HONEST CAVEATS - PLEASE READ","h"),
 ("* The data covers 6.8 years, not 10. Free 1-minute NQ/MNQ history does not go back further.",""),
 ("* The source data is missing Oct-Nov 2023, so those columns look thin.",""),
 ("* 159 trades over 6.8 years is a small sample: per-year win rates on 4-34 trades are noisy.",""),
 ("* A limit fill is assumed when price touches the level; on the entry candle only the stop side is checked, so no",""),
 ("  trade is ever given credit for hitting its target in the same candle it was filled.",""),
 ("* The rule was built on 2019-2022 and checked unchanged on 2023-2026 (see InSample_vs_OutSample).",""),
 ("* Low R:R targets (1:0.5, 1:0.67) show a high win rate but almost no profit after costs. Win rate alone is not edge.",""),
 ("* This is research, not investment advice.",""),
]
for i,(t,st) in enumerate(lines,start=1):
    c=ws.cell(row=i,column=1,value=t)
    if st=="title": c.font=TITLE_F
    elif st=="sub": c.font=SUB_F
    elif st=="h": c.font=Font(bold=True,size=11,color="1F3864")
ws.column_dimensions["A"].width=125

# ---------------- 1. Summary ----------------
sheet("Summary_By_RR", SUMMARY,
      "HEADLINE RESULTS BY TARGET (R:R)",
      "159 trades, May 2019 - Feb 2026, net of 1.00 point round-trip cost. 'edge_pp' = win rate minus break-even win rate.",
      widths={"RR":8,"trades":8,"wins":7,"losses":7,"win_rate_pct":11,"breakeven_win_pct":12,"edge_pp":9,
              "R_per_trade":11,"total_R":9,"profit_factor":10,"avg_pts_per_trade":12,"total_pts":9,
              "usd_per_trade_1MNQ":12,"usd_total_1MNQ":12,"usd_per_trade_1NQ":12,"usd_total_1NQ":12},
      pct_cols=("win_rate_pct","breakeven_win_pct","edge_pp"), r_cols=("R_per_trade",),
      stoplight={"win_rate_pct":50})

# ---------------- 2. Win rate by year ----------------
sheet("WinRate_By_Year", BY_YEAR,
      "WIN RATE (%) BY YEAR FOR EVERY TARGET  <-- the main answer",
      "Green = 50% or better. Remember the break-even win rate: 1:2 needs 33.3%, 1:1.5 needs 40%, 1:1 needs 50%, "
      "1:0.75 needs 57.1%, 1:0.67 needs 60%, 1:0.5 needs 66.7%.",
      widths={"year":8,"trades":8,"total_R@1:2":11}, pct_cols=("1:2","1:1.5","1:1","1:0.75","1:0.67","1:0.5"),
      stoplight={"1:2":50,"1:1.5":50,"1:1":50,"1:0.75":57.1,"1:0.67":60,"1:0.5":66.7})
sheet("TotalR_By_Year", YEAR_R, "TOTAL R BY YEAR FOR EVERY TARGET",
      "Negative years in red. 2019 = May-Dec only, 2026 = Jan 1 - Feb 18 only.",
      widths={"year":8}, r_cols=("1:2","1:1.5","1:1","1:0.75","1:0.67","1:0.5"),
      stoplight={"1:2":0,"1:1.5":0,"1:1":0,"1:0.75":0,"1:0.67":0,"1:0.5":0})

# ---------------- 3. month / dow / side / time ----------------
sheet("WinRate_By_Month", BY_MONTH, "WIN RATE (%) BY MONTH, ALL YEARS POOLED",
      "Break-even win rates as above. Oct/Nov counts are low because the source data is missing those months in 2023.",
      widths={"month":9,"trades":8}, pct_cols=("1:2","1:1.5","1:1","1:0.75","1:0.67","1:0.5"),
      stoplight={"1:2":50,"1:1.5":50,"1:1":50})
sheet("TotalR_By_Month", MONTH_R, "TOTAL R BY MONTH, ALL YEARS POOLED",
      widths={"month":9}, r_cols=("1:2","1:1.5","1:1","1:0.75","1:0.67","1:0.5"))
sheet("WinRate_By_Weekday", BY_DOW, "WIN RATE (%) BY WEEKDAY",
      widths={"dow":9,"trades":8}, pct_cols=("1:2","1:1.5","1:1","1:0.75","1:0.67","1:0.5"),
      stoplight={"1:2":50,"1:1.5":50,"1:1":50})
sheet("WinRate_By_Side", BY_SIDE, "WIN RATE (%) BY DIRECTION",
      widths={"side":9,"trades":8}, pct_cols=("1:2","1:1.5","1:1","1:0.75","1:0.67","1:0.5"),
      stoplight={"1:2":50,"1:1.5":50,"1:1":50})
sheet("WinRate_By_Time", BY_TIME, "WIN RATE (%) BY ENTRY TIME (15-minute buckets, New York)",
      widths={"bucket":10,"trades":8}, pct_cols=("1:2","1:1.5","1:1","1:0.75","1:0.67","1:0.5"),
      stoplight={"1:2":50,"1:1.5":50,"1:1":50})

# ---------------- 4. IS/OOS + robustness ----------------
sheet("InSample_vs_OutSample", SPLIT.reset_index().rename(columns={"index":"R:R"}),
      "IN-SAMPLE vs OUT-OF-SAMPLE",
      "The rule was designed on 2019-2022 and then run unchanged on 2023-2026.",
      widths={"R:R":9,"period":24,"trades":8,"wins":7,"losses":7,"win_rate_%":11,"R_per_trade":11,"total_R":9,"profit_factor":11},
      pct_cols=("win_rate_%",), r_cols=("R_per_trade",))
sheet("Gross_vs_Net", GROSS, "GROSS vs NET: WHAT THE 1.00-POINT COST DOES",
      "Win rate is the same gross and net. The R column is where the cost shows up - and it decides whether a low "
      "R:R target is tradeable at all.",
      widths={"RR":8,"win_rate_pct":11,"gross_R_per_trade":14,"cost_R_per_trade":14,"net_R_per_trade":14,
              "gross_total_R":12,"net_total_R":12}, pct_cols=("win_rate_pct",),
      r_cols=("gross_R_per_trade","cost_R_per_trade","net_R_per_trade"),
      stoplight={"net_R_per_trade":0})
sheet("Cost_Sensitivity", COSTS, "COST SENSITIVITY: R PER TRADE AT DIFFERENT ROUND-TRIP COSTS",
      "Rows = assumed round-trip cost in index points. This pattern is a scalp, so friction matters.",
      widths={"round_trip_cost_pts":14}, r_cols=tuple([c for c in COSTS.columns if c.startswith("R_per_trade")]))

# ---------------- 5. confluence + configs ----------------
sheet("Confluence_Study", CONFLUENCE, "WHAT EACH CONFLUENCE IS WORTH (win% at 1:2, on the premium-filtered pool)",
      "All measured on signals that already passed the 15-min premium filter, so the 'none' row is the baseline "
      "this workbook's rule starts from.",
      widths={"confluence":28,"signals":9,"win_pct_1to2":12,"R_1to2":10,"win_pct_1to1":12},
      pct_cols=("win_pct_1to2","win_pct_1to1"), r_cols=("R_1to2",), stoplight={"win_pct_1to2":50})
sheet("Config_Comparison", CONFIGS, "HOW MANY CONFLUENCES TO REQUIRE  (all with max 2 trades/day)",
      "min_confluences = how many of the four 3-min confluences are demanded. 2 is the rule used in this workbook.",
      widths={"min_confluences":15,"trades":8,"per_year":9,"R_per_trade@1:2":14,"PF@1:2":8,
              "IS_win%_1:2":11,"OOS_win%_1:2":12,"positive_years":13})
sheet("Trades_Per_Day", TPD, "HOW OFTEN THE 2-PER-DAY CAP IS USED",
      "Most qualifying days produce exactly one trade.", widths={"trades_in_that_day":17,"number_of_days":14})

# ---------------- 6. trade log + equity ----------------
for c in LOG.columns:
    if c.startswith("outcome"): LOG[c]=LOG[c].astype(str)
sheet("Trade_Log", LOG, "EVERY TRADE (159 rows) WITH ITS OUTCOME AT EVERY TARGET",
      "Entry/stop/target are index points. 'confluences' lists which 3-min confluences were present. "
      "pts_net_* is net of the 1 point cost.",
      widths={"date":11,"weekday":8,"direction":9,"trade_no_of_day":9,"setup_time":9,"entry_time":9,
              "exit_time_@1:2":10,"gap_size_ticks":9,"entry":10,"stop":10,"stop_size_pts_1R":10,
              "target_@1:2":11,"confluences":40,"conv_15m_premium":11}, freeze="C5")
sheet("Equity_Curves", EQUITY, "CUMULATIVE R FOR EACH TARGET (1 R = the risk of that trade)",
      "Trade number on the x-axis.", widths={"trade":7,"date":11},
      r_cols=("1:2","1:1.5","1:0.5"))

wb.save(OUT)
print("saved", OUT, os.path.getsize(OUT)//1024, "KB,", len(wb.sheetnames), "sheets")
print(wb.sheetnames)
