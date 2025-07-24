#!/usr/bin/env python3
# teste_persistencia_postgresql.py
# Script isolado para diagnosticar problemas de persistência

import os
import sys
import json
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

# Adicionar o diretório src ao path para importar database_manager
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from database_manager import db_manager
    print("✅ DatabaseManager importado com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar DatabaseManager: {e}")
    sys.exit(1)

def debug_env_vars():
    """Verifica variáveis de ambiente"""
    print("\n=== 🔍 DEBUG VARIÁVEIS DE AMBIENTE ===")
    
    load_dotenv()
    
    vars_to_check = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    
    for var in vars_to_check:
        value = os.getenv(var)
        if var == 'DB_PASSWORD':
            display_value = '***' if value else 'None'
        else:
            display_value = value or 'None'
        print(f"  {var}: {display_value}")
    
    # Verificar se todas estão definidas
    missing = [var for var in vars_to_check if not os.getenv(var)]
    if missing:
        print(f"⚠️ Variáveis faltando: {missing}")
        return False
    else:
        print("✅ Todas as variáveis de ambiente estão definidas")
        return True

def test_direct_connection():
    """Testa conexão direta ao PostgreSQL"""
    print("\n=== 🔗 TESTE CONEXÃO DIRETA POSTGRESQL ===")
    
    try:
        conn_params = {
            'host': os.getenv("DB_HOST"),
            'port': os.getenv("DB_PORT"),
            'dbname': os.getenv("DB_NAME"),
            'user': os.getenv("DB_USER"),
            'password': os.getenv("DB_PASSWORD")
        }
        
        print(f"  Tentando conectar com:")
        for key, value in conn_params.items():
            if key == 'password':
                print(f"    {key}: {'***' if value else 'None'}")
            else:
                print(f"    {key}: {value}")
        
        conn = psycopg2.connect(**conn_params)
        print("✅ Conexão direta PostgreSQL: SUCESSO")
        
        cursor = conn.cursor()
        
        # Verificar versão
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"📄 PostgreSQL Version: {version}")
        
        # Verificar se tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'ai_training_data'
            );
        """)
        table_exists = cursor.fetchone()[0]
        print(f"📋 Tabela ai_training_data existe: {table_exists}")
        
        if table_exists:
            # Verificar estrutura da tabela
            cursor.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'ai_training_data'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            print("📊 Estrutura da tabela:")
            for col_name, data_type, nullable in columns:
                print(f"    {col_name}: {data_type} (NULL: {nullable})")
            
            # Verificar quantos registros existem
            cursor.execute("SELECT COUNT(*) FROM ai_training_data;")
            count = cursor.fetchone()[0]
            print(f"📈 Registros na tabela: {count}")
        else:
            print("❌ Tabela ai_training_data não existe!")
            print("   Você precisa criar a tabela primeiro.")
        
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Erro de conexão PostgreSQL: {e}")
        print("   Verifique:")
        print("   - Se o PostgreSQL está rodando")
        print("   - Se as credenciais estão corretas")
        print("   - Se o usuário tem permissão para conectar")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def test_database_manager():
    """Testa a classe DatabaseManager"""
    print("\n=== 🎯 TESTE DATABASE MANAGER ===")
    
    # Dados de teste
    test_data = [
        {
            "id": f"test-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "training_data_type": "sql",
            "question": "Teste de inserção via DatabaseManager",
            "content": "SELECT 'teste_persistencia' as resultado;"
        }
    ]
    
    try:
        print(f"  📊 Dados de teste: {test_data}")
        
        # Tentar salvar
        print("  🎯 Chamando db_manager.save_training_data...")
        success = db_manager.save_training_data(client_id=999, training_data=test_data)
        print(f"  📋 Resultado save_training_data: {success}")
        
        if success:
            # Verificar se foi realmente inserido
            print("  🔍 Verificando se foi inserido...")
            
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD")
            )
            cursor = conn.cursor()
            
            external_id = test_data[0]["id"]
            cursor.execute(
                "SELECT * FROM ai_training_data WHERE external_id = %s AND client_id = %s",
                (external_id, 999)
            )
            result = cursor.fetchone()
            
            if result:
                print(f"✅ Registro inserido com sucesso: {result}")
                
                # Cleanup - remover registro de teste
                cursor.execute(
                    "DELETE FROM ai_training_data WHERE external_id = %s AND client_id = %s",
                    (external_id, 999)
                )
                conn.commit()
                print("🧹 Registro de teste removido")
            else:
                print("❌ Registro não encontrado no banco!")
                print("   save_training_data retornou True mas nada foi inserido")
            
            conn.close()
            return result is not None
        else:
            print("❌ save_training_data retornou False")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste DatabaseManager: {e}")
        import traceback
        print(f"📍 Traceback: {traceback.format_exc()}")
        return False

def test_load_training_data():
    """Testa carregamento de dados"""
    print("\n=== 📥 TESTE LOAD TRAINING DATA ===")
    
    try:
        # Tentar carregar dados globais
        print("  🔍 Carregando dados globais (client_id=None)...")
        global_data = db_manager.load_training_data(client_id=None)
        print(f"  📊 Dados globais carregados: {len(global_data) if global_data else 0} itens")
        
        # Tentar carregar dados de cliente específico
        print("  🔍 Carregando dados do cliente 1...")
        client_data = db_manager.load_training_data(client_id=1)
        print(f"  📊 Dados cliente 1: {len(client_data) if client_data else 0} itens")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste load_training_data: {e}")
        return False

def main():
    """Função principal de diagnóstico"""
    print("=" * 60)
    print("🔬 DIAGNÓSTICO PERSISTÊNCIA POSTGRESQL - SOLIRIS")
    print("=" * 60)
    
    # 1. Verificar variáveis de ambiente
    env_ok = debug_env_vars()
    
    if not env_ok:
        print("\n❌ FALHA: Variáveis de ambiente incompletas")
        print("   Configure o arquivo .env com todas as variáveis necessárias")
        return False
    
    # 2. Testar conexão direta
    conn_ok = test_direct_connection()
    
    if not conn_ok:
        print("\n❌ FALHA: Não foi possível conectar ao PostgreSQL")
        print("   Resolva os problemas de conexão antes de continuar")
        return False
    
    # 3. Testar DatabaseManager
    manager_ok = test_database_manager()
    
    if not manager_ok:
        print("\n❌ FALHA: DatabaseManager não está funcionando corretamente")
        print("   Há problemas na implementação de save_training_data")
        return False
    
    # 4. Testar carregamento
    load_ok = test_load_training_data()
    
    if not load_ok:
        print("\n❌ FALHA: Problema no carregamento de dados")
        return False
    
    print("\n" + "=" * 60)
    print("✅ DIAGNÓSTICO CONCLUÍDO - TUDO FUNCIONANDO!")
    print("=" * 60)
    print("\n🎯 PRÓXIMOS PASSOS:")
    print("  1. Se todos os testes passaram, o problema pode estar no fluxo da aplicação")
    print("  2. Adicione logs nas funções do vanna_core.py para rastrear as chamadas")
    print("  3. Verifique se salvar_training_filtrado() está sendo chamado")
    print("  4. Monitore os logs durante uma sessão real da aplicação")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erro inesperado: {e}")
        import traceback
        print(f"📍 Traceback: {traceback.format_exc()}")
        sys.exit(1)
