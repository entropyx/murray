# Guía Completa: API Response de Evaluación de Murray

## Índice
1. [Resumen de Datos](#resumen-de-datos)
2. [Series Temporales](#series-temporales)
3. [Bandas de Confianza](#bandas-de-confianza)
4. [Métricas Estadísticas](#métricas-estadísticas)
5. [Datos Pre/Post Tratamiento](#datos-prepost-tratamiento)
6. [Gráfico de 3 Paneles](#gráfico-de-3-paneles)
7. [Generación de PDF](#generación-de-pdf)
8. [Ejemplos de Implementación](#ejemplos-de-implementación)

---

## Resumen de Datos

El endpoint `/analyze/evaluation` devuelve un objeto JSON completo con todos los datos necesarios para crear visualizaciones y reportes. Los datos están organizados en las siguientes categorías:

### Estructura General del Response
```json
{
  "task_id": "string",
  "status": "SUCCESS",
  "results": {
    // Todos los datos de evaluación aquí
  }
}
```

---

## Series Temporales

### **Datos Principales**
```json
{
  "dates": ["2024-01-01", "2024-01-02", ...],
  "treatment": [100, 105, 98, ...],
  "counterfactual": [95, 102, 96, ...],
  "point_difference": [5, 3, 2, ...],
  "cumulative_effect": [0, 0, 5, 8, 10, ...]
}
```

| Campo | Descripción | Uso |
|-------|-------------|-----|
| `dates` | Array de fechas en formato YYYY-MM-DD | Eje X de todos los gráficos |
| `treatment` | Valores observados del grupo de tratamiento | Serie principal azul/verde |
| `counterfactual` | Valores predichos sin tratamiento (control sintético) | Serie de control (línea punteada) |
| `point_difference` | Diferencia tratamiento - control en cada punto | Panel 2: Efecto causal punto por punto |
| `cumulative_effect` | Suma acumulativa del efecto | Panel 3: Efecto acumulativo |

### **Datos del Período de Tratamiento**
```json
{
  "treatment_dates": ["2024-06-01", "2024-06-02", ...],
  "y_treatment": [120, 125, 118, ...],
  "point_difference_treatment": [10, 8, 12, ...],
  "cumulative_effect_treatment": [10, 18, 30, ...]
}
```

**Uso**: Solo los datos del período donde ocurrió el tratamiento, útiles para análisis específicos del período de intervención.

---

## Bandas de Confianza

### **Para el Panel 1 - Serie Principal**
```json
{
  "lower_bound": [115, 118, 112, ...],
  "upper_bound": [125, 132, 128, ...]
}
```

### **Para el Panel 2 - Point Difference**
```json
{
  "lower_bound_pd": [2, 0, 4, ...],
  "upper_bound_pd": [18, 16, 20, ...]
}
```

### **Para el Panel 3 - Cumulative Effect**
```json
{
  "lower_bound_ce": [5, 10, 25, ...],
  "upper_bound_ce": [15, 26, 35, ...]
}
```

**Uso**: Crear zonas sombreadas de confianza en cada panel del gráfico.

---

## Métricas Estadísticas

### **Métricas de Efectividad**
```json
{
  "att": 12.5,
  "incremental": 250.0,
  "percenge_lift": 8.5,
  "MAPE": 2.1,
  "SMAPE": 2.3
}
```

| Métrica | Descripción | Uso en UI |
|---------|-------------|-----------|
| `att` | Average Treatment Effect por ubicación | Indicador de efectividad promedio |
| `incremental` | Efecto incremental total | Valor absoluto del impacto |
| `percenge_lift` | Porcentaje de lift | Indicador principal de performance |
| `MAPE/SMAPE` | Errores del modelo | Indicadores de calidad del ajuste |

### **Métricas de Significancia**
```json
{
  "p_value": 0.023,
  "power": 0.85,
  "observed_stat": 250.0,
  "null_stats": [45, 12, -8, 67, ...]
}
```

### **Métricas MMM**
```json
{
  "spend": 10000,
  "mmm_option": "iROAS",
  "mmm_metric": 0.025
}
```

---

## Datos Pre/Post Tratamiento

### **Estructura**
```json
{
  "pre_treatment": [95, 98, 92, ...],
  "pre_counterfactual": [93, 96, 90, ...],
  "post_treatment": [120, 125, 118, ...],
  "post_counterfactual": [95, 98, 95, ...]
}
```

### **Uso en Tablas de Comparación**
```javascript
// Ejemplo de tabla para PDF/UI
const comparisonData = [
  {
    group: "Treatment",
    pre: sumArray(pre_treatment),
    post: sumArray(post_treatment),
    difference: sumArray(post_treatment) - sumArray(pre_treatment)
  },
  {
    group: "Counterfactual",
    pre: sumArray(pre_counterfactual),
    post: sumArray(post_counterfactual),
    difference: sumArray(post_counterfactual) - sumArray(pre_counterfactual)
  }
];
```

---

## Gráfico de 3 Paneles

### **Panel 1: Observed Data vs Counterfactual**

**Propósito**: Mostrar la comparación entre lo que realmente pasó (treatment) vs lo que hubiera pasado sin tratamiento (counterfactual).

**Datos necesarios**:
```javascript
{
  x: dates,
  y1: treatment,        // Línea sólida (grupo tratamiento)
  y2: counterfactual,   // Línea punteada (grupo control)
  // Banda de confianza
  upper: upper_bound,
  lower: lower_bound,
  // Línea vertical del inicio del tratamiento
  treatment_start: start_position_treatment
}
```

**Implementación**:
```javascript
// Serie principal - Treatment
{
  x: dates,
  y: treatment,
  type: 'scatter',
  mode: 'lines',
  name: 'Treatment Group',
  line: { color: '#2E8B57', width: 2 }
}

// Serie de control - Counterfactual
{
  x: dates,
  y: counterfactual,
  type: 'scatter',
  mode: 'lines',
  name: 'Control Group',
  line: { color: '#808080', dash: 'dash', width: 2 }
}

// Banda de confianza (solo en período de tratamiento)
{
  x: treatment_dates,
  y: upper_bound,
  type: 'scatter',
  mode: 'lines',
  line: { color: 'rgba(0,0,0,0)' },
  showlegend: false
},
{
  x: treatment_dates,
  y: lower_bound,
  type: 'scatter',
  mode: 'lines',
  fill: 'tonexty',
  fillcolor: 'rgba(128,128,128,0.3)',
  line: { color: 'rgba(0,0,0,0)' },
  name: '95% Confidence Interval'
}

// Línea vertical de inicio de tratamiento
{
  type: 'line',
  x0: dates[start_position_treatment],
  x1: dates[start_position_treatment],
  y0: 0,
  y1: 1,
  yref: 'paper',
  line: { color: 'black', dash: 'dash' }
}
```

### **Panel 2: Point Difference (Causal Effect)**

**Propósito**: Mostrar el efecto causal punto por punto (tratamiento - control en cada momento).

**Datos necesarios**:
```javascript
{
  x: dates,
  y: point_difference,
  upper: upper_bound_pd,
  lower: lower_bound_pd,
  zero_line: true  // Línea horizontal en y=0
}
```

**Implementación**:
```javascript
// Serie de diferencias
{
  x: dates,
  y: point_difference,
  type: 'scatter',
  mode: 'lines',
  name: 'Causal Effect',
  line: { color: '#2E8B57', width: 2 }
}

// Banda de confianza para diferencias
{
  x: treatment_dates,
  y: upper_bound_pd,
  type: 'scatter',
  mode: 'lines',
  line: { color: 'rgba(0,0,0,0)' },
  showlegend: false
},
{
  x: treatment_dates,
  y: lower_bound_pd,
  type: 'scatter',
  mode: 'lines',
  fill: 'tonexty',
  fillcolor: 'rgba(128,128,128,0.3)',
  line: { color: 'rgba(0,0,0,0)' },
  name: '95% CI'
}

// Línea horizontal en cero
{
  type: 'line',
  x0: dates[0],
  x1: dates[dates.length - 1],
  y0: 0,
  y1: 0,
  line: { color: 'gray', dash: 'dash', width: 1 }
}
```

### **Panel 3: Cumulative Effect**

**Propósito**: Mostrar el efecto acumulativo a lo largo del tiempo.

**Datos necesarios**:
```javascript
{
  x: dates,
  y: cumulative_effect,
  upper: upper_bound_ce,
  lower: lower_bound_ce
}
```

**Implementación**:
```javascript
// Serie acumulativa
{
  x: dates,
  y: cumulative_effect,
  type: 'scatter',
  mode: 'lines',
  name: 'Cumulative Effect',
  line: { color: '#2E8B57', width: 2 }
}

// Banda de confianza acumulativa
{
  x: treatment_dates,
  y: upper_bound_ce,
  type: 'scatter',
  mode: 'lines',
  line: { color: 'rgba(0,0,0,0)' },
  showlegend: false
},
{
  x: treatment_dates,
  y: lower_bound_ce,
  type: 'scatter',
  mode: 'lines',
  fill: 'tonexty',
  fillcolor: 'rgba(128,128,128,0.3)',
  line: { color: 'rgba(0,0,0,0)' },
  name: '95% CI'
}
```
