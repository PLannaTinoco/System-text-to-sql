#!/usr/bin/env python3
"""
🔍 Script de Verificação Rápida - Sistema Soliris
Executa testes básicos de conectividade e configuração
"""

import os
import sys
import traceback
from pathlib import Path

# Adiciona src ao path
sys.path.append(str(Path(__file__).parent / "src"))

def test_env_variables():
    """Testa variáveis de ambiente"""
    print("🔧 Testando variáveis de ambiente...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = [
            "DB_HOST", "DB_PORT", "DB_NAME", 
            "DB_USER", "DB_PASSWORD", "API_KEY"
        ]
        
        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            print(f"❌ Variáveis faltando: {', '.join(missing)}")
            return False
        else:
            print("✅ Todas as variáveis de ambiente configuradas")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao carregar .env: {e}")
        return False

def test_database_connection():
    """Testa conexão com PostgreSQL"""
    print("\n🗄️ Testando conexão PostgreSQL...")
    
    try:
        from kpis_Setup import conectar_postgres
        
        conn = conectar_postgres()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        print(f"✅ PostgreSQL conectado: {version[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão PostgreSQL: {e}")
        return False

def test_vanna_connection():
    """Testa conexão com Vanna AI"""
    print("\n🤖 Testando Vanna AI...")
    
    try:
        from vanna.remote import VannaDefault
        from dotenv import load_dotenv
        
        load_dotenv()
        api_key = os.getenv("API_KEY")
        
        if not api_key:
            print("❌ API_KEY não configurada")
            return False
        
        vn = VannaDefault(model="jarves", api_key=api_key)
        print("✅ Vanna AI instanciado com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro no Vanna AI: {e}")
        return False

def test_streamlit_imports():
    """Testa importações do Streamlit"""
    print("\n🖥️ Testando importações Streamlit...")
    
    try:
        import streamlit as st
        import pandas as pd
        import tempfile
        
        print("✅ Streamlit e dependências importados")
        return True
        
    except Exception as e:
        print(f"❌ Erro nas importações: {e}")
        return False

def test_interface_files():
    """Verifica arquivos principais da interface"""
    print("\n📁 Verificando arquivos da interface...")
    
    required_files = [
        "interface/app.py",
        "interface/views/cadastro_setup.py", 
        "interface/views/configuracoes.py",
        "interface/views/alertas.py",
        "interface/components/chatbot.py",
        "src/kpis_Setup.py",
        "src/vanna_core.py"
    ]
    
    missing = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing.append(file_path)
    
    if missing:
        print(f"❌ Arquivos faltando: {', '.join(missing)}")
        return False
    else:
        print("✅ Todos os arquivos principais encontrados")
        return True

def test_requirements():
    """Verifica requirements.txt"""
    print("\n📦 Verificando requirements.txt...")
    
    try:
        if not os.path.exists("requirements.txt"):
            print("❌ requirements.txt não encontrado")
            return False
        
        with open("requirements.txt", "r") as f:
            requirements = f.read()
        
        required_packages = [
            "streamlit", "pandas", "psycopg2", 
            "python-dotenv", "vanna"
        ]
        
        missing = []
        for pkg in required_packages:
            if pkg not in requirements:
                missing.append(pkg)
        
        if missing:
            print(f"❌ Pacotes faltando no requirements.txt: {', '.join(missing)}")
            return False
        else:
            print("✅ requirements.txt contém pacotes principais")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao verificar requirements.txt: {e}")
        return False

def test_csv_samples():
    """Verifica arquivos CSV de exemplo"""
    print("\n📊 Verificando CSVs de exemplo...")
    
    csv_dir = Path("Planilhas")
    if not csv_dir.exists():
        print("❌ Diretório Planilhas/ não encontrado")
        return False
    
    sample_files = list(csv_dir.glob("*.csv"))
    if not sample_files:
        print("❌ Nenhum CSV de exemplo encontrado")
        return False
    
    print(f"✅ {len(sample_files)} CSVs de exemplo encontrados")
    for csv_file in sample_files[:3]:  # Mostra apenas os 3 primeiros
        print(f"   📄 {csv_file.name}")
    
    return True

def main():
    """Executa todos os testes"""
    print("🚀 VERIFICAÇÃO RÁPIDA - SISTEMA SOLIRIS")
    print("=" * 50)
    
    tests = [
        ("Variáveis de Ambiente", test_env_variables),
        ("Conexão PostgreSQL", test_database_connection),
        ("Vanna AI", test_vanna_connection),
        ("Importações Streamlit", test_streamlit_imports),
        ("Arquivos da Interface", test_interface_files),
        ("Requirements.txt", test_requirements),
        ("CSVs de Exemplo", test_csv_samples)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro crítico em {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo final
    print("\n" + "=" * 50)
    print("📋 RESUMO DOS TESTES")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 RESULTADO: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 SISTEMA PRONTO PARA TESTES MANUAIS!")
        print("\n📖 Próximos passos:")
        print("1. Execute: cd interface && streamlit run app.py")
        print("2. Siga o GUIA_TESTE_MANUAL_COMPLETO.md")
        print("3. Teste todas as funcionalidades")
    else:
        print("⚠️  CORRIJA OS PROBLEMAS ANTES DE PROSSEGUIR")
        print("\n🔧 Dicas:")
        print("- Verifique arquivo .env")
        print("- Instale dependências: pip install -r requirements.txt")
        print("- Confirme conexão com PostgreSQL")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
