# Slide versions of the paper's charts, plus teaching charts, from the same analysis code.
# Run from the project folder:  Rscript deck/deck_charts.R   (after the paper's .R exists: build_paper.ps1)
pdf(NULL)                                   # keep the paper's own plots off-screen
source("storm_outage_cost_jakemoore.R", echo = FALSE, print.eval = FALSE)
dir.create("deck/charts", showWarnings = FALSE)

red <- "#8B0000"; green <- "#006400"; ink <- "#1C1C1C"; grey <- "#9A9A9A"
deck_theme <- theme_minimal(base_size = 17, base_family = "sans") +
  theme(plot.title = element_text(face = "bold", size = 19, color = ink),
        plot.subtitle = element_text(size = 14, color = "#444444"),
        plot.caption = element_text(size = 11, color = "#666666"),
        axis.text = element_text(color = "#333333"), panel.grid.minor = element_blank(),
        legend.position = "none", plot.margin = margin(10, 34, 10, 10))
save <- function(p, name, w = 7.6, h = 4.9) ggsave(file.path("deck/charts", name), p, width = w, height = h, dpi = 220, bg = "white")

# 1. Outage time by month
save(ggplot(by_month, aes(month, cust_min, fill = month %in% c("Jul", "Aug"))) +
  geom_col(width = 0.78) +
  geom_text(aes(label = scales::percent(share, 1)), vjust = -0.45, size = 4.6) +
  scale_fill_manual(values = c(`FALSE` = green, `TRUE` = red)) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
  labs(title = paste0("July Holds ", scales::percent(jul, 1), " of Recorded Outage Time"),
       subtitle = "Customer-minutes without power, Pima County, 2020-2025",
       x = NULL, y = "Customer-minutes (millions)", caption = "Source: EAGLE-I (Oak Ridge National Laboratory)") + deck_theme,
  "c01_month.png", 8.2, 4.9)

# 2. The worst night, with the 3 PM-6 AM storm-night window marked
w0 <- as.POSIXct("2023-07-28 15:00", tz = "America/Phoenix"); w1 <- as.POSIXct("2023-07-29 06:00", tz = "America/Phoenix")
worst_curve <- outage_series %>% filter(time >= as.POSIXct("2023-07-28 12:00", tz = "America/Phoenix"),
                                        time <= as.POSIXct("2023-07-29 20:00", tz = "America/Phoenix"))
save(ggplot(worst_curve, aes(time, customers_out)) +
  annotate("rect", xmin = w0, xmax = w1, ymin = -Inf, ymax = Inf, fill = "#EFE7EC") +
  annotate("text", x = w0 + hours(1), y = 58500, label = "Storm night: 3 PM to 6 AM", hjust = 0, size = 4.6, color = "#734B67") +
  geom_area(fill = red, alpha = 0.85) + geom_line(color = ink, linewidth = 0.5) +
  scale_y_continuous(labels = scales::comma, limits = c(0, 61000)) +
  scale_x_datetime(date_labels = "%a %l %p", date_breaks = "6 hours") +
  annotate("text", x = as.POSIXct("2023-07-29 07:00", tz = "America/Phoenix"), y = 47000,
           label = "Peak: 54,076 out", hjust = 0, size = 5) +
  labs(title = "July 28, 2023: The Worst Night in Six Years", subtitle = "Customers without power, every 15 minutes",
       x = NULL, y = "Customers out", caption = "Shaded red area = customer-minutes. Source: EAGLE-I") + deck_theme,
  "c02_worst_night.png", 8.2, 4.7)

# 3. Humidity boxplot
save(ggplot(monsoon_nights, aes(factor(big_night, labels = c("Normal night", "Big outage night")), noon_dew, fill = factor(big_night))) +
  geom_boxplot(width = 0.5, outlier.alpha = 0.35) + scale_fill_manual(values = c(`0` = green, `1` = red)) +
  labs(title = "Big Outage Nights Start Humid", subtitle = "Dew point at noon, monsoon season 2020-2025",
       x = NULL, y = "Noon dew point (°F)", caption = "Source: EAGLE-I, Open-Meteo") + deck_theme,
  "c03_humidity.png", 6.4, 5.0)

# 4. Annual cost
save(ggplot(annual_cost, aes(factor(year), cost_m, fill = season)) + geom_col(width = 0.72) +
  scale_fill_manual(values = c(monsoon_cost = red, rest_cost = green), labels = c("Monsoon season", "Rest of year")) +
  scale_y_continuous(labels = scales::dollar_format(suffix = "M")) +
  labs(title = "Modeled Outage Cost by Year", subtitle = "Homes and businesses, base assumptions, 2025 dollars",
       x = NULL, y = NULL, fill = NULL, caption = "Source: EAGLE-I, LBNL-6941E, EIA-861M, BLS CPI-U") +
  deck_theme + theme(legend.position = "top", legend.justification = "left"),
  "c04_annual_cost.png", 7.0, 5.0)

# 5. LBNL cost curve
curve_df <- tibble(minutes = seq(5, 960, by = 5)) %>% mutate(cost = cost_per_customer(minutes))
save(ggplot(curve_df, aes(minutes / 60, cost)) + geom_line(color = red, linewidth = 1.6) +
  geom_point(data = tibble(m = duration_points, c = blended_2013 * cpi_factor), aes(m / 60, c), size = 3, color = ink) +
  scale_y_continuous(labels = scales::dollar) +
  labs(title = "Cost Climbs Slowly With Length", subtitle = "Blended TEP customer, per outage, 2025 dollars",
       x = "Hours without power", y = NULL, caption = "Dots: LBNL survey points. Line: straight-line interpolation") + deck_theme,
  "c05_cost_curve.png", 6.6, 4.8)

# 5b. Sensitivity: how far each assumption moves the cost
sens_plot <- sensitivity %>% filter(Type == "One at a time") %>% mutate(Assumption = factor(Assumption, rev(Assumption)), chg = value / avg_cost - 1)
save(ggplot(sens_plot, aes(chg, Assumption, fill = chg > 0)) + geom_col(width = 0.6) +
  geom_vline(xintercept = 0, color = ink) +
  geom_text(aes(label = scales::percent(chg, 1), hjust = ifelse(chg > 0, -0.15, 1.15)), size = 4.8) +
  scale_fill_manual(values = c(`TRUE` = red, `FALSE` = green)) +
  scale_x_continuous(labels = scales::percent, expand = expansion(mult = 0.25)) +
  labs(title = "What Moves the Estimate", subtitle = "One assumption changed at a time",
       x = NULL, y = NULL, caption = "Base case: modeled 2020-2025 average") + deck_theme + theme(plot.title.position = "plot"),
  "c15_sensitivity.png", 8.4, 5.0)

# 6. Model 1 teaching scatter
save(ggplot(monsoon_nights, aes(noon_dew, log1p(night_cmin))) +
  geom_point(alpha = 0.35, color = green) + geom_smooth(method = "lm", se = FALSE, color = red, linewidth = 1.4) +
  labs(title = "One Input, One Line", subtitle = "648 monsoon nights, noon dew point only",
       x = "Noon dew point (°F)", y = "log(customer-minutes + 1)", caption = "Source: EAGLE-I, Open-Meteo") + deck_theme,
  "c06_mlr_scatter.png", 6.6, 4.8)

# 7. Model 1 standardized effects with 95% intervals
std_plot <- tidy(model1_std, conf.int = TRUE) %>% filter(term != "(Intercept)") %>%
  mutate(term = c(paste0("Peak gust (1 SD = ", round(sd(monsoon_nights$storm_gust), 1), " mph)"),
                  paste0("Rain (1 SD = ", round(sd(monsoon_nights$storm_rain), 2), " in)"),
                  paste0("Noon dew point (1 SD = ", round(sd(monsoon_nights$noon_dew), 1), "°F)"),
                  paste0("Daily high (1 SD = ", round(sd(monsoon_nights$day_high), 1), "°F)")),
         across(c(estimate, conf.low, conf.high), ~ (exp(.x) - 1) * 100))
save(ggplot(std_plot, aes(estimate, reorder(term, estimate))) +
  geom_errorbarh(aes(xmin = conf.low, xmax = conf.high), height = 0.2, color = grey, linewidth = 1) +
  geom_point(size = 4, color = red) +
  geom_text(aes(label = paste0("+", round(estimate), "%")), vjust = -1.1, size = 4.8) +
  scale_x_continuous(limits = c(0, NA), labels = function(x) paste0("+", x, "%")) +
  labs(title = "Associations on a Common Scale", subtitle = "Per 1 standard deviation, 95% intervals",
       x = NULL, y = NULL, caption = "Model 1, 648 monsoon nights, others held fixed. R² = 0.11") + deck_theme,
  "c07_mlr_effects.png", 8.0, 4.7)

# 8. Residuals
save(ggplot(augment(model1), aes(.fitted, .resid)) + geom_point(alpha = 0.35, color = green) +
  geom_hline(yintercept = 0, linetype = "dashed", color = red) +
  labs(title = "Residuals vs. Fitted", subtitle = "The diagonal edge is the zero-outage floor",
       x = "Fitted log(customer-minutes)", y = "Residual", caption = "Model 1") + deck_theme,
  "c08_residuals.png", 6.4, 4.8)

# 9. Model 2 effects with robust intervals
m2_plot <- tidy(model2) %>% filter(term != "(Intercept)") %>%
  mutate(se = robust_se[term], sc = ifelse(term == "log(peak)", log(2), 1),
         est = (exp(estimate * sc) - 1) * 100, lo = (exp((estimate - 1.96 * se) * sc) - 1) * 100,
         hi = (exp((estimate + 1.96 * se) * sc) - 1) * 100,
         term = dplyr::recode(term, `log(peak)` = "Twice as many customers out", night = "Peaks at night (8 PM-6 AM)",
                              monsoonTRUE = "Monsoon season", weekend = "Weekend", storm_rain_tenths = "+0.1 inch rain",
                              back_to_back = "Back-to-back event", storm_gust = "+1 mph gust"))
save(ggplot(m2_plot, aes(est, reorder(term, est))) +
  geom_vline(xintercept = 0, color = ink) +
  geom_errorbarh(aes(xmin = lo, xmax = hi), height = 0.2, color = grey, linewidth = 1) +
  geom_point(aes(shape = term == "Peaks at night (8 PM-6 AM)"), size = 4, color = red) +
  geom_text(aes(label = paste0(ifelse(est > 0, "+", ""), round(est), "%")), vjust = -1.1, size = 4.6) +
  scale_shape_manual(values = c(`TRUE` = 15, `FALSE` = 16)) +
  labs(title = "What Goes With Slower Restoration", subtitle = "% change in restoration time, robust 95% intervals",
       x = NULL, y = NULL, caption = paste0("Model 2, ", nrow(events_m2), " events with measured restoration. Night, clustered by storm date: +",
                         round(night_cl[1]), "% to +", round(night_cl[2]), "%")) + deck_theme,
  "c09_restore_effects.png", 8.0, 4.9)

# 10. The S-curve
s_df <- tibble(noon_dew = seq(20, 72, by = 0.5), high_by_3pm = median(train_data$high_by_3pm)) %>%
  mutate(p = predict(logit_model, ., type = "response"))
save(ggplot(s_df, aes(noon_dew, p)) + geom_line(color = red, linewidth = 1.6) +
  geom_rug(data = train_data %>% filter(big_night == 1), aes(noon_dew, 0), inherit.aes = FALSE, sides = "b", color = ink, length = unit(0.05, "npc")) +
  scale_y_continuous(labels = scales::percent) +
  labs(title = "Logistic Regression Bends a Line Into a Probability", subtitle = "Chance of a big night by noon dew point, heat held at its median",
       x = "Noon dew point (°F)", y = "Predicted chance", caption = paste0("Ticks along the bottom: the ", sum(train_data$big_night), " big nights in the training years")) + deck_theme,
  "c10_scurve.png", 7.4, 4.8)

# 11. ROC (line type as well as color)
save(ggplot(plot_data, aes(FPR, TPR, color = model, linetype = model)) + geom_line(linewidth = 1.3) +
  geom_abline(intercept = 0, slope = 1, linetype = "dotted", color = grey) +
  scale_color_manual(values = c(ink, red)) +
  labs(title = "ROC Curve, 2024-2025 Test Years", x = "False positive rate", y = "True positive rate",
       color = NULL, linetype = NULL, caption = "Dotted line: a coin flip") +
  deck_theme + theme(legend.position = "bottom", legend.text = element_text(size = 13)),
  "c11_roc.png", 6.4, 5.4)

# 12. Overfitting: train vs test AUC
ovf <- comparison %>% pivot_longer(c(`Train AUC`, `Test AUC`), names_to = "set", values_to = "auc") %>%
  mutate(set = factor(set, c("Train AUC", "Test AUC")),
         Model = factor(Model, c("Logistic regression (Model 3)", "Rule-card tree (Model 4)", "Unrestricted tree, no pruning", "Calendar only"),
                        c("Logistic\nregression", "Rule-card\ntree", "Unpruned\ntree", "Calendar\nonly")))
save(ggplot(ovf, aes(Model, auc, fill = set)) + geom_col(position = position_dodge(0.75), width = 0.7) +
  geom_text(aes(label = sprintf("%.2f", auc)), position = position_dodge(0.75), vjust = -0.4, size = 4.6) +
  scale_fill_manual(values = c(`Train AUC` = grey, `Test AUC` = red)) + coord_cartesian(ylim = c(0.4, 1.05)) +
  labs(title = "Memorizing Is Not Learning", subtitle = "AUC on the years each model trained on vs. the years it never saw",
       x = NULL, y = "AUC", fill = NULL, caption = "Train: 2020-2023. Test: 2024-2025") +
  deck_theme + theme(legend.position = "top", legend.justification = "left"),
  "c12_overfit.png", 7.6, 4.9)

# 13. Scenarios (hypothetical)
sc <- scenarios %>% mutate(Scenario = c("10% fewer customers\ninterrupted", "Every outage restored\n10% faster",
                                        "Night outages at\ndaytime pace", "Half the night\ndifference closed"),
                           lever = c("Prevention", "Speed", "Night difference", "Night difference"))
save(ggplot(sc, aes(reorder(Scenario, value), value / 1e6, fill = lever)) + geom_col(width = 0.62) +
  geom_text(aes(label = paste0("$", sprintf("%.1f", value / 1e6), "M")), hjust = -0.12, size = 5.2) + coord_flip() +
  scale_fill_manual(values = c(Prevention = green, Speed = grey, `Night difference` = red)) +
  scale_y_continuous(labels = scales::dollar_format(suffix = "M"), expand = expansion(mult = c(0, 0.2))) +
  labs(title = "Hypothetical Annual Benefit", subtitle = "Base cost assumptions, 2025 dollars",
       x = NULL, y = NULL, fill = NULL, caption = "Benefit scenarios, not forecasts. Cost of achieving each is not included") +
  deck_theme + theme(legend.position = "top", legend.justification = "left"),
  "c13_scenarios.png", 7.6, 4.8)

# 14. Rule-card tree
png("deck/charts/c14_tree.png", width = 7.6, height = 4.8, units = "in", res = 220)
rpart.plot(rule_tree, type = 2, extra = 104, box.palette = c("#CFE6D3", "#F1C9C9"), fallen.leaves = TRUE, varlen = 0,
           split.yshift = 1.4, cex = 1.15, branch.lwd = 2, main = "")
dev.off()

# 16. Rolling-origin validation
roll_plot <- rolling %>% mutate(label = ifelse(is.na(AUC), "no big\nnights", sprintf("%.2f", AUC)), AUCp = replace_na(AUC, 0))
save(ggplot(roll_plot, aes(factor(`Test year`), AUCp)) +
  geom_hline(yintercept = 0.5, linetype = "dotted", color = grey) +
  geom_col(width = 0.6, fill = red) + geom_text(aes(y = pmax(AUCp, 0) + 0.04, label = label), size = 4.8, vjust = 0) +
  scale_y_continuous(limits = c(0, 1.08), breaks = seq(0, 1, 0.25)) +
  labs(title = "Year by Year, the Flag Is Uneven", subtitle = "Trained on every earlier year, tested on one year at a time",
       x = "Test year", y = "AUC", caption = "Dotted line: a coin flip. 2025 had no big outage nights") + deck_theme,
  "c16_rolling.png", 6.4, 4.8)

# 17. Precision-recall
save(ggplot(pr, aes(recall, precision)) +
  geom_step(color = red, linewidth = 1.2) +
  geom_hline(yintercept = mean(test_data$big_night), linetype = "dashed", color = grey) +
  annotate("point", x = sens, y = prec, size = 4, color = ink) +
  annotate("label", x = sens - 0.02, y = prec + 0.2, label = paste0("Operating cutoff:
", round(prec * 100), "% of flags real"), label.size = 0,
           hjust = 1, size = 4.6) +
  scale_x_continuous(labels = scales::percent) + scale_y_continuous(labels = scales::percent) +
  labs(title = "How Many Flags Were Real?", subtitle = "Precision vs. recall, 2024-2025 test years",
       x = "Big nights caught (recall)", y = "Flags that were real (precision)", caption = "Dashed line: the share of nights that are big") + deck_theme,
  "c17_precision.png", 6.6, 4.8)

# Numbers the slides quote
nums <- list(
  readings = nrow(outages_raw), intervals = nrow(outage_series), removed = as.list(removed),
  uncertain_int = sum(outage_series$uncertain), uncertain_runs = nrow(gap_runs), gap_effect = cm_interp / cm_base - 1,
  nights = nrow(storm_nights), events = nrow(events), events_m2 = nrow(events_m2), gap_touch = sum(!events$censored & events$gap_touch),
  monsoon_nights = nrow(monsoon_nights), avg_cost = avg_cost, sens = setNames(as.list(sensitivity$value), sensitivity$Assumption),
  sens_lo = sens_range[1], sens_hi = sens_range[2], res_floor = avg_res, mons_cost_share = mons_cost_share,
  worst_year = worst_yr$c, home_share = home_share, large_n = large_n, weights = as.list(weights), cpi = cpi_factor,
  jul = jul, aug = aug, mons_share = mons_share, top8 = top8_share, top_night_cmin = top_night$night_cmin,
  dew_big = dew_med$m[dew_med$big_night == 1], dew_norm = dew_med$m[dew_med$big_night == 0],
  m1_r2 = m1r2, m1b_r2 = m1br2, vif = as.list(round(vif(model1), 2)), std = as.list(std_eff),
  m1_pct = list(gust = pct1("storm_gust"), rain = pct1("storm_rain_tenths"), dew = pct1("noon_dew"), high = pct1("day_high")),
  night_pct = night_pct, night_ci = night_ci, night_trim = night_trim, size_pct = size_pct, med_restore_hrs = med_restore,
  m2_table = model2_table, already_out = already_out,
  train_n = nrow(train_data), train_big = sum(train_data$big_night), test_n = nrow(test_data), test_big = sum(test_data$big_night),
  or_dew = orr("noon_dew"), or_high = orr("high_by_3pm"), auc_full = as.numeric(auc(roc_full)),
  auc_test = as.numeric(auc(roc_test)), auc_train = as.numeric(auc(roc_train)), auc_cal = as.numeric(auc(roc_calendar)),
  auc_lo = auc_ci[1], auc_hi = auc_ci[3], p_cal = rt$p.value, rolling = rolling,
  cm = list(tp = tp, fn = fn, fp = fp, tn = tn), sens = as.numeric(sens), spec = as.numeric(spec), bal = as.numeric(bal),
  prec = as.numeric(prec), cut_table = cutoff_compare, comparison = comparison, rule_dew = rule_dew, free_leaves = free_leaves,
  tree_flag = tree_flag, scen = scenarios$value, flag_share = flag_share, tgt_share = tgt_flag / tgt_all,
  night_share = night_share, validation = validation,
  exp_half = exp_half, exp_double = exp_double, combo_low = combo_low, combo_high = combo_high, mons_cost = mons_cost,
  large_half = large_half, large_double = large_double,
  night_cl = as.numeric(night_cl), selection = selection, link_cor = link_cor, link_el = as.numeric(link_el),
  night_len = night_len, night_len_ci = as.numeric(night_len_ci), rule_date = rule_date, rule_sd = rule_sd,
  random_leaves = random_leaves, season_leaves = season_leaves, free_train = free_train, free_test = free_test,
  rule_leaves = rule_leaves)
names(nums)[names(nums) == "sens"][1] <- "sensitivity"
jsonlite::write_json(nums, "deck/numbers.json", auto_unbox = TRUE, digits = 6, pretty = TRUE)
cat("charts and numbers written\n")
