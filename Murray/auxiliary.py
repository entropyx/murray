import pandas as pd

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
        pd.DataFrame: A cleaned and processed DataFrame, indexed by date and location, with missing
                      values in the target column filled and ready for visualization or analysis.
    """
    # Remove rows with invalid location values
    valores_no_validos = ['(not set)']
    data = data[~data[col_locations].isin(valores_no_validos)]
    data = data.dropna(subset=[col_locations])

    # Clean the location column
    data[col_locations] = data[col_locations].str.strip().str.lower()

    # Rename columns 
    data_input = data.rename(columns={
        col_locations: 'location',
        col_target: 'Y',
        col_dates: 'time'
    })

    # Generate a complete date range from the minimum to maximum date
    all_dates = pd.date_range(start=data_input['time'].min(), end=data_input['time'].max(), freq='D')
    data_input['time'] = pd.to_datetime(data_input['time'])
    all_locations = data_input['location'].unique()
    full_index = pd.MultiIndex.from_product([all_dates, all_locations], names=['time', 'location'])
    full_data = pd.DataFrame(index=full_index).reset_index()
    full_data['time'] = pd.to_datetime(full_data['time'])
    merged_data = pd.merge(full_data, data_input, on=['time', 'location'], how='left')
    merged_data['Y'] = merged_data['Y'].fillna(fill_value)

    # Sort the DataFrame by time and location 
    merged_data = merged_data.sort_values(by=['time', 'location'])

    # Identify rows with missing location values 
    if merged_data['location'].isna().any():
        raise ValueError("NaN values found in the 'location' column. Please review the data.")

    return merged_data


def market_correlations(data, excluded_states):
        """
        Determines similarity between states using correlations, while excluding specific states.

        Args:
            data (pd.DataFrame): The DataFrame containing the locations of interest.
            excluded_states (set): A set of states to exclude from the correlation matrix.

        Returns:
            correlation_matrix (pd.DataFrame): DataFrame containing correlations between locations in a standard matrix format.
        """

        required_columns = {'time', 'location', 'Y'}
        if not required_columns.issubset(data.columns):
            raise ValueError(f"The DataFrame must contain the columns: {required_columns}")

        # Create the correlation matrix
        pivoted_data = data.pivot(index='time', columns='location', values='Y')
        correlation_matrix = pivoted_data.corr(method='pearson')



        # Reshape the correlation matrix to long format
        correlation_df = correlation_matrix.reset_index().melt(
            id_vars='location',
            var_name='var2',
            value_name='correlation')
        # Sort values for each state by correlation (highest to lowest)
        sorted_correlation_df = (
            correlation_df
            .sort_values(by=['location', 'correlation'], ascending=[True, False])
            .query("location != var2"))
        # Assign a rank based on correlation
        sorted_correlation_df['rank'] = sorted_correlation_df.groupby('location').cumcount() + 2
        wide_correlation_df = (
            sorted_correlation_df
            .pivot(index='location', columns='rank', values='var2')
            .reset_index())
        wide_correlation_df.columns = ['location'] + [f"location_{i}" for i in range(2, len(wide_correlation_df.columns) + 1)]

        return correlation_matrix
