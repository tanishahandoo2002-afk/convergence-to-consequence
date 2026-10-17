# Known-answer tests for rq3_stimulation/effect_sizes.R
source("rq3_stimulation/effect_sizes.R")

row <- function(...) {
  base <- list(es_id = "e1", design = "parallel", n_active = 20, n_sham = 20, m_active = 10, sd_active = 2,
               m_sham = 9, sd_sham = 2, t_value = NA, higher_is_better = 1, reported_g = NA)
  as.data.frame(modifyList(base, list(...)))
}

g <- compute_es(row(), r = 0.5)$yi
stopifnot(abs(g - 0.4901) < 1e-4)                                   # hand-computed Hedges' g

stopifnot(abs(compute_es(row(higher_is_better = 0), r = 0.5)$yi + 0.4901) < 1e-4)   # sign flip

t_only <- row(m_active = NA, sd_active = NA, m_sham = NA, sd_sham = NA, t_value = 1.5811)
stopifnot(abs(compute_es(t_only, r = 0.5)$yi - 0.4901) < 1e-3)     # from t, parallel design

# crossover, r = .5: SD of change = sqrt(4 + 4 - 2*.5*2*2) = 2, d = 0.5, small-sample J(df = 19) ~ 0.960
cross <- row(design = "crossover")
stopifnot(abs(compute_es(cross, r = 0.5)$yi - 0.5 * 0.9603) < 2e-3)
# a higher assumed correlation shrinks the change-score SD, so g grows with r
stopifnot(compute_es(cross, r = 0.7)$yi > compute_es(cross, r = 0.3)$yi)

mixed <- rbind(row(es_id = "a", reported_g = 0.49), row(es_id = "b", reported_g = 0.9))
stopifnot(identical(flag_reported(compute_es(mixed, r = 0.5)), "b"))
cat("rq3 effect sizes: all known-answer tests passed\n")
