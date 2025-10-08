# Modelo Multicell: Guía Completa para Usuarios

## ¿Qué es el Modelo Multicell?

El modelo multicell es una evolución del diseño experimental tradicional que permite crear **múltiples grupos de tratamiento** en un solo experimento de marketing. En lugar de probar una sola campaña en un grupo de ciudades, puedes probar **varias versiones** simultáneamente, cada una en diferentes conjuntos de ubicaciones.

### Analogía Simple
Imagina que tienes una cadena de tiendas y quieres probar diferentes estrategias de marketing:
- **Método tradicional**: Probar una estrategia en 3 ciudades
- **Método multicell**: Probar 3 estrategias diferentes, cada una en grupos distintos de ciudades

## ¿Para Qué Sirve?

### 1. **Reduce el Riesgo**
- Si una estrategia falla, las otras pueden compensar
- No pones "todos los huevos en una canasta"

### 2. **Aumenta el Aprendizaje**
- Comparas múltiples enfoques simultáneamente
- Identificas qué funciona mejor en diferentes contextos

### 3. **Optimiza Recursos**
- Aprovechas mejor tus ubicaciones disponibles
- Reduces el tiempo total de experimentación

## ¿Cómo Funciona?

### Paso 1: Definición de Parámetros
El usuario configura:
- **Número de celdas**: Cuántos grupos de tratamiento quiere
- **Tamaños permitidos**: Qué tamaños puede tener cada grupo
- **Ubicaciones excluidas**: Ciudades que no pueden participar

### Paso 2: Análisis Inteligente
El sistema:
1. **Analiza todas las combinaciones posibles** de ubicaciones
2. **Calcula qué tan bien funcionaría cada combinación** usando modelos estadísticos
3. **Encuentra la mejor combinación global** considerando todos los grupos simultáneamente

### Paso 3: Selección Óptima
- **Elige los mejores grupos** que no compartan ubicaciones de tratamiento
- **Optimiza el diseño completo** para maximizar la precisión del experimento

## Parámetros de Entrada

### 1. **Número de Celdas (Cells)**
- **Qué es**: Cuántos grupos de tratamiento diferentes quieres en tu experimento
- **Ejemplo**: Si eliges 3, tendrás 3 campañas diferentes corriendo simultáneamente
- **Por qué es importante**: Determina cuántas estrategias puedes probar a la vez

### 2. **Tamaños Permitidos (Allowed Sizes)**
- **Qué es**: Una lista de cuántas ubicaciones puede tener cada grupo de tratamiento
- **Ejemplo**: [2, 3, 4] significa que cada grupo puede tener 2, 3 o 4 ciudades
- **Por qué es importante**: Te da flexibilidad para que el sistema encuentre la mejor combinación

### 3. **Ubicaciones Excluidas (Excluded Locations)**
- **Qué es**: Ciudades o regiones que no pueden participar en el experimento
- **Ejemplo**: ["Ciudad de México", "Guadalajara"] si no quieres incluir estas ciudades
- **Por qué es importante**: Respeta restricciones operativas o estratégicas

### 4. **Porcentaje Máximo de Tratamiento (Maximum Treatment Percentage)**
- **Qué es**: Qué porcentaje de tus ubicaciones totales pueden recibir tratamiento
- **Ejemplo**: 30% significa que máximo el 30% de tus ciudades pueden tener campaña
- **Por qué es importante**: Asegura que tengas suficientes ubicaciones de control para medir el impacto

### 5. **Nivel de Significancia (Significance Level)**
- **Qué es**: Qué tan estricto quieres ser para considerar un resultado como "exitoso"
- **Ejemplo**: 0.1 (10%) es menos estricto que 0.05 (5%)
- **Por qué es importante**: Determina qué tan confiable debe ser tu resultado

## Cómo el Sistema Decide los Grupos y Tamaños

### Ejemplo Detallado del Proceso de Selección

Supongamos que configuras:
- **Número de celdas**: 3
- **Tamaños permitidos**: [1, 2, 3, 4, 5]

### Fase 1: Generación de Candidatos

El sistema genera y evalúa **todos los grupos posibles** para cada tamaño:

```
Tamaño 1:
- Grupo A: [Ciudad A] → Precisión: 0.08 (malo)
- Grupo B: [Ciudad B] → Precisión: 0.12 (peor)
- Grupo C: [Ciudad C] → Precisión: 0.06 (bueno)
- ... (más combinaciones)

Tamaño 2:
- Grupo D: [Ciudad D, E] → Precisión: 0.05 (excelente)
- Grupo E: [Ciudad F, G] → Precisión: 0.09 (regular)
- Grupo F: [Ciudad H, I] → Precisión: 0.07 (bueno)
- ... (más combinaciones)

Tamaño 3:
- Grupo G: [Ciudad J, K, L] → Precisión: 0.06 (bueno)
- Grupo H: [Ciudad M, N, O] → Precisión: 0.11 (malo)
- ... (más combinaciones)

Tamaño 4:
- Grupo I: [Ciudad P, Q, R, S] → Precisión: 0.07 (bueno)
- ... (más combinaciones)

Tamaño 5:
- Grupo J: [Ciudad T, U, V, W, X] → Precisión: 0.10 (regular)
- ... (más combinaciones)
```

### Fase 2: Selección Global Óptima

El sistema **ordena TODOS los candidatos** por precisión, sin importar el tamaño:

```
Ranking Global:
1. Grupo D (Tamaño 2): [Ciudad D, E] → Precisión: 0.05 ✓ SELECCIONADO
2. Grupo C (Tamaño 1): [Ciudad C] → Precisión: 0.06 ✓ SELECCIONADO  
3. Grupo G (Tamaño 3): [Ciudad J, K, L] → Precisión: 0.06 ✓ SELECCIONADO
4. Grupo F (Tamaño 2): [Ciudad H, I] → Precisión: 0.07 ← Ya no se necesita
5. Grupo I (Tamaño 4): [Ciudad P, Q, R, S] → Precisión: 0.07 ← Ya no se necesita
```

### Resultado Final

**Experimento con 3 celdas:**
- **Celda 1**: Tamaño 2 - [Ciudad D, E] (la mejor opción global)
- **Celda 2**: Tamaño 1 - [Ciudad C] (segunda mejor opción)
- **Celda 3**: Tamaño 3 - [Ciudad J, K, L] (tercera mejor opción)

### Puntos Clave del Proceso

1. **No hay asignación predeterminada**: El sistema NO decide "voy a hacer una celda de cada tamaño"
2. **Selección por rendimiento**: Podría resultar en 3 celdas de tamaño 2 si esas son las mejores
3. **Exclusividad mutua**: Si Ciudad D está en Celda 1, no puede estar en Celda 2 o 3
4. **Optimización global**: Busca la mejor combinación considerando todas las opciones juntas

### ¿Por Qué Esta Combinación?

- **Tamaño 2 ganó**: Los datos mostraron que el mejor grupo individual tiene 2 ciudades
- **Tamaño 1 fue segundo**: Una ciudad específica funcionó muy bien sola
- **Tamaño 3 fue tercero**: Un grupo de 3 ciudades tuvo buen rendimiento
- **Tamaños 4 y 5 no se usaron**: Sus mejores opciones no fueron competitivas

## Diferencias con el Método Tradicional

| Aspecto | Método Tradicional | Modelo Multicell |
|---------|-------------------|------------------|
| Grupos de tratamiento | 1 | Múltiples |
| Tamaños de grupo | Fijo | Flexibles |
| Riesgo | Alto | Distribuido |
| Aprendizaje | Limitado | Amplio |

## Cuándo Usar el Modelo Multicell

### Ideal Para:
- **Múltiples estrategias** que quieres comparar
- **Suficientes ubicaciones** para crear varios grupos
- **Experimentos de alto valor** donde la precisión es crítica
- **Situaciones de incertidumbre** donde quieres diversificar el riesgo

### No Recomendado Para:
- **Muy pocas ubicaciones** (menos de 10)
- **Una sola estrategia** específica para probar
- **Experimentos simples** donde la complejidad adicional no se justifica

## Interpretación de Resultados

### Métricas Clave
- **MAPE (Error Porcentual Medio)**: Qué tan preciso es cada grupo
- **Impacto Estimado**: Cuánto creció cada tratamiento vs. control
- **Nivel de Confianza**: Qué tan seguros estamos del resultado

### Ejemplo de Interpretación
```
Celda 1 (Tamaño 2): +15% de crecimiento (95% confianza)
Celda 2 (Tamaño 1): +8% de crecimiento (90% confianza)
Celda 3 (Tamaño 3): +3% de crecimiento (80% confianza)

Conclusión: La estrategia de la Celda 1 es la más efectiva
```

## Conclusión

El modelo multicell representa una evolución natural en el diseño experimental, permitiendo experimentos más inteligentes y precisos. Al automatizar la selección óptima de grupos y tamaños, libera al usuario de decisiones complejas mientras maximiza el valor del experimento.

La clave está en entender que el sistema busca la **mejor combinación global** de rendimiento, no una distribución equilibrada de tamaños. Esto significa que podrías obtener resultados como "3 celdas de tamaño 2" si esa es la combinación más precisa para tus datos específicos.