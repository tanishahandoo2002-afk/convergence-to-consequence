# Integration (design §11): the memory-map vs control comparison from RQ2 (H2b) and RQ3 (H3b), side by side.
# The two differences are on different scales, so the table names each scale and the figure gives each its own
# panel instead of a shared axis. Interpretation is the author's.
# `Rscript integration.R --run` reads rq2_nsd/results and rq3_stimulation/results (r = .5), writes to results/.

integration_table <- function(h2, counts, h3) {
  a <- h2[h2$model == "H2b" & h2$subject == "all" & h2$term %in% "z_memory - z_control", ]
  b <- h3[h3$model == "H3b" & h3$term %in% "field_map = field_control", ]
  stopifnot(nrow(a) == 1, nrow(b) == 1)
  old <- counts[counts$outcome %in% c("hit", "fa") & counts$n > 0, ]
  data.frame(rq = c("RQ2", "RQ3"), hypothesis = c("H2b", "H3b"),
             contrast = c("memory-map signal minus control signal", "memory-map field minus control field"),
             scale = c("log-odds, hit vs false alarm, per SD of signal", "Hedges' g per V/m"),
             estimate = c(a$estimate, b$estimate), ci_low = c(a$ci_low, b$ci_low), ci_high = c(a$ci_high, b$ci_high),
             p = c(a$p, b$p_cr2),
             n = c(sprintf("%d trials answered old, %d participants", sum(old$n), length(unique(old$subject))),
                   sprintf("%d effects, %d studies", b$k_effects, b$k_studies)))
}

integration_plot <- function(tab, png_path) {
  png(png_path, width = 2400, height = 800, res = 200)
  par(mfrow = c(1, nrow(tab)), mar = c(5, 1, 4, 1))
  for (i in seq_len(nrow(tab))) {
    r <- tab[i, ]
    plot(r$estimate, 1, xlim = range(0, r$ci_low, r$ci_high), ylim = c(0.5, 1.5), pch = 19, yaxt = "n",
         ylab = "", xlab = r$scale, main = sprintf("%s %s: %s\n%s", r$rq, r$hypothesis, r$contrast, r$n),
         cex.main = 0.85)
    segments(r$ci_low, 1, r$ci_high, 1, lwd = 2)
    abline(v = 0, lty = 2)
  }
  dev.off()
}

main <- function() {
  rq2 <- "rq2_nsd/results"
  tab <- integration_table(read.csv(file.path(rq2, "h2_results.csv")), read.csv(file.path(rq2, "trial_counts.csv")),
                           read.csv("rq3_stimulation/results/h3_results_r0.5.csv"))
  dir.create("results", showWarnings = FALSE)
  write.csv(tab, "results/integration_table.csv", row.names = FALSE)
  integration_plot(tab, "results/integration.png")
  cat("integration table and figure written to results/\n")
}

if (sys.nframe() == 0 && "--run" %in% commandArgs(trailingOnly = TRUE)) main()
