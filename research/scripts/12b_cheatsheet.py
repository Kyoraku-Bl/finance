"""Illustrate the pattern with two real trades from the dataset."""
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import sys; sys.path.insert(0,"research/scripts")
from final_rule import build
from lib import load
plt.rcParams.update({"figure.dpi":140,"font.size":9,"axes.grid":False})

df=load(); S={pd.Timestamp(s["date"]):s for s in build(df)}
tr=pd.read_parquet("research/data/trades_final.parquet"); tr["dt"]=pd.to_datetime(tr.date)
GREEN,RED,BLUE,GREY,AMBER="#0e9f6e","#e02424","#1a56db","#6b7280","#d97706"

PICKS=[("2025-03-05","short"),("2022-03-15","long")]
fig,axes=plt.subplots(1,2,figsize=(13.4,5.6))
for ax,(dstr,tag) in zip(axes,PICKS):
    t=tr[tr.date==dstr].iloc[0]; s=S[pd.Timestamp(t.date)]
    k0=max(0,int(t.gap_i)-7); k1=min(len(s["h"]), int(t.entry_i)+16)
    lo=min(s["l"][k0:k1].min(), t.entry+2*(t.entry-t.stop)*t.side); hi=max(s["h"][k0:k1].max(), t.stop)
    pad=(hi-lo)*0.16; lo-=pad; hi+=pad
    ax.set_facecolor("#fcfcfe")
    for i in range(k0,k1):
        col=GREEN if s["c"][i]>=s["o"][i] else RED
        ax.plot([i,i],[s["l"][i],s["h"][i]],color=col,lw=1.1,zorder=2)
        ax.add_patch(Rectangle((i-.32,min(s["o"][i],s["c"][i])),.64,
                     max(abs(s["c"][i]-s["o"][i]),0.25),color=col,zorder=3))
    # 1. the FVG
    ax.axhspan(t.gap_lo,t.gap_hi,color=AMBER,alpha=.18,zorder=1)
    gx = k1+0.25 if t.side==-1 else k0+0.3
    ax.annotate("1  the gap (FVG)",(gx,(t.gap_lo+t.gap_hi)/2),color="#92400e",fontsize=8,
                fontweight="bold",va="center",ha="left",
                bbox=dict(fc="white",ec="#f5d0a9",alpha=.9,pad=1.6))
    # 2. inverting candle
    ax.scatter([t.inv_i],[s["c"][t.inv_i]],marker="v" if t.side==-1 else "^",s=95,
               color=BLUE,zorder=8,edgecolor="white",linewidth=.8)
    ax.annotate("2  candle closes\nthrough the gap",(t.inv_i,s["c"][t.inv_i]),
                xytext=(0.015,0.965),textcoords="axes fraction",ha="left",va="top",
                fontsize=8,color=BLUE,
                arrowprops=dict(arrowstyle="->",color=BLUE,lw=.8,ls=":",shrinkB=6))
    # 3. entry / stop / target
    tgt=t.entry+2*(t.entry-t.stop)*t.side
    for y,lab,col in [(t.entry,"3  entry",BLUE),(t.stop,"stop",RED),(tgt,"target (2R)",GREEN)]:
        ax.hlines(y,k0-.5,k1-.5,color=col,lw=1.3,ls="-" if col!=RED else (0,(4,2)))
        ax.text(k1-.4,y,f" {lab}  {y:,.2f}",color=col,fontsize=8,va="center",ha="left",
                bbox=dict(fc="white",ec="none",alpha=.75,pad=.8))
    ax.scatter([t.entry_i],[t.entry],s=45,color="black",zorder=7)
    ax.set_xlim(k0-.8,k1+3.6); ax.set_ylim(lo,hi)
    ax.set_aspect("auto")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.set_title(f"{tag.upper()}  ·  {pd.Timestamp(t.date).date()}  ·  "
                 f"{'WIN' if t.outcome=='target' else 'LOSS'} ({t.pnl_pts:+.2f} pt)",
                 fontsize=10,fontweight="bold",color=GREEN if t.outcome=="target" else RED)
fig.legend(handles=[Line2D([],[],color=BLUE,lw=1.3,label="entry"),
                    Line2D([],[],color=RED,lw=1.3,ls="--",label="stop"),
                    Line2D([],[],color=GREEN,lw=1.3,label="target = 2 × risk"),
                    Line2D([],[],color=AMBER,lw=6,alpha=.35,label="the gap (FVG)")],
           loc="lower center",ncol=4,frameon=False,fontsize=9)
fig.suptitle("THE MORNING IFVG — two real occurrences in Nasdaq-100 futures (1-min candles)",
             fontsize=12,fontweight="bold")
fig.tight_layout(rect=[0,0.06,1,.94])
fig.savefig("research/figs/pattern_cheatsheet.png",bbox_inches="tight"); print("ok")
