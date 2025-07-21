import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Any

class HubSpotIntegration:
    """Integração com HubSpot API para importação de dados por usuário"""
    
    def __init__(self, api_token: str = None):
        self.api_token = api_token or os.getenv("HUBSPOT_TOKEN")
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    def validar_token(self) -> bool:
        """Valida se o token está funcionando"""
        try:
            if not self.api_token:
                st.error("❌ Token HubSpot não encontrado. Verifique as variáveis de ambiente.")
                return False
                
            url = f"{self.base_url}/account-info/v3/details"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                account_info = response.json()
                st.info(f"🏢 Conta HubSpot: {account_info.get('companyName', 'N/A')}")
                return True
            elif response.status_code == 401:
                st.error("❌ Token HubSpot inválido ou expirado.")
                return False
            else:
                st.error(f"❌ Erro na validação do token: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            st.error("❌ Timeout na conexão com HubSpot.")
            return False
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erro de rede: {e}")
            return False
        except Exception as e:
            st.error(f"❌ Erro inesperado na validação: {e}")
            return False
    
    def obter_contatos(self, limit: int = 100) -> pd.DataFrame:
        """Obtém contatos do HubSpot em formato DataFrame"""
        try:
            # Garante que o limite não exceda 100 (limite da API)
            limit = min(limit, 100)
            st.info(f"🔄 Buscando até {limit} contatos no HubSpot...")
            
            url = f"{self.base_url}/crm/v3/objects/contacts"
            params = {
                "limit": limit,
                "properties": "firstname,lastname,email,phone,company,jobtitle,createdate,lastmodifieddate"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                total_results = len(data.get('results', []))
                
                st.info(f"📊 {total_results} contatos encontrados na API")
                
                if total_results == 0:
                    st.warning("⚠️ Nenhum contato encontrado na sua conta HubSpot.")
                    return pd.DataFrame()
                
                # Converte para DataFrame
                contatos = []
                for contact in data.get('results', []):
                    props = contact.get('properties', {})
                    contatos.append({
                        'id_hubspot': contact.get('id'),
                        'nome': f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                        'email': props.get('email'),
                        'telefone': props.get('phone'),
                        'empresa': props.get('company'),
                        'cargo': props.get('jobtitle'),
                        'data_criacao': props.get('createdate'),
                        'data_modificacao': props.get('lastmodifieddate'),
                        'importado_em': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                df = pd.DataFrame(contatos)
                st.success(f"✅ {len(df)} contatos processados com sucesso!")
                return df
                
            else:
                st.error(f"❌ Erro ao obter contatos: {response.status_code}")
                st.error(f"Resposta: {response.text[:200]}...")
                return pd.DataFrame()
                
        except requests.exceptions.Timeout:
            st.error("❌ Timeout na busca de contatos. Tente um limite menor.")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Erro na requisição de contatos: {e}")
            return pd.DataFrame()
    
    def obter_deals(self, limit: int = 100) -> pd.DataFrame:
        """Obtém deals (negócios) do HubSpot"""
        try:
            # Garante que o limite não exceda 100 (limite da API)
            limit = min(limit, 100)
            st.info(f"🔄 Buscando até {limit} deals no HubSpot...")
            
            url = f"{self.base_url}/crm/v3/objects/deals"
            params = {
                "limit": limit,
                "properties": "dealname,amount,dealstage,pipeline,closedate,createdate,hubspot_owner_id"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                total_results = len(data.get('results', []))
                
                st.info(f"📊 {total_results} deals encontrados na API")
                
                if total_results == 0:
                    st.warning("⚠️ Nenhum deal encontrado na sua conta HubSpot.")
                    return pd.DataFrame()
                
                deals = []
                for deal in data.get('results', []):
                    props = deal.get('properties', {})
                    deals.append({
                        'id_hubspot': deal.get('id'),
                        'nome_deal': props.get('dealname'),
                        'valor': props.get('amount'),
                        'estagio': props.get('dealstage'),
                        'pipeline': props.get('pipeline'),
                        'data_fechamento': props.get('closedate'),
                        'data_criacao': props.get('createdate'),
                        'proprietario_id': props.get('hubspot_owner_id'),
                        'importado_em': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                df = pd.DataFrame(deals)
                st.success(f"✅ {len(df)} deals processados com sucesso!")
                return df
                
            else:
                st.error(f"❌ Erro ao obter deals: {response.status_code}")
                st.error(f"Resposta: {response.text[:200]}...")
                return pd.DataFrame()
                
        except requests.exceptions.Timeout:
            st.error("❌ Timeout na busca de deals. Tente um limite menor.")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Erro na requisição de deals: {e}")
            return pd.DataFrame()
    
    def obter_empresas(self, limit: int = 100) -> pd.DataFrame:
        """Obtém empresas do HubSpot"""
        try:
            # Garante que o limite não exceda 100 (limite da API)
            limit = min(limit, 100)
            st.info(f"🔄 Buscando até {limit} empresas no HubSpot...")
            
            url = f"{self.base_url}/crm/v3/objects/companies"
            params = {
                "limit": limit,
                "properties": "name,domain,industry,city,state,country,phone,createdate"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                total_results = len(data.get('results', []))
                
                st.info(f"📊 {total_results} empresas encontradas na API")
                
                if total_results == 0:
                    st.warning("⚠️ Nenhuma empresa encontrada na sua conta HubSpot.")
                    return pd.DataFrame()
                
                empresas = []
                for company in data.get('results', []):
                    props = company.get('properties', {})
                    empresas.append({
                        'id_hubspot': company.get('id'),
                        'nome_empresa': props.get('name'),
                        'dominio': props.get('domain'),
                        'setor': props.get('industry'),
                        'cidade': props.get('city'),
                        'estado': props.get('state'),
                        'pais': props.get('country'),
                        'telefone': props.get('phone'),
                        'data_criacao': props.get('createdate'),
                        'importado_em': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                df = pd.DataFrame(empresas)
                st.success(f"✅ {len(df)} empresas processadas com sucesso!")
                return df
                
            else:
                st.error(f"❌ Erro ao obter empresas: {response.status_code}")
                st.error(f"Resposta: {response.text[:200]}...")
                return pd.DataFrame()
                
        except requests.exceptions.Timeout:
            st.error("❌ Timeout na busca de empresas. Tente um limite menor.")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Erro na requisição de empresas: {e}")
            return pd.DataFrame()

def salvar_dados_hubspot_usuario(df: pd.DataFrame, nome_tabela: str, id_client: int) -> bool:
    """Salva dados do HubSpot na tabela específica do usuário usando SQLAlchemy"""
    
    try:
        # Import usando caminho relativo correto
        from db_utils import criar_engine
        from sqlalchemy import text
        
        # CORREÇÃO: Validar id_client primeiro
        if not id_client or id_client <= 0:
            st.error(f"❌ ID do cliente inválido: {id_client}")
            return False
        
        # CORREÇÃO: Garantir que id_client seja int
        try:
            id_client = int(id_client)
        except (ValueError, TypeError):
            st.error(f"❌ ID do cliente não é um número válido: {id_client}")
            return False
        
        # Validação inicial
        if df.empty:
            st.warning("⚠️ Nenhum dado para salvar - DataFrame vazio.")
            return False
        
        # Nome da tabela com prefixo do cliente
        nome_tabela_final = f"cli{id_client:02d}_{nome_tabela}"
        
        # Debug detalhado
        st.info(f"🔧 **Debug do ID do Cliente:**")
        st.info(f"   • Cliente ID: {id_client} (tipo: {type(id_client)})")
        st.info(f"   • Nome tabela base: {nome_tabela}")
        st.info(f"   • Nome tabela final: `{nome_tabela_final}`")
        st.info(f"   • Registros para salvar: {len(df)}")
        
        # Cria engine SQLAlchemy
        engine = criar_engine()
        st.info("✅ Engine SQLAlchemy criada!")
        
        # Testa a conexão
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            st.info(f"✅ Conexão estabelecida: PostgreSQL {version.split()[1]}")
        
        # Salva o DataFrame no PostgreSQL usando SQLAlchemy
        st.info("💾 Iniciando salvamento...")
        
        df.to_sql(
            name=nome_tabela_final,
            con=engine,
            if_exists='replace',
            index=False,
            method='multi',  # Otimização para inserções em lote
            chunksize=1000   # Processa em chunks para DataFrames grandes
        )
        
        st.info("✅ Dados salvos com sucesso!")
        
        # Confirma o salvamento
        with engine.connect() as conn:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{nome_tabela_final}"'))
            count = result.fetchone()[0]
            st.success(f"✅ {count} registros confirmados na tabela: `{nome_tabela_final}`")
        
        # Dispose da engine para liberar recursos
        engine.dispose()
        
        return True
        
    except ImportError as e:
        st.error(f"❌ Erro no import de db_utils: {e}")
        return False
        
    except Exception as e:
        st.error(f"❌ Erro ao salvar dados no banco: {e}")
        
        # Debug adicional para troubleshooting
        import traceback
        error_details = traceback.format_exc()
        with st.expander("🔍 Detalhes técnicos do erro"):
            st.code(error_details)
        
        return False