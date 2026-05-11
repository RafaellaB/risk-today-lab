import glob
import os
from datetime import datetime

import numpy as np
import pandas as pd


ARQUIVO_SAIDA = "historico_risco.csv"
ARQUIVO_MARE = os.path.join("tide", "mare_calculada_hora_em_hora_ano-completo.csv")
PREFIXO_CHUVA = "chuva_recife_"
URL_BASE_CHUVAS = "https://raw.githubusercontent.com/RafaellaB/risco-hoje/main/chuva_recife_"
SUFIXO_ARQUIVO_CHUVA = ".csv"
ESTACOES_DESEJADAS = ["Campina do Barreto", "Torreão", "RECIFE - APAC", "Imbiribeira", "Dois Irmãos"]
DATA_INICIO = pd.to_datetime("2026-05-01")


def carregar_mare_local(caminho_arquivo: str) -> pd.DataFrame:
    if not os.path.exists(caminho_arquivo):
        raise FileNotFoundError(f"Arquivo de maré não encontrado: {caminho_arquivo}")

    df_mare = pd.read_csv(caminho_arquivo, sep=";", decimal=",", encoding="utf-8")
    df_mare = df_mare.rename(columns={"Hora_Exata": "datahora", "Altura_m": "AM"})
    df_mare["datahora"] = pd.to_datetime(df_mare["datahora"], errors="coerce")
    df_mare = df_mare.dropna(subset=["datahora"])
    df_mare["data"] = df_mare["datahora"].dt.strftime("%Y-%m-%d")
    df_mare["hora_ref"] = df_mare["datahora"].dt.strftime("%H:00:00")
    df_mare["AM"] = pd.to_numeric(df_mare["AM"], errors="coerce")
    return df_mare[["data", "hora_ref", "AM"]]


def carregar_chuva_local(caminho_arquivo: str) -> pd.DataFrame:
    df = pd.read_csv(caminho_arquivo, encoding="utf-8", sep=",")
    df = df.rename(columns={"nome": "nomeEstacao", "valor": "valorMedida"})
    df["datahora"] = pd.to_datetime(df["datahora"], errors="coerce")
    df["valorMedida"] = pd.to_numeric(df["valorMedida"], errors="coerce")
    df = df.dropna(subset=["datahora", "valorMedida"])
    return df


def carregar_chuva_remota(data_str: str) -> pd.DataFrame:
    url = f"{URL_BASE_CHUVAS}{data_str}{SUFIXO_ARQUIVO_CHUVA}"
    try:
        df = pd.read_csv(url, encoding="utf-8", sep=",")
    except Exception:
        return pd.DataFrame()

    df = df.rename(columns={"nome": "nomeEstacao", "valor": "valorMedida"})
    df["datahora"] = pd.to_datetime(df["datahora"], errors="coerce")
    df["valorMedida"] = pd.to_numeric(df["valorMedida"], errors="coerce")
    df = df.dropna(subset=["datahora", "valorMedida"])
    return df


def processar_chuva_do_dia(df_chuva: pd.DataFrame, data_alvo: str) -> pd.DataFrame:
    df = df_chuva[df_chuva["nomeEstacao"].isin(ESTACOES_DESEJADAS)].copy()
    df["data"] = df["datahora"].dt.strftime("%Y-%m-%d")
    df = df[df["data"] == data_alvo]
    if df.empty:
        return pd.DataFrame()

    df = df.set_index("datahora").sort_index()
    resultados = []

    for estacao, grupo in df.groupby("nomeEstacao"):
        chuva_10min = grupo["valorMedida"].rolling("10min").sum()
        chuva_2h = grupo["valorMedida"].rolling("2h").sum()
        janela = pd.DataFrame({"chuva_10min": chuva_10min, "chuva_2h": chuva_2h})
        agregado_horario = janela.resample("h").last()
        agregado_horario["VP"] = (agregado_horario["chuva_10min"] * 6) + agregado_horario["chuva_2h"]
        agregado_horario["nomeEstacao"] = estacao
        resultados.append(agregado_horario)

    if not resultados:
        return pd.DataFrame()

    df_vp = pd.concat(resultados).reset_index()
    df_vp["data"] = df_vp["datahora"].dt.strftime("%Y-%m-%d")
    df_vp["hora_ref"] = df_vp["datahora"].dt.strftime("%H:00:00")
    return df_vp[["data", "hora_ref", "nomeEstacao", "VP"]]


def classificar_risco(valor: float) -> str:
    if valor <= 30:
        return "Baixo"
    if valor <= 50:
        return "Moderado"
    if valor <= 100:
        return "Moderado Alto"
    return "Alto"


def gerar_historico_local() -> pd.DataFrame:
    df_mare = carregar_mare_local(ARQUIVO_MARE)

    registros = []

    hoje = pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
    for data_arquivo in pd.date_range(DATA_INICIO, hoje, freq="D"):
        data_str = data_arquivo.strftime("%Y-%m-%d")
        df_chuva = carregar_chuva_remota(data_str)

        # Fallback opcional para execução local quando o CSV remoto ainda não existe.
        if df_chuva.empty:
            caminho_local = f"{PREFIXO_CHUVA}{data_str}.csv"
            if os.path.exists(caminho_local):
                df_chuva = carregar_chuva_local(caminho_local)

        if df_chuva.empty:
            continue

        df_vp = processar_chuva_do_dia(df_chuva, data_str)
        if df_vp.empty:
            continue

        df_mesclado = pd.merge(df_vp, df_mare, on=["data", "hora_ref"], how="left")
        df_mesclado["AM_real"] = df_mesclado["AM"]
        df_mesclado["AM_calc"] = df_mesclado["AM_real"]
        df_mesclado.loc[df_mesclado["AM_calc"].notna() & (df_mesclado["AM_calc"] < 1), "AM_calc"] = 1
        df_mesclado["Nivel_Risco_Valor"] = (df_mesclado["VP"] * df_mesclado["AM_calc"]).round(2)
        df_mesclado["Classificacao_Risco"] = df_mesclado["Nivel_Risco_Valor"].apply(classificar_risco)
        registros.append(
            df_mesclado[[
                "data",
                "hora_ref",
                "nomeEstacao",
                "VP",
                "AM_real",
                "AM_calc",
                "Nivel_Risco_Valor",
                "Classificacao_Risco",
            ]]
        )

    if not registros:
        return pd.DataFrame(columns=["data", "hora_ref", "nomeEstacao", "VP", "AM_real", "AM_calc", "Nivel_Risco_Valor", "Classificacao_Risco"])

    df_final = pd.concat(registros, ignore_index=True)
    df_final.drop_duplicates(subset=["data", "hora_ref", "nomeEstacao"], keep="last", inplace=True)
    df_final.sort_values(["data", "hora_ref", "nomeEstacao"], ascending=[False, False, True], inplace=True)
    return df_final


def main():
    df_historico = gerar_historico_local()
    df_historico.to_csv(ARQUIVO_SAIDA, index=False)
    print(f"✅ Historico atualizado em {ARQUIVO_SAIDA} com {len(df_historico)} registros.")


if __name__ == "__main__":
    main()