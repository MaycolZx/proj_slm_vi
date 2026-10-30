#!/bin/bash

# Comprobamos si tenemos posgresql
psql --version
sudo service postgresql status

sudo -u postgres createdb crime_analytics

pg_lsclusters
pg_isready

sudo -u postgres psql -d crime_analytics -c "SELECT current_database(), current_setting('server_version');"

#Creamos las tablas para el Schema RAG

sudo -u postgres psql -d crime_analytics -v ON_ERROR_STOP=1 <<'SQL'
CREATE SCHEMA IF NOT EXISTS chicago;
CREATE SCHEMA IF NOT EXISTS nyc;
CREATE SCHEMA IF NOT EXISTS catalog;
CREATE SCHEMA IF NOT EXISTS research;

SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('chicago', 'nyc', 'catalog', 'research')
ORDER BY schema_name;

SQL

python -m pytest -q data_ingestion_v01/tests

udo -u postgres psql -X -d crime_analytics \
  -v ON_ERROR_STOP=1 \
  -v owner_role="$USER" \
  -f data_ingestion_v01/sql/setup_roles.sql

python -m data_ingestion_v01.cli bootstrap

python -m data_ingestion_v01.cli verify

# Ingestion de datos 100 registros

python -m data_ingestion_v01.cli fetch \
  --source all \
  --start 2023-01-01 \
  --end 2023-01-08 \
  --max-rows 200 \
  --page-size 100 \
  --timeout 180 \
  --retries 2

# Pruebas de validacin

python -m data_ingestion_v01.cli check \
  --manifest data_ingestion_v01/data/chicago_2023-01-01_2023-01-08_max200.manifest.json

python -m data_ingestion_v01.cli load \
  --manifest data_ingestion_v01/data/chicago_2023-01-01_2023-01-08_max200.manifest.json \
  --dry-run

# Validamos el ingresta de datos de NY 
python -m data_ingestion_v01.cli check \
  --manifest data_ingestion_v01/data/nyc_2023-01-01_2023-01-08_max200.manifest.json
# ahora comprobamos la carga simulada 
python -m data_ingestion_v01.cli load \
  --manifest data_ingestion_v01/data/nyc_2023-01-01_2023-01-08_max200.manifest.json \
  --dry-run

# CARGAS REALES:
python -m data_ingestion_v01.cli load \
  --manifest data_ingestion_v01/data/chicago_2023-01-01_2023-01-08_max200.manifest.json
python -m data_ingestion_v01.cli load \
  --manifest data_ingestion_v01/data/nyc_2023-01-01_2023-01-08_max200.manifest.json

# Verificar que los datos esten almacenados

python -m data_ingestion_v01.cli verify


