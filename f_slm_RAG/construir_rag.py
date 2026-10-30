import psycopg2
import requests
import json

DB_CONFIG = {
    "dbname": "chicago_crime_db",
    "user": "postgres",
    "password": "palta123",
    "host": "localhost",
    "port": "5432",
}
OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

EJEMPLOS_SQL = [
    {
        "pregunta": "Encuentra la cantidad de crímenes a menos de 500 metros del punto con latitud 41.87 y longitud -87.62.",
        "sql": "SELECT COUNT(*) FROM crimes WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(-87.62, 41.87), 4326), 500);",
    },
    {
        "pregunta": "¿Cuántos crímenes del tipo 'HOMICIDE' existen?",
        "sql": "SELECT COUNT(*) FROM crimes WHERE primary_type = 'HOMICIDE';",
    },
    {
        "pregunta": "Muestra las 3 áreas con más crímenes violentos.",
        "sql": "SELECT primary_type, COUNT(*) as total FROM crimes GROUP BY primary_type ORDER BY total DESC LIMIT 3;",
    },
]


def obtener_embedding(texto):
    payload = {"model": EMBED_MODEL, "prompt": texto}
    respuesta = requests.post(OLLAMA_URL, json=payload)
    return respuesta.json()["embedding"]


def inicializar_memoria_rag():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rag_memoria (
            id SERIAL PRIMARY KEY,
            pregunta TEXT,
            query_sql TEXT,
            embedding VECTOR(768)
        );
    """)

    cur.execute("TRUNCATE TABLE rag_memoria;")

    print("Inyectando ejemplos curados al ST-RAG...")
    for ej in EJEMPLOS_SQL:
        vector = obtener_embedding(ej["pregunta"])
        cur.execute(
            "INSERT INTO rag_memoria (pregunta, query_sql, embedding) VALUES (%s, %s, %s)",
            (ej["pregunta"], ej["sql"], vector),
        )
        print(f"Memorizado: {ej['pregunta']}")

    conn.commit()
    cur.close()
    conn.close()
    print("\nBase de datos vectorial ST-RAG construida")


if __name__ == "__main__":
    inicializar_memoria_rag()
