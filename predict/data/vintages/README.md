# Vintage decision packs (`data/vintages/`)

Each `decisions_{WINDOW}.json` freezes the EXACT decision inputs used by
`scripts/backtest_pit_vintages.py` for one window (per ticker: vintage EPS,
sales base/prev/latest, CFO/PAT sums, entry price, DMA200, entry date).

Status: **as-served snapshots, NOT as-reported archives.** Screener rewrites
history (restatements, bonus/split adjustments), so a frozen pack still
carries restatement residual versus what was knowable on the entry date.
What freezing buys:

- Reproducibility: re-runs can diff live inputs against the frozen pack.
  Any restatement since the freeze is printed as `[DRIFT]` lines and does
  not silently change published numbers.
- The residual is therefore measured per run, not closed. Closing it
  requires archived annual-report vintages (no programmatic source found;
  check BSE filing PDFs per name if a judge asks).

Refresh: packs rewrite on every `backtest_pit_vintages.py` run that reaches
the save step. Commit the refreshed packs alongside
`scripts/pit_calibration.json` so the numbers stay jointly reproducible.

Measured drift (Oct-26 smallcap cache vs live Oct-29, FY23 columns):
ACE sales 2160->2158, PAT 173->161 (-7%), EPS 14.41->13.54 (-6%);
KSB and TITAGARH unchanged. Single-digit restatements inside three days —
enough to flip close gates, which is why frozen packs are mandatory.
