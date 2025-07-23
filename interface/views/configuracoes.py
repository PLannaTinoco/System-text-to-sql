import streamlit as st
import sys
import os
import pandas as pd
import tempfile
import logging

# 🔧 [LOGGING] Configuração de logging para Render
def setup_render_logging():
    """Configura logging para ser visível no Render"""
    logger = logging.getLogger('soliris_config')
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - SOLIRIS-CONFIG - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    return logger

# Inicializar logger
render_logger = setup_render_logging()

# Adiciona src ao path para importar funções
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from import_csv import processar_csv_para_banco_usuario
from utils.db_utils import conectar_db

def obter_tabelas_usuario(client_id: int) -> list:
    """Obtém lista de tabelas do usuário"""
    render_logger.info(f"🔍 [DB] Buscando tabelas para cliente {client_id}")
    
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE %s
            ORDER BY table_name
        """, (f"cli{client_id:02d}_%",))
        
        tabelas = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        render_logger.info(f"✅ [DB] {len(tabelas)} tabelas encontradas para cliente {client_id}")
        return tabelas
        
    except Exception as e:
        render_logger.error(f"❌ [DB] Erro ao obter tabelas para cliente {client_id}: {e}")
        st.error(f"Erro ao obter tabelas: {e}")
        return []

def obter_preview_tabela(nome_tabela: str, limit: int = 5):
    """Obtém preview de uma tabela"""
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        # Obtém colunas
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (nome_tabela,))
        
        colunas = cursor.fetchall()
        
        # Obtém dados
        cursor.execute(f'SELECT * FROM "{nome_tabela}" LIMIT %s', (limit,))
        dados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return colunas, dados
        
    except Exception as e:
        st.error(f"Erro ao obter preview da tabela: {e}")
        return [], []

def deletar_tabela(nome_tabela: str) -> bool:
    """Deleta uma tabela do banco de dados"""
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        # Executa DROP TABLE
        cursor.execute(f'DROP TABLE IF EXISTS "{nome_tabela}"')
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        st.error(f"Erro ao deletar tabela: {e}")
        return False

def mostrar_configuracoes():
    st.title("⚙️ Configurações do Sistema")
    
    # ADICIONAR a nova tab do HubSpot e KPIs
    tab_usuario, tab_upload, tab_tabelas, tab_hubspot, tab_kpis = st.tabs([
        "👤 Minha Conta", 
        "📁 Upload CSV",
        "🗃️ Minhas Tabelas",
        "🔗 HubSpot API",
        "📊 KPIs"  # NOVA TAB
    ])
    
    # ========== TAB 1: CONTA DO USUÁRIO ==========
    with tab_usuario:
        st.subheader("👤 Informações da Conta")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📧 Email:**", st.session_state.get("email", "N/A"))
            st.write("**👤 Nome:**", st.session_state.get("name", "N/A"))
            st.write("**🆔 ID:**", st.session_state.get("id_client", "N/A"))
        
        with col2:
            st.info("🔧 Funcionalidades futuras:")
            st.write("- Alterar nome")
            st.write("- Alterar senha")
            st.write("- Histórico de acessos")
            st.write("- Preferências do sistema")
    
    # ========== TAB 2: UPLOAD CSV ==========
    with tab_upload:
        st.subheader("📁 Upload de Arquivos CSV")
        
        id_client = st.session_state.get("id_client")
        if not id_client:
            st.error("ID do cliente não encontrado. Faça login novamente.")
            return
        
        st.write("📋 **Instruções:**")
        st.write("- Carregue arquivos CSV para criar tabelas no banco de dados")
        st.write("- O nome da tabela será: `cli{:02d}_<nome_arquivo>`".format(id_client))
        st.write("- Arquivos grandes podem demorar alguns minutos para processar")
        
        st.divider()
        
        # Upload de arquivo
        uploaded_file = st.file_uploader(
            "Escolha um arquivo CSV",
            type=['csv'],
            help="Selecione um arquivo CSV para importar"
        )
        
        if uploaded_file is not None:
            # Preview do arquivo
            st.write("📊 **Preview do arquivo:**")
            try:
                df = pd.read_csv(uploaded_file, nrows=5)
                st.dataframe(df)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Linhas (amostra):** {len(df)}")
                    st.write(f"**Colunas:** {len(df.columns)}")
                
                with col2:
                    # Nome da tabela
                    nome_base = os.path.splitext(uploaded_file.name)[0]
                    nome_tabela = f"cli{id_client:02d}_{nome_base}"
                    st.write(f"**Nome da tabela:** `{nome_tabela}`")
                
                st.divider()
                
                # Configurações de importação
                col1, col2 = st.columns(2)
                
                with col1:
                    nome_personalizado = st.text_input(
                        "Nome personalizado (opcional)",
                        value=nome_base,
                        help="Deixe em branco para usar o nome do arquivo"
                    )
                
                with col2:
                    confirmar_importacao = st.checkbox(
                        "Confirmo que quero importar este arquivo",
                        help="Marque para habilitar a importação"
                    )
                
                # Botão de importação
                if st.button("🚀 Importar para Banco de Dados", disabled=not confirmar_importacao):
                    if nome_personalizado.strip():
                        nome_final = nome_personalizado.strip()
                    else:
                        nome_final = nome_base
                    
                    # Salva arquivo temporário
                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_file:
                        uploaded_file.seek(0)
                        tmp_file.write(uploaded_file.read())
                        tmp_path = tmp_file.name
                    
                    try:
                        with st.spinner(f"Importando {uploaded_file.name}..."):
                            processar_csv_para_banco_usuario(tmp_path, nome_final, id_client)
                        
                        st.success(f"✅ Arquivo importado com sucesso!")
                        st.success(f"📊 Tabela criada: `cli{id_client:02d}_{nome_final}`")
                        
                        # Remove arquivo temporário
                        os.unlink(tmp_path)
                        
                        # Rerun para atualizar a lista de tabelas
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erro na importação: {str(e)}")
                        # Remove arquivo temporário em caso de erro
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                
            except Exception as e:
                st.error(f"❌ Erro ao ler arquivo: {str(e)}")
    
    # ========== TAB 3: MINHAS TABELAS ==========
    with tab_tabelas:
        st.subheader("🗃️ Minhas Tabelas")
        
        id_client = st.session_state.get("id_client")
        if not id_client:
            st.error("ID do cliente não encontrado. Faça login novamente.")
            return
        
        # Obtém tabelas do usuário
        tabelas = obter_tabelas_usuario(id_client)
        
        if tabelas:
            st.write(f"📊 **{len(tabelas)} tabelas** encontradas:")
            
            # Seleção de tabela
            tabela_selecionada = st.selectbox(
                "Selecione uma tabela para visualizar:",
                tabelas,
                format_func=lambda x: x.replace(f"cli{id_client:02d}_", "")
            )
            
            if tabela_selecionada:
                st.divider()
                
                # Informações da tabela
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**📋 Tabela:** `{tabela_selecionada}`")
                    nome_amigavel = tabela_selecionada.replace(f"cli{id_client:02d}_", "")
                    st.write(f"**📝 Nome amigável:** {nome_amigavel}")
                
                with col2:
                    if st.button("🔄 Atualizar"):
                        st.rerun()
                
                with col3:
                    # Botão de deletar com confirmação
                    if st.button("🗑️ Deletar", type="secondary"):
                        st.session_state[f"confirmar_delete_{tabela_selecionada}"] = True
                
                # Confirmação de deleção
                if st.session_state.get(f"confirmar_delete_{tabela_selecionada}", False):
                    st.warning(f"⚠️ **ATENÇÃO:** Você tem certeza que deseja deletar a tabela `{nome_amigavel}`?")
                    st.write("Esta ação é **irreversível** e todos os dados serão perdidos permanentemente.")
                    
                    col_conf1, col_conf2, col_conf3 = st.columns([1, 1, 2])
                    
                    with col_conf1:
                        if st.button("✅ Sim, deletar", type="primary"):
                            with st.spinner(f"Deletando tabela {nome_amigavel}..."):
                                sucesso = deletar_tabela(tabela_selecionada)
                            
                            if sucesso:
                                st.success(f"✅ Tabela `{nome_amigavel}` deletada com sucesso!")
                                # Limpa o estado de confirmação
                                if f"confirmar_delete_{tabela_selecionada}" in st.session_state:
                                    del st.session_state[f"confirmar_delete_{tabela_selecionada}"]
                                st.rerun()
                            else:
                                st.error("❌ Erro ao deletar a tabela.")
                    
                    with col_conf2:
                        if st.button("❌ Cancelar"):
                            # Limpa o estado de confirmação
                            if f"confirmar_delete_{tabela_selecionada}" in st.session_state:
                                del st.session_state[f"confirmar_delete_{tabela_selecionada}"]
                            st.rerun()
                    
                    with col_conf3:
                        st.write("")  # Espaço vazio
                
                # Só mostra o preview se não estiver no modo de confirmação
                if not st.session_state.get(f"confirmar_delete_{tabela_selecionada}", False):
                    # Preview da tabela
                    colunas, dados = obter_preview_tabela(tabela_selecionada)
                    
                    if colunas:
                        st.write("**📊 Estrutura da tabela:**")
                        
                        # Mostra colunas
                        col_info = []
                        for col_name, col_type in colunas:
                            col_info.append({"Coluna": col_name, "Tipo": col_type})
                        
                        st.dataframe(pd.DataFrame(col_info), use_container_width=True)
                        
                        # Mostra dados
                        if dados:
                            st.write("**📋 Preview dos dados (5 primeiras linhas):**")
                            col_names = [col[0] for col in colunas]
                            df_preview = pd.DataFrame(dados, columns=col_names)
                            st.dataframe(df_preview, use_container_width=True)
                        else:
                            st.info("A tabela está vazia.")
                    else:
                        st.error("Não foi possível obter informações da tabela.")
        else:
            st.info("📭 Você ainda não possui tabelas importadas.")
            st.write("💡 **Dica:** Use a aba 'Upload CSV' para importar seus dados.")
    
    # ========== TAB 4: HUBSPOT INTEGRATION ==========
    with tab_hubspot:
        st.subheader("🔗 Importação de Dados HubSpot")
        
        # IMPORT SIMPLIFICADO E DIRETO
        hubspot_disponivel = False
        
        try:
            # Adiciona o diretório raiz do projeto ao path
            import sys
            import os
            
            # Caminho para o diretório interface
            interface_dir = os.path.dirname(os.path.dirname(__file__))
            if interface_dir not in sys.path:
                sys.path.insert(0, interface_dir)
            
            # Import usando caminho relativo do utils
            from utils.hubspot_integration import HubSpotIntegration, salvar_dados_hubspot_usuario
            hubspot_disponivel = True
            st.success("✅ Módulo HubSpot carregado com sucesso!")
            
        except ImportError as e:
            # Tentativa alternativa: import direto
            try:
                import sys
                import os
                
                utils_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'utils')
                sys.path.insert(0, utils_path)
                
                from utils import hubspot_integration
                HubSpotIntegration = hubspot_integration.HubSpotIntegration
                salvar_dados_hubspot_usuario = hubspot_integration.salvar_dados_hubspot_usuario
                hubspot_disponivel = True
                st.success("✅ Módulo HubSpot carregado (alternativa)")
                
            except Exception as e2:
                hubspot_disponivel = False
                st.error(f"❌ Erro ao carregar HubSpot: {e2}")
                
                # Debug detalhado
                with st.expander("� Debug Info"):
                    st.write(f"**Erro principal:** {e}")
                    st.write(f"**Erro alternativo:** {e2}")
                    st.write(f"**Current file:** {__file__}")
                    st.write(f"**Interface dir:** {interface_dir}")
                    st.write(f"**Utils path:** {utils_path}")
                    st.write(f"**Utils exists:** {os.path.exists(utils_path)}")
                    
                    if os.path.exists(utils_path):
                        st.write("**Files in utils:**")
                        for f in os.listdir(utils_path):
                            st.write(f"- {f}")
        
        if not hubspot_disponivel:
            st.warning("⚠️ Funcionalidade HubSpot temporariamente indisponível")
            st.info("💡 Entre em contato com o administrador do sistema")
            return
        
        # CORREÇÃO: Verifica se usuário está logado E valida ID
        id_client = st.session_state.get("id_client")
        if not id_client:
            st.error("❌ Usuário não identificado. Faça login novamente.")
            return
        
        # CORREÇÃO: Garantir que id_client seja int válido
        try:
            id_client = int(id_client)
            if id_client <= 0:
                raise ValueError("ID deve ser positivo")
        except (ValueError, TypeError):
            st.error(f"❌ ID do cliente inválido: {id_client}")
            st.error("💡 Faça logout e login novamente")
            return
        
        # Debug do usuário logado
        st.info(f"👤 **Usuário logado:** ID {id_client} (Prefixo: cli{id_client:02d}_)")
        
        # Configuração da API
        st.write("### 🔑 Configuração da API")
        
        # Opção de usar token global ou individual
        usar_token_global = st.checkbox("Usar token configurado no sistema", value=True)
        
        if usar_token_global:
            # Testa o token global
            hubspot = HubSpotIntegration()
            if hubspot.validar_token():
                st.success("✅ Token do sistema validado com sucesso!")
            else:
                st.error("❌ Token do sistema inválido. Entre em contato com o administrador.")
                return
        else:
            # Permite token individual
            token_individual = st.text_input(
                "Token HubSpot individual:",
                type="password",
                help="Insira seu token pessoal do HubSpot"
            )
            
            if token_individual:
                hubspot = HubSpotIntegration(token_individual)
                if hubspot.validar_token():
                    st.success("✅ Token individual validado!")
                else:
                    st.error("❌ Token individual inválido.")
                    return
            else:
                st.info("💡 Insira um token para continuar.")
                return
        
        st.divider()
        
        # Seleção do tipo de dados
        st.write("### 📊 Importar Dados")
        
        tipo_dados = st.selectbox(
            "Escolha o tipo de dados para importar:",
            [
                "👤 Contatos",
                "💼 Deals (Negócios)",
                "🏢 Empresas"
            ]
        )
        
        # Configurações de importação
        col1, col2 = st.columns(2)
        
        with col1:
            limite = st.number_input(
                "Limite de registros:",
                min_value=10,
                max_value=100,  # Limite máximo da API HubSpot
                value=50,       # Valor padrão menor
                step=10,
                help="Máximo 100 registros por importação (limite da API HubSpot)"
            )
        
        with col2:
            nome_tabela = st.text_input(
                "Nome da tabela:",
                value=f"hubspot_{tipo_dados.split()[1].lower() if len(tipo_dados.split()) > 1 else 'dados'}",
                help="Nome que será dado à tabela no banco de dados"
            )
        
        # CORREÇÃO: Preview da tabela que será criada
        nome_tabela_final_preview = f"cli{id_client:02d}_{nome_tabela}"
        st.info(f"📋 **Tabela que será criada:** `{nome_tabela_final_preview}`")
        
        # Botão de importação
        if st.button("📥 Importar Dados", type="primary"):
            # CORREÇÃO: Debug antes de importar
            st.write(f"🔍 **Debug da Importação:**")
            st.write(f"   • Cliente ID: {id_client}")
            st.write(f"   • Tipo: {tipo_dados}")
            st.write(f"   • Limite: {limite}")
            st.write(f"   • Nome base: {nome_tabela}")
            st.write(f"   • Nome final: `{nome_tabela_final_preview}`")
            
            with st.spinner(f"Importando {tipo_dados.lower()}..."):
                try:
                    # Obtém dados baseado no tipo selecionado
                    if "Contatos" in tipo_dados:
                        df = hubspot.obter_contatos(limite)
                    elif "Deals" in tipo_dados:
                        df = hubspot.obter_deals(limite)
                    elif "Empresas" in tipo_dados:
                        df = hubspot.obter_empresas(limite)
                    
                    if not df.empty:
                        # Preview dos dados
                        st.write(f"### 👀 Preview dos Dados ({len(df)} registros)")
                        st.dataframe(df.head(10))
                        
                        # Salva automaticamente no banco
                        with st.spinner("💾 Salvando no banco de dados..."):
                            if salvar_dados_hubspot_usuario(df, nome_tabela, id_client):
                                st.balloons()
                                st.success(f"🎉 {len(df)} registros importados com sucesso!")
                                
                                # Informações da tabela criada
                                nome_final = f"cli{id_client:02d}_{nome_tabela}"
                                st.info(f"📋 Tabela criada: `{nome_final}`")
                                st.info("💡 Use esta tabela nos alertas e no chatbot!")
                                
                                # Atualiza a interface
                                st.rerun()
                            else:
                                st.error("❌ Falha ao salvar dados no banco.")
                    else:
                        st.warning("⚠️ Nenhum dado encontrado para importar.")
                        st.info("💡 Verifique se sua conta HubSpot possui dados do tipo selecionado.")
                        
                except Exception as e:
                    st.error(f"❌ Erro na importação: {e}")
                    import traceback
                    st.error(f"🔍 Detalhes técnicos: {traceback.format_exc()}")
        
        st.divider()
        
        # Informações sobre sincronização
        st.write("### 🔄 Sincronização")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("""
            **ℹ️ Como funciona:**
            - Dados são importados do HubSpot
            - Salvos com prefixo do seu usuário
            - Disponíveis no chatbot e alertas
            - Atualizações manuais por enquanto
            """)
        
        with col2:
            if st.button("🔄 Sincronizar Novamente"):
                st.info("🚧 Funcionalidade em desenvolvimento...")
                st.write("Em breve: sincronização automática agendada!")
    
    # ========== TAB 5: KPIs ==========
    with tab_kpis:
        st.subheader("📊 Gerenciamento de KPIs")
        
        id_client = st.session_state.get("id_client")
        if not id_client:
            st.error("❌ Usuário não identificado. Faça login novamente.")
            return
        
        st.write("Gerencie seus KPIs (Key Performance Indicators) personalizados:")
        
        # Verifica se já existe tabela de KPIs
        nome_tabela_kpis = f"cli{id_client:02d}_kpis_definicoes"
        
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            
            # Verifica se tabela existe
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (nome_tabela_kpis,))
            
            tabela_existe = cursor.fetchone()[0]
            
            if tabela_existe:
                # Mostra KPIs existentes
                cursor.execute(f'SELECT id, nome_kpi, descricao, data_criacao FROM "{nome_tabela_kpis}" ORDER BY id')
                kpis = cursor.fetchall()
                
                if kpis:
                    st.success(f"✅ {len(kpis)} KPIs configurados")
                    
                    # Mostra lista de KPIs
                    for kpi_id, nome, desc, data in kpis:
                        with st.expander(f"📈 {nome}"):
                            st.write(f"**Descrição:** {desc}")
                            st.write(f"**Criado em:** {data}")
                else:
                    st.info("📭 Nenhum KPI configurado ainda")
            else:
                st.info("📭 Tabela de KPIs ainda não foi criada")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            st.error(f"❌ Erro ao verificar KPIs: {e}")
        
        st.divider()
        
        # Upload de novo arquivo de KPIs
        st.write("### 📁 Importar Novos KPIs")
        
        uploaded_kpis = st.file_uploader(
            "Arquivo CSV com KPIs:",
            type=['csv'],
            help="CSV com colunas: nome, descricao (formula_sql será gerada automaticamente)"
        )
        
        if uploaded_kpis:
            try:
                # Preview do arquivo
                df_kpis = pd.read_csv(uploaded_kpis, nrows=10)
                st.write("**📋 Preview do arquivo:**")
                st.dataframe(df_kpis)
                
                # Valida colunas obrigatórias
                colunas_necessarias = ['nome', 'descricao']
                colunas_presentes = df_kpis.columns.tolist()
                
                if all(col in colunas_presentes for col in colunas_necessarias):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        substituir = st.checkbox(
                            "Substituir KPIs existentes",
                            help="Se marcado, remove todos os KPIs atuais"
                        )
                    
                    with col2:
                        st.write(f"**KPIs encontrados:** {len(df_kpis)}")
                    
                    if st.button("📥 Importar KPIs", type="primary"):
                        try:
                            # Salva arquivo temporário
                            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_file:
                                uploaded_kpis.seek(0)
                                tmp_file.write(uploaded_kpis.read())
                                tmp_path = tmp_file.name
                            
                            # Processa KPIs usando a função do cadastro
                            sys.path.append(os.path.join(os.path.dirname(__file__)))
                            from cadastro_setup import processar_csv_kpis_usuario
                            
                            sucesso = processar_csv_kpis_usuario(tmp_path, id_client)
                            
                            if sucesso:
                                st.balloons()
                                st.success(f"🎉 KPIs importados com sucesso!")
                                os.unlink(tmp_path)
                                st.rerun()
                            else:
                                st.error("❌ Falha ao importar KPIs")
                                if os.path.exists(tmp_path):
                                    os.unlink(tmp_path)
                                    
                        except Exception as e:
                            st.error(f"❌ Erro ao importar: {e}")
                            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                else:
                    st.error("❌ CSV deve conter as colunas: nome, descricao")
                    st.write("**Colunas encontradas:**", colunas_presentes)
                    
            except Exception as e:
                st.error(f"❌ Erro ao ler CSV: {e}")
        
        # Modelo de CSV para download
        st.write("### 💡 Modelo de CSV")
        st.write("Precisa de um modelo? Baixe este exemplo e adapte com seus KPIs:")
        
        modelo_kpis = pd.DataFrame({
            'nome': [
                'Total de Vendas',
                'Ticket Médio',
                'Taxa de Conversão',
                'Clientes Ativos',
                'Receita Recorrente'
            ],
            'descricao': [
                'Soma total de vendas do período',
                'Valor médio por venda realizada',
                'Percentual de conversão de leads em vendas',
                'Número de clientes com atividade no período',
                'Receita mensal recorrente (MRR)'
            ]
        })
        
        csv_modelo = modelo_kpis.to_csv(index=False)
        st.download_button(
            "📄 Baixar Modelo CSV de KPIs",
            csv_modelo,
            "modelo_kpis.csv",
            "text/csv",
            help="Baixe este modelo e adapte com seus KPIs específicos. As fórmulas SQL serão geradas automaticamente!"
        )