# Runs every tests/R/test_*.R; any failed stopifnot() stops with a non-zero exit.
files <- sort(list.files("tests/R", pattern = "^test_.*\\.R$", full.names = TRUE))
for (f in files) {
  cat("running", f, "\n")
  sys.source(f, envir = new.env())
}
cat("R tests:", length(files), "files passed\n")
