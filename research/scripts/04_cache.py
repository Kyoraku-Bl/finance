"""Cache per-session arrays + pre-known levels (no lookahead)."""
import numpy as np, pandas as pd, pickle, sys
sys.path.insert(0,"research/scripts"); from lib import *

df = load().sort_values("ts").reset_index(drop=True)

# ---- session dates = dates that contain a 09:30 bar ----
op = df[df["mod"]==WIN_START].ts.dt.normalize().drop_duplicates().to_numpy()
op = np.sort(op)
ix = np.searchsorted(op, df.ts.to_numpy(), side="left")   # first 09:30 at/after the bar
df["sess"] = pd.Series(op[np.clip(ix,0,len(op)-1)], index=df.index)
df.loc[ix>=len(op),"sess"] = pd.NaT                     # bars after the last session

# ---- reference levels known before 09:30 of the session date ----
def agg(g):
    return pd.Series(dict(hi=g.high.max(), lo=g.low.min(), cl=g.close.iloc[-1], n=len(g)))
rows=[]
for sess, g in df[df["sess"].notna()].groupby("sess", sort=True):
    m=g["mod"].to_numpy(); h=g.high.to_numpy(); l=g.low.to_numpy()
    on  = m>=18*60
    pre = (m<WIN_START) | on
    pm  = (m<WIN_START) & (m>=8*60)
    r=dict(date=sess)
    if on.any(): r["on_h"],r["on_l"]=h[on].max(),l[on].min()
    if pm.any(): r["pm_h"],r["pm_l"]=h[pm].max(),l[pm].min()
    if pre.any(): r["pre_h"],r["pre_l"]=h[pre].max(),l[pre].min()
    rows.append(r)
LV=pd.DataFrame(rows)

rth = df[(df["mod"]>=WIN_START)&(df["mod"]<=16*60)&df["sess"].notna()]
a = rth.groupby("sess").agg(pdh=("high","max"),pdl=("low","min"),pdc=("close","last"),n=("close","size"))
a = a[a.n>=100]
a[["pdh","pdl","pdc"]] = a[["pdh","pdl","pdc"]].shift(1)
LV = LV.merge(a.reset_index().rename(columns={"sess":"date"}), on="date", how="left")

# ---- session arrays 09:30 -> 15:55 ----
SESS=[]
for sess,g in df[df["sess"].notna()].groupby("sess", sort=True):
    g=g[(g["mod"]>=WIN_START)&(g["mod"]<=DEADLINE)]
    if len(g)<60: continue
    r=LV[LV.date==sess]
    SESS.append(dict(date=str(sess.date()),
        o=g.open.to_numpy(float),h=g.high.to_numpy(float),l=g.low.to_numpy(float),
        c=g.close.to_numpy(float),v=g.volume.to_numpy(float),mod=g["mod"].to_numpy(int),
        lv=(r.iloc[0].to_dict() if len(r) else {})))
pickle.dump(SESS,open("research/data/sessions.pkl","wb"))
print("sessions:",len(SESS))
import collections
c=collections.Counter()
for s in SESS:
    for k in ("on_l","pm_l","pdl","pdc"):
        if s["lv"].get(k) is not None and s["lv"].get(k)==s["lv"].get(k): c[k]+=1
print("level coverage:",dict(c))
