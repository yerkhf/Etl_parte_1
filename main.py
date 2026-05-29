import re
import sqlite3
import tempfile
from datetime import datetime, date

import pandas as pd
import streamlit as st


def limpiar_nombre(nombre):
    return re.sub(r"^\d+\.\s*", "", str(nombre)).strip()


def leer_archivo_texto(archivo):
    try:
        return archivo.read().decode("utf-8").splitlines()
    except UnicodeDecodeError:
        archivo.seek(0)
        return archivo.read().decode("latin-1").splitlines()


def detectar_fecha(fecha_texto):
    fecha_texto = str(fecha_texto).strip().lower()

    if "a.c" in fecha_texto or "alrededor" in fecha_texto:
        return None

    fecha_texto = fecha_texto.replace("/", "-")

    formatos = [
        "%Y-%m-%d",
        "%d-%m-%Y"
    ]

    for formato in formatos:
        try:
            return datetime.strptime(fecha_texto, formato).date()
        except ValueError:
            continue

    return None


def calcular_edad(fecha_nacimiento):
    hoy = date.today()
    edad = hoy.year - fecha_nacimiento.year

    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1

    return edad


def cumple_hoy(fecha_nacimiento):
    hoy = date.today()
    return "SI" if hoy.month == fecha_nacimiento.month and hoy.day == fecha_nacimiento.day else "NO"


def procesar_famosos(archivo):
    lineas = leer_archivo_texto(archivo)
    registros = []
    invalidos = []

    for linea in lineas:
        linea = linea.strip()

        if not linea:
            continue

        partes = linea.split(" - ", 1)

        if len(partes) != 2:
            invalidos.append({"linea": linea, "motivo": "No contiene separador válido ' - '"})
            continue

        nombre = limpiar_nombre(partes[0])
        fecha_original = partes[1].strip()
        fecha = detectar_fecha(fecha_original)

        if fecha is None:
            invalidos.append({"linea": linea, "motivo": "Fecha inválida o no convertible"})
            continue

        registros.append({
            "nombre": nombre,
            "fecha_nacimiento": str(fecha),
            "fecha_formato_chile": fecha.strftime("%d-%m-%Y"),
            "edad": calcular_edad(fecha),
            "cumple_hoy": cumple_hoy(fecha)
        })

    df = pd.DataFrame(registros)

    if not df.empty:
        df = df.drop_duplicates(subset=["nombre", "fecha_nacimiento"])
        df = df.sort_values(by="nombre").reset_index(drop=True)

    df_invalidos = pd.DataFrame(invalidos)

    return df, df_invalidos


def crear_sqlite(df):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        ruta_db = tmp.name

    conexion = sqlite3.connect(ruta_db)
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE famosos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            fecha_nacimiento TEXT NOT NULL,
            fecha_formato_chile TEXT NOT NULL,
            edad INTEGER NOT NULL,
            cumple_hoy TEXT NOT NULL
        );
    """)

    df.to_sql("famosos", conexion, if_exists="append", index=False)

    conexion.commit()
    conexion.close()

    with open(ruta_db, "rb") as archivo_db:
        return archivo_db.read()


st.set_page_config(
    page_title="ETL Parte I - Famosos",
    layout="wide"
)

st.title("ETL Parte I - Normalización de Famosos")
st.write("Carga un archivo con formato general: `Nombre - fecha`.")

archivo = st.file_uploader(
    "Subir archivo TXT",
    type=["txt", "TXT"]
)

if archivo is not None:
    if st.button("Procesar ETL"):
        df, df_invalidos = procesar_famosos(archivo)

        if df.empty:
            st.error("No se encontraron registros válidos.")
        else:
            st.success(f"Proceso ETL finalizado. Registros normalizados: {len(df)}")

            st.subheader("Tabla final normalizada")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            db = crear_sqlite(df)

            st.download_button(
                "Descargar CSV normalizado",
                data=csv,
                file_name="famosos_normalizados.csv",
                mime="text/csv"
            )

            st.download_button(
                "Descargar base de datos SQLite",
                data=db,
                file_name="famosos.db",
                mime="application/octet-stream"
            )

        if not df_invalidos.empty:
            st.subheader("Registros descartados")
            st.dataframe(df_invalidos, use_container_width=True)

            csv_invalidos = df_invalidos.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

            st.download_button(
                "Descargar registros descartados",
                data=csv_invalidos,
                file_name="famosos_registros_descartados.csv",
                mime="text/csv"
            )