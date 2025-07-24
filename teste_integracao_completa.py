#!/usr/bin/env python3
"""
Teste de integração completa da migração PostgreSQL.
Simula um ciclo completo: login → treinamento → salvamento → cleanup → reinício → verificação.
"""

import os
import sys
import json
from datetime import datetime

# Adicionar src ao path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
if src_path not in sys.path:
    sys.path.append(src_path)

# Importar módulos do projeto
from database_manager import db_manager
from dotenv import load_dotenv

def simular_sessao_usuario(client_id=1):
    """Simula uma sessão completa de usuário"""
    print(f"\n🎬 [SIMULAÇÃO] Iniciando sessão para cliente {client_id}")
    
    # 1. VERIFICAR ESTADO INICIAL
    print("\n📊 [ETAPA 1] Verificando estado inicial...")
    try:
        dados_iniciais = db_manager.load_training_data(client_id)
        print(f"   - Dados iniciais no banco: {len(dados_iniciais) if dados_iniciais else 0} registros")
        
        # Listar IDs existentes
        ids_iniciais = db_manager.get_training_data_ids(client_id)
        print(f"   - IDs iniciais: {ids_iniciais[:5]}{'...' if len(ids_iniciais) > 5 else ''}")
        
    except Exception as e:
        print(f"   ❌ Erro ao verificar estado inicial: {e}")
        return False
    
    # 2. SIMULAR TREINAMENTO FICTÍCIO
    print("\n🧠 [ETAPA 2] Simulando treinamento fictício...")
    try:
        # Dados de teste que simulam o que viria da Vanna
        mock_training_data = [
            {
                "id": f"integ-test-{client_id}-sql-01",
                "training_data_type": "sql",
                "question": "Quantos clientes temos cadastrados?",
                "content": "SELECT COUNT(*) FROM clientes;",
                "metadata": {"source": "integration_test", "timestamp": datetime.now().isoformat()}
            },
            {
                "id": f"integ-test-{client_id}-ddl-01", 
                "training_data_type": "ddl",
                "question": "",
                "content": "CREATE TABLE clientes (id SERIAL PRIMARY KEY, nome VARCHAR(255));",
                "metadata": {"source": "integration_test", "timestamp": datetime.now().isoformat()}
            },
            {
                "id": f"integ-test-{client_id}-doc-01",
                "training_data_type": "documentation",
                "question": "",
                "content": "A tabela clientes armazena informações básicas dos clientes da empresa.",
                "metadata": {"source": "integration_test", "timestamp": datetime.now().isoformat()}
            }
        ]
        
        print(f"   - Preparados {len(mock_training_data)} itens de treinamento")
        for item in mock_training_data:
            print(f"     * {item['training_data_type']}: {item['id']}")
        
    except Exception as e:
        print(f"   ❌ Erro ao preparar dados de treinamento: {e}")
        return False
    
    # 3. SALVAR NO POSTGRESQL (simula cleanup de sessão)
    print("\n💾 [ETAPA 3] Salvando dados no PostgreSQL...")
    try:
        # Usar helper para garantir formato correto
        formatted_data = db_manager.format_training_data_batch(mock_training_data, client_id)
        
        success = db_manager.save_training_data(client_id, formatted_data)
        if success:
            print("   ✅ Dados salvos com sucesso!")
            print("   ✔ Dados salvos no PostgreSQL")
        else:
            print("   ❌ Falha ao salvar dados")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro ao salvar no PostgreSQL: {e}")
        return False
    
    # 4. VERIFICAR PERSISTÊNCIA
    print("\n🔍 [ETAPA 4] Verificando persistência...")
    try:
        dados_salvos = db_manager.load_training_data(client_id)
        ids_salvos = [item['id'] for item in dados_salvos] if dados_salvos else []
        
        print(f"   - Total de registros após salvamento: {len(dados_salvos) if dados_salvos else 0}")
        
        # Verificar se nossos dados de teste estão lá
        test_ids = [item['id'] for item in mock_training_data]
        encontrados = [test_id for test_id in test_ids if test_id in ids_salvos]
        
        print(f"   - Dados de teste encontrados: {len(encontrados)}/{len(test_ids)}")
        for test_id in encontrados:
            print(f"     ✅ {test_id}")
        
        for test_id in test_ids:
            if test_id not in encontrados:
                print(f"     ❌ {test_id} (não encontrado)")
        
        if len(encontrados) != len(test_ids):
            print("   ⚠️ Nem todos os dados de teste foram persistidos corretamente")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar persistência: {e}")
        return False
    
    # 5. SIMULAR REINÍCIO (carregar dados do banco)
    print("\n🔄 [ETAPA 5] Simulando reinício (carregamento do banco)...")
    try:
        # Simula setup_treinamento_cliente_interface
        dados_carregados = db_manager.load_training_data(client_id)
        
        if dados_carregados:
            print(f"   ✅ {len(dados_carregados)} registros carregados do banco")
            print("   ✔ Dados carregados do PostgreSQL")
            
            # Verificar tipos de dados
            tipos = {}
            for item in dados_carregados:
                tipo = item.get('training_data_type', 'unknown')
                tipos[tipo] = tipos.get(tipo, 0) + 1
            
            print(f"   - Distribuição por tipo: {tipos}")
        else:
            print("   ❌ Nenhum dado carregado do banco")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro ao carregar dados do banco: {e}")
        return False
    
    # 6. LIMPEZA DOS DADOS DE TESTE
    print("\n🧹 [ETAPA 6] Limpeza dos dados de teste...")
    try:
        # Remover apenas os dados de teste que criamos
        for item in mock_training_data:
            success = db_manager.delete_training_data_item(client_id, item['id'])
            if success:
                print(f"   ✅ Removido: {item['id']}")
            else:
                print(f"   ⚠️ Falha ao remover: {item['id']}")
                
    except Exception as e:
        print(f"   ⚠️ Erro na limpeza (não crítico): {e}")
    
    print(f"\n🎉 [SIMULAÇÃO] Ciclo completo executado com sucesso para cliente {client_id}!")
    return True

def testar_conexao():
    """Testa a conexão básica com o banco"""
    print("\n🔌 [CONEXÃO] Testando conexão com PostgreSQL...")
    try:
        if db_manager.test_connection():
            print("   ✅ Conexão estabelecida com sucesso!")
            return True
        else:
            print("   ❌ Falha na conexão!")
            return False
    except Exception as e:
        print(f"   ❌ Erro na conexão: {e}")
        return False

def testar_formatacao():
    """Testa as funções de formatação de dados"""
    print("\n📝 [FORMATAÇÃO] Testando formatação de dados...")
    try:
        # Simular dados vindos da Vanna (formato inconsistente)
        dados_vanna = [
            {"id": "test-1", "training_data_type": "sql", "content": "SELECT 1", "question": "teste"},
            {"training_data_type": "ddl", "content": "CREATE TABLE test()"},  # sem ID
            {"content": "Documentação teste"},  # sem tipo nem ID
        ]
        
        formatted = db_manager.format_training_data_batch(dados_vanna, client_id=99)
        
        print(f"   - {len(formatted)} itens formatados")
        for item in formatted:
            print(f"     * ID: {item['id'][:20]}...")
            print(f"       Tipo: {item['training_data_type']}")
            print(f"       Content: {item['content'][:30]}...")
        
        # Verificar se todos têm campos obrigatórios
        for item in formatted:
            if not all(key in item for key in ['id', 'training_data_type', 'content', 'question', 'metadata']):
                print("   ❌ Formatação falhou - campos obrigatórios ausentes")
                return False
        
        print("   ✅ Formatação funcionando corretamente!")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro na formatação: {e}")
        return False

def main():
    """Executa todos os testes de integração"""
    print("🚀 INICIANDO TESTES DE INTEGRAÇÃO COMPLETA")
    print("=" * 50)
    
    # Carregar ambiente
    load_dotenv()
    
    # Lista de testes
    testes = [
        ("Conexão PostgreSQL", testar_conexao),
        ("Formatação de dados", testar_formatacao),
        ("Ciclo completo Cliente 1", lambda: simular_sessao_usuario(1)),
        ("Ciclo completo Cliente 5", lambda: simular_sessao_usuario(5)),
    ]
    
    sucessos = 0
    total = len(testes)
    
    for nome, teste_func in testes:
        print(f"\n{'='*20} {nome} {'='*20}")
        try:
            if teste_func():
                sucessos += 1
                print(f"✅ {nome}: SUCESSO")
            else:
                print(f"❌ {nome}: FALHA")
        except Exception as e:
            print(f"💥 {nome}: EXCEÇÃO - {e}")
    
    print(f"\n{'='*50}")
    print(f"🏁 RESULTADO FINAL: {sucessos}/{total} testes passaram")
    
    if sucessos == total:
        print("🎉 TODOS OS TESTES PASSARAM! Migração PostgreSQL está funcionando!")
        return True
    else:
        print("⚠️ ALGUNS TESTES FALHARAM. Verifique os logs acima.")
        return False

if __name__ == "__main__":
    main()
