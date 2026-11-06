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

# crossover: d_av = 1 / sqrt((4 + 4) / 2) = 0.5, J uses df = 2(n - 1) / (1 + r^2). At r = .7 change-score
# standardisation would give about 0.62, so this value tells the two methods apart.
cross <- row(design = "crossover")
j <- function(r) 1 - 3 / (4 * 2 * 19 / (1 + r^2) - 1)
stopifnot(abs(compute_es(cross, r = 0.5)$yi - 0.5 * j(0.5)) < 1e-3)
stopifnot(abs(compute_es(cross, r = 0.7)$yi - 0.5 * j(0.7)) < 1e-3)
# unequal SDs pool their variances: 1 / sqrt((4 + 16) / 2)
stopifnot(abs(compute_es(row(design = "crossover", sd_sham = 4), r = 0.5)$yi - j(0.5) / sqrt(10)) < 1e-3)
# a higher assumed correlation shrinks the sampling variance
stopifnot(compute_es(cross, r = 0.7)$vi < compute_es(cross, r = 0.3)$vi)

mixed <- rbind(row(es_id = "a", reported_g = 0.49), row(es_id = "b", reported_g = 0.9))
stopifnot(identical(flag_reported(compute_es(mixed, r = 0.5)), "b"))
cat("rq3 effect sizes: all known-answer tests passed\n")
