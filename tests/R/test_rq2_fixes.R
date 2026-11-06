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
pick <- function(r) r$estimate[r$model == "H2b" & r$term == "z_memory - z_control"]
stopifnot(abs(pick(r1) - pick(r2)) < 1e-6)

# H2b keeps one row per trial, and the Wald contrast equals the same contrast fitted directly:
# b0 + bm*zm + bc*zc = b0 + (bm - bc)*zm + bc*(zm + zc)
wide <- h2b_data(prepare(d))
stopifnot(nrow(wide) == sum(prepare(d)$outcome %in% c("hit", "fa")), !anyDuplicated(rownames(wide)))
w <- tidy_fit(fit_simplified(list(correct ~ z_memory + z_control), wide), "H2b", "x", c("z_memory", "z_control"))
w <- w[w$term == "z_memory - z_control", ]
direct <- coef(summary(glm(correct ~ z_memory + I(z_memory + z_control), data = wide, family = binomial)))["z_memory", ]
stopifnot(abs(w$estimate - direct[1]) < 1e-5, abs(w$se - direct[2]) < 1e-5, abs(w$p - direct[4]) < 1e-5)

# spec §9 checks: trial counts per participant and outcome; diagnostic plot written
tc <- trial_counts(d)
stopifnot(all(c("subject", "outcome", "n") %in% names(tc)), sum(tc$n) == nrow(d))
png_path <- tempfile(fileext = ".png")
binned_residuals(fit_simplified(h2_formulas("hit", "sig_memory", "sig_memory"), prepare(d)[prepare(d)$is_old == 1, ])$fit, png_path)
stopifnot(file.exists(png_path))
cat("rq2 review fixes: all tests passed\n")
