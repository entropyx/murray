import pandas as pd
import numpy as np
from scipy import stats
from logger_config import get_logger

logger = get_logger("auxiliary")


def handle_duplicates(data, subset=["time", "location"], agg_method="mean"):
    """
    Handle duplicate entries in a DataFrame by aggregating them.

    Args:
        data (pd.DataFrame): The DataFrame to check for duplicates
        subset (list): Columns to check for duplicates
        agg_method (str): Aggregation method ('mean', 'sum', 'first', 'last')

    Returns:
        pd.DataFrame: DataFrame with duplicates handled
    """

    if data.empty:
        logger.warning("DataFrame is empty, returning as is")
        return data

    missing_cols = [col for col in subset if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Missing columns for duplicate check: {missing_cols}")

    duplicates = data.duplicated(subset=subset, keep=False)
    if duplicates.any():
        logger.warning(
            f"Found {duplicates.sum()} duplicate entries in the data. Aggregating by {agg_method}."
        )

        data = data.groupby(subset)["Y"].agg(agg_method).reset_index()
    else:
        logger.debug("No duplicate entries found")

    if data.duplicated(subset=subset).any():
        raise ValueError(
            f"Duplicate entries still exist after aggregation in columns {subset}. Please check your data."
        )

    return data


def cleaned_data(data, col_target, col_locations, col_dates, fill_value=0):
    """
    Cleans and processes input data to prepare it for analysis and visualization.

    Parameters:
        data (pd.DataFrame): The input DataFrame containing the data to clean.
        col_target (str): The name of the column containing the target variable (e.g., conversions).
        col_locations (str): The name of the column representing the locations.
        col_dates (str): The name of the column with date information.
        fill_value (int, optional): The value to use for filling missing target values. Defaults to 0.

    Returns:
        pd.DataFrame: A cleaned and processed DataFrame, indexed by date and location.
    """
    try:

        if not isinstance(data, pd.DataFrame):
            raise TypeError("Input data must be a pandas DataFrame.")

        missing_columns = [
            col
            for col in [col_target, col_locations, col_dates]
            if col not in data.columns
        ]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

        invalid_values = ["(not set)", "nan"]
        data = data[~data[col_locations].isin(invalid_values)]
        data = data.dropna(subset=[col_locations])

        data[col_locations] = data[col_locations].str.strip().str.lower()

        data_input = data.rename(
            columns={col_locations: "location", col_target: "Y", col_dates: "time"}
        )

        if data_input.empty:
            raise ValueError(
                f"The DataFrame is empty after processing. Please check your data in the {col_target} column."
            )

        data_input["time"] = pd.to_datetime(data_input["time"], errors="coerce")

        if data_input["time"].isna().any():
            raise ValueError("Some dates are invalid. Please check and correct them.")

        if not data_input["time"].notna().any():
            raise ValueError(
                "No valid dates found in the 'time' column. Please check your data."
            )

        all_dates = pd.date_range(
            start=data_input["time"].min(), end=data_input["time"].max(), freq="D"
        )
        all_locations = data_input["location"].unique()

        if data_input["location"].isna().any():
            raise ValueError(
                "NaN values found in the 'location' column. Please review the data."
            )

        if len(all_locations) == 0:
            raise ValueError(
                "No valid locations found after cleaning. Please check your data."
            )

        data_input = handle_duplicates(
            data_input, subset=["time", "location"], agg_method="mean"
        )

        full_index = pd.MultiIndex.from_product(
            [all_dates, all_locations], names=["time", "location"]
        )
        full_data = pd.DataFrame(index=full_index).reset_index()
        full_data["time"] = pd.to_datetime(full_data["time"])

        merged_data = pd.merge(
            full_data, data_input, on=["time", "location"], how="left"
        )
        merged_data["Y"] = merged_data["Y"].fillna(fill_value)

        zero_counts = merged_data.groupby("location")["Y"].apply(
            lambda x: (x == 0).sum()
        )
        high_zero_locations = zero_counts[zero_counts > len(merged_data) * 0.8]

        return merged_data

    except (TypeError, ValueError) as e:
        logger.error(f"Data Cleaning Error: {str(e)}")
        raise ValueError(f"Data Cleaning Error: {str(e)}") from e
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise Exception(f"An unexpected error occurred: {str(e)}") from e


def market_correlations(data):
    """
    Determines similarity between locations using correlations.

    Args:
        data (pd.DataFrame): The DataFrame containing the locations of interest.
        excluded_states (set): A set of states to exclude from the correlation matrix.

    Returns:
        correlation_matrix (pd.DataFrame): DataFrame containing correlations between locations in a standard matrix format.
    """

    required_columns = {"time", "location", "Y"}
    if not required_columns.issubset(data.columns):
        raise ValueError(f"The DataFrame must contain the columns: {required_columns}")

    pivoted_data = data.pivot(index="time", columns="location", values="Y")

    correlation_matrix = pivoted_data.corr(method="pearson")
    return correlation_matrix


def analyze_data_characteristics(data, col_target="Y"):
    """
    Analyze data characteristics to recommend appropriate statistical test functions.
    
    Args:
        data (pd.DataFrame): The DataFrame containing the data to analyze.
        col_target (str): The name of the target variable column.
        
    Returns:
        dict: Dictionary containing data characteristics and test recommendations.
    """
    logger.info("Analyzing data characteristics for statistical test selection")
    
    try:
        if col_target not in data.columns:
            raise ValueError(f"Target column '{col_target}' not found in data")
        
        target_data = data[col_target].dropna()
        
        if len(target_data) < 3:
            logger.warning("Insufficient data for statistical analysis")
            return {
                "sample_size": len(target_data),
                "recommended_test": "sum",
                "confidence": "low",
                "reason": "Insufficient data for statistical analysis"
            }
        
        # Basic statistics
        sample_size = len(target_data)
        mean_val = target_data.mean()
        median_val = target_data.median()
        std_val = target_data.std()
        min_val = target_data.min()
        max_val = target_data.max()
        
        # Check for normality (Shapiro-Wilk test)
        if sample_size <= 5000:  # Shapiro-Wilk works best for smaller samples
            normality_stat, normality_p = stats.shapiro(target_data)
            is_normal = normality_p > 0.05
            normality_test = "Shapiro-Wilk"
        else:
            # Use D'Agostino's test for larger samples
            normality_stat, normality_p = stats.normaltest(target_data)
            is_normal = normality_p > 0.05
            normality_test = "D'Agostino-Pearson"
        
        # Check for outliers using IQR method
        Q1 = target_data.quantile(0.25)
        Q3 = target_data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = target_data[(target_data < lower_bound) | (target_data > upper_bound)]
        has_outliers = len(outliers) > 0
        outlier_percentage = (len(outliers) / len(target_data)) * 100
        
        # Check if data is count/discrete
        is_integer = target_data.apply(lambda x: x == int(x) if pd.notna(x) else False).all()
        is_non_negative = (target_data >= 0).all()
        
        # Check skewness
        skewness = stats.skew(target_data)
        is_skewed = abs(skewness) > 1.0  # Moderate to high skewness
        
        # Determine data type characteristics
        if is_integer and is_non_negative and mean_val > 0:
            data_type = "count"
        elif is_non_negative and not is_integer:
            data_type = "continuous_positive"
        elif is_integer:
            data_type = "discrete"
        else:
            data_type = "continuous"
        
        # Decision tree for test recommendation
        recommended_test, confidence, reason = _recommend_statistical_test(
            data_type=data_type,
            is_normal=is_normal,
            has_outliers=has_outliers,
            outlier_percentage=outlier_percentage,
            sample_size=sample_size,
            is_skewed=is_skewed,
            skewness=skewness
        )
        
        return {
            "sample_size": sample_size,
            "mean": mean_val,
            "median": median_val,
            "std": std_val,
            "min": min_val,
            "max": max_val,
            "data_type": data_type,
            "is_normal": is_normal,
            "normality_p_value": normality_p,
            "normality_test": normality_test,
            "has_outliers": has_outliers,
            "outlier_count": len(outliers),
            "outlier_percentage": outlier_percentage,
            "skewness": skewness,
            "is_skewed": is_skewed,
            "recommended_test": recommended_test,
            "confidence": confidence,
            "reason": reason
        }
        
    except Exception as e:
        logger.error(f"Error analyzing data characteristics: {str(e)}")
        return {
            "sample_size": 0,
            "recommended_test": "sum",
            "confidence": "low",
            "reason": f"Error in analysis: {str(e)}"
        }


def _recommend_statistical_test(data_type, is_normal, has_outliers, outlier_percentage, 
                               sample_size, is_skewed, skewness):
    """
    Internal function to recommend statistical test based on data characteristics.
    
    Returns:
        tuple: (recommended_test, confidence, reason)
    """
    
    # High confidence recommendations
    if data_type == "count" and not has_outliers:
        return "sum", "high", "Count data without outliers - sum test captures total impact"
    
    if data_type == "count" and has_outliers and outlier_percentage > 10:
        return "median_diff", "high", "Count data with significant outliers - median test is robust"
    
    if not is_normal and (is_skewed or has_outliers) and outlier_percentage > 5:
        return "median_diff", "high", "Non-normal data with outliers - median test is robust to outliers"
    
    if is_normal and not has_outliers and sample_size >= 30:
        return "mean_diff", "high", "Normal data without outliers - mean test is optimal"
    
    if is_normal and not has_outliers and sample_size < 30:
        return "t_test", "high", "Normal data with small sample - t-test accounts for sample size"
    
    # Medium confidence recommendations
    if data_type == "continuous_positive" and not is_skewed and not has_outliers:
        return "mean_diff", "medium", "Continuous positive data - mean test suitable"
    
    if not is_normal and not has_outliers and sample_size >= 50:
        return "mean_diff", "medium", "Non-normal data without outliers - mean test with large sample"
    
    if is_normal and has_outliers and outlier_percentage <= 5:
        return "mean_diff", "medium", "Normal data with few outliers - mean test acceptable"
    
    # Low confidence / fallback recommendations
    if has_outliers and outlier_percentage > 15:
        return "median_diff", "low", "High outlier percentage - median test as fallback"
    
    if abs(skewness) > 2:
        return "median_diff", "low", "Highly skewed data - median test as fallback"
    
    if sample_size < 10:
        return "median_diff", "low", "Very small sample - median test as conservative choice"
    
    # Default recommendation
    return "sum", "low", "Default recommendation - sum test for general use"


def get_test_explanation(test_type):
    """
    Get explanation for each statistical test type.
    
    Args:
        test_type (str): The statistical test type.
        
    Returns:
        dict: Dictionary with explanation, use_cases, and assumptions.
    """
    explanations = {
        "sum": {
            "name": "Sum Test",
            "description": "Tests the total cumulative effect across the treatment period",
            "use_cases": [
                "Count data (sales, conversions, clicks)",
                "When total impact/volume matters",
                "Business metrics where absolute magnitude is important"
            ],
            "assumptions": [
                "Data represents counts or totals",
                "Non-negative values",
                "Additive effects are meaningful"
            ],
            "formula": "Σ(treatment_residuals)",
            "interpretation": "Detects changes in total volume or count"
        },
        "mean_diff": {
            "name": "Mean Difference Test",
            "description": "Tests the average difference between treatment and control",
            "use_cases": [
                "Continuous data with normal distribution",
                "Per-unit effects (average order value)",
                "When you want to detect average changes"
            ],
            "assumptions": [
                "Data is approximately normally distributed",
                "Similar variances between groups",
                "No significant outliers"
            ],
            "formula": "Mean(treatment_residuals)",
            "interpretation": "Detects changes in average values"
        },
        "t_test": {
            "name": "T-Test Statistic",
            "description": "Tests standardized mean difference accounting for variance and sample size",
            "use_cases": [
                "Normal data with small sample sizes",
                "When you need standardized effect sizes",
                "A/B testing with continuous outcomes"
            ],
            "assumptions": [
                "Data is normally distributed",
                "Independent observations",
                "Constant variance"
            ],
            "formula": "Mean(residuals) / (Std(residuals) / √n)",
            "interpretation": "Detects standardized changes accounting for variability"
        },
        "median_diff": {
            "name": "Median Difference Test",
            "description": "Tests the median difference, robust to outliers and non-normal data",
            "use_cases": [
                "Non-normal or skewed data",
                "Data with outliers",
                "When you want robust estimates"
            ],
            "assumptions": [
                "Independent observations",
                "Ordinal or continuous data",
                "Minimal assumptions about distribution"
            ],
            "formula": "Median(treatment_residuals)",
            "interpretation": "Detects changes in median values, robust to outliers"
        }
    }
    
    return explanations.get(test_type, {
        "name": "Unknown Test",
        "description": "Test type not recognized",
        "use_cases": [],
        "assumptions": [],
        "formula": "Unknown",
        "interpretation": "Unknown"
    })
