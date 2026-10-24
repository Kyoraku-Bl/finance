import glob, os, re
import pandas as pd, numpy as np

SRC = "/tmp/mnqtest/plaintext_csv"
files = sorted(glob.glob(os.path.join(SRC, "*", "*.Last.csv")))
rows = []
for f in files:
    contract = os.path.basename(os.path.dirname(f))          # e.g. "MNQ 03-20"
    fdate = os.path.basename(f).split(".")[0]                # e.g. 20191217
    try:
        df = pd.read_csv(f, header=0)
    except Exception:
        continue
    if len(df) == 0: continue
    df["contract"] = contract
    df["file_date"] = fdate
    rows.append(df)
df = pd.concat(rows, ignore_index=True)
df["datetime"] = pd.to_datetime(df["datetime"])
print("raw rows", len(df), "files", len(files))
print(df.head(3))
# volume per contract per calendar-date
df["cal_date"] = df["datetime"].dt.date.astype(str).str.replace("-", "")
print("date range", df.datetime.min(), df.datetime.max())
df.to_parquet("/home/user/finance/research/data/raw_all.parquet")
