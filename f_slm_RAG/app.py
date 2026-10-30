from flask import Flask, render_template, request, jsonify
import psycopg2
import requests
import pandas as pd
from keplergl import KeplerGl
import time

app = Flask(__name__)

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
- block (text)
- date (timestamp)
- latitude (double precision)
- longitude (double precision)
- geom (geometry, Point, 4326)
"""


def recuperar_contexto_rag(pregunta):
    vector = requests.post(
        OLLAMA_URL_EMBED, json={"model": EMBED_MODEL, "prompt": pregunta}
    ).json()["embedding"]
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        "SELECT query_sql FROM rag_memoria ORDER BY embedding <=> %s::vector LIMIT 1;",
        (vector,),
    )
    resultado = cur.fetchone()
    cur.close()
    conn.close()
    return resultado[0] if resultado else "No hay contexto previo."


def generar_sql(pregunta, contexto):
    prompt = f"""Eres un experto en bases de datos espaciales. Analiza la pregunta y genera código SQL puro.
REGLA 1 (Visualización Espacial): Si la pregunta pide mostrar incidentes, mapas o ubicaciones, devuelve SIEMPRE 'SELECT latitude, longitude FROM crimes'. NUNCA uses 'SELECT *'.
REGLA 2 (Visualización Analítica): Si pide rankings o conteos, usa consultas de agregación (ej. GROUP BY).
REGLA 3 (Filtro de Tiempo): Para buscar meses o años específicos, aplica la función exclusivamente sobre la columna 'date' convertida a fecha. Ejemplo obligatorio: EXTRACT(YEAR FROM date::date) = 2018 AND EXTRACT(MONTH FROM date::date) = 12. NUNCA apliques EXTRACT sobre textos sin usar ::date.

ESQUEMA: {ESQUEMA_DB}
EJEMPLO BASE: {contexto}
PREGUNTA: {pregunta}
SQL:"""

    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.0,
        "options": {"num_predict": 150},
    }
    respuesta_cruda = requests.post(OLLAMA_URL_GENERATE, json=payload).json()[
        "response"
    ]
    sql_limpio = (
        respuesta_cruda.split(";")[0] + ";"
        if ";" in respuesta_cruda
        else respuesta_cruda.strip()
    )
    return sql_limpio.replace("```sql", "").replace("```", "").strip()


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/analizar", methods=["POST"])
def analizar():
    data = request.json
    pregunta_usuario = data.get("pregunta", "")

    try:
        start_time = time.time()
        contexto_sql = recuperar_contexto_rag(pregunta_usuario)
        sql_generado = generar_sql(pregunta_usuario, contexto_sql)

        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(sql_generado)

        columnas = [desc[0] for desc in cur.description]
        resultados = cur.fetchall()
        cur.close()
        conn.close()

        if not resultados:
            return jsonify(
                {"status": "error", "mensaje": "La consulta no retorno datos."}
            )

        latencia = round(time.time() - start_time, 2)

        if "latitude" in columnas and "longitude" in columnas:
            df = pd.DataFrame(resultados, columns=columnas)
            config_kepler = {
                "version": "v1",
                "config": {
                    "visState": {
                        "layers": [
                            {
                                "type": "heatmap",
                                "config": {
                                    "dataId": "crimenes",
                                    "columns": {"lat": "latitude", "lng": "longitude"},
                                    "isVisible": True,
                                },
                            }
                        ]
                    }
                },
            }

            mapa = KeplerGl(height=600, data={"crimenes": df}, config=config_kepler)
            # html_mapa = mapa._repr_html_().decode("utf-8")
            html_mapa = mapa.get_html(center_map=True)

            muestra_datos = df.head(5).values.tolist()
            return jsonify(
                {
                    "status": "success",
                    "tipo": "mapa",
                    "latencia": latencia,
                    "sql": sql_generado,
                    "columnas": columnas,
                    "datos_crudos": muestra_datos,
                    "html": html_mapa,
                }
            )

        else:
            datos_tabla = resultados[:10]
            return jsonify(
                {
                    "status": "success",
                    "tipo": "tabla",
                    "latencia": latencia,
                    "sql": sql_generado,
                    "columnas": columnas,
                    "datos_crudos": datos_tabla,
                    "html": None,
                }
            )

    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)})


if __name__ == "__main__":
    # app.run(debug=True, host="127.0.0.1", port=5000)
    app.run(debug=True, host="100.104.162.95", port=5000)
