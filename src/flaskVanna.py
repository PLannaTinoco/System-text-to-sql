from runpy import run_path
from vanna.remote import VannaDefault
from vanna.flask import VannaFlaskApp
import pandas as pd
import psycopg2
import os
import logging
import json
from dotenv import load_dotenv

# � [MIGRATION] Import do DatabaseManager
from database_manager import db_manager

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

# Função para adicionar DDL e Documentation do backup JSON
def adicionar_ddl_documentation_backup(vn, backup_path=None):
    """Adiciona dados de treinamento DDL e Documentation a partir do backup JSON"""
    
    logging.info("Adicionando DDL e Documentation a partir do backup JSON...")
    
    if not backup_path:
        backup_path = os.path.join(os.path.dirname(__file__), "arq", "backup.json")
    
    if not os.path.isfile(backup_path):
        logging.warning("Backup JSON não encontrado: %s", backup_path)
        return
    
    try:
        with open(backup_path, "r", encoding="utf-8") as f:
            treinos = json.load(f)
        
        ddl_count = 0
        doc_count = 0
        
        for item in treinos:
            training_type = item.get("training_data_type", "").lower()
            content = (item.get("content") or "").strip()
            
            # Pular se não for DDL nem Documentation
            if training_type not in ["ddl", "documentation"]:
                continue
            
            # Pular se não tiver conteúdo
            if not content:
                continue
            
            try:
                if training_type == "ddl":
                    # Treinar DDL (sem pergunta)
                    vn.train(ddl=content)
                    ddl_count += 1
                    logging.info("DDL treinado: %s", content[:50] + "..." if len(content) > 50 else content)
                    
                elif training_type == "documentation":
                    # Treinar Documentation (sem pergunta)
                    vn.train(documentation=content)
                    doc_count += 1
                    logging.info("Documentation treinado: %s", content[:50] + "..." if len(content) > 50 else content)
                    
            except Exception as e:
                logging.error("Falha ao treinar %s '%s': %s", training_type, content[:30], e)
        
        logging.info("Treinamento concluído - DDL: %d, Documentation: %d", ddl_count, doc_count)
        
    except Exception as e:
        logging.error("Erro ao processar backup JSON: %s", e)

# ADICIONANDO DDL e Documentation antes da aplicação Flask

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

# adicionar_ddl_documentation_backup(vn)

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

# Salvando dados treinados - 🔄 [MIGRATION] Refatorado para PostgreSQL
logging.info("💾 [DB] Salvando dados treinados no PostgreSQL...")
training_data = vn.get_training_data()  # Atualiza

# 🔄 [MIGRATION] Salva no PostgreSQL ao invés de arquivo JSON
try:
    training_data_dict = training_data.to_dict(orient="records")
    
    # Salva como dados globais (backup) no PostgreSQL
    success = db_manager.save_training_data(client_id=None, training_data=training_data_dict)
    
    if success:
        logging.info("✅ [DB] Dados de treinamento salvos no PostgreSQL como backup global")
    else:
        logging.error("❌ [DB] Falha ao salvar dados de treinamento no PostgreSQL")
    
except Exception as e:
    logging.error(f"❌ [DB] Erro ao salvar training data no PostgreSQL: {e}")

# 📁 [OLD] Código original comentado - manter por segurança
# training_data_dict = training_data.to_dict(orient="records")
# os.makedirs("arq", exist_ok=True)
# file = os.path.join("arq", "dados_treinados.json")
# with open(file, "w", encoding="utf-8") as f:
#     json.dump(training_data_dict, f, indent=4, ensure_ascii=False)
# logging.info("Arquivo de dados treinados salvo em: %s", file)

logging.info("✅ [DB] Training data salvo no PostgreSQL com sucesso!")
logging.info("==== Vanna Flask App - Encerrado ====")