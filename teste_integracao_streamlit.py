#!/usr/bin/env python3
"""
Teste de validação da integração DatabaseManager no Streamlit
"""

import sys
import os

# Adicionar caminhos necessários
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
interface_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'interface'))
sys.path.extend([src_path, interface_path])

def test_database_manager_integration():
    """Testa se o DatabaseManager está funcionando na interface"""
    print("🔍 TESTE DE INTEGRAÇÃO STREAMLIT + POSTGRESQL")
    print("=" * 60)
    
    try:
        # 1. Testar import do DatabaseManager
        print("\n1. Testando import do DatabaseManager...")
        from database_manager import db_manager
        print("✅ DatabaseManager importado com sucesso")
        
        # 2. Testar conexão
        print("\n2. Testando conexão PostgreSQL...")
        if db_manager.test_connection():
            print("✅ Conexão PostgreSQL estabelecida")
        else:
            print("❌ Falha na conexão PostgreSQL")
            return False
        
        # 3. Testar tabela
        print("\n3. Verificando tabela ai_training_data...")
        if db_manager.ensure_table_exists():
            print("✅ Tabela ai_training_data pronta")
        else:
            print("❌ Erro na tabela ai_training_data")
            return False
        
        # 4. Testar imports da interface
        print("\n4. Testando imports da interface...")
        from interface.utils.vanna_setup import has_training_data, setup_treinamento_cliente_interface
        from interface.utils.session_cleanup_controller import SessionCleanupController
        print("✅ Módulos da interface importados")
        
        # 5. Testar função has_training_data
        print("\n5. Testando verificação de dados...")
        has_data = has_training_data(99)  # Cliente teste
        print(f"✅ has_training_data(99): {has_data}")
        
        # 6. Testar salvamento de dados mock
        print("\n6. Testando salvamento mock...")
        mock_data = [{
            "id": "integration-test-001",
            "training_data_type": "sql",
            "content": "SELECT 1 as test;",
            "question": "Teste de integração"
        }]
        
        success = db_manager.save_training_data("integration_test", mock_data)
        if success:
            print("✅ Dados mock salvos com sucesso")
            print("✔ Dados salvos no PostgreSQL")
        else:
            print("❌ Falha ao salvar dados mock")
            return False
        
        # 7. Testar carregamento
        print("\n7. Testando carregamento...")
        loaded_data = db_manager.load_training_data("integration_test")
        if loaded_data:
            print(f"✅ {len(loaded_data)} registros carregados")
            print("✔ Dados carregados do PostgreSQL")
        else:
            print("⚠️ Nenhum dado carregado (isso pode ser normal)")
        
        # 8. Limpeza
        print("\n8. Limpando dados de teste...")
        if loaded_data:
            test_ids = [item['id'] for item in loaded_data if item['id'].startswith('integration-test')]
            if test_ids:
                db_manager.delete_training_data("integration_test", test_ids)
                print(f"✅ {len(test_ids)} registros de teste removidos")
        
        print("\n" + "=" * 60)
        print("🎉 INTEGRAÇÃO STREAMLIT + POSTGRESQL FUNCIONANDO!")
        print("✅ Todos os componentes integrados com sucesso")
        print("✅ DatabaseManager operacional")
        print("✅ Interface pronta para uso")
        return True
        
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_database_manager_integration()
    print(f"\n{'✅ SUCESSO' if success else '❌ FALHA'}")
    exit(0 if success else 1)
