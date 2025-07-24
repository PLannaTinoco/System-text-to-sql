from typing import Any, Dict, Optional
import os
import json
import logging
import sys
from runpy import run_path
from datetime import datetime
from dotenv import load_dotenv
import requests
import pandas as pd

from vanna.remote import VannaDefault
 # ou ajuste conforme o import correto
import psycopg2
from gerarDDL import gerar_ddl_para_cliente

from gerar_schema_cliente import gerar_plan_treinamento
from kpis_Setup import (
    conectar_postgres,
    criar_tabela_kpis,
    processar_csv,
    criar_kpis_automatico,
    gerar_schema_json,
    fetch_kpis
)

# 🔧 [MIGRATION] Import do DatabaseManager para persistência PostgreSQL
from database_manager import db_manager

# 🔧 [LOGGING] Configuração de logging para Render
def setup_render_logging():
    """Configura logging para ser visível no Render"""
    logger = logging.getLogger('soliris_core')
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - SOLIRIS-CORE - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    return logger

# Inicializar logger
render_logger = setup_render_logging()

 # ajuste o import conforme necessário
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
API_KEY = os.getenv("API_KEY")

render_logger.info("🔧 [ENV] Variáveis de ambiente carregadas")

# Monkey patch para timeout global
_original_post = requests.post
def _patched_post(*args, **kwargs):
    if "timeout" not in kwargs:
        kwargs["timeout"] = 120  # segundos
    return _original_post(*args, **kwargs)
requests.post = _patched_post

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
# filepath: src/app.py
def get_abs_path(*path_parts) -> str:
    """
    Retorna um caminho absoluto seguro baseado na raiz do vanna_core.py,
    mesmo que o script esteja sendo executado de outro diretório.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))  # src/
    return os.path.join(base_dir, *path_parts)

# 🔧 [NEW] Configuração para PostgreSQL - DatabaseManager importado diretamente
# Constantes antigas de JSON removidas após migração para PostgreSQL

def get_training_data_ids(vn: VannaDefault) -> list[int]:
    """
    Obtém os IDs dos dados de treinamento atuais do modelo Vanna.

    Args:
        vn (VannaDefault): Instância do modelo Vanna.

    Returns:
        list[str]: Lista de IDs dos dados de treinamento.
    """
    training_data = vn.get_training_data()
    if training_data is None:
        return []
    return training_data["id"].tolist()


def salvar_training_filtrado(vn, client_id):
    """
    🔄 [MIGRATION] Refatorada para usar PostgreSQL
    Salva training_data filtrado (novos dados da sessão) no banco
    """
    render_logger.info(f"💾 [DB] Salvando training_data filtrado para cliente {client_id}")
    
    try:
        # 🔧 [NEW] Carrega dados de backup do PostgreSQL (dados globais)
        backup_data = db_manager.load_training_data(client_id=None)  # client_id=None = dados globais
        ids_backup = {item["id"] for item in backup_data if isinstance(item, dict) and "id" in item}
        render_logger.info(f"📋 [DB] {len(ids_backup)} IDs no backup PostgreSQL")

        # Obtém dados atuais do modelo Vanna
        training_data = vn.get_training_data()
        if training_data is None or training_data.empty:
            render_logger.info("ℹ️ [DB] Nenhum training_data no modelo para salvar")
            return
            
        # Filtra apenas dados novos (não estão no backup)
        filtrados_df = training_data[~training_data["id"].isin(ids_backup)]
        filtrados = filtrados_df.to_dict(orient="records")
        
        if not filtrados:
            render_logger.info("ℹ️ [DB] Nenhum dado novo para salvar (todos já estão no backup)")
            return

        # 🔧 [NEW] Salva no PostgreSQL
        success = db_manager.save_training_data(client_id, filtrados)
        
        if success:
            render_logger.info(f"✅ [DB] Training data filtrado salvo - Cliente: {client_id}, Novos itens: {len(filtrados)}")
        else:
            render_logger.error(f"❌ [DB] Falha ao salvar training data filtrado")
            
        # 📁 [OLD] Código original comentado - manter por segurança
        # training_path = get_abs_path("vanna_core", "training_data", f"training_cliente_{client_id:02d}.json")
        # backup_path = get_abs_path("arq", "dados_treinados.json")
        # 
        # render_logger.info(f"📁 [FILE] Acessando arquivo backup: {backup_path}")
        # 
        # with open(backup_path, "r", encoding="utf-8") as f:
        #     backup = json.load(f)
        # ids_backup = {item["id"] for item in backup if isinstance(item, dict) and "id" in item}
        # 
        # training_data = vn.get_training_data()
        # # Supondo que training_data é um DataFrame
        # filtrados_df = training_data[~training_data["id"].isin(ids_backup)]
        # filtrados = filtrados_df.to_dict(orient="records")
        # 
        # render_logger.info(f"📝 [FILE] Gerando arquivo de treinamento: {training_path}")
        # with open(training_path, "w", encoding="utf-8") as f:
        #     json.dump(filtrados, f, ensure_ascii=False, indent=2)
        # print(f"Salvo {len(filtrados)} itens em {training_path}")
        # render_logger.info(f"✅ [FILE] Arquivo de treinamento salvo com {len(filtrados)} itens")
        
    except Exception as e:
        render_logger.error(f"❌ [DB] Erro ao salvar training_data filtrado: {e}")
        raise

def limpar_data_training_backup_only(vn):
    """
    🔄 [MIGRATION] Refatorada para usar PostgreSQL
    Remove apenas dados que não estão no backup
    """
    render_logger.info("🧹 [DB] Iniciando limpeza - removendo apenas dados não salvos no backup")
    
    try:
        # 🔧 [NEW] Carrega IDs do backup PostgreSQL (dados globais)
        ids_backup = db_manager.get_training_data_ids(client_id=None)  # client_id=None = dados globais
        render_logger.info(f"📋 [DB] {len(ids_backup)} IDs no backup PostgreSQL")

        # Obtém dados atuais do modelo Vanna
        training_data = vn.get_training_data()
        if training_data is None or training_data.empty:
            render_logger.info("ℹ️ [DB] Nenhum training_data no modelo para limpar")
            return
            
        ids_atual = training_data["id"].tolist()
        render_logger.info(f"📋 [DB] {len(ids_atual)} IDs no modelo atual")

        # Remove IDs que não estão no backup
        removidos = 0
        for data_id in ids_atual:
            if data_id not in ids_backup:
                try:
                    vn.remove_training_data(id=data_id)
                    removidos += 1
                    render_logger.info(f"🗑️ [CLEANUP] Removido ID {data_id} do modelo (não estava no backup)")
                except Exception as e:
                    render_logger.error(f"❌ [CLEANUP] Erro ao remover ID {data_id}: {e}")
        
        if removidos > 0:
            render_logger.info(f"✅ [DB] Limpeza concluída - {removidos} itens removidos do modelo")
        else:
            render_logger.info("ℹ️ [DB] Nenhum item para remover (todos estão no backup)")
        
        # 📁 [OLD] Código original comentado - manter por segurança
        # backup_path = get_abs_path("arq", "dados_treinados.json")
        # render_logger.info(f"📁 [FILE] Acessando backup para limpeza: {backup_path}")
        # with open(backup_path, "r", encoding="utf-8") as f:
        #     dados = json.load(f)
        # ids_backup = {item["id"] for item in dados if isinstance(item, dict) and "id" in item}
        # 
        # training_data = vn.get_training_data()
        # ids_atual = training_data["id"].tolist()
        # 
        # for id in ids_atual:
        #     if id not in ids_backup:
        #         try:
        #             vn.remove_training_data(id=id)
        #             print(f"Removido id {id} do modelo (não está no backup)")
        #             render_logger.info(f"🗑️ [CLEANUP] Removido ID {id} do modelo")
        #         except Exception as e:
        #             print(f"Erro ao remover id {id}: {e}")
        #             render_logger.error(f"❌ [CLEANUP] Erro ao remover ID {id}: {e}")
            
    except Exception as e:
        render_logger.error(f"❌ [DB] Erro na limpeza backup_only: {e}")
        raise

def save_training_plan(vn: VannaDefault, client_id: int):
    """
    🔄 [MIGRATION] Refatorada para usar PostgreSQL
    Salva o training_data atual do modelo no banco de dados

    Args:
        vn (VannaDefault): Instância do modelo Vanna.
        client_id (int): ID do cliente para identificar o treinamento.

    Raises:
        Exception: Caso ocorra algum erro ao salvar o plano.
    """
    render_logger.info(f"💾 [DB] Salvando training_plan para cliente {client_id}")
    
    try:
        # Obtém o training_data atual do modelo Vanna
        training_data = vn.get_training_data()
        if training_data is None or training_data.empty:
            render_logger.warning(f"⚠️ [DB] Nenhum training_data no modelo para salvar (cliente {client_id})")
            return
            
        training_data_dict = training_data.to_dict(orient='records')
        
        # 🔧 [NEW] Salva no PostgreSQL
        success = db_manager.save_training_data(client_id, training_data_dict)
        
        if success:
            render_logger.info(f"✅ [DB] Training plan salvo com sucesso - Cliente: {client_id}, Itens: {len(training_data_dict)}")
        else:
            render_logger.error(f"❌ [DB] Falha ao salvar training plan para cliente {client_id}")
            raise Exception("Falha ao salvar no PostgreSQL")
        
    except Exception as e:
        render_logger.error(f"❌ [DB] Erro ao salvar training_plan: {e}")
        raise

def converter_plan_markdown_para_vanna(plan_markdown: dict) -> list:
    """
    Converte um dicionário no formato {"_plan": [...]} com colunas em markdown
    para um plano compatível com vn.train(plan) da Vanna.AI.
    """

    def extrair_colunas(item_value: str) -> list:
        """
        Recebe uma string em Markdown contendo colunas de uma tabela,
        retorna uma lista de dicionários com name e type.
        """
        linhas = item_value.strip().split('\n')
        colunas = []
        # pula as 3 primeiras linhas (descrição, cabeçalho e separador)
        for linha in linhas[3:]:
            partes = linha.strip('|').split('|')
            if len(partes) >= 6:
                nome = partes[4].strip()
                tipo = partes[5].strip()
                colunas.append({'name': nome, 'type': tipo})
        return colunas

    novo_plan = []
    for item in plan_markdown.get('_plan', []):
        novo_item = {
            "item_type": "table",
            "item_group": item["item_group"],
            "item_name": item["item_name"],
            "columns": extrair_colunas(item["item_value"])
        }
        novo_plan.append(novo_item)

    return novo_plan

def load_training_data(vn: VannaDefault, client_id: int) -> bool:
    """
    🔄 [MIGRATION] Refatorada para usar PostgreSQL
    Carrega o training_data salvo e reexecuta o treinamento no modelo.

    Args:
        vn (VannaDefault): Instância do modelo Vanna.
        client_id (int): ID do cliente para identificar o treinamento.

    Returns:
        bool: True se o training_data foi carregado e treinado com sucesso, False caso contrário.
    """
    render_logger.info(f"📖 [DB] Carregando training_data para cliente {client_id}")
    
    try:
        # 🔧 [NEW] Carrega do PostgreSQL
        training_data = db_manager.load_training_data(client_id)
        
        if not training_data:
            render_logger.warning(f"⚠️ [DB] Nenhum training_data encontrado para cliente {client_id}")
            return False
        
        render_logger.info(f"📋 [DB] {len(training_data)} itens carregados para treinamento")
        
        # Aplica o treinamento no modelo Vanna (mesma lógica original)
        trained_items = 0
        for item in training_data:
            tipo = item.get("training_data_type")
            conteudo = item.get("content")
            pergunta = item.get("question")

            if not conteudo:
                continue  # ignora entradas sem conteúdo válido

            try:
                if tipo == "ddl":
                    vn.train(ddl=conteudo)
                    trained_items += 1

                elif tipo == "sql":
                    if not pergunta:
                        render_logger.warning(f"⚠️ [DB] Entrada SQL sem 'question', id: {item.get('id')}")
                        continue
                    vn.train(sql=conteudo, question=pergunta)
                    trained_items += 1

                elif tipo == "documentation":
                    vn.train(documentation=conteudo)
                    trained_items += 1

                else:
                    render_logger.warning(f"⚠️ [DB] Tipo de treinamento desconhecido: {tipo}")
                    
            except Exception as e:
                render_logger.error(f"❌ [DB] Erro ao treinar item {item.get('id')}: {e}")

        render_logger.info(f"✅ [DB] Training data aplicado com sucesso - Cliente: {client_id}, Itens treinados: {trained_items}/{len(training_data)}")
        return True
            
    except Exception as e:
        render_logger.error(f"❌ [DB] Erro ao carregar training_data: {e}")
        return False

def treinar_com_ddl(id_client: int, vn: VannaDefault):
    # gera o dict {tabela: ddl_sql, ...}
    ddls = gerar_ddl_para_cliente(id_client, vn)
    for tabela, ddl_sql in ddls.items():
        logging.info("Treinando com DDL da tabela %s...", tabela)
        # se sua versão do vn.train aceita 'ddl' sozinho:
        vn.train(ddl=ddl_sql)
        # caso ainda reclame de SQL ausente, use:
        # vn.train(question=f"DDL de {tabela}", sql=ddl_sql)
    logging.info("Treinamento com DDL concluído.")

def obter_id_client_por_email(email: str) -> int:
    logging.info("Buscando ID do cliente para o e-mail: %s", email)
    render_logger.info(f"🔍 [DB] Buscando ID do cliente para email: {email}")
    
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    cur = conn.cursor()
    cur.execute("SELECT id FROM usuarios WHERE email = %s;", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if not row:
        render_logger.error(f"❌ [DB] Usuário não encontrado para email: {email}")
        raise ValueError(f"Usuário com e-mail '{email}' não encontrado.")
    
    logging.info("ID do cliente encontrado: %d", row[0])
    render_logger.info(f"✅ [DB] ID do cliente encontrado: {row[0]} para email: {email}")
    return row[0]


def carregar_plan(id_client: int) -> list[dict]:
    """Lê ./arq/plan_cliente_XX.json e retorna lista de itens."""
    path = get_abs_path("arq", f"plan_cliente_{id_client:02d}.json")
    render_logger.info(f"📁 [FILE] Carregando plano do arquivo: {path}")
    with open(path, "r", encoding="utf-8") as f:
        blob = json.load(f)
    render_logger.info(f"✅ [FILE] Plano carregado com sucesso para cliente {id_client}")
    return blob.get("_plan", blob)


def treinar_com_plan(id_client: int, vn: VannaDefault):
    plan = carregar_plan(id_client)
    logging.info("Treinando Vanna com plano de dados (%d itens)...", len(plan))
    render_logger.info(f"🎯 [TRAIN] Iniciando treinamento com plano - {len(plan)} itens")
    vn.train(
        question=f"Plano de treinamento do cliente {id_client:02d}",
        sql=json.dumps(plan, ensure_ascii=False)
    )
    logging.info("Treinamento com plano concluído.")
    render_logger.info("✅ [TRAIN] Treinamento com plano concluído")


def treinar_com_kpis(id_client: int, vn: VannaDefault):
    logging.info("Treinando Vanna com definições de KPI...")
    conn = conectar_postgres()
    cur = conn.cursor()
    table = f"cli{int(id_client):02d}_kpis_definicoes"
    cur.execute(
        f"SELECT nome_kpi, descricao, formula_sql FROM {table} WHERE id_client = %s",
        (id_client,)
    )
    for nome, desc, formula in cur.fetchall():
        logging.info("\tKPI '%s': %s", nome, desc)
        vn.train(
            question=f"O KPI '{nome}' é definido como: {desc}",
            sql=formula
        )
    cur.close()
    conn.close()
    logging.info("Treinamento com KPIs concluído.")

def is_plan_valido(plan: dict) -> bool:
    return isinstance(plan, dict) and "_plan" in plan and isinstance(plan["_plan"], list)

def setup_treinamento_cliente(id_client: int) -> VannaDefault:
    """
    Prepara e faz fine-tuning do modelo Vanna para o cliente.
    Permite ao usuário escolher quais etapas executar.
    """
    render_logger.info(f"🚀 [SETUP] Iniciando setup_treinamento_cliente para ID {id_client}")
    
    vn = VannaDefault(model="jarves", api_key=os.getenv("API_KEY"))
    vn.connect_to_postgres(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    render_logger.info("✅ [SETUP] Conexão com PostgreSQL estabelecida")

    # 1) tenta carregar plano salvo
    if load_training_data(vn, id_client):
        logging.info("Pulando geração de plano para cliente %02d.", id_client)
        render_logger.info(f"✅ [SETUP] Training data carregado para cliente {id_client}")
        return vn

    # Verifica se já existe um arquivo de plan
    nome_plan = f"plan_cliente_{id_client:02d}.json"
    path_plan = os.path.join("arq", nome_plan)
    render_logger.info(f"📁 [FILE] Verificando existência do plano: {path_plan}")
    
    if os.path.exists(path_plan):
        render_logger.info(f"✅ [FILE] Arquivo de plano encontrado: {path_plan}")
        usar_plan_existente = input(f"Já existe um plan salvo em {path_plan}. Deseja usá-lo? (s/N): ").strip().lower() == "s"
        if usar_plan_existente:
            with open(path_plan, "r", encoding="utf-8") as f:
                plan_dict = json.load(f)
            logging.info("Usando plano existente: %s", path_plan)
            render_logger.info(f"📖 [FILE] Usando plano existente: {path_plan}")
        else:
            plan_dict = gerar_plan_treinamento(id_client, vn, salvar_em_arquivo=True)
            logging.info("Novo plano gerado e salvo.")
            render_logger.info("📝 [FILE] Novo plano gerado e salvo")
    else:
        render_logger.info(f"❌ [FILE] Arquivo de plano não encontrado: {path_plan}")
        plan_dict = gerar_plan_treinamento(id_client, vn, salvar_em_arquivo=True)
        logging.info("Plano gerado e salvo.")
        render_logger.info("📝 [FILE] Plano gerado e salvo")
   
    #plano = converter_plan_markdown_para_vanna(plan_dict)
    # Pergunta se deseja treinar o plano
    treinar_plan = input("Deseja treinar o plano de dados? (s/N): ").strip().lower() == "s"
    if treinar_plan:
        logging.info("Treinando com plano de dados...")
        vn.train(plan=plan_dict)
        logging.info("Plano de dados treinado para cliente %02d.", id_client)
    else:
        logging.info("Etapa de treinamento do plano pulada.")

    # Pergunta se deseja treinar KPIs
    treinar_kpis = input("Deseja treinar os KPIs? (s/N): ").strip().lower() == "s"
    if treinar_kpis:
        logging.info("Treinando com KPIs...")
        treinar_com_kpis(id_client, vn)
    else:
        logging.info("Etapa de treinamento dos KPIs pulada.")

    # Pergunta se deseja treinar DDL
    treinar_ddl = input("Deseja treinar as DDLs das tabelas? (s/N): ").strip().lower() == "s"
    if treinar_ddl:
        logging.info("Treinando com DDL das tabelas...")
        treinar_com_ddl(id_client, vn)
    else:
        logging.info("Etapa de treinamento das DDLs pulada.")

    return vn

def inicializar_vanna_para_interface(email: str) -> VannaDefault:
    id_client = obter_id_client_por_email(email)
    vn = setup_treinamento_cliente(id_client)
    return vn

def finalizar_sessao(vn: VannaDefault, id_client: int, historico: list[dict], email: str):
    """
    Finaliza a sessão do cliente: salva histórico, backup de treinamento e limpa dados temporários.
    """
    render_logger.info(f"🏁 [SESSION] Finalizando sessão para cliente {id_client} (email: {email})")
    
    try:
        # salva histórico de perguntas
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_file = get_abs_path("hist", f"historico_cli{id_client:02d}_{ts}.json")
        render_logger.info(f"📝 [FILE] Salvando histórico da sessão: {session_file}")
        
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(historico, f, indent=2, ensure_ascii=False)
        logging.info("Histórico de sessão salvo em: %s", session_file)
        render_logger.info(f"✅ [FILE] Histórico salvo com {len(historico)} entradas")

        # salva dados de treinamento filtrados
        salvar_training_filtrado(vn, id_client)

        # limpa o que não está no backup
        limpar_data_training_backup_only(vn)

        logging.info("Finalização da sessão concluída com sucesso.")
        render_logger.info("✅ [SESSION] Finalização da sessão concluída com sucesso")

    except Exception as e:
        logging.warning("Erro ao finalizar sessão do cliente: %s", e)
        render_logger.error(f"❌ [SESSION] Erro ao finalizar sessão: {e}")


def usar_vn_ask(vn, pergunta: str, email: str, id_client: int,
               gerar_grafico: bool = False):
    """
    Simula vn.ask no modo CLI:
      1) gera SQL com vn.generate_sql()
      2) executa com vn.run_sql()
      3) tenta gerar gráfico com vn.generate_plotly_code() + vn.get_plotly_figure()
      4) salva tudo no histórico (arq/historico_<email>.json)
      5) retorna dict com status, sql, resultado e figura
    """
    # monta timestamp para nome de arquivo
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"historico_cli{id_client:02d}_{ts}.json"
    os.makedirs("hist", exist_ok=True)
    hfile = os.path.join("hist", filename)

    # gera nome seguro para arquivos de figuras a partir do email
    safe_email = email.replace("@", "_").replace(".", "_")

    # tenta carregar histórico existente (se você quiser append em sessões múltiplas)
    try:
        with open(hfile, "r", encoding="utf-8") as f:
            historico = json.load(f)
    except FileNotFoundError:
        historico = []

    status = "success"
    figura: Optional[Any] = None
    plotly_code: Optional[str] = None

    # 1) gerar SQL
    raw = vn.generate_sql(pergunta)
    sql = raw.split("\n\n")[0].strip()

    try:
        # 2) executar SQL
        resultado = vn.run_sql(sql)

        # 3) gerar gráfico (se suportado)
        if gerar_grafico:
            try:
                plotly_code = vn.generate_plotly_code(pergunta)
                # 🔧 CORREÇÃO: get_plotly_figure precisa do DataFrame também
                figura = vn.get_plotly_figure(plotly_code, resultado)
                if figura:
                    # salva e abre HTML da figura
                    html_file = os.path.join("arq", f"figura_{safe_email}.html")
                    figura.write_html(html_file)
                    url = f"file://{os.path.abspath(html_file)}"
                    print("Abra este link no navegador:", url)
            except Exception:
                figura = None
    except Exception as e:
        # em caso de erro, retorna descrição
        status = "error"
        resultado = str(e)

    # registra entrada no histórico
    entry = {
        "id_client": id_client,
        "pergunta": pergunta,
        "sql": sql,
        "status": status,
        "resultado": str(resultado)
    }
    if plotly_code:
        entry["plotly_code"] = plotly_code
    if 'html_file' in locals():
        entry["html_file"] = html_file

    # retorna também o 'entry' para ser salvo externamente
    return {
        "status": status,
        "sql": sql,
        "resultado": resultado,
        "figura": figura,
        "url": url if 'url' in locals() else None,
        "entry": entry
    }


if __name__ == "__main__":
    # Escolha de modo de inicialização
    print("Modo de inicialização Vanna:")
    print(" 1) CLI interativo (padrão)")
    print(" 2) Web UI (Flask)")
    modo = input("Digite 1 ou 2 (Enter = 1): ").strip() or "1"

    if modo == "2":
        # executa todo o flaskVanna.py e sai deste script
        run_path(os.path.join(os.path.dirname(__file__), "flaskVanna.py"))
        sys.exit(0)

    # modo CLI interativo
    email = input("E-mail do usuário: ").strip()
    id_client = obter_id_client_por_email(email)
    logging.info("Iniciando pipeline para cliente %02d...", id_client)
    inclui_doc = input("Incluir documentação no fine-tuning? (s/N): ").lower().startswith("s")
    vn = setup_treinamento_cliente(id_client)

    # prepara histórico de sessão único
    historico: list[dict] = []
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_file = os.path.join("hist", f"historico_cli{id_client:02d}_{ts}.json")
    
    # Exemplo de loop interativo
    while True:
        pergunta = input("Pergunta: ").strip()
        if pergunta.lower() in ("sair","quit"):
            break

        modo_graf = input("Gerar gráfico? (s/N): ").lower().startswith("s")
        res = usar_vn_ask(vn, pergunta, email, id_client, gerar_grafico=modo_graf)

        if res["status"] == "success":
            print("Resultado:\n", res["resultado"])
            if res.get("url"):
                print("Abra este link no navegador:", res["url"])
        else:
            print("Erro:", res["resultado"])

        # acumula o registro no histórico de sessão
        historico.append(res["entry"])

    # grava **apenas um** JSON com todo o histórico
    os.makedirs("arq", exist_ok=True)
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)
    print(f"Histórico de sessão salvo em: {session_file}")
    # ao encerrar a sessão, salva o plano para próximas vezes
    try:
        salvar_training_filtrado(vn, id_client)
    except Exception as e:
        logging.warning("Falha ao salvar plano de treinamento: %s", e)
        
    # limpa training data que não está no backup
    try:
        limpar_data_training_backup_only(vn)
    except Exception as e:
        logging.warning("Falha ao limpar training data: %s", e)
    logging.info("Sessão encerrada.")


def executar_sql_e_gerar_grafico(vn, sql: str, titulo_grafico: str = "Gráfico Automático") -> dict:
    """
    Executa SQL e gera gráfico automático usando Vanna.
    
    Returns:
        dict: {"status": "success/error", "figura": plotly_figure, "erro": str}
    """
    print(f"🔧 [DEBUG executar_sql_e_gerar_grafico] Iniciando...")
    print(f"   - SQL recebido: {sql}")
    print(f"   - Título: {titulo_grafico}")
    
    try:
        # 1. Executa o SQL para obter dados
        print(f"   🔄 Executando SQL...")
        resultado = vn.run_sql(sql)
        print(f"   - Tipo do resultado: {type(resultado)}")
        print(f"   - Resultado é None: {resultado is None}")
        
        if resultado is None:
            print(f"   ❌ SQL retornou None")
            return {"status": "error", "erro": "SQL retornou None", "figura": None}
        
        if hasattr(resultado, 'empty') and resultado.empty:
            print(f"   ❌ DataFrame está vazio")
            return {"status": "error", "erro": "Nenhum dado retornado pelo SQL", "figura": None}
        
        print(f"   ✅ SQL executado com sucesso")
        if hasattr(resultado, 'columns'):
            print(f"   - Colunas: {list(resultado.columns)}")
            print(f"   - Número de linhas: {len(resultado)}")
        
        # 2. Gera gráfico automático usando vn.get_plot()
        print(f"   🎨 Gerando gráfico automático com vn.get_plot()...")
        
        # Verifica se o método get_plot existe
        if hasattr(vn, 'get_plot'):
            print(f"   ✅ Método get_plot encontrado")
            figura = vn.get_plot(resultado)
        elif hasattr(vn, 'generate_plotly_code') and hasattr(vn, 'get_plotly_figure'):
            print(f"   ⚠️ Método get_plot não encontrado, tentando generate_plotly_code...")
            # Fallback para o método original
            plotly_code = vn.generate_plotly_code(
                f"Crie um gráfico para visualizar estes dados: {titulo_grafico}"
            )
            print(f"   - Código Plotly gerado: {plotly_code is not None}")
            if plotly_code:
                print(f"   - Código (primeiros 200 chars): {str(plotly_code)[:200]}...")
                try:
                    # 🔧 CORREÇÃO: get_plotly_figure precisa do DataFrame também
                    figura = vn.get_plotly_figure(plotly_code, resultado)
                    print(f"   ✅ get_plotly_figure executado com DataFrame")
                except Exception as e:
                    print(f"   ⚠️ get_plotly_figure falhou: {str(e)}")
                    print(f"   🔧 Tentando fallback para plotly manual...")
                    figura = None
            else:
                figura = None
        else:
            print(f"   🔧 Nenhum método de gráfico do Vanna disponível, usando plotly manual...")
            figura = None
        
        # Fallback final: se nenhum método do Vanna funcionou, usar plotly diretamente
        if figura is None:
            print(f"   🔧 Usando plotly manual como fallback...")
            # Fallback final: usar plotly diretamente
            import plotly.express as px
            
            # Detecta colunas automaticamente
            colunas = list(resultado.columns)
            if len(colunas) >= 2:
                x_col = colunas[0]
                y_col = colunas[1]
                
                # Lógica automática baseada nos tipos de dados
                if resultado[y_col].dtype in ['int64', 'float64']:
                    if resultado[x_col].dtype in ['int64', 'float64']:
                        print(f"   - Criando scatter plot: {x_col} vs {y_col}")
                        figura = px.scatter(resultado, x=x_col, y=y_col, title=titulo_grafico)
                    else:
                        print(f"   - Criando bar chart: {x_col} vs {y_col}")
                        figura = px.bar(resultado, x=x_col, y=y_col, title=titulo_grafico)
                else:
                    print(f"   - Criando bar chart padrão: {x_col} vs {y_col}")
                    figura = px.bar(resultado, x=x_col, y=y_col, title=titulo_grafico)
            elif len(colunas) == 1:
                print(f"   - Criando histograma: {colunas[0]}")
                figura = px.histogram(resultado, x=colunas[0], title=titulo_grafico)
            else:
                print(f"   ❌ Nenhuma coluna disponível para gráfico")
                figura = None
        
        print(f"   - Figura gerada: {figura is not None}")
        
        if figura is None:
            print(f"   ❌ Falha ao gerar figura")
            return {"status": "error", "erro": "Falha ao gerar figura", "figura": None}
        
        # 3. Adiciona título personalizado se possível
        if hasattr(figura, 'update_layout'):
            figura.update_layout(title=titulo_grafico)
            print(f"   ✅ Título personalizado adicionado: {titulo_grafico}")
        
        print(f"   ✅ Figura gerada com sucesso!")
        return {"status": "success", "figura": figura, "erro": None}
        
    except Exception as e:
        print(f"   💥 EXCEÇÃO em executar_sql_e_gerar_grafico: {str(e)}")
        import traceback
        print(f"   📍 Traceback: {traceback.format_exc()}")
        return {"status": "error", "erro": str(e), "figura": None}


def gerar_grafico_personalizado(vn, sql: str, tipo_grafico: str = "auto", 
                               titulo: str = "Gráfico", x_col: str = None, 
                               y_col: str = None) -> dict:
    """
    Gera gráfico personalizado com parâmetros específicos.
    
    Returns:
        dict: {"status": "success/error", "figura": plotly_figure, "erro": str}
    """
    print(f"🎨 [DEBUG gerar_grafico_personalizado] Iniciando...")
    print(f"   - SQL recebido: {sql}")
    print(f"   - Tipo gráfico: {tipo_grafico}")
    print(f"   - Título: {titulo}")
    print(f"   - X col: {x_col}")
    print(f"   - Y col: {y_col}")
    
    try:
        # 1. Executa SQL para obter dados
        print(f"   🔄 Executando SQL...")
        dados = vn.run_sql(sql)
        print(f"   - Tipo dos dados: {type(dados)}")
        print(f"   - Dados é None: {dados is None}")
        
        if dados is None:
            print(f"   ❌ SQL retornou None")
            return {"status": "error", "erro": "Nenhum dado retornado pelo SQL", "figura": None}
            
        if hasattr(dados, 'empty') and dados.empty:
            print(f"   ❌ DataFrame está vazio")
            return {"status": "error", "erro": "DataFrame está vazio", "figura": None}
        
        print(f"   ✅ SQL executado com sucesso")
        if hasattr(dados, 'columns'):
            print(f"   - Colunas: {list(dados.columns)}")
            print(f"   - Número de linhas: {len(dados)}")
        
        # 2. Detecta colunas automaticamente se não especificadas
        colunas = list(dados.columns)
        print(f"   🔍 Detectando colunas...")
        print(f"   - Colunas disponíveis: {colunas}")
        
        if x_col == "auto" or x_col is None:
            x_col = colunas[0] if len(colunas) > 0 else None
            print(f"   - X col detectada automaticamente: {x_col}")
            
        if y_col == "auto" or y_col is None:
            y_col = colunas[1] if len(colunas) > 1 else colunas[0]
            print(f"   - Y col detectada automaticamente: {y_col}")
        
        if not x_col or not y_col:
            print(f"   ❌ Não foi possível determinar colunas X e Y")
            return {"status": "error", "erro": "Não foi possível determinar colunas X e Y", "figura": None}
        
        print(f"   ✅ Colunas finais - X: {x_col}, Y: {y_col}")
        
        # 3. Tenta usar vn.get_plot() com chart_type primeiro
        print(f"   📊 Tentando usar vn.get_plot() com chart_type...")
        figura = None
        
        if hasattr(vn, 'get_plot') and tipo_grafico != "auto":
            try:
                # Mapeia tipos para o formato esperado pelo Vanna
                chart_type_map = {
                    "bar": "bar",
                    "line": "line", 
                    "scatter": "scatter",
                    "pie": "pie",
                    "histogram": "histogram"
                }
                
                chart_type = chart_type_map.get(tipo_grafico)
                if chart_type:
                    print(f"   - Usando chart_type: {chart_type}")
                    figura = vn.get_plot(dados, chart_type=chart_type)
                    print(f"   ✅ Gráfico gerado com vn.get_plot()")
            except Exception as e:
                print(f"   ⚠️ vn.get_plot() falhou: {str(e)}")
                figura = None
        
        # 4. Fallback para plotly manual se vn.get_plot() não funcionou
        if figura is None:
            print(f"   🔧 Usando plotly manual...")
            import plotly.express as px
            import plotly.graph_objects as go
            print(f"   ✅ Plotly importado com sucesso")
            
            if tipo_grafico == "auto":
                print(f"   🤖 Detectando tipo automático...")
                # Lógica automática: numérico = scatter, categórico = bar
                if dados[y_col].dtype in ['int64', 'float64']:
                    if dados[x_col].dtype in ['int64', 'float64']:
                        print(f"   - Ambas colunas numéricas -> scatter")
                        figura = px.scatter(dados, x=x_col, y=y_col, title=titulo)
                    else:
                        print(f"   - X categórico, Y numérico -> bar")
                        figura = px.bar(dados, x=x_col, y=y_col, title=titulo)
                else:
                    print(f"   - Y não numérico -> bar")
                    figura = px.bar(dados, x=x_col, y=y_col, title=titulo)
                    
            elif tipo_grafico == "bar":
                print(f"   📊 Criando gráfico de barras")
                figura = px.bar(dados, x=x_col, y=y_col, title=titulo)
                
            elif tipo_grafico == "line":
                print(f"   📈 Criando gráfico de linha")
                figura = px.line(dados, x=x_col, y=y_col, title=titulo)
                
            elif tipo_grafico == "scatter":
                print(f"   🔵 Criando gráfico de dispersão")
                figura = px.scatter(dados, x=x_col, y=y_col, title=titulo)
                
            elif tipo_grafico == "pie":
                print(f"   🥧 Criando gráfico de pizza")
                figura = px.pie(dados, names=x_col, values=y_col, title=titulo)
                
            elif tipo_grafico == "histogram":
                print(f"   📊 Criando histograma")
                figura = px.histogram(dados, x=x_col, title=titulo)
                
            else:
                print(f"   ❌ Tipo de gráfico não suportado: {tipo_grafico}")
                return {"status": "error", "erro": f"Tipo de gráfico '{tipo_grafico}' não suportado", "figura": None}
        
        # 5. Adiciona título personalizado se não foi usado vn.get_plot()
        if figura and hasattr(figura, 'update_layout'):
            figura.update_layout(title=titulo)
            print(f"   ✅ Título personalizado adicionado: {titulo}")
        
        if figura is None:
            print(f"   ❌ Falha ao gerar figura")
            return {"status": "error", "erro": "Falha ao gerar figura", "figura": None}
        
        print(f"   ✅ Figura criada com sucesso!")
        return {"status": "success", "figura": figura, "erro": None}
        
    except Exception as e:
        print(f"   💥 EXCEÇÃO em gerar_grafico_personalizado: {str(e)}")
        import traceback
        print(f"   📍 Traceback: {traceback.format_exc()}")
        return {"status": "error", "erro": str(e), "figura": None}


def limpar_data_training(vn, id_client=None):
    """
    Remove dados de treinamento da sessão, preservando dados do backup original.
    
    Args:
        vn: Instância do modelo Vanna
        id_client: ID do cliente (opcional, para salvar dados filtrados)
    
    Fluxo:
        1. Salva dados filtrados (apenas os novos da sessão)
        2. Remove apenas dados que não estão no backup original
    """
    try:
        print("🧽 [VANNA] Iniciando limpeza inteligente dos dados de treinamento...")
        removidos = 0
        
        # ETAPA 1: Salvar dados filtrados se id_client fornecido
        if id_client is not None:
            try:
                print(f"💾 [VANNA] Salvando dados filtrados do cliente {id_client}...")
                salvar_training_filtrado(vn, id_client)
                print("✅ [VANNA] Dados filtrados salvos com sucesso")
            except Exception as e:
                print(f"⚠️ [VANNA] Erro ao salvar dados filtrados: {e}")
        
        # ETAPA 2: Limpar apenas dados que não estão no backup
        try:
            print("🧹 [VANNA] Removendo apenas dados adicionados durante a sessão...")
            
            # Carrega IDs do backup original
            # 🔧 [NEW] Carrega do PostgreSQL ao invés do arquivo
            ids_backup = db_manager.get_training_data_ids(client_id=None)  # client_id=None = dados globais
            if not ids_backup:
                print("⚠️ [VANNA] Nenhum backup encontrado no PostgreSQL, removendo todos os dados")
                # Se não há backup, remove tudo
                return limpar_data_training_completo(vn)
            
            print(f"📋 [VANNA] {len(ids_backup)} IDs no backup PostgreSQL")
            
            # 📁 [OLD] Código original comentado
            # backup_path = get_abs_path("arq", "dados_treinados.json")
            # if not os.path.exists(backup_path):
            #     print("⚠️ [VANNA] Arquivo de backup não encontrado, removendo todos os dados")
            #     # Se não há backup, remove tudo
            #     return limpar_data_training_completo(vn)
            # 
            # with open(backup_path, "r", encoding="utf-8") as f:
            #     dados_backup = json.load(f)
            # ids_backup = {item["id"] for item in dados_backup if isinstance(item, dict) and "id" in item}
            # print(f"📋 [VANNA] {len(ids_backup)} IDs no backup original")
            
            # Obtém dados atuais do modelo
            training_data = vn.get_training_data()
            if training_data is not None and not training_data.empty:
                ids_atual = training_data["id"].tolist() if 'id' in training_data.columns else []
                print(f"📋 [VANNA] {len(ids_atual)} IDs no modelo atual")
                
                # Remove apenas IDs que NÃO estão no backup (dados da sessão)
                for data_id in ids_atual:
                    if data_id not in ids_backup:
                        try:
                            vn.remove_training_data(id=data_id)
                            removidos += 1
                            print(f"🗑️ [VANNA] Removido ID {data_id} (adicionado na sessão)")
                        except Exception as e:
                            print(f"⚠️ [VANNA] Erro ao remover ID {data_id}: {e}")
                
                if removidos > 0:
                    print(f"✅ [VANNA] {removidos} itens da sessão removidos (backup preservado)")
                else:
                    print("ℹ️ [VANNA] Nenhum dado da sessão para remover")
                    
            else:
                print("ℹ️ [VANNA] Nenhum dado de treinamento encontrado no modelo")
                
        except Exception as e:
            print(f"⚠️ [VANNA] Erro na limpeza inteligente: {e}")
            print("🔄 [VANNA] Tentando limpeza de backup...")
            # Fallback para método de backup
            limpar_data_training_backup_only(vn)
        
        print(f"✅ [VANNA] Limpeza inteligente concluída - dados originais preservados")
        return True
        
    except Exception as e:
        print(f"❌ [VANNA] Erro crítico na limpeza inteligente: {e}")
        return False


def limpar_data_training_completo(vn):
    """Remove TODOS os dados de treinamento do modelo Vanna (usado como fallback)"""
    try:
        print("🧽 [VANNA] Iniciando limpeza COMPLETA dos dados de treinamento...")
        removidos = 0
        
        # Método 1: Obter lista de IDs e remover um por um
        if hasattr(vn, 'get_training_data') and hasattr(vn, 'remove_training_data'):
            try:
                training_data = vn.get_training_data()
                if training_data is not None and not training_data.empty:
                    ids_para_remover = training_data['id'].tolist() if 'id' in training_data.columns else []
                    for data_id in ids_para_remover:
                        try:
                            vn.remove_training_data(id=data_id)
                            removidos += 1
                        except Exception as e:
                            print(f"⚠️ [VANNA] Erro ao remover ID {data_id}: {e}")
                    
                    if removidos > 0:
                        print(f"✅ [VANNA] {removidos} itens removidos via remove_training_data()")
                        return True
                    else:
                        print("ℹ️ [VANNA] Nenhum item para remover (training_data vazio)")
                else:
                    print("ℹ️ [VANNA] Nenhum dado de treinamento encontrado")
            except Exception as e:
                print(f"⚠️ [VANNA] Erro método 1: {e}")
        
        # Método 2: Clear training data
        if hasattr(vn, 'clear_training_data'):
            try:
                vn.clear_training_data()
                print("✅ [VANNA] Dados limpos via clear_training_data()")
                return True
            except Exception as e:
                print(f"⚠️ [VANNA] Erro método 2: {e}")
        
        # Método 3: Reset do modelo
        if hasattr(vn, 'reset'):
            try:
                vn.reset()
                print("✅ [VANNA] Modelo resetado via reset()")
                return True
            except Exception as e:
                print(f"⚠️ [VANNA] Erro método 3: {e}")
        
        print("⚠️ [VANNA] Limpeza COMPLETA executada - alguns métodos podem não estar disponíveis")
        return True
        
    except Exception as e:
        print(f"❌ [VANNA] Erro crítico na limpeza completa: {e}")
        return False


if __name__ == "__main__":
    pass