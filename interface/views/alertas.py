# alertas.py – exibe alertas e notificações por metas

import streamlit as st
import pandas as pd
import os
import sys
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import contextlib

# Adicionar src ao path para importar funções
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from import_csv import conectar_banco

@contextlib.contextmanager
def get_db_connection():
    """Context manager para conexões de banco de dados"""
    conn = None
    try:
        conn = conectar_banco()
        yield conn
    except Exception as e:
        st.error(f"Erro de conexão com banco: {e}")
        yield None
    finally:
        if conn:
            conn.close()

def mostrar_alertas():
    st.title("🚨 Central de Alertas")
    st.write("Configure e monitore alertas para seus KPIs e métricas importantes.")
    
    # Verifica se usuário está logado
    if "logado" not in st.session_state or not st.session_state["logado"]:
        st.error("Você precisa estar logado para acessar os alertas.")
        return
    
    client_id = st.session_state.get("id_client")
    if not client_id:
        st.error("ID do cliente não encontrado. Faça login novamente.")
        return
        
    nome_usuario = st.session_state.get("name", "usuário")
    
    # Obter alertas para verificar status
    alertas_ativos = obter_alertas_usuario(client_id)
    alertas_disparados = []
    alertas_erro = []
    
    if alertas_ativos:
        alertas_status = verificar_todos_alertas(client_id, alertas_ativos)
        alertas_disparados = [a for a in alertas_status if a['status'] == 'DISPARADO']
        alertas_erro = [a for a in alertas_status if a['status'] == 'ERRO']
    
    # Banner de status dos alertas no topo
    if alertas_disparados or alertas_erro:
        col_banner1, col_banner2 = st.columns([3, 1])
        
        with col_banner1:
            if alertas_disparados:
                st.error(f"🚨 **{len(alertas_disparados)} alerta(s) disparado(s)!** Verifique o dashboard abaixo.")
            if alertas_erro:
                st.warning(f"⚠️ **{len(alertas_erro)} alerta(s) com erro.** Verifique as configurações.")
        
        with col_banner2:
            # Botão para verificar alertas manualmente
            if st.button("🔄 Atualizar Status", type="secondary"):
                st.rerun()
    else:
        st.success("✅ **Todos os alertas estão normais!**")
    
    # Tabs para organizar funcionalidades
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard de Alertas", "⚙️ Configurar Alertas", "🤖 Alertas com IA", "📋 Histórico"])
    
    with tab1:
        mostrar_dashboard_alertas(client_id)
    
    with tab2:
        configurar_alertas(client_id)
    
    with tab3:
        configurar_alertas_ia(client_id)
    
    with tab4:
        mostrar_historico_alertas(client_id)

def mostrar_dashboard_alertas(client_id: int):
    """Dashboard principal com status dos alertas"""
    st.subheader("📊 Status dos Alertas")
    
    alertas_ativos = obter_alertas_usuario(client_id)
    
    if not alertas_ativos:
        st.info("📝 Nenhum alerta configurado. Vá para a aba 'Configurar Alertas' para criar seu primeiro alerta!")
        return
    
    # Verifica status de cada alerta
    alertas_status = verificar_todos_alertas(client_id, alertas_ativos)
    
    # Métricas em cards
    col1, col2, col3, col4 = st.columns(4)
    
    total_alertas = len(alertas_status)
    alertas_disparados = sum(1 for a in alertas_status if a['status'] == 'DISPARADO')
    alertas_normais = sum(1 for a in alertas_status if a['status'] == 'NORMAL')
    alertas_erro = sum(1 for a in alertas_status if a['status'] == 'ERRO')
    
    with col1:
        st.metric("Total de Alertas", total_alertas)
    with col2:
        st.metric("🚨 Disparados", alertas_disparados, delta=f"{alertas_disparados} alertas")
    with col3:
        st.metric("✅ Normais", alertas_normais)
    with col4:
        st.metric("⚠️ Com Erro", alertas_erro)
    
    # Lista de alertas com status
    st.subheader("📋 Status Detalhado")
    
    for alerta in alertas_status:
        status_color = {
            'DISPARADO': '🔴',
            'NORMAL': '🟢', 
            'ERRO': '🟡'
        }.get(alerta['status'], '⚫')
        
        with st.expander(f"{status_color} {alerta['nome']} - {alerta['status']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Tipo:** {alerta['tipo']}")
                
                # Para alertas personalizados, mostra a descrição
                if alerta.get('tipo') == 'Personalizado IA':
                    st.write(f"**Descrição:** {alerta.get('descricao', 'N/A')}")
                    
                    # Mostra SQL personalizado sem expander aninhado
                    if alerta.get('sql_personalizado'):
                        st.write("**SQL Personalizado:**")
                        st.code(alerta['sql_personalizado'], language="sql")
                else:
                    # Alertas tradicionais
                    st.write(f"**Tabela:** {alerta.get('tabela', 'N/A')}")
                    st.write(f"**Coluna:** {alerta.get('coluna', 'N/A')}")
                
                st.write(f"**Condição:** {alerta['condicao']}")
                st.write(f"**Valor Limite:** {alerta['valor_limite']}")
            
            with col2:
                st.write(f"**Valor Atual:** {alerta.get('valor_atual', 'N/A')}")
                st.write(f"**Última Verificação:** {alerta.get('ultima_verificacao', 'N/A')}")
                
                # Status do alerta
                if alerta['status'] == 'DISPARADO':
                    st.error(f"🚨 **ALERTA DISPARADO!**")
                    if alerta.get('valor_atual') is not None and alerta.get('valor_limite') is not None:
                        st.error(f"Valor {alerta['valor_atual']} {alerta['condicao'].lower()} {alerta['valor_limite']}")
                elif alerta['status'] == 'ERRO':
                    st.warning(f"❌ **Erro ao verificar:**")
                    st.warning(alerta.get('erro', 'Erro desconhecido'))
                else:
                    st.success("✅ **Status Normal**")
                
                # Email configurado
                if alerta.get('email'):
                    st.info(f"📧 Notificações: {alerta['email']}")
            
            # Botões de ação
            st.divider()
            col_edit, col_delete, col_test = st.columns(3)
            
            with col_test:
                if st.button(f"🧪 Testar Agora", key=f"test_{alerta['id']}"):
                    testar_alerta_agora(alerta, client_id)
            
            with col_edit:
                if st.button(f"✏️ Editar", key=f"edit_{alerta['id']}"):
                    editar_alerta(alerta)
            
            with col_delete:
                if st.button(f"🗑️ Remover", key=f"del_{alerta['id']}"):
                    remover_alerta(alerta['id'], client_id)

def configurar_alertas(client_id: int):
    """Interface para configurar novos alertas"""
    st.subheader("⚙️ Configurar Novo Alerta")
    
    # Obter tabelas do usuário
    tabelas_usuario = obter_tabelas_usuario_alertas(client_id)
    
    if not tabelas_usuario:
        st.warning("Você precisa ter tabelas importadas para configurar alertas. Vá para Configurações → Upload CSV.")
        return
    
    with st.form("novo_alerta"):
        col1, col2 = st.columns(2)
        
        with col1:
            nome_alerta = st.text_input("Nome do Alerta", placeholder="Ex: Vendas Baixas")
            
            tipo_alerta = st.selectbox(
                "Tipo de Alerta",
                ["Valor Simples", "Agregação", "Crescimento %", "Comparação Período"]
            )
            
            tabela_selecionada = st.selectbox("Tabela", tabelas_usuario)
        
        with col2:
            if tabela_selecionada:
                colunas = obter_colunas_tabela(tabela_selecionada)
                coluna_selecionada = st.selectbox("Coluna", colunas)
                
                condicao = st.selectbox("Condição", ["Maior que", "Menor que", "Igual a", "Diferente de"])
                
                valor_limite = st.number_input("Valor Limite", value=0.0)
        
        # Configurações avançadas
        st.subheader("Configurações Avançadas")
        
        col3, col4 = st.columns(2)
        with col3:
            frequencia = st.selectbox("Frequência", ["Manual", "A cada 5 min", "Diário", "Semanal"])
            ativo = st.checkbox("Alerta Ativo", value=True)
        
        with col4:
            # Usa o email do login como padrão
            email_padrao = st.session_state.get("email", "")
            email_notificacao = st.text_input("Email para Notificação", value=email_padrao)
            incluir_grafico = st.checkbox("Incluir Gráfico nos Alertas")
        
        # Botão de salvar
        if st.form_submit_button("💾 Salvar Alerta", type="primary"):
            if nome_alerta and tabela_selecionada and coluna_selecionada:
                sucesso = salvar_alerta(client_id, {
                    'nome': nome_alerta,
                    'tipo': tipo_alerta,
                    'tabela': tabela_selecionada,
                    'coluna': coluna_selecionada,
                    'condicao': condicao,
                    'valor_limite': valor_limite,
                    'frequencia': frequencia,
                    'ativo': ativo,
                    'email': email_notificacao,
                    'incluir_grafico': incluir_grafico
                })
                
                if sucesso:
                    st.success("✅ Alerta configurado com sucesso!")
                    st.rerun()
            else:
                st.error("❌ Preencha todos os campos obrigatórios!")

def mostrar_historico_alertas(client_id: int):
    """Mostra histórico de alertas disparados"""
    st.subheader("📋 Histórico de Alertas")
    
    historico = obter_historico_alertas(client_id)
    
    if not historico:
        st.info("Nenhum histórico de alertas encontrado.")
        return
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        periodo = st.selectbox("Período", ["Últimos 7 dias", "Últimos 30 dias", "Todos"])
    with col2:
        status_filtro = st.selectbox("Status", ["Todos", "Disparados", "Resolvidos"])
    
    # Tabela de histórico
    df_historico = pd.DataFrame(historico)
    
    if not df_historico.empty:
        # Aplica filtros
        if periodo == "Últimos 7 dias":
            data_limite = datetime.now() - timedelta(days=7)
            df_historico = df_historico[pd.to_datetime(df_historico['data']) >= data_limite]
        elif periodo == "Últimos 30 dias":
            data_limite = datetime.now() - timedelta(days=30)
            df_historico = df_historico[pd.to_datetime(df_historico['data']) >= data_limite]
        
        if status_filtro != "Todos":
            df_historico = df_historico[df_historico['status'] == status_filtro.upper()]
        
        st.dataframe(
            df_historico,
            use_container_width=True,
            column_config={
                "data": st.column_config.DatetimeColumn("Data/Hora"),
                "status": st.column_config.TextColumn("Status"),
                "alerta": st.column_config.TextColumn("Alerta"),
                "valor": st.column_config.NumberColumn("Valor"),
                "limite": st.column_config.NumberColumn("Limite")
            }
        )
        
        # Gráfico de alertas por dia
        if len(df_historico) > 0:
            st.subheader("📈 Alertas por Dia")
            df_por_dia = df_historico.groupby(df_historico['data'].dt.date).size().reset_index()
            df_por_dia.columns = ['Data', 'Quantidade']
            
            fig = px.bar(df_por_dia, x='Data', y='Quantidade', title="Número de Alertas por Dia")
            st.plotly_chart(fig, use_container_width=True)

def configurar_alertas_ia(client_id: int):
    """Interface para configurar alertas usando linguagem natural com Vanna"""
    st.subheader("🤖 Configurar Alertas com IA")
    st.write("Descreva seu alerta em linguagem natural e a IA criará a consulta SQL automaticamente!")
    
    # Verifica se tem Vanna disponível
    if "vanna" not in st.session_state:
        st.error("⚠️ Modelo Vanna não está carregado. Faça login novamente.")
        return
    
    vn = st.session_state["vanna"]
    
    # Obter tabelas do usuário
    tabelas_usuario = obter_tabelas_usuario_alertas(client_id)
    
    if not tabelas_usuario:
        st.warning("Você precisa ter tabelas importadas para configurar alertas. Vá para Configurações → Upload CSV.")
        return
    
    # Mostra tabelas disponíveis
    with st.expander("📋 Suas Tabelas Disponíveis"):
        st.write("**Tabelas que você pode usar nos alertas:**")
        for tabela in tabelas_usuario:
            colunas = obter_colunas_tabela(tabela)
            st.write(f"• **{tabela}**: {', '.join(colunas[:5])}{'...' if len(colunas) > 5 else ''}")
    
    # Seção para descrição do alerta
    st.subheader("📝 Descrição do Alerta")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        descricao_temp = st.text_area(
            "Descreva seu alerta em linguagem natural",
            placeholder="Exemplos:\n• Alertar quando CTR for menor que 2%\n• Avisar se vendas do dia forem menos de 1000\n• Notificar quando gasto médio ultrapassar R$ 500\n• Alerta se conversões ficarem abaixo de 50 por semana",
            height=120,
            key="desc_temp"
        )
    
    with col2:
        st.info("💡 **Dicas para melhor resultado:**\n\n"
               "🎯 **Seja específico:**\n"
               "• Mencione a métrica exata (CTR, vendas, conversões)\n"
               "• Inclua o valor limite (ex: 2%, R$ 1000)\n"
               "• Use condições claras (menor que, maior que)\n\n"
               "📊 **Exemplos de métricas:**\n"
               "• Taxa de conversão, CTR, CPC\n"
               "• Vendas, receita, lucro\n"
               "• Número de cliques, impressões\n"
               "• Valores médios, totais, contagens")
    
    # Botão para gerar SQL
    if st.button("🔮 Gerar SQL com IA", type="secondary", disabled=not descricao_temp):
        if descricao_temp:
            with st.spinner("🤖 A IA está analisando sua descrição e gerando o SQL..."):
                sql_gerado, explicacao = gerar_sql_alerta_ia(vn, descricao_temp, tabelas_usuario)
                
                if sql_gerado:
                    st.session_state["sql_alerta_gerado"] = sql_gerado
                    st.session_state["descricao_alerta"] = descricao_temp
                    st.session_state["explicacao_sql"] = explicacao
                    st.rerun()
                else:
                    st.error("❌ Não foi possível gerar SQL. Tente reformular a descrição ou verificar se mencionou tabelas/colunas corretas.")

# Funções auxiliares

def obter_alertas_usuario(client_id: int) -> list:
    """Carrega alertas salvos do usuário"""
    try:
        alertas_path = f"/home/lanna/Estudos/2025-1/Soliris/interface/hist_alerta/alertas_cli{client_id:02d}.json"
        if os.path.exists(alertas_path):
            with open(alertas_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        st.error(f"Erro ao carregar alertas: {e}")
        return []

def validar_sql_seguro(sql: str) -> bool:
    """Valida se o SQL é seguro para execução (apenas SELECT)"""
    sql_upper = sql.upper().strip()
    
    # Lista de comandos perigosos
    comandos_proibidos = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 
        'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE'
    ]
    
    # Verifica se contém apenas SELECT
    if not sql_upper.startswith('SELECT'):
        return False
    
    # Verifica se contém comandos perigosos
    for comando in comandos_proibidos:
        if comando in sql_upper:
            return False
    
    return True

def salvar_alerta(client_id: int, alerta_config: dict):
    """Salva um novo alerta com validações"""
    try:
        # Validações básicas
        campos_obrigatorios = ['nome', 'tipo', 'tabela', 'coluna', 'condicao', 'valor_limite']
        for campo in campos_obrigatorios:
            if not alerta_config.get(campo):
                st.error(f"❌ Campo obrigatório '{campo}' não preenchido!")
                return False
        
        # Valida valor limite
        try:
            float(alerta_config['valor_limite'])
        except (ValueError, TypeError):
            st.error("❌ Valor limite deve ser numérico!")
            return False
        
        alertas = obter_alertas_usuario(client_id)
        
        # Verifica se nome já existe
        nomes_existentes = [a.get('nome', '').lower() for a in alertas]
        if alerta_config['nome'].lower() in nomes_existentes:
            st.error("❌ Já existe um alerta com este nome!")
            return False
        
        # Adiciona ID único e timestamp
        alerta_config['id'] = len(alertas) + 1
        alerta_config['criado_em'] = datetime.now().isoformat()
        alerta_config['ativo'] = alerta_config.get('ativo', True)
        
        alertas.append(alerta_config)
        
        # Salva arquivo
        os.makedirs("/home/lanna/Estudos/2025-1/Soliris/interface/hist_alerta", exist_ok=True)
        alertas_path = f"/home/lanna/Estudos/2025-1/Soliris/interface/hist_alerta/alertas_cli{client_id:02d}.json"
        
        with open(alertas_path, 'w', encoding='utf-8') as f:
            json.dump(alertas, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        st.error(f"Erro ao salvar alerta: {e}")
        return False

def verificar_todos_alertas(client_id: int, alertas: list) -> list:
    """Verifica status de todos os alertas"""
    resultado = []
    
    for alerta in alertas:
        if not alerta.get('ativo', True):
            continue
            
        try:
            valor_atual = executar_query_alerta(alerta)
            status = avaliar_condicao_alerta(valor_atual, alerta)
            
            # Salva no histórico se alerta foi disparado
            if status == 'DISPARADO':
                salvar_historico_alerta(client_id, alerta, status, valor_atual)
            
            resultado.append({
                **alerta,
                'valor_atual': valor_atual,
                'status': status,
                'ultima_verificacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
        except Exception as e:
            resultado.append({
                **alerta,
                'status': 'ERRO',
                'erro': str(e),
                'ultima_verificacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    
    return resultado

def executar_query_alerta(alerta: dict):
    """Executa query para obter valor atual do alerta"""
    with get_db_connection() as conn:
        if not conn:
            raise Exception("Falha na conexão com banco de dados")
            
        cursor = conn.cursor()
        
        try:
            # Verifica se é um alerta personalizado (gerado por IA)
            if alerta.get('tipo') == 'Personalizado IA' and 'sql_personalizado' in alerta:
                query = alerta['sql_personalizado']
            else:
                # Alertas tradicionais
                tabela = alerta['tabela']
                coluna = alerta['coluna']
                tipo = alerta['tipo']
                
                if tipo == "Valor Simples":
                    query = f'SELECT "{coluna}" FROM "{tabela}" ORDER BY "id" DESC LIMIT 1'
                elif tipo == "Agregação":
                    query = f'SELECT COUNT("{coluna}") FROM "{tabela}"'
                else:  # Outros tipos
                    query = f'SELECT AVG("{coluna}") FROM "{tabela}"'
            
            cursor.execute(query)
            resultado = cursor.fetchone()
            
            # Converte Decimal para float se necessário
            if resultado:
                valor = resultado[0]
                if hasattr(valor, '__float__'):  # Se é um tipo numérico (incluindo Decimal)
                    return float(valor)
                return valor
            return 0
            
        finally:
            cursor.close()

def avaliar_condicao_alerta(valor_atual, alerta: dict) -> str:
    """Avalia se a condição do alerta foi atendida"""
    valor_limite = alerta['valor_limite']
    condicao = alerta['condicao']
    
    if condicao == "Maior que" and valor_atual > valor_limite:
        return "DISPARADO"
    elif condicao == "Menor que" and valor_atual < valor_limite:
        return "DISPARADO"
    elif condicao == "Igual a" and valor_atual == valor_limite:
        return "DISPARADO"
    elif condicao == "Diferente de" and valor_atual != valor_limite:
        return "DISPARADO"
    else:
        return "NORMAL"

def obter_tabelas_usuario_alertas(client_id: int) -> list:
    """Obtém lista de tabelas do usuário para alertas"""
    with get_db_connection() as conn:
        if not conn:
            return []
            
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE %s
                ORDER BY table_name
            """, (f"cli{client_id:02d}_%",))
            
            tabelas = [row[0] for row in cursor.fetchall()]
            return tabelas
            
        except Exception as e:
            st.error(f"Erro ao obter tabelas: {e}")
            return []
        finally:
            cursor.close()

def obter_colunas_tabela(nome_tabela: str) -> list:
    """Obtém colunas de uma tabela específica"""
    with get_db_connection() as conn:
        if not conn:
            return []
            
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns 
                WHERE table_name = %s
                AND table_schema = 'public'
                ORDER BY ordinal_position
            """, (nome_tabela,))
            
            colunas = [row[0] for row in cursor.fetchall()]
            return colunas
            
        except Exception as e:
            st.error(f"Erro ao obter colunas: {e}")
            return []
        finally:
            cursor.close()

def obter_historico_alertas(client_id: int) -> list:
    """Obtém histórico de alertas disparados"""
    try:
        historico_path = f"/home/lanna/Estudos/2025-1/Soliris/interface/hist_alerta/historico_alertas_cli{client_id:02d}.json"
        if os.path.exists(historico_path):
            with open(historico_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        return []

def salvar_historico_alerta(client_id: int, alerta: dict, status: str, valor_atual=None):
    """Salva entrada no histórico de alertas"""
    try:
        historico = obter_historico_alertas(client_id)
        
        entrada = {
            'id': len(historico) + 1,
            'data': datetime.now().isoformat(),
            'alerta': alerta['nome'],
            'status': status,
            'valor': valor_atual,
            'limite': alerta['valor_limite'],
            'condicao': alerta['condicao'],
            'tipo': alerta.get('tipo', 'N/A')
        }
        
        historico.append(entrada)
        
        # Mantém apenas os últimos 1000 registros
        if len(historico) > 1000:
            historico = historico[-1000:]
        
        # Salva histórico
        os.makedirs("/home/lanna/Estudos/2025-1/Soliris/interface/hist_alerta", exist_ok=True)
        historico_path = f"/home/lanna/Estudos/2025-1/Soliris/interface/hist_alerta/historico_alertas_cli{client_id:02d}.json"
        
        with open(historico_path, 'w', encoding='utf-8') as f:
            json.dump(historico, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        print(f"Erro ao salvar histórico de alerta: {e}")
        return False

def editar_alerta(alerta: dict):
    """Função para editar um alerta existente"""
    st.info("🔧 Funcionalidade de edição será implementada em breve!")

def remover_alerta(alerta_id: int, client_id: int):
    """Remove um alerta"""
    try:
        alertas = obter_alertas_usuario(client_id)
        alertas = [a for a in alertas if a.get('id') != alerta_id]
        
        alertas_path = f"/home/lanna/Estudos/2025-1/Soliris/interface/hist_alerta/alertas_cli{client_id:02d}.json"
        with open(alertas_path, 'w', encoding='utf-8') as f:
            json.dump(alertas, f, indent=2, ensure_ascii=False)
        
        st.success("✅ Alerta removido com sucesso!")
        st.rerun()
        
    except Exception as e:
        st.error(f"Erro ao remover alerta: {e}")

def testar_alerta_agora(alerta: dict, client_id: int):
    """Testa um alerta específico imediatamente"""
    try:
        with st.spinner(f"Testando alerta '{alerta['nome']}'..."):
            valor_atual = executar_query_alerta(alerta)
            status = avaliar_condicao_alerta(valor_atual, alerta)
            
            st.success(f"✅ **Teste concluído!**")
            st.info(f"**Valor atual:** {valor_atual}")
            st.info(f"**Status:** {status}")
            
            if status == 'DISPARADO':
                st.warning("🚨 **Este alerta DISPARARIA agora!**")
            else:
                st.success("✅ **Alerta está NORMAL**")
                
    except Exception as e:
        st.error(f"Erro ao testar alerta: {e}")

def gerar_sql_alerta_ia(vn, descricao: str, tabelas_disponiveis: list) -> tuple:
    """Gera SQL usando Vanna baseado na descrição em linguagem natural"""
    try:
        # Obter informações detalhadas das tabelas
        info_tabelas = []
        for tabela in tabelas_disponiveis:
            colunas = obter_colunas_tabela(tabela)
            info_tabelas.append(f"Tabela {tabela}: colunas disponíveis: {', '.join(colunas)}")
        
        contexto_tabelas = "\n".join(info_tabelas)
        
        # Monta um prompt mais detalhado e específico
        prompt_completo = f"""
        CONTEXTO DO BANCO DE DADOS:
        {contexto_tabelas}
        
        REQUISITO DO USUÁRIO:
        {descricao}
        
        INSTRUÇÕES:
        - Gere apenas uma consulta SQL que retorne UM ÚNICO VALOR NUMÉRICO
        - Use as tabelas e colunas mencionadas acima
        - A consulta deve ser otimizada para monitoramento de alertas
        - Se a descrição mencionar "CTR", calcule como cliques/impressões * 100
        - Se mencionar "taxa de conversão", calcule como conversões/visitantes * 100
        - Se mencionar "média", "total", "contagem", use as funções SQL apropriadas
        - Para valores de "hoje" ou "dia atual", use condições de data quando aplicável
        - Para "semana" ou "mês", agrupe adequadamente os dados
        
        GERE APENAS O SQL, SEM EXPLICAÇÕES ADICIONAIS:
        """
        
        # Gera SQL usando Vanna
        sql_gerado = vn.generate_sql(prompt_completo)
        
        # Limpa o SQL (remove explicações extras se houver)
        sql_limpo = extrair_sql_limpo(sql_gerado)
        
        # Gera explicação baseada na descrição
        explicacao = f"Esta consulta analisa: {descricao}\n\nTabelas utilizadas: {', '.join(tabelas_disponiveis)}"
        
        return sql_limpo, explicacao
        
    except Exception as e:
        st.error(f"Erro ao gerar SQL: {e}")
        return None, None

def extrair_sql_limpo(sql_bruto: str) -> str:
    """Extrai apenas o SQL válido, removendo comentários e explicações"""
    linhas = sql_bruto.split('\n')
    sql_lines = []
    
    for linha in linhas:
        linha = linha.strip()
        # Pula linhas vazias e comentários
        if linha and not linha.startswith('--') and not linha.startswith('#'):
            sql_lines.append(linha)
    
    sql_limpo = ' '.join(sql_lines)
    
    # Remove possíveis explicações em texto
    if 'SELECT' in sql_limpo.upper():
        # Procura o primeiro SELECT e pega dali em diante
        inicio = sql_limpo.upper().find('SELECT')
        sql_limpo = sql_limpo[inicio:]
    
    return sql_limpo.strip()
