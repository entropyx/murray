# Murray

Murray is a Python package for geographic incrementality testing that helps determine the true lift of marketing campaigns through advanced synthetic control methods. It generates heatmaps of Minimum Detectable Effects (MDE) across different configurations to optimize treatment selection, and provides impact analysis through counterfactual modeling.

## Installation

You can install Murray using pip:

```bash
pip install git+https://github.com/entropyx/murray.git
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
data=data,
excluyed_states=[],
minimum_holdout_percentage=70,
nivel_significancia=0.05,
deltas_range=(0.01, 0.20, 0.01),
periodos_range=(4, 13, 1)
)
```
