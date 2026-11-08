# Known-answer tests for integration.R on made-up RQ2 and RQ3 result tables.
source("integration.R")

h2 <- data.frame(model = c("H2a", "H2b", "H2b", "H2b"), subject = c("all", "all", "all", "subj01"),
                 term = c("sig_memory", "z_memory", "z_memory - z_control", "z_memory - z_control"),
                 estimate = c(0.9, 0.5, 0.20, 0.7), ci_low = c(0.5, 0.3, 0.05, 0.1), ci_high = c(1.3, 0.7, 0.35, 1.3),
                 p = c(0.01, 0.001, 0.009, 0.02))
counts <- data.frame(subject = rep(c("subj01", "subj02"), each = 4), outcome = rep(c("hit", "fa", "miss", "cr"), 2),
                     n = c(100, 40, 60, 300, 80, 20, 70, 330))
h3 <- data.frame(model = c("H3a", "H3b", "H3b"), term = c("field_map", "field_map", "field_map = field_control"),
                 estimate = c(0.3, 0.33, 0.45), ci_low = c(-2.9, -6, -5.1), ci_high = c(3.5, 6.6, 6.0),
                 p_cr2 = c(0.82, 0.88, 0.94), k_effects = 61, k_studies = 33)

tab <- integration_table(h2, counts, h3)
stopifnot(nrow(tab) == 2, identical(tab$hypothesis, c("H2b", "H3b")),
          identical(tab$estimate, c(0.20, 0.45)), identical(tab$ci_low, c(0.05, -5.1)), identical(tab$p, c(0.009, 0.94)),
          tab$n[1] == "240 trials answered old, 2 participants", tab$n[2] == "61 effects, 33 studies")

# a missing H2b difference row stops rather than writing a half-empty table
stopped <- tryCatch({ integration_table(h2[h2$model != "H2b", ], counts, h3); FALSE }, error = function(e) TRUE)
stopifnot(stopped)

png_path <- tempfile(fileext = ".png")
integration_plot(tab, png_path)
stopifnot(file.exists(png_path), file.size(png_path) > 0)
cat("integration: all known-answer tests passed\n")
