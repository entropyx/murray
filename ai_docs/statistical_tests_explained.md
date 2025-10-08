# Guía de Pruebas Estadísticas en Murray

Este documento explica las diferentes pruebas estadísticas (estadísticos de prueba) que se pueden utilizar en el framework de Murray, específicamente dentro de la función `simulate_power` en `Murray/main.py`. La elección de la prueba se controla mediante el parámetro `inference_type`.

## Contexto: Pruebas de Permutación

El motor de inferencia de Murray utiliza **pruebas de permutación** para determinar si el impacto observado de una campaña es estadísticamente significativo o si podría deberse al azar.

El proceso funciona así:
1.  Se calcula la diferencia entre los resultados reales del grupo de tratamiento y los resultados del control sintético (el contrafactual).
2.  Se calcula un **estadístico de prueba** sobre esa serie de diferencias (por ejemplo, la media, la suma, etc.). Este es el valor observado.
3.  Se barajan aleatoriamente los datos muchas veces (permutaciones) y se vuelve a calcular el mismo estadístico de prueba en cada permutación. Esto crea una "distribución nula", que muestra cómo se vería el estadístico si no hubiera un efecto real.
4.  Se compara el valor observado con la distribución nula para obtener un p-value.

El parámetro `inference_type` te permite elegir qué estadístico de prueba se utilizará en este proceso.

---

## Opciones para `inference_type`

### 1. `inference_type="sum"` (Suma de Diferencias) - Opción por Defecto

-   **¿Qué mide?:** El impacto **total y acumulado** durante todo el período de tratamiento.
-   **Estadístico de prueba:** `np.sum(diferencias)`
-   **Cuándo usarlo:**
    -   Cuando la pregunta de negocio principal es sobre el retorno total. Por ejemplo: "¿Cuántos ingresos adicionales totales generó la campaña?".
    -   Es útil si esperas que el impacto sea volátil (algunos días buenos, otros malos) y te importa el resultado final agregado.
    -   Es el método por defecto y una elección sólida para medir el valor de negocio global.

### 2. `inference_type="mean_diff"` (Diferencia de Medias)

-   **¿Qué mide?:** El impacto **promedio diario** durante el período de tratamiento.
-   **Estadístico de prueba:** `np.mean(diferencias)`
-   **Cuándo usarlo:**
    -   Cuando quieres una métrica fácil de interpretar y comunicar. Por ejemplo: "La campaña generó un promedio de 50 conversiones adicionales por día".
    -   Es ideal para campañas con un efecto esperado constante a lo largo del tiempo.
    -   **Precaución:** Puede ser sensible a valores atípicos (outliers). Un día con un rendimiento extremadamente bueno o malo puede sesgar el promedio.

### 3. `inference_type="t_test"` (Prueba T)

-   **¿Qué mide?:** La diferencia de medias ajustada por la variabilidad de los datos. No solo mira el tamaño del efecto, sino también su **consistencia**.
-   **Estadístico de prueba:** `media / (desviación_estándar / sqrt(N))`
-   **Cuándo usarlo:**
    -   Cuando buscas un análisis estadísticamente más riguroso.
    -   Es la mejor opción para confirmar que un efecto no solo es grande, sino también estable y no solo producto de fluctuaciones aleatorias.
    -   Úsalo si quieres estar muy seguro de la fiabilidad del efecto observado.

### 4. `inference_type="median_diff"` (Diferencia de Medianas)

-   **¿Qué mide?:** El impacto del "día típico". La mediana es el valor que se encuentra justo en el medio de todas las diferencias diarias.
-   **Estadístico de prueba:** `np.median(diferencias)`
-   **Cuándo usarlo:**
    -   Es la mejor opción cuando tus datos tienen **valores atípicos extremos** (por ejemplo, un pico de ventas por el Black Friday que no es representativo del rendimiento normal).
    -   La mediana no se ve afectada por estos valores extremos, dándote una medida más robusta del impacto central de la campaña.
    -   Úsalo para responder: "¿Cuál fue el impacto en un día normal, sin contar los picos?".

---

## Tabla Resumen

| `inference_type` | Pregunta que Responde                               | Fortalezas                                    | Debilidades                               |
| ---------------- | --------------------------------------------------- | --------------------------------------------- | ----------------------------------------- |
| **`sum`**        | ¿Cuál fue el impacto **total acumulado**?           | Mide el valor de negocio global.              | No informa sobre la consistencia del efecto. |
| **`mean_diff`**  | ¿Cuál fue el impacto **promedio diario**?           | Fácil de interpretar y comunicar.             | Sensible a valores atípicos.              |
| **`t_test`**     | ¿El impacto fue **consistente y fiable**?           | Robusto estadísticamente, considera la variabilidad. | Menos directo de interpretar que la media. |
| **`median_diff`**| ¿Cuál fue el impacto en un **día típico**?          | Robusto frente a valores atípicos extremos.   | Ignora la magnitud de los picos.          |
