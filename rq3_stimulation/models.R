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

with_fields <- function(es, fields, clinical_head = "ernie") {
  d <- merge(es, fields[fields$head_model == "ernie", ], by = "montage_id")
  d$group <- factor(ifelse(d$population == "healthy", "healthy", "clinical"), levels = c("healthy", "clinical"))
  if (clinical_head != "ernie") {
    alt <- fields[fields$head_model == clinical_head, ]
    i <- d$group == "clinical"
    m <- match(d$montage_id[i], alt$montage_id)
    d$field_map[i] <- alt$field_map[m]
    d$field_control[i] <- alt$field_control[m]
  }
  # Drop rows the models cannot use up front, so k_effects and the CR2 clusters match the fitted data.
  d[!is.na(d$field_map) & !is.na(d$field_control), ]
}

fit_h3d <- function(d, min_clinical, model, note = "") {
  n_clin <- length(unique(d$study_id[d$group == "clinical"]))
  if (n_clin < min_clinical) {
    return(data.frame(model = model, term = NA, estimate = NA, se = NA, ci_low = NA, ci_high = NA, p_cr2 = NA,
                      k_effects = nrow(d), k_studies = length(unique(d$study_id)),
                      note = sprintf("skipped: %d clinical studies < %d; clinical arm reported descriptively", n_clin, min_clinical)))
  }
  robust_rows(fit_mv(~ field_map * group + sessions, d), d, model, note)
}

fit_rq3 <- function(es, fields, min_clinical = 8) {
  es <- es[!is.na(es$sessions), ]
  d <- with_fields(es, fields)
  out <- list(robust_rows(fit_mv(~ field_map + sessions, d), d, "H3a"))
  h3b <- fit_mv(~ field_map + field_control + sessions, d)
  wald <- Wald_test(h3b, constraints = constrain_equal(c("field_map", "field_control")), vcov = "CR2",
                    cluster = d$study_id)
  out[[2]] <- robust_rows(h3b, d, "H3b")
  # The difference itself, with a CR2 CI, so integration.R can set it beside RQ2's H2b; p stays the Wald test.
  b <- names(coef(h3b))
  diff <- linear_contrast(h3b, vcov = "CR2", cluster = d$study_id,
                          contrasts = matrix((b == "field_map") - (b == "field_control"), nrow = 1))
  out[[3]] <- data.frame(model = "H3b", term = "field_map = field_control", estimate = diff$Est, se = diff$SE,
                         ci_low = diff$CI_L, ci_high = diff$CI_U, p_cr2 = wald$p_val, k_effects = nrow(d), k_studies = length(unique(d$study_id)),
                         note = sprintf("CR2 Wald F = %.2f", wald$Fstat))
  # H3c has no field term, so it keeps the effects whose montage could not be modelled.
  out[[4]] <- robust_rows(fit_mv(~ test_type + sessions, es), es, "H3c")
  out[[5]] <- fit_h3d(d, min_clinical, "H3d")
  # Sensitivity: clinical effects take their field from the older-adult head (CHANGELOG 2026-11-10).
  if ("older" %in% fields$head_model) {
    out[[6]] <- fit_h3d(with_fields(es, fields, "older"), min_clinical, "H3d_older",
                        "clinical fields from the older-adult head")
  }
  do.call(rbind, out)
}

bias <- function(es, funnel_png = NULL) {
  row <- function(test, fit, i, extra = "") {
    data.frame(test = test, term = names(coef(fit))[i], estimate = coef(fit)[i], ci_low = fit$ci.lb[i],
               ci_high = fit$ci.ub[i], p = fit$pval[i], k_effects = fit$k, k_studies = fit$s.nlevels[1],
               note = extra, row.names = NULL)
  }
  es$sei <- sqrt(es$vi)
  overall <- fit_mv(~ 1, es)
  pet <- fit_mv(~ sei, es)
  peese <- fit_mv(~ vi, es)
  out <- list(row("overall", overall, 1), row("egger", pet, 2), row("pet", pet, 1), row("peese", peese, 1))
  for (s in unique(es$study_id)) {
    fit <- fit_mv(~ 1, es[es$study_id != s, ])
    out[[length(out) + 1]] <- row("leave_one_out", fit, 1, paste("without", s))
  }
  if (!is.null(funnel_png)) {
    png(funnel_png, width = 1600, height = 1400, res = 200); funnel(overall); dev.off()
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
