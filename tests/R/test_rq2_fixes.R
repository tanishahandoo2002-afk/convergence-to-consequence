# Regression tests for the plan-02 final review findings.
source("rq2_nsd/models.R")
src <- readLines("tests/R/test_rq2_models.R")
eval(parse(text = src[grep("^sim_trials <-", src):grep("^row_of <-", src) - 1]))

d <- sim_trials(slope = 0.4, seed = 7, n_trials = 600, n_img = 1000)

# a NaN signal trial must not abort the permutation test
d_nan <- d; d_nan$sig_memory[c(3, 50)] <- NaN
p <- perm_test(d_nan, n_perm = 20, seed = 1)
stopifnot(nrow(p) == 8)

# H2b network comparison must not depend on each signal's scale
r1 <- fit_h2(d, per_subject = FALSE); d10 <- d; d10$sig_control_md <- 10 * d10$sig_control_md
r2 <- fit_h2(d10, per_subject = FALSE)
pick <- function(r) r$estimate[r$model == "H2b" & r$term == "sig:networkcontrol_md"]
stopifnot(abs(pick(r1) - pick(r2)) < 1e-6)

# spec §9 checks: trial counts per participant and outcome; diagnostic plot written
tc <- trial_counts(d)
stopifnot(all(c("subject", "outcome", "n") %in% names(tc)), sum(tc$n) == nrow(d))
png_path <- tempfile(fileext = ".png")
binned_residuals(fit_simplified(h2_formulas("hit", "sig_memory", "sig_memory"), prepare(d)[prepare(d)$is_old == 1, ])$fit, png_path)
stopifnot(file.exists(png_path))
cat("rq2 review fixes: all tests passed\n")
