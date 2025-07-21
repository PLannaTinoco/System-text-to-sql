import os
import json
import logging
from vanna.remote import VannaDefault
from gerar_schema_cliente import gerar_plan_treinamento
from kpis_Setup import conectar_postgres

def gerar_ddl_para_cliente(id_client: int,
                           vn: VannaDefault,
                           salvar_em_arquivo: bool = False
                          ) -> dict[str, str]:
    """
    1) Treina o agente com o plan de dados do cliente
    2) Lista tabelas cliXX_*
    3) Gera DDL de cada tabela via vn.generate_sql(...)
    4) (Opcional) Salva em arq/ddl_cliente_XX.json
    Retorna {table_name: ddl_sql}.
    """
    # 1) Treina com plan de dados
    logging.info("Treinando agente com plan de dados para gerar DDL...")
    gerar_plan_treinamento(id_client, vn, salvar_em_arquivo=False)

    # 2) Lista tabelas do cliente
    conn = conectar_postgres()
    cur = conn.cursor()
    prefixo = f"cli{id_client:02d}_%"
    cur.execute("""
        SELECT table_name
          FROM information_schema.tables
         WHERE table_schema='public'
           AND table_name LIKE %s
         ORDER BY table_name
    """, (prefixo,))
    tabelas = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()

    # 3) Gera DDLs
    ddls: dict[str, str] = {}
    for tbl in tabelas:
        logging.info("Gerando DDL para tabela %s...", tbl)
        try:
            ddl_sql = vn.generate_sql(
                question=f"Crie um script DDL (CREATE TABLE) para a tabela '{tbl}'."
            )
            ddls[tbl] = ddl_sql
            logging.info("DDL gerado para %s.", tbl)
        except Exception as e:
            logging.error("Erro ao gerar DDL para %s: %s", tbl, e)

    # 4) Salva em JSON
    if salvar_em_arquivo:
        os.makedirs("arq", exist_ok=True)
        fname = f"ddl_cliente_{id_client:02d}.json"
        path = os.path.join("arq", fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ddls, f, indent=2, ensure_ascii=False)
        logging.info("DDLs salvos em: %s", path)

    return ddls

def criar_agente_e_gerar_ddl(id_client: int,
                             model_name: str = "jarves",
                             salvar_em_arquivo: bool = True
                            ) -> dict[str, str]:
    """
    Instancia e conecta VannaDefault, 
    chama gerar_ddl_para_cliente(..., salvar_em_arquivo=...)
    """
    vn = VannaDefault(model=model_name, api_key=os.getenv("API_KEY"))
    vn.connect_to_postgres(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return gerar_ddl_para_cliente(id_client, vn, salvar_em_arquivo=salvar_em_arquivo)