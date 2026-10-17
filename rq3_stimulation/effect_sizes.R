# RQ3 effect sizes (plan §8.3 step 7): Hedges' g for active vs sham, positive = better memory.
# Parallel designs: SMD from means/SDs, or from t when only t is reported.
# Crossover designs: change-score SMD (SMCC) with an assumed correlation r (.5 primary; .3/.7 sensitivity).
# `Rscript rq3_stimulation/effect_sizes.R --run` writes results/effect_sizes_r<r>.csv and reported-g flags.
suppressPackageStartupMessages(library(metafor))

compute_es <- function(effects, r) {
  e <- effects
  e$yi <- NA_real_; e$vi <- NA_real_
  has_means <- with(e, !is.na(m_active) & !is.na(sd_active) & !is.na(m_sham) & !is.na(sd_sham))
  par_m <- e$design == "parallel" & has_means
  par_t <- e$design == "parallel" & !has_means & !is.na(e$t_value)
  cross <- e$design == "crossover" & has_means
  if (any(par_m)) e[par_m, c("yi", "vi")] <- as.data.frame(with(e[par_m, ], escalc("SMD", m1i = m_active,
    sd1i = sd_active, n1i = n_active, m2i = m_sham, sd2i = sd_sham, n2i = n_sham)))[, c("yi", "vi")]
  if (any(par_t)) e[par_t, c("yi", "vi")] <- as.data.frame(with(e[par_t, ], escalc("SMD", ti = t_value,
    n1i = n_active, n2i = n_sham)))[, c("yi", "vi")]
  if (any(cross)) e[cross, c("yi", "vi")] <- as.data.frame(with(e[cross, ], escalc("SMCC", m1i = m_active,
    m2i = m_sham, sd1i = sd_active, sd2i = sd_sham, ni = n_active, ri = rep(r, sum(cross)))))[, c("yi", "vi")]
  flip <- e$higher_is_better == 0
  e$yi[flip] <- -e$yi[flip]
  e
}

# es_ids whose recomputed g differs from the paper's reported g by more than tol (checked by hand).
flag_reported <- function(es, tol = 0.05) {
  bad <- !is.na(es$reported_g) & abs(es$yi - es$reported_g) > tol
  as.character(es$es_id[bad])
}

main <- function() {
  effects <- read.csv("rq3_stimulation/effects.csv")
  dir.create("rq3_stimulation/results", showWarnings = FALSE)
  for (r in c(0.3, 0.5, 0.7)) {
    es <- compute_es(effects, r)
    write.csv(es, sprintf("rq3_stimulation/results/effect_sizes_r%.1f.csv", r), row.names = FALSE)
  }
  es <- compute_es(effects, 0.5)
  flags <- flag_reported(es)
  writeLines(flags, "rq3_stimulation/results/reported_g_flags.txt")
  if (length(flags)) cat("check against the papers (recomputed g differs from reported):", flags, "\n")
}

if (sys.nframe() == 0 && "--run" %in% commandArgs(trailingOnly = TRUE)) main()
