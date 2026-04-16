import pandas as pd
from sqlalchemy import create_engine

# conexão com PostgreSQL
engine = create_engine('postgresql://postgres:masterkey@localhost:5432/uberdataset')

# =========================
# 1. EXTRAÇÃO
# =========================
arquivo_csv = 'UberDataset.csv'  # troque pelo nome do seu arquivo
df = pd.read_csv(arquivo_csv)

# =========================
# 2. TRANSFORMAÇÃO
# =========================

# padroniza nomes das colunas
df.columns = [col.strip().upper() for col in df.columns]

# converte datas
df['START_DATE'] = pd.to_datetime(df['START_DATE'], format='%m-%d-%Y %H:%M', errors='coerce')
df['END_DATE'] = pd.to_datetime(df['END_DATE'], format='%m-%d-%Y %H:%M', errors='coerce')

# remove linhas com datas inválidas
df = df.dropna(subset=['START_DATE', 'END_DATE'])

# trata valores ausentes
df['CATEGORY'] = df['CATEGORY'].fillna('Unknown')
df['START'] = df['START'].fillna('Unknown')
df['STOP'] = df['STOP'].fillna('Unknown')
df['PURPOSE'] = df['PURPOSE'].fillna('Sem propósito informado')

# converte miles para número
df['MILES'] = pd.to_numeric(df['MILES'], errors='coerce')
df = df.dropna(subset=['MILES'])

# remove valores negativos ou inconsistentes
df = df[df['MILES'] >= 0]

# calcula duração em minutos
df['DURACAO_MIN'] = (df['END_DATE'] - df['START_DATE']).dt.total_seconds() / 60

# remove durações inválidas
df = df[df['DURACAO_MIN'] >= 0]

# =========================
# 3. CRIAÇÃO DAS DIMENSÕES
# =========================

# DIM_DATA_INICIO
dim_data_inicio = df[['START_DATE']].drop_duplicates().reset_index(drop=True)
dim_data_inicio.columns = ['data_hora']
dim_data_inicio['data'] = dim_data_inicio['data_hora'].dt.date
dim_data_inicio['dia'] = dim_data_inicio['data_hora'].dt.day
dim_data_inicio['mes'] = dim_data_inicio['data_hora'].dt.month
dim_data_inicio['ano'] = dim_data_inicio['data_hora'].dt.year
dim_data_inicio['hora'] = dim_data_inicio['data_hora'].dt.hour
dim_data_inicio['dia_semana'] = dim_data_inicio['data_hora'].dt.day_name()
dim_data_inicio['fim_de_semana'] = dim_data_inicio['data_hora'].dt.weekday >= 5
dim_data_inicio.index.name = 'id_data_inicio'
dim_data_inicio = dim_data_inicio.reset_index()

# DIM_DATA_FIM
dim_data_fim = df[['END_DATE']].drop_duplicates().reset_index(drop=True)
dim_data_fim.columns = ['data_hora']
dim_data_fim['data'] = dim_data_fim['data_hora'].dt.date
dim_data_fim['dia'] = dim_data_fim['data_hora'].dt.day
dim_data_fim['mes'] = dim_data_fim['data_hora'].dt.month
dim_data_fim['ano'] = dim_data_fim['data_hora'].dt.year
dim_data_fim['hora'] = dim_data_fim['data_hora'].dt.hour
dim_data_fim['dia_semana'] = dim_data_fim['data_hora'].dt.day_name()
dim_data_fim['fim_de_semana'] = dim_data_fim['data_hora'].dt.weekday >= 5
dim_data_fim.index.name = 'id_data_fim'
dim_data_fim = dim_data_fim.reset_index()

# DIM_CATEGORIA
dim_categoria = df[['CATEGORY']].drop_duplicates().reset_index(drop=True)
dim_categoria.columns = ['categoria']
dim_categoria.index.name = 'id_categoria'
dim_categoria = dim_categoria.reset_index()

# DIM_LOCAL_INICIO
dim_local_inicio = df[['START']].drop_duplicates().reset_index(drop=True)
dim_local_inicio.columns = ['local_inicio']
dim_local_inicio.index.name = 'id_local_inicio'
dim_local_inicio = dim_local_inicio.reset_index()

# DIM_LOCAL_FIM
dim_local_fim = df[['STOP']].drop_duplicates().reset_index(drop=True)
dim_local_fim.columns = ['local_fim']
dim_local_fim.index.name = 'id_local_fim'
dim_local_fim = dim_local_fim.reset_index()

# DIM_PURPOSE
dim_purpose = df[['PURPOSE']].drop_duplicates().reset_index(drop=True)
dim_purpose.columns = ['purpose']
dim_purpose.index.name = 'id_purpose'
dim_purpose = dim_purpose.reset_index()

# =========================
# 4. CRIAÇÃO DA TABELA FATO
# =========================

fato = df.merge(dim_data_inicio, left_on='START_DATE', right_on='data_hora') \
         .merge(dim_data_fim, left_on='END_DATE', right_on='data_hora') \
         .merge(dim_categoria, left_on='CATEGORY', right_on='categoria') \
         .merge(dim_local_inicio, left_on='START', right_on='local_inicio') \
         .merge(dim_local_fim, left_on='STOP', right_on='local_fim') \
         .merge(dim_purpose, left_on='PURPOSE', right_on='purpose')

fato_viagem = fato[
    [
        'id_data_inicio',
        'id_data_fim',
        'id_categoria',
        'id_local_inicio',
        'id_local_fim',
        'id_purpose',
        'MILES',
        'DURACAO_MIN'
    ]
].copy()

fato_viagem.columns = [
    'id_data_inicio',
    'id_data_fim',
    'id_categoria',
    'id_local_inicio',
    'id_local_fim',
    'id_purpose',
    'miles',
    'duracao_min'
]

fato_viagem.index.name = 'id_viagem'
fato_viagem = fato_viagem.reset_index()

# =========================
# 5. CARGA NO POSTGRESQL
# =========================

dim_data_inicio.to_sql('dim_data_inicio', engine, if_exists='replace', index=False)
dim_data_fim.to_sql('dim_data_fim', engine, if_exists='replace', index=False)
dim_categoria.to_sql('dim_categoria', engine, if_exists='replace', index=False)
dim_local_inicio.to_sql('dim_local_inicio', engine, if_exists='replace', index=False)
dim_local_fim.to_sql('dim_local_fim', engine, if_exists='replace', index=False)
dim_purpose.to_sql('dim_purpose', engine, if_exists='replace', index=False)
fato_viagem.to_sql('fato_viagem', engine, if_exists='replace', index=False)

print("ETL concluído com sucesso e Data Warehouse carregado!")