import os


def _limit_blas_threads():
    """Limit internal BLAS/OpenMP threads to 1 per worker process.

    We parallelize at the process level (4 workers × 1 core each),
    so BLAS must not spawn its own threads or we oversubscribe the 4 vCPUs.
    """
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
