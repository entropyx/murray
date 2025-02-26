



<p align="center">
  <img src="https://raw.githubusercontent.com/entropyx/murray/main/utils/Logo%20Entropy%20Dark%20Gray.png" width="550" height="auto">
</p>


# Murray

Murray is a Python package for geographic incrementality testing that helps determine the true lift of marketing campaigns through advanced synthetic control methods. It generates heatmaps of Minimum Detectable Effects (MDE) across different configurations to optimize treatment selection, and provides impact analysis through counterfactual modeling.

# Installation

You can install Murray using pip:

```bash
pip install murray-geo
```

Also, you can download the package directly from the GitHub repository:

```bash
pip install pip install git+https://github.com/entropyx/murray.git
```


# Prepare your data
```python
data = pd.DataFrame({
'time': [...], # timestamps
'location': [...], # location identifiers
'Y': [...] # target metric values
})
```

# Run analysis
```python
results = run_geo_analysis(
    data = data,
    excluded_locations = ['mexico city', 'méxico'],
    maximum_treatment_percentage=0.30,
    significance_level = 0.1,
    deltas_range = (0.01, 0.3, 0.02),
    periods_range = (5, 45, 5)
)
```
# Run evaluation
```python
results = run_geo_evaluation(
    data_input=data,
    start_treatment='01-12-2024',
    end_treatment='31-12-2024',
    treatment_group=['durango','puebla','queretaro'], 
    spend=10000)
```


# Documentation
You can check the documentation [here](https://entropy.tech/murray/docs/Welcome%20to%20Murray)
