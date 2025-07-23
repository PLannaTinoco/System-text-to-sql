import os
import pandas as pd
import psycopg2
import datetime
import logging
import sys
from dotenv import load_dotenv

# 🔧 [LOGGING] Configuração de logging para Render
def setup_render_logging():
    """Configura logging para ser visível no Render"""
    logger = logging.getLogger('soliris_import')
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - SOLIRIS-IMPORT - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    return logger

# Inicializar logger
render_logger = setup_render_logging()

load_dotenv()
render_logger.info("🔧 [ENV] Variáveis de ambiente carregadas para import_csv")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Sugestões de chaves primárias (comentadas) para documentação
PK_SUGGESTIONS = {
    "olist_orders_dataset": ["order_id"],  # PK: order_id
    "olist_order_items_dataset": ["order_id", "order_item_id"],  # Composite PK: (order_id, order_item_id)
    "olist_order_payments_dataset": ["order_id", "payment_sequential"],  # Composite PK: (order_id, payment_sequential)
    "olist_order_reviews_dataset": ["review_id"],  # PK: review_id
    "olist_customers_dataset": ["customer_id"],  # PK: customer_id
    "olist_products_dataset": ["product_id"],  # PK: product_id
    "olist_sellers_dataset": ["seller_id"],  # PK: seller_id
    "product_category_name_translation": ["product_category_name"]  # PK: product_category_name
}

TABLE_PREFIX = "cli02_"

def conectar_banco():
    render_logger.info("🔌 [DB] Conectando ao banco PostgreSQL para import")
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        render_logger.info("✅ [DB] Conexão estabelecida com sucesso")
        return conn
    except Exception as e:
        render_logger.error(f"❌ [DB] Erro ao conectar: {e}")
        raise

def criar_tabela_automatica(nome_tabela: str, df: pd.DataFrame):
    """
    Cria tabela no Postgres usando o nome e colunas de df.
    Mantém nomes originais de colunas para preservar JOINs.
    """
    render_logger.info(f"🏗️ [TABLE] Criando tabela: {nome_tabela}")
    conn = conectar_banco()
    cursor = conn.cursor()

    col_defs = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        if dtype.startswith("datetime64"):
            # detecta apenas data ou timestamp
            if (df[col].dt.time == datetime.time(0, 0)).all():
                sql_type = "DATE"
            else:
                sql_type = "TIMESTAMP"
        else:
            map_tipo = {
                "int64": "INTEGER",
                "float64": "DECIMAL(18,6)",
                "bool": "BOOLEAN",
                "object": "TEXT"
            }
            sql_type = map_tipo.get(dtype, "TEXT")
        # preserva nome exato da coluna
        col_defs.append(f'"{col}" {sql_type}')

    # monta lista de linhas (colunas + comentário de PK)
    items = col_defs.copy()
    pk = PK_SUGGESTIONS.get(nome_tabela)
    if pk:
        if isinstance(pk, (list, tuple)):
            cols = '", "'.join(pk)
        else:
            cols = pk
        items.append(f'-- SUGESTÃO PK: PRIMARY KEY ("{cols}")')

    # gera DDL sem vírgula sobrando
    ddl = (
        f'CREATE TABLE IF NOT EXISTS "{nome_tabela}" (\n  '
        + ",\n  ".join(items)
        + "\n);"
    )

    logging.info("Executando DDL para %s:\n%s", nome_tabela, ddl)
    render_logger.info(f"📝 [DDL] Executando DDL para tabela {nome_tabela}")
    cursor.execute(ddl)
    conn.commit()
    logging.info("Tabela '%s' criada com sucesso.", nome_tabela)
    render_logger.info(f"✅ [TABLE] Tabela {nome_tabela} criada com {len(df.columns)} colunas")
    cursor.close()
    conn.close()

def inserir_dados(nome_tabela, df: pd.DataFrame):
    """
    Insere linhas de df na tabela nome_tabela.
    Usa placeholders para evitar SQL injection.
    """
    conn = conectar_banco()
    cursor = conn.cursor()

    cols = ', '.join(f'"{c}"' for c in df.columns)
    placeholders = ', '.join(['%s'] * len(df.columns))
    insert_sql = f'INSERT INTO "{nome_tabela}" ({cols}) VALUES ({placeholders});'

    for _, row in df.iterrows():
        # converte NaN/NaT em None para virar NULL no Postgres
        vals = [None if pd.isna(v) else v for v in row.values]
        cursor.execute(insert_sql, tuple(vals))

    conn.commit()
    cursor.close()
    conn.close()

def processar_csv_para_banco(caminho_csv: str, nome_tabela: str):
    """
    Lê CSV, converte colunas object para datetime quando possível,
    cria tabela e popula dados.
    """
    logging.info("Processando %s → tabela %s", caminho_csv, nome_tabela)
    df = pd.read_csv(caminho_csv, low_memory=False)

    # tenta converter strings para datetime
    for col in df.select_dtypes(include=["object"]).columns:
        try:
            df[col] = pd.to_datetime(df[col])
            logging.info("Coluna %s convertida para datetime", col)
        except (ValueError, TypeError):
            pass

    criar_tabela_automatica(nome_tabela, df)
    logging.info("Preparando inserção de dados na tabela %s …", nome_tabela)
    inserir_dados(nome_tabela, df)
    logging.info("Inseridos %d registros em %s.", len(df), nome_tabela)

def processar_csv_para_banco_usuario(caminho_csv: str, nome_base: str, id_client: int):
    """
    Versão específica para usuários que adiciona prefixo automaticamente
    """
    nome_tabela = f"cli{id_client:02d}_{nome_base}"
    return processar_csv_para_banco(caminho_csv, nome_tabela)

# def importar_todas_planilhas_olist():
#     """
#     Importa automaticamente todas as planilhas CSV da Olist
#     em /home/lanna/Estudos/2025-1/Soliris/Planilhas/DadosAvancados.
#     """
#     base_dir = "/home/lanna/Estudos/2025-1/Soliris/Planilhas/DadosAvancados"
#     if not os.path.isdir(base_dir):
#         raise FileNotFoundError(f"Diretório não encontrado: {base_dir}")

#     for fname in sorted(os.listdir(base_dir)):
#         if fname.lower().endswith(".csv"):
#             caminho = os.path.join(base_dir, fname)
#             # aplica prefixo "cli02_" ao nome da tabela
#             base = os.path.splitext(fname)[0]
#             nome_tabela = f"{TABLE_PREFIX}{base}"
#             processar_csv_para_banco(caminho, nome_tabela)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

