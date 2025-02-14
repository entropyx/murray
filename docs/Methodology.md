---
sidebar_position: 4
---

# Methodology


## Geographic experiments
As time progresses, advertising evolves, and consumer privacy increases. This is where the importance of geographic experiments arises, as they use measurement techniques based on models and data aggregation to help determine the true lift.

Currently, there are many algoritmos de pruebas pruebas geograficas in the market, such as Geolift and GeoX. However, Murray stands out as an efficient and accurate model. Additionally, Murray can generate all possible results based on the available data.

## Counterfactual

Murray arises from the need to achieve solid results with a model that is easy for users to manipulate. Murray's methodology is based on constructing a highly representative counterfactual for the treatment group to obtain reliable results. The selection of treatment and control groups is carried out based on their similarity, followed by the use of advanced synthetic control methods. It is worth noting that this method has gained traction compared to others, such as Difference-in-Differences. However, this method can produce biased results if a representative counterfactual is not constructed. For this reason, a robust synthetic control method for the counterfactual will be implemented in this case. The following constraints were used:

![Locale Dropdown](/img/0_ecuacion.png)




This ensures that the weights sum to 1 and remain positive for all states that make up the counterfactual, improving the interpretability of the locations that constitute the control group and avoiding problematic extrapolations.  

Additionally, the synthetic control model in Murray includes minimizing prediction error (squared error) combined with Ridge regression. This approach improves the estimation of intervention effects by penalizing the magnitude of the coefficients. This regularization prevents overfitting, enhances robustness in control selection, and stabilizes the estimation process, leading to more reliable and interpretable results, especially in cases where the assumptions of the standard synthetic control model are relaxed.Mathematically, this function can be expressed as follows:


![Locale Dropdown](/img/1_ecuacion.png)



The synthetic control approach in Murray was based on the augmented synthetic control method, as convex optimization tools with constraints are employed.

## Statistical Test
On the other hand, a non-parametric test is used for statistical evaluation. This test is widely applicable, not only in marketing but also in other fields, such as healthcare. The permutation test does not assume any specific distribution of the data, thereby avoiding errors in the results when determining the sensitivity of the experiment.


![Locale Dropdown](/img/2_ecuacion.png)



With a solid foundation in constructing a representative counterfactual for the treatment group and using non-parametric tests for statistical evaluations, biases in the results are effectively avoided.


## Usability and Ergonomics

To facilitate the use of the package for users, Murray internally integrates some default parameters to achieve optimal results. This approach avoids unnecessary simulations, leaving more intuitive parameters for the user, such as the range of increments and periods. By significantly reducing the number of input parameters, Murray stands out compared to existing models in geographical experiments like Geolift or GeoX.

Providing a broad range of results across different configurations, Murray emerges as an important option for geographical testing, which, as previously mentioned, has been gaining significant traction in the market.

It is worth noting that no extensive knowledge of the required parameters is necessary to run Murray; all parameters are highly intuitive and simplified. These improvements prevent the time-consuming need to fully understand all parameters to achieve the best configuration for the tests. Additionally, such tests can sometimes incur high computational costs, increasing execution times.

The package focuses on delivering critical metrics, such as the Minimum Detectable Effect (MDE), leveraging advanced synthetic control methods to generate robust counterfactuals, ensuring reliable and solid results.


## Conclusions

Although Murray is a new product in the market, it introduces key features for geographical experiments. One of its most important objectives is to build a highly representative counterfactual, enabling an accurate evaluation of a treatment’s impact. It is a user-friendly package, suitable for any user, and provides a highly viable solution for identifying the best combinations of locations and periods to apply treatments.  

The results are presented in a simple manner, eliminating the need to manually configure experiment parameters. This allows users to gain a comprehensive view of different scenarios when applying a treatment, with the confidence that results are generated through robust synthetic control methods, ensuring a representative counterfactual for the treated group.