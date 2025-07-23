# db_utils.py – conexão com banco e funções auxiliares
import psycopg2
import os
import logging
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# 🔧 [LOGGING] Configuração de logging para Render
def setup_render_logging():
    """Configura logging para ser visível no Render"""
    logger = logging.getLogger('soliris_db')
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - SOLIRIS-DB - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    return logger

# Inicializar logger
render_logger = setup_render_logging()

# Caminho absoluto do .env (2 níveis acima)
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
render_logger.info(f"🔧 [ENV] Caminho do .env: {os.path.abspath(env_path)}")
load_dotenv(dotenv_path=os.path.abspath(env_path))
render_logger.info("✅ [ENV] Variáveis de ambiente carregadas")

def conectar_db():
    """Conexão psycopg2 para queries diretas (compatibilidade)"""
    render_logger.info("🔌 [DB] Iniciando conexão com banco PostgreSQL")
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        render_logger.info("✅ [DB] Conexão PostgreSQL estabelecida com sucesso")
        return conn
    except Exception as e:
        render_logger.error(f"❌ [DB] Erro ao conectar com PostgreSQL: {e}")
        raise

def criar_engine() -> Engine:
    """Cria engine SQLAlchemy para uso com pandas.to_sql()"""
    render_logger.info("🔧 [DB] Criando engine SQLAlchemy")
    
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    
    # String de conexão PostgreSQL para SQLAlchemy
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    render_logger.info(f"🔧 [DB] Connection string: postgresql://{db_user}:***@{db_host}:{db_port}/{db_name}")
    
    try:
        # Cria engine com configurações otimizadas
        engine = create_engine(
            connection_string,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
            echo=False  # Mude para True se quiser logs SQL
        )
        render_logger.info("✅ [DB] Engine SQLAlchemy criada com sucesso")
        return engine
    except Exception as e:
        render_logger.error(f"❌ [DB] Erro ao criar engine SQLAlchemy: {e}")
        raise

def autenticar_usuario(email, senha):
    """
    Autentica o usuário com base no email e senha.
    Retorna o id e o nome do usuário se encontrado, ou None se não encontrado.
    """
    render_logger.info(f"🔐 [AUTH] Tentando autenticar usuário: {email}")
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nome FROM usuarios WHERE email=%s AND senha=%s", (email, senha))
    resultado = cur.fetchone()
    cur.close()
    conn.close()
    return resultado if resultado else None

