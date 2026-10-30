import psycopg2
import requests

DB_CONFIG = {
    "dbname": "chicago_crime_db",
    "user": "postgres",
    "password": "palta123",
    "host": "localhost",
    "port": "5432",
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
- description (text)
- geom (geometry, Point, 4326) - Coordenadas espaciales.
"""


def obtener_embedding(texto):
    payload = {"model": EMBED_MODEL, "prompt": texto}
    return requests.post(OLLAMA_URL_EMBED, json=payload).json()["embedding"]


def recuperar_contexto_rag(pregunta_vector):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT pregunta, query_sql 
        FROM rag_memoria 
        ORDER BY embedding <=> %s::vector 
        LIMIT 1;
    """,
        (pregunta_vector,),
    )
    resultado = cur.fetchone()
    cur.close()
    conn.close()
    return resultado


def generar_sql_con_gemma(pregunta, contexto):
    prompt_rag = f"""Eres un analista de datos policiales. Genera una consulta SQL para PostgreSQL/PostGIS.
No expliques nada. Solo devuelve el código SQL puro.

ESQUEMA DE LA BASE DE DATOS:
{ESQUEMA_DB}

EJEMPLO DE REFERENCIA (Úsalo como guía para la sintaxis espacial):
Pregunta similar: {contexto[0]}
SQL correcto: {contexto[1]}

PREGUNTA DEL USUARIO:
{pregunta}
SQL:"""

    payload = {
        "model": LLM_MODEL,
        "prompt": prompt_rag,
        "stream": False,
        "temperature": 0.0,
    }
    respuesta = requests.post(OLLAMA_URL_GENERATE, json=payload)
    return respuesta.json()["response"].replace("```sql", "").replace("```", "").strip()


def ejecutar_sql(query):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(query)
    resultado = cur.fetchall()
    cur.close()
    conn.close()
    return resultado


if __name__ == "__main__":
    pregunta_usuario = "Encuentra la cantidad de crímenes a menos de 500 metros del punto con latitud 41.87 y longitud -87.62."
    print(f"Pregunta: {pregunta_usuario}\n")

    vector_pregunta = obtener_embedding(pregunta_usuario)
    contexto = recuperar_contexto_rag(vector_pregunta)
    print(f"Contexto inyectado al modelo desde pgvector:\n- {contexto[1]}\n")

    sql_generado = generar_sql_con_gemma(pregunta_usuario, contexto)
    print(f"SQL Generado por {LLM_MODEL.upper()}:\n{sql_generado}\n")

    try:
        resultado = ejecutar_sql(sql_generado)
        print(f"Resultado de la Base de Datos: {resultado}")
    except Exception as e:
        print(f"Fallo de ejecucion: {e}")
