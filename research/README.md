# Morning IFVG research — Nasdaq-100 futures, 1-minute candles

The written-up result is in **[REPORT.md](REPORT.md)**. It has two parts:

- **Part 1 (§0–§13)** — 1-minute IFVG only, one trade a day, fixed 1:2. 318 trades, 56.6 % wins.
- **Part 2 (§14–§25)** — the same entries plus **3-minute and 15-minute candlestick confirmations**,
  up to **2 trades a day**, with the win rate reported at **1:2, 1:1.5, 1:1, 1:0.75, 1:0.67 and 1:0.5
  for every year**. 159 trades, 56.6 % at 1:2.

**The Part 2 dataset is a workbook: [`out/IFVG_MTF_NQ.xlsx`](out/IFVG_MTF_NQ.xlsx) — 17 sheets.**
README/rules, summary by R:R, win rate and total R by year/month/weekday/side/time, in-sample vs
out-of-sample, gross vs net, cost sensitivity, confluence study, config comparison, all 159 trades,
equity curves. It is mirrored to a Google Sheet:
`docs.google.com/spreadsheets/d/1VQMIAI6qA7jel_YTXmbJgXcF-mBVq3d9uMltE30R-XU`

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
| `mtf.py`, `mtf_signals.py` | **Part 2:** 1-min → 3-min → 15-min aggregation, candle-shape features, and the 737-signal pool with all six R:R outcomes |
| `final_mtf.py` | **Part 2 rule:** `select(P, min_conf=2, max_per_day=2, sequential=True)` + the R:R table |
| `16_mtf_search.py`, `17_configs.py` | **Part 2:** the confluence-combination and config searches |
| `18_mtf_metrics.py` | **Part 2:** every table (writes `out/mtf_*.csv`) |
| `18b_mtf_charts.py`, `19_build_excel.py` | **Part 2:** the three charts and the `.xlsx` workbook |

To rebuild Part 2 end to end (needs `research/data/sessions.pkl` from step 2):

```bash
python research/scripts/mtf_signals.py    # -> data/pool_mtf.parquet (737 signals)
python research/scripts/16_mtf_search.py  # -> out/mtf_combos.csv
python research/scripts/17_configs.py     # -> out/mtf_configs.csv
python research/scripts/18_mtf_metrics.py # -> out/mtf_*.csv
python research/scripts/18b_mtf_charts.py # -> figs/mtf_*.png
python research/scripts/19_build_excel.py # -> out/IFVG_MTF_NQ.xlsx
```

## Files that are *not* committed

`research/data/*` (≈100 MB of parquet/pickle caches) and the raw search CSVs are
rebuildable from the scripts above and are git-ignored.
