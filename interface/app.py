# app.py – entrada principal da interface Streamlit

import streamlit as st
import os
import sys
import atexit
import logging

# 🔧 [LOGGING] Configuração de logging para Render
def setup_render_logging():
    """Configura logging para ser visível no Render"""
    logger = logging.getLogger('soliris_app')
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - SOLIRIS-APP - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    return logger

# Inicializar logger
render_logger = setup_render_logging()

# Adiciona o diretório src/ ao sys.path para permitir importações
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.append(src_path)
render_logger.info(f"🔧 [PATH] Src path adicionado: {src_path}")

# Agora é seguro importar coisas de src/
try:
    from vanna_core import inicializar_vanna_para_interface
    from auth.auth_utils import login, logout
    from utils.session_cleanup_controller import SessionCleanupController
    render_logger.info("✅ [IMPORT] Módulos principais importados com sucesso")
except ImportError as e:
    render_logger.error(f"❌ [IMPORT] Erro ao importar módulos principais: {e}")
    raise

# Instância global do controlador de sessão
cleanup_controller = SessionCleanupController()

def carregar_pagina():
    pagina = st.session_state.get("pagina", "Home")
    render_logger.info(f"📄 [PAGE] Carregando página: {pagina}")

    if pagina == "Home":
        from views.home import mostrar_home
        mostrar_home()
    elif pagina == "Alertas":
        from views.alertas import mostrar_alertas
        mostrar_alertas()
    elif pagina == "Histórico":
        from views.historico import mostrar_historico
        mostrar_historico()
    elif pagina == "Configurações":
        from views.configuracoes import mostrar_configuracoes
        mostrar_configuracoes()
    elif st.session_state.get("pagina") == "configuracoes":
        mostrar_configuracoes()

def main():
    """Aplicação principal com sistema de cleanup otimizado"""
    render_logger.info("🚀 [MAIN] Iniciando aplicação principal")
    
    # SISTEMA DE CLEANUP OTIMIZADO - UMA ÚNICA VEZ POR SESSÃO
    if "cleanup_registrado" not in st.session_state:
        # Registra callback de emergência para encerramento inesperado
        atexit.register(lambda: cleanup_controller.execute_session_cleanup(force=True))
        
        # Inicia monitor leve de sessão
        cleanup_controller.start_session_monitor()
        
        st.session_state.cleanup_registrado = True
        print("🔧 [INIT] Sistema de cleanup otimizado ativado")
        render_logger.info("🔧 [CLEANUP] Sistema de cleanup otimizado ativado")
    
    # Detecta mudança de usuário e executa cleanup se necessário
    current_user = st.session_state.get("id_client")
    if "last_user" in st.session_state and st.session_state.last_user != current_user:
        print(f"👤 [USER_CHANGE] Detectada mudança de usuário: {st.session_state.last_user} → {current_user}")
        if st.session_state.last_user:  # Se havia usuário anterior
            cleanup_controller.execute_session_cleanup()
    st.session_state.last_user = current_user
    
    if not st.session_state.get("logado"):
        login()
    else:
        # Verifica se os dados da sessão estão completos
        if not st.session_state.get("email") or not st.session_state.get("id_client"):
            st.error("❌ Dados da sessão incompletos. Faça login novamente.")
            st.session_state.logado = False
            st.rerun()
        
        # Carregamento do modelo Vanna pós-login
        if "vanna" not in st.session_state:
            with st.spinner("Carregando modelo Vanna..."):
                st.session_state.vanna = inicializar_vanna_para_interface(st.session_state.email)
                st.success("Modelo carregado com sucesso!")

        st.sidebar.title(f"Bem-vindo, {st.session_state.get('name', 'Usuário')}")
        pagina = st.sidebar.radio("Navegação", ["Home", "Alertas", "Histórico", "Configurações"])
        st.session_state.pagina = pagina

        if st.sidebar.button("Sair"):
            # Executa cleanup antes do logout
            cleanup_controller.execute_session_cleanup()
            logout()
            
        carregar_pagina()

if __name__ == "__main__":
    main()
