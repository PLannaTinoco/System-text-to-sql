# db_utils.py – conexão com banco e funções auxiliares
import psycopg2
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Caminho absoluto do .env (2 níveis acima)
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=os.path.abspath(env_path))

def conectar_db():
    """Conexão psycopg2 para queries diretas (compatibilidade)"""
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def criar_engine() -> Engine:
    """Cria engine SQLAlchemy para uso com pandas.to_sql()"""
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    
    # String de conexão PostgreSQL para SQLAlchemy
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Cria engine com configurações otimizadas
    engine = create_engine(
        connection_string,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False  # Mude para True se quiser logs SQL
    )
    
    return engine

def autenticar_usuario(email, senha):
    """
    Autentica o usuário com base no email e senha.
    Retorna o id e o nome do usuário se encontrado, ou None se não encontrado.
    """
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nome FROM usuarios WHERE email=%s AND senha=%s", (email, senha))
    resultado = cur.fetchone()
    cur.close()
    conn.close()
    return resultado if resultado else None

