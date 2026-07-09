import pandas as pd

arquivo = 'dados_maio_2026_estacoes_geotecnicas.csv'
try:
    df = pd.read_csv(arquivo, encoding='utf-8-sig')
except FileNotFoundError:
    print(f"Arquivo não encontrado: {arquivo}")
    raise

# parse datetime
if 'datahora_recife' in df.columns:
    df['datahora_recife'] = pd.to_datetime(df['datahora_recife'], errors='coerce')
else:
    print("Coluna datahora_recife não encontrada no CSV.")
    raise SystemExit(1)

est_name = 'Barreira'
day = pd.Timestamp('2026-05-01').date()

mask_est = df['estacao_nome'].str.contains(est_name, case=False, na=False)
mask_day = df['datahora_recife'].dt.date == day

df_barreira_day = df[mask_est & mask_day].copy()

print(f"Registros para {est_name} em {day}: {len(df_barreira_day)}\n")
if df_barreira_day.empty:
    print('Nenhum registro encontrado.')
else:
    # mostrar dia inteiro
    print('--- Registros do dia (ordenados) ---')
    print(df_barreira_day.sort_values('datahora_recife').to_string(index=False))

    # filtrar hora 12:00
    df_barreira_12 = df_barreira_day[df_barreira_day['datahora_recife'].dt.hour == 12]
    print('\n--- Registros às 12:00 ---')
    if df_barreira_12.empty:
        print('Nenhum registro às 12:00')
    else:
        print(df_barreira_12.to_string(index=False))
