# Murray 


## Geographic experiments
As time progresses, advertising evolves, and consumer privacy increases. This is where the importance of geographic experiments arises, as they use measurement techniques based on models and data aggregation to help determine the true lift. 

Currently, there are many algoritmos de pruebas pruebas geograficas in the market, such as Geolift and GeoX. However, Murray stands out as an efficient and accurate model. Additionally, Murray can generate all possible results based on the available data.

## Counterfactual

Murray arises from the need to achieve solid results with a model that is easy for users to manipulate. Murray's methodology is based on constructing a highly representative counterfactual for the treatment group to obtain reliable results. The selection of treatment and control groups is carried out based on their similarity, followed by the use of advanced synthetic control methods. It is worth noting that this method has gained traction compared to others, such as Difference-in-Differences. However, this method can produce biased results if a representative counterfactual is not constructed. For this reason, a robust synthetic control method for the counterfactual will be implemented in this case. The following constraints were used: 

![Weights constraints](https://latex.codecogs.com/svg.image?\arg\min_{w}\left\|y-Xw\right\|\text{and}\sum&space;w_{j}=1,\quad&space;w_{j}>0\;\forall&space;j&space;)


Lo cual basicamente hace que los pesos sumen 1 y sean positivos, logrando una Sure! Here's the translated version in English:

---

This essentially ensures that the weights sum up to 1 and are positive, improving the interpretability of the locations that make up the control group and avoiding dangerous extrapolations.

Additionally, the synthetic control model in Murray includes the minimization of prediction error (quadratic error) combined with Elastic Net regularization (Ridge + Lasso). This allows for addressing multicollinearity issues and selecting only a subset of relevant locations. Mathematically, this function can be expressed as follows:


![Elastic net](https://latex.codecogs.com/svg.image?L(\boldsymbol{\beta})=\frac{1}{2n}\sum_{i=1}^n\left(y_i-\mathbf{x}_i^\top\boldsymbol{\beta}\right)^2&plus;\lambda_1\|\boldsymbol{\beta}\|_1&plus;\frac{\lambda_2}{2}\|\boldsymbol{\beta}\|_2^2&space;)

The synthetic control approach in Murray was based on the augmented synthetic control method, as convex optimization tools with constraints are employed.

## Statistical Test
On the other hand, a non-parametric test is used for statistical evaluation. This test is widely applicable, not only in marketing but also in other fields, such as healthcare. The permutation test does not assume any specific distribution of the data, thereby avoiding errors in the results when determining the sensitivity of the experiment. 

![Permutations](https://latex.codecogs.com/svg.image?\text{P-value}=\frac{1}{|\Pi|}\sum_{\pi\in\Pi}\mathbb{}\{S(\hat{u}_{\pi_0})\leq&space;S(\hat{u}_{\pi})\})

With a solid foundation in constructing a representative counterfactual for the treatment group and using non-parametric tests for statistical evaluations, biases in the results are effectively avoided.


## Usability and Ergonomics

To facilitate the use of the package for users, Murray internally integrates some default parameters to achieve optimal results. This approach avoids unnecessary simulations, leaving more intuitive parameters for the user, such as the range of increments and periods. By significantly reducing the number of input parameters, Murray stands out compared to existing models in geographical experiments like Geolift or GeoX.

Providing a broad range of results across different configurations, Murray emerges as an important option for geographical testing, which, as previously mentioned, has been gaining significant traction in the market.

It is worth noting that no extensive knowledge of the required parameters is necessary to run Murray; all parameters are highly intuitive and simplified. These improvements prevent the time-consuming need to fully understand all parameters to achieve the best configuration for the tests. Additionally, such tests can sometimes incur high computational costs, increasing execution times.

The package focuses on delivering critical metrics, such as the Minimum Detectable Effect (MDE), leveraging advanced synthetic control methods to generate robust counterfactuals, ensuring reliable and solid results.


### Comparison Table



| Features                              | Geolift  | GeoX        | Murray        |  
|:--------------------------------------|:--------:|:-----------:|:-------------:|
| Easy result interpretability          |    ✗     |     ✔       |       ✔       |
| Low knowledge requirement             |    ✗     |     ✔       |       ✔       |
| Low computational cost                |    ✗     |     ✔       |       ✔       |
| Functional flexibility                |    ✔     |     ✗       |       ✔       |
| Reliable with large samples           |    ✔     |     ✗       |       ✗       |
| Open source                           |    ✔     |     ✗       |       ✔       |




## Conclusions

Although Murray is a new product in the market, it introduces key features for geographical experiments. It is a user-friendly package, suitable for any user, and provides a highly viable solution for identifying the best combinations of locations and periods to apply treatments. The results are presented in a simple manner, eliminating the need to manually configure parameters for your experiments. This enables users to gain a comprehensive view of different scenarios when applying a treatment, with the confidence of obtaining results through robust synthetic control methods that generate a representative counterfactual for the treated group.
