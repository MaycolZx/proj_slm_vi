import pandas as pd
from sqlalchemy import create_engine
import time

archivo_csv = "./Crimes_CHICAGO.csv"
chunk_size = 100000
db_url = "postgresql://postgres:palta123@localhost:5432/chicago_crime_db"
engine = create_engine(db_url)

# print("Iniciando el procesamiento del dataset de Chicago Crime...")
start_time = time.time()
filas_procesadas = 0

for chunk in pd.read_csv(archivo_csv, chunksize=chunk_size, low_memory=False):
    chunk = chunk.dropna(subset=["Latitude", "Longitude"])
    chunk.columns = [col.lower().replace(" ", "_") for col in chunk.columns]
    chunk.to_sql("crimes", engine, if_exists="append", index=False)
    filas_procesadas += len(chunk)
    print(f"Lote procesado. Filas totales insertadas: {filas_procesadas}...")

end_time = time.time()
print(f"\nProcesamiento completo en {round((end_time - start_time)/60, 2)} minutos!")
print(f"Total de crimenes con coordenadas validas insertados: {filas_procesadas}")
