import psycopg2

DB_CONFIG = {
    "dbname": "chicago_crime_db",
    "user": "postgres",
    "password": "palta123",
    "host": "localhost",
    "port": "5432",
}

sql_corregido = "SELECT COUNT(*) FROM crimes WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(-87.62, 41.87), 4326)::geography, 500);"

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE rag_memoria 
        SET query_sql = %s 
        WHERE pregunta LIKE '%%500 metros%%';
    """,
        (sql_corregido,),
    )

    conn.commit()
    print("¡Memoria ST-RAG actualizada con éxito!")
    print(f"Nuevo contexto: {sql_corregido}")

except Exception as e:
    print(f"Error: {e}")
finally:
    if "cur" in locals():
        cur.close()
    if "conn" in locals():
        conn.close()
