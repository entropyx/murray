import pandas as pd
from logger_config import get_logger

logger = get_logger("auxiliary")

def handle_duplicates(data, subset=['time', 'location'], agg_method='mean'):
    """
    Handle duplicate entries in a DataFrame by aggregating them.
    
    Args:
        data (pd.DataFrame): The DataFrame to check for duplicates
        subset (list): Columns to check for duplicates
        agg_method (str): Aggregation method ('mean', 'sum', 'first', 'last')
    
    Returns:
        pd.DataFrame: DataFrame with duplicates handled
    """
    logger.info(f"Starting duplicate handling for {len(data)} rows")

    
    if data.empty:
        logger.warning("DataFrame is empty, returning as is")
        return data
    
    # Check if required columns exist
    missing_cols = [col for col in subset if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Missing columns for duplicate check: {missing_cols}")
    
    duplicates = data.duplicated(subset=subset, keep=False)
    if duplicates.any():
        logger.warning(f"Found {duplicates.sum()} duplicate entries in the data. Aggregating by {agg_method}.")
        # Group by subset columns and aggregate Y values
        data = data.groupby(subset)['Y'].agg(agg_method).reset_index()
        logger.info(f"Data shape after deduplication: {data.shape}")
    else:
        logger.info("No duplicate entries found")
    
    # Verify no duplicates remain
    if data.duplicated(subset=subset).any():
        raise ValueError(f"Duplicate entries still exist after aggregation in columns {subset}. Please check your data.")
    
    logger.info("Duplicate handling completed successfully")
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

        
        missing_columns = [col for col in [col_target, col_locations, col_dates] if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

        
        invalid_values = ['(not set)', 'nan']
        data = data[~data[col_locations].isin(invalid_values)]
        data = data.dropna(subset=[col_locations])

        
        data[col_locations] = data[col_locations].str.strip().str.lower()

        
        data_input = data.rename(columns={
            col_locations: 'location',
            col_target: 'Y',
            col_dates: 'time'
        })

        
        if data_input.empty:
            raise ValueError(f"The DataFrame is empty after processing. Please check your data in the {col_target} column.")

        
        data_input['time'] = pd.to_datetime(data_input['time'], errors='coerce')

        
        if data_input['time'].isna().any():
            raise ValueError("Some dates are invalid. Please check and correct them.")

        
        if not data_input['time'].notna().any():
            raise ValueError("No valid dates found in the 'time' column. Please check your data.")

        
        all_dates = pd.date_range(start=data_input['time'].min(), end=data_input['time'].max(), freq='D')
        all_locations = data_input['location'].unique()

        
        if data_input['location'].isna().any():
            raise ValueError("NaN values found in the 'location' column. Please review the data.")

        
        if len(all_locations) == 0:
            raise ValueError("No valid locations found after cleaning. Please check your data.")

        
        data_input = handle_duplicates(data_input, subset=['time', 'location'], agg_method='mean')
        
        
        full_index = pd.MultiIndex.from_product([all_dates, all_locations], names=['time', 'location'])
        full_data = pd.DataFrame(index=full_index).reset_index()
        full_data['time'] = pd.to_datetime(full_data['time'])

        
        merged_data = pd.merge(full_data, data_input, on=['time', 'location'], how='left')
        merged_data['Y'] = merged_data['Y'].fillna(fill_value)

        
        zero_counts = merged_data.groupby('location')['Y'].apply(lambda x: (x == 0).sum())
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
    logger.info("Starting market correlations calculation")
    logger.info(f"Input data shape: {data.shape}")
    
    required_columns = {'time', 'location', 'Y'}
    if not required_columns.issubset(data.columns):
        raise ValueError(f"The DataFrame must contain the columns: {required_columns}")

    # Check for duplicate entries and handle them
    logger.info("Checking for duplicates before pivot...")
    data = handle_duplicates(data, subset=['time', 'location'], agg_method='mean')
    
    logger.info("Creating pivot table for correlation calculation...")
    pivoted_data = data.pivot(index='time', columns='location', values='Y')
    logger.info(f"Pivot table shape: {pivoted_data.shape}")
    logger.info(f"Number of locations: {pivoted_data.shape[1]}")
    logger.info(f"Number of time periods: {pivoted_data.shape[0]}")
    
    logger.info("Calculating correlation matrix...")
    correlation_matrix = pivoted_data.corr(method='pearson')
    logger.info(f"Correlation matrix shape: {correlation_matrix.shape}")
    
    # Log some correlation statistics
    logger.info(f"Correlation statistics:")
    logger.info(f"  Min correlation: {correlation_matrix.values[correlation_matrix.values != 1.0].min():.4f}")
    logger.info(f"  Max correlation: {correlation_matrix.values[correlation_matrix.values != 1.0].max():.4f}")
    logger.info(f"  Mean correlation: {correlation_matrix.values[correlation_matrix.values != 1.0].mean():.4f}")
    
    logger.info("Market correlations calculation completed successfully")
    return correlation_matrix