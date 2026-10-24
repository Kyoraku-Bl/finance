import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TR=pd.read_csv("research/out/mtf_PRIMARY.csv")
EQ=pd.read_csv("research/out/mtf_EQUITY.csv")
BY=pd.read_csv("research/out/mtf_BY_YEAR.csv")
plt.rcParams.update({"figure.dpi":130,"font.size":9,"axes.grid":True,"grid.alpha":.25})

# 1. equity curves
fig,ax=plt.subplots(figsize=(8,4.2))
cols={"1:2":"#1f3864","1:1.5":"#2e75b6","1:1":"#548235","1:0.75":"#bf8f00","1:0.67":"#c55a11","1:0.5":"#a02020"}
for k,c in cols.items():
    ax.plot(EQ["trade"],EQ[k],label=k,color=c,lw=1.6 if k=="1:2" else 1.1)
ax.axhline(0,color="k",lw=.8)
ax.set_xlabel("trade number"); ax.set_ylabel("cumulative R (net of 1 pt cost)")
ax.set_title("Cumulative R by target — 159 trades, 2019-2026")
ax.legend(title="R:R",ncol=3,fontsize=8)
fig.tight_layout(); fig.savefig("research/figs/mtf_equity.png"); plt.close(fig)

# 2. win rate by year
fig,ax=plt.subplots(figsize=(8,3.8))
x=np.arange(len(BY)); w=0.13
order=["1:2","1:1.5","1:1","1:0.75","1:0.67","1:0.5"]
for i,k in enumerate(order):
    ax.bar(x+(i-2.5)*w, BY[k], width=w, label=k, color=cols[k])
for i,(yr,n) in enumerate(zip(BY.year,BY.trades)):
    ax.text(i,103,f"n={n}",ha="center",fontsize=7,color="#444")
ax.axhline(50,color="k",ls="--",lw=.8)
ax.set_xticks(x); ax.set_xticklabels(BY.year); ax.set_ylim(0,112)
ax.set_ylabel("win rate %"); ax.set_title("Win rate by year at every target (dashed = 50%)")
ax.legend(title="R:R",ncol=6,fontsize=7,loc="upper center",bbox_to_anchor=(0.5,-0.12),frameon=False)
fig.tight_layout(); fig.savefig("research/figs/mtf_year.png",bbox_inches="tight"); plt.close(fig)

# 3. gross vs net
G=pd.read_csv("research/out/mtf_GROSS.csv")
fig,ax=plt.subplots(figsize=(7,3.4))
x=np.arange(len(G))
ax.bar(x-0.2,G.gross_R_per_trade,0.4,label="gross",color="#9db7d6")
ax.bar(x+0.2,G.net_R_per_trade,0.4,label="net of 1 pt cost",color="#1f3864")
ax.axhline(0,color="k",lw=.8); ax.set_xticks(x); ax.set_xticklabels(G.RR)
ax.set_ylabel("R per trade"); ax.set_title("The same trades, with and without friction")
ax.legend(); fig.tight_layout(); fig.savefig("research/figs/mtf_gross_net.png"); plt.close(fig)
print("ok")
