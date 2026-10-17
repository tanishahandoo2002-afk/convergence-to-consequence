# RQ3 meta-regression (plan §8.3 steps 9-10): three-level random-effects models (effects within studies)
# with CR2 robust inference; number of sessions is a covariate in every model.
# `Rscript rq3_stimulation/models.R --run` fits H3a-H3d and bias checks for r = .3/.5/.7 and draws RoB 2 plots.
suppressPackageStartupMessages({library(metafor); library(clubSandwich)})

fit_mv <- function(mods, data) {
  rma.mv(yi, vi, mods = mods, random = ~ 1 | study_id / es_id, data = data, method = "REML")
}

robust_rows <- function(fit, data, model, note = "") {
  ct <- coef_test(fit, vcov = "CR2", cluster = data$study_id)
  ci <- conf_int(fit, vcov = "CR2", cluster = data$study_id)
  data.frame(model = model, term = ct$Coef, estimate = ct$beta, se = ct$SE, ci_low = ci$CI_L, ci_high = ci$CI_U,
             p_cr2 = ct$p_Satt, k_effects = nrow(data), k_studies = length(unique(data$study_id)), note = note,
             row.names = NULL)
}

fit_rq3 <- function(es, fields, min_clinical = 8) {
  d <- merge(es, fields[fields$head_model == "ernie", ], by = "montage_id")
  d$group <- factor(ifelse(d$population == "healthy", "healthy", "clinical"), levels = c("healthy", "clinical"))
  out <- list(robust_rows(fit_mv(~ field_map + sessions, d), d, "H3a"))
  h3b <- fit_mv(~ field_map + field_control + sessions, d)
  wald <- Wald_test(h3b, constraints = constrain_equal(c("field_map", "field_control")), vcov = "CR2",
                    cluster = d$study_id)
  out[[2]] <- robust_rows(h3b, d, "H3b")
  out[[3]] <- data.frame(model = "H3b", term = "field_map = field_control", estimate = NA, se = NA, ci_low = NA,
                         ci_high = NA, p_cr2 = wald$p_val, k_effects = nrow(d), k_studies = length(unique(d$study_id)),
                         note = sprintf("CR2 Wald F = %.2f", wald$Fstat))
  out[[4]] <- robust_rows(fit_mv(~ test_type + sessions, d), d, "H3c")
  n_clin <- length(unique(d$study_id[d$group == "clinical"]))
  out[[5]] <- if (n_clin < min_clinical) {
    data.frame(model = "H3d", term = NA, estimate = NA, se = NA, ci_low = NA, ci_high = NA, p_cr2 = NA,
               k_effects = nrow(d), k_studies = length(unique(d$study_id)),
               note = sprintf("skipped: %d clinical studies < %d; clinical arm reported descriptively", n_clin, min_clinical))
  } else robust_rows(fit_mv(~ field_map * group + sessions, d), d, "H3d")
  do.call(rbind, out)
}

bias <- function(es, funnel_png = NULL) {
  row <- function(test, fit, i, extra = "") {
    data.frame(test = test, term = names(coef(fit))[i], estimate = coef(fit)[i], ci_low = fit$ci.lb[i],
               ci_high = fit$ci.ub[i], p = fit$pval[i], note = extra, row.names = NULL)
  }
  es$sei <- sqrt(es$vi)
  pet <- fit_mv(~ sei, es)
  peese <- fit_mv(~ vi, es)
  out <- list(row("egger", pet, 2), row("pet", pet, 1), row("peese", peese, 1))
  for (s in unique(es$study_id)) {
    fit <- fit_mv(~ 1, es[es$study_id != s, ])
    out[[length(out) + 1]] <- row("leave_one_out", fit, 1, paste("without", s))
  }
  if (!is.null(funnel_png)) {
    png(funnel_png, width = 1600, height = 1400, res = 200); funnel(fit_mv(~ 1, es)); dev.off()
  }
  do.call(rbind, out)
}

rob_plots <- function(rob2, out_dir) {
  lab <- c(low = "Low", some = "Some concerns", high = "High")
  d <- data.frame(Study = rob2$study_id, D1 = lab[rob2$d1_randomisation], D2 = lab[rob2$d2_deviations],
                  D3 = lab[rob2$d3_missing], D4 = lab[rob2$d4_measurement], D5 = lab[rob2$d5_selection],
                  Overall = lab[rob2$overall], Weight = 1)
  ggplot2::ggsave(file.path(out_dir, "rob2_traffic_light.png"), robvis::rob_traffic_light(d, tool = "ROB2"),
                  width = 8, height = 2 + 0.3 * nrow(d))
  ggplot2::ggsave(file.path(out_dir, "rob2_summary.png"), robvis::rob_summary(d, tool = "ROB2"), width = 8, height = 3)
}

main <- function() {
  out <- "rq3_stimulation/results"
  fields <- read.csv("rq3_stimulation/simnibs/fields.csv")
  for (r in c(0.3, 0.5, 0.7)) {
    es <- read.csv(sprintf("%s/effect_sizes_r%.1f.csv", out, r))
    write.csv(fit_rq3(es, fields), sprintf("%s/h3_results_r%.1f.csv", out, r), row.names = FALSE)
    write.csv(bias(es, if (r == 0.5) file.path(out, "funnel.png")), sprintf("%s/bias_r%.1f.csv", out, r), row.names = FALSE)
  }
  rob_plots(read.csv("rq3_stimulation/rob2.csv"), out)
  cat("RQ3 models written to", out, "\n")
}

if (sys.nframe() == 0 && "--run" %in% commandArgs(trailingOnly = TRUE)) main()
