import os, json, csv, logging
import psycopg2
from dotenv import load_dotenv
from vanna.remote import VannaDefault
from gerar_schema_cliente import gerar_plan_treinamento


load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Instancia Vanna para uso geral
vn = VannaDefault(model="jarves", api_key=os.getenv("API_KEY"))

def conectar_postgres():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def criar_tabela_kpis(id_client: int):
    table = f"cli{int(id_client):02d}_kpis_definicoes"
    conn = conectar_postgres()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id SERIAL PRIMARY KEY,
            id_client INTEGER NOT NULL,
            nome_kpi TEXT NOT NULL,
            descricao TEXT,
            formula_sql TEXT,
            UNIQUE (id_client, nome_kpi)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    logging.info("Tabela '%s' criada ou já existia.", table)

def inserir_kpi(id_client: int, nome: str, desc: str, formula: str):
    table = f"cli{int(id_client):02d}_kpis_definicoes"
    conn = conectar_postgres()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO {table} (id_client, nome_kpi, descricao, formula_sql)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id_client, nome_kpi) DO UPDATE SET
            descricao = EXCLUDED.descricao,
            formula_sql = EXCLUDED.formula_sql;
    """, (id_client, nome, desc, formula))
    conn.commit()
    cur.close()
    conn.close()
    logging.info("KPI '%s' atualizada/inserida em %s.", nome, table)

def processar_csv(csv_path: str, id_client: int, vn: VannaDefault):
    """
    1) Treina o agente com o plano de dados do cliente
    2) Lê o CSV de KPIs
    3) Para cada KPI chama vn.generate_sql() e insere no banco
    """
    logging.info("Processando CSV de KPIs: %s", csv_path)

    # re-treina com o plan antes de gerar cada SQL de KPI
    gerar_plan_treinamento(id_client, vn, salvar_em_arquivo=False)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nome = row["nome"].strip()
            desc = row["descricao"].strip()
            logging.info("Gerando SQL para KPI '%s' via Vanna...", nome)
            formula_sql = vn.generate_sql(
                question=f"Crie a consulta SQL para o KPI '{nome}': {desc}"
            )
            logging.info("SQL gerada para '%s': %s", nome, formula_sql)
            inserir_kpi(id_client, nome, desc, formula_sql)

def criar_kpis_automatico(id_client: int, schema_json: list[dict]):
    """
    Gera KPIs padrão (exemplo: count(*) por tabela) 
    a partir do schema_json e insere via inserir_kpi().
    """
    for tbl in schema_json:
        nome = f"count_{tbl['table_name']}"
        desc = f"Contagem de registros em {tbl['table_name']}"
        formula = f"SELECT COUNT(*) FROM {tbl['table_name']};"
        inserir_kpi(id_client, nome, desc, formula)

def gerar_schema_json(id_client: int) -> list[dict]:
    """
    1) Lista tabelas public CLIXX_  
    2) Para cada tabela busca colunas  
    3) Monta lista de {table_name, columns:[{name,type},…]}  
    4) Salva em arq/schema_cliente_XX.json  
    """
    conn = conectar_postgres()
    cur = conn.cursor()
    prefixo = f"cli{int(id_client):02d}_"
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public'
          AND table_name LIKE %s
        ORDER BY table_name
    """, (prefixo+"%",))
    tabelas = [r[0] for r in cur.fetchall()]

    schema = []
    for tbl in tabelas:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (tbl,))
        cols = [{"name":c, "type":t} for c,t in cur.fetchall()]
        schema.append({"table_name": tbl, "columns": cols})

    cur.close()
    conn.close()

    os.makedirs("arq", exist_ok=True)
    fname = f"schema_cliente_{id_client:02d}.json"
    path = os.path.join("arq", fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    logging.info("Schema salvo em: %s", path)

    return schema

def fetch_kpis(id_client: int) -> list[tuple[str, str, str]]:
    """
    Retorna lista de KPIs definidos para o cliente:
    cada tupla é (nome_kpi, descricao, formula_sql)
    """
    conn = conectar_postgres()
    cur = conn.cursor()
    table = f"cli{int(id_client):02d}_kpis_definicoes"
    cur.execute(f'''
        SELECT nome_kpi, descricao, formula_sql
        FROM {table};
    ''')
    kpis = cur.fetchall()
    cur.close()
    conn.close()
    return kpis

# --------------------------------------------------------------------------------
# Rotina principal: junta tudo
# --------------------------------------------------------------------------------

if __name__ == "__main__":
    ID_CLIENTE = 1

    # 1) Conecta a Vanna ao Postgres
    vn.connect_to_postgres(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    # 2) Gera somente o JSON de plano, sobrescrevendo se já existir
    logging.info("Gerando e salvando apenas o plan de treinamento para cliente %02d", ID_CLIENTE)
    gerar_plan_treinamento(ID_CLIENTE, vn, salvar_em_arquivo=True)

    logging.info("Plan salvo em: arq/plan_cliente_%02d.json", ID_CLIENTE)
    # --- fim do fluxo, não executa nada além disso ---
    exit(0)

def setup_treinamento_cliente(id_client):
    # 1) plan de dados
    gerar_plan_treinamento(id_client, vn, salvar_em_arquivo=True)
    # 2) tabela/kpis
    criar_tabela_kpis(id_client)
    csv_kpis = f"csv/kpis_cliente_{id_client:02d}.csv"
    if os.path.exists(csv_kpis):
        processar_csv(csv_kpis, id_client)
    else:
        schema = gerar_schema_json(id_client)
        criar_kpis_automatico(id_client, schema)
    # 3) treinos separados em app.py: plan + kpis
    ...
