# Morning IFVG research — Nasdaq-100 futures, 1-minute candles

The written-up result is in **[REPORT.md](REPORT.md)**.

## Reproduce

```bash
pip install pandas numpy matplotlib pyarrow tabulate
```

1. **Get the data.** The raw feed is CME **MNQ** 1-minute OHLCV from the public
   `mbytes21/MNQ_DATA` repository (per-contract `*.Last.csv` files, 2019-05 → 2026-02,
   New York local time, bars labelled at the *end* of the minute).

   ```bash
   git clone --filter=blob:none --no-checkout --depth 1 https://github.com/mbytes21/MNQ_DATA.git /tmp/mnqtest
   cd /tmp/mnqtest && printf '/*/*/*.Last.csv\n' > .git/info/sparse-checkout \
     && rm -f .git/index && git read-tree -mu HEAD
   ```

2. **Build the clean dataset** (picks the most liquid contract per day, converts bar
   timestamps to bar-*open* time, marks each bar with its session date):

   ```bash
   python research/scripts/01_load.py      # raw CSVs -> data/raw_all.parquet
   python research/scripts/02_build.py     # -> data/mnq_1m.parquet
   python research/scripts/04_cache.py     # -> data/sessions.pkl (arrays + lookahead-free levels)
   ```

3. **Run the final rule and rebuild every number / chart:**

   ```bash
   python research/scripts/final_rule.py    # ~1 s: prints the headline variants
   python research/scripts/13_report.py     # out/report_tables.md + out/trades_final.csv
   python research/scripts/12_charts.py     # figs/equity, yearly, month_dow, time_of_day, distributions
   python research/scripts/12b_cheatsheet.py# figs/pattern_cheatsheet.png
   ```

## What each script is

| Script | Purpose |
|---|---|
| `01_load.py`, `02_build.py`, `04_cache.py` | Data cleaning, contract stitching, per-session arrays and pre-session levels |
| `lib.py` | Shared primitives: tick size, the trade simulator (worst-case in-candle rules), ATR |
| `05*_*.py` | Candidate-pattern generators (sweep→FVG, IFVG, momentum, multi-sweep) |
| `06_analyze.py`, `07*_search.py`, `08_final_search.py`, `10_ifvg_search.py` | Feature/condition grid searches with in-sample vs out-of-sample scoring |
| `09_finalists.py`, `final_rule.py` | The surviving rule, standalone |
| `11_metrics.py`, `13_report.py` | Metric tables |
| `12_charts.py`, `12b_cheatsheet.py` | Charts |

## Files that are *not* committed

`research/data/*` (≈100 MB of parquet/pickle caches) and the raw search CSVs are
rebuildable from the scripts above and are git-ignored.
