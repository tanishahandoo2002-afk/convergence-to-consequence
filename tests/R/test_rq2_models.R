# Known-answer tests for rq2_nsd/models.R on simulated NSD-like trials.
source("rq2_nsd/models.R")

sim_trials <- function(slope = 0.4, inter = 0, seed = 1, n_subj = 8, n_trials = 1500, n_img = 2000) {
  set.seed(seed)
  d <- data.frame(subject = rep(seq_len(n_subj), each = n_trials),
                  session = rep(rep(1:2, each = n_trials / 2), n_subj),
                  image = sample(n_img, n_subj * n_trials, replace = TRUE),
                  sig_memory = rnorm(n_subj * n_trials), sig_control_md = rnorm(n_subj * n_trials),
                  sig_control_yeo = rnorm(n_subj * n_trials))
  d$sig_memory_top50 <- d$sig_memory + rnorm(nrow(d), sd = 0.3)
  d$is_old <- rbinom(nrow(d), 1, 0.6)
  d$log_delay_s <- ifelse(d$is_old == 1, runif(nrow(d), 1, 7), NA)
  u_s <- rnorm(n_subj, sd = 0.3); b_s <- slope + rnorm(n_subj, sd = 0.1); v_i <- rnorm(n_img, sd = 0.3)
  eta <- 0.5 + u_s[d$subject] + v_i[d$image] + b_s[d$subject] * d$sig_memory +
    inter * d$sig_memory * ifelse(is.na(d$log_delay_s), 0, d$log_delay_s - 4)
  hit <- rbinom(nrow(d), 1, plogis(eta))
  fa <- rbinom(nrow(d), 1, plogis(-1.5 + u_s[d$subject]))
  d$outcome <- ifelse(d$is_old == 1, ifelse(hit == 1, "hit", "miss"), ifelse(fa == 1, "fa", "cr"))
  d
}

row_of <- function(res, model, term, subject = "all") {
  r <- res[res$model == model & res$term == term & res$subject == subject, ]
  stopifnot(nrow(r) == 1)
  r
}

# planted H2a slope 0.4: pooled CI contains 0.4 and excludes 0
planted <- sim_trials(slope = 0.4)
res <- fit_h2(planted)
r <- row_of(res, "H2a", "sig_memory")
stopifnot(r$ci_low < 0.4, r$ci_high > 0.4, r$ci_low > 0, isTRUE(r$converged))
stopifnot(all(c(as.character(1:8), "all") %in% res$subject[res$model == "H2a"]))
stopifnot(abs(r$or - exp(r$estimate)) < 1e-12)

# H2b: memory signal separates hits from false alarms more than the control signal
r <- row_of(res, "H2b", "sig:networkcontrol_md")
stopifnot(r$estimate < 0)

# null slope: CI contains 0
r <- row_of(fit_h2(sim_trials(slope = 0, seed = 2), per_subject = FALSE), "H2a", "sig_memory")
stopifnot(r$ci_low < 0, r$ci_high > 0)

# planted H2c interaction -0.2
r <- row_of(fit_h2(sim_trials(slope = 0.4, inter = -0.2, seed = 3), per_subject = FALSE), "H2c", "sig_memory:log_delay_s")
stopifnot(r$ci_low < -0.2, r$ci_high > -0.2)

# a model that fails at every step is recorded, not fatal
bad <- data.frame(y = rbinom(50, 1, 0.5), x = rnorm(50), g = factor("only"))
f <- fit_simplified(list(y ~ x + (1 | g)), bad)
stopifnot(is.null(f$fit), identical(f$converged, FALSE))

# robustness: 8 leave-one-participant-out rows plus top-50% and Yeo variants
rob <- robustness(sim_trials(slope = 0.4, seed = 5, n_trials = 500, n_img = 800))
stopifnot(sum(grepl("^lopo_", unique(rob$variant))) == 8, all(c("top50", "yeo") %in% rob$variant))

# permutation: planted -> p < .05 for every participant; null -> mostly not significant
p1 <- perm_test(planted, n_perm = 200, seed = 1)
stopifnot(nrow(p1) == 8, all(p1$p < 0.05))
p0 <- perm_test(sim_trials(slope = 0, seed = 4), n_perm = 200, seed = 1)
stopifnot(sum(p0$p > 0.01) >= 6)
cat("rq2 models: all known-answer tests passed\n")
