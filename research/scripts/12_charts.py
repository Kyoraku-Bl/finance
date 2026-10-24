import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
import sys; sys.path.insert(0,"research/scripts")
from lib import load, TICK
from final_rule import build, backtest

plt.rcParams.update({"figure.dpi":135,"font.size":9,"axes.grid":True,"grid.alpha":.25,
                     "axes.spines.top":False,"axes.spines.right":False})
GREEN="#0e9f6e"; RED="#e02424"; BLUE="#1a56db"; GREY="#6b7280"; AMBER="#d97706"

df=load(); S=build(df); tr=backtest(S)
tr.to_parquet("research/data/trades_final.parquet")
S_by_date={pd.Timestamp(s["date"]):s for s in S}
tr["dt"]=pd.to_datetime(tr.date); S_by_date={pd.Timestamp(k):v for k,v in S_by_date.items()}

# ---------------------------------------------------------------- 1. cheat sheet
def candles(ax,o,h,l,c,x0=0,w=0.6,col_up=GREEN,col_dn=RED):
    for i,(oo,hh,ll,cc) in enumerate(zip(o,h,l,c)):
        x=x0+i; col=col_up if cc>=oo else col_dn
        ax.plot([x,x],[ll,hh],color=col,lw=1.0,zorder=2)
        ax.add_patch(Rectangle((x-w/2,min(oo,cc)),w,abs(cc-oo) or .02,color=col,zorder=3,alpha=.9))

fig,axes=plt.subplots(1,2,figsize=(12.2,5.2))
# ---- panel A: short example (bullish gap inverted) ----
ax=axes[0]
o=np.array([100,100.8,101.2,100.9,101.4,102.0,101.6,101.0,100.4,99.8,99.2,99.0,99.4,99.2])
h=np.array([100.4,101.0,101.6,101.3,101.8,102.4,102.0,101.3,100.7,100.0,99.4,99.3,99.6,99.3])
l=np.array([99.7,100.5,101.0,100.6,101.1,101.7,101.2,100.6,100.0,99.3,98.9,98.8,99.1,98.9])
c=np.array([100.2,100.9,101.4,101.0,101.6,102.1,101.4,100.8,100.2,99.5,99.0,99.1,99.4,99.0])
candles(ax,o,h,l,c)
gi=5   # gap between candle index 3 high and 5 low
ax.axhspan(l[gi],h[gi-2],xmin=.20,xmax=.95,color=AMBER,alpha=.13,zorder=1)
ax.hlines(l[gi],3,13,color=AMBER,lw=1.2,ls="--")
ax.hlines(h[gi-2],3,13,color=AMBER,lw=1.2,ls="--")
ax.annotate("1  FVG (gap between\ncandle 3 high and candle 5 low)",(6.1,101.85),fontsize=8,color="#92400e")
ax.annotate("2  a candle CLOSES below\nthe gap  →  gap is 'inverted' (IFVG)",(9.0,100.15),fontsize=8,color="#92400e",
            ha="left")
ax.annotate("3  sell the retest\nof the inverted gap",(11.25,99.45),fontsize=8,color=BLUE)
ax.annotate("",xy=(12.4,99.05),xytext=(11.6,99.6),arrowprops=dict(arrowstyle="->",color=BLUE,lw=1.2))
# entry / stop / target lines
entry=l[gi]; stop=h[gi-2]+0.04; risk=stop-entry; target=entry-2*risk
for y,lab,col,ls in [(entry,"entry (sell limit)",BLUE,"-"),(stop,"stop",RED,"-"),(target,"target = 2R",GREEN,"-")]:
    ax.hlines(y,9.5,13.6,color=col,lw=1.4,ls=ls)
    ax.text(13.7,y,lab,color=col,fontsize=8,va="center")
ax.set_title("SHORT version — bullish gap gets inverted",fontsize=10,fontweight="bold")
ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
ax.set_xlim(-.8,15.4)

# ---- panel B: long example (bearish gap inverted) ----
ax=axes[1]
o=np.array([100,99.4,99.0,99.2,98.8,98.2,98.6,99.2,99.8,100.4,101.0,101.2,100.8,101.0])
h=np.array([100.3,99.7,99.2,99.5,99.0,98.5,99.0,99.6,100.2,100.8,101.3,101.5,101.2,101.4])
l=np.array([99.6,99.0,98.6,98.9,98.4,97.9,98.2,98.8,99.4,100.0,100.6,100.9,100.4,100.8])
c=np.array([99.8,99.1,98.8,99.1,98.6,98.0,98.8,99.4,100.0,100.6,101.2,101.0,100.7,101.2])
candles(ax,o,h,l,c)
gi=5
ax.axhspan(h[gi],l[gi-2],xmin=.20,xmax=.95,color=AMBER,alpha=.13,zorder=1)
ax.hlines(h[gi],3,13,color=AMBER,lw=1.2,ls="--"); ax.hlines(l[gi-2],3,13,color=AMBER,lw=1.2,ls="--")
ax.annotate("1  FVG (gap between\ncandle 3 low and candle 5 high)",(6.1,98.35),fontsize=8,color="#92400e")
ax.annotate("2  a candle CLOSES above\nthe gap  →  inverted (IFVG)",(9.0,100.15),fontsize=8,color="#92400e")
ax.annotate("3  buy the retest\nof the inverted gap",(11.25,100.9),fontsize=8,color=BLUE)
entry=h[gi]; stop=l[gi-2]-0.04; risk=entry-stop; target=entry+2*risk
for y,lab,col in [(entry,"entry (buy limit)",BLUE),(stop,"stop",RED),(target,"target = 2R",GREEN)]:
    ax.hlines(y,9.5,13.6,color=col,lw=1.4)
    ax.text(13.7,y,lab,color=col,fontsize=8,va="center")
ax.set_title("LONG version — bearish gap gets inverted",fontsize=10,fontweight="bold")
ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
ax.set_xlim(-.8,15.4)
fig.suptitle("THE MORNING IFVG  ·  Nasdaq-100 futures, 1-minute candles, 09:30-10:00 New York",
             fontsize=12,fontweight="bold")
fig.tight_layout(rect=[0,0,1,.94]); fig.savefig("research/figs/pattern_cheatsheet.png",bbox_inches="tight"); plt.close(fig)

# ---------------------------------------------------------------- 2. real examples
cand=tr.sort_values("dt")
examples=[cand.iloc[i] for i in (len(cand)//5, len(cand)//2, int(len(cand)*0.82))]
fix,axs=plt.subplots(1,3,figsize=(13,4.4))
for ax,(_,t) in zip(axs, enumerate(examples)):
    s=S_by_date[pd.Timestamp(t.date)]
    k0=max(0,t.gap_i-6); k1=min(len(s["h"]), t.entry_i+12)
    ax.set_facecolor("#fbfbfd")
    for i in range(k0,k1):
        col=GREEN if s["c"][i]>=s["o"][i] else RED
        ax.plot([i,i],[s["l"][i],s["h"][i]],color=col,lw=1.0)
        ax.add_patch(Rectangle((i-.3,min(s["o"][i],s["c"][i])),.6,
                     max(abs(s["c"][i]-s["o"][i]),TICK),color=col,alpha=.95))
    ax.axhspan(t.gap_lo,t.gap_hi,color=AMBER,alpha=.15)
    ax.hlines([t.gap_lo,t.gap_hi],k0-0.5,k1-0.5,color=AMBER,lw=.9,ls="--")
    ax.scatter([t.inv_i],[s["c"][t.inv_i]],marker="v" if t.side==-1 else "^",s=70,color=BLUE,zorder=5)
    ax.scatter([t.entry_i],[t.entry],marker="o",s=55,color="black",zorder=6)
    ax.hlines(t.entry,k0-0.5,k1-0.5,color=BLUE,lw=1.1)
    ax.hlines(t.stop,k0-0.5,k1-0.5,color=RED,lw=1.1)
    ax.hlines(t.entry+2*(t.entry-t.stop)*t.side,k0-0.5,k1-0.5,color=GREEN,lw=1.1)
    ax.set_title(f"{t.date}  {'LONG' if t.side==1 else 'SHORT'}  → {t.outcome.upper()}  "
                 f"({t.pnl_pts:+.2f} pt)",fontsize=9,fontweight="bold",
                 color=GREEN if t.outcome=="target" else RED)
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
fig.suptitle("Real examples: amber = the gap · ▼/▲ = the inverting candle · ● = entry · "
             "blue/red/green = entry/stop/target",fontsize=10)
fig.tight_layout(rect=[0,0,1,.93]); fig.savefig("research/figs/examples.png",bbox_inches="tight"); plt.close(fig)

# ---------------------------------------------------------------- 3. equity
fig,axes=plt.subplots(2,1,figsize=(11,6.4),gridspec_kw=dict(height_ratios=[2,1]))
cum=tr.sort_values("dt").R.cumsum()
ax=axes[0]
ax.plot(pd.to_datetime(tr.sort_values("dt").dt),cum.values,color=BLUE,lw=1.6)
ax.fill_between(pd.to_datetime(tr.sort_values("dt").dt),0,cum.values,color=BLUE,alpha=.08)
ax.axhline(0,color=GREY,lw=.8)
ax.set_title(f"Cumulative R  ·  {len(tr)} trades  ·  {100*(tr.R>0).mean():.1f}% win  ·  "
             f"PF {tr.R[tr.R>0].sum()/abs(tr.R[tr.R<=0].sum()):.2f}",fontweight="bold")
ax.set_ylabel("R (1R = the risk on that trade)")
dd=cum-cum.cummax()
axes[1].fill_between(pd.to_datetime(tr.sort_values("dt").dt),dd.values,0,color=RED,alpha=.35)
axes[1].set_title(f"Drawdown ({dd.min():.1f} R max)"); axes[1].set_ylabel("R")
fig.tight_layout(); fig.savefig("research/figs/equity.png",bbox_inches="tight"); plt.close(fig)

# ---------------------------------------------------------------- 4. yearly
g=tr.groupby(tr.dt.dt.year).agg(n=("R","size"),win=("R",lambda x:100*(x>0).mean()),R=("R","sum"))
fig,ax=plt.subplots(figsize=(9,4.2))
ax.bar(g.index.astype(str),g.n,color="#c7d2fe",label="trades")
ax.set_ylabel("trades"); ax.set_ylim(0,g.n.max()*1.35)
ax2=ax.twinx(); ax2.plot(g.index.astype(str),g.win,"o-",color=BLUE,lw=2,label="win rate %")
ax2.axhline(33.33,color=RED,ls="--",lw=1); ax2.text(0,34.5,"break-even at 1:2 = 33.3%",color=RED,fontsize=8)
ax2.set_ylabel("win rate %"); ax2.set_ylim(0,100); ax2.grid(False)
for i,(y,r,w) in enumerate(zip(g.index,g.R,g.win)):
    ax2.annotate(f"{r:+.0f}R",(i,w),textcoords="offset points",xytext=(0,8),ha="center",fontsize=8,color=BLUE)
ax.set_title("Per year: number of trades and win rate",fontweight="bold")
fig.tight_layout(); fig.savefig("research/figs/yearly.png",bbox_inches="tight"); plt.close(fig)

# ---------------------------------------------------------------- 5. month + dow
fig,axes=plt.subplots(1,2,figsize=(12,4.2))
m=tr.groupby("month").agg(n=("R","size"),win=("R",lambda x:100*(x>0).mean()))
names=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
axes[0].bar([names[i-1] for i in m.index],m.win,color=[GREEN if w>=50 else RED for w in m.win],alpha=.75)
axes[0].axhline(33.33,color=RED,ls="--",lw=1); axes[0].axhline(50,color=GREY,ls=":",lw=1)
axes[0].set_title("Win rate by month (all years)",fontweight="bold"); axes[0].set_ylim(0,100)
for i,(x,w,n) in enumerate(zip(range(len(m)),m.win,m.n)):
    axes[0].text(i,w+2,f"{w:.0f}%\nn={n}",ha="center",fontsize=7.5)
d=tr.groupby("dow").agg(n=("R","size"),win=("R",lambda x:100*(x>0).mean()))
dn=["Mon","Tue","Wed","Thu","Fri"]
axes[1].bar([dn[i] for i in d.index],d.win,color=[GREEN if w>=50 else RED for w in d.win],alpha=.75)
axes[1].axhline(33.33,color=RED,ls="--",lw=1); axes[1].set_ylim(0,100)
axes[1].set_title("Win rate by weekday",fontweight="bold")
for i,(x,w,n) in enumerate(zip(range(len(d)),d.win,d.n)):
    axes[1].text(i,w+2,f"{w:.0f}%\nn={n}",ha="center",fontsize=7.5)
fig.tight_layout(); fig.savefig("research/figs/month_dow.png",bbox_inches="tight"); plt.close(fig)

# ---------------------------------------------------------------- 6. distributions
fig,axes=plt.subplots(1,3,figsize=(13,3.8))
axes[0].hist(tr.R,bins=24,color=BLUE,alpha=.75)
axes[0].set_title("R per trade"); axes[0].set_xlabel("R")
axes[1].hist(tr.risk,bins=26,color=AMBER,alpha=.8)
axes[1].set_title("Stop size (points)"); axes[1].set_xlabel("points")
axes[2].hist(tr.bars.clip(0,20),bins=20,color=GREEN,alpha=.75)
axes[2].set_title("Minutes in trade"); axes[2].set_xlabel("1-min bars held")
fig.suptitle("Trade distributions",fontweight="bold")
fig.tight_layout(rect=[0,0,1,.93]); fig.savefig("research/figs/distributions.png",bbox_inches="tight"); plt.close(fig)

# ---------------------------------------------------------------- 7. time of day
fig,ax=plt.subplots(figsize=(9,3.6))
h=tr.groupby(tr.entry_t//15).agg(n=("R","size"),win=("R",lambda x:100*(x>0).mean()))
lab=[f"{(int(i)*15)//60:02d}:{int(i)*15%60:02d}" for i in h.index]
b=ax.bar(lab,h.win,color=[GREEN if w>=50 else RED for w in h.win],alpha=.75)
ax2=ax.twinx(); ax2.plot(lab,h.n,"o-",color=BLUE); ax2.grid(False); ax2.set_ylabel("trades")
ax.axhline(33.33,color=RED,ls="--",lw=1)
ax.set_ylim(0,100); ax.set_title("Win rate by 15-min bucket of entry time (New York)",fontweight="bold")
for i,(w,n) in enumerate(zip(h.win,h.n)): ax.text(i,w+2,f"{w:.0f}%\nn={n}",ha="center",fontsize=7.5)
fig.tight_layout(); fig.savefig("research/figs/time_of_day.png",bbox_inches="tight"); plt.close(fig)
print("charts written")
