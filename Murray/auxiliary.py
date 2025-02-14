import streamlit as st
import pandas as pd
import difflib  # Library for fuzzy matching

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
    
    
    invalid_values = ['(not set)']
    data = data[~data[col_locations].isin(invalid_values)]
    data = data.dropna(subset=[col_locations])
    
    
    data[col_locations] = data[col_locations].str.strip().str.lower()

    
    data_input = data.rename(columns={
        col_locations: 'location',
        col_target: 'Y',
        col_dates: 'time'
    })

    try:
        
        if data_input.empty:
            st.error("The DataFrame is empty. Please upload the data correctly.")
            st.stop()

        
        missing_columns = [col for col in ['time', 'location', 'Y'] if col not in data_input.columns]
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}")
            st.stop()

        
        try:
            data_input['time'] = pd.to_datetime(data_input['time'], errors='coerce')  # Converts invalid values to NaT
            
            
            if data_input['time'].isna().any():
                st.error("Some dates are invalid. Please correct them.")
                st.stop()

        except Exception as e:
            st.error(f"Error while converting dates: {str(e)}")
            st.stop()

        
        if not data_input['time'].notna().any():
            st.error("No valid dates found in the 'time' column. Please check your data.")
            st.stop()

        
        all_dates = pd.date_range(start=data_input['time'].min(), end=data_input['time'].max(), freq='D')
        all_locations = data_input['location'].unique()

        
        if data_input['location'].isna().any():
            st.error("NaN values found in the 'location' column. Please review the data.")
            st.stop()

        if len(all_locations) == 0:
            st.error("No valid locations found after cleaning. Please check your data.")
            st.stop()

        
        location_counts = data_input['location'].value_counts()
        low_freq_locations = location_counts[location_counts < 5].index  

        suggested_corrections = {}
        for loc in low_freq_locations:
            close_matches = difflib.get_close_matches(loc, all_locations, n=1, cutoff=0.8)
            if close_matches and close_matches[0] != loc:
                suggested_corrections[loc] = close_matches[0]
        if not low_freq_locations.empty:
            st.write(" **Locations with few values:**", ", ".join(low_freq_locations))


        
        full_index = pd.MultiIndex.from_product([all_dates, all_locations], names=['time', 'location'])
        full_data = pd.DataFrame(index=full_index).reset_index()
        full_data['time'] = pd.to_datetime(full_data['time'])
        
        
        merged_data = pd.merge(full_data, data_input, on=['time', 'location'], how='left')
        merged_data['Y'] = merged_data['Y'].fillna(fill_value)  

        
        zero_counts = merged_data.groupby('location')['Y'].apply(lambda x: (x == 0).sum())
        high_zero_locations = zero_counts[zero_counts > len(merged_data) * 0.8]  

        if not high_zero_locations.empty:
            st.warning(f"Some locations have too many zero values in the target column: {', '.join(high_zero_locations.index)}. This may affect the analysis.")

        merged_data = merged_data.sort_values(by=['time', 'location'])

        return merged_data

    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        st.stop()




def market_correlations(data):
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

    
    threshold = 0.5
    pivoted_data = data.pivot(index='time', columns='location', values='Y')
    correlation_matrix = pivoted_data.corr(method='pearson')

    avg_correlation = correlation_matrix.stack().mean()
    if avg_correlation < threshold:
        st.warning(f"⚠️ Low correlation detected! Average correlation: {avg_correlation:.2f}. "
                   "This may affect the quality of the results.")
        
    correlation_df = correlation_matrix.reset_index().melt(
        id_vars='location',
        var_name='var2',
        value_name='correlation'
    )


    sorted_correlation_df = (
        correlation_df
        .sort_values(by=['location', 'correlation'], ascending=[True, False])
        .query("location != var2")
    )


    sorted_correlation_df['rank'] = sorted_correlation_df.groupby('location').cumcount() + 2
    

    wide_correlation_df = (
        sorted_correlation_df
        .pivot(index='location', columns='rank', values='var2')
        .reset_index()
    )

    wide_correlation_df.columns = ['location'] + [f"location_{i}" for i in range(2, len(wide_correlation_df.columns) + 1)]

    return correlation_matrix
