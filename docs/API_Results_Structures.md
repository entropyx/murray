# API Result Structures

This document outlines the data structure of the results returned by the Murray API for each analysis type.

---

## 1. Experimental Design (`/analyze/design`)

The result from a design task is a JSON object containing the analysis mode and the detailed results.

```json
{
  "analysis_mode": "single-cell" or "multicell",
  "multicell_config": { ... } or null,
  "global_optimization": true or false,
  "results": { ... } 
}
```

### 1.1. Single-Cell Mode Results

When `analysis_mode` is `single-cell`, the `results` object contains the following keys:

-   **`results_by_size`**: An object where each key is a group size (as a string). The value is an object with details for the best group found for that size.
    -   `Best Treatment Group`: Array of location strings.
    -   `Control Group`: Array of location strings.
    -   `MAPE`: Float.
    -   `SMAPE`: Float.
    -   `Holdout Percentage`: Float.
    -   `observed_conformity`: Float.
    -   `Actual Target Metric (y)`: Array of numbers (time series).
    -   `Predictions`: Array of numbers (time series).
    -   `Weights`: Array of numbers.
-   **`sensitivity_results`**: An object containing the sensitivity analysis. Keys are group sizes. Values are objects where keys are treatment periods.
    -   `MDE`: The Minimum Detectable Effect (Float or null).
    -   `P-Value`: The p-value associated with the MDE (Float or null).
    -   `Power`: The statistical power (Float or null).
    -   `MDE_CI`: Confidence interval for the MDE (Array of two floats or null).
    -   `Statistical Power`: An array of tuples, each with `[delta, power, power_ci, p_value]`.
-   **`lift_series`**: Object containing time series data with simulated lifts.
-   **`correlation_matrix`**: A matrix (array of arrays) showing correlations between locations.
-   **`df_pivot`**: The pivoted data used for analysis (array of arrays).
-   **`data_info`**: Object with summary statistics of the input data.

### 1.2. Multi-Cell Mode Results

When `analysis_mode` is `multicell`, the `results` object contains a single key:

-   **`global_experiment`**: An array of objects, where each object represents a single optimized cell.
    -   `Cell`: Integer identifier for the cell.
    -   `Size`: Integer, the number of locations in the treatment group.
    -   `Best Treatment Group`: Array of location strings.
    -   `Control Group`: Array of location strings.
    -   `MAPE`: Float.
    -   `SMAPE`: Float.
    -   `Holdout Percentage`: Float.
    -   `observed_conformity`: Float.
    -   `Actual Target Metric (y)`: Array of numbers (time series).
    -   `Predictions`: Array of numbers (time series).
    -   `Weights`: Array of numbers.

---

## 2. Experimental Evaluation (`/analyze/evaluation`)

The result from an evaluation task is a JSON object with the following structure:

-   **`MAPE`**: Mean Absolute Percentage Error (Float).
-   **`SMAPE`**: Symmetric Mean Absolute Percentage Error (Float).
-   **`p_value`**: The calculated p-value from the permutation test (Float).
-   **`power`**: The statistical power (Float).
-   **`percenge_lift`**: The percentage lift observed in the treatment group (Float).
-   **`period`**: The duration of the treatment period in days (Integer).
-   **`spend`**: The spend value provided for the evaluation (Float).
-   **`length_treatment`**: The number of locations in the treatment group (Integer).
-   **`control_group`**: Array of location strings used as the control.
-   **`weights`**: An array of float values representing the contribution of each control location.
-   **`observed_stat`**: The observed test statistic (Float).
-   **`counterfactual`**: An array of numbers representing the predicted time series for the treatment group had it not received treatment.
-   **`treatment`**: An array of numbers representing the actual time series for the treatment group.
-   **`null_stats`**: An array of numbers representing the distribution of the test statistic under the null hypothesis.
