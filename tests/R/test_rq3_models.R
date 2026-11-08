# Known-answer tests for rq3_stimulation/models.R on simulated stimulation trials.
source("rq3_stimulation/models.R")

sim_es <- function(n_studies = 30, n_clinical = 10, slope = 1.0, seed = 1, n_range = c(40, 400)) {
  set.seed(seed)
  k <- sample(1:3, n_studies, replace = TRUE)
  study <- rep(sprintf("s%02d", seq_len(n_studies)), k)
  montage <- sprintf("m%02d", seq_len(n_studies))
  fields <- data.frame(montage_id = montage, head_model = "ernie",
                       field_map = runif(n_studies, 0.05, 0.4), field_control = runif(n_studies, 0.05, 0.4))
  pop <- ifelse(seq_len(n_studies) <= n_clinical, "MCI", "healthy")
  u <- rnorm(n_studies, sd = 0.1)
  sid <- match(study, sprintf("s%02d", seq_len(n_studies)))
  n <- round(runif(length(study), n_range[1], n_range[2]))
  es <- data.frame(es_id = seq_along(study), study_id = study, montage_id = montage[sid], population = pop[sid],
                   sessions = sample(1:10, n_studies, replace = TRUE)[sid],
                   test_type = sample(c("recall", "recognition"), length(study), replace = TRUE), vi = 4 / n)
  true <- 0.1 + slope * fields$field_map[sid] + u[sid] + rnorm(length(study), sd = 0.05)
  es$yi <- rnorm(length(study), true, sqrt(es$vi))
  list(es = es, fields = fields)
}

term <- function(res, model, t) { r <- res[res$model == model & res$term == t, ]; stopifnot(nrow(r) == 1); r }

# planted slope with enough studies and precision that the answer is unambiguous
s <- sim_es(n_studies = 60, n_clinical = 20, n_range = c(200, 800))
res <- fit_rq3(s$es, s$fields, min_clinical = 8)
r <- term(res, "H3a", "field_map")
stopifnot(r$ci_low < 1.0, r$ci_high > 1.0, r$ci_low > 0, r$k_studies == 60, r$k_effects == nrow(s$es))
h3b_diff <- term(res, "H3b", "field_map = field_control")
coefs <- res[res$model == "H3b", ]
stopifnot(h3b_diff$p_cr2 < 0.05, h3b_diff$ci_low < 1.0, h3b_diff$ci_high > 1.0, h3b_diff$ci_low > 0,
          abs(h3b_diff$estimate - (coefs$estimate[coefs$term == "field_map"] -
                                   coefs$estimate[coefs$term == "field_control"])) < 1e-8)
stopifnot(nrow(res[res$model == "H3c", ]) >= 2, nrow(res[res$model == "H3d", ]) >= 4)

# montages without a field and effects without a session count are left out; H3c keeps the field-less ones
gap <- s
gap$fields$field_map[1:2] <- NA
gap$es$sessions[gap$es$study_id == "s03"] <- NA
res <- fit_rq3(gap$es, gap$fields, min_clinical = 8)
no_sessions <- sum(gap$es$study_id == "s03")
stopifnot(term(res, "H3a", "field_map")$k_studies == 57,
          term(res, "H3c", "sessions")$k_studies == 59,
          term(res, "H3c", "sessions")$k_effects == nrow(gap$es) - no_sessions)

few <- sim_es(n_clinical = 5, seed = 2)
r <- fit_rq3(few$es, few$fields, min_clinical = 8)
stopifnot(any(r$model == "H3d" & grepl("skipped: 5 clinical studies < 8", r$note)))

b <- bias(s$es)
eg <- b[b$test == "egger", ]
stopifnot(nrow(eg) == 1, eg$ci_low < 0, eg$ci_high > 0)
stopifnot(sum(b$test == "leave_one_out") == 60, all(c("pet", "peese") %in% b$test))
ov <- b[b$test == "overall", ]
stopifnot(nrow(ov) == 1, ov$k_studies == 60, ov$k_effects == nrow(s$es), all(b$k_studies[b$test == "leave_one_out"] == 59))

out <- tempfile(); dir.create(out)
rob_plots(data.frame(study_id = c("s1", "s2"), d1_randomisation = c("low", "some"), d1b_carryover = "",
                     d2_deviations = "low", d3_missing = c("high", "low"), d4_measurement = "low",
                     d5_selection = "low", overall = c("high", "some")), out)
stopifnot(file.exists(file.path(out, "rob2_traffic_light.png")), file.exists(file.path(out, "rob2_summary.png")))
cat("rq3 models: all known-answer tests passed\n")
