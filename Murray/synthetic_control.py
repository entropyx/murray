import concurrent.futures
import multiprocessing

import numpy as np
import cvxpy as cp
from sklearn.preprocessing import MinMaxScaler
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.linear_model import Ridge

from logger_config import get_logger

from .parallel import _limit_blas_threads

logger = get_logger("synthetic_control")

_ASCM_LAMBDAS = (0.1, 0.5, 1.0, 5.0, 20.0, 100.0)
_ASCM_MIN_IMPROVEMENT = 0.05


class SyntheticControl(BaseEstimator, RegressorMixin):
    """
    Simplex synthetic control (Abadie: ``sum(w)=1, w>=0``) with an optional Ridge-on-time
    adjustment of the pre-intervention residuals.

    Note (ISS-11): when ``use_ridge_adjustment=True`` the model fits a Ridge regression of
    the residuals on *time* and extrapolates that linear-in-time correction past the
    training window. This is an augmented-SCM-style choice (cf. Ben-Michael, Feller &
    Rothstein 2021) that **re-introduces extrapolation outside the convex hull** the simplex
    is designed to stay within — it deviates from Abadie's no-extrapolation guarantee and
    can amplify sensitivity to a spurious trend, especially with a small donor pool. It is a
    deliberate modeling decision, not a free lunch; validate that it does not degrade the
    holdout fit.
    """

    def __init__(
        self,
        regularization_strength_l1=0.1,
        regularization_strength_l2=0.1,
        seasonality=None,
        delta=1.0,
        use_ridge_adjustment=False,
        ridge_alpha=1.0,
        augmentation=None,
    ):
        """
        Args:
            regularization_strength_l1: Strength of L1 regularization (not used in this example, but can be expanded).
            regularization_strength_l2: Strength of L2 regularization in the optimization of the weights.
            seasonality: DataFrame with the calculated seasonality, indexed by time.
            delta: Parameter for the Huber loss function (not used in this example).
            use_ridge_adjustment: If True, adjusts the pre-intervention residual with Ridge regression on TIME (legacy).
            ridge_alpha: Ridge regularization strength (used by both the time-ridge and the ASCM augmentation).
            augmentation: None (legacy, controlled by use_ridge_adjustment), "ascm" (principled
                Ben-Michael ridge-augmented SCM in DONOR space — corrects the simplex fit by
                ridge-regressing the pre-period residual onto the donors, allowing controlled
                extrapolation outside the convex hull; supersedes the ridge-on-time hack of
                ISS-11), or "none" (plain simplex). When "ascm", the time-ridge is not used.
        """
        self.regularization_strength_l1 = regularization_strength_l1
        self.regularization_strength_l2 = regularization_strength_l2
        self.seasonality = seasonality
        self.delta = delta
        self.use_ridge_adjustment = use_ridge_adjustment
        self.ridge_alpha = ridge_alpha
        self.augmentation = augmentation

    def _prepare_data(self, X, time_index=None):
        """
        Combines the original features with seasonality if available.

        Args:
            X: Input features
            time_index: Time index in case of using seasonality

        Returns:
            numpy.ndarray: Processed features matrix
        """
        X = np.array(X)
        if self.seasonality is not None and time_index is not None:
            if len(time_index) != X.shape[0]:
                raise ValueError("The size of the time index does not match X.")
            seasonal_values = self.seasonality.loc[time_index].to_numpy().reshape(-1, 1)
            X = np.hstack([X, seasonal_values])
        return X

    def squared_loss(self, x):
        """Calculates the quadratic loss."""
        return cp.sum_squares(x)

    def fit(self, X, y, time_train=None):
        """
        Fits the synthetic control model.

        Args:
            X: Training features
            y: Target values
            time_train (optional): Time vector or indices for the training data, required if Ridge adjustment is enabled.

        Returns:
            self: Fitted model
        """

        X_proc = self._prepare_data(X, time_index=time_train)
        y = np.ravel(y)

        if X_proc.shape[0] != y.shape[0]:
            raise ValueError("The number of rows in X must match the size of y.")

        w = cp.Variable(X_proc.shape[1])
        errors = X_proc @ w - y

        regularization_l2 = self.regularization_strength_l2 * cp.norm2(w)
        objective = cp.Minimize(self.squared_loss(errors) + regularization_l2)
        constraints = [cp.sum(w) == 1, w >= 0]
        problem = cp.Problem(objective, constraints)
        problem.solve(solver=cp.SCS, verbose=False)

        if problem.status != cp.OPTIMAL:
            problem.solve(solver=cp.ECOS, verbose=False)

        if problem.status != cp.OPTIMAL:
            raise ValueError(
                "The optimization did not converge. Status: " + problem.status
            )

        self.X_ = X_proc
        self.y_ = y
        self.w_ = w.value
        self.is_fitted_ = True

        self.synthetic_prediction_ = X_proc.dot(self.w_)
        self.w_aug_ = None

        if self.augmentation == "ascm":
            # Ben-Michael ridge-augmented SCM (donor space): correct the simplex weights by
            # ridge-regressing the pre-period residual onto the donors. The augmented weights
            # are NOT constrained to the simplex, so the counterfactual can extrapolate
            # outside the convex hull in a controlled way (lambda = ridge_alpha).
            #   ridge_corr = (y - X w) @ (X X^T + lambda I)^-1 @ X ;  w_aug = w + ridge_corr
            residual = y - self.synthetic_prediction_
            n_pre = X_proc.shape[0]
            gram = X_proc @ X_proc.T + self.ridge_alpha * np.eye(n_pre)
            self.w_aug_ = self.w_ + residual @ np.linalg.solve(gram, X_proc)
        elif self.use_ridge_adjustment:
            if time_train is None:
                raise ValueError("The time vector is required for Ridge adjustment.")
            self.residuals_ = y - self.synthetic_prediction_
            time_train = np.array(time_train).reshape(-1, 1)
            self.ridge_model_ = Ridge(alpha=self.ridge_alpha)
            self.ridge_model_.fit(time_train, self.residuals_)
        return self

    def predict(self, X, time_index=None):
        """
        Performs prediction using synthetic control. If Ridge adjustment is enabled and a time vector is provided,
        the prediction is adjusted with the predicted residual.

        Args:
            X: Test features
            time_index (optional): Time vector for the test data

        Returns:
            tuple: (predictions, weights)
                - predictions: numpy.ndarray with the final predictions
                - weights: numpy.ndarray with the fitted weights
        """
        if not self.is_fitted_:
            raise ValueError("The model has not been fitted yet. Call 'fit' first.")

        X_proc = self._prepare_data(X, time_index=time_index)
        base_prediction = X_proc.dot(self.w_)

        if self.augmentation == "ascm":
            # Counterfactual from the augmented weights; return the simplex weights for the
            # weight filter / donor display (w_aug can be negative under extrapolation).
            return X_proc.dot(self.w_aug_), self.w_

        if self.use_ridge_adjustment:
            if time_index is None:
                raise ValueError(
                    "The time vector is required to predict with the Ridge adjustment."
                )
            time_index = np.array(time_index).reshape(-1, 1)
            ridge_adjustment = self.ridge_model_.predict(time_index)
            return base_prediction + ridge_adjustment, self.w_

        return base_prediction, self.w_

    def filter_controls_by_weights(self, control_group, min_weight_threshold=0.001):
        """
        Filters control locations based on their weights, removing those with very small contributions.

        Args:
            control_group (list): List of control location names
            min_weight_threshold (float): Minimum weight threshold to keep a control location

        Returns:
            tuple: (filtered_control_group, filtered_weights)
                - filtered_control_group: List of control locations with significant weights
                - filtered_weights: Array of weights for the filtered control locations
        """
        if not self.is_fitted_:
            raise ValueError("The model has not been fitted yet. Call 'fit' first.")

        if len(control_group) != len(self.w_):
            raise ValueError(
                "The number of control locations must match the number of weights."
            )

        significant_indices = np.where(self.w_ >= min_weight_threshold)[0]

        if len(significant_indices) == 0:

            significant_indices = [np.argmax(self.w_)]

        filtered_control_group = [control_group[i] for i in significant_indices]
        filtered_weights = self.w_[significant_indices]

        if np.sum(filtered_weights) > 0:
            filtered_weights = filtered_weights / np.sum(filtered_weights)

        # Round weights to 2 decimal places
        filtered_weights = np.round(filtered_weights, 2)

        return filtered_control_group, filtered_weights


def smape(A, F):
    denominator = np.abs(A) + np.abs(F)
    denominator = np.where(denominator == 0, 1e-8, denominator)
    return 100 / len(A) * np.sum(2 * np.abs(F - A) / denominator)


def scaled_l2_imbalance(y, y_synth, donors):
    """
    Scaled L2 imbalance — a scale-invariant skill score for control fit quality (ISS-1).

        scaled_l2 = ||y - y_synth|| / ||y - mean(donors)||

    0 = perfect fit, ~1 = no better than the naive donor average, >1 = worse. The
    numerator is Abadie's pre-treatment RMSPE; normalizing by the naive donor mean makes
    it comparable across groups of different magnitude. Used as a diagnostic and as the
    deterministic tie-break in the two-stage selection (mitigates the non-uniqueness of
    the synthetic-control V).

    Args:
        y (array-like): observed treatment series (training window).
        y_synth (array-like): synthetic-control prediction over the same window.
        donors (array-like): donor level matrix (n_periods x n_donors) for the naive mean.

    Returns:
        float: the scaled L2 imbalance.
    """
    y = np.asarray(y, dtype=float).flatten()
    y_synth = np.asarray(y_synth, dtype=float).flatten()
    donors = np.asarray(donors, dtype=float)
    naive = donors.mean(axis=1) if donors.ndim == 2 else donors.flatten()
    denom = float(np.linalg.norm(y - naive))
    if denom <= 0:
        return 0.0
    return float(np.linalg.norm(y - y_synth) / denom)


def _fit_sc_counterfactual(X, y, split_index, augmentation=None, ridge_alpha=1.0):
    """
    Scale donors X and treatment y, fit a SyntheticControl on ``[:split_index]``, and
    predict the full series back on the original scale. Extracted so that evaluate_group
    and the sliding-window falsification (compute_falsification_metrics) use the IDENTICAL
    fit per window (ISS-1).

    Args:
        X (array-like): donor level matrix (n_periods x n_donors).
        y (array-like): treatment level series (n_periods,).
        split_index (int): end of the training window (clamped to [1, n-1]).
        augmentation (str|None): SCM augmentation — None (legacy ridge-on-time), "ascm"
            (Ben-Michael ridge-augmented SCM, ISS-11), or "auto" (CV the ASCM lambda and pick
            ridge-vs-ASCM by holdout fit — see _fit_sc_auto). Default keeps current behavior.
        ridge_alpha (float): ridge strength for the chosen augmentation.

    Returns:
        dict: {"counterfactual": full series (original scale), "y_original": full series,
               "model": fitted SyntheticControl, "split_index": clamped split}; "auto" also
               adds {"engine", "ridge_alpha"}.
    """
    if augmentation == "auto":
        return _fit_sc_auto(X, y, split_index)

    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1, 1)
    n = len(X)
    time_index = np.arange(n)

    scaler_x = MinMaxScaler()
    scaler_y = MinMaxScaler()
    X_scaled = scaler_x.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y)

    split_index = max(1, min(split_index, n - 1))

    model = SyntheticControl(
        use_ridge_adjustment=True, ridge_alpha=ridge_alpha, augmentation=augmentation
    )
    model.fit(
        X_scaled[:split_index], y_scaled[:split_index], time_train=time_index[:split_index]
    )

    counterfactual_full, _ = model.predict(X_scaled, time_index=time_index)
    counterfactual_full_original = scaler_y.inverse_transform(
        np.asarray(counterfactual_full).reshape(-1, 1)
    ).flatten()
    y_original = scaler_y.inverse_transform(y_scaled).flatten()

    return {
        "counterfactual": counterfactual_full_original,
        "y_original": y_original,
        "model": model,
        "split_index": split_index,
    }


def _rolling_origin_smapes(
    X, y, start_frac=0.5, end_frac=0.8, n_folds=2, augmentation=None, ridge_alpha=1.0
):
    """
    Forward-chaining out-of-sample SMAPEs (ISS-7).

    For each fold, fit the SCM on ``[0, origin)`` and score the SMAPE on the next block,
    walking the origin forward across ``[start_frac, end_frac]`` of the series. Averaging
    several origins lowers the variance of a single 80/20 split and de-sensitizes the
    ranking to a one-off shock in the most recent window (Bergmeir & Hyndman 2018). The
    ``augmentation``/``ridge_alpha`` args let the ASCM lambda-CV reuse this scorer.

    Returns:
        list[float]: one SMAPE per fold (empty if the series is too short).
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).flatten()
    n = len(X)
    smapes = []
    if n_folds < 1:
        return smapes
    start, end = int(start_frac * n), int(end_frac * n)
    if end <= start or start < 2:
        return smapes
    origins = np.linspace(start, end, n_folds + 1).astype(int)
    for i in range(n_folds):
        o0, o1 = int(origins[i]), int(origins[i + 1])
        if o1 <= o0 or o0 < 2:
            continue
        try:
            fit = _fit_sc_counterfactual(
                X[:o1], y[:o1], split_index=o0,
                augmentation=augmentation, ridge_alpha=ridge_alpha,
            )
            cf = fit["counterfactual"][o0:o1]
            yo = fit["y_original"][o0:o1]
            if len(yo) > 0:
                smapes.append(smape(yo, cf))
        except Exception as e:
            logger.debug(f"rolling-origin fold {i} skipped: {e}")
    return smapes


def _select_lambda_ascm(X, y, split_index, lambdas=_ASCM_LAMBDAS, cv_folds=3):
    """
    Cross-validate the ASCM ridge lambda by forward-chaining holdout SMAPE (Murray's own CV,
    ISS-7 — more appropriate for time series than pysyncon's leave-block-out). Picks the
    largest lambda within 1 SE of the minimum mean CV error (the "1-SE rule", parsimony →
    less extrapolation), like pysyncon's AugSynth. Returns a single lambda.
    """
    best_lambda = 1.0
    rows = []  # (lambda, mean_smape, se)
    for lam in lambdas:
        folds = _rolling_origin_smapes(
            X, y, n_folds=cv_folds, augmentation="ascm", ridge_alpha=lam
        )
        if folds:
            arr = np.asarray(folds, dtype=float)
            rows.append((lam, float(arr.mean()), float(arr.std() / np.sqrt(len(arr)))))
    if not rows:
        return best_lambda

    means = np.array([r[1] for r in rows])
    i_min = int(np.argmin(means))
    threshold = means[i_min] + rows[i_min][2]  # min + 1 SE
    # largest lambda whose mean is within 1 SE of the best (most regularized within tolerance)
    within = [r[0] for r in rows if r[1] <= threshold]
    return max(within) if within else rows[i_min][0]


def _fit_sc_auto(
    X, y, split_index, lambdas=_ASCM_LAMBDAS, cv_folds=3,
    min_improvement=_ASCM_MIN_IMPROVEMENT,
):
    """
    Combined engine selection (ISS-11): CV the ASCM lambda, then pick ridge-on-time vs
    ASCM(lambda*) by the holdout SMAPE on ``[split_index:]`` — so ASCM is used only where it
    actually improves the out-of-sample counterfactual, and ridge-on-time elsewhere. The
    downstream falsification gate (abs_lift_in_zero) still guards against a biased winner.

    ASCM must beat ridge by at least ``min_improvement`` (RELATIVE holdout SMAPE) to be
    chosen: the flip is decided on a single 80/20 holdout, so a sub-margin edge is treated as
    sampling noise and the default (ridge) is kept. ``min_improvement=0`` recovers the plain
    "any improvement flips" rule.

    Returns the chosen fit dict plus {"engine": "ascm"|"ridge_time", "ridge_alpha": lambda*}.
    """
    ridge_fit = _fit_sc_counterfactual(X, y, split_index, augmentation=None)
    s = ridge_fit["split_index"]
    ridge_smape = smape(ridge_fit["y_original"][s:], ridge_fit["counterfactual"][s:])

    lam = _select_lambda_ascm(X, y, split_index, lambdas=lambdas, cv_folds=cv_folds)
    try:
        ascm_fit = _fit_sc_counterfactual(X, y, split_index, augmentation="ascm", ridge_alpha=lam)
        ascm_smape = smape(ascm_fit["y_original"][s:], ascm_fit["counterfactual"][s:])
    except Exception as e:
        logger.debug(f"ASCM fit failed in auto-select, keeping ridge: {e}")
        ridge_fit.update({"engine": "ridge_time", "ridge_alpha": None})
        return ridge_fit

    if ascm_smape < ridge_smape * (1.0 - min_improvement):
        ascm_fit.update({"engine": "ascm", "ridge_alpha": lam})
        return ascm_fit
    ridge_fit.update({"engine": "ridge_time", "ridge_alpha": None})
    return ridge_fit


def _auto_engine_decision(X, y, split_index):
    """Picklable wrapper that returns ONLY the (engine, ridge_alpha) decision of _fit_sc_auto,
    so the selector can run in an isolated worker process without pickling the fitted model.
    """
    fit = _fit_sc_auto(X, y, split_index)
    return {"engine": fit.get("engine"), "ridge_alpha": fit.get("ridge_alpha")}


def select_engine_isolated(X, y, split_index, timeout=180):
    """
    Run the combined engine-selector in a SEPARATE single-threaded-BLAS process and return its
    decision as ``(augmentation, ridge_alpha, engine_label)``.

    Why isolate: _fit_sc_auto runs ~20 cvxpy/SCS solves. In the Modal container, running many
    solves in the main thread without limiting BLAS threads can trigger a native SIGSEGV
    (OpenBLAS/SCS), which no try/except can catch — it kills the whole runner and Modal retries
    it (a crash loop). Running it in a child process with ``_limit_blas_threads`` (the same
    guard BetterGroups' pool uses) addresses the threading cause AND means that if the child
    still dies, only the child dies: we fall back to ridge-on-time and the evaluation completes.

    Returns:
        (augmentation, ridge_alpha, engine_label): augmentation is "ascm" or None (the value to
        pass to SyntheticControl); engine_label is for logging ("ascm"/"ridge_time"/fallback).
    """
    # "spawn" (not the Linux default "fork"): the analysis runs inside a thread of the asyncio
    # loop, and forking from a thread copies held locks (malloc/OpenBLAS/import) into the child
    # → deadlock risk. spawn re-imports cleanly, and the image's single-thread BLAS env vars are
    # read at that import, so the child is genuinely single-threaded.
    executor = concurrent.futures.ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn"),
        initializer=_limit_blas_threads,
    )
    try:
        dec = executor.submit(
            _auto_engine_decision,
            np.asarray(X, dtype=float), np.asarray(y, dtype=float), int(split_index),
        ).result(timeout=timeout)
        aug = "ascm" if dec.get("engine") == "ascm" else None
        alpha = dec.get("ridge_alpha")
        return aug, (alpha if alpha is not None else 1.0), dec.get("engine")
    except Exception as e:
        logger.warning(
            f"isolated auto engine selection failed ({type(e).__name__}: {e}); "
            f"falling back to ridge-on-time"
        )
        return None, 1.0, "ridge_time(fallback)"
    finally:
        # Don't block on a hung child (a crash already raised BrokenProcessPool above).
        executor.shutdown(wait=False, cancel_futures=True)
