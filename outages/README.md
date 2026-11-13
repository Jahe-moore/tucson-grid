# What Do Monsoon Power Outages Cost Tucson?

**Status 2026-11-10: v3 done** (paper, 34-slide deck, talk track). v2 applied Jake's first external logic review
(restoration measured properly, uncertain gaps flagged, associations, precision and rolling validation, tree as an
alternative). v3 applies the second review: the $ range is labeled a one-at-a-time sensitivity range with stacked corners
shown, business exposure among interrupted customers tested, night scenarios priced on the cost model's own length measure
(39%, not Model 2's 61%), set-aside events compared, errors clustered by storm date, 3 PM exclusion uses the 2:45 PM count,
tree pruned with season folds, leap-year-safe season day, ERA5 vs. forecast archive dates, EAGLE-I yearly files cited.
Jake kept the long paper and long video; red circles are off the section dividers.
Local only: no repo, site page or resume line until Jake says yes. A separate operations project may follow.

## Files

| File | What |
|---|---|
| `storm_outage_cost_jakemoore.Rmd` | The paper: R Markdown, sections 1-12 |
| `storm_outage_cost_jakemoore.pdf` | Knitted paper (HTML printed by Chrome) |
| `build_paper.ps1` | One command: knit, print the PDF, write the `.R` |
| `deck\storm_outage_cost_jakemoore.pptx` | 34-slide deck on Jake's ESOC 214 deck as template (ChronicleVTI theme, Univers Condensed / Calisto MT), speaker notes on every slide |
| `deck\deck_script.md` | Talk track, about 30 minutes (v4: each slide opens on what is on screen), Wispr check 10/10. Edit here, then rebuild |
| `deck\storm_outage_cost_jakemoore_10min.pptx`, `deck\mini_script.md` | 10-minute version: 16 of the 34 slides (`MINI_KEEP` in `build_deck.py`), own script, 10/10. Build with `python deck/build_deck.py --mini`; the full deck is unchanged |
| `deck\deck_charts.R`, `deck\build_deck.py` | After `build_paper.ps1`: `Rscript deck/deck_charts.R` (17 charts + `numbers.json`), then `python deck/build_deck.py` |
| `deck\img\` | Wikimedia Commons photos, credits in `credits.json` (mostly A Guy Named Nyal, CC BY-SA 2.0) |
| `storm_outage_cost_jakemoore.R` | Code only (`knitr::purl`) |
| `paper.css` | Makes the HTML knit look like the LaTeX `pdf_document` |
| `pull_data.py` | Re-pulls every source into `data\` (`--outages` re-streams EAGLE-I, about 7 GB) |
| `data\` | Pima outages and EAGLE-I quality files (`raw\`), weather, NOAA reports, TEP customers and sales, LBNL Tables ES-1 and ES-2, CPI-U, EIA-861 reliability |

**PDF on JAHE:** Windows Smart App Control blocks TinyTeX's installer (and the `utf8` and `zoo` R DLLs), so LaTeX can't
run here. `build_paper.ps1` knits to HTML and prints with Chrome. Pandoc comes from RStudio.

## Headline results (2020-2025, Pima County)

| Section | Result |
|---|---|
| Cleaning | 1,321 blank + 3 out-of-range readings removed. 3,165 uncertain intervals (112 stretches) flagged; filling them adds 17.7% to outage time |
| EDA | July holds 42% of recorded outage time; June 15 to September 30 holds 66% (timing, not proof of storm cause) |
| Cost | Modeled $72.9M a year (central), all qualifying events; monsoon season about $49.3M. One-at-a-time sensitivity range $38M-$143M (not a confidence interval); stacked corners $28M-$242M. Business share of interrupted customers moves it most (-48% / +96%), then large-account count (-11% / +22%, ~590 estimated under LBNL average sizes), length proxy (±20%), gaps (+16%) |
| Model 1, MLR | Outage severity; per 1 SD: dew point +108%, daily high +98%, rain +76%, gust +63% (broadly comparable, associations); R² 0.11 on log customer-minutes |
| Model 2, MLR | 510 events with observed restoration; 86 set aside (similar size, 29% vs 50% monsoon, 8% of cost). Median 1.0 h to 10% of peak; night +61% (HC3 31-99%, clustered by storm date 31-99%) |
| Model 3, logistic | Two inputs fixed in advance; 4 days removed (5,000+ still out at 2:45 PM). Train 430/24 big, test 214/10. Test AUC 0.89 (0.80-0.98) vs 0.69 date only. Precision 15% (8 of 52 flags). Rolling AUC 0.50 (2022), 0.77 (2023), 0.85 (2024); 2025 had no big nights. Promising but unstable |
| Model 4, tree | Rule card: dew point >= 42°F before Sept 1 (365-day calendar); flags 60% of nights vs 24%; AUC 0.71. Unpruned tree 41 leaves overfits (1.00 / 0.48); season-fold pruning gives the 3-leaf card |
| Recommendations | Scenarios, not forecasts: prevention $7.3M/yr per 10% vs $5.5M for 10% faster; night difference on average outage length is +39% (restore-time and length measures correlate 0.74): full $8.7M, half $4.7M if fixable; flag as promising, not proven |

## Rules

- Public data only. Never imply TEP or Trico endorsed or supplied anything.
- Every number in prose is computed inline in the Rmd; re-knit after any data change.
- Brand surfaces go through `personal-brand`; nothing publishes without Jake's yes.
