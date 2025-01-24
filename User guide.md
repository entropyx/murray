# User Guide 

This guide constains an overview of Package Murray, as well as instructions for your used.

### Getting Started 
---

Murray is an Python package, it is necessary to have Python version 11.0 (or higher) installed. To install the package, you need to run this:

```
pip install murray
```
### Fuctions 
---

#### Data

First, you need to read data with Pandas:

```
data = pd.read(data.csv)
```

After, you ca use the fuctions ```cleaned_data ``` where you add the data, name of target column, name of location and date columns. For example:

```
data = cleaned_data(data,col_target='sessions',col_locations='location',col_dates='date')
```

The fuctions will clean and plot tha data.
![Data plot](utils\data_plot.png)



#### Sensitiviy Analysis

Finally, you just to need running the ```run_geo_analysis``` fuction which is the main fuction for get the results.

The parameters needed to run this function are:

* ```data```: A data frame containing historical conversions by locations. This parameters must cotain a ```location``` column, ```time``` column and ```Y``` column. This columns get after to run ```cleaned_fuction``` or add the data manually with these feactures. 

* ```excluded_states```: A list of states to exclude from treatment groups. These states will no be include in the treatment groups, but these can be include in the control groups. 

* ```significance_level```: A number which is a significance level, that is mean, with ```significance_level=0.1``` you have a 90% confidence level in your results.

* ```deltas_range```: This parameter contains a range of different lifts. You can agg the minimum lift, maximum lift and the steps. For example, if ```deltas_range = (0.01, 0.3, 0.02)``` so the lifts will from 1% until 30% with 2% increments.

* ```periods_range```: A list constain a range of differents periods. This one is very parameter before. You can agg the minimum period, maximum period and the steps. For example, if ```periods_range = (5, 40, 5)``` so the lifts will from 5 days until 40 days with 5 days of increments.

<br>

Example:
```
geo_test = run_geo_analysis(
    data = data,
    excluded_states = {'mexico city', 'méxico'},
    significance_level = 0.1,
    deltas_range = (0.01, 0.3, 0.02),
    periods_range = (5, 45, 5)
)
```


![Data plot](utils\mde_heatmap.png)

The results of the test provide us a visualization about the sensitivity in all periods admitted and differents holdouts. The holdouts depend of the data and locations, by default the number of treatment locations is 20% until 50% of total of locations. For example, if you have 32 locations, the range of size of treatment groups is 6-16 locations. 

#### Impact graphs

You can get a graph about lift, point difference and cumulative effect with the ```plot_impact()``` function. The parameters for run are:

* ```geo_test```: Results of the main function (```run_geo_analysis```).

* ```holdout_percentage```: The number of holdout percentage, this number you can see in the heatmap of the ```run_geo_analysis``` function.

* ```top_n```: Number of cases with the higher MDE values to plot. 

For example:
```
plot_impact(geo_test,periodo_especifico=10,top_n=1)
```

![Data plot](utils\impact_graph.png)


#### Treatment and control groups

For can get the treatment and control groups, you must run ```print_locations()``` function, this one print the treatment and control group you choose. The parameters needed to run are:

* ```geo_test```: Results of the main function (```run_geo_analysis```).

* ```holdout_percentage```: The number of holdout percentage, this number you can see in the heatmap of the ```run_geo_analysis``` function.

For example:

```
print_locations(geo_test,holdout_percentage=85.75)
```



#### Weights

Murry can print the weights of the control locations that built the counterfactual, you just must run ```print_weighs()```. The parameters is the same that ```print_locations()``` function. For example:


```
print_weights(geo_test,holdout_percentage=85.75)
```


