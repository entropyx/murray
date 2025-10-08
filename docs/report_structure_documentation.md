# Estructura del Reporte PDF Murray

Este documento describe la estructura completa del reporte PDF generado por la función `generate_pdf` en el módulo de diseño experimental de Murray.

## Información General del Reporte

### Metadatos y Configuración
- **Formato**: PDF con fuentes Poppins (Bold y Regular)
- **Colores Corporativos**: 
  - Títulos: RGB(27, 0, 67) - Púrpura Entropy
  - Texto: RGB(33, 31, 36) - Gris oscuro
  - Headers: RGB(103, 85, 130) - Púrpura claro
- **Manejo de Páginas**: Salto automático con margen de 15px

---

## Estructura de Secciones

### 1. Encabezado del Reporte

**Elementos visuales:**
- Logo Entropy (esquina superior izquierda)
- Título centrado: "Geo Murray Report"
- Línea separadora

**Texto introductorio (dinámico):**
```
This report provides information about the experimental design on the variable '{target_variable}', 
the experimental design was conducted for a duration of {period} days. 
The data included in the design have a period of {first_day_data} to {last_day_data} where the treatment 
started on {treatment_day} until {last_day}. It includes information about the treatment group, 
control group, minimum detectable effect (MDE), and other relevant information.
```

### 2. Treatment Group

**Título:** "Treatment Group:"

**Texto estándar:**
```
The treatment group consists of individuals or units that received the experimental intervention or treatment. 
The following is the description of the treatment group: 
```

**Contenido dinámico:**
- Lista de locations del grupo de tratamiento (formato: texto en negrita)

### 3. Control Group

**Título:** "Control Group:"

**Texto estándar:**
```
The control group is used as a baseline for comparison. These are the individuals or units that did not 
receive the treatment but were otherwise similar. Here is each location of the control group: 
```

**Contenido dinámico:**
- Lista de locations del grupo control (formato: texto en negrita)

### 4. Minimum Detectable Effect (MDE)

**Título:** "Minimum Detectable Effect (MDE)"

**Texto dinámico:**
```
The experimental design is based on the minimum detectable effect (MDE) which is the smallest effect 
that can be detected with a given level of confidence. In this case, the MDE is {mde_percentage}% 
for the period of {period_idx} days.
```

### 5. Statistical Significance (P-Value) - SECCIÓN CONDICIONAL

**Condición:** Solo aparece si `p_value is not None` (o sea que si esa variable tiene un valor)

**Título:** "Statistical Significance (P-Value)"

**Texto variable según rango del p-value:**

#### p < 0.001 - Highly Significant
```
The obtained p-value is {p_value:.6f} (p < 0.001), indicating that the result is highly significant. 
This means there is less than a 0.1% chance that these results occurred by chance. 
We have extremely strong evidence that the treatment is having a real effect.
```

#### p < 0.01 - Very Significant
```
The obtained p-value is {p_value:.4f} (p < 0.01), indicating that the result is very significant. 
This means there is less than a 1% chance that these results occurred by chance. 
We have very solid evidence that the treatment is working as expected.
```

#### p < 0.05 - Significant
```
The obtained p-value is {p_value:.4f} (p < 0.05), indicating that the result is significant. 
This means there is less than a 5% chance that these results occurred by chance. 
We have good evidence that the treatment is having a positive effect.
```

#### p < 0.1 - Marginally Significant
```
The obtained p-value is {p_value:.4f} (p < 0.1), indicating that the result is marginally significant. 
This means there is less than a 10% chance that these results occurred by chance. 
While there is evidence of a treatment effect, the results should be interpreted with some caution.
```

#### p ≥ 0.1 - Not Significant
```
The obtained p-value is {p_value:.4f} (p ≥ 0.1), indicating that the result is not significant. 
This means there is more than a 10% chance that these results occurred by chance. 
We don't have sufficient evidence to conclude that the treatment is having a real effect.
```

### 6. Statistical Power - SECCIÓN CONDICIONAL

**Condición:** Solo aparece si `power_value is not None` (o sea que si esa variable tiene un valor)

**Título:** "Statistical Power"

**Texto variable según valor del power:**

#### Power ≥ 80% - High Power
```
The statistical power is {power_percentage:.0f}%, which is considered high. 
This means we have a high probability of detecting a true effect if one exists. 
High power (≥80%) reduces the risk of missing real treatment effects (false negatives).
```

#### 50% ≤ Power < 80% - Moderate Power
```
The statistical power is {power_percentage:.0f}%, which is considered moderate. 
This means we have a moderate probability of detecting a true effect if one exists. 
While acceptable, higher power would be preferable to reduce the risk of missing real effects.
```

#### Power < 50% - Low Power
```
The statistical power is {power_percentage:.0f}%, which is considered low. 
This means we have a low probability of detecting a true effect if one exists. 
Low power increases the risk of missing real treatment effects (false negatives).
```

### 7. Conversion Percentages

**Título:** "Conversion Percentages"

**Contenido:**
- `Treatment Percentage: {treatment_percentage:.2f}%` 
- `Holdout Percentage: {holdout_percentage:.2f}%`

(ambos con redondeados a dos decimales)

**Texto explicativo:**
```
The holdout percentage represents the portion of the total conversions that belong to the control group. 
The treatment percentage represents the portion of the total conversions that are allocated to the treatment group.
```

### 8. Control Locations and Weights

**Título:** "Control Locations and Weights:"

**Formato:** Tabla con alternancia de colores
- **Columnas:** "Location" | "Weight"
- **Header:** Fondo púrpura, texto blanco
- **Filas:** Alternancia entre gris claro y blanco
- **Weights:** Formato con 4 decimales

### 9. Impact

**Título:** "Impact"

**Texto introductorio:**
```
The results show the impact of the treatment on different treatment locations. 
Below is the ATT value and the lift value total of the target variable.
```

#### Tabla de Resultados

**Header dinámico:**
- Si existe p-value: `P-Value: {formatted_p_value}`
- Si no existe p-value: `Confidence Level {confidence_level * 100}%`

**Filas de datos:**
| Metric | Absolute Value | Percentage |
|--------|---------------|------------|
| **Median Prediction** | {prediction_absolute:,.2f} | {prediction_percentage:,.2f}% |
| Lower Bound | {lower_bound_absolute:,.2f} | {lower_bound_percentage:,.2f}% |
| Upper Bound | {upper_bound_absolute:,.2f} | {upper_bound_percentage:,.2f}% |

**Footer:** `MDE: {mde * 100}%`

### 10. Pre/Post Treatment Comparison

**Texto explicativo:**
```
It is important to be able to identify the impact of the intervention pre-intervention and 
post-intervention in real values. In this case, a small table is presented where the pre-intervention 
value (with the same duration as the treatment period) and the post-intervention value are observed. 
This allows for a quick and simple identification of the impact that an intervention would have in 
comparison to the locations where it is not applied (counterfactual).
```

#### Tabla Comparativa

**Headers:**
- "Group"
- "Pre-treatment ({first_report_day} to {second_report_day})"  
- "Post-treatment ({treatment_day} to {last_day})"

**Contenido:** Datos numéricos formateados con comas y 2 decimales

### 11. Impact Graph

**Texto introductorio:**
```
The graph below shows the aggregate effect, the point effect, and the cumulative effect.
```

**Contenido:** Gráfico insertado como imagen (190px de ancho)

---

## Especificaciones Técnicas

### Variables Dinámicas Requeridas

**Obligatorias:**
- `treatment_group`: Lista de locations de tratamiento
- `control_group`: Lista de locations de control  
- `holdout_percentage`: Porcentaje del grupo control
- `mde`: Efecto mínimo detectable (decimal)
- `tarjet_variable`: Variable objetivo del análisis
- `period_idx`: Duración del experimento en días
- `first_day`, `last_day`, `treatment_day`: Fechas del experimento
- `weights`: DataFrame con locations y weights del control
- `prediction_value_*`, `lower_bound_*`, `upper_bound_*`: Valores del impacto
- `confidence_level`: Nivel de confianza
- `impact_graph`: Objeto matplotlib para el gráfico

**Opcionales:**
- `p_value`: Valor p para significancia estadística
- `power_value`: Valor del poder estadístico

### Formato y Estilo

**Fuentes:**
- Títulos: Poppins Bold
- Texto: Poppins Regular
- Tamaños: 20px (título principal), 12px (subtítulos), 10px (texto)

**Colores:**
- Títulos: RGB(27, 0, 67)
- Texto: RGB(33, 31, 36)
- Headers tablas: RGB(103, 85, 130)
- Filas alternas: RGB(209, 204, 217) y RGB(246, 246, 246)

**Tablas:**
- Bordes: 1px
- Altura de fila: 8px
- Alineación: Centrada
- Alternancia de colores por fila

---

## Función para Gráfica y Cálculos del Reporte

### `plot_impact_report()` - La función clave del reporte


**Propósito:** Es la función PRINCIPAL del reporte. No solo genera la gráfica, sino que también calcula TODOS los valores necesarios para las tablas del reporte PDF.

### Parámetros de Entrada
```python
plot_impact_report(
    geo_test,                    # Diccionario completo de resultados de Murray
    period,                      # Período del tratamiento en días (ej: 30)  
    holdout_percentage,          # Porcentaje de holdout deseado (ej: 20.0)
    length_treatment,            # Número de locations en tratamiento
    significance_level=0.05      # Nivel de significancia (default: 0.05)
)
```

### Proceso Interno (Lo que hace la función)

1. **Selección de Configuración:**
   - Busca el `size_key` que coincida con el `holdout_percentage` especificado
   - Obtiene el MDE correspondiente al período deseado

2. **Extracción de Series:**
   - Obtiene las predicciones contrafactuales (`counterfactual`)
   - Encuentra la serie de tratamiento con lift más cercana al MDE objetivo
   - Calcula el punto donde inicia el tratamiento

3. **Cálculos de Efectos:**
   - **Point Difference:** Diferencia punto a punto entre tratamiento y contrafactual
   - **Cumulative Effect:** Efecto acumulativo a lo largo del tiempo
   - **ATT (Average Treatment Effect):** Promedio normalizado por cantidad de locations
   - **Incremental:** Suma total del efecto (lift total)

4. **Bandas de Confianza:**
   - Calcula intervalos de confianza para cada panel usando bootstrap
   - Usa función `calculate_optimal_noise_scale()` para determinar la variabilidad
   - Genera `lower_bound` y `upper_bound` para los 3 paneles

5. **Valores Pre/Post Treatment:**
   - **Pre-treatment:** Suma del período anterior al tratamiento (misma duración)
   - **Post-treatment:** Suma del período durante el tratamiento
   - Se calculan tanto para tratamiento como para contrafactual

6. **Generación de Gráfica:**
   - **Panel 1:** Series de tiempo completas (tratamiento vs contrafactual)
   - **Panel 2:** Diferencia puntual con línea de referencia en cero
   - **Panel 3:** Efecto acumulativo a lo largo del tiempo
   - Cada panel incluye bandas de confianza en gris
   - Línea vertical negra marca el inicio del tratamiento

### Valores que Retorna (TUPLE de 10 elementos)
```python
return (
    pre_treatment,           # Array: valores pre-treatment del grupo tratamiento  
    pre_counterfactual,      # Array: valores pre-treatment del grupo control
    post_treatment,          # Array: valores post-treatment del grupo tratamiento
    post_counterfactual,     # Array: valores post-treatment del grupo control
    fig,                     # Matplotlib figure: gráfica de 3 paneles
    att,                     # Float: Average Treatment Effect (redondeado 2 decimales)
    incremental,             # Float: Lift total (redondeado 2 decimales)  
    lower_bound_value,       # Float: Valor inferior del intervalo confianza (redondeado 2 decimales)
    upper_bound_value,       # Float: Valor superior del intervalo confianza (redondeado 2 decimales)
    prediction_value         # Float: Suma total del tratamiento en período post (redondeado 2 decimales)
)
```

### Uso en el Reporte PDF
Esta función es ESENCIAL porque proporciona:

**Para la gráfica:**
- `fig` → Se guarda como imagen temporal y se inserta en el PDF

**Para la tabla de Impact:**
- `prediction_value` → Median Prediction (absoluto)
- `lower_bound_value` → Lower Bound (absoluto)  
- `upper_bound_value` → Upper Bound (absoluto)
- `incremental` → Para calcular porcentajes de impacto

**Para la tabla Pre/Post Treatment:**
- `pre_treatment` → Suma para grupo "Treatment" columna "Pre-treatment"
- `pre_counterfactual` → Suma para grupo "Control" columna "Pre-treatment"  
- `post_treatment` → Suma para grupo "Treatment" columna "Post-treatment"
- `post_counterfactual` → Suma para grupo "Control" columna "Post-treatment"

**Para métricas adicionales:**
- `att` → Average Treatment Effect
- `incremental` → Lift total del experimento

### Dependencias Importantes
La función requiere las funciones auxiliares:
- `calculate_optimal_noise_scale()` - Para calcular variabilidad del ruido
- `calculate_confidence_bands()` - Para generar intervalos de confianza
- `millify()` - Para formatear números grandes en las gráficas

### Consideración Clave
Esta función centraliza TODOS los cálculos matemáticos del reporte. Si tu amigo la replica correctamente en otro lenguaje, tendrá todos los valores necesarios para generar el reporte completo.

---

## Obtención de Datos desde la API de Murray

Se necesita obtener los siguientes datos de la API de Murray:

### Estructura de Respuesta de la API Murray
Cuando llamas a la API de Murray, obtienes una estructura como esta:

```python
murray_response = {
    "simulation_results": {
        size_key: {
            "Best Treatment Group": list,      # Locations de tratamiento
            "Control Group": list,             # Locations de control  
            "Weights": list,                   # Weights del control group
            "Holdout Percentage": float,       # Porcentaje de holdout
            "MAPE": float,                     # Métricas de calidad
            "SMAPE": float,
            "p_value": float,                  # Puede ser null
            "power": float,                    # Puede ser null
            "Predictions": array,              # Predicciones contrafactuales
            "Actual Target Metric (y)": array # Valores reales
        }
    },
    "sensitivity_results": {
        size_key: {
            period: {"MDE": float}
        }
    },
    "series_lifts": {
        (size_key, delta, period): array    # Series de tratamiento con lift
    }
}
```

### Cómo Extraer Datos para Cada Sección del Reporte

#### **1. Seleccionar la Configuración Deseada**
```python
# Selecciona el size_key basado en holdout_percentage deseado
target_holdout = 20.0  # Ejemplo: 20% holdout
selected_size = None
for size_key, result in murray_response["simulation_results"].items():
    if abs(result["Holdout Percentage"] - target_holdout) < 0.01:
        selected_size = size_key
        break

selected_result = murray_response["simulation_results"][selected_size]
```

#### **2. Treatment y Control Groups**
```python
treatment_group = selected_result["Best Treatment Group"]
control_group = selected_result["Control Group"]

# Formatear como string para el PDF
treatment_group_str = ", ".join(treatment_group)
control_group_str = ", ".join(control_group)
```

#### **3. Weights para la Tabla**
```python
weights_data = []
for i, location in enumerate(control_group):
    weights_data.append({
        "Control Location": location,
        "Weights": selected_result["Weights"][i]
    })

# Ordenar por weights descendente
weights_df = pd.DataFrame(weights_data).sort_values("Weights", ascending=False)
```

#### **4. MDE**
```python
# Seleccionar período deseado (ej: 30 días)
target_period = 30
mde = murray_response["sensitivity_results"][selected_size][target_period]["MDE"]
mde_percentage = f"{mde * 100:.0f}%"
```

#### **5. P-value y Statistical Power**
```python
p_value = selected_result.get("p_value")  # Puede ser None
power_value = selected_result.get("power")  # Puede ser None

# Usar lógica condicional como en el código original
if p_value is not None:
    # Mostrar sección de significancia estadística
    pass
if power_value is not None:
    # Mostrar sección de poder estadístico
    pass
```

#### **6. Conversion Percentages**
```python
holdout_percentage = selected_result["Holdout Percentage"]
treatment_percentage = 100 - holdout_percentage
```

#### **7. Valores de Impacto**
```python
# Obtener series de datos
counterfactual = selected_result["Predictions"].flatten()
target_mde = murray_response["sensitivity_results"][selected_size][target_period]["MDE"]

# Encontrar la serie de lift más cercana al MDE
closest_delta = min(available_deltas, key=lambda x: abs(x - target_mde))
treatment = murray_response["series_lifts"][(selected_size, closest_delta, target_period)]

# Calcular valores
start_treatment = len(treatment) - target_period
att = np.mean(treatment[start_treatment:] - counterfactual[start_treatment:])
incremental = np.sum(treatment[start_treatment:] - counterfactual[start_treatment:])

# Calcular bounds de confianza (usando función calculate_confidence_bands)
lower_bound_value, upper_bound_value = calculate_confidence_bands(...)
prediction_value = np.sum(treatment[start_treatment:])

# Valores para la tabla
prediction_value_absolute = prediction_value
prediction_value_percentage = (incremental / baseline) * 100  # Necesitas baseline
lower_bound_value_absolute = lower_bound_value
# ... etc
```

#### **8. Datos Pre/Post Treatment**
```python
start_treatment = len(treatment) - target_period

# Pre-treatment (mismo período que treatment)
pre_treatment = np.sum(treatment[start_treatment - target_period : start_treatment])
pre_counterfactual = np.sum(counterfactual[start_treatment - target_period : start_treatment])

# Post-treatment
post_treatment = np.sum(treatment[start_treatment:])
post_counterfactual = np.sum(counterfactual[start_treatment:])

pre_post_data = [
    {"Group": "Treatment", "Pre-treatment": pre_treatment, "Post-treatment": post_treatment},
    {"Group": "Control", "Pre-treatment": pre_counterfactual, "Post-treatment": post_counterfactual}
]
```

#### **9. Generar la Gráfica**
```python
# Usar la función plot_impact_report del archivo plots.py
fig = plot_impact_report(
    geo_test=murray_response, 
    period=target_period,
    holdout_percentage=holdout_percentage,
    length_treatment=len(treatment_locations)  # Necesitas esto
)
```

### Parámetros Adicionales Necesarios

Además de la respuesta de Murray, necesitarás proporcionar:
- **target_variable**: Nombre de la variable analizada (ej: "conversions")
- **Fechas del experimento**: first_day, last_day, treatment_day, etc.
- **Confidence level**: Nivel de confianza deseado (ej: 0.95)
- **Baseline value**: Para calcular porcentajes de impacto

---

