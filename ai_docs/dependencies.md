# Dependencies

This project relies on several key Python libraries.

## Core Libraries

- **`streamlit`:** Used to create the interactive web application.
- **`pandas`:** For data manipulation and analysis.
- **`numpy`:** For numerical operations.
- **`scikit-learn`:** Used for machine learning tasks, including the `Ridge` regression model for adjustments in the synthetic control model.
- **`cvxpy`:** A Python-embedded modeling language for convex optimization problems. It is used to solve the optimization problem in the `SyntheticControl` model.
- **`plotly`:** For creating interactive plots and visualizations.
- **`filelock`:** To prevent race conditions when writing to the metrics file.

## Other Libraries

- **`matplotlib`**, **`seaborn`**: For plotting.
- **`statsmodels`**: For statistical computations.
- **`loguru`**: For logging.
