import os
import requests
from dotenv import load_dotenv

load_dotenv()

from vanna.remote import VannaDefault

vn = VannaDefault(model="jarves", api_key=os.getenv("API_KEY"))
endpoint = vn._endpoint
print("Endpoint Vanna:", endpoint)

headers = {
    "Authorization": f"Bearer {os.getenv('API_KEY')}",
    "Content-Type": "application/json"
}

payload = {
    "method": "ask",
    "params": {
        "question": "Qual o maior faturamento?",
        "model": "jarves"
    }
}

try:
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=10)
    print("Status:", resp.status_code)
    print("Resposta:", resp.text)
except Exception as e:
    print("Erro ao conectar:", e)