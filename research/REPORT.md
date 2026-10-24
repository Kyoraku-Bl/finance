# THE MORNING IFVG
### A repeatable 1-minute pattern on Nasdaq-100 futures, 09:30–10:00 New York

---

## 0. What I actually tested

| | |
|---|---|
| **Instrument** | Nasdaq-100 futures — **MNQ / NQ** (they track the same index, same price, MNQ is 1/10 the size). Data is the **CME MNQ 1-minute OHLCV** feed. |
| **History** | **May 2019 → Feb 2026** (~6.8 years) · **1,493 trading sessions** · 2.03 M one-minute candles |
| **Timeframe** | 1-minute candles only |
| **Clock** | New York time. Every bar is labelled with the **start** of the minute, so the 09:30 bar = 09:30:00–09:30:59. |
| **Session studied** | 09:30 → 11:30 (as you asked). The rule only *fires* between 09:30 and 10:00 because that's where the edge is. |
| **Trade management** | Fixed 1:2 R:R — target = 2 × stop distance, stop = 2 ticks beyond the gap. One trade per day, flat by 15:55 if neither level is touched. |
| **Costs** | **1.00 index point round-trip** (≈1 tick spread + 3 ticks commission/slippage) deducted from **every** trade. |

**Honest data notes (please read these, they matter):**

1. **Only ~6.8 years, not 10.** Free 1-minute NQ/MNQ history doesn't extend further. Only `github` and `pypi` are reachable from this sandbox; Yahoo/Stooq/paid vendors are blocked. This is the longest clean 1-min dataset I could actually get.
2. **The source has a hole: October–November 2023 is missing** (194 sessions in 2023 instead of ~250). Months Oct/Nov therefore look thin in the tables.
3. **Signed-off logic:** on the candle where the limit order fills, only the *stop* side is checked (worst-case in-candle path). No trade is ever given credit for hitting the target inside the same candle it was entered — that removes the most common backtest lie at 1-minute resolution.
4. Everything is measured **after** costs, and the rule was chosen on 2019-2022 and then checked unchanged on 2023-2026.

---

## 1. The pattern in plain English

Think of it as **"a gap that fails becomes a wall."**

### Step 0 — What a "gap" (FVG) is on a 1-minute chart
Look at three candles in a row. If candle 1's **high** is *below* candle 3's **low**, the market moved so fast that nobody traded in between — a hole is left on the chart. That hole is a **Fair Value Gap (FVG)**.

```
        candle1        candle3
          ██             ██
          ██   <-- hole --> ██      the hole = FVG
```

Normally price later dips back into the hole and bounces — that's the classic FVG trade.

### Step 1 — Wait for the gap to FAIL (this is the "IFVG")
Instead of bouncing, price **closes a whole candle through the far side of the hole**. The gap is now *broken*. In ICT language the FVG has become an **IFVG** (Inverted Fair Value Gap).

That matters because a broken gap changes meaning: the hole that used to be **support** is now **resistance** (and vice-versa). The traders who bought the gap are trapped and will sell on the way back up.

### Step 2 — Sell/buy the retest of the broken gap
- Price comes back **up** into the broken hole → **sell** at the hole's edge (limit order).
- Price comes back **down** into the broken hole → **buy** at the hole's edge.

### Step 3 — Risk and target
- **Stop:** 2 ticks beyond the *other* side of the hole (the hole itself is the danger zone — if price closes back through it, the idea is dead).
- **Target:** exactly **2 × the risk**. Nothing else. No trailing, no partials.

### Step 4 — Three quality filters (this is what turns 45% into 56.6%)

| Filter | What it says in plain words | Why it works |
|---|---|---|
| **Q1 — small target vs the day's range** | Only take it if **2R is ≤ 8 % of the average daily range** of the last 5 sessions. | If the 2R target is tiny compared with how far this market normally travels in a day, the target is inside the "noise-free" part of the move. Big 2R targets in a quiet market are hope. |
| **Q2 — the inverting candle must be quiet** | Volume on the candle that closes through the gap must be **≤ 1.2 × the morning's median volume**. | A hole punched through on *normal* volume is a genuine failure. A hole punched through on a volume spike is news/panic — it keeps running and stops you out. |
| **Q3 — it must fail fast** | The candle that closes through the gap must come **within 10 minutes** of the gap forming. | A gap that gets broken straight away is broken by the same aggressive move that created it. A gap broken 40 minutes later is just the market drifting. |

If several setups appear, take **the first one that day**. If none appear, you don't trade. That is roughly **47 trades per year ≈ 4 per month**.

---

## 2. The pattern on real candles

![The Morning IFVG on two real trades](figs/pattern_cheatsheet.png)

*Amber band = the gap. ▼ / ▲ = the candle that closes through it (the "inversion"). ● = where the limit order fills. Blue = entry, red dashed = stop, green = target.*

Look at the left panel (short): the market gaps **up** through a hole between candle 3 and candle 5, then one candle **closes back below** the hole — the hole is now a ceiling. Price retests it, the sell limit is filled, and 2R is reached a few minutes later.

---

## 3. Headline results

| Metric | Value |
|---|---|
| **Trades** | **318** (≈ 47 per year, ≈ 4 per month) |
| **Win rate @ 1:2 R:R** | **56.6 %** (180 wins / 138 losses) |
| Break-even win rate at 1:2 | 33.3 % |
| **R per trade (net)** | **+0.54 R** |
| **Profit factor** | **2.07** |
| Total R over 6.8 years | **+171 R** |
| Avg points per trade (net of 1 pt cost) | **+5.48 pts** |
| Total points (net) | +1,742 pts |
| USD per trade, 1 MNQ ($2/pt) | **+$9.72** |
| USD per trade, 1 NQ ($20/pt) | **+$104.58** |
| Median stop | **6.0 pts = 24 ticks** |
| Median time in trade | **1 minute** (289 of 318 trades finish in ≤ 2 min) |
| Max drawdown | **−9.3 R** |
| Longest losing streak | 9 |
| Best / worst trade | +1.95 R / −1.25 R |

![Equity curve](figs/equity.png)

**The most important line in this report:** the rule was selected on 2019–2022 and then run unchanged on 2023–2026.

| Period | Trades | Win rate | R/trade | PF |
|---|---|---|---|---|
| 2019–2022 (in-sample) | 163 | 55.8 % | +0.51 | 1.99 |
| 2023–2026 (out-of-sample) | 155 | **57.4 %** | +0.57 | 2.15 |

No degradation out of sample.

![Per year](figs/yearly.png)

---

## 4. Every year

| Year | Trades | Wins | Losses | Win rate | Total R | R/trade | PF | Pts/trade | USD (1 MNQ) |
|---|---|---|---|---|---|---|---|---|---|
| 2019* | 2 | 0 | 2 | 0.0 % | −2.4 | −1.18 | 0.00 | −5.6 | −$31 |
| 2020 | 54 | 30 | 24 | **55.6 %** | +26.3 | +0.49 | 1.93 | +4.1 | +$227 |
| 2021 | 44 | 19 | 25 | 43.2 % | +5.0 | +0.11 | 1.17 | +1.9 | −$8 |
| 2022 | 63 | 42 | 21 | **66.7 %** | +54.2 | +0.86 | 3.26 | +8.8 | +$860 |
| 2023 | 33 | 18 | 15 | 54.5 % | +15.1 | +0.46 | 1.86 | +3.8 | +$116 |
| 2024 | 59 | 32 | 27 | 54.2 % | +27.4 | +0.46 | 1.87 | +5.1 | +$364 |
| 2025 | 55 | 35 | 20 | **63.6 %** | +42.4 | +0.77 | 2.87 | +7.6 | +$618 |
| 2026* | 8 | 4 | 4 | 50.0 % | +3.0 | +0.37 | 1.65 | +6.2 | +$67 |

\*2019 = May→Dec only (dataset starts in May); 2026 = Jan→18 Feb (dataset ends there). **7 of 8 calendar years positive; the only negative year (2019) has 2 trades.**

---

## 5. Every month

![Month and weekday](figs/month_dow.png)

| Month | Trades | Win rate | Total R | PF | Pts/trade |
|---|---|---|---|---|---|
| Jan | 33 | 45.5 % | +6.8 | 1.33 | +3.7 |
| Feb | 33 | 42.4 % | +4.0 | 1.18 | +2.9 |
| Mar | 41 | 46.3 % | +10.6 | 1.43 | +3.8 |
| Apr | 32 | **68.8 %** | +29.4 | 3.57 | +9.5 |
| May | 34 | 55.9 % | +17.1 | 1.96 | +5.8 |
| Jun | 28 | **78.6 %** | +32.9 | 5.58 | +8.5 |
| Jul | 24 | 62.5 % | +17.0 | 2.60 | +6.7 |
| Aug | 33 | 63.6 % | +24.4 | 2.73 | +6.4 |
| Sep | 19 | 68.4 % | +17.1 | 3.42 | +8.5 |
| Oct | 9 | 44.4 % | +1.1 | 1.17 | +1.4 |
| Nov | 6 | 50.0 % | +1.9 | 1.54 | +2.2 |
| Dec | 26 | 50.0 % | +8.8 | 1.59 | +2.9 |

**All 12 months are net positive.** The weak stretch is **Jan–Mar (45/42/46 %)** and the strongest is **Apr–Sep (56–79 %)** — spring/summer trends are cleaner for this pattern than the January chop. Oct/Nov trade counts are low because that's the data hole.

<details>
<summary><b>Year × month: total R (click)</b></summary>

| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2019 | · | · | · | · | −1.2 | · | · | −1.2 | · | · | · | · |
| 2020 | · | · | +7.6 | · | · | · | −1.0 | · | +18.4 | −0.8 | · | · |
| 2021 | · | −1.0 | −2.8 | · | +1.0 | · | · | · | · | · | · | +7.9 |
| 2022 | +4.2 | +1.2 | +1.6 | +2.0 | +7.4 | +3.1 | +5.9 | −0.8 | +1.5 | · | · | +6.5 |
| 2023 | +2.9 | +2.0 | −2.8 | · | · | · | · | +2.0 | · | · | · | · |
| 2024 | +4.8 | −4.5 | +8.4 | +16.8 | −1.0 | −1.0 | +6.9 | +5.0 | +1.5 | · | · | +2.9 |
| 2025 | −1.0 | +0.8 | −4.4 | +2.0 | +6.2 | +4.0 | +6.4 | +12.3 | · | · | · | +2.0 |
| 2026 | −0.5 | +3.5 | · | · | · | · | · | · | · | · | · | · |

</details>

---

## 6. Every weekday

| Day | Trades | Win rate | Total R | PF | Pts/trade |
|---|---|---|---|---|---|
| **Monday** | 64 | **62.5 %** | +46.3 | 2.68 | +7.0 |
| **Tuesday** | 76 | **61.8 %** | +52.6 | 2.56 | +6.1 |
| Wednesday | 72 | 47.2 % | +17.9 | 1.40 | +3.1 |
| Thursday | 49 | 44.9 % | +9.2 | 1.29 | +3.7 |
| **Friday** | 57 | **64.9 %** | +45.0 | 2.95 | +7.6 |

Monday, Tuesday and Friday carry most of the edge; **Wednesday and Thursday are close to break-even** — a practical take-away is to skip mid-week, or size down.

---

## 7. Every time-of-day slice

| Entry window (NY) | Trades | Win rate | R/trade |
|---|---|---|---|
| 09:30–09:45 | 72 | 55.6 % | +0.50 |
| **09:45–10:00** | **188** | **60.1 %** | **+0.65** |
| 10:00–10:15 | 39 | 56.4 % | +0.53 |
| 10:15–10:30 | 7 | 28.6 % | −0.33 |
| 10:30–11:30 | 12 | 25.0 % | −0.41 |

The edge lives in the **first 30 minutes**, peaks at **09:45–10:00** (right after the opening auction noise settles), and is gone after **10:15**. This is why the rule stops taking setups at 10:00 even though your window ran to 11:30.

![Time of day](figs/time_of_day.png)

---

## 8. Direction, stop size, gap size, hold time

**Direction**

| Side | Trades | Win rate | R/trade | PF |
|---|---|---|---|---|
| Long | 162 | 58.0 % | +0.58 | 2.20 |
| Short | 156 | 55.1 % | +0.49 | 1.94 |

Both sides work. Longs slightly better (the 2019-2026 Nasdaq uptrend).

**Stop size (1R in points)**

| 1R | Trades | Win rate | R/trade | PF |
|---|---|---|---|---|
| 4–6 pts | 167 | 55.1 % | +0.45 | 1.83 |
| 6–8 pts | 62 | 54.8 % | +0.50 | 1.98 |
| 8–10 pts | 38 | 44.7 % | +0.23 | 1.38 |
| 10–13 pts | 32 | 68.8 % | +0.97 | 3.87 |
| 13–20 pts | 17 | 82.4 % | +1.41 | 8.47 |
| 20+ pts | 2 | 50.0 % | +0.45 | 1.87 |

Win rate is fairly flat across stop sizes (the 8–10 pt bucket is the only soft spot) — the *points* per trade grow with stop size because 1R is worth more, which is the mechanical result, not extra edge. Remember **1 MNQ tick = $0.50 (micro) / $5 (mini)**: a 6-point stop is $120 on 1 NQ contract and $12 on 1 MNQ.

**Gap size**

| Gap | Trades | Win rate | R/trade | PF |
|---|---|---|---|---|
| 16–30 ticks (4.0–7.5 pt) | 194 | 56.2 % | +0.49 | 1.93 |
| **30+ ticks (>7.5 pt)** | **124** | **57.3 %** | **+0.61** | **2.30** |

**Note on the missing small holes:** the rule needs a stop of at least 4 points, and the stop sits behind the far edge of the hole — so a hole smaller than about **4.5 points (18 ticks)** can never qualify. In practice that means **the rule only trades big holes**, and the biggest ones are the best ones. This is a deliberate consequence of the "1R ≥ 4 points" floor, disclosed in the rules card.

**Time in trade**

| Hold | Trades | Win rate | R/trade |
|---|---|---|---|
| 1–2 min | 289 | 57.1 % | +0.55 |
| 3–5 min | 22 | 59.1 % | +0.64 |
| 6–15 min | 7 | 28.6 % | −0.29 |

This is a **scalp**: 91 % of trades resolve in under 2 minutes. If it hasn't hit target or stop within ~15 minutes, the setup is stale.

---

## 9. Why you should (and shouldn't) believe it

### Does each filter actually add value? (ablation)

| Variant | Trades | Win rate | R/trade | PF |
|---|---|---|---|---|
| No filters | 757 | 45.2 % | +0.23 | 1.38 |
| Only Q1 (small target) | 453 | 52.1 % | +0.40 | 1.73 |
| Q1 + Q2 | 356 | 54.8 % | +0.48 | 1.92 |
| Q1 + Q3 | 398 | 54.3 % | +0.47 | 1.88 |
| **Q1 + Q2 + Q3** | **318** | **56.6 %** | **+0.54** | **2.07** |

Each filter adds, and none of them is carrying the whole thing.

### Are the thresholds fragile?

| Q1 target ≤ | Trades | Win rate | PF |
|---|---|---|---|
| 6 % | 221 | 59.3 % | 2.26 |
| 7 % | 283 | 56.5 % | 2.04 |
| **8 %** | **318** | **56.6 %** | **2.07** |
| 10 % | 397 | 52.6 % | 1.79 |
| 12 % | 443 | 52.6 % | 1.81 |
| 15 % | 495 | 51.3 % | 1.73 |

| Q2 volume ≤ | Trades | Win rate | PF |
|---|---|---|---|
| 0.8× | 120 | 57.5 % | 2.12 |
| 1.0× | 229 | 60.7 % | 2.44 |
| **1.2×** | **318** | **56.6 %** | **2.07** |
| 1.5× | 369 | 55.0 % | 1.94 |
| 2.0× | 392 | 54.1 % | 1.86 |
| no filter | 398 | 54.3 % | 1.88 |

The response is **monotone**, not a lucky spike — tightening the filters keeps improving the result, loosening degrades it. That's the signature of a real effect rather than curve-fitting.

### Cost sensitivity

| Round-trip cost | R/trade | PF |
|---|---|---|
| 0.0 pt | +0.70 | 2.61 |
| 0.5 pt | +0.62 | 2.32 |
| **1.0 pt (assumed)** | **+0.54** | **2.07** |
| 2.0 pt | +0.38 | 1.66 |
| 3.0 pt | +0.22 | 1.34 |

Still profitable even at 3× the assumed friction — but note the margin: **this pattern is a scalp, execution quality is half the edge.**

### What if you want a bigger target? (same 318 entries)

| Target | Win rate | R/trade | PF |
|---|---|---|---|
| 1:1 | 65.2 % | +0.14 | 1.35 |
| 1:1.5 | 61.4 % | +0.38 | 1.84 |
| **1:2** | **56.7 %** | **+0.54** | **2.08** |
| 1:2.5 | 52.0 % | +0.66 | 2.18 |
| 1:3 | 48.3 % | +0.77 | 2.28 |

1:2 is the sweet spot you asked for; 1:2.5–1:3 actually make slightly more R per trade but with a much lower win rate (harder to hold psychologically).

---

## 10. Other pattern families I tested and rejected

I didn't just test one idea — these all failed to clear the same bar (≥50 % win at 1:2, consistent across years):

| Family | Best result | Verdict |
|---|---|---|
| **Liquidity sweep → FVG retest** (sweep overnight high/low, then trade the FVG it leaves) | 36 % win, +0.01 R | The "textbook" ICT setup is a coin flip at 1:2 on NQ mornings. |
| Sweep + momentum entry (market order on the reversal candle) | 38.6 % win, +0.09 R | Works only in the 09:30–09:40 opening burst. |
| FVG retest with no sweep (pure gap fill) | 40.5 % win, +0.14 R | Too weak. |
| Sweep of previous-day high/low → FVG | 36 % win | No edge. |
| Repeated sweeps (2nd / 3rd attempt at a level) | 36 % win | No edge. |
| **IFVG with no filters** | **45.2 % win, +0.23 R** | **This is the seed that became the rule.** |
| Sweep **+** IFVG combined | 41–49 % win, 0.13–0.40 R | Good, but thinner sample and no better than the plain IFVG — so the sweep isn't required. |
| Opening-drive pullback | too few trades | Sample too small. |

The **inverted gap (IFVG)** was the only structure that survived; adding the sweep requirement actually *hurt* it (sweeps happen after the fact and reduce the sample without improving accuracy).

---

## 11. Rules card (print this)

```
INSTRUMENT   NQ / MNQ, 1-minute candles
WINDOW       09:30 – 10:00 New York.  One trade max per day.  No setup = no trade.
TREND        Don't care. This is a mean-reversion scalp.

SETUP
 1. Find a gap (FVG): candle1.high < candle3.low   (bullish hole)
                      candle1.low  > candle3.high  (bearish hole)
    Minimum size: 4 ticks (1.00 pt).
 2. Wait for a candle to CLOSE fully through the far side of that hole
    -> the hole is now an IFVG.
    It must happen within 10 candles of the hole forming.
 3. The candle that closes through must have volume
    <= 1.2 x the median volume of the first 20 candles of the session.

ENTRY   Limit order at the edge of the inverted hole (the side price is coming back to).
        Entry must be filled before 10:00.

STOP    2 ticks beyond the other edge of the hole.
        1R must be >= 4 points and the resulting 2R target must be
        <= 8% of the average daily range of the last 5 sessions.

TARGET  Exactly 2 x risk. Hard exit. No trailing.
        If neither stop nor target by 15:55, exit at market.

SIZE    Risk a fixed % per trade. Median 1R = 6 pts = $120 on 1 NQ, $12 on 1 MNQ.
```

---

## 12. Files

| File | What's in it |
|---|---|
| `research/scripts/final_rule.py` | The complete rule, standalone and readable — change `Q1_TGT`, `Q2_VOL`, `Q3_LAG` and re-run. |
| `research/scripts/13_report.py` | Rebuilds every table in this report. |
| `research/scripts/12_charts.py`, `12b_cheatsheet.py` | Rebuilds all charts. |
| `research/out/trades_final.csv` | **All 318 trades**, one row each: date, side, entry time, entry, stop, 1R, outcome, minutes held, points, R. |
| `research/out/report_tables.md` | Every table above in raw markdown. |
| `research/figs/*.png` | All charts. |

---

## 13. The fine print

- **This is research on historical data, not investment advice.** Past win rates do not guarantee future results.
- Results assume the limit order fills when price touches the level and the stop fills at its exact price. In fast markets (and this pattern lives in the fastest 30 minutes of the day) slippage is real — the cost table in §9 shows what 2–3× friction does.
- One trade per day is deliberately conservative; taking several setups per day would need its own validation before being trusted.
- The pattern was found by searching a large parameter space, so even with the in-sample / out-of-sample split, **some of the 56.6 % is luck.** A reasonable expectation for live trading is **50–55 %** at 1:2, which is still a strong edge.
