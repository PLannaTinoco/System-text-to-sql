#!/usr/bin/env python3
"""
Wrapper para usar vanna_core.py na interface Streamlit
sem alterar o código original - soluciona problema dos input() interativos
"""

import sys
import os
import streamlit as st
from unittest.mock import patch
from typing import Dict, Optional, Any

# Adiciona o path do src para importar vanna_core
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import do vanna_core original
from vanna_core import setup_treinamento_cliente as setup_original
from vanna_core import VannaDefault

def setup_treinamento_cliente_interface(id_client: int, configuracoes: dict) -> VannaDefault:
    """
    Wrapper que executa setup_treinamento_cliente() automaticamente
    sem input() interativo para usar na interface Streamlit
    
    Args:
        id_client: ID do cliente
        configuracoes: {
            "usar_plan_existente": True/False,  # Se deve usar plano existente
            "treinar_plan": True/False,         # Se deve treinar plano
            "treinar_kpis": True/False,         # Se deve treinar KPIs
            "treinar_ddl": True/False           # Se deve treinar DDLs
        }
    
    Returns:
        VannaDefault: Instância do modelo treinado
    
    Raises:
        Exception: Se ocorrer erro durante o setup
    """
    
    print(f"🔧 [WRAPPER] Iniciando setup para cliente {id_client}")
    print(f"🔧 [WRAPPER] Configurações: {configuracoes}")
    
    # Mapeia configurações para respostas automáticas dos input()
    respostas_automaticas = []
    
    # Resposta 1: "Já existe um plan salvo. Deseja usá-lo? (s/N)"
    if configuracoes.get("usar_plan_existente", True):
        respostas_automaticas.append("s")
        print("📋 [WRAPPER] Configurado para USAR plano existente")
    else:
        respostas_automaticas.append("n")
        print("📋 [WRAPPER] Configurado para GERAR novo plano")
    
    # Resposta 2: "Deseja treinar o plano de dados? (s/N)"
    if configuracoes.get("treinar_plan", True):
        respostas_automaticas.append("s")
        print("🎯 [WRAPPER] Configurado para TREINAR plano")
    else:
        respostas_automaticas.append("n")
        print("🎯 [WRAPPER] Configurado para PULAR treinamento do plano")
    
    # Resposta 3: "Deseja treinar os KPIs? (s/N)"
    if configuracoes.get("treinar_kpis", True):
        respostas_automaticas.append("s")
        print("📊 [WRAPPER] Configurado para TREINAR KPIs")
    else:
        respostas_automaticas.append("n")
        print("📊 [WRAPPER] Configurado para PULAR treinamento de KPIs")
    
    # Resposta 4: "Deseja treinar as DDLs das tabelas? (s/N)"
    if configuracoes.get("treinar_ddl", True):
        respostas_automaticas.append("s")
        print("🏗️ [WRAPPER] Configurado para TREINAR DDLs")
    else:
        respostas_automaticas.append("n")
        print("🏗️ [WRAPPER] Configurado para PULAR treinamento de DDLs")
    
    print(f"💬 [WRAPPER] Respostas automáticas: {respostas_automaticas}")
    
    try:
        # Simula input interativo com respostas automáticas
        resposta_index = 0
        
        def mock_input(prompt):
            nonlocal resposta_index
            if resposta_index < len(respostas_automaticas):
                resposta = respostas_automaticas[resposta_index]
                resposta_index += 1
                print(f"🤖 [AUTO-INPUT] {prompt.strip()} -> {resposta}")
                return resposta
            else:
                print(f"⚠️ [AUTO-INPUT] Prompt inesperado: {prompt}")
                return "n"  # Resposta padrão segura
        
        # Executa a função original com input simulado
        print("🚀 [WRAPPER] Executando setup_treinamento_cliente() original...")
        
        with patch('builtins.input', side_effect=mock_input):
            vn = setup_original(id_client)
        
        print("✅ [WRAPPER] Setup concluído com sucesso!")
        return vn
        
    except Exception as e:
        print(f"❌ [WRAPPER] Erro durante setup: {e}")
        raise

def setup_treinamento_completo_automatico(id_client: int) -> dict:
    """
    Executa setup completo com todas as opções ativadas
    Usado durante o onboarding para treinar o modelo completamente
    
    Args:
        id_client: ID do cliente
        
    Returns:
        dict: {
            "status": "success/error",
            "vn": modelo_treinado,
            "erro": str_erro,
            "detalhes": informações_adicionais
        }
    """
    
    print(f"🎯 [SETUP_COMPLETO] Iniciando para cliente {id_client}")
    
    try:
        configuracoes = {
            "usar_plan_existente": True,  # Usa plano se existir (economiza tempo)
            "treinar_plan": True,         # Treina plano (essencial)
            "treinar_kpis": True,         # Treina KPIs (importante para análises)
            "treinar_ddl": True           # Treina DDLs (importante para estrutura)
        }
        
        print("📋 [SETUP_COMPLETO] Configurações: Todos os treinamentos ativados")
        
        # Chama o wrapper
        vn = setup_treinamento_cliente_interface(id_client, configuracoes)
        
        print("🎉 [SETUP_COMPLETO] Treinamento completo concluído!")
        
        return {
            "status": "success",
            "vn": vn,
            "erro": None,
            "detalhes": "Treinamento completo: plano + KPIs + DDLs"
        }
        
    except Exception as e:
        print(f"❌ [SETUP_COMPLETO] Erro: {e}")
        return {
            "status": "error",
            "vn": None,
            "erro": str(e),
            "detalhes": "Falha no treinamento completo"
        }

def setup_treinamento_rapido(id_client: int) -> dict:
    """
    Setup rápido apenas com plano (sem KPIs e DDL)
    Usado quando o usuário quer começar rapidamente
    
    Args:
        id_client: ID do cliente
        
    Returns:
        dict: {
            "status": "success/error", 
            "vn": modelo_treinado,
            "erro": str_erro,
            "detalhes": informações_adicionais
        }
    """
    
    print(f"⚡ [SETUP_RAPIDO] Iniciando para cliente {id_client}")
    
    try:
        configuracoes = {
            "usar_plan_existente": True,  # Usa plano se existir
            "treinar_plan": True,         # Treina plano (mínimo necessário)
            "treinar_kpis": False,        # Pula KPIs (pode ser feito depois)
            "treinar_ddl": False          # Pula DDLs (pode ser feito depois)
        }
        
        print("📋 [SETUP_RAPIDO] Configurações: Apenas plano básico")
        
        # Chama o wrapper
        vn = setup_treinamento_cliente_interface(id_client, configuracoes)
        
        print("⚡ [SETUP_RAPIDO] Treinamento rápido concluído!")
        
        return {
            "status": "success",
            "vn": vn,
            "erro": None,
            "detalhes": "Treinamento rápido: apenas plano básico"
        }
        
    except Exception as e:
        print(f"❌ [SETUP_RAPIDO] Erro: {e}")
        return {
            "status": "error",
            "vn": None,
            "erro": str(e),
            "detalhes": "Falha no treinamento rápido"
        }

def setup_treinamento_personalizado(id_client: int, opcoes: dict) -> dict:
    """
    Setup personalizado com opções específicas do usuário
    
    Args:
        id_client: ID do cliente
        opcoes: {
            "usar_plan_existente": True/False,
            "treinar_plan": True/False,
            "treinar_kpis": True/False,
            "treinar_ddl": True/False,
            "modo": "completo/rapido/personalizado"
        }
        
    Returns:
        dict: {"status": "success/error", "vn": modelo, "erro": str, "detalhes": str}
    """
    
    print(f"🎨 [SETUP_PERSONALIZADO] Iniciando para cliente {id_client}")
    print(f"🎨 [SETUP_PERSONALIZADO] Opções: {opcoes}")
    
    try:
        configuracoes = {
            "usar_plan_existente": opcoes.get("usar_plan_existente", True),
            "treinar_plan": opcoes.get("treinar_plan", True),
            "treinar_kpis": opcoes.get("treinar_kpis", False),
            "treinar_ddl": opcoes.get("treinar_ddl", False)
        }
        
        # Chama o wrapper
        vn = setup_treinamento_cliente_interface(id_client, configuracoes)
        
        # Monta detalhes das opções executadas
        detalhes_opcoes = []
        if configuracoes["treinar_plan"]:
            detalhes_opcoes.append("plano")
        if configuracoes["treinar_kpis"]:
            detalhes_opcoes.append("KPIs")
        if configuracoes["treinar_ddl"]:
            detalhes_opcoes.append("DDLs")
        
        detalhes = f"Treinamento personalizado: {', '.join(detalhes_opcoes)}"
        
        print(f"🎨 [SETUP_PERSONALIZADO] Concluído: {detalhes}")
        
        return {
            "status": "success",
            "vn": vn,
            "erro": None,
            "detalhes": detalhes
        }
        
    except Exception as e:
        print(f"❌ [SETUP_PERSONALIZADO] Erro: {e}")
        return {
            "status": "error",
            "vn": None,
            "erro": str(e),
            "detalhes": "Falha no treinamento personalizado"
        }

def inicializar_vanna_para_interface_otimizado(email: str, modo: str = "completo") -> dict:
    """
    Versão otimizada do inicializar_vanna_para_interface() que não trava
    
    Args:
        email: Email do usuário
        modo: "completo", "rapido" ou "personalizado"
        
    Returns:
        dict: {"status": "success/error", "vn": modelo, "erro": str, "id_client": int}
    """
    
    print(f"🔄 [INIT_OTIMIZADO] Inicializando para {email} (modo: {modo})")
    
    try:
        # Obtém ID do cliente via vanna_core
        from vanna_core import obter_id_client_por_email
        id_client = obter_id_client_por_email(email)
        
        print(f"👤 [INIT_OTIMIZADO] Cliente ID: {id_client}")
        
        # Escolhe método de setup baseado no modo
        if modo == "completo":
            resultado = setup_treinamento_completo_automatico(id_client)
        elif modo == "rapido":
            resultado = setup_treinamento_rapido(id_client)
        else:
            # Modo padrão se não especificado
            resultado = setup_treinamento_completo_automatico(id_client)
        
        # Adiciona ID do cliente ao resultado
        resultado["id_client"] = id_client
        
        return resultado
        
    except Exception as e:
        print(f"❌ [INIT_OTIMIZADO] Erro: {e}")
        return {
            "status": "error",
            "vn": None,
            "erro": str(e),
            "id_client": None,
            "detalhes": "Falha na inicialização otimizada"
        }

# Função auxiliar para usar no Streamlit
def executar_setup_com_progress(id_client: int, configuracoes: dict, 
                               progress_callback=None) -> dict:
    """
    Executa setup com callback de progresso para interface Streamlit
    
    Args:
        id_client: ID do cliente
        configuracoes: Configurações do setup
        progress_callback: Função callback para atualizar progresso
        
    Returns:
        dict: Resultado do setup
    """
    
    if progress_callback:
        progress_callback(0.1, "Iniciando setup...")
    
    try:
        if progress_callback:
            progress_callback(0.3, "Configurando modelo...")
        
        # Executa setup
        vn = setup_treinamento_cliente_interface(id_client, configuracoes)
        
        if progress_callback:
            progress_callback(1.0, "Setup concluído!")
        
        return {
            "status": "success",
            "vn": vn,
            "erro": None
        }
        
    except Exception as e:
        if progress_callback:
            progress_callback(1.0, f"Erro: {str(e)}")
        
        return {
            "status": "error",
            "vn": None,
            "erro": str(e)
        }

if __name__ == "__main__":
    # Teste local do wrapper
    print("🧪 [TESTE] Testando wrapper...")
    
    # Configura um teste
    id_teste = 1
    config_teste = {
        "usar_plan_existente": True,
        "treinar_plan": True,
        "treinar_kpis": False,
        "treinar_ddl": False
    }
    
    try:
        resultado = setup_treinamento_personalizado(id_teste, config_teste)
        print(f"📊 [TESTE] Resultado: {resultado['status']}")
        if resultado['erro']:
            print(f"❌ [TESTE] Erro: {resultado['erro']}")
        else:
            print("✅ [TESTE] Wrapper funcionando!")
    except Exception as e:
        print(f"💥 [TESTE] Exceção: {e}")
