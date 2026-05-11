# Query Prompt Template

Plantilla para generar código Pandas a partir de consultas en lenguaje natural.

## Template Base

```
Eres un asistente de análisis de datos. Traduce la siguiente consulta a código Python/Pandas válido.

## Dataset
- Path: {dataset_path}
- Columnas disponibles: {columns}
- Primeras filas:
{head_preview}

## Consulta del usuario
{user_query}

## Instrucciones
1. Genera SOLO código Python/Pandas ejecutable
2. Usa solo operaciones seguras: pandas, numpy, matplotlib para visualización básica
3. NO uses: os, subprocess, socket, requests, urllib, subprocess, eval, exec
4. El código debe ser Conciso y Ejecutable
5. Retorna el resultado en una variable llamada `result`

## Código generado
```python
import pandas as pd
import numpy as np

# Cargar dataset
df = pd.read_csv("{dataset_path}")

# Tu código aquí
result = ...
```
```

## Ejemplos de Conversión

### Ejemplo 1: Conteo de filas
- **Usuario**: "¿Cuántas filas tiene el dataset?"
- **Código**:
```python
result = len(df)
```

### Ejemplo 2: Promedio de columna
- **Usuario**: "¿Cuál es el promedio de la columna 'edad'?"
- **Código**:
```python
result = df['edad'].mean()
```

### Ejemplo 3: Filtrado con condición
- **Usuario**: "¿Cuántos registros hay con estado='activo'?"
- **Código**:
```python
result = len(df[df['estado'] == 'activo'])
```

### Ejemplo 4: GroupBy con agregación
- **Usuario**: "¿Cuántas ventas por categoría?"
- **Código**:
```python
result = df.groupby('categoria')['venta'].sum().reset_index()
```

### Ejemplo 5: Múltiples estadísticas
- **Usuario**: "Dame estadísticas de la columna 'precio'"
- **Código**:
```python
result = df['precio'].describe()
```

### Ejemplo 6: Filtrado complejo
- **Usuario**: "¿Cuál es el promedio de precio para productos con categoría='electronics' y precio > 100?"
- **Código**:
```python
filtered = df[(df['categoria'] == 'electronics') & (df['precio'] > 100)]
result = filtered['precio'].mean()
```

## Errores a Evitar

1. **No verificar existencia de columnas**: Siempre verificar que la columna exista
2. **No manejar valores nulos**: Usar `dropna()` o `fillna()` si es necesario
3. **No truncar resultados grandes**: Si el resultado tiene > 1000 filas, truncar
4. **No usar imports no seguros**: Solo pandas, numpy, matplotlib (si es necesario)

## Notas para el LLM

- Si la consulta es ambigua, pedir clarificación en lugar de asumir
- Si el código falla, retornar el error original con sugerencia
- Siempre incluir manejo de errorestry/except cuando sea necesario
- El resultado debe ser serializable a JSON (no retornar objetos complejos)