"""Build the deliverable: research/deliverables/IFVG_WIDE_STOP_1SHEET.xlsx (all-in-one tab + trade log)."""
import pandas as pd, numpy as np, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side as BS
from openpyxl.utils import get_column_letter

OUT="research/deliverables/IFVG_WIDE_STOP_1SHEET.xlsx"
os.makedirs("research/deliverables",exist_ok=True)
C=lambda n: pd.read_csv(f"research/out/mtf3_{n}.csv")
SUMMARY,BY_YEAR,YEAR_R,BY_MONTH,BY_DOW,BY_SIDE,BY_TIME,BY_STOP=C("SUMMARY"),C("BY_YEAR"),C("YEAR_R"),C("BY_MONTH"),C("BY_DOW"),C("BY_SIDE"),C("BY_TIME"),C("BY_STOP")
SPLIT,CONF,SENS,GROSS,COSTS,STATS,LOG,EQ=C("SPLIT"),C("CONFLUENCE"),C("SENS"),C("GROSS"),C("COSTS"),C("STATS"),C("LOG"),C("EQUITY")

TITLE=Font(bold=True,size=15,color="1F3864")
H1=Font(bold=True,size=12,color="FFFFFF")
H2=Font(bold=True,size=10.5,color="1F3864")
BOLD=Font(bold=True,size=10)
SMALL=Font(italic=True,size=9,color="555555")
FILL_H=PatternFill("solid",fgColor="1F3864")
FILL_SEC=PatternFill("solid",fgColor="D9E2F3")
FILL_GOOD=PatternFill("solid",fgColor="D5F0DC")
FILL_BAD=PatternFill("solid",fgColor="FADBDB")
FILL_KEY=PatternFill("solid",fgColor="FFF2CC")
thin=BS(style="thin",color="C8C8C8")
BORD=Border(left=thin,right=thin,top=thin,bottom=thin)

wb=Workbook(); ws=wb.active; ws.title="ALL-IN-ONE"
r=1
def put(row_vals, font=None, fill=None, fmt=None, bold_first=False):
    global r
    for j,v in enumerate(row_vals,start=1):
        c=ws.cell(row=r,column=j,value=v)
        if font: c.font=font
        if fill: c.fill=fill
        c.border=BORD
        if fmt and isinstance(v,(int,float)): c.number_format=fmt
        if bold_first and j==1: c.font=BOLD
    r+=1
def blank(n=1):
    global r
    r+=n
def section(title, note=""):
    global r
    c=ws.cell(row=r,column=1,value=title); c.font=H2; c.fill=FILL_SEC
    for j in range(2,14): ws.cell(row=r,column=j).fill=FILL_SEC
    r+=1
    if note:
        c=ws.cell(row=r,column=1,value=note); c.font=SMALL; r+=1
def df_block(df, pct_cols=(), r_cols=(), num_cols=(), key_rows=(), green_ge=None, red_lt=None):
    global r
    put(list(df.columns), font=H1, fill=FILL_H)
    for i,(_,row) in enumerate(df.iterrows()):
        vals=[]
        for c in df.columns:
            v=row[c]
            if isinstance(v,(np.floating,float)) and (np.isnan(v) if isinstance(v,float) else False): v=None
            if isinstance(v,(np.integer,)): v=int(v)
            if isinstance(v,(np.floating,)): v=float(v)
            vals.append(v)
        f=None
        if i in key_rows: f=FILL_KEY
        put(vals, fill=f)
        # formats
        for j,c in enumerate(df.columns,start=1):
            cell=ws.cell(row=r-1,column=j)
            if c in pct_cols: cell.number_format="0.0"
            elif c in r_cols: cell.number_format="+0.00;-0.00"
            elif c in num_cols: cell.number_format="0.00"
            if green_ge is not None and c in pct_cols and isinstance(cell.value,(int,float)):
                cell.fill = FILL_GOOD if cell.value>=green_ge else FILL_BAD
            if red_lt is not None and c in r_cols and isinstance(cell.value,(int,float)):
                cell.fill = FILL_BAD if cell.value<red_lt else FILL_GOOD

# ---------------- header ----------------
c=ws.cell(row=r,column=1,value="MORNING IFVG  --  WIDE STOP (10+ points), 09:45-12:00 New York"); c.font=TITLE; r+=1
c=ws.cell(row=r,column=1,value="Nasdaq-100 futures (NQ / MNQ), 1-minute entries, 3-min + 15-min + 1-hour candle confirmations, no indicators. June 2019 - February 2026."); c.font=SMALL; r+=1
c=ws.cell(row=r,column=1,value="Every result below is NET of 1.00 index point round-trip cost on every trade. All times New York."); c.font=SMALL; r+=1
blank()

section("1. THE RULE  (simple, no indicators)")
rule_lines=[
 "STEP 1 - FIND THE HOLE (1-min). A Fair Value Gap: candle1.high < candle3.low (bullish hole) or candle1.low > candle3.high",
 "         (bearish hole), at least 4 ticks tall, formed between 09:30 and 10:00 New York.",
 "STEP 2 - WAIT FOR IT TO FAIL. A 1-min candle must CLOSE fully through the far side of that hole within 10 candles.",
 "         That candle's volume must be <= 1.2x the median volume of the first 20 one-minute bars (no volume spike).",
 "STEP 3 - STOP SIZE. The hole must be 10 to 20 points tall. Entry = limit at the far edge, stop = 2 ticks past the",
 "         other edge => the stop is ALWAYS between 10 and 20 points. Never less than 10.",
 "STEP 4 - CONFIRMATIONS (candles only). At least 2 of these 3 must be true at the moment your limit fills:",
 "         3-MIN  : the last COMPLETED 3-minute candle has a body >= 50% of its range (a decisive break, not a doji).",
 "         15-MIN : price is on the premium/discount side - upper half of the 15-min candle still forming for a short,",
 "                  lower half for a long (sell strength, buy weakness).",
 "         1-HOUR : price is on the trade's side of the 1-hour candle's open (= the 09:30 open), i.e. WITH the",
 "                  morning direction.",
 "STEP 5 - EXECUTE. Limit order at the gap edge, filled between 09:45 and 12:00. Maximum 2 trades per day,",
 "         one position at a time. Hard target, hard stop, flat at 15:55 if neither is hit.",
]
for t in rule_lines: put([t], font=Font(size=9.5))
blank()

section("2. HEADLINE - the same 100 trades, measured at all six targets",
        "Win rate must be read against break-even: 1:2 needs 33.3%, 1:1.5 40%, 1:1 50%, 1:0.75 57.1%, 1:0.67 60%, 1:0.5 66.7%.")
df_block(SUMMARY, pct_cols=("win_pct",), r_cols=("R_per_trade",), num_cols=("profit_factor","pts_per_trade","usd_per_trade_1NQ","usd_per_trade_1MNQ"), key_rows=(0,))
blank()

section("3. WIN RATE (%) BY YEAR  -  every year, every target",
        "This is the table you asked for. Green = 50% or better. 2019 starts in May, 2026 ends 18 February.")
df_block(BY_YEAR, pct_cols=tuple(c for c in BY_YEAR.columns if c.startswith("win%")), green_ge=50)
blank()
section("4. TOTAL R BY YEAR (net of cost)  -  does the money actually show up?")
df_block(YEAR_R, r_cols=tuple(YEAR_R.columns[1:]), red_lt=0)
blank()

section("5. IN-SAMPLE vs OUT-OF-SAMPLE  (built on 2019-2022, tested unchanged on 2023-2026)")
df_block(SPLIT, pct_cols=tuple(c for c in SPLIT.columns if c.startswith("win%")), r_cols=tuple(c for c in SPLIT.columns if c.startswith("R_")))
blank()

section("6. WHAT EACH CONFIRMATION IS WORTH  (win% at 1:2 on the structural base, before the 2-of-3 filter)")
df_block(CONF, pct_cols=("win_pct_1to2",), r_cols=("R_1to2",), key_rows=(5,))
blank()

section("7. ROBUSTNESS  -  move the two knobs and see if the edge survives")
df_block(SENS, pct_cols=("win_pct_1to2","is_win","oos_win"), r_cols=("R_1to2",), key_rows=(4,))
blank()

section("8. BY WEEKDAY / DIRECTION / ENTRY TIME / STOP SIZE / MONTH  (win% at each target)")
for name,df in [("WEEKDAY",BY_DOW),("DIRECTION",BY_SIDE),("ENTRY TIME (15-min buckets)",BY_TIME),("STOP SIZE",BY_STOP),("MONTH",BY_MONTH)]:
    c=ws.cell(row=r,column=1,value=name); c.font=BOLD; r+=1
    df_block(df, pct_cols=tuple(c for c in df.columns if c.startswith("win%")), green_ge=50)
    blank()
blank()

section("9. GROSS vs NET  -  what the 1-point cost does to each target")
df_block(GROSS, pct_cols=("win_pct",), r_cols=("gross_R","cost_R","net_R"))
blank()
section("10. COST SENSITIVITY  -  R per trade at different round-trip costs (points)")
df_block(COSTS, r_cols=tuple(COSTS.columns[1:]))
blank()

section("11. TRADE STATS")
df_block(STATS)
blank()

section("12. EVERY TRADE  -  100 trades, results at all six targets",
        "pts_net columns are index points after cost. R_net_1to2 is in units of the trade's own risk.")
LOG2=LOG.copy()
df_block(LOG2)

widths={1:22,2:12,3:12,4:11,5:11,6:11,7:13,8:12,9:12,10:12,11:12,12:12,13:12,14:12,15:12,16:11,17:11,18:11,19:11,20:11,21:11,22:11,23:11,24:11,25:11,26:11}
for col,w in widths.items(): ws.column_dimensions[get_column_letter(col)].width=w
ws.freeze_panes="A5"

# conditional colouring of the year win-rate block
wb.save(OUT)
print("saved",OUT,os.path.getsize(OUT)//1024,"KB")
