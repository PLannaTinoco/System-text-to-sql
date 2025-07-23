# historico.py – histórico de interações e KPIs (VERSÃO SIMPLIFICADA)

import os
import json
import pickle
import streamlit as st
import logging
import sys
from datetime import datetime

# 🔧 [LOGGING] Configuração de logging para Render
def setup_render_logging():
    """Configura logging para ser visível no Render"""
    logger = logging.getLogger('soliris_historico')
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - SOLIRIS-HIST - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    return logger

# Inicializar logger
render_logger = setup_render_logging()

def get_abs_path(*path_parts):
    """Vai para interface/auth/hist/usuario_XX/ baseado no usuário logado"""
    id_client = st.session_state.get("id_client")
    if not id_client:
        # Fallback para usuário não identificado
        id_client = 1
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # interface/
    hist_dir = os.path.join(base_dir, "auth", "hist", f"usuario_{id_client:02d}")  # interface/auth/hist/usuario_01/
    
    # Cria diretório se não existir
    os.makedirs(hist_dir, exist_ok=True)
    render_logger.info(f"📁 [HIST] Diretório de histórico: {hist_dir}")
    
    full_path = os.path.join(hist_dir, *path_parts)
    return full_path

def carregar_qualquer_historico(arquivo_path):
    """Carrega qualquer tipo de arquivo de histórico (pkl ou json)"""
    render_logger.info(f"📁 [FILE] Carregando histórico: {arquivo_path}")
    
    try:
        if arquivo_path.endswith('.pkl'):
            render_logger.info("📄 [FILE] Formato pickle detectado")
            with open(arquivo_path, "rb") as f:
                historico = pickle.load(f)
            render_logger.info(f"✅ [FILE] Histórico pickle carregado com {len(historico) if isinstance(historico, list) else 'N/A'} entradas")
            return historico
        else:  # json
            render_logger.info("📄 [FILE] Formato JSON detectado")
            with open(arquivo_path, "r", encoding="utf-8") as f:
                historico_raw = json.load(f)
            
            # Se for formato do backend, converte para Streamlit
            if isinstance(historico_raw, list) and len(historico_raw) > 0:
                primeira_entrada = historico_raw[0]
                
                # Se tem "resultado" em vez de "resposta", é formato backend
                if "resultado" in primeira_entrada and "resposta" not in primeira_entrada:
                    render_logger.info("🔄 [CONVERT] Convertendo formato backend para Streamlit")
                    historico_convertido = []
                    for entry in historico_raw:
                        chat_entry = {
                            "mensagem": entry.get("pergunta", ""),
                            "pergunta": entry.get("pergunta", ""),
                            "sql": entry.get("sql", ""),
                            "resposta": entry.get("resultado", ""),
                            "figura_auto": None,
                            "figura_personalizada": None,
                            "mostrar_grafico_auto": False,
                            "mostrar_grafico_personalizado": False
                        }
                        historico_convertido.append(chat_entry)
                    return historico_convertido
            
            return historico_raw
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return []

def formatar_nome_arquivo(filename):
    """Formata nome do arquivo para exibição amigável"""
    try:
        # Remove extensão
        nome = filename.replace('.pkl', '').replace('.json', '')
        
        # Busca por timestamp
        import re
        match = re.search(r'(\d{8}_\d{6})', nome)
        if match:
            timestamp = match.group(1)
            # Converte para formato legível
            ano = timestamp[:4]
            mes = timestamp[4:6] 
            dia = timestamp[6:8]
            hora = timestamp[9:11]
            minuto = timestamp[11:13]
            
            return f"📅 {dia}/{mes}/{ano} {hora}:{minuto} ({filename})"
        
        return f"📂 {filename}"
    except:
        return f"📂 {filename}"

def mostrar_historico():
    st.title("📚 Histórico de Conversas")
    
    # Verifica se usuário está logado
    id_client = st.session_state.get("id_client")
    if not id_client:
        st.error("❌ Usuário não identificado. Faça login novamente.")
        return
    
    # Configuração do diretório
    hist_dir = get_abs_path()
    if not os.path.exists(hist_dir):
        os.makedirs(hist_dir, exist_ok=True)
        st.info(f"📁 Diretório criado: {hist_dir}")
    
    # Lista arquivos úteis (exclui backups de perguntas individuais)
    todos_arquivos = os.listdir(hist_dir)
    arquivos_historico = [
        f for f in todos_arquivos 
        if (f.endswith('.pkl') or f.endswith('.json')) and not f.startswith('pergunta_')
    ]
    
    # =============== SEÇÃO PRINCIPAL ===============
    if arquivos_historico:
        st.subheader("💾 Carregar Histórico Anterior")
        
        # Ordena por data (mais recente primeiro)
        arquivos_historico.sort(reverse=True)
        
        # Seleção do arquivo
        arquivo_selecionado = st.selectbox(
            "Escolha um histórico para carregar:",
            arquivos_historico,
            format_func=formatar_nome_arquivo
        )
        
        # Botões de ação
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("📂 Carregar"):
                arquivo_path = get_abs_path(arquivo_selecionado)
                historico = carregar_qualquer_historico(arquivo_path)
                
                if historico:
                    st.session_state["chat_history"] = historico
                    st.success(f"✅ Histórico carregado! {len(historico)} conversas.")
                    st.rerun()
                else:
                    st.error("❌ Erro ao carregar histórico.")
        
        with col2:
            if st.button("👁️ Preview"):
                arquivo_path = get_abs_path(arquivo_selecionado)
                historico = carregar_qualquer_historico(arquivo_path)
                
                if historico:
                    st.info(f"📊 **{len(historico)} conversas** no arquivo")
                    
                    # Mostra preview das 3 primeiras
                    with st.expander("🔍 Preview das conversas"):
                        for i, entrada in enumerate(historico[:3], 1):
                            pergunta = entrada.get("pergunta", entrada.get("mensagem", "N/A"))
                            st.write(f"**{i}.** {pergunta[:60]}{'...' if len(pergunta) > 60 else ''}")
                        
                        if len(historico) > 3:
                            st.write(f"... e mais {len(historico) - 3} conversas.")
        
        with col3:
            st.info(f"📂 Arquivo: `{arquivo_selecionado}`")
            
        # Linha divisória
        st.divider()
        
        # =============== ADMINISTRAÇÃO (OPCIONAL) ===============
        with st.expander("⚙️ Administração (Avançado)"):
            col_stats, col_actions = st.columns(2)
            
            with col_stats:
                st.write("📊 **Estatísticas:**")
                arquivos_pkl = [f for f in todos_arquivos if f.endswith('.pkl')]
                arquivos_json = [f for f in todos_arquivos if f.endswith('.json')]
                backups = [f for f in todos_arquivos if f.startswith('pergunta_')]
                
                st.write(f"- Total de arquivos: {len(todos_arquivos)}")
                st.write(f"- Históricos (.pkl): {len(arquivos_pkl)}")
                st.write(f"- Históricos (.json): {len(arquivos_json)}")
                st.write(f"- Backups individuais: {len(backups)}")
            
            with col_actions:
                st.write("🛠️ **Ações:**")
                
                if st.button("🔄 Atualizar Lista"):
                    st.rerun()
                
                if st.button("🗑️ Limpar Backups Antigos"):
                    import time
                    current_time = time.time()
                    removed = 0
                    
                    for arquivo in backups:
                        arquivo_path = get_abs_path(arquivo)
                        file_time = os.path.getctime(arquivo_path)
                        
                        # Remove se mais de 7 dias
                        if current_time - file_time > 604800:
                            os.remove(arquivo_path)
                            removed += 1
                    
                    if removed > 0:
                        st.success(f"🗑️ {removed} backups removidos.")
                        st.rerun()
                    else:
                        st.info("Nenhum backup antigo encontrado.")
    else:
        st.info("📭 Nenhum histórico salvo encontrado.")
        st.write("💡 **Dica:** Históricos são salvos automaticamente após cada conversa.")
    
    # =============== CONVERSAS DA SESSÃO ATUAL ===============
    st.divider()
    st.subheader("💬 Conversas da Sessão Atual")
    
    historico_atual = st.session_state.get("chat_history", [])
    if historico_atual:
        st.write(f"📝 **{len(historico_atual)} conversas** nesta sessão:")
        
        # Lista resumida
        for i, entrada in enumerate(historico_atual, 1):
            pergunta = entrada.get("pergunta", entrada.get("mensagem", "N/A"))
            
            col_num, col_pergunta, col_status = st.columns([0.5, 3, 1])
            
            with col_num:
                st.write(f"**{i}.**")
            
            with col_pergunta:
                st.write(pergunta[:80] + "..." if len(pergunta) > 80 else pergunta)
            
            with col_status:
                if entrada.get("sql"):
                    st.success("✅ SQL")
                if entrada.get("resposta") is not None:
                    st.success("✅ Dados")
        
        # Detalhes expandidos (opcional)
        if st.checkbox("🔍 Mostrar detalhes das conversas"):
            for i, entrada in enumerate(historico_atual, 1):
                with st.expander(f"Conversa {i}: {entrada.get('pergunta', 'N/A')[:40]}..."):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**📝 Pergunta:**")
                        st.write(entrada.get('pergunta', entrada.get('mensagem', 'N/A')))
                        
                        st.write("**🔍 SQL:**")
                        sql = entrada.get('sql', 'N/A')
                        if sql and sql != 'N/A':
                            st.code(sql, language="sql")
                        else:
                            st.write("N/A")
                    
                    with col2:
                        st.write("**📊 Resultado:**")
                        resposta = entrada.get('resposta')
                        if resposta is not None:
                            if hasattr(resposta, 'shape'):
                                st.write(f"DataFrame: {resposta.shape[0]} linhas × {resposta.shape[1]} colunas")
                                if not resposta.empty:
                                    st.dataframe(resposta.head(3))
                            else:
                                resultado_str = str(resposta)
                                st.write(resultado_str[:200] + "..." if len(resultado_str) > 200 else resultado_str)
                        else:
                            st.write("N/A")
    else:
        st.info("Nenhuma conversa nesta sessão.")