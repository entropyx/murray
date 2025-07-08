# Explicación Detallada del Análisis de Potencia en Murray

Este documento detalla la implementación del análisis de potencia estadística utilizado en el archivo `Murray/main.py`.

## Conceptos Fundamentales

El análisis de potencia en este código se basa en una **simulación de Monte Carlo utilizando pruebas de permutación**. A continuación se desglosan los conceptos clave:

*   **Método de Control Sintético:** El análisis utiliza un grupo de control sintético para estimar lo que le habría sucedido al grupo de tratamiento si no hubiera recibido el tratamiento. Esta es una técnica común en la inferencia causal para estudios observacionales. El control sintético se construye como una combinación ponderada de unidades de control (por ejemplo, ubicaciones geográficas) que se asemejan al grupo de tratamiento antes de la intervención.

*   **Pruebas de Permutación:** En lugar de depender de supuestos sobre la distribución de los datos (como en una prueba t), el análisis utiliza pruebas de permutación para generar una distribución nula. Esto implica barajar los datos (permutarlos) para romper cualquier efecto real y luego calcular un estadístico de prueba. Al repetir este proceso muchas veces, podemos ver el rango de estadísticos de prueba que esperaríamos observar si no hubiera un efecto real. Esto proporciona una forma robusta y no paramétrica de calcular los p-values.

*   **Simulación de Monte Carlo:** Para calcular la potencia estadística, el código simula el experimento completo muchas veces. En cada simulación, introduce un tamaño de efecto conocido (un "lift" o incremento) y luego ejecuta una prueba de permutación para ver si puede detectar ese efecto. La **potencia** es el porcentaje de simulaciones en las que el efecto se detectó con éxito (es decir, el p-value fue inferior al nivel de significancia).

## Funciones Clave

A continuación, se presenta un vistazo a las funciones más importantes involucradas في el análisis de potencia:

1.  **`apply_lift`**: Esta función simula el efecto del tratamiento aplicando un "lift" (un aumento porcentual) a los datos del grupo de tratamiento durante el período de tratamiento.

2.  **`calculate_conformity`**: Esta función calcula la diferencia entre los resultados reales y los predichos (por el control sintético) para el grupo de tratamiento. Esta es una métrica clave utilizada en el análisis.

3.  **`simulate_power`**: Este es el núcleo del análisis de potencia. Toma los datos reales y de control sintético, un tamaño de efecto dado (`delta`) y otros parámetros, y luego realiza lo siguiente:
    *   **Simula la "hipótesis alternativa"**: Aplica el `delta` a los datos reales para crear un escenario donde *sí* hay un efecto.
    *   **Calcula el "estadístico observado"**: Calcula un estadístico de prueba (como la diferencia de medias, el estadístico t o la diferencia de medianas) sobre los datos con el efecto simulado.
    *   **Ejecuta una prueba de permutación**: Baraja los datos muchas veces (controlado por `n_permutations`) y recalcula el estadístico de prueba para cada permutación. Esto crea una "distribución nula" del estadístico.
    *   **Calcula el p-value**: Compara el "estadístico observado" con la distribución nula para obtener un p-value.
    *   **Calcula la Potencia**: Repite este proceso múltiples veces (`n_power_simulations`) y calcula la proporción de veces que el p-value está por debajo del `significance_level`. Esta proporción es la potencia estadística.

4.  **`run_simulation`**: Es una función contenedora que llama a `simulate_power` para una única ejecución de simulación.

5.  **`evaluate_sensitivity`**: Esta función ejecuta el análisis de potencia para un rango de diferentes tamaños de efecto (`deltas`) y períodos de tratamiento (`periods`). Esto permite ver cómo cambia la potencia en diferentes condiciones.

6.  **`BetterGroups`**: Esta función es responsable de seleccionar los mejores grupos de tratamiento y control a partir de los datos. Utiliza una matriz de similitud (correlación) para encontrar grupos de ubicaciones que están altamente correlacionadas.

## ¿Cómo Funciona Todo en Conjunto?

1.  **Selección de Grupos**: La función `BetterGroups` primero identifica las mejores combinaciones de grupos de tratamiento y control a partir de los datos proporcionados.
2.  **Análisis de Sensibilidad**: La función `evaluate_sensitivity` toma estos grupos y ejecuta el análisis de potencia para cada uno, probando un rango de diferentes `deltas` y `periods`.
3.  **Simulación de Monte Carlo**: Para cada combinación de grupo, delta y período, la función `simulate_power` ejecuta una simulación de Monte Carlo para calcular la potencia estadística.
4.  **Resultados**: El resultado final es un diccionario que contiene los resultados del análisis de potencia para cada tamaño de grupo, delta y período.

## Diferentes Estadísticos de Prueba

La función `simulate_power` permite utilizar diferentes estadísticos de prueba en la prueba de permutación. Esto se controla mediante el parámetro `inference_type`:

*   **`mean_diff`**: Utiliza la diferencia de medias entre los residuos del grupo de tratamiento y de control como estadístico de prueba.
*   **`t_test`**: Utiliza un estadístico t como estadístico de prueba.
*   **`median_diff`**: Utiliza la diferencia de medianas como estadístico de prueba.
*   **`sum` (predeterminado)**: Utiliza la suma de las diferencias (residuos) como estadístico de prueba.

También puedes proporcionar tu propia función de estadístico de prueba personalizada utilizando el parámetro `stat_func`.
