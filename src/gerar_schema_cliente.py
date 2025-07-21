import os, json, logging
import psycopg2
from dotenv import load_dotenv
from vanna.remote import VannaDefault
"""
Este codigo ja esta linkado dentro o kpis_Setup.py, 
Logo é gerado dois arquivos que se atualizam,
O primeiro gerado pelo gerar_schema_cliente.py
e o segundo pelo kpis_Setup.py
"""
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def conectar_postgres():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def gerar_plan_treinamento(id_client: int,
                           vn: VannaDefault,
                           salvar_em_arquivo: bool = False):
    prefixo = f"cli{id_client:02d}"
    consulta = f"""
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE table_name LIKE '{prefixo}%'
    """
    try:
        df_info = vn.run_sql(consulta)
    except Exception as e:
        logging.error("Erro ao executar SQL para plan de treinamento: %s → %s", consulta, e)
        return []                        # fallback vazio
    plan = vn.get_training_plan_generic(df_info)
    if salvar_em_arquivo:
        os.makedirs("arq", exist_ok=True)
        nome = f"plan_cliente_{id_client:02d}.json"
        path = os.path.join("arq", nome)
        # serializa via __dict__
        with open(path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False, default=lambda o: o.__dict__)
        logging.info("Plano salvo em: %s", path)

    return plan


if __name__ == "__main__":
    from vanna.remote import VannaDefault
    api_key = os.getenv("API_KEY")
    vn = VannaDefault(model="jarves", api_key=api_key)
    vn.connect_to_postgres(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    plan = gerar_plan_treinamento(1, vn, salvar_em_arquivo=True)

    # converte o TrainingPlan em lista de dicts
    plan_list = json.loads(
        json.dumps(plan, default=lambda o: o.__dict__, ensure_ascii=False)
    )

    print(f"Gerados {len(plan_list)} itens de treinamento.")
