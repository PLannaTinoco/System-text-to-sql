"""
Módulo de persistência para dados de treinamento de IA.
Migração do armazenamento local JSON para PostgreSQL.
"""

import os
import json
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

class DatabaseManager:
    """
    Gerenciador de persistência de dados de treinamento de IA.
    Usa PostgreSQL com psycopg2 e parâmetros explícitos do .env.
    """
    
    def __init__(self):
        """Inicializa o gerenciador carregando configurações do .env"""
        # Carregar .env SEMPRE antes de qualquer conexão
        load_dotenv()
        print("[DB] Arquivo .env carregado")
        
        # Parâmetros de conexão explícitos do .env
        self.conn_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'soliris_db'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        # Log dos parâmetros (senha mascarada)
        masked_params = self.conn_params.copy()
        masked_params['password'] = '***' if masked_params['password'] else None
        print(f"[DB] Parâmetros de conexão: {masked_params}")
        
        # Validar parâmetros obrigatórios
        if not self.conn_params['user'] or not self.conn_params['password']:
            raise ValueError("DB_USER e DB_PASSWORD devem estar definidos no .env")
    
    def _get_connection(self):
        """
        Cria uma conexão PostgreSQL usando parâmetros explícitos.
        NUNCA faz fallback para usuário do OS.
        """
        try:
            print("[DB] Tentando conectar ao PostgreSQL...")
            print(f"[DEBUG] conn_params: {self.conn_params['user']}@{self.conn_params['host']}:{self.conn_params['port']}/{self.conn_params['database']}")
            conn = psycopg2.connect(**self.conn_params)
            print("[DB] Conexão PostgreSQL estabelecida")
            return conn
        except psycopg2.Error as e:
            print(f"[DB ERROR] Erro de conexão PostgreSQL: {e}")
            raise
        except Exception as e:
            print(f"[DB ERROR] Erro inesperado na conexão: {e}")
            raise
    
    def save_training_data(self, client_id, training_data_list) -> bool:
        """
        Salva lista de dados de treinamento na tabela ai_training_data.
        
        Args:
            client_id: ID do cliente (pode ser None para dados globais)
            training_data_list: Lista de dicionários com dados de treinamento
            
        Returns:
            bool: True se salvou com sucesso, False caso contrário
        """
        try:
            # Log dos dados a serem salvos
            print(f"[DEBUG] Salvando dados de treinamento para cliente: {client_id}")
            print(f"[DEBUG] Número de registros: {len(training_data_list)}")
            if training_data_list:
                print(f"[DEBUG] Amostra primeiro registro: {training_data_list[0]}")
            
            conn = psycopg2.connect(**self.conn_params)
            cursor = conn.cursor()
            
            saved_count = 0
            for item in training_data_list:
                try:
                    # Extrair campos do formato Vanna
                    item_id = item.get('id')
                    training_type = item.get('training_data_type', 'unknown')
                    content = item.get('content', '')
                    question = item.get('question', '')
                    
                    # Insert na tabela ai_training_data
                    insert_sql = """
                        INSERT INTO ai_training_data (
                            client_id, vanna_id, training_type, content, question, created_at
                        ) VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (client_id, vanna_id) DO UPDATE SET
                            training_type = EXCLUDED.training_type,
                            content = EXCLUDED.content,
                            question = EXCLUDED.question
                    """
                    
                    cursor.execute(insert_sql, (client_id, item_id, training_type, content, question))
                    saved_count += 1
                    
                except Exception as item_error:
                    print(f"[DB ERROR] Erro ao salvar item {item.get('id', 'unknown')}: {item_error}")
                    continue
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[DB] {saved_count} registros salvos para cliente {client_id}")
            return True
            
        except psycopg2.Error as e:
            print(f"[DB ERROR] Erro PostgreSQL ao salvar dados: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
        except Exception as e:
            print(f"[DB ERROR] Erro inesperado ao salvar dados: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def load_training_data(self, client_id) -> List[Dict[str, Any]]:
        """
        Carrega dados de treinamento da tabela ai_training_data.
        
        Args:
            client_id: ID do cliente (None para dados globais)
            
        Returns:
            List[Dict]: Lista de dados de treinamento no formato Vanna
        """
        try:
            print(f"[DEBUG] Carregando dados de treinamento para cliente: {client_id}")
            
            conn = psycopg2.connect(**self.conn_params)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Query baseada no client_id
            if client_id is None:
                query_sql = """
                    SELECT vanna_id, training_type, content, question, created_at
                    FROM ai_training_data 
                    WHERE client_id IS NULL
                    ORDER BY created_at DESC
                """
                cursor.execute(query_sql)
            else:
                query_sql = """
                    SELECT vanna_id, training_type, content, question, created_at
                    FROM ai_training_data 
                    WHERE client_id = %s
                    ORDER BY created_at DESC
                """
                cursor.execute(query_sql, (str(client_id),))
            
            results = cursor.fetchall()
            
            # Converter para formato Vanna
            training_data = []
            for row in results:
                training_data.append({
                    'id': row['vanna_id'],
                    'training_data_type': row['training_type'],
                    'content': row['content'],
                    'question': row['question']
                })
            
            print(f"[DB] Carregados {len(training_data)} registros de treinamento")
            if training_data:
                print(f"[DEBUG] Amostra primeiro registro: {training_data[0]}")
            
            cursor.close()
            conn.close()
            return training_data
            
        except psycopg2.Error as e:
            print(f"[DB ERROR] Erro PostgreSQL ao carregar dados: {e}")
            if 'conn' in locals():
                conn.close()
            return []
        except Exception as e:
            print(f"[DB ERROR] Erro inesperado ao carregar dados: {e}")
            if 'conn' in locals():
                conn.close()
            return []
    
    def get_training_data_ids(self, client_id) -> List[str]:
        """
        Obtém apenas os IDs dos dados de treinamento.
        
        Args:
            client_id: ID do cliente (None para dados globais)
            
        Returns:
            List[str]: Lista de IDs dos dados de treinamento
        """
        try:
            print(f"[DEBUG] Carregando IDs de treinamento para cliente: {client_id}")
            
            conn = psycopg2.connect(**self.conn_params)
            cursor = conn.cursor()
            
            # Query baseada no client_id
            if client_id is None:
                query_sql = "SELECT vanna_id FROM ai_training_data WHERE client_id IS NULL"
                cursor.execute(query_sql)
            else:
                query_sql = "SELECT vanna_id FROM ai_training_data WHERE client_id = %s"
                cursor.execute(query_sql, (str(client_id),))
            
            results = cursor.fetchall()
            ids = [row[0] for row in results if row[0] is not None]
            
            print(f"[DB] Carregados {len(ids)} IDs de treinamento")
            
            cursor.close()
            conn.close()
            return ids
            
        except psycopg2.Error as e:
            print(f"[DB ERROR] Erro PostgreSQL ao carregar IDs: {e}")
            if 'conn' in locals():
                conn.close()
            return []
        except Exception as e:
            print(f"[DB ERROR] Erro inesperado ao carregar IDs: {e}")
            if 'conn' in locals():
                conn.close()
            return []
    
    def test_connection(self) -> bool:
        """
        Testa a conexão com o banco de dados.
        
        Returns:
            bool: True se a conexão foi bem-sucedida
        """
        try:
            print("[DEBUG] Testando conexão com o banco...")
            conn = psycopg2.connect(**self.conn_params)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            print("[DB] Teste de conexão bem-sucedido")
            return True
        except Exception as e:
            print(f"[DB ERROR] Teste de conexão falhou: {e}")
            return False
    
    def ensure_table_exists(self) -> bool:
        """
        Garante que a tabela ai_training_data existe.
        
        Returns:
            bool: True se a tabela existe ou foi criada
        """
        try:
            print("[DEBUG] Verificando se tabela ai_training_data existe...")
            conn = psycopg2.connect(**self.conn_params)
            cursor = conn.cursor()
            
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS ai_training_data (
                    id SERIAL PRIMARY KEY,
                    client_id VARCHAR(100),
                    vanna_id VARCHAR(255),
                    training_type VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    question TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(client_id, vanna_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_ai_training_client 
                ON ai_training_data(client_id);
                
                CREATE INDEX IF NOT EXISTS idx_ai_training_vanna_id 
                ON ai_training_data(vanna_id);
            """
            
            cursor.execute(create_table_sql)
            conn.commit()
            cursor.close()
            conn.close()
            
            print("[DB] Tabela ai_training_data verificada/criada")
            return True
            
        except psycopg2.Error as e:
            print(f"[DB ERROR] Erro ao criar/verificar tabela: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
        except Exception as e:
            print(f"[DB ERROR] Erro inesperado ao verificar tabela: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def delete_training_data(self, client_id, vanna_ids: List[str]) -> bool:
        """
        Remove dados de treinamento específicos.
        
        Args:
            client_id: ID do cliente (None para dados globais)
            vanna_ids: Lista de IDs do Vanna para remover
            
        Returns:
            bool: True se removeu com sucesso
        """
        try:
            print(f"[DEBUG] Removendo {len(vanna_ids)} registros para cliente: {client_id}")
            
            conn = psycopg2.connect(**self.conn_params)
            cursor = conn.cursor()
            
            deleted_count = 0
            for vanna_id in vanna_ids:
                try:
                    if client_id is None:
                        delete_sql = "DELETE FROM ai_training_data WHERE client_id IS NULL AND vanna_id = %s"
                        cursor.execute(delete_sql, (vanna_id,))
                    else:
                        delete_sql = "DELETE FROM ai_training_data WHERE client_id = %s AND vanna_id = %s"
                        cursor.execute(delete_sql, (client_id, vanna_id))
                    
                    if cursor.rowcount > 0:
                        deleted_count += 1
                        
                except Exception as item_error:
                    print(f"[DB ERROR] Erro ao remover item {vanna_id}: {item_error}")
                    continue
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[DB] {deleted_count} registros removidos para cliente {client_id}")
            return True
            
        except psycopg2.Error as e:
            print(f"[DB ERROR] Erro PostgreSQL ao remover dados: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
        except Exception as e:
            print(f"[DB ERROR] Erro inesperado ao remover dados: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def format_training_data_item(self, item: Dict[str, Any], client_id: int, index: int = 0) -> Dict[str, Any]:
        """
        Padroniza um item de training_data para o formato correto do banco.
        
        Args:
            item: Item original (pode vir do Vanna ou de outra fonte)
            client_id: ID do cliente
            index: Índice para gerar ID único se necessário
        
        Returns:
            Dict com formato padronizado: {id, training_data_type, question, content, metadata}
        """
        return {
            "id": item.get("id", f"auto-{client_id}-{index}-{hash(str(item))%10000}"),
            "training_data_type": item.get("training_data_type", "unknown"),
            "question": item.get("question", ""),
            "content": item.get("content", ""),
            "metadata": item.get("metadata", {})
        }
    
    def format_training_data_batch(self, training_data: List[Dict[str, Any]], client_id: int) -> List[Dict[str, Any]]:
        """
        Padroniza um lote de training_data para o formato correto do banco.
        
        Args:
            training_data: Lista de itens de training_data
            client_id: ID do cliente
        
        Returns:
            Lista com itens formatados corretamente
        """
        formatted_data = []
        for index, item in enumerate(training_data):
            formatted_item = self.format_training_data_item(item, client_id, index)
            formatted_data.append(formatted_item)
        
        print(f"[DB] Formatados {len(formatted_data)} itens para cliente {client_id}")
        return formatted_data

# Instância global para uso nos módulos
db_manager = DatabaseManager()
