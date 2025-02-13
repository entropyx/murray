# Murray

Murray is a Python package for geographic incrementality testing that helps determine the true lift of marketing campaigns through advanced synthetic control methods. It generates heatmaps of Minimum Detectable Effects (MDE) across different configurations to optimize treatment selection, and provides impact analysis through counterfactual modeling.

## Installation

You can install Murray using pip:

```bash
<<<<<<< HEAD
pip install git+https://github.com/entropyx/murray.git
=======
>>>>>>> post-analysis
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
    excluded_locations = [],
    maximum_treatment_percentage=30,
    significance_level = 0.1,
    deltas_range = (0.01, 0.3, 0.02),
    periods_range = (5, 45, 5)
)

```


# Documentation
[Entropy Murray Documentation](https://entropy.tech/murray/docs/Murray)