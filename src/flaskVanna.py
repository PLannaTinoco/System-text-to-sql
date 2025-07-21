from runpy import run_path
from vanna.remote import VannaDefault
from vanna.flask import VannaFlaskApp
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import logging
import json

# Configuração do log para visualizar cada etapa
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logging.info("Carregando variáveis de ambiente...")
load_dotenv(override=True)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
API_KEY = os.getenv("API_KEY")

logging.info("Criando objeto VannaDefault...")
vn = VannaDefault(model="jarves", api_key=API_KEY)

logging.info("Conectando ao banco PostgreSQL...")
response = vn.connect_to_postgres(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)
logging.info(f"Resposta da conexão: {response}")

logging.info("Executando consulta para obter dados da tabela_marketing...")
try:
    result = vn.run_sql("SELECT * FROM tabela_marketing LIMIT 10;")
    print(result)
except Exception as e:
    logging.error(f"Erro ao executar SQL: {e}")

# Adicionando dados de treinamento corretamente

# #! função adicionar backup JSON
# logging.info("Adicionando dados de treinamento a partir do backup JSON…")
# backup_path = os.path.join(os.path.dirname(__file__), "arq", "backup.json")
# if os.path.isfile(backup_path):
#     with open(backup_path, "r", encoding="utf-8") as f:
#         treinos = json.load(f)
#     for item in treinos:
#         # só SQL
#         if item.get("training_data_type") != "sql":
#             continue
#         pergunta = (item.get("question") or "").strip()
#         sql       = (item.get("content")  or "").strip()
#         if not pergunta or not sql:
#             continue
#         try:
#             vn.train(question=pergunta, sql=sql)
#             logging.info("Treinado: %s", pergunta)
#         except Exception as e:
#             logging.error("Falha ao treinar '%s': %s", pergunta, e)
# else:
#     logging.warning("Backup JSON não encontrado: %s", backup_path)

# logging.info("Listando dados de treinamento...")
# training_data = vn.get_training_data()
# print(training_data)


logging.info("==== Iniciando Vanna Flask App ====")
VannaFlaskApp(vn, allow_llm_to_see_data=True).run()

#! função para remover todos os data training 
# # Para cada item, remove pelo id

# # Supondo que vn é sua instância VannaDefault já autenticada

# training_data = vn.get_training_data()
# print(training_data)

# # Se for DataFrame (caso mais comum com Vanna)
# try:
#     ids = training_data["id"].tolist()
# except (AttributeError, KeyError, TypeError):
#     # Fallback para outros formatos
#     if isinstance(training_data, list):
#         if training_data and isinstance(training_data[0], dict):
#             ids = [item["id"] for item in training_data if "id" in item]
#         else:
#             ids = list(training_data)
#     elif isinstance(training_data, dict):
#         ids = [training_data["id"]]
#     else:
#         ids = []

# print(f"Total de IDs encontrados no modelo: {len(ids)}")
# print("IDs:", ids)

# for item_id in ids:
#     try:
#         vn.remove_training_data(id=item_id)
#         print(f"Removido: {item_id}")
#     except Exception as e:
#         print(f"Erro ao remover {item_id}: {e}")


# Salvando dados treinados em um arquivo JSON
logging.info("Salvando dados treinados em arquivo...")
training_data = vn.get_training_data()  # Atualiza
training_data_dict = training_data.to_dict(orient="records")

# #função que remove por id o trainign data de acordo com o arq/dados_treinados.json

training_data_dict = training_data.to_dict(orient="records")
os.makedirs("arq", exist_ok=True)
file = os.path.join("arq", "dados_treinados.json")
with open(file, "w", encoding="utf-8") as f:
    json.dump(training_data_dict, f, indent=4, ensure_ascii=False)
logging.info("Arquivo de dados treinados salvo em: %s", file)


logging.info("Arquivo 'dados_treinados.json' criado com sucesso!")
logging.info("==== Vanna Flask App - Encerrado ====")



