# Core Library (`Murray/`)

The `Murray/` directory contains the core logic for the geographical incrementality testing.

## Key Modules

- **`main.py`:** This is the heart of the library.
    - `BetterGroups`: This is the main function that orchestrates the process of finding the best treatment and control groups. It uses a synthetic control model to evaluate different combinations of locations.
    - `evaluate_sensitivity`: This function performs a sensitivity analysis to calculate the Minimum Detectable Effect (MDE) for different scenarios.
    - `SyntheticControl`: A class that implements the synthetic control model using `cvxpy` for optimization.

- **`auxiliary.py`:** This module provides helper functions for data manipulation.
    - `handle_duplicates`:  Handles duplicate entries in the data.
    - `cleaned_data`:  Cleans and prepares the data for analysis.
    - `market_correlations`: Calculates the correlation between different markets.

- **`metrics.py`:** This module is responsible for tracking application usage. It logs events to a JSON file.

- **`plots.py`:** This module contains functions to generate the various plots used in the Streamlit application, such as the MDE heatmap.
