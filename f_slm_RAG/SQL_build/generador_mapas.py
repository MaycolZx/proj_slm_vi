import psycopg2
import requests
import folium
from folium.plugins import HeatMap
import os

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
- latitude (double precision)
- longitude (double precision)
- geom (geometry, Point, 4326)
"""


def recuperar_contexto_rag(pregunta):
    """Obtiene el embedding y recupera la sintaxis espacial correcta."""
    vector = requests.post(
        OLLAMA_URL_EMBED, json={"model": EMBED_MODEL, "prompt": pregunta}
    ).json()["embedding"]
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        "SELECT query_sql FROM rag_memoria ORDER BY embedding <=> %s::vector LIMIT 1;",
        (vector,),
    )
    contexto = cur.fetchone()[0]
    cur.close()
    conn.close()
    return contexto


def generar_sql_visual(pregunta, contexto):
    """Fuerza al modelo a devolver coordenadas basándose en el ejemplo del RAG."""
    prompt = f"""Eres un experto en bases de datos espaciales. 
Convierte la siguiente consulta de conteo en una consulta que devuelva 'latitude' y 'longitude'.
No uses LIMIT. Solo devuelve el código SQL puro. No des explicaciones.

ESQUEMA: {ESQUEMA_DB}
EJEMPLO BASE (Usa esta lógica espacial): {contexto}
PREGUNTA: {pregunta}
SQL:"""

    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.0,
    }
    respuesta_cruda = requests.post(OLLAMA_URL_GENERATE, json=payload).json()[
        "response"
    ]
    sql_limpio = respuesta_cruda.split(";")[0] + ";"
    return sql_limpio.replace("```sql", "").replace("```", "").strip()


def generar_mapa(query_sql, lat_centro, lon_centro):
    """Ejecuta el SQL y dibuja un mapa de calor con los resultados."""
    print("Ejecutando consulta en PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(query_sql)
    coordenadas = cur.fetchall()
    cur.close()
    conn.close()

    if not coordenadas:
        print("No se encontraron crímenes en esa área.")
        return

    print(f"Graficando {len(coordenadas)} puntos en el mapa...")
    mapa = folium.Map(location=[lat_centro, lon_centro], zoom_start=15)
    HeatMap(coordenadas, radius=12, blur=10, max_zoom=1).add_to(mapa)
    archivo_salida = "mapa_hotspots.html"
    mapa.save(archivo_salida)
    print(f"✅ Mapa interactivo generado con éxito: {os.path.abspath(archivo_salida)}")


if __name__ == "__main__":
    pregunta_usuario = "Muestra las ubicaciones de los crímenes a menos de 500 metros del punto con latitud 41.87 y longitud -87.62."
    lat_objetivo, lon_objetivo = 41.87, -87.62

    print(f"Pregunta: {pregunta_usuario}\n")
    contexto_sql = recuperar_contexto_rag(pregunta_usuario)

    sql_generado = generar_sql_visual(pregunta_usuario, contexto_sql)
    print(f"SQL Generado:\n{sql_generado}\n")

    generar_mapa(sql_generado, lat_objetivo, lon_objetivo)
