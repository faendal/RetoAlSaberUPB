import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def clasificar_curso(nombre: str) -> str:
    nombre = str(nombre).upper()
    if "LECTURA" in nombre:
        return "Lectura Crítica"
    if "RAZONAMIENTO" in nombre or "CUANTITATIVO" in nombre:
        return "Razonamiento Cuantitativo"
    if "CIUDADANAS" in nombre or "COMPETENCIA" in nombre:
        return "Competencias Ciudadanas"
    return "Otro"


def procesar_reto_saber() -> pd.DataFrame:
    archivos_reto = sorted(RAW_DIR.glob("REPORTE RETO SABER*.xlsx"))
    if not archivos_reto:
        raise FileNotFoundError(
            f"No se encontraron archivos 'REPORTE RETO SABER*.xlsx' en {RAW_DIR}"
        )

    df_reto = pd.concat([pd.read_excel(f) for f in archivos_reto], ignore_index=True)
    df_reto.columns = df_reto.columns.str.strip()

    # Reparación de notas (comas a puntos y conversión numérica)
    df_reto["NOTA_HISTORIA"] = (
        df_reto["NOTA_HISTORIA"].astype(str).str.replace(",", ".", regex=False)
    )
    df_reto["NOTA_HISTORIA"] = pd.to_numeric(
        df_reto["NOTA_HISTORIA"], errors="coerce"
    ).fillna(0)

    # Clasificación y filtrado de los 3 módulos obligatorios
    df_reto["TÍTULO_MAP"] = df_reto["TÍTULO"].apply(clasificar_curso)
    df_reto = df_reto[df_reto["TÍTULO_MAP"] != "Otro"]

    # Agrupación por estudiante y curso
    df_agg = (
        df_reto.groupby(["ID_ESTUDIANTE", "NOMBRE", "TÍTULO_MAP"])["NOTA_HISTORIA"]
        .agg(Puntaje_Max="max", Intentos="count")
        .reset_index()
    )

    # Pivoteo a formato de una fila por estudiante
    df_pivot = df_agg.pivot_table(
        index=["ID_ESTUDIANTE", "NOMBRE"],
        columns="TÍTULO_MAP",
        values=["Puntaje_Max", "Intentos"],
        fill_value=0,
    )

    df_pivot.columns = [
        f"{'Nota' if col[0] == 'Puntaje_Max' else 'Intentos'} {col[1]}"
        for col in df_pivot.columns
    ]
    df_pivot = df_pivot.reset_index()

    cursos = ["Lectura Crítica", "Razonamiento Cuantitativo", "Competencias Ciudadanas"]
    for c in cursos:
        if f"Nota {c}" not in df_pivot.columns:
            df_pivot[f"Nota {c}"] = 0
        if f"Intentos {c}" not in df_pivot.columns:
            df_pivot[f"Intentos {c}"] = 0

    col_orden = ["ID_ESTUDIANTE", "NOMBRE"]
    for c in cursos:
        col_orden.extend([f"Nota {c}", f"Intentos {c}"])
    df_pivot = df_pivot[col_orden]

    # Cálculo de cursos ganados (> 3.0) y Estado final (>= 2 cursos)
    df_pivot["Cursos Ganados"] = (
        (df_pivot["Nota Lectura Crítica"] > 3.0).astype(int)
        + (df_pivot["Nota Razonamiento Cuantitativo"] > 3.0).astype(int)
        + (df_pivot["Nota Competencias Ciudadanas"] > 3.0).astype(int)
    )
    df_pivot["Estado"] = np.where(
        df_pivot["Cursos Ganados"] >= 2, "Aprobado", "No Aprobado"
    )

    df_pivot = df_pivot.rename(columns={"ID_ESTUDIANTE": "Id", "NOMBRE": "Nombre"})

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DIR / "REPORTE_FINAL_RETO_SABER.xlsx"
    df_pivot.to_excel(output_path, index=False, engine="openpyxl")
    return df_pivot


def procesar_autodiagnostica() -> pd.DataFrame:
    archivos_auto = sorted(RAW_DIR.glob("REPORTE AUTODIAGNOSTICA*.xlsx"))
    if not archivos_auto:
        raise FileNotFoundError(
            f"No se encontraron archivos 'REPORTE AUTODIAGNOSTICA*.xlsx' en {RAW_DIR}"
        )

    df_auto = pd.concat([pd.read_excel(f) for f in archivos_auto], ignore_index=True)
    df_auto.columns = df_auto.columns.str.strip()

    # Reparación de puntajes
    df_auto["PUNTAJE"] = (
        df_auto["PUNTAJE"].astype(str).str.replace(",", ".", regex=False)
    )
    df_auto["PUNTAJE"] = pd.to_numeric(df_auto["PUNTAJE"], errors="coerce").fillna(0)

    df_auto_agg = (
        df_auto.groupby(["PIDM", "NOMBRE_ESTUDIANTE"])["PUNTAJE"]
        .agg(Puntaje_Max="max", Intentos="count")
        .reset_index()
    )

    df_auto_agg["Estado"] = np.where(
        df_auto_agg["Puntaje_Max"] > 4.0, "Aprobado", "No Aprobado"
    )
    df_auto_agg = df_auto_agg.rename(
        columns={"PIDM": "Id", "NOMBRE_ESTUDIANTE": "Nombre"}
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DIR / "REPORTE_FINAL_AUTODIAGNOSTICA.xlsx"
    df_auto_agg.to_excel(output_path, index=False, engine="openpyxl")
    return df_auto_agg


def ejecutar_etl():
    df_reto = procesar_reto_saber()
    df_auto = procesar_autodiagnostica()
    return df_reto, df_auto


if __name__ == "__main__":
    reto, auto = ejecutar_etl()
    print(
        f"ETL completado. Registros Reto al Saber: {len(reto)} | Autodiagnóstica: {len(auto)}"
    )
    print(f"Archivos guardados en: {PROCESSED_DIR}")
