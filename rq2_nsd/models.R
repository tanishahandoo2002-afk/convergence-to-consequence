# RQ2 models (plan §8.2 steps 6-8): mixed-effects logistic regressions of memory on single-trial signal.
# Functions are sourced by tests/R/test_rq2_models.R; `Rscript rq2_nsd/models.R --run --input DIR --output DIR`
# fits everything on the extracted session tables.
suppressPackageStartupMessages(library(lme4))
`%||%` <- function(a, b) if (is.null(a)) b else a

# Pre-registered simplification order (pooled models); per-participant models drop the subject terms.
h2_formulas <- function(outcome, terms, slope) {
  lapply(c(sprintf("%s ~ %s + (1 + %s | subject) + (1 | image)", outcome, terms, slope),
           sprintf("%s ~ %s + (1 + %s || subject) + (1 | image)", outcome, terms, slope),
           sprintf("%s ~ %s + (1 | subject) + (1 | image)", outcome, terms),
           sprintf("%s ~ %s + (1 | subject)", outcome, terms)), as.formula)
}

subject_formulas <- function(outcome, terms) {
  lapply(c(sprintf("%s ~ %s + (1 | image)", outcome, terms), sprintf("%s ~ %s", outcome, terms)), as.formula)
}

# Try each formula in order; the first that fits without a convergence warning or singular fit is used.
# Singular fits move on to the next (simpler) formula; if every warning-free fit is singular, the last one is
# kept as a boundary estimate and flagged `singular`, rather than dropping the model.
fit_simplified <- function(formulas, data, family = binomial) {
  boundary <- NULL
  for (f in formulas) {
    warned <- FALSE
    fit <- tryCatch(suppressMessages(withCallingHandlers(
      if (is.null(findbars(f))) glm(f, data = data, family = family)
      else glmer(f, data = data, family = family, control = glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 2e5))),
      warning = function(w) { warned <<- TRUE; invokeRestart("muffleWarning") })),
      error = function(e) NULL)
    if (is.null(fit) || warned) next
    used <- paste(deparse(f), collapse = "")
    if (inherits(fit, "merMod") && isSingular(fit)) {
      boundary <- list(fit = fit, formula_used = used, converged = TRUE, singular = TRUE)
      next
    }
    return(list(fit = fit, formula_used = used, converged = TRUE, singular = FALSE))
  }
  boundary %||% list(fit = NULL, formula_used = NA_character_, converged = FALSE, singular = NA)
}

# Wald test of beta_a - beta_b, in the columns of a coefficient table.
wald_diff <- function(fit, a, b) {
  co <- coef(summary(fit)); v <- as.matrix(vcov(fit))
  est <- co[a, 1] - co[b, 1]
  se <- sqrt(v[a, a] + v[b, b] - 2 * v[a, b])
  c(est, se, est / se, 2 * pnorm(-abs(est / se)))
}

tidy_fit <- function(res, model, subject, diff = NULL) {
  if (is.null(res$fit)) {
    return(data.frame(model = model, subject = subject, term = NA, estimate = NA, se = NA, or = NA, ci_low = NA,
                      ci_high = NA, p = NA, formula_used = NA, converged = FALSE, singular = NA))
  }
  co <- coef(summary(res$fit))
  if (!is.null(diff)) {
    co <- rbind(co, wald_diff(res$fit, diff[1], diff[2]))
    rownames(co)[nrow(co)] <- paste(diff, collapse = " - ")
  }
  data.frame(model = model, subject = subject, term = rownames(co), estimate = co[, 1], se = co[, 2],
             or = exp(co[, 1]), ci_low = co[, 1] - 1.96 * co[, 2], ci_high = co[, 1] + 1.96 * co[, 2],
             p = co[, 4], formula_used = res$formula_used, converged = TRUE, singular = res$singular, row.names = NULL)
}

prepare <- function(trials) {
  d <- trials[!is.na(trials$outcome), ]
  d$subject <- factor(d$subject); d$image <- factor(d$image)
  d$hit <- as.integer(d$outcome == "hit")
  d
}

zscore <- function(x) (x - mean(x, na.rm = TRUE)) / sd(x, na.rm = TRUE)

# H2b: trials answered "old" (hits and false alarms), one row per trial. Stacking each trial once per network
# would make the standard error too small. Each signal is z-scored within participant so the difference between
# the two slopes doesn't depend on predictor scales (docs/decisions-proposed.md §4.3).
h2b_data <- function(d, control = "sig_control_md") {
  old_resp <- d[d$outcome %in% c("hit", "fa"), ]
  old_resp$z_memory <- ave(old_resp$sig_memory, old_resp$subject, FUN = zscore)
  old_resp$z_control <- ave(old_resp[[control]], old_resp$subject, FUN = zscore)
  old_resp$correct <- as.integer(old_resp$outcome == "hit")
  old_resp
}

# H2c centres delay at this value, so the memory-signal main effect is the effect at a typical delay, not at 1 s
# (docs/decisions-proposed.md §4.4). Pooled across participants; per-participant fits use the same value.
delay_centre <- function(d) median(d$log_delay_s[d$is_old == 1], na.rm = TRUE)

specs <- function(d, memory = "sig_memory", control = "sig_control_md") {
  old <- d[d$is_old == 1, ]
  old$log_delay_c <- old$log_delay_s - delay_centre(d)
  list(H2a = list(data = old, outcome = "hit", terms = memory, slope = memory),
       H2b = list(data = h2b_data(d, control), outcome = "correct", terms = "z_memory + z_control",
                  slope = "z_memory + z_control", diff = c("z_memory", "z_control")),
       H2c = list(data = old[!is.na(old$log_delay_c), ], outcome = "hit",
                  terms = paste0(memory, " * log_delay_c"), slope = memory))
}

fit_h2 <- function(trials, memory = "sig_memory", control = "sig_control_md", per_subject = TRUE) {
  d <- prepare(trials)
  out <- list()
  for (m in names(sp <- specs(d, memory, control))) {
    s <- sp[[m]]
    out[[length(out) + 1]] <- tidy_fit(fit_simplified(h2_formulas(s$outcome, s$terms, s$slope), s$data), m, "all", s$diff)
    if (per_subject) for (subj in levels(droplevels(s$data$subject))) {
      sd <- droplevels(s$data[s$data$subject == subj, ])
      out[[length(out) + 1]] <- tidy_fit(fit_simplified(subject_formulas(s$outcome, s$terms), sd), m, subj, s$diff)
    }
  }
  do.call(rbind, out)
}

robustness <- function(trials) {
  d <- prepare(trials)
  pick <- function(res, models, variant) transform(res[res$model %in% models, ], variant = variant)
  out <- lapply(levels(d$subject), function(s)
    pick(fit_h2(droplevels(d[d$subject != s, ]), per_subject = FALSE), "H2a", paste0("lopo_", s)))
  out[[length(out) + 1]] <- pick(fit_h2(d, memory = "sig_memory_top50", per_subject = FALSE), "H2a", "top50")
  out[[length(out) + 1]] <- pick(fit_h2(d, control = "sig_control_yeo", per_subject = FALSE), "H2b", "yeo")
  # the map without unverified experiments, with its own control so the two masks stay disjoint
  out[[length(out) + 1]] <- pick(fit_h2(d, memory = "sig_memory_verified", control = "sig_control_md_verified",
                                        per_subject = FALSE), c("H2a", "H2b", "H2c"), "verified_only")
  do.call(rbind, out)
}

# Per participant: fixed-effects logistic slope of hit on memory signal, labels shuffled within session.
perm_test <- function(trials, n_perm = 1000, seed = 20261019) {
  set.seed(seed)
  d <- prepare(trials)
  d <- d[d$is_old == 1 & is.finite(d$sig_memory), ]
  slope <- function(y, x) coef(glm.fit(cbind(1, x), y, family = binomial()))[2]
  do.call(rbind, lapply(levels(droplevels(d$subject)), function(s) {
    ds <- d[d$subject == s, ]
    obs <- slope(ds$hit, ds$sig_memory)
    null <- replicate(n_perm, slope(ave(ds$hit, ds$session, FUN = sample), ds$sig_memory))
    data.frame(subject = s, slope = obs, p = (1 + sum(abs(null) >= abs(obs))) / (n_perm + 1), n_perm = n_perm)
  }))
}

# Spec §9 check: trials per participant and outcome (missing responses counted as "missing").
trial_counts <- function(trials) {
  o <- ifelse(is.na(trials$outcome), "missing", trials$outcome)
  setNames(as.data.frame(table(trials$subject, o), stringsAsFactors = FALSE), c("subject", "outcome", "n"))
}

# Binned residual plot for a logistic (mixed) model: mean residual per bin of fitted probability, +/- 2 SE.
binned_residuals <- function(fit, png_path, n_bins = NULL) {
  p <- fitted(fit); y <- if (inherits(fit, "merMod")) getME(fit, "y") else fit$y
  n_bins <- n_bins %||% max(10, floor(sqrt(length(p))))
  bin <- cut(rank(p, ties.method = "first"), n_bins, labels = FALSE)
  mp <- tapply(p, bin, mean); mr <- tapply(y - p, bin, mean); se <- tapply(p, bin, function(q) sqrt(mean(q * (1 - q)) / length(q)))
  png(png_path, width = 1400, height = 1100, res = 200)
  plot(mp, mr, pch = 19, cex = 0.6, xlab = "Mean fitted probability", ylab = "Mean residual", main = "Binned residuals")
  lines(mp, 2 * se, col = "grey50"); lines(mp, -2 * se, col = "grey50"); abline(h = 0, lty = 2)
  dev.off()
}

diagnostics <- function(trials, out_dir) {
  d <- prepare(trials)
  for (m in names(sp <- specs(d))) {
    s <- sp[[m]]
    f <- fit_simplified(h2_formulas(s$outcome, s$terms, s$slope), s$data)
    if (!is.null(f$fit)) binned_residuals(f$fit, file.path(out_dir, sprintf("diagnostics_%s.png", m)))
  }
}

main <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  input <- args[which(args == "--input") + 1]; output <- args[which(args == "--output") + 1]
  files <- list.files(input, pattern = "^subj.*_sess.*\\.csv$", full.names = TRUE)
  trials <- do.call(rbind, lapply(files, read.csv))
  dir.create(output, showWarnings = FALSE, recursive = TRUE)
  writeLines(format(delay_centre(prepare(trials)), digits = 15), file.path(output, "h2c_delay_centre.txt"))
  write.csv(fit_h2(trials), file.path(output, "h2_results.csv"), row.names = FALSE)
  write.csv(robustness(trials), file.path(output, "h2_robustness.csv"), row.names = FALSE)
  write.csv(perm_test(trials), file.path(output, "permutation.csv"), row.names = FALSE)
  write.csv(trial_counts(trials), file.path(output, "trial_counts.csv"), row.names = FALSE)
  diagnostics(trials, output)
  cat("RQ2 models written to", output, "\n")
}

if (sys.nframe() == 0 && "--run" %in% commandArgs(trailingOnly = TRUE)) main()
