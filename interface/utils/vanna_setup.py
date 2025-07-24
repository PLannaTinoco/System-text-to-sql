#!/usr/bin/env python3
"""
Versão do vanna_core adaptada para interface Streamlit
Remove inputs interativos e permite configuração via parâmetros
"""

import os
import json
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adicionar src ao path para importar database_manager
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from database_manager import db_manager
    print("✅ [VANNA_SETUP] DatabaseManager importado com sucesso")
except ImportError as e:
    print(f"❌ [VANNA_SETUP] Erro ao importar DatabaseManager: {e}")
    db_manager = None

def verificar_tabela_existe(nome_tabela: str) -> bool:
    """Verifica se uma tabela existe no banco de dados"""
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """, (nome_tabela,))
        
        existe = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return existe
        
    except Exception as e:
        logging.error(f"Erro ao verificar se tabela {nome_tabela} existe: {e}")
        return False

def verificar_usuario_tem_dados(id_client: int) -> dict:
    """Verifica quais dados o usuário possui no banco"""
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        
        cursor = conn.cursor()
        
        # Busca todas as tabelas do usuário
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE %s
            ORDER BY table_name
        """, (f"cli{id_client:02d}_%",))
        
        tabelas = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        dados = {
            "tabelas": tabelas,
            "tem_kpis": any("kpis" in t for t in tabelas),
            "tem_dados": len(tabelas) > 0,
            "total_tabelas": len(tabelas)
        }
        
        return dados
        
    except Exception as e:
        logging.error(f"Erro ao verificar dados do usuário {id_client}: {e}")
        return {"tabelas": [], "tem_kpis": False, "tem_dados": False, "total_tabelas": 0}

def setup_treinamento_cliente_interface(id_client: int, config: dict):
    """
    Versão adaptada para Streamlit - sem inputs interativos
    Recebe configurações via dict config em vez de perguntar ao usuário
    Agora usa DatabaseManager para carregar training_data do PostgreSQL
    """
    from vanna.remote import VannaDefault
    from vanna_core import (
        gerar_plan_treinamento, 
        treinar_com_kpis, 
        treinar_com_ddl,
        load_training_data
    )
    
    print(f"🚀 [VANNA_SETUP] Iniciando setup para cliente {id_client}")
    
    # Inicializa Vanna
    vn = VannaDefault(model="jarves", api_key=os.getenv("API_KEY"))
    vn.connect_to_postgres(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    # 1) Tenta carregar dados do PostgreSQL usando DatabaseManager
    try:
        print(f"📚 [VANNA_SETUP] Tentando carregar training_data do PostgreSQL para cliente {id_client}")
        
        if db_manager:
            # Usa novo método com DatabaseManager
            training_data = db_manager.load_training_data(id_client)
            
            if training_data:
                print(f"✅ [VANNA_SETUP] {len(training_data)} registros carregados do PostgreSQL")
                
                # Aplicar training_data no modelo Vanna
                trained_items = 0
                for item in training_data:
                    try:
                        tipo = item.get("training_data_type")
                        conteudo = item.get("content")
                        pergunta = item.get("question")

                        if not conteudo:
                            continue

                        if tipo == "ddl":
                            vn.train(ddl=conteudo)
                            trained_items += 1
                        elif tipo == "sql":
                            if pergunta:
                                vn.train(sql=conteudo, question=pergunta)
                                trained_items += 1
                        elif tipo == "documentation":
                            vn.train(documentation=conteudo)
                            trained_items += 1
                            
                    except Exception as item_error:
                        print(f"⚠️ [VANNA_SETUP] Erro ao treinar item {item.get('id')}: {item_error}")
                
                print(f"✅ [VANNA_SETUP] {trained_items} itens aplicados ao modelo Vanna")
                print("✔ Dados carregados do PostgreSQL")
                return vn
            else:
                print(f"ℹ️ [VANNA_SETUP] Nenhum training_data encontrado no PostgreSQL para cliente {id_client}")
        else:
            print("⚠️ [VANNA_SETUP] DatabaseManager não disponível")
            
    except Exception as e:
        print(f"⚠️ [VANNA_SETUP] Erro ao carregar training data: {e}")
        logging.warning("Erro ao carregar training data: %s", e)

    # Verifica se já existe um arquivo de plan
    nome_plan = f"plan_cliente_{id_client:02d}.json"
    path_plan = os.path.join("arq", nome_plan)
    
    plan_dict = None
    
    if os.path.exists(path_plan):
        try:
            # Sempre usa o plano existente se houver
            with open(path_plan, "r", encoding="utf-8") as f:
                plan_dict = json.load(f)
            logging.info("Usando plano existente: %s", path_plan)
        except Exception as e:
            logging.error("Erro ao carregar plano existente: %s", e)
            plan_dict = gerar_plan_treinamento(id_client, vn, salvar_em_arquivo=True)
    else:
        # Gera novo plano
        try:
            plan_dict = gerar_plan_treinamento(id_client, vn, salvar_em_arquivo=True)
            logging.info("Novo plano gerado e salvo.")
        except Exception as e:
            logging.error("Erro ao gerar plano: %s", e)
            return vn
   
    # 1. Treinamento do Plano (baseado na configuração)
    if config.get("treinar_plan", False) and plan_dict:
        try:
            logging.info("Treinando com plano de dados...")
            # CORREÇÃO: Garante que o plano seja passado corretamente
            if isinstance(plan_dict, dict):
                vn.train(plan=plan_dict)
            else:
                logging.warning("Plano não é um dict válido, pulando treinamento")
            logging.info("Plano de dados treinado para cliente %02d.", id_client)
        except Exception as e:
            logging.error("Erro no treinamento do plano: %s", e)
    else:
        logging.info("Etapa de treinamento do plano pulada.")

    # 2. Treinamento de KPIs (baseado na configuração)
    if config.get("treinar_kpis", False):
        try:
            logging.info("Treinando com KPIs...")
            # CORREÇÃO: Verifica se tabela de KPIs existe antes de treinar
            if verificar_tabela_existe(f"cli{id_client:02d}_kpis_definicoes"):
                treinar_com_kpis(id_client, vn)
                logging.info("KPIs treinados para cliente %02d.", id_client)
            else:
                logging.warning("Tabela de KPIs não encontrada para cliente %02d, pulando treinamento", id_client)
        except Exception as e:
            logging.error("Erro no treinamento de KPIs: %s", e)
    else:
        logging.info("Etapa de treinamento dos KPIs pulada.")

    # 3. Treinamento de DDL (baseado na configuração)
    if config.get("treinar_ddl", False):
        try:
            logging.info("Treinando com DDL das tabelas...")
            treinar_com_ddl(id_client, vn)
            logging.info("DDL treinado para cliente %02d.", id_client)
        except Exception as e:
            logging.error("Erro no treinamento de DDL: %s", e)
        logging.info("DDL treinado para cliente %02d.", id_client)
    else:
        logging.info("Etapa de treinamento das DDLs pulada.")
    
    # 4. Documentação personalizada (baseado na configuração)
    if config.get("treinar_docs", False) and config.get("documentacao"):
        logging.info("Treinando com documentação personalizada...")
        vn.train(documentation=config["documentacao"])
        logging.info("Documentação personalizada treinada para cliente %02d.", id_client)
    else:
        logging.info("Etapa de documentação personalizada pulada.")

    return vn

def executar_treinamento_completo(id_client: int, config: dict) -> bool:
    """
    Executa o treinamento completo baseado na configuração
    Retorna True se bem-sucedido, False caso contrário
    """
    try:
        # Log de início
        inicio = datetime.now()
        logging.info(f"Iniciando treinamento completo para cliente {id_client:02d}")
        
        # CORREÇÃO: Verifica integridade do cliente
        integridade = verificar_integridade_cliente(id_client)
        if "erro" in integridade:
            logging.error(f"Erro na verificação de integridade: {integridade['erro']}")
            return False
        
        logging.info(f"Cliente {id_client:02d} - {integridade['usuario']['nome']}")
        logging.info(f"Tabelas encontradas: {integridade['total_tabelas']}")
        
        # Se não tem dados, cria estrutura básica
        if not integridade["tem_dados"]:
            logging.info(f"Cliente {id_client:02d} sem dados. Criando estrutura básica...")
            criar_estrutura_basica_cliente(id_client)
        
        # Se não tem KPIs e vai treinar KPIs, cria estrutura
        if config.get("treinar_kpis", False) and not integridade["tem_kpis"]:
            logging.info(f"Criando estrutura de KPIs para cliente {id_client:02d}...")
            criar_estrutura_basica_cliente(id_client)
        
        # Executa o setup com as configurações
        vn = setup_treinamento_cliente_interface(id_client, config)
        
        if vn is None:
            logging.error(f"Falha ao inicializar Vanna para cliente {id_client:02d}")
            return False
        
        # Log de conclusão
        fim = datetime.now()
        duracao = fim - inicio
        logging.info(f"Treinamento concluído em {duracao.total_seconds():.2f} segundos")
        
        return True
        
    except Exception as e:
        logging.error(f"Erro no treinamento do cliente {id_client:02d}: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return False

def validar_configuracao_treinamento(config: dict) -> tuple[bool, list]:
    """
    Valida se a configuração de treinamento está correta
    Retorna (válido, lista_de_erros)
    """
    erros = []
    
    # Verifica se pelo menos uma opção de treinamento está ativada
    opcoes_treinamento = [
        config.get("treinar_plan", False),
        config.get("treinar_kpis", False), 
        config.get("treinar_ddl", False),
        config.get("treinar_docs", False)
    ]
    
    if not any(opcoes_treinamento):
        erros.append("Pelo menos uma opção de treinamento deve estar ativada")
    
    # Verifica documentação se necessário
    if config.get("treinar_docs", False):
        if not config.get("documentacao") or len(config.get("documentacao", "").strip()) < 10:
            erros.append("Documentação deve ter pelo menos 10 caracteres")
    
    return len(erros) == 0, erros

def obter_resumo_configuracao(config: dict) -> dict:
    """
    Retorna um resumo legível da configuração de treinamento
    """
    resumo = {
        "etapas_ativas": [],
        "etapas_inativas": [],
        "total_etapas": 0,
        "tem_documentacao": False
    }
    
    etapas = [
        ("treinar_plan", "Plano de Dados Automático"),
        ("treinar_kpis", "KPIs e Métricas"),
        ("treinar_ddl", "Estrutura das Tabelas (DDL)"),
        ("treinar_docs", "Documentação Personalizada")
    ]
    
    for chave, nome in etapas:
        if config.get(chave, False):
            resumo["etapas_ativas"].append(nome)
        else:
            resumo["etapas_inativas"].append(nome)
        resumo["total_etapas"] += 1
    
    resumo["tem_documentacao"] = bool(config.get("documentacao", "").strip())
    
    return resumo

def verificar_integridade_cliente(id_client: int) -> dict:
    """Verifica a integridade dos dados de um cliente específico"""
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        
        cursor = conn.cursor()
        
        # 1. Verifica se o usuário existe
        cursor.execute("SELECT id, nome, email FROM usuarios WHERE id = %s", (id_client,))
        usuario = cursor.fetchone()
        
        if not usuario:
            cursor.close()
            conn.close()
            return {"erro": f"Usuário com ID {id_client} não encontrado"}
        
        # 2. Busca todas as tabelas do usuário
        cursor.execute("""
            SELECT table_name, 
                   (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as colunas
            FROM information_schema.tables t
            WHERE table_schema = 'public' 
            AND table_name LIKE %s
            ORDER BY table_name
        """, (f"cli{id_client:02d}_%",))
        
        tabelas_info = cursor.fetchall()
        
        # 3. Conta registros em cada tabela
        tabelas_detalhes = []
        for nome_tabela, num_colunas in tabelas_info:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{nome_tabela}"')
                num_registros = cursor.fetchone()[0]
                tabelas_detalhes.append({
                    "nome": nome_tabela,
                    "colunas": num_colunas,
                    "registros": num_registros,
                    "tipo": "kpis" if "kpis" in nome_tabela else "dados"
                })
            except Exception as e:
                tabelas_detalhes.append({
                    "nome": nome_tabela,
                    "colunas": num_colunas,
                    "registros": 0,
                    "tipo": "erro",
                    "erro": str(e)
                })
        
        cursor.close()
        conn.close()
        
        return {
            "usuario": {"id": usuario[0], "nome": usuario[1], "email": usuario[2]},
            "tabelas": tabelas_detalhes,
            "total_tabelas": len(tabelas_detalhes),
            "tem_dados": len(tabelas_detalhes) > 0,
            "tem_kpis": any(t["tipo"] == "kpis" for t in tabelas_detalhes),
            "prefixo_esperado": f"cli{id_client:02d}_"
        }
        
    except Exception as e:
        logging.error(f"Erro ao verificar integridade do cliente {id_client}: {e}")
        return {"erro": str(e)}

def criar_estrutura_basica_cliente(id_client: int) -> bool:
    """Cria estrutura básica para um cliente (tabelas KPIs, etc.)"""
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        
        cursor = conn.cursor()
        
        # 1. Cria tabela de KPIs básica se não existir
        nome_kpis = f"cli{id_client:02d}_kpis_definicoes"
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS "{nome_kpis}" (
                id SERIAL PRIMARY KEY,
                nome_kpi VARCHAR(255) NOT NULL,
                descricao TEXT,
                formula_sql TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Insere alguns KPIs básicos se a tabela estiver vazia
        cursor.execute(f'SELECT COUNT(*) FROM "{nome_kpis}"')
        if cursor.fetchone()[0] == 0:
            kpis_basicos = [
                ("Total de Registros", "Conta total de registros em tabelas do usuário", "SELECT COUNT(*) as total"),
                ("Tabelas Disponíveis", "Número de tabelas disponíveis", "SELECT COUNT(*) as tabelas"),
                ("Última Atualização", "Data da última modificação", "SELECT CURRENT_TIMESTAMP as ultima_atualizacao")
            ]
            
            for nome, desc, formula in kpis_basicos:
                cursor.execute(f'''
                    INSERT INTO "{nome_kpis}" (nome_kpi, descricao, formula_sql)
                    VALUES (%s, %s, %s)
                ''', (nome, desc, formula))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logging.info(f"Estrutura básica criada para cliente {id_client:02d}")
        return True
        
    except Exception as e:
        logging.error(f"Erro ao criar estrutura básica para cliente {id_client}: {e}")
        return False

def has_training_data(client_id: int) -> bool:
    """
    Verifica se há dados de treinamento salvos para um cliente.
    
    Args:
        client_id: ID do cliente
        
    Returns:
        bool: True se há dados salvos, False caso contrário
    """
    try:
        if not db_manager:
            print("⚠️ [VANNA_SETUP] DatabaseManager não disponível")
            return False
            
        # Usa DatabaseManager para verificar PostgreSQL
        ids = db_manager.get_training_data_ids(client_id)
        count = len(ids) if ids else 0
        print(f"📊 [VANNA_SETUP] Cliente {client_id} tem {count} registros no PostgreSQL")
        return count > 0
            
    except Exception as e:
        print(f"⚠️ [VANNA_SETUP] Erro ao verificar training data: {e}")
        return False
