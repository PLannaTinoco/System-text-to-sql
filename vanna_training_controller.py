#!/usr/bin/env python3
"""
Script de Controle de Training Data - Modelo Vanna
Funções: Backup, Remoção, Listagem e Restauração de dados de treinamento

🔧 FUNCIONALIDADES:
- ✅ Backup de dados de treinamento (JSON + PostgreSQL)
- ✅ Remoção segura de todos os dados
- ✅ Restauração de backups
- ✅ Listagem detalhada de dados
- ✅ Listagem de backups disponíveis

🚀 EXEMPLOS DE USO:
# Listar dados atuais
python vanna_training_controller.py list

# Fazer backup completo
python vanna_training_controller.py backup --backup-type both

# Fazer backup para cliente específico
python vanna_training_controller.py backup --client-id cliente_001 --backup-type postgresql

# Remover todos os dados (CUIDADO!)
python vanna_training_controller.py remove --confirm

# Restaurar do PostgreSQL
python vanna_training_controller.py restore --client-id cliente_001

# Restaurar de arquivo JSON
python vanna_training_controller.py restore --backup-path backups/backup_training_global_20250123_143052.json

# Listar backups disponíveis
python vanna_training_controller.py list-backups

# Ver status completo do sistema
python vanna_training_controller.py status

# Sincronizar dados Vanna → PostgreSQL
python vanna_training_controller.py sync --direction vanna_to_postgresql --client-id cliente_001

# Sincronizar dados PostgreSQL → Vanna
python vanna_training_controller.py sync --direction postgresql_to_vanna --client-id cliente_001

# Comparar dados entre Vanna e PostgreSQL
python vanna_training_controller.py compare --client-id cliente_001

📋 CONFIGURAÇÃO:
- Crie arquivo .env com as variáveis: API_KEY, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
- Instale dependências: pip install vanna python-dotenv psycopg2-binary pandas

Baseado no padrão estabelecido em flaskVanna.py
Integrado com migração PostgreSQL via DatabaseManager
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from vanna.remote import VannaDefault

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - VANNA_CONTROL - %(levelname)s - %(message)s"
)

# Adicionar src ao path para importar database_manager
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from database_manager import db_manager
    print("✅ DatabaseManager importado com sucesso")
    DB_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ DatabaseManager não disponível: {e}")
    DB_AVAILABLE = False

class VannaTrainingController:
    """
    Controlador para gerenciamento de training_data do modelo Vanna
    Integrado com PostgreSQL e backup JSON
    """
    
    def __init__(self):
        """Inicializa o controlador carregando configurações"""
        logging.info("🚀 Inicializando Vanna Training Controller...")
        
        # Carregar variáveis de ambiente
        load_dotenv(override=True)
        logging.info("📋 Variáveis de ambiente carregadas")
        
        # Configurações do banco
        self.db_config = {
            'host': os.getenv("DB_HOST"),
            'port': os.getenv("DB_PORT"),
            'dbname': os.getenv("DB_NAME"),
            'user': os.getenv("DB_USER"),
            'password': os.getenv("DB_PASSWORD")
        }
        
        # API Key da Vanna
        self.api_key = os.getenv("API_KEY")
        
        # Validações
        if not self.api_key:
            raise ValueError("API_KEY deve estar definida no .env")
        
        if not all([self.db_config['host'], self.db_config['user'], self.db_config['password']]):
            logging.warning("⚠️ Configurações do banco incompletas - alguns recursos podem não funcionar")
        
        # Inicializar Vanna
        self.vn = None
        self._connect_vanna()
        
        # Diretórios para backup
        self.backup_dir = os.path.join(os.path.dirname(__file__), "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        
        logging.info("✅ Vanna Training Controller inicializado com sucesso")
    
    def _connect_vanna(self):
        """Conecta ao modelo Vanna e banco PostgreSQL"""
        try:
            logging.info("🔌 Conectando ao modelo Vanna...")
            self.vn = VannaDefault(model="jarves", api_key=self.api_key)
            
            # Conectar ao PostgreSQL
            response = self.vn.connect_to_postgres(**self.db_config)
            logging.info(f"✅ Conexão estabelecida: {response}")
            
        except Exception as e:
            logging.error(f"❌ Erro ao conectar Vanna: {e}")
            raise
    
    def listar_training_data(self, show_details=True):
        """
        Lista todos os dados de treinamento do modelo Vanna
        
        Args:
            show_details (bool): Se deve mostrar detalhes dos dados
            
        Returns:
            pandas.DataFrame: Dados de treinamento
        """
        logging.info("📋 Listando dados de treinamento...")
        
        try:
            training_data = self.vn.get_training_data()
            
            if training_data is None or training_data.empty:
                logging.info("ℹ️ Nenhum dado de treinamento encontrado no modelo")
                return None
            
            total_records = len(training_data)
            logging.info(f"📊 Total de registros encontrados: {total_records}")
            
            if show_details:
                # Mostrar estatísticas por tipo
                if 'training_data_type' in training_data.columns:
                    tipos = training_data['training_data_type'].value_counts()
                    logging.info("📈 Distribuição por tipo:")
                    for tipo, count in tipos.items():
                        logging.info(f"   - {tipo}: {count} registros")
                
                # Mostrar algumas amostras
                logging.info("🔍 Primeiros 3 registros:")
                for i, row in training_data.head(3).iterrows():
                    logging.info(f"   [{i}] ID: {row.get('id', 'N/A')}")
                    logging.info(f"       Tipo: {row.get('training_data_type', 'N/A')}")
                    if 'question' in row and row['question']:
                        logging.info(f"       Pergunta: {str(row['question'])[:50]}...")
                    if 'content' in row:
                        logging.info(f"       Conteúdo: {str(row['content'])[:50]}...")
                    logging.info("       ---")
            
            return training_data
            
        except Exception as e:
            logging.error(f"❌ Erro ao listar training data: {e}")
            return None
    
    def realizar_backup(self, client_id=None, backup_type="both"):
        """
        Realiza backup dos dados de treinamento
        
        Args:
            client_id (str, optional): ID do cliente (None = backup global)
            backup_type (str): Tipo de backup - "json", "postgresql", "both"
            
        Returns:
            dict: Resultado do backup com paths e estatísticas
        """
        logging.info(f"💾 Iniciando backup (tipo: {backup_type}, cliente: {client_id or 'global'})...")
        
        resultado = {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "client_id": client_id,
            "backup_type": backup_type,
            "records_count": 0,
            "json_path": None,
            "postgresql_success": False,
            "errors": []
        }
        
        try:
            # Obter dados do modelo Vanna
            training_data = self.vn.get_training_data()
            
            if training_data is None or training_data.empty:
                logging.warning("⚠️ Nenhum dado encontrado para backup")
                resultado["errors"].append("Nenhum dado encontrado no modelo")
                return resultado
            
            # Converter para dict
            training_data_dict = training_data.to_dict(orient="records")
            resultado["records_count"] = len(training_data_dict)
            
            logging.info(f"📋 {len(training_data_dict)} registros obtidos do modelo")
            
            # Backup JSON
            if backup_type in ["json", "both"]:
                json_success, json_path = self._backup_to_json(training_data_dict, client_id)
                resultado["json_path"] = json_path
                if not json_success:
                    resultado["errors"].append("Falha no backup JSON")
            
            # Backup PostgreSQL
            if backup_type in ["postgresql", "both"] and DB_AVAILABLE:
                pg_success = self._backup_to_postgresql(training_data_dict, client_id)
                resultado["postgresql_success"] = pg_success
                if not pg_success:
                    resultado["errors"].append("Falha no backup PostgreSQL")
            elif backup_type in ["postgresql", "both"]:
                resultado["errors"].append("PostgreSQL não disponível")
            
            # Determinar sucesso geral
            if backup_type == "json":
                resultado["success"] = resultado["json_path"] is not None
            elif backup_type == "postgresql":
                resultado["success"] = resultado["postgresql_success"]
            else:  # both
                resultado["success"] = (resultado["json_path"] is not None or 
                                      resultado["postgresql_success"])
            
            if resultado["success"]:
                logging.info("✅ Backup concluído com sucesso!")
            else:
                logging.error("❌ Backup falhou")
            
            return resultado
            
        except Exception as e:
            logging.error(f"❌ Erro durante backup: {e}")
            resultado["errors"].append(str(e))
            return resultado
    
    def _backup_to_json(self, training_data_dict, client_id):
        """Realiza backup para arquivo JSON"""
        try:
            # Nome do arquivo com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if client_id:
                filename = f"backup_training_client_{client_id}_{timestamp}.json"
            else:
                filename = f"backup_training_global_{timestamp}.json"
            
            backup_path = os.path.join(self.backup_dir, filename)
            
            # Adicionar metadados ao backup
            backup_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "client_id": client_id,
                    "records_count": len(training_data_dict),
                    "backup_type": "vanna_training_data"
                },
                "training_data": training_data_dict
            }
            
            # Salvar arquivo
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"✅ Backup JSON salvo: {backup_path}")
            return True, backup_path
            
        except Exception as e:
            logging.error(f"❌ Erro no backup JSON: {e}")
            return False, None
    
    def _backup_to_postgresql(self, training_data_dict, client_id):
        """Realiza backup para PostgreSQL usando DatabaseManager"""
        try:
            # Usar helper para formatação consistente
            formatted_data = db_manager.format_training_data_batch(training_data_dict, client_id or "global")
            
            # Salvar no PostgreSQL
            success = db_manager.save_training_data(client_id, formatted_data)
            
            if success:
                logging.info(f"✅ Backup PostgreSQL salvo: {len(formatted_data)} registros")
                logging.info("✔ Dados salvos no PostgreSQL")
                return True
            else:
                logging.error("❌ Falha ao salvar backup no PostgreSQL")
                return False
                
        except Exception as e:
            logging.error(f"❌ Erro no backup PostgreSQL: {e}")
            return False
    
    def remover_todos_training_data(self, confirm=False):
        """
        Remove todos os dados de treinamento do modelo Vanna
        
        Args:
            confirm (bool): Confirmação de segurança
            
        Returns:
            dict: Resultado da operação
        """
        if not confirm:
            logging.warning("⚠️ ATENÇÃO: Esta operação remove TODOS os dados de treinamento!")
            logging.warning("⚠️ Execute novamente com confirm=True para confirmar")
            return {"success": False, "message": "Operação não confirmada"}
        
        logging.info("🗑️ INICIANDO REMOÇÃO DE TODOS OS DADOS DE TREINAMENTO...")
        
        resultado = {
            "success": False,
            "total_found": 0,
            "removed_count": 0,
            "failed_count": 0,
            "errors": []
        }
        
        try:
            # Obter todos os dados
            training_data = self.vn.get_training_data()
            
            if training_data is None or training_data.empty:
                logging.info("ℹ️ Nenhum dado encontrado para remover")
                resultado["success"] = True
                return resultado
            
            # Extrair IDs para remoção
            ids = self._extract_ids_from_training_data(training_data)
            resultado["total_found"] = len(ids)
            
            logging.info(f"🎯 {len(ids)} registros encontrados para remoção")
            
            # Remover cada item
            for i, item_id in enumerate(ids, 1):
                try:
                    self.vn.remove_training_data(id=item_id)
                    resultado["removed_count"] += 1
                    logging.info(f"✅ [{i}/{len(ids)}] Removido: {item_id}")
                    
                except Exception as e:
                    resultado["failed_count"] += 1
                    error_msg = f"Erro ao remover {item_id}: {e}"
                    resultado["errors"].append(error_msg)
                    logging.error(f"❌ [{i}/{len(ids)}] {error_msg}")
            
            # Verificar resultado
            if resultado["removed_count"] == resultado["total_found"]:
                resultado["success"] = True
                logging.info(f"✅ REMOÇÃO CONCLUÍDA: {resultado['removed_count']} registros removidos")
            else:
                logging.warning(f"⚠️ REMOÇÃO PARCIAL: {resultado['removed_count']}/{resultado['total_found']} removidos")
            
            return resultado
            
        except Exception as e:
            logging.error(f"❌ Erro durante remoção: {e}")
            resultado["errors"].append(str(e))
            return resultado
    
    def _extract_ids_from_training_data(self, training_data):
        """Extrai IDs dos dados de treinamento (baseado no código do flaskVanna)"""
        try:
            # Método principal: DataFrame com coluna 'id'
            ids = training_data["id"].tolist()
            return ids
            
        except (AttributeError, KeyError, TypeError):
            # Fallbacks para outros formatos
            logging.warning("⚠️ Usando fallback para extração de IDs")
            
            if isinstance(training_data, list):
                if training_data and isinstance(training_data[0], dict):
                    ids = [item["id"] for item in training_data if "id" in item]
                else:
                    ids = list(training_data)
            elif isinstance(training_data, dict):
                ids = [training_data["id"]] if "id" in training_data else []
            else:
                ids = []
            
            return ids
    
    def restaurar_backup(self, backup_path=None, client_id=None):
        """
        Restaura dados de treinamento a partir de backup
        
        Args:
            backup_path (str): Caminho para arquivo de backup JSON
            client_id (str): ID do cliente (para backup PostgreSQL)
            
        Returns:
            dict: Resultado da restauração
        """
        logging.info("🔄 Iniciando restauração de backup...")
        
        resultado = {
            "success": False,
            "source": None,
            "records_loaded": 0,
            "trained_count": 0,
            "errors": []
        }
        
        try:
            training_data = None
            
            # Restaurar do arquivo JSON
            if backup_path:
                training_data = self._load_from_json_backup(backup_path)
                resultado["source"] = f"JSON: {backup_path}"
            
            # Restaurar do PostgreSQL
            elif client_id is not None and DB_AVAILABLE:
                training_data = db_manager.load_training_data(client_id)
                resultado["source"] = f"PostgreSQL: cliente {client_id}"
            
            # Restaurar de backup global PostgreSQL
            elif DB_AVAILABLE:
                training_data = db_manager.load_training_data(None)  # Dados globais
                resultado["source"] = "PostgreSQL: backup global"
            
            else:
                resultado["errors"].append("Nenhuma fonte de backup especificada ou disponível")
                return resultado
            
            if not training_data:
                resultado["errors"].append("Nenhum dado encontrado na fonte de backup")
                return resultado
            
            resultado["records_loaded"] = len(training_data)
            logging.info(f"📋 {len(training_data)} registros carregados de {resultado['source']}")
            
            # Aplicar treinamento no modelo Vanna
            for item in training_data:
                try:
                    tipo = item.get("training_data_type", "").lower()
                    conteudo = item.get("content", "").strip()
                    pergunta = item.get("question", "").strip()
                    
                    if not conteudo:
                        continue
                    
                    if tipo == "ddl":
                        self.vn.train(ddl=conteudo)
                        resultado["trained_count"] += 1
                    elif tipo == "sql" and pergunta:
                        self.vn.train(sql=conteudo, question=pergunta)
                        resultado["trained_count"] += 1
                    elif tipo == "documentation":
                        self.vn.train(documentation=conteudo)
                        resultado["trained_count"] += 1
                    
                except Exception as e:
                    error_msg = f"Erro ao treinar item {item.get('id', 'N/A')}: {e}"
                    resultado["errors"].append(error_msg)
                    logging.error(f"❌ {error_msg}")
            
            resultado["success"] = resultado["trained_count"] > 0
            
            if resultado["success"]:
                logging.info(f"✅ Restauração concluída: {resultado['trained_count']} itens treinados")
                logging.info("✔ Dados carregados e aplicados ao modelo")
            else:
                logging.warning("⚠️ Nenhum item foi treinado com sucesso")
            
            return resultado
            
        except Exception as e:
            logging.error(f"❌ Erro durante restauração: {e}")
            resultado["errors"].append(str(e))
            return resultado
    
    def _load_from_json_backup(self, backup_path):
        """Carrega dados de backup JSON"""
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            
            # Verificar formato do backup
            if "training_data" in backup_data:
                return backup_data["training_data"]
            elif isinstance(backup_data, list):
                return backup_data
            else:
                raise ValueError("Formato de backup não reconhecido")
                
        except Exception as e:
            logging.error(f"❌ Erro ao carregar backup JSON: {e}")
            return None
    
    def listar_backups(self):
        """Lista todos os backups disponíveis"""
        logging.info("📁 Listando backups disponíveis...")
        
        backups = {
            "json_backups": [],
            "postgresql_clients": []
        }
        
        # Backups JSON
        try:
            if os.path.exists(self.backup_dir):
                for filename in os.listdir(self.backup_dir):
                    if filename.endswith('.json') and 'backup_training' in filename:
                        filepath = os.path.join(self.backup_dir, filename)
                        stat = os.stat(filepath)
                        
                        backups["json_backups"].append({
                            "filename": filename,
                            "path": filepath,
                            "size_mb": round(stat.st_size / (1024*1024), 2),
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                
                logging.info(f"📄 {len(backups['json_backups'])} backups JSON encontrados")
        except Exception as e:
            logging.error(f"❌ Erro ao listar backups JSON: {e}")
        
        # Backups PostgreSQL
        if DB_AVAILABLE:
            try:
                # Listar clientes com dados
                clients = db_manager.get_training_data_ids(None)  # Método para listar todos os clientes
                backups["postgresql_clients"] = list(set([id.split('-')[0] for id in clients if '-' in id]))
                logging.info(f"🗄️ {len(backups['postgresql_clients'])} clientes com dados no PostgreSQL")
            except Exception as e:
                logging.error(f"❌ Erro ao listar backups PostgreSQL: {e}")
        
        return backups
    
    def sincronizar_dados(self, direcao="vanna_to_postgresql", client_id=None):
        """
        Sincroniza dados entre modelo Vanna e PostgreSQL
        
        Args:
            direcao (str): "vanna_to_postgresql" ou "postgresql_to_vanna"
            client_id (str): ID do cliente (para PostgreSQL)
        
        Returns:
            dict: Resultado da sincronização
        """
        logging.info(f"🔄 Iniciando sincronização: {direcao}")
        
        resultado = {
            "success": False,
            "direction": direcao,
            "client_id": client_id,
            "source_count": 0,
            "target_count": 0,
            "synced_count": 0,
            "errors": []
        }
        
        try:
            if direcao == "vanna_to_postgresql":
                # Vanna → PostgreSQL
                vanna_data = self.vn.get_training_data()
                
                if vanna_data is None or vanna_data.empty:
                    logging.info("ℹ️ Nenhum dado no modelo Vanna para sincronizar")
                    resultado["source_count"] = 0
                    resultado["success"] = True
                    return resultado
                
                vanna_data_dict = vanna_data.to_dict(orient="records")
                resultado["source_count"] = len(vanna_data_dict)
                
                # Salvar no PostgreSQL
                if DB_AVAILABLE:
                    success = db_manager.save_training_data(client_id, vanna_data_dict)
                    if success:
                        resultado["synced_count"] = len(vanna_data_dict)
                        resultado["success"] = True
                        logging.info(f"✅ {len(vanna_data_dict)} registros sincronizados: Vanna → PostgreSQL")
                    else:
                        resultado["errors"].append("Falha ao salvar no PostgreSQL")
                else:
                    resultado["errors"].append("PostgreSQL não disponível")
            
            elif direcao == "postgresql_to_vanna":
                # PostgreSQL → Vanna
                if not DB_AVAILABLE:
                    resultado["errors"].append("PostgreSQL não disponível")
                    return resultado
                
                pg_data = db_manager.load_training_data(client_id)
                
                if not pg_data:
                    logging.info("ℹ️ Nenhum dado no PostgreSQL para sincronizar")
                    resultado["source_count"] = 0
                    resultado["success"] = True
                    return resultado
                
                resultado["source_count"] = len(pg_data)
                
                # Aplicar ao modelo Vanna
                for item in pg_data:
                    try:
                        tipo = item.get("training_data_type", "").lower()
                        conteudo = item.get("content", "").strip()
                        pergunta = item.get("question", "").strip()
                        
                        if not conteudo:
                            continue
                        
                        if tipo == "ddl":
                            self.vn.train(ddl=conteudo)
                            resultado["synced_count"] += 1
                        elif tipo == "sql" and pergunta:
                            self.vn.train(sql=conteudo, question=pergunta)
                            resultado["synced_count"] += 1
                        elif tipo == "documentation":
                            self.vn.train(documentation=conteudo)
                            resultado["synced_count"] += 1
                    
                    except Exception as e:
                        error_msg = f"Erro ao sincronizar item: {e}"
                        resultado["errors"].append(error_msg)
                        logging.error(f"❌ {error_msg}")
                
                resultado["success"] = resultado["synced_count"] > 0
                logging.info(f"✅ {resultado['synced_count']} registros sincronizados: PostgreSQL → Vanna")
            
            else:
                resultado["errors"].append(f"Direção inválida: {direcao}")
            
            return resultado
            
        except Exception as e:
            logging.error(f"❌ Erro durante sincronização: {e}")
            resultado["errors"].append(str(e))
            return resultado
    
    def comparar_dados(self, client_id=None):
        """
        Compara dados entre modelo Vanna e PostgreSQL
        
        Args:
            client_id (str): ID do cliente (para PostgreSQL)
        
        Returns:
            dict: Comparação detalhada dos dados
        """
        logging.info("🔍 Comparando dados entre Vanna e PostgreSQL...")
        
        resultado = {
            "success": False,
            "client_id": client_id,
            "vanna_count": 0,
            "postgresql_count": 0,
            "differences": {
                "only_in_vanna": 0,
                "only_in_postgresql": 0,
                "content_mismatch": 0
            },
            "details": []
        }
        
        try:
            # Dados do Vanna
            vanna_data = self.vn.get_training_data()
            if vanna_data is not None and not vanna_data.empty:
                resultado["vanna_count"] = len(vanna_data)
                vanna_items = vanna_data.to_dict(orient="records")
            else:
                vanna_items = []
            
            # Dados do PostgreSQL
            if DB_AVAILABLE:
                pg_data = db_manager.load_training_data(client_id)
                resultado["postgresql_count"] = len(pg_data) if pg_data else 0
                pg_items = pg_data or []
            else:
                resultado["details"].append("PostgreSQL não disponível para comparação")
                pg_items = []
            
            # Criar índices para comparação
            vanna_index = {
                item.get('id', f"temp_{i}"): item 
                for i, item in enumerate(vanna_items)
            }
            
            pg_index = {
                item.get('id', f"temp_{i}"): item 
                for i, item in enumerate(pg_items)
            }
            
            # Analisar diferenças
            vanna_ids = set(vanna_index.keys())
            pg_ids = set(pg_index.keys())
            
            # IDs únicos em cada fonte
            only_vanna = vanna_ids - pg_ids
            only_pg = pg_ids - vanna_ids
            common_ids = vanna_ids & pg_ids
            
            resultado["differences"]["only_in_vanna"] = len(only_vanna)
            resultado["differences"]["only_in_postgresql"] = len(only_pg)
            
            # Verificar diferenças de conteúdo nos IDs comuns
            content_mismatches = 0
            for common_id in common_ids:
                vanna_item = vanna_index[common_id]
                pg_item = pg_index[common_id]
                
                # Comparar campos principais
                vanna_content = vanna_item.get("content", "").strip()
                pg_content = pg_item.get("content", "").strip()
                
                if vanna_content != pg_content:
                    content_mismatches += 1
            
            resultado["differences"]["content_mismatch"] = content_mismatches
            
            # Adicionar detalhes
            if only_vanna:
                resultado["details"].append(f"{len(only_vanna)} itens apenas no Vanna")
            if only_pg:
                resultado["details"].append(f"{len(only_pg)} itens apenas no PostgreSQL")
            if content_mismatches:
                resultado["details"].append(f"{content_mismatches} itens com conteúdo diferente")
            
            if not any(resultado["differences"].values()):
                resultado["details"].append("✅ Dados sincronizados entre Vanna e PostgreSQL")
            
            resultado["success"] = True
            
            logging.info(f"📊 Comparação concluída:")
            logging.info(f"   Vanna: {resultado['vanna_count']} registros")
            logging.info(f"   PostgreSQL: {resultado['postgresql_count']} registros")
            logging.info(f"   Diferenças: {sum(resultado['differences'].values())}")
            
            return resultado
            
        except Exception as e:
            logging.error(f"❌ Erro durante comparação: {e}")
            resultado["details"].append(f"Erro: {str(e)}")
            return resultado

def main():
    """Função principal para uso via linha de comando"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Controlador de Training Data do Vanna - Backup, Remoção e Restauração",
        epilog="""
EXEMPLOS DE USO:
  %(prog)s list                                    # Listar dados atuais
  %(prog)s backup --backup-type both              # Backup completo (JSON + PostgreSQL)
  %(prog)s backup --client-id cli01 --backup-type postgresql  # Backup PostgreSQL específico
  %(prog)s remove --confirm                        # Remover TODOS os dados (CUIDADO!)
  %(prog)s restore --client-id cli01              # Restaurar do PostgreSQL
  %(prog)s restore --backup-path backups/backup.json         # Restaurar de JSON
  %(prog)s list-backups                           # Listar backups disponíveis

CONFIGURAÇÃO:
  Crie arquivo .env com: API_KEY, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("action", choices=["list", "backup", "remove", "restore", "list-backups", "status", "sync", "compare"],
                       help="Ação a ser executada")
    parser.add_argument("--client-id", help="ID do cliente (opcional)")
    parser.add_argument("--backup-type", choices=["json", "postgresql", "both"], 
                       default="both", help="Tipo de backup (padrão: both)")
    parser.add_argument("--backup-path", help="Caminho para arquivo de backup JSON")
    parser.add_argument("--confirm", action="store_true", 
                       help="Confirmar operações perigosas (obrigatório para remove)")
    parser.add_argument("--details", action="store_true",
                       help="Mostrar detalhes extras na listagem")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Modo verboso com logs detalhados")
    parser.add_argument("--direction", choices=["vanna_to_postgresql", "postgresql_to_vanna"],
                       default="vanna_to_postgresql", help="Direção da sincronização")
    
    args = parser.parse_args()
    
    # Configurar nível de log baseado em verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("🔍 Modo verboso ativado")
    
    try:
        controller = VannaTrainingController()
        
        if args.action == "list":
            controller.listar_training_data(show_details=args.details)
        
        elif args.action == "backup":
            print(f"\n💾 Iniciando backup (tipo: {args.backup_type}, cliente: {args.client_id or 'global'})...")
            resultado = controller.realizar_backup(args.client_id, args.backup_type)
            
            print(f"\n📊 RESULTADO DO BACKUP:")
            print(f"   ✅ Sucesso: {resultado['success']}")
            print(f"   📋 Registros: {resultado['records_count']}")
            print(f"   🕐 Timestamp: {resultado['timestamp']}")
            if resultado['json_path']:
                print(f"   📄 Arquivo JSON: {resultado['json_path']}")
            print(f"   🗄️ PostgreSQL: {'✅ Sucesso' if resultado['postgresql_success'] else '❌ Falha'}")
            if resultado['errors']:
                print(f"   ❌ Erros: {'; '.join(resultado['errors'])}")
            
            print(f"\n📋 RESUMO:")
            print(f"   • Backup Type: {resultado['backup_type']}")
            print(f"   • Client ID: {resultado['client_id'] or 'Global'}")
            print(f"   • Records: {resultado['records_count']}")
        
        elif args.action == "remove":
            if not args.confirm:
                print("❌ ERRO: Operação 'remove' requer --confirm para segurança")
                print("   Esta operação remove TODOS os dados de treinamento do modelo!")
                print("   Use: python vanna_training_controller.py remove --confirm")
                sys.exit(1)
            
            print("\n🗑️ ATENÇÃO: Removendo TODOS os dados de treinamento...")
            resultado = controller.remover_todos_training_data(args.confirm)
            
            print(f"\n🗑️ RESULTADO DA REMOÇÃO:")
            print(f"   ✅ Sucesso: {resultado['success']}")
            print(f"   📋 Encontrados: {resultado.get('total_found', 0)}")
            print(f"   ✅ Removidos: {resultado.get('removed_count', 0)}")
            print(f"   ❌ Falharam: {resultado.get('failed_count', 0)}")
            if resultado.get('errors'):
                print(f"   ⚠️ Erros: {len(resultado['errors'])} erros ocorreram")
        
        elif args.action == "restore":
            if not args.backup_path and not args.client_id:
                print("❌ ERRO: Especifique --backup-path (para JSON) ou --client-id (para PostgreSQL)")
                sys.exit(1)
            
            source = args.backup_path if args.backup_path else f"PostgreSQL (cliente: {args.client_id})"
            print(f"\n🔄 Restaurando dados de: {source}")
            
            resultado = controller.restaurar_backup(args.backup_path, args.client_id)
            
            print(f"\n🔄 RESULTADO DA RESTAURAÇÃO:")
            print(f"   ✅ Sucesso: {resultado['success']}")
            print(f"   📋 Carregados: {resultado['records_loaded']}")
            print(f"   🎯 Treinados: {resultado['trained_count']}")
            print(f"   📍 Fonte: {resultado['source']}")
            if resultado.get('errors'):
                print(f"   ⚠️ Erros: {len(resultado['errors'])} erros durante treinamento")
        
        elif args.action == "list-backups":
            backups = controller.listar_backups()
            
            print(f"\n📁 BACKUPS DISPONÍVEIS:")
            
            print(f"\n📄 BACKUPS JSON ({len(backups['json_backups'])} arquivos):")
            if backups['json_backups']:
                for backup in sorted(backups['json_backups'], key=lambda x: x['modified'], reverse=True):
                    print(f"   • {backup['filename']}")
                    print(f"     📏 Tamanho: {backup['size_mb']} MB")
                    print(f"     🕐 Modificado: {backup['modified']}")
                    print(f"     � Path: {backup['path']}")
                    print()
            else:
                print("   Nenhum backup JSON encontrado")
            
            print(f"\n🗄️ BACKUPS POSTGRESQL ({len(backups['postgresql_clients'])} clientes):")
            if backups['postgresql_clients']:
                for client in sorted(backups['postgresql_clients']):
                    print(f"   • Cliente: {client}")
            else:
                print("   Nenhum backup PostgreSQL encontrado")
        
        elif args.action == "status":
            # Nova funcionalidade: status detalhado
            print("\n📊 STATUS DO SISTEMA:")
            
            # Status do modelo Vanna
            training_data = controller.listar_training_data(show_details=False)
            if training_data is not None:
                print(f"   🎯 Modelo Vanna: {len(training_data)} registros")
            else:
                print("   🎯 Modelo Vanna: Vazio")
            
            # Status PostgreSQL
            if DB_AVAILABLE:
                try:
                    pg_ids = db_manager.get_training_data_ids(None)
                    print(f"   🗄️ PostgreSQL: {len(pg_ids)} registros")
                except:
                    print("   🗄️ PostgreSQL: Erro de conexão")
            else:
                print("   🗄️ PostgreSQL: Não disponível")
            
            # Status backups JSON
            backups = controller.listar_backups()
            print(f"   📄 Backups JSON: {len(backups['json_backups'])} arquivos")
            
            # Configurações
            print(f"\n⚙️ CONFIGURAÇÕES:")
            print(f"   • API Key: {'✅ Configurada' if controller.api_key else '❌ Faltando'}")
            print(f"   • DB Host: {controller.db_config.get('host', 'N/A')}")
            print(f"   • DB Name: {controller.db_config.get('dbname', 'N/A')}")
            print(f"   • Backup Dir: {controller.backup_dir}")
        
        elif args.action == "sync":
            print(f"\n🔄 Sincronizando dados ({args.direction})...")
            resultado = controller.sincronizar_dados(args.direction, args.client_id)
            
            print(f"\n🔄 RESULTADO DA SINCRONIZAÇÃO:")
            print(f"   ✅ Sucesso: {resultado['success']}")
            print(f"   📍 Direção: {resultado['direction']}")
            print(f"   📋 Origem: {resultado['source_count']} registros")
            print(f"   🎯 Sincronizados: {resultado['synced_count']} registros")
            print(f"   👤 Cliente: {resultado['client_id'] or 'Global'}")
            if resultado.get('errors'):
                print(f"   ❌ Erros: {'; '.join(resultado['errors'])}")
        
        elif args.action == "compare":
            print(f"\n🔍 Comparando dados (Cliente: {args.client_id or 'Global'})...")
            resultado = controller.comparar_dados(args.client_id)
            
            print(f"\n🔍 RESULTADO DA COMPARAÇÃO:")
            print(f"   ✅ Sucesso: {resultado['success']}")
            print(f"   🎯 Vanna: {resultado['vanna_count']} registros")
            print(f"   🗄️ PostgreSQL: {resultado['postgresql_count']} registros")
            print(f"   👤 Cliente: {resultado['client_id'] or 'Global'}")
            
            print(f"\n📊 DIFERENÇAS ENCONTRADAS:")
            diffs = resultado['differences']
            print(f"   • Apenas no Vanna: {diffs['only_in_vanna']}")
            print(f"   • Apenas no PostgreSQL: {diffs['only_in_postgresql']}")
            print(f"   • Conteúdo divergente: {diffs['content_mismatch']}")
            
            if resultado.get('details'):
                print(f"\n📋 DETALHES:")
                for detail in resultado['details']:
                    print(f"   • {detail}")
    
    except KeyboardInterrupt:
        print("\n⏹️ Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        logging.error(f"❌ Erro na execução: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
