## ----setup, include=FALSE-----------------------------------------------------
knitr::opts_chunk$set(echo = TRUE, message = FALSE, warning = FALSE, fig.width = 7.5, fig.height = 4.4, dpi = 150)
library(tidyverse)
library(lubridate)
library(broom)
library(car)
library(pROC)
library(caret)
library(rpart)
library(rpart.plot)
library(knitr)
# Print tables as plain data frames (tibble's printer needs a library this machine blocks)
print.tbl_df <- function(x, ...) print(as.data.frame(x), ...)
print.tbl <- print.tbl_df
fmt <- function(x, d = 0) trimws(format(round(x, d), big.mark = ",", nsmall = d))
dollars <- function(x) paste0("\\$", fmt(x))   # escaped so two amounts in one table are not read as math
pct <- function(x, d = 0) scales::percent(x, accuracy = 10^-d)
f2 <- function(x) sprintf("%.2f", x)


## -----------------------------------------------------------------------------
# Load the six yearly outage files (Pima County rows, FIPS 04019)
outage_files <- list.files("data/raw", pattern = "eaglei_pima_", full.names = TRUE)
outages_raw <- map_dfr(outage_files, ~ read_csv(.x, col_types = cols(.default = "c")) %>%
  rename(customers_out = 4) %>%           # the 2023 file names this column "sum"
  select(customers_out, run_start_time))

weather_raw <- read_csv("data/tucson_weather_hourly.csv", col_types = cols(local_time = "c"))
storms_raw  <- read_csv("data/noaa_storm_events_pima.csv")
customers   <- read_csv("data/tep_customers_2025.csv")
lbnl_cost   <- read_csv("data/lbnl_cost_per_event_2013usd.csv")
lbnl_timing <- read_csv("data/lbnl_cost_by_timing_2013usd.csv")
cpi         <- read_csv("data/cpi_u_annual.csv")
reliability <- read_csv("../peak/data/eia861_reliability.csv")   # the one copy, shared with the peak-demand study


## -----------------------------------------------------------------------------
# Glimpse the data
glimpse(outages_raw)
glimpse(weather_raw)


## -----------------------------------------------------------------------------
# Total N/A Values
sum(is.na(outages_raw$customers_out))
sum(is.na(weather_raw))

# Percentage of N/A Data
(sum(is.na(outages_raw$customers_out)) / nrow(outages_raw)) * 100


## -----------------------------------------------------------------------------
step1 <- outages_raw %>% mutate(customers_out = as.numeric(customers_out)) %>% filter(!is.na(customers_out))
step2 <- step1 %>% mutate(time = with_tz(ymd_hms(run_start_time, tz = "UTC"), "America/Phoenix")) %>%
  filter(year(time) %in% 2020:2025)
outages_clean <- step2 %>% distinct(time, .keep_all = TRUE) %>% select(time, customers_out)

removed <- c(blank = nrow(outages_raw) - nrow(step1), outside_2020_2025 = nrow(step1) - nrow(step2),
             duplicate = nrow(step2) - nrow(outages_clean))
removed


## -----------------------------------------------------------------------------
outage_series <- tibble(time = seq(min(outages_clean$time), max(outages_clean$time), by = "15 min")) %>%
  left_join(outages_clean, by = "time") %>%
  mutate(observed = !is.na(customers_out),
         before = customers_out, after = customers_out) %>%
  fill(before, .direction = "down") %>% fill(after, .direction = "up") %>%
  mutate(gap_id = cumsum(observed),
         uncertain = !observed & before >= 500) %>%
  group_by(gap_id) %>%
  mutate(pos = row_number() - 1, len = n() - 1) %>% ungroup() %>%
  mutate(customers_out_interp = case_when(observed ~ customers_out,
                                          uncertain ~ before + (replace_na(after, 0) - before) * pos / (len + 1),
                                          TRUE ~ 0),
         customers_out = replace_na(customers_out, 0)) %>%
  select(time, customers_out, customers_out_interp, observed, uncertain)

gap_runs <- outage_series %>% mutate(run = cumsum(uncertain != lag(uncertain, default = FALSE))) %>%
  filter(uncertain) %>% count(run)
expected_intervals <- as.numeric(difftime(as.POSIXct("2026-01-01", tz = "America/Phoenix"),
                                          as.POSIXct("2020-01-01", tz = "America/Phoenix"), units = "mins")) / 15

tibble(intervals = nrow(outage_series), expected_for_six_full_years = expected_intervals,
       first = format(min(outage_series$time)), last = format(max(outage_series$time)),
       missing_filled_zero = sum(!outage_series$observed), uncertain_intervals = sum(outage_series$uncertain),
       uncertain_stretches = nrow(gap_runs))


## ----include=FALSE------------------------------------------------------------
cm_base <- sum(outage_series$customers_out) * 15
cm_interp <- sum(outage_series$customers_out_interp) * 15
short_hours <- (expected_intervals - nrow(outage_series)) / 4


## -----------------------------------------------------------------------------
paste(sum(removed), "readings removed:", removed["blank"], "blank,", removed["outside_2020_2025"],
      "outside 2020-2025 after the time shift,", removed["duplicate"], "duplicate.")


## -----------------------------------------------------------------------------
# Storm nights: 3 PM on day D through 5:45 AM on day D+1
nights <- outage_series %>%
  mutate(night = as_date(time - hours(15)),           # 3 PM-midnight and 12-6 AM map to the same night
         in_night = hour(time) >= 15 | hour(time) < 6) %>%
  group_by(night) %>%
  summarise(night_peak = max(customers_out[in_night], 0),
            night_cmin = sum(customers_out[in_night]) * 15,
            .groups = "drop")

# Customers still out at 2:45 PM, the last reading before the 3 PM decision
before_3pm <- outage_series %>%
  filter(hour(time) == 14, minute(time) == 45) %>%
  transmute(night = as_date(time), out_at_3pm = customers_out)

weather <- weather_raw %>% mutate(time = ymd_hm(local_time, tz = "America/Phoenix"), day = as_date(time))
wx_by_3pm <- weather %>% filter(hour(time) < 15) %>% group_by(day) %>%
  summarise(noon_dew = dewpoint_f[hour(time) == 12][1], high_by_3pm = max(temp_f),
            gust_by_3pm = max(gust_mph), rain_by_3pm = sum(precip_in), .groups = "drop")
wx_storm <- weather %>% filter(hour(time) >= 12) %>% group_by(day) %>%
  summarise(storm_gust = max(gust_mph), storm_rain = sum(precip_in), .groups = "drop")
wx_day <- weather %>% group_by(day) %>%
  summarise(day_dew = mean(dewpoint_f), day_high = max(temp_f), .groups = "drop")

storm_reports <- storms_raw %>%
  mutate(day = as_date(dmy_hms(BEGIN_DATE_TIME, tz = "America/Phoenix"))) %>%
  group_by(day) %>%
  summarise(wind_reports = sum(EVENT_TYPE == "Thunderstorm Wind"),
            flood_reports = sum(EVENT_TYPE %in% c("Flash Flood", "Flood", "Debris Flow")),
            hail_reports = sum(EVENT_TYPE == "Hail"), .groups = "drop")

storm_nights <- nights %>% rename(day = night) %>%
  left_join(before_3pm %>% rename(day = night), by = "day") %>%
  left_join(wx_by_3pm, by = "day") %>% left_join(wx_storm, by = "day") %>% left_join(wx_day, by = "day") %>%
  left_join(storm_reports, by = "day") %>%
  mutate(across(c(wind_reports, flood_reports, hail_reports, out_at_3pm), ~ replace_na(.x, 0)),
         monsoon = (month(day) == 6 & mday(day) >= 15) | month(day) %in% 7:9,
         big_night = as.integer(night_peak >= 5000),
         season_day = yday(day) - as.integer(leap_year(day) & month(day) > 2),   # day of year on a 365-day calendar, so 244 is always September 1
         year = year(day)) %>%
  arrange(day) %>%
  mutate(prev_day_dew = lag(day_dew), prev_night_peak = lag(night_peak)) %>%
  filter(year %in% 2020:2025, !is.na(prev_day_dew), !is.na(noon_dew))

# Outage events, built by a function so the cost sensitivity can rebuild them with other settings
build_events <- function(series, value = "customers_out", on_thr = 500, peak_thr = 1000) {
  x <- series[[value]]; unc <- series$uncertain; tm <- series$time
  runs <- rle(x >= on_thr); run_end <- cumsum(runs$lengths); run_start <- run_end - runs$lengths + 1
  spans <- tibble(start = run_start[runs$values], end = run_end[runs$values])
  keep <- c(TRUE, spans$start[-1] - spans$end[-nrow(spans)] > 4)       # join runs less than an hour apart
  spans <- spans %>% mutate(grp = cumsum(keep)) %>% group_by(grp) %>%
    summarise(start = min(start), end = max(end), .groups = "drop")
  map_dfr(seq_len(nrow(spans)), function(k) {
    s <- spans$start[k]; e <- spans$end[k]; seg <- x[s:e]
    pk <- max(seg); pi <- s - 1 + which.max(seg)
    lim <- min(length(x), pi + 288)                                      # look up to 72 hours ahead
    back <- which(x[pi:lim] <= 0.1 * pk)[1]
    stop_i <- if (is.na(back)) lim else pi + back - 1
    tibble(start = s, end = e, peak = pk, peak_time = tm[pi], cust_min = sum(seg) * 15,
           restore_hrs = if (is.na(back)) NA_real_ else (back - 1) * 0.25,
           censored = is.na(back), gap_touch = any(unc[pi:stop_i]), start_time = tm[s], end_time = tm[e])
  }) %>%
    filter(peak >= peak_thr) %>%
    mutate(storm_date = as_date(peak_time) - days(as.integer(hour(peak_time) < 6)),
           peak_hour = hour(peak_time),
           night = as.integer(peak_hour >= 20 | peak_hour < 6),
           monsoon = (month(storm_date) == 6 & mday(storm_date) >= 15) | month(storm_date) %in% 7:9,
           weekend = as.integer(wday(peak_time) %in% c(1, 7)),
           back_to_back = as.integer(replace_na(as.numeric(difftime(start_time, lag(end_time), units = "hours")) <= 24, FALSE)),
           avg_minutes_out = cust_min / peak)
}

events <- build_events(outage_series) %>% left_join(wx_storm, by = c("storm_date" = "day"))

tibble(n_storm_nights = nrow(storm_nights), n_events = nrow(events),
       restoration_measured = sum(!events$censored & !events$gap_touch),
       never_reached_10pct = sum(events$censored), crossed_uncertain_gap = sum(!events$censored & events$gap_touch))


## -----------------------------------------------------------------------------
by_month <- outage_series %>%
  group_by(month = month(time, label = TRUE)) %>%
  summarise(cust_min = sum(customers_out) * 15 / 1e6, .groups = "drop") %>%
  mutate(share = cust_min / sum(cust_min))

ggplot(by_month, aes(x = month, y = cust_min, fill = month %in% c("Jul", "Aug"))) +
  geom_col(width = 0.8) +
  geom_text(aes(label = scales::percent(share, accuracy = 1)), vjust = -0.4, size = 3.5) +
  scale_fill_manual(values = c("FALSE" = "darkgreen", "TRUE" = "darkred")) +
  labs(
    title = paste0("July Alone Holds ", scales::percent(by_month$share[by_month$month == "Jul"], 1),
                   " of the Year's Outage Time"),
    subtitle = "Customer-minutes without power by month, Pima County, 2020-2025 (July and August in red)",
    x = "Month", y = "Customer-minutes (millions)",
    caption = "Source: EAGLE-I (Oak Ridge National Laboratory)"
  ) +
  theme_minimal(base_size = 14) +
  theme(legend.position = "none")


## ----include=FALSE------------------------------------------------------------
jul <- by_month$share[by_month$month == "Jul"]; aug <- by_month$share[by_month$month == "Aug"]
mons_share <- outage_series %>% mutate(m = (month(time) == 6 & mday(time) >= 15) | month(time) %in% 7:9) %>%
  summarise(s = sum(customers_out[m]) / sum(customers_out)) %>% pull(s)


## -----------------------------------------------------------------------------
worst <- storm_nights %>%
  arrange(desc(night_cmin)) %>%
  slice_head(n = 8) %>%
  transmute(Night = format(day, "%b %d, %Y"), `Peak customers out` = fmt(night_peak),
            `Customer-minutes (3 PM-6 AM)` = fmt(night_cmin), `Gust (mph)` = round(storm_gust),
            `Rain (in)` = round(storm_rain, 2), `NOAA wind reports` = wind_reports)
kable(worst, caption = "Eight worst outage nights (3 PM-6 AM), 2020-2025")


## ----include=FALSE------------------------------------------------------------
top8_share <- sum(sort(storm_nights$night_cmin, decreasing = TRUE)[1:8]) / sum(storm_nights$night_cmin)
top_night <- storm_nights %>% slice_max(night_cmin, n = 1)
worst_july <- storm_nights %>% arrange(desc(night_cmin)) %>% slice_head(n = 8) %>% summarise(n = sum(month(day) == 7)) %>% pull(n)


## -----------------------------------------------------------------------------
monsoon_nights <- storm_nights %>% filter(monsoon)

ggplot(monsoon_nights, aes(x = factor(big_night, labels = c("Normal night", "Big outage night")),
                           y = noon_dew, fill = factor(big_night))) +
  geom_boxplot(width = 0.55, outlier.alpha = 0.4) +
  scale_fill_manual(values = c("0" = "darkgreen", "1" = "darkred")) +
  labs(
    title = "Big Outage Nights Start With Humid Afternoons",
    subtitle = "Dew point at noon, monsoon season 2020-2025",
    x = NULL, y = "Dew point at noon (F)",
    caption = "Source: EAGLE-I, Open-Meteo"
  ) +
  theme_minimal(base_size = 14) +
  theme(legend.position = "none")


## ----include=FALSE------------------------------------------------------------
dew_med <- monsoon_nights %>% group_by(big_night) %>% summarise(m = median(noon_dew))


## -----------------------------------------------------------------------------
total_customers <- 456766   # EAGLE-I's Pima County customer count
validation <- outage_series %>%
  group_by(Year = year(time)) %>%
  summarise(`EAGLE-I minutes per customer` = round(sum(customers_out) * 15 / total_customers, 1)) %>%
  left_join(reliability %>% filter(utility == "TEP", events == "all") %>%
              transmute(Year = year, `TEP reported (all events)` = round(saidi_min, 1)), by = "Year")
kable(validation, caption = "Outage minutes per customer: county data vs. TEP's EIA-861 filing")


## -----------------------------------------------------------------------------
kable(lbnl_cost, col.names = c("Customer class", "Momentary", "30 min", "1 hour", "4 hours", "8 hours", "16 hours"),
      caption = "LBNL cost per interruption event (2013 dollars)")


## -----------------------------------------------------------------------------
# The file has one row per month of 2025: customer counts are averaged, sales are summed to a year
stopifnot(nrow(customers) == 12)
mix <- customers %>% summarise(res = mean(res_cust), ci = mean(com_cust) + mean(ind_cust),
                               ci_kwh = (sum(com_mwh) + sum(ind_mwh)) * 1000)
large_n <- (mix$ci_kwh - mix$ci * 19214) / (7140501 - 19214)     # energy balance with LBNL's average customer sizes
mix_weights <- function(large) c(Residential = mix$res, `Small C&I` = mix$ci - large, `Medium and Large C&I` = large) /
  (mix$res + mix$ci)
weights <- mix_weights(large_n)
cpi_factor <- cpi$cpi_u_annual_avg[cpi$year == 2025] / cpi$cpi_u_annual_avg[cpi$year == 2013]

duration_points <- c(5, 30, 60, 240, 480, 960)          # minutes: momentary, 30 min, 1, 4, 8, 16 hours
cost_matrix <- as.matrix(lbnl_cost[match(names(weights), lbnl_cost$customer_class), -1])
blend <- function(w) as.numeric(w %*% cost_matrix)
blended_2013 <- blend(weights)
residential_2013 <- cost_matrix[1, ]

cost_per_customer <- function(minutes, curve = blended_2013) {
  approx(duration_points, curve, xout = pmin(pmax(minutes, 5), 960))$y * cpi_factor
}

events <- events %>%
  mutate(cost = peak * cost_per_customer(avg_minutes_out),
         cost_res_only = peak * cost_per_customer(avg_minutes_out, residential_2013))

c(large_accounts = round(large_n), share_of_business_accounts = round(large_n / mix$ci, 4))
round(weights, 4)
round(cpi_factor, 3)
c(events_below_5_min = sum(events$avg_minutes_out < 5), events_above_16_hours = sum(events$avg_minutes_out > 960))


## -----------------------------------------------------------------------------
annual_cost <- events %>%
  group_by(year = year(storm_date)) %>%
  summarise(monsoon_cost = sum(cost[monsoon]) / 1e6, rest_cost = sum(cost[!monsoon]) / 1e6, .groups = "drop") %>%
  pivot_longer(c(monsoon_cost, rest_cost), names_to = "season", values_to = "cost_m")

ggplot(annual_cost, aes(x = factor(year), y = cost_m, fill = season)) +
  geom_col(width = 0.75) +
  scale_fill_manual(values = c(monsoon_cost = "darkred", rest_cost = "darkgreen"),
                    labels = c("Monsoon season", "Rest of year")) +
  scale_y_continuous(labels = scales::dollar_format(suffix = "M")) +
  labs(
    title = "Modeled Outage Cost to Pima County Each Year",
    subtitle = "Homes and businesses, outage events of 1,000+ customers (2025 dollars)",
    x = "Year", y = "Modeled cost", fill = NULL,
    caption = "Source: EAGLE-I, LBNL-6941E, EIA-861M, BLS CPI-U"
  ) +
  theme_minimal(base_size = 14)


## ----include=FALSE------------------------------------------------------------
yr_cost <- events %>% group_by(year = year(storm_date)) %>% summarise(c = sum(cost), r = sum(cost_res_only), m = sum(cost[monsoon]))
yrs_cost <- nrow(yr_cost)
avg_cost <- mean(yr_cost$c); avg_res <- mean(yr_cost$r); mons_cost_share <- sum(yr_cost$m) / sum(yr_cost$c)
home_share <- sum(events$peak * weights["Residential"] * cost_per_customer(events$avg_minutes_out, residential_2013)) / sum(events$cost)
worst_yr <- yr_cost %>% slice_max(c, n = 1)
event_share <- sum(events$cust_min) / (sum(outage_series$customers_out) * 15)


## -----------------------------------------------------------------------------
annual <- function(ev, w = weights, len_mult = 1) {
  sum(ev$peak * cost_per_customer(ev$avg_minutes_out * len_mult, blend(w))) / yrs_cost
}
# Businesses' share of interrupted customers scaled by k; homes make up the rest
exposure <- function(k, w = weights) { w[2:3] <- w[2:3] * k; w[1] <- 1 - sum(w[2:3]); w }

# Priced by season and hour of the peak (LBNL Table ES-2)
curve_for <- function(class, season, slot) {
  as.numeric(lbnl_timing %>% filter(customer_class == class, season == !!season, time_of_day == slot) %>%
               select(momentary:hr_16))
}
timed_cost <- map_dbl(seq_len(nrow(events)), function(i) {
  h <- events$peak_hour[i]; season <- ifelse(month(events$peak_time[i]) %in% 6:9, "summer", "non-summer")
  res_slot <- case_when(h >= 12 & h < 17 ~ "afternoon", h >= 17 & h < 22 ~ "evening", TRUE ~ "morning/night")
  com_slot <- case_when(h >= 6 & h < 12 ~ "morning", h >= 12 & h < 17 ~ "afternoon", TRUE ~ "evening/night")
  curve <- weights["Residential"] * curve_for("Residential", season, res_slot) +
           weights["Small C&I"] * curve_for("Small C&I", season, com_slot) +
           weights["Medium and Large C&I"] * curve_for("Medium and Large C&I", season, "all")
  events$peak[i] * cost_per_customer(events$avg_minutes_out[i], curve)
})

events_interp <- build_events(outage_series, value = "customers_out_interp")
events_wide <- build_events(outage_series, on_thr = 250, peak_thr = 500)

sensitivity <- tibble(
  Assumption = c("Base case",
                 "Half as many large business accounts", "Twice as many large business accounts",
                 "Businesses' share of those interrupted halved", "Businesses' share of those interrupted doubled",
                 "Outages 25% shorter than the proxy", "Outages 25% longer than the proxy",
                 "Uncertain gaps filled in", "Smaller events counted (peak 500+)",
                 "Priced by season and hour (Table ES-2)",
                 "Low settings together", "High settings together",
                 "Every customer priced as a home"),
  Type = c("Base", rep("One at a time", 9), "Combined", "Combined", "Floor"),
  `Annual cost` = c(annual(events),
                    annual(events, mix_weights(large_n / 2)), annual(events, mix_weights(large_n * 2)),
                    annual(events, exposure(0.5)), annual(events, exposure(2)),
                    annual(events, len_mult = 0.75), annual(events, len_mult = 1.25),
                    annual(events_interp), annual(events_wide),
                    sum(timed_cost) / yrs_cost,
                    annual(events, exposure(0.5, mix_weights(large_n / 2)), len_mult = 0.75),
                    annual(events_interp, exposure(2, mix_weights(large_n * 2)), len_mult = 1.25),
                    avg_res)) %>%
  mutate(`vs. base` = pct(`Annual cost` / `Annual cost`[1] - 1), value = `Annual cost`, `Annual cost` = dollars(`Annual cost`))
kable(sensitivity %>% select(-value), caption = "Modeled annual outage cost when assumptions change (2025 dollars)")


## ----include=FALSE------------------------------------------------------------
sv <- setNames(sensitivity$value, sensitivity$Assumption)
sens_range <- range(sensitivity$value[sensitivity$Type == "One at a time"])
large_half <- sv["Half as many large business accounts"]; large_double <- sv["Twice as many large business accounts"]
exp_half <- sv["Businesses' share of those interrupted halved"]; exp_double <- sv["Businesses' share of those interrupted doubled"]
combo_low <- sv["Low settings together"]; combo_high <- sv["High settings together"]
mons_cost <- avg_cost * mons_cost_share


## -----------------------------------------------------------------------------
monsoon_nights <- monsoon_nights %>% mutate(storm_rain_tenths = storm_rain * 10)
model1 <- lm(log1p(night_cmin) ~ storm_gust + storm_rain_tenths + noon_dew + day_high, data = monsoon_nights)

model1_table <- tidy(model1, conf.int = TRUE) %>%
  filter(term != "(Intercept)") %>%
  mutate(`% change` = round((exp(estimate) - 1) * 100, 1),
         `95% CI (%)` = paste0(round((exp(conf.low) - 1) * 100), " to ", round((exp(conf.high) - 1) * 100)),
         across(c(estimate, std.error, statistic), ~ round(.x, 3)), p.value = signif(p.value, 2)) %>%
  select(term, estimate, std.error, p.value, `% change`, `95% CI (%)`)
kable(model1_table, caption = "Model 1: log(customer-minutes + 1) on storm-night weather, per unit of each input")

model1_std <- lm(log1p(night_cmin) ~ scale(storm_gust) + scale(storm_rain_tenths) + scale(noon_dew) + scale(day_high),
                 data = monsoon_nights)
std_table <- tidy(model1_std, conf.int = TRUE) %>% filter(term != "(Intercept)") %>%
  mutate(term = gsub("scale\\(|\\)", "", term),
         `% change per 1 SD` = round((exp(estimate) - 1) * 100),
         `95% CI (%)` = paste0(round((exp(conf.low) - 1) * 100), " to ", round((exp(conf.high) - 1) * 100)),
         `1 SD equals` = c(paste(round(sd(monsoon_nights$storm_gust), 1), "mph"),
                           paste(round(sd(monsoon_nights$storm_rain), 2), "in"),
                           paste(round(sd(monsoon_nights$noon_dew), 1), "°F"),
                           paste(round(sd(monsoon_nights$day_high), 1), "°F"))) %>%
  select(term, `1 SD equals`, `% change per 1 SD`, `95% CI (%)`)
kable(std_table, caption = "The same model on standardized inputs")
glance(model1) %>% select(r.squared, adj.r.squared, nobs) %>% round(3)


## ----include=FALSE------------------------------------------------------------
pct1 <- function(term) round((exp(coef(model1)[term]) - 1) * 100, 1)
m1r2 <- summary(model1)$r.squared
model1b <- lm(log1p(night_cmin) ~ storm_gust + storm_rain_tenths + noon_dew + day_high + wind_reports + flood_reports, data = monsoon_nights)
m1br2 <- summary(model1b)$r.squared
std_eff <- setNames(std_table$`% change per 1 SD`, std_table$term)
top_std <- names(which.max(std_eff))


## -----------------------------------------------------------------------------
round(vif(model1), 2)

ggplot(augment(model1), aes(x = .fitted, y = .resid)) +
  geom_point(alpha = 0.35, color = "darkgreen") +
  geom_hline(yintercept = 0, linetype = "dashed", color = "darkred") +
  labs(
    title = "Residuals Show the Zero-Outage Floor",
    subtitle = "Model 1 residuals vs. fitted values",
    x = "Fitted log(customer-minutes)", y = "Residual",
    caption = "Source: EAGLE-I, Open-Meteo"
  ) +
  theme_minimal(base_size = 14)


## -----------------------------------------------------------------------------
events_m2 <- events %>% filter(!censored, !gap_touch, restore_hrs > 0, !is.na(storm_gust)) %>%
  mutate(storm_rain_tenths = storm_rain * 10)
c(events = nrow(events), used = nrow(events_m2), never_reached_10pct = sum(events$censored),
  crossed_uncertain_gap = sum(!events$censored & events$gap_touch))

ggplot(events_m2, aes(restore_hrs)) +
  geom_histogram(bins = 30, fill = "darkgreen", color = "white") +
  scale_x_log10() +
  labs(title = "Restoration Times Are Heavily Skewed", subtitle = "Hours until the county count falls to 10% of the peak (log scale)",
       x = "Restoration hours", y = "Events", caption = "Source: EAGLE-I") +
  theme_minimal(base_size = 14)

model2 <- lm(log(restore_hrs) ~ log(peak) + night + back_to_back + weekend + monsoon + storm_gust + storm_rain_tenths,
             data = events_m2)

# Heteroskedasticity-robust (HC3) confidence intervals, since the spread of restoration times varies by event size
robust_se <- sqrt(diag(hccm(model2, type = "hc3")))
model2_table <- tidy(model2) %>%
  mutate(robust_se = robust_se, low = estimate - 1.96 * robust_se, high = estimate + 1.96 * robust_se,
         p_robust = 2 * pnorm(-abs(estimate / robust_se))) %>%
  filter(term != "(Intercept)") %>%
  mutate(scale = ifelse(term == "log(peak)", log(2), 1),
         `% change` = round((exp(estimate * scale) - 1) * 100, 1),
         `95% CI (%)` = paste0(round((exp(low * scale) - 1) * 100), " to ", round((exp(high * scale) - 1) * 100)),
         p.value = signif(p_robust, 2), estimate = round(estimate, 3)) %>%
  select(term, estimate, p.value, `% change`, `95% CI (%)`)
kable(model2_table, caption = "Model 2: log(restoration hours), robust 95% intervals. For log(peak), the % is for twice as many customers out.")
glance(model2) %>% select(r.squared, adj.r.squared, nobs) %>% round(3)


## -----------------------------------------------------------------------------
# Intervals clustered by storm date (events from the same storm share errors)
X <- model.matrix(model2); e <- resid(model2); g <- events_m2$storm_date
XtXi <- solve(crossprod(X)); u <- rowsum(X * e, g)
G <- length(unique(g)); n <- nrow(X); k <- ncol(X)
vc_cluster <- G / (G - 1) * (n - 1) / (n - k) * XtXi %*% crossprod(u) %*% XtXi
night_cl <- (exp(coef(model2)["night"] + c(-1.96, 1.96) * sqrt(vc_cluster["night", "night"])) - 1) * 100
c(storm_dates = G, night_low = round(night_cl[1]), night_high = round(night_cl[2]))

# Are the set-aside events different?
selection <- events %>%
  mutate(group = ifelse(!censored & !gap_touch & restore_hrs > 0 & !is.na(storm_gust), "Used in Model 2", "Set aside")) %>%
  group_by(group) %>%
  summarise(Events = n(), `Median peak` = fmt(median(peak)), `Peaked at night` = pct(mean(night)),
            `Monsoon season` = pct(mean(monsoon)), `Median gust (mph)` = round(median(storm_gust, na.rm = TRUE)),
            `Share of modeled cost` = pct(sum(cost) / sum(events$cost)), .groups = "drop")
kable(selection, caption = "Events used in Model 2 vs. events set aside")

cooks <- cooks.distance(model2)
c(influential_events = sum(cooks > 4 / nrow(events_m2)))
model2_trim <- update(model2, data = events_m2[cooks <= 4 / nrow(events_m2), ])

ggplot(augment(model2), aes(.fitted, .resid)) +
  geom_point(alpha = 0.4, color = "darkgreen") +
  geom_hline(yintercept = 0, linetype = "dashed", color = "darkred") +
  labs(title = "Model 2 Residuals vs. Fitted", x = "Fitted log(restoration hours)", y = "Residual",
       caption = "Source: EAGLE-I, Open-Meteo") +
  theme_minimal(base_size = 14)


## ----include=FALSE------------------------------------------------------------
m2row <- function(term) model2_table %>% filter(.data$term == !!term)
night_pct <- m2row("night")$`% change`; night_ci <- m2row("night")$`95% CI (%)`; night_p <- m2row("night")$p.value
size_pct <- m2row("log(peak)")$`% change`
night_trim <- round((exp(coef(model2_trim)["night"]) - 1) * 100)
med_restore <- median(events_m2$restore_hrs)
sig_terms <- model2_table %>% filter(p.value < 0.05) %>% pull(term)
night_sig <- night_p < 0.05
sel_used <- selection %>% filter(group == "Used in Model 2"); sel_out <- selection %>% filter(group == "Set aside")


## -----------------------------------------------------------------------------
already_out <- sum(monsoon_nights$out_at_3pm >= 5000)
paste(already_out, "monsoon days removed: 5,000+ customers still out at 2:45 PM.")

model_data <- monsoon_nights %>%
  filter(out_at_3pm < 5000) %>%
  select(day, big_night, year, noon_dew, high_by_3pm, gust_by_3pm, rain_by_3pm, prev_day_dew, prev_night_peak, season_day) %>%
  mutate(log_prev_night_peak = log1p(prev_night_peak)) %>%
  na.omit()
table(model_data$big_night)


## -----------------------------------------------------------------------------
train_data <- model_data %>% filter(year <= 2023)
test_data  <- model_data %>% filter(year >= 2024)
c(train_nights = nrow(train_data), train_big = sum(train_data$big_night),
  test_nights = nrow(test_data), test_big = sum(test_data$big_night))


## -----------------------------------------------------------------------------
logit_model <- glm(big_night ~ noon_dew + high_by_3pm, data = train_data, family = "binomial")
full_formula <- big_night ~ noon_dew + high_by_3pm + gust_by_3pm + rain_by_3pm + prev_day_dew + log_prev_night_peak + season_day
full_model <- glm(full_formula, data = train_data, family = "binomial")

odds_table <- tidy(logit_model, conf.int = TRUE, exponentiate = TRUE) %>%
  filter(term != "(Intercept)") %>%
  mutate(across(c(estimate, std.error, statistic, conf.low, conf.high), ~ round(.x, 3)), p.value = signif(p.value, 2)) %>%
  rename(odds_ratio = estimate)
kable(odds_table, caption = "Model 3: odds ratios (trained on 2020-2023)")


## ----include=FALSE------------------------------------------------------------
orr <- function(term) exp(coef(logit_model)[term])


## -----------------------------------------------------------------------------
train_prob <- predict(logit_model, train_data, type = "response")
test_prob  <- predict(logit_model, test_data, type = "response")
roc_train <- roc(train_data$big_night, train_prob, quiet = TRUE)
roc_test <- roc(test_data$big_night, test_prob, quiet = TRUE)
roc_full <- roc(test_data$big_night, predict(full_model, test_data, type = "response"), quiet = TRUE)
calendar_model <- glm(big_night ~ season_day + I(season_day^2), data = train_data, family = "binomial")
roc_calendar <- roc(test_data$big_night, predict(calendar_model, test_data, type = "response"), quiet = TRUE)

# Two cutoffs, both set on the training years and applied unchanged to the test years:
#  - Balanced (Youden's J): the point that best balances catching big nights against false alarms
#  - Operating budget: flag the riskiest 20% of nights, about one evening in five
youden_cutoff <- coords(roc_train, "best", best.method = "youden", ret = "threshold")$threshold[1]
cutoff <- as.numeric(quantile(train_prob, 0.80))
cutoff_compare <- tibble(Cutoff = c("Balanced (Youden)", "Operating budget (top 20%)"),
                         Probability = round(c(youden_cutoff, cutoff), 3)) %>%
  rowwise() %>%
  mutate(`Test nights flagged` = sum(test_prob > Probability),
         `Big nights caught` = sum(test_prob > Probability & test_data$big_night == 1),
         `False alarms` = sum(test_prob > Probability & test_data$big_night == 0),
         Precision = pct(`Big nights caught` / `Test nights flagged`)) %>% ungroup()
kable(cutoff_compare, caption = "Cutoff choice, test years 2024-2025")

predicted_classes <- ifelse(test_prob > cutoff, 1, 0)
conf_matrix <- confusionMatrix(factor(predicted_classes, levels = 0:1), factor(test_data$big_night, levels = 0:1),
                               positive = "1")
print(conf_matrix)

auc_ci <- ci.auc(roc_test)
auc_ci
roc.test(roc_test, roc_calendar)
c(two_input_auc = round(auc(roc_test), 3), full_model_auc = round(auc(roc_full), 3))


## -----------------------------------------------------------------------------
plot_data <- bind_rows(
  tibble(model = paste0("3 PM model (AUC = ", f2(auc(roc_test)), ")"),
         FPR = 1 - roc_test$specificities, TPR = roc_test$sensitivities),
  tibble(model = paste0("Calendar only (AUC = ", f2(auc(roc_calendar)), ")"),
         FPR = 1 - roc_calendar$specificities, TPR = roc_calendar$sensitivities))

ggplot(plot_data, aes(x = FPR, y = TPR, color = model, linetype = model)) +
  geom_line(linewidth = 1) +
  geom_abline(intercept = 0, slope = 1, linetype = "dotted", color = "grey50") +
  scale_color_manual(values = c("black", "darkred")) +
  labs(
    title = paste0("ROC Curve, 2024-2025 Test Years (AUC = ", f2(auc(roc_test)), ")"),
    x = "False Positive Rate (1 - Specificity)", y = "True Positive Rate (Sensitivity)", color = NULL, linetype = NULL,
    caption = "Source: EAGLE-I, Open-Meteo"
  ) +
  theme_minimal(base_size = 14) +
  theme(legend.position = "bottom")

# Precision-recall: of the nights flagged, how many were really big?
pr <- coords(roc_test, "all", ret = c("threshold", "recall", "precision"), transpose = FALSE) %>%
  filter(!is.na(precision))
ggplot(pr, aes(recall, precision)) +
  geom_step(color = "darkred", linewidth = 1) +
  geom_hline(yintercept = mean(test_data$big_night), linetype = "dashed", color = "grey50") +
  annotate("point", x = conf_matrix$byClass["Sensitivity"], y = conf_matrix$byClass["Pos Pred Value"], size = 3) +
  scale_x_continuous(labels = scales::percent) + scale_y_continuous(labels = scales::percent) +
  labs(title = "Precision-Recall, 2024-2025 Test Years", subtitle = "Dot: the operating cutoff. Dashed line: the share of nights that are big",
       x = "Recall (big nights caught)", y = "Precision (flags that were real)", caption = "Source: EAGLE-I, Open-Meteo") +
  theme_minimal(base_size = 14)


## -----------------------------------------------------------------------------
rolling <- map_dfr(2022:2025, function(y) {
  tr <- model_data %>% filter(year < y); te <- model_data %>% filter(year == y)
  fit <- glm(big_night ~ noon_dew + high_by_3pm, data = tr, family = "binomial")
  p <- predict(fit, te, type = "response"); cut_y <- quantile(predict(fit, tr, type = "response"), 0.80)
  tibble(`Test year` = y, `Trained on` = paste0("2020-", y - 1), `Big nights` = sum(te$big_night),
         AUC = if (sum(te$big_night) > 0) round(as.numeric(auc(roc(te$big_night, p, quiet = TRUE))), 2) else NA,
         Flagged = sum(p > cut_y), Caught = sum(p > cut_y & te$big_night == 1))
}) %>% mutate(Precision = ifelse(Flagged > 0, pct(Caught / Flagged), "-"))
kable(rolling, caption = "Rolling-origin validation of the two-input model")


## ----include=FALSE------------------------------------------------------------
cm <- conf_matrix$table
tp <- cm["1", "1"]; fn <- cm["0", "1"]; fp <- cm["1", "0"]; tn <- cm["0", "0"]
sens <- conf_matrix$byClass["Sensitivity"]; spec <- conf_matrix$byClass["Specificity"]
bal <- conf_matrix$byClass["Balanced Accuracy"]; prec <- conf_matrix$byClass["Pos Pred Value"]
rt <- roc.test(roc_test, roc_calendar)
base_rate <- mean(test_data$big_night)
yd <- cutoff_compare[1, ]
roll_auc <- range(rolling$AUC, na.rm = TRUE)


## -----------------------------------------------------------------------------
set.seed(123) # for reproducibility
season_folds <- as.integer(factor(train_data$year))   # cross-validation folds are whole seasons, not random nights
tree_inputs <- big_night ~ noon_dew + high_by_3pm + gust_by_3pm + rain_by_3pm + prev_day_dew + log_prev_night_peak + season_day

# First, a tree grown with no limits, then pruned by cross-validation (random folds and whole-season folds)
best_free <- rpart(tree_inputs, data = train_data %>% mutate(big_night = factor(big_night)), method = "class",
                   parms = list(prior = c(0.5, 0.5)), control = rpart.control(cp = 0, minsplit = 2, xval = season_folds))
prune_by <- function(folds) {
  t <- rpart(tree_inputs, data = train_data %>% mutate(big_night = factor(big_night)), method = "class",
             parms = list(prior = c(0.5, 0.5)), control = rpart.control(cp = 0.001, xval = folds))
  prune(t, cp = t$cptable[which.min(t$cptable[, "xerror"]), "CP"])
}
random_free <- prune_by(10)              # random 10-fold
season_free <- prune_by(season_folds)    # whole seasons as folds
c(unpruned_leaves = sum(best_free$frame$var == "<leaf>"), random_fold_leaves = sum(random_free$frame$var == "<leaf>"),
  season_fold_leaves = sum(season_free$frame$var == "<leaf>"))

# Then a rule card: at most three questions deep, at least 20 nights per leaf
rule_tree <- rpart(tree_inputs, data = train_data %>% mutate(big_night = factor(big_night)), method = "class",
                   parms = list(prior = c(0.5, 0.5)),
                   control = rpart.control(maxdepth = 3, minbucket = 20, cp = 0.001, xval = season_folds))
rule_tree <- prune(rule_tree, cp = rule_tree$cptable[which.min(rule_tree$cptable[, "xerror"]), "CP"])

rpart.plot(rule_tree, type = 4, extra = 104, box.palette = c("#CFE6D3", "#F1C9C9"), fallen.leaves = TRUE, varlen = 0,
           main = "Big Outage Night Rule Card (trained 2020-2023)", cex = 1.0, branch.lwd = 2)

# The same tree as plain-language rules
rpart.rules(rule_tree, cover = TRUE)


## -----------------------------------------------------------------------------
tree_prob <- predict(rule_tree, test_data, type = "prob")[, "1"]
roc_tree <- roc(test_data$big_night, tree_prob, quiet = TRUE)
tree_classes <- predict(rule_tree, test_data, type = "class")
roc_free <- roc(test_data$big_night, predict(best_free, test_data, type = "prob")[, "1"], quiet = TRUE)

comparison <- tibble(
  Model = c("Logistic regression (Model 3)", "Rule-card tree (Model 4)", "Unrestricted tree, no pruning", "Calendar only"),
  `Train AUC` = round(c(auc(roc_train),
                        auc(roc(train_data$big_night, predict(rule_tree, train_data, type = "prob")[, "1"], quiet = TRUE)),
                        auc(roc(train_data$big_night, predict(best_free, train_data, type = "prob")[, "1"], quiet = TRUE)),
                        auc(roc(train_data$big_night, fitted(calendar_model), quiet = TRUE))), 2),
  `Test AUC` = round(c(auc(roc_test), auc(roc_tree), auc(roc_free), auc(roc_calendar)), 2),
  `Share of test nights flagged` = c(pct(mean(predicted_classes)), pct(mean(tree_classes == "1")), "-", "-"))
kable(comparison, caption = "Train vs. test AUC, and how often each model flags")


## ----include=FALSE------------------------------------------------------------
free_leaves <- sum(best_free$frame$var == "<leaf>")
free_train <- comparison$`Train AUC`[3]; free_test <- comparison$`Test AUC`[3]
rule_leaves <- sum(rule_tree$frame$var == "<leaf>")
rule_dew <- round(rule_tree$splits[rownames(rule_tree$splits) == "noon_dew", "index"][1])
rule_sd <- ceiling(rule_tree$splits[rownames(rule_tree$splits) == "season_day", "index"][1])
rule_date <- format(as.Date("2025-01-01") + rule_sd - 1, "%B %e") %>% gsub("  ", " ", .)
season_leaves <- sum(season_free$frame$var == "<leaf>")
random_leaves <- sum(random_free$frame$var == "<leaf>")
same_as_card <- isTRUE(all.equal(predict(season_free, test_data, type = "prob"), predict(rule_tree, test_data, type = "prob")))
tree_flag <- mean(tree_classes == "1")


## -----------------------------------------------------------------------------
# How closely do the two duration measures move together? (events used in Model 2)
link <- lm(log(avg_minutes_out) ~ log(restore_hrs), data = events_m2)
c(correlation = round(cor(log(events_m2$restore_hrs), log(events_m2$avg_minutes_out)), 2),
  elasticity = round(unname(coef(link)[2]), 2))

# The night difference measured directly on average outage length, all events with weather
events_len <- events %>% filter(!is.na(storm_gust)) %>% mutate(storm_rain_tenths = storm_rain * 10)
model2_len <- lm(log(avg_minutes_out) ~ log(peak) + night + back_to_back + weekend + monsoon + storm_gust + storm_rain_tenths,
                 data = events_len)
night_len_ci <- (exp(confint(model2_len)["night", ]) - 1) * 100
c(night_pct_avg_length = unname(round((exp(coef(model2_len)["night"]) - 1) * 100)), low = unname(round(night_len_ci[1])),
  high = unname(round(night_len_ci[2])), events = nobs(model2_len))

night_factor <- exp(coef(model2_len)["night"])     # the scenarios use the night difference in average outage length
link_cor <- cor(log(events_m2$restore_hrs), log(events_m2$avg_minutes_out)); link_el <- coef(link)[2]
night_len <- round((exp(coef(model2_len)["night"]) - 1) * 100)
night_ev <- events %>% filter(night == 1)
savings <- function(new_cost) sum(new_cost) / yrs_cost

scenarios <- tibble(
  Scenario = c("1. 10% fewer customers interrupted", "2. All outages restored 10% faster",
               "3. Night outages at daytime pace", "4. Half the night difference closed"),
  value = c(
    savings(events$cost * 0.10),
    savings(events$cost - events$peak * cost_per_customer(events$avg_minutes_out * 0.9)),
    savings(night_ev$cost - night_ev$peak * cost_per_customer(night_ev$avg_minutes_out / night_factor)),
    savings(night_ev$cost - night_ev$peak * cost_per_customer(night_ev$avg_minutes_out / sqrt(night_factor)))
  )) %>%
  mutate(`Annual benefit` = dollars(value))
kable(scenarios %>% select(-value), caption = "Hypothetical annual benefit to Pima County customers (2025 dollars, base cost assumptions)")


## -----------------------------------------------------------------------------
flagged <- test_data %>% mutate(flag = test_prob > cutoff)
backtest <- tibble(
  `Monsoon nights, 2024-2025` = nrow(flagged),
  `Nights flagged` = sum(flagged$flag),
  `Big nights caught` = sum(flagged$flag & flagged$big_night == 1),
  `Big nights missed` = sum(!flagged$flag & flagged$big_night == 1),
  `False alarms` = sum(flagged$flag & flagged$big_night == 0))
kable(backtest)

half_gap_saving <- function(ev) ev$cost - ev$peak * cost_per_customer(ev$avg_minutes_out / sqrt(night_factor))
test_night_ev <- night_ev %>% filter(year(storm_date) %in% 2024:2025) %>%
  mutate(flagged = storm_date %in% flagged$day[flagged$flag])
targeting <- tibble(
  `Night outages, 2024-2025` = c("All night outages (year-round)", "After a flagged afternoon"),
  Events = c(nrow(test_night_ev), sum(test_night_ev$flagged)),
  `Half-difference benefit per year` = c(sum(half_gap_saving(test_night_ev)),
                                         sum(half_gap_saving(test_night_ev[test_night_ev$flagged, ]))) / 2) %>%
  mutate(Share = pct(`Half-difference benefit per year` / `Half-difference benefit per year`[1]),
         `Half-difference benefit per year` = dollars(`Half-difference benefit per year`))
kable(targeting, caption = "How much of the night scenario follows a flagged afternoon, test seasons")


## ----include=FALSE------------------------------------------------------------
s_prev <- scenarios$value[1]; s_fast <- scenarios$value[2]; s_night <- scenarios$value[3]; s_half <- scenarios$value[4]
flag_share <- mean(flagged$flag)
night_share <- sum(night_ev$cost) / sum(events$cost)
tgt_all <- sum(half_gap_saving(test_night_ev)) / 2
tgt_flag <- sum(half_gap_saving(test_night_ev[test_night_ev$flagged, ])) / 2

