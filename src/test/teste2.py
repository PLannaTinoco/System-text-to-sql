from datetime import datetime
from typing import Any, Dict, Optional
import os
import json
import logging
from runpy import run_path
import sys
import time
from dotenv import load_dotenv
from vanna.remote import VannaDefault
import psycopg2
from gerarDDL import gerar_ddl_para_cliente

from gerar_schema_cliente import gerar_plan_treinamento
from kpis_Setup import (
    conectar_postgres,
    criar_tabela_kpis,
    processar_csv,
    criar_kpis_automatico,
    gerar_schema_json
)

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
# filepath: src/app.py

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
        raise ValueError(f"Usuário com e-mail '{email}' não encontrado.")
    logging.info("ID do cliente encontrado: %d", row[0])
    return row[0]


def carregar_plan(id_client: int) -> list[dict]:
    """Lê ./arq/plan_cliente_XX.json e retorna lista de itens."""
    path = os.path.join("arq", f"plan_cliente_{id_client:02d}.json")
    with open(path, "r", encoding="utf-8") as f:
        blob = json.load(f)
    return blob.get("_plan", blob)


def treinar_com_plan(id_client: int, vn: VannaDefault):
    plan = carregar_plan(id_client)
    logging.info("Treinando Vanna com plano de dados (%d itens)...", len(plan))
    vn.train(
        question=f"Plano de treinamento do cliente {id_client:02d}",
        sql=json.dumps(plan, ensure_ascii=False)
    )
    logging.info("Treinamento com plano concluído.")


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


def setup_treinamento_cliente(id_client: int) -> VannaDefault:
    model_name = "jarves"

    vn = VannaDefault(model=model_name, api_key=os.getenv("API_KEY"))

    # 3) conecta ao Postgres e faz o fine-tuning
    vn.connect_to_postgres(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    # 1) Plan de dados
    logging.info("Gerando plano de dados para cliente %02d...", id_client)
    gerar_plan_treinamento(id_client, vn, salvar_em_arquivo=True)

    # 2) KPIs
    logging.info("Inicializando definições de KPI para cliente %02d...", id_client)
    criar_tabela_kpis(id_client)
    csv_kpis = f"Planilhas/DadosW/kpis_marketing.csv"
    if os.path.exists(csv_kpis):
        processar_csv(csv_kpis, id_client, vn)
    else:
        schema = gerar_schema_json(id_client)
        criar_kpis_automatico(id_client, schema)

    # 3) Treinamentos
    treinar_com_plan(id_client, vn)
    treinar_com_kpis(id_client, vn)
    treinar_com_ddl(id_client, vn)
    logging.info("Treinamento completo para cliente %02d.", id_client)

    return vn


def auto_fix_and_run_sql(vn, question: str, email: str) -> Dict[str, Any]:
    """
    Gera e executa SQL para `question` usando `vn`.
    Em caso de erro, tenta corrigir automaticamente a SQL e reexecutar.
    Salva cada tentativa no histórico do usuário (arq/historico_<email>.json).
    Retorna dict com:
      - status: "success" ou "error"
      - sql_original: SQL inicial
      - sql_corrigida: SQL corrigida (ou None)
      - resultado: DataFrame ou mensagem de erro final
    """
    # monta caminho do histórico
    safe_email = email.replace("@", "_").replace(".", "_")
    os.makedirs("arq", exist_ok=True)
    hfile = os.path.join("arq", f"historico_{safe_email}.json")

    # carrega histórico existente
    try:
        with open(hfile, "r", encoding="utf-8") as hf:
            historico = json.load(hf)
    except FileNotFoundError:
        historico = []

    # gera SQL original
    raw = vn.generate_sql(question)
    sql_original = raw.split("\n\n")[0].strip()
    sql_corrigida: Optional[str] = None

    # tenta executar SQL original
    try:
        result = vn.run_sql(sql_original)
        status = "success"
        entry = {
            "pergunta": question,
            "sql_original": sql_original,
            "resultado": str(result)
        }
    except Exception as e1:
        err1 = str(e1)
        # prepara prompt de correção
        prompt = (
            f"I have an error: {err1}. "
            f"Here is the SQL I tried:\n{sql_original}\n"
            f"This was the question: {question}"
        )
        raw2 = vn.generate_sql(prompt)
        sql_corrigida = raw2.split("\n\n")[0].strip()
        try:
            result = vn.run_sql(sql_corrigida)
            status = "success"
            entry = {
                "pergunta": question,
                "sql_original": sql_original,
                "sql_corrigida": sql_corrigida,
                "resultado": str(result)
            }
        except Exception as e2:
            err2 = str(e2)
            status = "error"
            entry = {
                "pergunta": question,
                "sql_original": sql_original,
                "sql_corrigida": sql_corrigida,
                "erro": err2
            }
            result = err2

    # salva no histórico
    historico.append(entry)
    with open(hfile, "w", encoding="utf-8") as hf:
        json.dump(historico, hf, indent=2, ensure_ascii=False)

    return {
        "status": status,
        "sql_original": sql_original,
        "sql_corrigida": sql_corrigida,
        "resultado": result
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
    vn = setup_treinamento_cliente(id_client)

    # Exemplo de loop interativo
    historico = []
    while True:
        pergunta = input("Pergunta: ").strip()
        if pergunta.lower() in ("sair","quit"):
            break

        res = auto_fix_and_run_sql(vn, pergunta, email)
        if res["status"] == "success":
            print(res["resultado"])
        else:
            print("Erro final:", res["resultado"])

        # opcional: mantém histórico em memória se precisar usar depois
        historico.append({
            "pergunta": pergunta,
            "status": res["status"],
            "sql_original": res["sql_original"],
            "sql_corrigida": res.get("sql_corrigida"),
            "resultado": str(res["resultado"])
        })

    # grava histórico de sessão
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_file = os.path.join("arq", f"historico_cli{id_client:02d}_{ts}.json")
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)

    logging.info("Sessão encerrada.")
