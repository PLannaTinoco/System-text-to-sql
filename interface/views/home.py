# interface/views/home.py

import streamlit as st
import sys
import os
import logging

# 🔧 [LOGGING] Configuração de logging para Render
def setup_render_logging():
    """Configura logging para ser visível no Render"""
    logger = logging.getLogger('soliris_home')
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - SOLIRIS-HOME - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    return logger

# Inicializar logger
render_logger = setup_render_logging()

# Adicionar src ao path para importar vanna_core
src_path = os.path.join(os.path.dirname(__file__), "..", "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
render_logger.info(f"🔧 [PATH] Src path adicionado: {src_path}")

try:
    from vanna_core import usar_vn_ask, executar_sql_e_gerar_grafico, gerar_grafico_personalizado
    from database_manager import db_manager
    from dotenv import load_dotenv
    
    # Carregar .env para garantir acesso ao DatabaseManager
    load_dotenv()
    
    print("✅ [DEBUG] Funções importadas com sucesso do vanna_core!")
    print("✅ [DEBUG] DatabaseManager importado com sucesso!")
    render_logger.info("✅ [IMPORT] Módulos principais importados com sucesso")
    print("   - usar_vn_ask: ", usar_vn_ask)
    print("   - executar_sql_e_gerar_grafico: ", executar_sql_e_gerar_grafico)
    print("   - gerar_grafico_personalizado: ", gerar_grafico_personalizado)
    print("   - db_manager: ", db_manager)
except ImportError as e:
    print(f"❌ [DEBUG] Erro ao importar módulos: {e}")
    render_logger.error(f"❌ [IMPORT] Erro ao importar módulos: {e}")
    st.error(f"Erro ao importar módulos: {e}")
    st.stop()

def mostrar_home():
    st.title("🤖 Chatbot de KPIs")
    render_logger.info("🏠 [HOME] Página home acessada")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    mensagem = st.chat_input("Pergunte algo sobre seus KPIs")

    if mensagem:
        print(f"\n🚀 [DEBUG] NOVA MENSAGEM RECEBIDA: {mensagem}")
        render_logger.info(f"💬 [CHAT] Nova pergunta recebida: {mensagem}")
        
        with st.spinner("🔍 Consultando a Vanna..."):
            vn = st.session_state.vanna
            email = st.session_state.email
            id_client = st.session_state.get("id_client", 1)

            print(f"   📝 Parâmetros para usar_vn_ask:")
            print(f"   - Pergunta: {mensagem}")
            print(f"   - Email: {email}")
            print(f"   - ID Client: {id_client}")
            print(f"   - Gerar gráfico: False")
            render_logger.info(f"🔄 [CHAT] Processando pergunta para cliente {id_client}")

            resultado = usar_vn_ask(
                vn=vn,
                pergunta=mensagem,
                email=email,
                id_client=id_client,
                gerar_grafico=False
            )
            
            print(f"   ✅ Resultado retornado de usar_vn_ask:")
            print(f"   - Tipo do resultado: {type(resultado)}")
            print(f"   - Keys disponíveis: {list(resultado.keys()) if isinstance(resultado, dict) else 'N/A'}")
            print(f"   - SQL: {resultado.get('sql', 'N/A') if isinstance(resultado, dict) else 'N/A'}")
            
            # Verificar especificamente o resultado
            resultado_dados = resultado.get("resultado") if isinstance(resultado, dict) else None
            print(f"   - Tipo do campo 'resultado': {type(resultado_dados)}")
            if resultado_dados is not None:
                if hasattr(resultado_dados, 'columns'):
                    print(f"   - É DataFrame com colunas: {list(resultado_dados.columns)}")
                    print(f"   - Número de linhas: {len(resultado_dados)}")
                    print(f"   - Está vazio: {resultado_dados.empty}")
                else:
                    print(f"   - Não é DataFrame, conteúdo: {str(resultado_dados)[:200]}...")
            else:
                print("   - Campo 'resultado' é None")

        st.session_state.chat_history.append({
            "mensagem": mensagem,
            "resposta": resultado.get("resultado"),
            "sql": resultado.get("sql"),
            "figura_auto": None,
            "figura_personalizada": None,
            "mostrar_grafico_auto": False,
            "mostrar_grafico_personalizado": False,
            "pergunta": mensagem
        })

    # Exibe o histórico de conversas
    for i, troca in enumerate(st.session_state.chat_history):
        with st.chat_message("user"):
            st.write(troca["mensagem"])

        with st.chat_message("assistant"):
            # Mostra SQL e dados
            col_sql, col_dados = st.columns([1, 1])
            
            with col_sql:
                st.write("**📋 SQL Gerado:**")
                st.code(troca.get('sql', 'N/A'), language="sql")
            
            with col_dados:
                st.write("**📊 Dados Retornados:**")
                if troca["resposta"] is not None:
                    # Validação para evitar erro com strings
                    try:
                        st.dataframe(troca["resposta"], use_container_width=True)
                    except:
                        st.text(str(troca["resposta"]))
                else:
                    st.warning("Nenhum dado retornado")

            # 🔍 DEBUG: Verificar cada condição para gráficos
            resposta = troca["resposta"]
            sql = troca.get('sql')
            
            print(f"\n🔍 [DEBUG] Verificando condições para gráfico - Conversa {i}")
            print(f"   - Resposta não é None: {resposta is not None}")
            print(f"   - Tipo da resposta: {type(resposta)}")
            
            if resposta is not None:
                print(f"   - Tem atributo 'columns': {hasattr(resposta, 'columns')}")
                if hasattr(resposta, 'columns'):
                    print(f"   - Colunas disponíveis: {list(resposta.columns)}")
                    print(f"   - Número de linhas: {len(resposta)}")
                    print(f"   - DataFrame não está vazio: {not resposta.empty}")
                else:
                    print(f"   - Conteúdo (não DataFrame): {str(resposta)[:200]}...")
            else:
                print("   - Resposta é None")
            
            print(f"   - SQL existe: {sql is not None}")
            if sql:
                print(f"   - SQL (primeiros 100 chars): {sql[:100]}...")
            else:
                print("   - SQL é None ou vazio")
            
            # Seção de gráficos - SÓ aparece se temos dados válidos
            dados_validos = (
                troca["resposta"] is not None and 
                hasattr(troca["resposta"], 'columns') and
                not troca["resposta"].empty and
                troca.get('sql')
            )
            
            print(f"   🎯 RESULTADO FINAL - dados_validos: {dados_validos}")
            
            # 🐛 DEBUG VISUAL: Mostrar estado das condições
            with st.expander("🔍 Debug - Condições para Gráfico", expanded=False):
                st.write(f"**Resposta não é None:** {resposta is not None}")
                st.write(f"**Tipo da resposta:** {type(resposta)}")
                if resposta is not None:
                    st.write(f"**Tem atributo 'columns':** {hasattr(resposta, 'columns')}")
                    if hasattr(resposta, 'columns'):
                        st.write(f"**Colunas:** {list(resposta.columns)}")
                        st.write(f"**Não está vazio:** {not resposta.empty}")
                    else:
                        st.write(f"**Conteúdo (não DataFrame):** {str(resposta)[:200]}...")
                st.write(f"**SQL existe:** {sql is not None}")
                if sql:
                    st.code(f"{sql[:200]}...", language="sql")
                st.write(f"**🎯 Resultado Final - dados_validos:** {dados_validos}")
            
            if dados_validos:
                st.divider()
                
                # Tabs para diferentes tipos de gráfico
                tab_auto, tab_personalizado = st.tabs(["🎯 Gráfico Automático", "🎨 Gráfico Personalizado"])
                
                # TAB 1: Gráfico Automático
                with tab_auto:
                    col_btn_auto, col_status_auto = st.columns([1, 2])
                    
                    with col_btn_auto:
                        if not troca.get("mostrar_grafico_auto", False):
                            # BOTÃO: Só executa quando clicado
                            if st.button("📈 Gerar Gráfico", key=f"grafico_auto_{i}"):
                                print(f"\n🎨 [DEBUG] BOTÃO GRÁFICO AUTO CLICADO - Conversa {i}")
                                print(f"   - SQL disponível: {troca.get('sql')}")
                                print(f"   - Vanna instance: {st.session_state.vanna}")
                                print(f"   - Vanna tem get_plot: {hasattr(st.session_state.vanna, 'get_plot')}")
                                print(f"   - Vanna tem generate_plotly_code: {hasattr(st.session_state.vanna, 'generate_plotly_code')}")
                                print(f"   - Vanna tem get_plotly_figure: {hasattr(st.session_state.vanna, 'get_plotly_figure')}")
                                
                                with st.spinner("🎨 Gerando gráfico automático..."):
                                    vn = st.session_state.vanna
                                    sql = troca.get('sql')
                                    
                                    print(f"   🚀 Iniciando execução de executar_sql_e_gerar_grafico")
                                    print(f"   - SQL a ser executado: {sql}")
                                    
                                    try:
                                        # EXECUÇÃO SÓ ACONTECE AQUI
                                        resultado_grafico = executar_sql_e_gerar_grafico(
                                            vn=vn,
                                            sql=sql,
                                            titulo_grafico=f"Gráfico: {troca['mensagem'][:50]}..."
                                        )
                                        
                                        print(f"   ✅ Resultado da função executar_sql_e_gerar_grafico:")
                                        print(f"   - Status: {resultado_grafico.get('status', 'N/A')}")
                                        print(f"   - Erro: {resultado_grafico.get('erro', 'N/A')}")
                                        print(f"   - Figura existe: {resultado_grafico.get('figura') is not None}")
                                        
                                        # 🐛 DEBUG VISUAL: Mostrar resultado no Streamlit
                                        with st.expander("🔍 Debug - Resultado da Geração", expanded=True):
                                            st.write(f"**Status:** {resultado_grafico.get('status', 'N/A')}")
                                            st.write(f"**Figura existe:** {resultado_grafico.get('figura') is not None}")
                                            if resultado_grafico.get('erro'):
                                                st.write(f"**Erro:** {resultado_grafico.get('erro')}")
                                            if resultado_grafico.get('figura') is not None:
                                                st.write(f"**Tipo da figura:** {type(resultado_grafico.get('figura'))}")
                                        
                                        if resultado_grafico["status"] == "success":
                                            st.session_state.chat_history[i]["mostrar_grafico_auto"] = True
                                            st.session_state.chat_history[i]["figura_auto"] = resultado_grafico["figura"]
                                            st.success("✅ Gráfico gerado com sucesso!")
                                            print(f"   🎯 Gráfico salvo no chat_history[{i}]")
                                        else:
                                            st.error(f"❌ Erro: {resultado_grafico['erro']}")
                                            print(f"   ❌ Erro reportado: {resultado_grafico['erro']}")
                                    
                                    except Exception as e:
                                        print(f"   💥 EXCEÇÃO durante execução: {str(e)}")
                                        import traceback
                                        print(f"   📍 Traceback: {traceback.format_exc()}")
                                        st.error(f"❌ Exceção: {str(e)}")
                                
                                st.rerun()
                        else:
                            if st.button("🔄 Regenerar", key=f"regenerar_auto_{i}"):
                                st.session_state.chat_history[i]["mostrar_grafico_auto"] = False
                                st.session_state.chat_history[i]["figura_auto"] = None
                                st.rerun()
                    
                    with col_status_auto:
                        if troca.get("mostrar_grafico_auto", False):
                            st.success("✅ Gráfico automático ativo - Vanna escolheu o melhor tipo")
                        else:
                            st.info("💡 A IA escolherá automaticamente o melhor tipo de gráfico")
                    
                    # Exibe gráfico automático - SÓ se foi gerado
                    if troca.get("mostrar_grafico_auto", False):
                        figura = troca.get("figura_auto")
                        if figura:
                            st.plotly_chart(figura, use_container_width=True)
                        else:
                            st.warning("⚠️ Gráfico não disponível")

                # TAB 2: Gráfico Personalizado
                with tab_personalizado:
                    if not troca.get("mostrar_grafico_personalizado", False):
                        st.write("**🎨 Configure seu gráfico personalizado:**")
                        
                        # Formulário para gráfico personalizado
                        with st.form(key=f"form_personalizado_{i}"):
                            col_tipo, col_titulo = st.columns(2)
                            
                            with col_tipo:
                                tipo_grafico = st.selectbox(
                                    "Tipo de Gráfico",
                                    ["auto", "bar", "line", "scatter", "pie", "histogram"],
                                    key=f"tipo_{i}",
                                    help="Escolha o tipo específico de gráfico"
                                )
                            
                            with col_titulo:
                                titulo_personalizado = st.text_input(
                                    "Título do Gráfico",
                                    value=f"Análise: {troca['mensagem'][:30]}...",
                                    key=f"titulo_{i}"
                                )
                            
                            # Detecta colunas disponíveis nos dados
                            colunas_disponiveis = list(troca["resposta"].columns)
                            
                            col_x, col_y = st.columns(2)
                            
                            with col_x:
                                x_col = st.selectbox(
                                    "Coluna X (Eixo Horizontal)",
                                    ["auto"] + colunas_disponiveis,
                                    key=f"x_col_{i}",
                                    help="Escolha a coluna para o eixo X"
                                )
                            
                            with col_y:
                                y_col = st.selectbox(
                                    "Coluna Y (Eixo Vertical)",
                                    ["auto"] + colunas_disponiveis,
                                    key=f"y_col_{i}",
                                    help="Escolha a coluna para o eixo Y"
                                )
                            
                            # BOTÃO: Só executa quando clicado
                            submitted = st.form_submit_button("🎨 Criar Gráfico Personalizado")
                            
                            if submitted:
                                print(f"\n🎨 [DEBUG] BOTÃO GRÁFICO PERSONALIZADO CLICADO - Conversa {i}")
                                print(f"   - SQL disponível: {troca.get('sql')}")
                                print(f"   - Tipo gráfico: {tipo_grafico}")
                                print(f"   - Título: {titulo_personalizado}")
                                print(f"   - X col: {x_col}")
                                print(f"   - Y col: {y_col}")
                                print(f"   - Colunas disponíveis: {colunas_disponiveis}")
                                
                                with st.spinner("🎨 Criando gráfico personalizado..."):
                                    vn = st.session_state.vanna
                                    sql = troca.get('sql')
                                    
                                    print(f"   🚀 Iniciando execução de gerar_grafico_personalizado")
                                    print(f"   - SQL a ser executado: {sql}")
                                    
                                    try:
                                        # EXECUÇÃO SÓ ACONTECE AQUI
                                        resultado_personalizado = gerar_grafico_personalizado(
                                            vn=vn,
                                            sql=sql,
                                            tipo_grafico=tipo_grafico,
                                            titulo=titulo_personalizado,
                                            x_col=x_col if x_col != "auto" else None,
                                            y_col=y_col if y_col != "auto" else None
                                        )
                                        
                                        print(f"   ✅ Resultado da função gerar_grafico_personalizado:")
                                        print(f"   - Status: {resultado_personalizado.get('status', 'N/A')}")
                                        print(f"   - Erro: {resultado_personalizado.get('erro', 'N/A')}")
                                        print(f"   - Figura existe: {resultado_personalizado.get('figura') is not None}")
                                        
                                        # 🐛 DEBUG VISUAL: Mostrar resultado no Streamlit
                                        with st.expander("🔍 Debug - Resultado da Geração Personalizada", expanded=True):
                                            st.write(f"**Status:** {resultado_personalizado.get('status', 'N/A')}")
                                            st.write(f"**Figura existe:** {resultado_personalizado.get('figura') is not None}")
                                            if resultado_personalizado.get('erro'):
                                                st.write(f"**Erro:** {resultado_personalizado.get('erro')}")
                                            if resultado_personalizado.get('figura') is not None:
                                                st.write(f"**Tipo da figura:** {type(resultado_personalizado.get('figura'))}")
                                        
                                        if resultado_personalizado["status"] == "success":
                                            st.session_state.chat_history[i]["mostrar_grafico_personalizado"] = True
                                            st.session_state.chat_history[i]["figura_personalizada"] = resultado_personalizado["figura"]
                                            st.success("✅ Gráfico personalizado criado!")
                                            print(f"   🎯 Gráfico personalizado salvo no chat_history[{i}]")
                                        else:
                                            st.error(f"❌ Erro: {resultado_personalizado['erro']}")
                                            print(f"   ❌ Erro reportado: {resultado_personalizado['erro']}")
                                    
                                    except Exception as e:
                                        print(f"   💥 EXCEÇÃO durante execução: {str(e)}")
                                        import traceback
                                        print(f"   📍 Traceback: {traceback.format_exc()}")
                                        st.error(f"❌ Exceção: {str(e)}")
                                
                                st.rerun()
                    
                    else:
                        # Controles quando gráfico personalizado está ativo
                        col_reset, col_info = st.columns([1, 2])
                        
                        with col_reset:
                            if st.button("🔄 Reconfigurar", key=f"reset_personalizado_{i}"):
                                st.session_state.chat_history[i]["mostrar_grafico_personalizado"] = False
                                st.session_state.chat_history[i]["figura_personalizada"] = None
                                st.rerun()
                        
                        with col_info:
                            st.success("✅ Gráfico personalizado ativo")
                        
                        # Exibe gráfico personalizado - SÓ se foi gerado
                        figura_personalizada = troca.get("figura_personalizada")
                        if figura_personalizada:
                            st.plotly_chart(figura_personalizada, use_container_width=True)
                        else:
                            st.warning("⚠️ Gráfico personalizado não disponível")

            else:
                st.warning("⚠️ Gráficos não disponíveis - Verifique se a consulta retornou dados válidos")
                print(f"   ⚠️ Gráficos não exibidos - dados_validos = {dados_validos}")

            st.divider()

    # Seção de teste da persistência PostgreSQL
    st.markdown("---")
    st.subheader("🗄️ Persistência de Dados (PostgreSQL)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Teste de Salvamento**")
        if st.button("💾 Testar Persistência", key="test_persistence"):
            try:
                client_id = st.session_state.get("id_client")
                mock_data = [{
                    "id": f"streamlit-test-{client_id}-01",
                    "training_data_type": "sql",
                    "content": "SELECT COUNT(*) FROM clientes;",
                    "question": "Quantos clientes temos no total?"
                }]
                
                print(f"[DEBUG] Testando persistência para cliente {client_id}")
                success = db_manager.save_training_data(client_id, mock_data)
                
                if success:
                    st.success("✅ Dados de treino salvos no PostgreSQL!")
                    print(f"[SUCCESS] Dados salvos com sucesso no banco")
                else:
                    st.error("❌ Erro ao salvar no banco PostgreSQL.")
                    print(f"[ERROR] Falha ao salvar dados no banco")
                    
            except Exception as e:
                st.error(f"❌ Exceção: {str(e)}")
                print(f"[EXCEPTION] Erro na persistência: {e}")
    
    with col2:
        st.write("**Visualização de Dados**")
        if st.button("📋 Carregar Dados do Banco", key="load_persistence"):
            try:
                client_id = st.session_state.get("id_client")
                print(f"[DEBUG] Carregando dados do cliente {client_id}")
                
                dados = db_manager.load_training_data(client_id)
                
                if dados:
                    st.success(f"✅ {len(dados)} registros carregados!")
                    print(f"[SUCCESS] {len(dados)} registros carregados do banco")
                    
                    # Exibir amostra dos dados
                    with st.expander("📊 Dados de Treinamento", expanded=True):
                        for i, item in enumerate(dados[:5]):  # Mostrar apenas os 5 primeiros
                            with st.container():
                                st.write(f"**Registro {i+1}:**")
                                col_id, col_type = st.columns(2)
                                with col_id:
                                    st.text(f"ID: {item.get('id', 'N/A')}")
                                with col_type:
                                    st.text(f"Tipo: {item.get('training_data_type', 'N/A')}")
                                
                                if item.get('question'):
                                    st.text(f"Pergunta: {item['question']}")
                                st.code(item.get('content', 'N/A'), language='sql')
                                st.divider()
                        
                        if len(dados) > 5:
                            st.info(f"... e mais {len(dados) - 5} registros")
                else:
                    st.warning("⚠️ Nenhum dado encontrado no banco para este cliente")
                    print(f"[WARNING] Nenhum dado encontrado para cliente {client_id}")
                    
            except Exception as e:
                st.error(f"❌ Exceção: {str(e)}")
                print(f"[EXCEPTION] Erro ao carregar dados: {e}")
    
    # Estatísticas do banco
    st.write("**Estatísticas do Banco**")
    try:
        client_id = st.session_state.get("id_client")
        ids_disponiveis = db_manager.get_training_data_ids(client_id)
        
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        with col_stats1:
            st.metric("Total de Registros", len(ids_disponiveis))
        with col_stats2:
            st.metric("Cliente ID", client_id)
        with col_stats3:
            connection_status = "🟢 Conectado" if db_manager.test_connection() else "🔴 Desconectado"
            st.metric("Status Conexão", connection_status)
            
    except Exception as e:
        st.error(f"❌ Erro ao obter estatísticas: {e}")
        print(f"[EXCEPTION] Erro nas estatísticas: {e}")

    print("✅ [DEBUG] Seção de persistência renderizada")
