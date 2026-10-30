import psycopg2
import requests
import time
import pandas as pd
from datetime import datetime

DB_CONFIG = {
    "dbname": "chicago_crime_db",
    "user": "postgres",
    "password": "palta123",
    "host": "localhost",
    "port": "5432"
}
OLLAMA_URL_EMBED = "http://localhost:11434/api/embeddings"
OLLAMA_URL_GENERATE = "http://localhost:11434/api/generate"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "gemma2"

ESQUEMA_DB = """
Tabla: crimes
Columnas:
- id (integer)
- primary_type (text)
- date (timestamp)
- latitude (double precision)
- longitude (double precision)
- geom (geometry, Point, 4326)
"""

PREGUNTAS_ESTRES = [
    "Genera una consulta para encontrar todos los 'MOTOR VEHICLE THEFT' ocurridos entre la medianoche (00:00:00) y las 05:00:00 a menos de 1000 metros de la latitud 41.87 y longitud -87.62.",
    "Muestra los crímenes cerca del centro.", 
    "Cuenta el total de crímenes agrupados por tipo (primary_type) en toda la ciudad y ordénalos de mayor a menor.",
    "Encuentra las 5 ubicaciones (latitud, longitud) con mayor concentración de 'HOMICIDE'."
]

def obtener_embedding(texto):
    payload = {"model": EMBED_MODEL, "prompt": texto}
    respuesta = requests.post(OLLAMA_URL_EMBED, json=payload)
    return respuesta.json()["embedding"]

def recuperar_contexto_rag(pregunta_vector):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT query_sql FROM rag_memoria ORDER BY embedding <=> %s::vector LIMIT 1;", (pregunta_vector,))
        resultado = cur.fetchone()
        cur.close()
        conn.close()
        return resultado[0] if resultado else "No hay contexto."
    except Exception as e:
        print(f"Error en RAG: {e}")
        return "Error en RAG."

def generar_sql_con_gemma(pregunta, contexto):
    prompt_rag = f"""Eres un experto en bases de datos espaciales. 
Genera el código SQL puro para responder a la pregunta. No incluyas explicaciones ni bloques markdown.
Usa punto y coma al final.

ESQUEMA:
{ESQUEMA_DB}

CONTEXTO RAG:
{contexto}

PREGUNTA:
{pregunta}
SQL:"""

    payload = {
        "model": LLM_MODEL,
        "prompt": prompt_rag,
        "stream": False,
        "temperature": 0.0,
        "options": {
            "num_predict": 150
        }
    }
    
    try:
        respuesta = requests.post(OLLAMA_URL_GENERATE, json=payload)
        texto = respuesta.json()["response"]
        return texto.split(';')[0] + ';' if ';' in texto else texto.strip()
    except Exception as e:
         print(f"Error LLM: {e}")
         return "Error LLM"

def ejecutar_sql(query):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(query)
        resultado = cur.fetchall()
        cur.close()
        conn.close()
        return "Exito", len(resultado)
    except Exception as e:
        return "Fallo", str(e) 

def ejecutar_pruebas():
    resultados = []
    print(f"Iniciando Pruebas de Estres {LLM_MODEL.upper()} ---\n")

    for i, pregunta in enumerate(PREGUNTAS_ESTRES):
        print(f"[{i+1}/4] Procesando: {pregunta}")
        start_time = time.time()
        vector = obtener_embedding(pregunta)
        contexto = recuperar_contexto_rag(vector)
        
        sql_generado = generar_sql_con_gemma(pregunta, contexto)
        
        estado, detalle = ejecutar_sql(sql_generado)
        
        latencia = round(time.time() - start_time, 2)
        
        print(f"  -> Estado: {estado} | Latencia: {latencia}s")
        
        resultados.append({
            "Prueba_ID": i+1,
            "Pregunta": pregunta,
            "Contexto_RAG": contexto,
            "SQL_Generado": sql_generado,
            "Estado_Ejecucion": estado,
            "Detalle_DB": detalle,
            "Latencia_Segundos": latencia
        })

    df = pd.DataFrame(resultados)
    nombre_archivo = f"reporte_estres_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(nombre_archivo, index=False, encoding='utf-8')
    print(f"\nPruebas finalizadas. Reporte guardado en: {nombre_archivo}")

if __name__ == "__main__":
    ejecutar_pruebas()
