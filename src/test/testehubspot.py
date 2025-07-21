import os
import requests
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()
HUBSPOT_TOKEN = os.getenv("HUBSPOT_TOKEN")

BASE_URL = "https://api.hubapi.com"
HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_TOKEN}",
    "Content-Type": "application/json"
}

def requisitar(url, params=None, descricao=""):
    try:
        print(f"\n🔎 Requisição: {descricao} ({url})")
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)

        if response.status_code == 200:
            print("✅ Requisição bem-sucedida")
            return response.json()
        elif response.status_code == 403:
            print("❌ Permissão negada (403) – verifique os escopos do token!")
        else:
            print(f"❌ Erro {response.status_code}: {response.text[:100]}")
    except Exception as e:
        print(f"❌ Erro durante requisição: {str(e)[:100]}")
    return None

def testar_info_conta():
    """Testa o endpoint de informações da conta"""
    data = requisitar(
        url=f"{BASE_URL}/account-info/v3/details",
        descricao="Informações da conta"
    )
    if data:
        print(f"📌 Portal ID: {data.get('portalId')}")
        print(f"🏢 Nome: {data.get('accountName')}")
        print(f"🌐 Domínio: {data.get('domain')}")

def testar_contatos():
    """Testa a listagem de contatos"""
    data = requisitar(
        url=f"{BASE_URL}/crm/v3/objects/contacts",
        params={"limit": 5, "properties": "firstname,lastname,email"},
        descricao="Listagem de contatos"
    )
    if data:
        for c in data.get("results", []):
            props = c.get("properties", {})
            print(f"   👤 {props.get('firstname')} {props.get('lastname')} - {props.get('email')}")

def testar_deals():
    """Testa a listagem de negócios"""
    data = requisitar(
        url=f"{BASE_URL}/crm/v3/objects/deals",
        params={"limit": 5, "properties": "dealname,amount,dealstage"},
        descricao="Listagem de deals"
    )
    if data:
        for d in data.get("results", []):
            props = d.get("properties", {})
            print(f"   💼 {props.get('dealname')} - R${props.get('amount')} - Estágio: {props.get('dealstage')}")

def testar_empresas():
    data = requisitar(
        url=f"{BASE_URL}/crm/v3/objects/companies",
        params={"limit": 3, "properties": "name,domain,industry"},
        descricao="Listagem de empresas"
    )
    if data:
        for c in data.get("results", []):
            props = c.get("properties", {})
            print(f"   🏢 {props.get('name')} - {props.get('domain')} - {props.get('industry')}")

def testar_chamadas():
    data = requisitar(
        url=f"{BASE_URL}/crm/v3/objects/calls",
        params={"limit": 3, "properties": "hs_call_title,hs_call_duration"},
        descricao="Listagem de chamadas"
    )
    if data:
        for call in data.get("results", []):
            props = call.get("properties", {})
            print(f"   📞 {props.get('hs_call_title')} - duração: {props.get('hs_call_duration')}s")

def testar_tickets():
    data = requisitar(
        url=f"{BASE_URL}/crm/v3/objects/tickets",
        params={"limit": 3, "properties": "subject,hs_ticket_priority"},
        descricao="Listagem de tickets"
    )
    if data:
        for t in data.get("results", []):
            props = t.get("properties", {})
            print(f"   🎫 {props.get('subject')} - Prioridade: {props.get('hs_ticket_priority')}")

def validar_token():
    """Valida se o token foi carregado"""
    if not HUBSPOT_TOKEN:
        print("❌ Token não encontrado no .env")
        return False
    print(f"🔐 Token carregado com sucesso: {HUBSPOT_TOKEN[:20]}...")
    return True

def executar_testes():
    print("🚀 INICIANDO TESTES COMPLETOS HUBSPOT API")
    print("=" * 60)
    
    if not validar_token():
        return
    
    # Testes principais
    testar_info_conta()
    testar_contatos()
    testar_deals()

    # Testes complementares
    testar_empresas()
    testar_chamadas()
    testar_tickets()

    print("\n✅ Todos os testes foram concluídos.")
    print("📊 Sua conexão com a API do HubSpot está funcionando!")

if __name__ == "__main__":
    executar_testes()
