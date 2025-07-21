# auth_utils.py – validação e autenticação de usuário
import json
import streamlit as st
import sys
import os
import pickle
from datetime import datetime

# Adiciona caminhos necessários ao sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.join(current_dir, "..", "utils")
src_dir = os.path.join(current_dir, "..", "..", "src")

if utils_dir not in sys.path:
    sys.path.append(utils_dir)
if src_dir not in sys.path:
    sys.path.append(src_dir)

def autenticar_usuario(email, senha):
    """Wrapper para importar e usar db_utils.autenticar_usuario"""
    try:
        # Import dinâmico para evitar problemas de path
        import importlib.util
        db_utils_path = os.path.join(current_dir, "..", "utils", "db_utils.py")
        spec = importlib.util.spec_from_file_location("db_utils", db_utils_path)
        db_utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(db_utils)
        
        return db_utils.autenticar_usuario(email, senha)
    except Exception as e:
        print(f"Erro ao importar db_utils: {e}")
        return None

# Import do vanna_core
from vanna_core import finalizar_sessao

def get_abs_path(*path_parts):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, *path_parts)

def get_hist_user_path(id_client, *path_parts):
    """Retorna caminho para o diretório de histórico do usuário específico"""
    base_dir = os.path.dirname(os.path.abspath(__file__))  # interface/auth/
    
    # Formatar id_client corretamente (numérico ou string)
    if isinstance(id_client, (int, float)):
        user_folder = f"usuario_{int(id_client):02d}"
    else:
        user_folder = f"usuario_{str(id_client)}"
    
    hist_dir = os.path.join(base_dir, "hist", user_folder)  # interface/auth/hist/usuario_01/ ou usuario_admin/
    
    # Cria diretório se não existir
    os.makedirs(hist_dir, exist_ok=True)
    
    return os.path.join(hist_dir, *path_parts)

def salvar_historico_chat():
    historico = st.session_state.get("chat_history", [])
    if not historico:
        st.info("Nenhum histórico de chat para salvar.")
        return
    
    id_client = st.session_state.get("id_client", 1)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"historico_chat_{ts}.json"
    path = get_hist_user_path(id_client, filename)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)
    st.success(f"Histórico salvo em: {path}")

def salvar_historico_chat_pickle():
    historico = st.session_state.get("chat_history", [])
    if not historico:
        st.info("Nenhum histórico de chat para salvar.")
        return
    
    id_client = st.session_state.get("id_client", 1)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"historico_chat_{ts}.pkl"
    path = get_hist_user_path(id_client, filename)
    
    with open(path, "wb") as f:
        pickle.dump(historico, f)
    st.success(f"Histórico salvo em: {path}")

def login():
    """Tela de login com opção de cadastro"""
    
    # Verifica se está no modo cadastro
    if st.session_state.get("modo_cadastro"):
        from views.cadastro_setup import mostrar_cadastro_setup
        mostrar_cadastro_setup()
        return
    
    st.title("🔐 Login - Sistema Soliris")
    
    # Tabs para Login e Cadastro
    tab_login, tab_cadastro = st.tabs(["🔑 Fazer Login", "📝 Criar Conta"])
    
    with tab_login:
        st.subheader("Entre na sua conta")
        
        col1, col2 = st.columns([1, 2])
        
        with col2:
            with st.form("login_form"):
                email = st.text_input("📧 Email")
                senha = st.text_input("🔒 Senha", type="password")
                
                submitted = st.form_submit_button("🚀 Entrar", type="primary", use_container_width=True)
                
                if submitted:
                    if email and senha:
                        resultado = autenticar_usuario(email, senha)
                        if resultado:
                            id_client, nome = resultado
                            st.session_state.logado = True
                            st.session_state.email = email
                            st.session_state.name = nome
                            st.session_state.id_client = id_client
                            st.success(f"✅ Bem-vindo, {nome}!")
                            st.rerun()
                        else:
                            st.error("❌ Email ou senha incorretos")
                    else:
                        st.error("❌ Preencha todos os campos")
        
        with col1:
            st.info("""
            **ℹ️ Sistema Soliris**
            
            Faça login para acessar:
            - 🤖 Chatbot IA personalizado
            - 📊 Alertas inteligentes  
            - 📈 Dashboard analytics
            - ⚙️ Importação de dados
            """)
    
    with tab_cadastro:
        st.subheader("Criar nova conta")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("""
            **🚀 Novo no Soliris?**
            
            Ao criar sua conta, você terá:
            - ✅ Modelo de IA personalizado
            - ✅ Importação automática de dados
            - ✅ Treinamento guiado do sistema
            - ✅ Interface completa liberada
            
            **O processo leva apenas alguns minutos!**
            """)
            
            if st.button("📝 Criar Nova Conta", type="secondary", use_container_width=True):
                # Redireciona para o fluxo de cadastro
                st.session_state["modo_cadastro"] = True
                st.rerun()
        
        with col2:
            st.write("")  # Espaço vazio

def logout():
    """Limpa dados da sessão - o cleanup já foi executado pelo controlador"""
    try:
        print("🚪 [LOGOUT] Iniciando logout...")
        
        # Salva histórico (se ainda não foi salvo)
        if "chat_history" in st.session_state and st.session_state.chat_history:
            try:
                salvar_historico_chat_pickle()
                print("💾 [LOGOUT] Histórico salvo")
            except Exception as e:
                print(f"⚠️ [LOGOUT] Erro ao salvar histórico: {e}")
        
        # Coleta dados para salvar histórico de sessão (apenas histórico)
        id_client = st.session_state.get("id_client")
        email = st.session_state.get("email")
        historico = []

        # Se tiver histórico no chat
        if "chat_history" in st.session_state:
            for entrada in st.session_state.chat_history:
                historico.append({
                    "pergunta": entrada.get("pergunta"),
                    "sql": entrada.get("sql"),
                    "resultado": str(entrada.get("resposta"))
                })

        # Salva APENAS o histórico da sessão (sem mexer no training data)
        if id_client and historico:
            try:
                import sys
                import os
                from datetime import datetime
                import json
                
                src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
                if src_path not in sys.path:
                    sys.path.append(src_path)
                
                from vanna_core import get_abs_path
                
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                session_file = get_abs_path("hist", f"historico_cli{id_client:02d}_{ts}.json")
                with open(session_file, "w", encoding="utf-8") as f:
                    json.dump(historico, f, indent=2, ensure_ascii=False)
                print(f"📝 [LOGOUT] Histórico de sessão salvo: {session_file}")
            except Exception as e:
                print(f"⚠️ [LOGOUT] Erro ao salvar histórico de sessão: {e}")

        # IMPORTANTE: NÃO chamamos finalizar_sessao() porque:
        # 1. O cleanup controller já salvou o training data corretamente
        # 2. finalizar_sessao() sobrescreveria o arquivo com dados vazios
        print("✅ [LOGOUT] Training data preservado pelo cleanup controller")

        # Limpa a sessão (mantém apenas dados essenciais)
        keys_to_keep = ["cleanup_registrado"]
        for chave in list(st.session_state.keys()):
            if chave not in keys_to_keep:
                del st.session_state[chave]

        print("✅ [LOGOUT] Logout concluído com sucesso")
        st.success("Sessão finalizada com sucesso.")
        st.rerun()
        
    except Exception as e:
        print(f"❌ [LOGOUT] Erro no processo de logout: {e}")
        # Em caso de erro, força limpeza básica
        for chave in list(st.session_state.keys()):
            if chave not in ["cleanup_registrado"]:
                del st.session_state[chave]
        st.rerun()