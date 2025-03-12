import pytest
import numpy as np
import pandas as pd
from Murray.main import SyntheticControl
from Murray.auxiliary import cleaned_data, market_correlations

@pytest.fixture(scope="module")
def synthetic_data():
    """Fixture that creates synthetic test data"""
    np.random.seed(42)
    
    dates = pd.date_range(start='2023-01-01', periods=100)
    regions = ['Control_1', 'Control_2', 'Control_3', 'Treatment']
    
    data = []
    for region in regions:
        base_value = np.random.randint(50, 100)
        trend = np.linspace(0, 10, len(dates))
        
        for i, date in enumerate(dates):
            value = (base_value + 
                    trend[i] + 
                    np.sin(date.day/15) * 10 + 
                    np.random.normal(0, 2))
            
            if region == 'Treatment' and i > 70:
                value += 20
                
            data.append({
                'date': date,
                'region': region,
                'add_to_carts': max(0, int(value))
            })
    
    df = pd.DataFrame(data)
    return cleaned_data(df, "add_to_carts", "region", "date")

@pytest.fixture(scope="module")
def correlation_matrix(synthetic_data):
    """Fixture that generates correlation matrix from synthetic data"""
    return market_correlations(synthetic_data)

@pytest.fixture(scope="module")
def synthetic_control(synthetic_data):
    """Fixture that creates a synthetic control instance"""
    treatment_group = ['Treatment']
    control_group = ['Control_1', 'Control_2', 'Control_3']
    
    sc = SyntheticControl(
        data=synthetic_data,
        treatment_group=treatment_group,
        control_group=control_group,
        date_column='date'
    )
    return sc

def test_synthetic_control_fit(synthetic_control):
    """Test that synthetic control can fit the data"""
    synthetic_control.fit()
    assert hasattr(synthetic_control, 'weights_')
    assert isinstance(synthetic_control.weights_, dict)
    assert len(synthetic_control.weights_) > 0
    
def test_synthetic_control_predict(synthetic_control):
    """Test that synthetic control can make predictions"""
    synthetic_control.fit()
    predictions = synthetic_control.predict()
    
    assert isinstance(predictions, pd.Series)
    assert len(predictions) > 0
    assert not predictions.isna().any()
