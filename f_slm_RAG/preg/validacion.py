import psycopg2
import requests
import json
import time

DB_CONFIG = {
    "dbname": "chicago_crime_db",
    "user": "postgres",
    "password": "palta123",
    "host": "localhost",
    "port": "5432",
}
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma2"

ESQUEMA_DB = """
Tabla: crimes
Columnas principales:
- id (integer)
- primary_type (text) - Ej: 'THEFT', 'HOMICIDE'
- description (text)
- latitude (double precision)
- longitude (double precision)
- geom (geometry, Point, 4326)
"""

PREGUNTAS = [
    "¿Cuántos incidentes hay registrados en total en la base de datos?",
    "¿Cuántos crímenes del tipo 'HOMICIDE' existen?",
    "Encuentra la cantidad de crímenes a menos de 500 metros del punto con latitud 41.87 y longitud -87.62.",
]


def generar_sql_con_gemma(pregunta):
    prompt = f"""Eres un experto en bases de datos PostgreSQL y PostGIS. 
Dada la siguiente estructura de tabla, escribe una consulta SQL que responda a la pregunta del usuario. 
Solo devuelve el código SQL puro sin bloques de formato (```sql) ni explicaciones.

{ESQUEMA_DB}

Pregunta: {pregunta}
SQL:"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.0,
    }

    response = requests.post(OLLAMA_URL, json=payload)
    if response.status_code == 200:
        return response.json()["response"].strip()
    return "ERROR_EN_LLM"


def ejecutar_sql(query):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(query)
        resultado = cur.fetchall()
        cur.close()
        conn.close()
        return f"Exito: {resultado}"
    except Exception as e:
        return f"Fallo de ejecucion: {str(e)}"


print(f"--- Iniciando Evaluacion Baseline con {MODEL_NAME.upper()} (Sin RAG) ---\n")

for i, pregunta in enumerate(PREGUNTAS):
    print(f"Pregunta {i+1}: {pregunta}")

    start_time = time.time()
    sql_generado = generar_sql_con_gemma(pregunta)
    latencia = round(time.time() - start_time, 2)

    sql_limpio = sql_generado.replace("```sql", "").replace("```", "").strip()

    print(f"SQL Generado (en {latencia}s):\n{sql_limpio}")

    resultado_db = ejecutar_sql(sql_limpio)
    print(f"Resultado DB: {resultado_db}")
    print("-" * 50)
