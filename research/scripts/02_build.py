"""Build a clean 1-min MNQ dataset from the raw per-contract dumps.

Source: github.com/mbytes21/MNQ_DATA (CME MNQ 1-minute OHLCV, 2019-05 -> 2026-02)
Timestamps in the source are New York local time and label the END of the minute
(verified: the largest volume bar of the day is labelled 09:31, i.e. the 09:30 open
minute; the 16:00 bar is the closing minute). We shift by -1 min so every row is
labelled with the bar's OPEN time -> 09:30 bar == 09:30:00-09:30:59 ET.
"""
import pandas as pd, numpy as np

df = pd.read_parquet("research/data/raw_all.parquet")
df = df.rename(columns={"datetime": "ts_end"})

# --- pick one contract per delivery-file: the most liquid one on that date ---
vol = df.groupby(["file_date", "contract"], as_index=False)["volume"].sum()
best = vol.sort_values("volume").drop_duplicates("file_date", keep="last")
df = df.merge(best[["file_date", "contract"]], on=["file_date", "contract"], how="inner")

# --- bar-open timestamps ---
df["ts"] = df["ts_end"] - pd.Timedelta(minutes=1)
df = df[["ts", "open", "high", "low", "close", "volume", "contract"]]
df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)

# sanity
bad = (df.high < df.low) | (df.high < df.open) | (df.high < df.close) | (df.low > df.open) | (df.low > df.close)
print("rows:", len(df), " bad OHLC rows dropped:", int(bad.sum()))
df = df[~bad]

# trading session = date of the 09:30 bar
df["date"] = df["ts"].dt.normalize()
# rows before 18:00 belong to the *next* session's overnight
df.loc[df["ts"].dt.hour < 18, "date"] = (df.loc[df["ts"].dt.hour < 18, "ts"] - pd.Timedelta(days=1)).dt.normalize()

print(df.ts.min(), "->", df.ts.max())
print("sessions:", df.date.nunique())
df.to_parquet("research/data/mnq_1m.parquet")
print(df.head(3).to_string())
print(df.tail(3).to_string())

# density inside the 09:30-11:30 window
w = df[(df.ts.dt.hour * 60 + df.ts.dt.minute >= 570) & (df.ts.dt.hour * 60 + df.ts.dt.minute < 690)]
per = w.groupby("date").size()
print("\nminutes per session inside 09:30-11:30 (ideal 120):")
print(per.describe().to_string())
