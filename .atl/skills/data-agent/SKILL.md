---
name: data-agent
description: Agente de análisis de datos que traduce consultas NL a código Pandas ejecutable en sandbox Docker
triggers:
  - analiza
  - consulta
  - explora
  - visualiza
actions:
  - execute_query
  - execute_visualization
  - list_datasets
version: 1.0.0
author: gentleman-programming
type: sdds-agent
---

# Skill: data-agent

Agente de análisis de datos especializado en traducir consultas en lenguaje natural a código Python/Pandas y ejecutarlo de forma segura en un sandbox Docker.

## Cuándo Activar Este Skill

Este skill se activa cuando el usuario:
- Pide analizar, consultar, explorar o visualizar datos
- Proporciona un archivo CSV, Parquet, o JSON con datos
- Quiere obtener insights, estadísticas, o gráficos de un dataset
- Usa palabras como: "analiza", "consulta", "explora", "visualiza", "¿cuántos?", "¿cuál?", "promedio", "total", "gráfico"

## Cómo Ejecutar una Consulta

### Paso 1: Validar el Dataset
Antes de ejecutar cualquier consulta:
1. Verificar que `dataset_path` apunte a un archivo válido (CSV, Parquet)
2. Si el archivo no existe, retornar error claro: "Dataset no encontrado: {path}"
3. Cargar el DataFrame para explorar columnas disponibles

### Paso 2: Generar Código Pandas
El LLM genera código Python/Pandas basado en la consulta:
- **Agregaciones**: `df.groupby().agg()`, `df['col'].mean()`, `df['col'].count()`
- **Filtrado**: `df[df['col'] > valor]`, `df.query()`
- **Transformaciones**: `df['new_col'] = ...`, `df.apply()`
- **Visualizaciones**: `plt.hist()`, `df.plot()`, `seaborn.*`

### Paso 3: Ejecutar en Sandbox
El código se ejecuta en un kernel Jupyter aislado:
- Timeout: 60 segundos máximo
- Memoria máxima: 512MB
- APIs bloqueadas: `os`, `subprocess`, `socket`, `requests`, `urllib`

### Paso 4: Formatear Resultado
El resultado se serializa según su tipo:
- **DataFrame**: JSON con primeras 1000 filas, metadatos de tipos
- **Figura**: PNG codificado en base64
- **Escalar**: Valor primitivo (int, float, string, bool)

## Patrones de Consulta

### Consulta de Agregación
```
Usuario: "¿cuál es el promedio de edad?"
Código: df['edad'].mean()
```

### Consulta de Filtrado
```
Usuario: "¿cuántos registros hay con estado='activo'?"
Código: len(df[df['estado'] == 'activo'])
```

### Consulta de GroupBy
```
Usuario: "¿cuántas ventas por categoría?"
Código: df.groupby('categoria')['venta'].sum()
```

### Consulta de Visualización
```
Usuario: "haz un histograma de precios"
Código: fig, ax = plt.subplots(); ax.hist(df['precios']); ...
```

## Errores Comunes y Cómo Manejarlos

### Error: SyntaxError en código generado
- El LLM generó código inválido
- Retornar: "No pude interpretar la consulta. ¿Podés reformularla?"

### Error: AttributeError (columna no existe)
- La columna en la consulta no existe en el DataFrame
- Mostrar columnas disponibles: "Columnas: {cols}. ¿Cuál usás?"

### Error: Timeout (>60s)
- El código tardó mucho en ejecutarse
- Sugerir: "La consulta es compleja. ¿Podés simplificar o filtrar datos?"

### Error: SecurityViolation
- El código intentó usar APIs bloqueadas
- Retornar: "No se permite acceso al sistema. Solo operaciones de análisis."

## Integración con OpenCode

### Flujo de Invocación
```
1. SDD Orchestrator detecta trigger en el prompt del usuario
2. Carga skill.json para verificar acciones disponibles
3. Lee SKILL.md para obtener instrucciones específicas
4. Invoca execute_query o execute_visualization con {query, dataset_path}
5. El agente retorna resultado formateado (JSON/Base64)
```

### Parámetros de Entrada
```json
{
  "query": "¿cuántas filas tiene el dataset?",
  "dataset_path": "/data/ventas.csv"
}
```

### Respuesta Exitosa
```json
{
  "success": true,
  "result": {
    "type": "scalar",
    "value": 1500
  },
  "execution_time_ms": 2300
}
```

### Respuesta con DataFrame
```json
{
  "success": true,
  "result": {
    "type": "dataframe",
    "data": [...],
    "metadata": {
      "row_count": 50,
      "column_count": 4,
      "truncated": true,
      "original_row_count": 1500
    }
  },
  "execution_time_ms": 4500
}
```

## Configuración

El skill usa las siguientes variables de entorno:
- `OLLAMA_MODEL`: Modelo LLM a usar (default: "llama3.2")
- `OLLAMA_BASE_URL`: URL del servidor Ollama (default: "http://localhost:11434")
- `DATASET_MAX_ROWS`: Filas máximas a retornar (default: 1000)
- `KERNEL_TIMEOUT`: Timeout de ejecución en segundos (default: 60)
- `DOCKER_SANDBOX_IMAGE`: Imagen Docker del sandbox (default configurada en docker-compose)

## Reglas de Seguridad

⚠️ **CRÍTICO**: El código se ejecuta en un entorno aislado. Estas reglas son obligatorias:

1. **Nunca permitir acceso al sistema de archivos fuera del dataset**
2. **Nunca permitir conexiones de red** (requests, urllib, socket)
3. **Nunca permitir ejecución de comandos del sistema** (os.system, subprocess)
4. **Siempre usar pandas/numpy para manipulación de datos**
5. **Siempre verificar que las columnas consultadas existan en el DataFrame**
6. **Truncar DataFrames grandes a 1000 filas máximo**

## Métricas de Éxito

| Métrica | Target |
|---------|--------|
| Tiempo de respuesta (query simple) | < 10 segundos |
| Tiempo de respuesta (visualización) | < 30 segundos |
| Accuracy de código generado | > 90% |
| Bloqueo de código malicioso | 100% |
| Satisfaction del usuario | > 4/5 |

## Siguiente Paso

Si el usuario pide algo fuera del alcance de este skill (ej: entrenar un modelo ML, hacer predicción), responder:
"Este skill es para análisis y visualización de datos. Para modelos ML, necesitás un skill diferente o podés usar código Python directamente en el kernel."