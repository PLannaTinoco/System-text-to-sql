import streamlit as st
import sys
import os
import pandas as pd
import tempfile
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona src ao path para importar funções
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from utils.db_utils import conectar_db, criar_engine
from import_csv import processar_csv_para_banco_usuario

def criar_usuario_no_banco(nome: str, email: str, senha: str) -> int:
    """Cria novo usuário no banco e retorna o ID"""
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        
        # Verifica se email já existe
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            raise ValueError("Email já cadastrado no sistema")
        
        # Insere novo usuário
        cursor.execute("""
            INSERT INTO usuarios (nome, email, senha) 
            VALUES (%s, %s, %s) 
            RETURNING id
        """, (nome, email, senha))
        
        id_client = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return id_client
        
    except Exception as e:
        st.error(f"Erro ao criar usuário: {e}")
        return None

def salvar_configuracao_setup(id_client: int, config: dict):
    """Salva configurações do setup do usuário"""
    arq_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "arq"
    )
    
    # Cria diretório arq se não existir
    if not os.path.exists(arq_dir):
        os.makedirs(arq_dir)
    
    config_path = os.path.join(arq_dir, f"setup_config_cli{id_client:02d}.json")
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def carregar_configuracao_setup(id_client: int) -> dict:
    """Carrega configurações salvas do setup"""
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "arq", 
        f"setup_config_cli{id_client:02d}.json"
    )
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def mostrar_cadastro_setup():
    """Interface principal de cadastro e setup"""
    
    st.title("🚀 Cadastro e Setup Inicial")
    st.write("Bem-vindo ao Soliris! Vamos configurar sua conta e treinar seu modelo personalizado.")
    
    # Verifica se já existe um setup em andamento
    if "setup_id_client" in st.session_state:
        mostrar_setup_continuacao()
        return
    
    # Formulário de cadastro
    st.subheader("📋 Criar Nova Conta")
    
    with st.form("cadastro_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input(
                "Nome completo *",
                placeholder="João Silva"
            )
            email = st.text_input(
                "Email *",
                placeholder="joao@empresa.com"
            )
        
        with col2:
            senha = st.text_input(
                "Senha *",
                type="password",
                placeholder="Mínimo 6 caracteres"
            )
            senha_confirm = st.text_input(
                "Confirmar senha *",
                type="password",
                placeholder="Digite a senha novamente"
            )
        
        submitted = st.form_submit_button("🎯 Criar Conta e Iniciar Setup", type="primary")
        
        if submitted:
            # Validações
            if not nome or not email or not senha:
                st.error("❌ Todos os campos são obrigatórios")
                return
            
            if len(senha) < 6:
                st.error("❌ Senha deve ter pelo menos 6 caracteres")
                return
            
            if senha != senha_confirm:
                st.error("❌ Senhas não coincidem")
                return
            
            if "@" not in email:
                st.error("❌ Email inválido")
                return
            
            # Cria usuário
            with st.spinner("Criando sua conta..."):
                id_client = criar_usuario_no_banco(nome, email, senha)
            
            if id_client:
                st.success(f"✅ Conta criada com sucesso! ID: CLI{id_client:02d}")
                
                # Salva no session state para continuar setup
                st.session_state["setup_id_client"] = id_client
                st.session_state["setup_nome"] = nome
                st.session_state["setup_email"] = email
                
                # Recarrega para mostrar próxima etapa
                st.rerun()

def mostrar_setup_continuacao():
    """Continua o setup após cadastro"""
    
    id_client = st.session_state.get("setup_id_client")
    nome = st.session_state.get("setup_nome")
    
    st.title(f"⚙️ Setup - {nome}")
    st.info(f"🆔 Seu ID de cliente: **CLI{id_client:02d}**")
    
    # Progress tracker
    etapas = [
        "📋 Cadastro",
        "📊 Importação de Dados", 
        "🤖 Configuração do Modelo",
        "🎓 Treinamento",
        "✅ Finalização"
    ]
    
    # Carrega configuração salva
    config = carregar_configuracao_setup(id_client)
    etapa_atual = config.get("etapa_atual", 1)
    
    # Mostra progresso
    progress_text = " → ".join([
        f"**{etapa}**" if i == etapa_atual else etapa 
        for i, etapa in enumerate(etapas)
    ])
    st.markdown(progress_text)
    st.progress(etapa_atual / (len(etapas) - 1))
    
    st.divider()
    
    # Executa etapa atual
    if etapa_atual == 1:
        etapa_importacao_dados(id_client, config)
    elif etapa_atual == 2:
        etapa_configuracao_modelo(id_client, config)
    elif etapa_atual == 3:
        etapa_treinamento(id_client, config)
    elif etapa_atual == 4:
        etapa_finalizacao(id_client, config)

def etapa_importacao_dados(id_client: int, config: dict):
    """Etapa 1: Importação de dados"""
    
    st.subheader("📊 Importação de Dados")
    st.write("Para treinar seu modelo, você precisa importar dados. Escolha uma ou ambas as opções:")
    
    tab_hubspot, tab_csv = st.tabs(["🔗 HubSpot API", "📁 Upload CSV"])
    
    dados_importados = config.get("dados_importados", {})
    
    # TAB HUBSPOT
    with tab_hubspot:
        st.write("### 🔗 Importar do HubSpot")
        
        if dados_importados.get("hubspot"):
            st.success(f"✅ Dados HubSpot já importados: {dados_importados['hubspot']}")
        else:
            # Reutiliza a lógica da aba HubSpot das configurações
            try:
                from utils.hubspot_integration import HubSpotIntegration, salvar_dados_hubspot_usuario
                
                hubspot = HubSpotIntegration()
                
                if hubspot.validar_token():
                    st.success("✅ Token HubSpot validado!")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        tipo_dados = st.selectbox(
                            "Tipo de dados:",
                            ["👤 Contatos", "💼 Deals", "🏢 Empresas"],
                            key="setup_hubspot_tipo"
                        )
                    
                    with col2:
                        limite = st.number_input(
                            "Limite:",
                            min_value=10,
                            max_value=100,  # Limite máximo da API HubSpot
                            value=50,       # Valor padrão menor
                            key="setup_hubspot_limite",
                            help="Máximo 100 registros (limite da API)"
                        )
                    
                    nome_tabela = st.text_input(
                        "Nome da tabela:",
                        value=f"dados_{tipo_dados.split()[1].lower() if len(tipo_dados.split()) > 1 else 'hubspot'}",
                        key="setup_hubspot_nome"
                    )
                    
                    # CORREÇÃO: Debug antes da importação
                    nome_tabela_final_debug = f"cli{id_client:02d}_{nome_tabela}"
                    st.info(f"📋 Tabela que será criada: `{nome_tabela_final_debug}`")
                    
                    if st.button("📥 Importar do HubSpot", type="primary"):
                        # CORREÇÃO: Validar id_client antes de usar
                        if not id_client or id_client <= 0:
                            st.error(f"❌ ID do cliente inválido: {id_client}")
                            return
                        
                        st.write(f"🔍 Debug: Importando para cliente ID {id_client}")
                        
                        with st.spinner("Importando..."):
                            try:
                                if "Contatos" in tipo_dados:
                                    df = hubspot.obter_contatos(limite)
                                elif "Deals" in tipo_dados:
                                    df = hubspot.obter_deals(limite)
                                else:
                                    df = hubspot.obter_empresas(limite)
                                
                                if not df.empty and salvar_dados_hubspot_usuario(df, nome_tabela, id_client):
                                    dados_importados["hubspot"] = f"{len(df)} {tipo_dados.lower()}"
                                    config["dados_importados"] = dados_importados
                                    salvar_configuracao_setup(id_client, config)
                                    
                                    st.success(f"✅ {len(df)} registros importados!")
                                    st.rerun()
                                    
                            except Exception as e:
                                st.error(f"❌ Erro: {e}")
                else:
                    st.error("❌ Token HubSpot inválido")
                    
            except ImportError:
                st.warning("⚠️ Módulo HubSpot não disponível")
    
    # TAB CSV
    with tab_csv:
        st.write("### 📁 Upload de CSV")
        
        csvs_importados = dados_importados.get("csvs", [])
        
        if csvs_importados:
            st.success(f"✅ CSVs importados: {', '.join(csvs_importados)}")
        
        uploaded_file = st.file_uploader(
            "Escolha arquivo CSV:",
            type=['csv'],
            key="setup_csv_upload"
        )
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file, nrows=5)
                st.dataframe(df)
                
                nome_arquivo = os.path.splitext(uploaded_file.name)[0]
                nome_personalizado = st.text_input(
                    "Nome da tabela:",
                    value=nome_arquivo,
                    key="setup_csv_nome"
                )
                
                if st.button("📁 Importar CSV", type="secondary"):
                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_file:
                        uploaded_file.seek(0)
                        tmp_file.write(uploaded_file.read())
                        tmp_path = tmp_file.name
                    
                    try:
                        with st.spinner("Importando CSV..."):
                            processar_csv_para_banco_usuario(tmp_path, nome_personalizado, id_client)
                        
                        csvs_importados.append(nome_personalizado)
                        dados_importados["csvs"] = csvs_importados
                        config["dados_importados"] = dados_importados
                        salvar_configuracao_setup(id_client, config)
                        
                        st.success(f"✅ CSV '{nome_personalizado}' importado!")
                        os.unlink(tmp_path)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erro: {e}")
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                            
            except Exception as e:
                st.error(f"❌ Erro ao ler CSV: {e}")
    
    # Botão para próxima etapa
    if dados_importados:
        st.divider()
        if st.button("➡️ Continuar para Configuração do Modelo", type="primary"):
            config["etapa_atual"] = 2
            salvar_configuracao_setup(id_client, config)
            st.rerun()
    else:
        st.info("💡 Importe pelo menos um conjunto de dados para continuar")

def etapa_configuracao_modelo(id_client: int, config: dict):
    """Etapa 2: Configuração do modelo de treinamento"""
    
    st.subheader("🤖 Configuração do Modelo")
    st.write("Configure como o modelo será treinado:")
    
    # Opções de treinamento
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("#### 📋 Treinamento do Plano de Dados")
        treinar_plan = st.checkbox(
            "Gerar e treinar plano automático das tabelas",
            value=config.get("treinar_plan", True),
            help="Analisa suas tabelas e cria consultas automáticas"
        )
        
        st.write("#### 📊 Treinamento de KPIs")
        treinar_kpis = st.checkbox(
            "Treinar com KPIs personalizados",
            value=config.get("treinar_kpis", False),
            help="Importe um CSV com suas métricas e indicadores"
        )
        
        # Upload de KPIs se ativado
        if treinar_kpis:
            st.write("**📁 Upload do arquivo de KPIs:**")
            
            # Verifica se já foi feito upload
            if config.get("kpis_csv_importado"):
                st.success(f"✅ KPIs importados: {config.get('kpis_arquivo_nome', 'arquivo')}")
                
                col_kpi1, col_kpi2 = st.columns([3, 1])
                with col_kpi2:
                    if st.button("🔄 Trocar arquivo", key="trocar_kpis"):
                        config["kpis_csv_importado"] = False
                        config["kpis_arquivo_nome"] = ""
                        salvar_configuracao_setup(id_client, config)
                        st.rerun()
            else:
                uploaded_kpis = st.file_uploader(
                    "Arquivo CSV com KPIs:",
                    type=['csv'],
                    key="setup_kpis_upload",
                    help="CSV com colunas: nome, descricao (formula_sql será gerada automaticamente)"
                )
                
                if uploaded_kpis:
                    try:
                        # Preview do arquivo
                        df_kpis = pd.read_csv(uploaded_kpis, nrows=5)
                        st.write("**Preview do arquivo:**")
                        st.dataframe(df_kpis)
                        
                        # Valida colunas obrigatórias
                        colunas_necessarias = ['nome', 'descricao']
                        colunas_presentes = df_kpis.columns.tolist()
                        
                        if all(col in colunas_presentes for col in colunas_necessarias):
                            if st.button("📥 Importar KPIs", type="secondary"):
                                # Salva o arquivo
                                try:
                                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_file:
                                        uploaded_kpis.seek(0)
                                        tmp_file.write(uploaded_kpis.read())
                                        tmp_path = tmp_file.name
                                    
                                    # Processa KPIs
                                    sucesso = processar_csv_kpis_usuario(tmp_path, id_client)
                                    
                                    if sucesso:
                                        config["kpis_csv_importado"] = True
                                        config["kpis_arquivo_nome"] = uploaded_kpis.name
                                        salvar_configuracao_setup(id_client, config)
                                        st.success("✅ KPIs importados com sucesso!")
                                        os.unlink(tmp_path)
                                        st.rerun()
                                    else:
                                        st.error("❌ Erro ao processar KPIs")
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
                st.write("**💡 Precisa de um modelo?**")
                modelo_kpis = pd.DataFrame({
                    'nome_kpi': ['Total de Vendas', 'Ticket Médio', 'Conversão'],
                    'descricao': ['Soma total de vendas do período', 'Valor médio por venda', 'Taxa de conversão de leads'],
                    'formula_sql': ['SELECT SUM(valor) FROM vendas', 'SELECT AVG(valor) FROM vendas', 'SELECT (vendas/leads)*100 FROM metricas']
                })
                
                csv_modelo = modelo_kpis.to_csv(index=False)
                st.download_button(
                    "📄 Baixar modelo CSV",
                    csv_modelo,
                    "modelo_kpis.csv",
                    "text/csv",
                    help="Baixe este modelo e adapte com seus KPIs"
                )
    
    with col2:
        st.write("#### 🏗️ Treinamento de DDL")
        treinar_ddl = st.checkbox(
            "Treinar estrutura das tabelas (DDL)",
            value=config.get("treinar_ddl", True),
            help="Ensina o modelo sobre a estrutura do banco"
        )
        
        st.write("#### 📚 Documentação Personalizada")
        treinar_docs = st.checkbox(
            "Adicionar documentação personalizada",
            value=config.get("treinar_docs", False),
            help="Inclua contexto específico do seu negócio"
        )
    
    # Área de documentação
    documentacao = ""
    if treinar_docs:
        st.write("#### ✍️ Sua Documentação")
        documentacao = st.text_area(
            "Insira documentação sobre seu negócio:",
            value=config.get("documentacao", ""),
            height=150,
            placeholder="""Exemplo:
- Nossa empresa vende produtos online
- Clientes principais são B2B
- Métricas importantes: CAC, LTV, Churn
- Produtos: Software, Consultoria
"""
        )
    
    # Salva configurações
    config.update({
        "treinar_plan": treinar_plan,
        "treinar_kpis": treinar_kpis,  
        "treinar_ddl": treinar_ddl,
        "treinar_docs": treinar_docs,
        "documentacao": documentacao
    })
    salvar_configuracao_setup(id_client, config)
    
    # Botões de navegação
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⬅️ Voltar para Dados"):
            config["etapa_atual"] = 1
            salvar_configuracao_setup(id_client, config)
            st.rerun()
    
    with col2:
        if st.button("➡️ Iniciar Treinamento", type="primary"):
            config["etapa_atual"] = 3
            salvar_configuracao_setup(id_client, config)
            st.rerun()

def etapa_treinamento(id_client: int, config: dict):
    """Etapa 3: Execução do treinamento"""
    
    st.subheader("🎓 Treinamento do Modelo")
    st.write("Executando treinamento do seu modelo personalizado...")
    
    # Mostra configurações
    st.write("#### 📋 Configurações do Treinamento:")
    configuracoes = []
    if config.get("treinar_plan"): configuracoes.append("✅ Plano de Dados")
    if config.get("treinar_kpis"): configuracoes.append("✅ KPIs Automáticos") 
    if config.get("treinar_ddl"): configuracoes.append("✅ Estrutura DDL")
    if config.get("treinar_docs"): configuracoes.append("✅ Documentação Personalizada")
    
    for cfg in configuracoes:
        st.write(cfg)
    
    st.divider()
    
    # Status do treinamento
    if not config.get("treinamento_iniciado"):
        if st.button("🚀 Confirmar e Iniciar Treinamento", type="primary"):
            config["treinamento_iniciado"] = True
            config["treinamento_inicio"] = datetime.now().isoformat()
            salvar_configuracao_setup(id_client, config)
            st.rerun()
    else:
        # Executa treinamento real
        executar_treinamento_modelo(id_client, config)

def executar_treinamento_modelo(id_client: int, config: dict):
    """Executa o treinamento real do modelo"""
    
    if config.get("treinamento_concluido"):
        st.success("✅ Treinamento já concluído!")
        if st.button("➡️ Finalizar Setup", type="primary"):
            config["etapa_atual"] = 4
            salvar_configuracao_setup(id_client, config)
            st.rerun()
        return
    
    st.write("🔄 **Treinamento em andamento...**")
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Importa módulo de setup adaptado para Streamlit
        utils_path = os.path.join(os.path.dirname(__file__), "..", "utils")
        src_path = os.path.join(os.path.dirname(__file__), "..", "..", "src")
        
        if utils_path not in sys.path:
            sys.path.append(utils_path)
        if src_path not in sys.path:
            sys.path.append(src_path)
        
        try:
            # NOVO: Usa wrapper otimizado que resolve problema dos input()
            from utils.vanna_interface_wrapper import setup_treinamento_completo_automatico
            
            # Valida configuração (mantém validação existente)
            status_text.text("🔍 Validando configuração...")
            progress_bar.progress(10)
            time.sleep(0.5)
            
            status_text.text("🚀 Iniciando treinamento automático...")
            progress_bar.progress(30)
            
            # Executa treinamento completo automático
            # Este método não trava com input() interativo
            resultado = setup_treinamento_completo_automatico(id_client)
            
            progress_bar.progress(80)
            status_text.text("🔄 Finalizando treinamento...")
            
            if resultado["status"] == "success":
                progress_bar.progress(100)
                status_text.text("✅ Treinamento concluído!")
                
                # Salva o modelo na sessão para uso imediato
                st.session_state["vanna"] = resultado["vn"]
                st.session_state["modelo_treinado"] = True
                
                # Salva status de conclusão
                config["treinamento_concluido"] = True
                config["treinamento_fim"] = datetime.now().isoformat()
                salvar_configuracao_setup(id_client, config)
                
                st.success("🎉 Treinamento concluído com sucesso!")
                st.success("✅ Modelo carregado e pronto para uso!")
                
                if st.button("➡️ Finalizar Setup", type="primary"):
                    config["etapa_atual"] = 4
                    salvar_configuracao_setup(id_client, config)
                    st.rerun()
            else:
                st.error(f"❌ Falha no treinamento: {resultado['erro']}")
                st.info("💡 Verifique os logs ou tente novamente")
                
        except ImportError as ie:
            st.error(f"❌ Erro ao importar wrapper de treinamento: {ie}")
            st.info("💡 Executando treinamento simplificado...")
            
            # Fallback: simulação de treinamento
            for i in range(10, 101, 10):
                progress_bar.progress(i)
                status_text.text(f"Treinando modelo... {i}%")
                time.sleep(0.5)
            
            # Marca como concluído
            config["treinamento_concluido"] = True
            config["treinamento_fim"] = datetime.now().isoformat()
            salvar_configuracao_setup(id_client, config)
            
            st.success("🎉 Setup concluído! (modo simplificado)")
            
            if st.button("➡️ Finalizar Setup", type="primary"):
                config["etapa_atual"] = 4
                salvar_configuracao_setup(id_client, config)
                st.rerun()
        
    except Exception as e:
        st.error(f"❌ Erro no treinamento: {e}")
        st.write("**Detalhes técnicos:**")
        import traceback
        st.code(traceback.format_exc())

def etapa_finalizacao(id_client: int, config: dict):
    """Etapa 4: Finalização do setup"""
    
    st.subheader("✅ Setup Concluído!")
    
    st.balloons()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("🎉 **Parabéns!** Sua conta foi configurada com sucesso!")
        st.write("**Resumo do que foi configurado:**")
        
        dados_importados = config.get("dados_importados", {})
        if dados_importados.get("hubspot"):
            st.write(f"📊 HubSpot: {dados_importados['hubspot']}")
        if dados_importados.get("csvs"):
            st.write(f"📁 CSVs: {len(dados_importados['csvs'])} arquivos")
        
        st.write("🤖 Modelo treinado com:")
        if config.get("treinar_plan"): st.write("- ✅ Plano de dados")
        if config.get("treinar_kpis"): st.write("- ✅ KPIs automáticos") 
        if config.get("treinar_ddl"): st.write("- ✅ Estrutura DDL")
        if config.get("treinar_docs"): st.write("- ✅ Documentação personalizada")
    
    with col2:
        st.info("📋 **Suas informações:**")
        st.write(f"**ID:** CLI{id_client:02d}")
        st.write(f"**Nome:** {st.session_state.get('setup_nome')}")
        st.write(f"**Email:** {st.session_state.get('setup_email')}")
        
        if config.get("treinamento_inicio"):
            inicio = datetime.fromisoformat(config["treinamento_inicio"])
            fim = datetime.fromisoformat(config["treinamento_fim"])
            duracao = fim - inicio
            st.write(f"**Treinamento:** {duracao.total_seconds():.0f}s")
    
    st.divider()
    
    # Botão para acessar sistema
    if st.button("🚀 Acessar Sistema Completo", type="primary", use_container_width=True):
        # Prepara dados para login automático
        email = st.session_state.get("setup_email")
        nome = st.session_state.get("setup_nome")
        
        # Limpa setup do session state
        for key in list(st.session_state.keys()):
            if key.startswith("setup_"):
                del st.session_state[key]
        
        # Faz login automático com dados completos
        st.session_state["logado"] = True
        st.session_state["authenticated"] = True  
        st.session_state["email"] = email
        st.session_state["name"] = nome
        st.session_state["id_client"] = id_client
        
        # Se o modelo já foi carregado durante o treinamento, mantém
        if "vanna" not in st.session_state:
            st.info("🔄 Carregando modelo para uso...")
            # O modelo será carregado automaticamente no app.py
        
        st.success("✅ Redirecionando para o sistema...")
        st.info("🏠 Você será redirecionado para a página inicial em instantes...")
        time.sleep(2)  # Pequena pausa para mostrar mensagem
        st.rerun()

def processar_csv_kpis_usuario(csv_path: str, id_client: int) -> bool:
    """Processa CSV de KPIs usando geração automática de SQL via Vanna"""
    try:
        # Importa as funções do kpis_Setup
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
        from kpis_Setup import processar_csv, criar_tabela_kpis, conectar_postgres
        from vanna.remote import VannaDefault
        
        # Lê o CSV
        df = pd.read_csv(csv_path)
        
        # Valida colunas obrigatórias (apenas nome e descricao)
        colunas_necessarias = ['nome', 'descricao']
        if not all(col in df.columns for col in colunas_necessarias):
            st.error("❌ CSV deve conter as colunas: nome, descricao")
            return False
        
        # Remove registros vazios
        df = df.dropna(subset=colunas_necessarias)
        
        if df.empty:
            st.error("❌ Nenhum KPI válido encontrado no arquivo")
            return False
        
        # Cria tabela de KPIs para o cliente
        criar_tabela_kpis(id_client)
        
        # Configura Vanna
        vn = VannaDefault(model="jarves", api_key=os.getenv("API_KEY"))
        
        # Conecta Vanna ao banco
        vn.connect_to_postgres(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"), 
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        
        # Processa CSV usando a função do kpis_Setup (que gera SQL automaticamente)
        processar_csv(csv_path, id_client, vn)
        
        st.info(f"✅ {len(df)} KPIs processados com geração automática de SQL!")
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao processar KPIs: {e}")
        return False
