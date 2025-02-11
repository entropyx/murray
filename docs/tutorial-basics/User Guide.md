---
sidebar_position: 2
---

#  Walkthrough
---
This guide constains an overview of Package Murray, as well as instructions for your used.

## Experimental Design 

### 1. Upload data

First, you need to read data with Pandas:

```python
data = pd.read_csv("data.csv")
```

#### Cleaned data
After, if is neccesary, you can use the fuctions ```cleaned_data ``` where you add the data, name of target column, name of location and date columns. For example:

```python
data = cleaned_data(data,col_target='sessions',col_locations='location',col_dates='date')
```
:::note

If you data have NaN values or the data is incomplete, this function is necessary to clean the data and not get errors.

:::

The function will clean the data of irregularities. After, you can ue the ```plot_geodata``` function to see the data.

```python
plot_geodata(data)
```


### 2. Experimental desing

Now, you must configure the experimental design. In the ```run_geo_analysis``` fuction must add the following parameters:

The parameters needed to run this function are:

* ```data```: A data frame containing historical conversions by locations. This parameters must cotain a ```location``` column, ```time``` column and ```Y``` column. That columns get after to run ```cleaned_fuction``` or add the data manually with these feactures or the data must have this columns.

* ```excluded_states```: A list of states to exclude from treatment groups. These states will no be include in the treatment groups, but these can be include in the control groups. 

* ```significance_level```: A number which is a significance level, that is mean, with ```significance_level=0.1``` you have a 90% confidence level in your results.

* ```deltas_range```: This parameter contains a range of different lifts. You can agg the minimum lift, maximum lift and the steps. For example, if ```deltas_range = (0.01, 0.3, 0.02)``` so the lifts will from 1% until 30% with 2% increments.

* ```periods_range```: A list constain a range of differents periods. This one is very parameter before. You can agg the minimum period, maximum period and the steps. For example, if ```periods_range = (5, 40, 5)``` so the lifts will from 5 days until 40 days with 5 days of increments.




```python
geo_test = run_geo_analysis(
    data = data,
    excluded_states = ['mexico city', 'méxico'],
    significance_level = 0.1,
    deltas_range = (0.01, 0.3, 0.02),
    periods_range = (5, 45, 5)
)

```


The results of the test provide us a visualization about the sensitivity in all periods admitted and differents holdouts. The holdouts depend of the data and locations, by default the number of treatment locations is 20% until 50% of total of locations. For example, if you have 32 locations, the range of size of treatment groups is 6-16 locations.
Whe the simulation finish, you can see the heatmap of the results like this:



### 3. Results

Once the heatmap is displayed you can choose the best configuration for you, after that you can use the following functions to display the experiment results, such as the treatment and control locations, as well as metrics like MAE (Mean Absolute Error) and MAPE (Mean Absolute Percentage Error).



#### Treatment and control groups

For can get the treatment and control groups, you must run ```print_locations()``` function, this one print the treatment and control group you choose. The parameters needed to run are:

* ```geo_test```: Results of the main function (```run_geo_analysis```).

* ```holdout_percentage```: The number of holdout percentage, this number you can see in the heatmap of the ```run_geo_analysis``` function.



```python
print_locations(geo_test,holdout_percentage=85.75)
```

#### Impact graphs

You can get a graph about lift, point difference and cumulative effect with the ```plot_impact_graphs()``` function. The parameters for run are:

* ```geo_test```: Results of the main function (```run_geo_analysis```).

* ```period```: The period you want to see the impact graph.

* ```holdout_percentage```: The number of holdout percentage, this number you can see in the heatmap of the ```run_geo_analysis``` function.


```python
plot_impact(geo_test,period=10,holdout_percentage=85.75)
```




#### Weights

Murry can print the weights of the control locations that built the counterfactual, you just must run ```print_weighs()```. The parameters is the same that ```print_locations()``` function. For example:


```python
print_weights(geo_test,holdout_percentage=85.75)
```

### Incremental results

You can get the incremental results with the ```plint_incremental_results()``` function. The parameter is:

* ```geo_test```: Results of the main function (```run_geo_analysis```).


```python
print_incremental_results(geo_test)
```

### Metrics

You can get the metrics of the experiment with the ```plot_metrics()``` function. The parameter is:

* ```geo_test```: Results of the main function (```run_geo_analysis```).


```python
plot_metrics(geo_test)
```





## Experimental Evaluation

### 1. Data
To evaluate an implemented experiment you can use Murray. This analysis is simpler than the design, but it is very similar in terms of functions and workflow. The first thing is to load read your data.

```python
data = pd.read_csv("data_marketing_campaign.csv")
```
You can also use the same function to display the graph of the entered data.

```python
plot_geodata(data)
```

### 2. Experimental evaluation
This part is very similar to the experimental design, but in this case you must add the parameter to ```post_analysis``` function. The parameters needed to run are:

* ```data```: A data frame containing historical conversions by locations. This parameters must cotain a ```location``` column, ```time``` column and ```Y``` column. That columns get after to run ```cleaned_fuction``` or add the data manually with these feactures or the data must have this columns.

* ```start_treatment```: The start date of the treatment.

* ```end_treatment```: The end date of the treatment.

* ```treatment_group```: The locations that are in the treatment group.



```python
results = post_analysis(data,start_treatment='2020-01-01',end_treatment='2020-01-31',treatment_group=['durango','puebla','queretaro'])
```

### 3. Results

Once the post analysis is finished you can get the results with the following functions:


#### Impact graph

You can get the impact graph with the ```plot_impact_graphs_evaluation()``` function. The parameters are:

* ```results```: The results of the post analysis.

```python
plot_impact_graphs_evaluation(results)
```


#### Incremental results

You can get the incremental results with the ```print_incremental_results_evaluation()``` function. The parameters are:

* ```results```: The results of the post analysis.

```python
print_incremental_results_evaluation(results)
```


#### Permutation test

You can get the permutation test with the ```plot_permutation_test()``` function. The parameters are:

* ```results```: The results of the post analysis.

```python
plot_permutation_test(results)
``` 



























