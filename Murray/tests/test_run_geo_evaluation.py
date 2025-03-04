import pytest
import numpy as np
import pandas as pd
from Murray.post_analysis import run_geo_evaluation
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


def test_run_geo_evaluation(sample_data):
    """Verifica que la función de evaluación geográfica se ejecute correctamente"""
    results = run_geo_evaluation(
        data_input=sample_data,
        start_treatment="2023-03-01",
        end_treatment="2023-03-10",
        treatment_group=["Location_0", "Location_1"],
        spend=50000,
        n_permutations=100,  
        inference_type="iid",
        significance_level=0.05
    )

    assert isinstance(results, dict), "El resultado debe ser un diccionario"
    expected_keys = [
        "MAPE", "SMAPE", "predictions", "treatment", "p_value", "power",
        "percenge_lift", "control_group", "observed_conformity",
        "null_conformities", "weights", "period", "spend"
    ]
    for key in expected_keys:
        assert key in results, f"Falta la clave '{key}' en los resultados"

    assert isinstance(results["MAPE"], float), "MAPE debe ser un float"
    assert isinstance(results["p_value"], float), "p_value debe ser un float"
    assert isinstance(results["power"], float), "Power debe ser un float"
    assert isinstance(results["control_group"], list), "Control group debe ser una lista"
    assert 0 <= results["power"] <= 1, "Power debe estar entre 0 y 1"
    assert 0 <= results["p_value"] <= 1, "p_value debe estar entre 0 y 1"
