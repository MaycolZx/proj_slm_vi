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
EMBED_MODEL = "nomic-embed-text"

pregunta_ejemplo = "Muestrame todos los robos ocurridos en diciembre de 2018."
sql_ejemplo = "SELECT latitude, longitude FROM crimes WHERE primary_type = 'ROBBERY' AND EXTRACT(YEAR FROM date::date) = 2018 AND EXTRACT(MONTH FROM date::date) = 12;"

vector = requests.post(
    OLLAMA_URL_EMBED, json={"model": EMBED_MODEL, "prompt": pregunta_ejemplo}
).json()["embedding"]

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()
cur.execute(
    "INSERT INTO rag_memoria (pregunta, query_sql, embedding) VALUES (%s, %s, %s);",
    (pregunta_ejemplo, sql_ejemplo, vector),
)
conn.commit()
cur.close()
conn.close()
print("patron de filtrado por meses inyectado")
