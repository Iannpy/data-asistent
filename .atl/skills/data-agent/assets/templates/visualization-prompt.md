# Visualization Prompt Template

Plantilla para generar visualizaciones (gráficos) a partir de especificaciones en lenguaje natural.

## Template Base

```
Eres un asistente de visualización de datos. Traduce la siguiente solicitud de gráfico a código Python válido usando matplotlib, seaborn, o plotly.

## Dataset
- Path: {dataset_path}
- Columnas disponibles: {columns}
- Primeras filas:
{head_preview}

## Solicitud del usuario
{user_query}

## Instrucciones
1. Genera código Python que produzca una figura (matplotlib.figure.Figure o plotly figure)
2. Usa matplotlib/seaborn/plotly para crear el gráfico
3. NO uses: os, subprocess, socket, requests, urllib
4. El código debe ser Conciso y Ejecutable
5. La figura debe ser retornada en una variable llamada `fig`

## Código generado
```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Cargar dataset
df = pd.read_csv("{dataset_path}")

# Crear figura
fig, ax = plt.subplots(figsize=(10, 6))

# Tu código aquí
ax.hist(df['columna'], bins=30)

# Configuración del gráfico
ax.set_title('Título del gráfico')
ax.set_xlabel('Eje X')
ax.set_ylabel('Eje Y')

plt.tight_layout()

# Retornar la figura
result = fig
```
```

## Tipos de Gráfico Soportados

| Tipo de Gráfico | Código Base | Palabras Clave |
|-----------------|-------------|----------------|
| Histograma | `ax.hist()` | "histograma", "distribución", "frecuencia" |
| Gráfico de barras | `ax.bar()` | "barras", "comparar", "por categoría" |
| Scatter plot | `ax.scatter()` | "scatter", "relación", "correlación" |
| Línea | `ax.plot()` | "línea", "tendencia", "evolución" |
| Box plot | `sns.boxplot()` | "boxplot", "distribución", "cuartiles" |
| Pie chart | `ax.pie()` | "pie", "porcentaje", "proporción" |
| Heatmap | `sns.heatmap()` | "heatmap", "correlación", "matriz" |

## Ejemplos de Conversión

### Ejemplo 1: Histograma
- **Usuario**: "Haz un histograma de precios"
- **Código**:
```python
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(df['precio'], bins=30, edgecolor='black')
ax.set_title('Distribución de Precios')
ax.set_xlabel('Precio')
ax.set_ylabel('Frecuencia')
plt.tight_layout()
result = fig
```

### Ejemplo 2: Scatter plot
- **Usuario**: "Quiero ver la relación entre edad e ingreso"
- **Código**:
```python
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(df['edad'], df['ingreso'], alpha=0.5)
ax.set_title('Relación Edad vs Ingreso')
ax.set_xlabel('Edad')
ax.set_ylabel('Ingreso')
plt.tight_layout()
result = fig
```

### Ejemplo 3: Gráfico de barras
- **Usuario**: "Muéstrame las ventas por categoría"
- **Código**:
```python
sales_by_category = df.groupby('categoria')['venta'].sum()
fig, ax = plt.subplots(figsize=(10, 6))
sales_by_category.plot(kind='bar', ax=ax)
ax.set_title('Ventas por Categoría')
ax.set_xlabel('Categoría')
ax.set_ylabel('Ventas')
plt.tight_layout()
result = fig
```

### Ejemplo 4: Box plot
- **Usuario**: "Dame un boxplot de salarios por departamento"
- **Código**:
```python
fig, ax = plt.subplots(figsize=(10, 6))
df.boxplot(column='salario', by='departamento', ax=ax)
ax.set_title('Distribución de Salarios por Departamento')
ax.set_xlabel('Departamento')
ax.set_ylabel('Salario')
plt.tight_layout()
result = fig
```

### Ejemplo 5: Heatmap de correlación
- **Usuario**: "Muestra la matriz de correlación"
- **Código**:
```python
corr = df.select_dtypes(include=['number']).corr()
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', ax=ax)
ax.set_title('Matriz de Correlación')
plt.tight_layout()
result = fig
```

## Configuración de Estilos

### Colores (seaborn)
```python
sns.set_palette("husl")
sns.set_style("whitegrid")
```

### Títulos y etiquetas
```python
ax.set_title('Título', fontsize=14, fontweight='bold')
ax.set_xlabel('Etiqueta X', fontsize=12)
ax.set_ylabel('Etiqueta Y', fontsize=12)
ax.tick_params(axis='both', labelsize=10)
```

### Leyenda
```python
ax.legend(title='Leyenda', loc='best')
```

## Errores a Evitar

1. **No verificar tipo de datos**: Solo graficar columnas numéricas para histogram/scatter
2. **No manejar valores nulos**: Limpiar datos antes de graficar
3. **Gráficos demasiado grandes**: Usar `figsize=(10, 6)` o menor
4. **No incluir labels**: Siempre agregar título, xlabel, ylabel

## Notas para el LLM

- Si la columna no es numérica, no se puede hacer histograma — usar value_counts().plot()
- Si hay muchos datos (>10000), sampling para evitar gráficos lentos
- Usar `plt.tight_layout()` antes de retornar la figura
- El resultado debe ser un objeto Figure de matplotlib, no un plt.show()