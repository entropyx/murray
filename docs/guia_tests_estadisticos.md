# Guía de Tests Estadísticos en Murray

## Introducción

Murray utiliza diferentes funciones de test estadístico para evaluar la significancia del efecto del tratamiento. La selección del test apropiado depende de las características de tus datos y del tipo de efecto que quieres detectar. Esta guía te ayudará a entender cuándo usar cada test.

## Tests Disponibles

### 1. **Sum Test (Test de Suma)** - `sum`

#### ¿Qué hace?
Evalúa el efecto acumulativo total durante el período de tratamiento sumando todos los residuales del tratamiento.

#### Fórmula
```
Estadístico = Σ(residuales_tratamiento)
```

#### ¿Cuándo usarlo?
**RECOMENDADO PARA:**
- ✅ Datos de conteo (ventas, conversiones, clics, impresiones)
- ✅ Métricas de volumen total donde el impacto agregado es importante
- ✅ Datos no negativos que representan cantidades acumulables
- ✅ Cuando te interesa el impacto total en lugar del promedio

**EJEMPLOS DE MÉTRICAS:**
- Ingresos totales por ventas
- Número total de conversiones
- Cantidad total de productos vendidos
- Total de clics en anuncios
- Volumen total de transacciones

#### Ventajas
- Detecta cambios en volumen total
- Apropiado para métricas de negocio
- No requiere distribución normal
- Robusto para datos de conteo

#### Desventajas
- Sensible al tamaño de la muestra
- No estandarizado por variabilidad

---

### 2. **Mean Difference Test (Test de Diferencia de Medias)** - `mean_diff`

#### ¿Qué hace?
Evalúa la diferencia promedio entre el tratamiento y control calculando la media de los residuales.

#### Fórmula
```
Estadístico = Media(residuales_tratamiento)
```

#### ¿Cuándo usarlo?
**RECOMENDADO PARA:**
- ✅ Datos continuos con distribución aproximadamente normal
- ✅ Efectos por unidad (valor promedio del pedido, tasa de conversión)
- ✅ Cuando quieres detectar cambios en valores promedio
- ✅ Tamaños de muestra similares entre grupos
- ✅ Datos sin outliers significativos

**EJEMPLOS DE MÉTRICAS:**
- Valor promedio del pedido (AOV)
- Tasa de conversión promedio
- Tiempo promedio de sesión
- Rating promedio de productos
- Margen promedio por transacción

#### Ventajas
- Fácil de interpretar
- Efectivo para datos normales
- Detecta cambios en nivel promedio

#### Desventajas
- Sensible a outliers
- Requiere distribución aproximadamente normal
- No considera variabilidad en el cálculo

---

### 3. **T-Test (Test T)** - `t_test`

#### ¿Qué hace?
Evalúa la diferencia estandarizada entre tratamiento y control, considerando tanto la media como la variabilidad y el tamaño de muestra.

#### Fórmula
```
Estadístico = Media(residuales) / (Desv_Estándar(residuales) / √n)
```

#### ¿Cuándo usarlo?
**RECOMENDADO PARA:**
- ✅ Datos con distribución normal
- ✅ Muestras pequeñas (n < 30)
- ✅ Cuando necesitas efectos estandarizados
- ✅ A/B testing con outcomes continuos
- ✅ Cuando la variabilidad es importante

**EJEMPLOS DE MÉTRICAS:**
- Tests A/B tradicionales
- Métricas con alta variabilidad
- Estudios con muestras limitadas
- Análisis que requieren tamaños de efecto estandarizados

#### Ventajas
- Considera variabilidad y tamaño de muestra
- Proporciona efectos estandarizados
- Robusto para muestras pequeñas
- Ampliamente usado en estadística

#### Desventajas
- Requiere normalidad estricta
- Sensible a outliers
- Más complejo de interpretar

---

### 4. **Median Difference Test (Test de Diferencia de Medianas)** - `median_diff`

#### ¿Qué hace?
Evalúa la diferencia en la mediana entre tratamiento y control, siendo robusto a outliers y distribuciones no normales.

#### Fórmula
```
Estadístico = Mediana(residuales_tratamiento)
```

#### ¿Cuándo usarlo?
**RECOMENDADO PARA:**
- ✅ Datos no normales o sesgados
- ✅ Presencia de outliers significativos
- ✅ Cuando quieres estimaciones robustas
- ✅ Datos ordinales
- ✅ Distribuciones asimétricas

**EJEMPLOS DE MÉTRICAS:**
- Datos de ingresos (típicamente sesgados)
- Tiempo de engagement (con outliers)
- Ratings o puntuaciones
- Métricas con valores extremos
- Cualquier métrica con distribución no normal

#### Ventajas
- Robusto a outliers
- No requiere normalidad
- Funciona con distribuciones asimétricas
- Menos sensible a valores extremos

#### Desventajas
- Menos eficiente que la media para datos normales
- Puede perder información sobre la cola de la distribución

---

## Sistema de Recomendación Automática

Murray analiza automáticamente tus datos y recomienda el test más apropiado basado en:

### Características Analizadas
1. **Tipo de datos**: Conteo, continuo positivo, discreto, continuo general
2. **Normalidad**: Test de Shapiro-Wilk o D'Agostino-Pearson
3. **Outliers**: Detección usando método IQR
4. **Asimetría**: Medida de skewness
5. **Tamaño de muestra**: Consideración para tests apropiados

### Árbol de Decisión

```
¿Es dato de conteo sin outliers?
├── SÍ → **SUM TEST** (Confianza Alta)
└── NO → ¿Hay outliers significativos (>5%)?
    ├── SÍ → **MEDIAN_DIFF** (Confianza Alta)
    └── NO → ¿Es distribución normal?
        ├── SÍ → ¿Muestra pequeña (<30)?
            ├── SÍ → **T_TEST** (Confianza Alta)
            └── NO → **MEAN_DIFF** (Confianza Alta)
        └── NO → ¿Muestra grande (>50)?
            ├── SÍ → **MEAN_DIFF** (Confianza Media)
            └── NO → **MEDIAN_DIFF** (Confianza Baja)
```

### Niveles de Confianza

- 🟢 **Alta**: Recomendación fuerte basada en características claras
- 🟡 **Media**: Recomendación razonable pero con consideraciones
- 🔴 **Baja**: Recomendación conservadora o de fallback

---

## Ejemplos Prácticos

### Caso 1: E-commerce - Conversiones
**Datos**: Número de conversiones diarias por región
- **Tipo**: Conteo, enteros no negativos
- **Distribución**: No normal, muchos ceros
- **Recomendación**: **SUM TEST**
- **Razón**: Interesa el impacto total en conversiones

### Caso 2: E-commerce - Valor Promedio del Pedido
**Datos**: AOV diario por región
- **Tipo**: Continuo positivo
- **Distribución**: Ligeramente sesgada, algunos outliers
- **Recomendación**: **MEDIAN_DIFF**
- **Razón**: Outliers en compras grandes, mediana más representativa

### Caso 3: SaaS - Tiempo de Sesión
**Datos**: Tiempo promedio de sesión por región
- **Tipo**: Continuo positivo
- **Distribución**: Normal, sin outliers
- **Muestra**: Grande (n > 100)
- **Recomendación**: **MEAN_DIFF**
- **Razón**: Distribución normal, interesa cambio promedio

### Caso 4: Aplicación Móvil - Rating
**Datos**: Rating promedio de app por región
- **Tipo**: Ordinal (1-5 estrellas)
- **Distribución**: No normal, sesgada hacia valores altos
- **Recomendación**: **MEDIAN_DIFF**
- **Razón**: Datos ordinales, distribución sesgada

---

## Consideraciones Especiales

### Para Métricas de Negocio
- **Revenue total**: Sum Test
- **Revenue per user**: Mean Diff o Median Diff (depende de outliers)
- **Conversion rate**: Mean Diff (si es continua) o Sum Test (si son conteos)

### Para Tests A/B Tradicionales
- **Continuous outcomes**: T-Test o Mean Diff
- **Binary outcomes**: Sum Test (conteo de éxitos)
- **Time-to-event**: Median Diff (datos típicamente sesgados)

### Para Datos de Marketing Digital
- **Impressions**: Sum Test
- **CTR**: Mean Diff
- **CPC**: Median Diff (suele tener outliers)
- **ROAS**: Depende de la distribución

---

## Interpretación de Resultados

### Sum Test
- **Resultado positivo**: El tratamiento aumentó el total acumulado
- **Magnitud**: Diferencia absoluta en unidades de la métrica

### Mean Diff
- **Resultado positivo**: El tratamiento aumentó el promedio
- **Magnitud**: Diferencia promedio por unidad/período

### T-Test
- **Resultado positivo**: Efecto estandarizado significativo
- **Magnitud**: Tamaño del efecto en desviaciones estándar

### Median Diff
- **Resultado positivo**: El tratamiento aumentó la mediana
- **Magnitud**: Diferencia en la mediana de la distribución

---

## Recomendaciones Finales

1. **Confía en la recomendación automática** cuando tenga confianza alta
2. **Revisa las características de tus datos** si tienes dudas
3. **Considera el contexto de negocio** para la interpretación
4. **Documenta tu elección** para análisis futuros
5. **Mantén consistencia** en tests similares para comparabilidad

El sistema de Murray está diseñado para guiarte hacia la elección más apropiada, pero el contexto de tu negocio y objetivos específicos siempre deben ser considerados en la decisión final.