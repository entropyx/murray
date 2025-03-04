import pytest
import numpy as np
import pandas as pd
from Murray.main import run_geo_analysis_streamlit_app
from Murray.auxiliary import market_correlations, cleaned_data

@pytest.fixture
def sample_data():
    """Fixture que genera un DataFrame de prueba con datos ficticios"""
    np.random.seed(42)
    data = pd.DataFrame({
        "time": np.tile(pd.date_range("2023-01-01", periods=100, freq="D"), 10),
        "location": np.repeat([f"Location_{i}" for i in range(10)], 100),
        "Y": np.random.rand(1000) * 100
    })
    return data


def test_run_geo_analysis(sample_data):
    """Verifica que la función de análisis se ejecute correctamente"""
    results = run_geo_analysis_streamlit_app(
        data=sample_data,
        maximum_treatment_percentage=0.50,
        significance_level=0.05,
        deltas_range=(0.05, 0.2, 0.05),
        periods_range=(10, 30, 10),
        excluded_locations=["Location_1"],
        n_permutations=100  
    )

    assert isinstance(results, dict), "El resultado debe ser un diccionario"
    assert "simulation_results" in results, "Falta 'simulation_results' en los resultados"
    assert "sensitivity_results" in results, "Falta 'sensitivity_results' en los resultados"
    assert "series_lifts" in results, "Falta 'series_lifts' en los resultados"

    assert isinstance(results["simulation_results"], dict), "simulation_results debe ser un diccionario"
    assert isinstance(results["sensitivity_results"], dict), "sensitivity_results debe ser un diccionario"
    assert isinstance(results["series_lifts"], dict), "series_lifts debe ser un diccionario"
