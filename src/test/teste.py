import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def gerar_schema_json(client_id):
    """
    Identifica todas as tabelas prefixadas com 'CliXX_' (onde XX = client_id)
    e retorna um objeto Python contendo o schema no formato esperado pela Vanna.AI:
    [
      {
        "table_name": "Cli01_tabela_exemplo",
        "columns": ["col1", "col2", "col3", ...]
      },
      ...
    ]
    """
    # Conexão com o PostgreSQL
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    cur = conn.cursor()

    # Prefixo de tabelas do cliente (ex: client_id = 1 → "Cli01_")
    prefixo = f"Cli{int(client_id):02d}_"

    # 1) Buscar nome de todas as tabelas que começam com o prefixo
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name LIKE %s
        ORDER BY table_name;
    """, (prefixo + "%",))
    tabelas = [row[0] for row in cur.fetchall()]

    schema_json = []
    for tabela in tabelas:
        # 2) Para cada tabela, buscar as colunas
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            ORDER BY ordinal_position;
        """, (tabela,))
        colunas = [row[0] for row in cur.fetchall()]
        schema_json.append({
            "table_name": tabela,
            "columns": colunas
        })

    cur.close()
    conn.close()
    return schema_json

if __name__ == "__main__":
    client_id = 1  # altere para o ID desejado
    schema = gerar_schema_json(client_id)
    os.makedirs("arq", exist_ok=True)
    file = os.path.join("arq", f"schema_cliente_{client_id:02d}.json")
    with open(file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f"schema_json para client_id={client_id} gerado em '{file}'.")
