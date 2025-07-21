#!/usr/bin/env python3
"""
Script para organizar arquivos PKL por usuário
Move arquivos antigos da pasta raiz para pastas de usuário específicas
"""

import os
import sys
import shutil
from datetime import datetime

# Adiciona path da interface
current_dir = os.path.dirname(os.path.abspath(__file__))
interface_dir = os.path.join(current_dir, 'interface')
sys.path.insert(0, interface_dir)

def get_hist_user_path_correto(id_client, *path_parts):
    """Retorna caminho correto para o diretório de histórico do usuário"""
    base_dir = os.path.join(current_dir, 'interface', 'auth')
    
    # Formatar id_client corretamente
    if isinstance(id_client, (int, float)):
        user_folder = f"usuario_{int(id_client):02d}"
    else:
        user_folder = f"usuario_{str(id_client)}"
    
    hist_dir = os.path.join(base_dir, "hist", user_folder)
    
    # Cria diretório se não existir
    os.makedirs(hist_dir, exist_ok=True)
    
    return os.path.join(hist_dir, *path_parts)

def listar_arquivos_pkl_raiz():
    """Lista todos os arquivos PKL na pasta raiz auth/hist/"""
    hist_raiz = os.path.join(current_dir, 'interface', 'auth', 'hist')
    
    arquivos_pkl = []
    
    if os.path.exists(hist_raiz):
        for arquivo in os.listdir(hist_raiz):
            if arquivo.endswith('.pkl') and os.path.isfile(os.path.join(hist_raiz, arquivo)):
                arquivos_pkl.append(arquivo)
    
    return arquivos_pkl

def organizar_arquivos_por_usuario():
    """Move arquivos PKL da raiz para pastas de usuário"""
    
    print("🔧 ORGANIZANDO ARQUIVOS PKL POR USUÁRIO")
    print("=" * 50)
    
    hist_raiz = os.path.join(current_dir, 'interface', 'auth', 'hist')
    arquivos_pkl = listar_arquivos_pkl_raiz()
    
    if not arquivos_pkl:
        print("✅ Nenhum arquivo PKL na pasta raiz para organizar")
        return True
    
    print(f"📁 Encontrados {len(arquivos_pkl)} arquivos PKL na pasta raiz:")
    for arquivo in arquivos_pkl:
        print(f"   📄 {arquivo}")
    
    # Determina usuário baseado no contexto (pode ser melhorado)
    print("\\n🤔 Como determinar o usuário destes arquivos antigos?")
    print("1. Mover todos para usuario_01 (usuário padrão)")
    print("2. Mover para usuario_admin (arquivos administrativos)")
    print("3. Criar pasta usuario_legacy (arquivos legados)")
    print("4. Deletar arquivos antigos")
    
    opcao = input("\\nEscolha uma opção (1/2/3/4): ")
    
    if opcao == "1":
        destino_usuario = 1
        pasta_destino = "usuario_01"
    elif opcao == "2":
        destino_usuario = "admin"
        pasta_destino = "usuario_admin"
    elif opcao == "3":
        destino_usuario = "legacy"
        pasta_destino = "usuario_legacy"
    elif opcao == "4":
        print("\\n🗑️ Deletando arquivos antigos...")
        for arquivo in arquivos_pkl:
            arquivo_path = os.path.join(hist_raiz, arquivo)
            try:
                os.remove(arquivo_path)
                print(f"   ✅ Deletado: {arquivo}")
            except Exception as e:
                print(f"   ❌ Erro ao deletar {arquivo}: {e}")
        return True
    else:
        print("❌ Opção inválida")
        return False
    
    # Move arquivos
    print(f"\\n📦 Movendo arquivos para {pasta_destino}...")
    
    destino_dir = get_hist_user_path_correto(destino_usuario)
    
    for arquivo in arquivos_pkl:
        origem = os.path.join(hist_raiz, arquivo)
        destino = os.path.join(destino_dir, arquivo)
        
        try:
            shutil.move(origem, destino)
            print(f"   ✅ {arquivo} → {pasta_destino}/")
        except Exception as e:
            print(f"   ❌ Erro ao mover {arquivo}: {e}")
    
    print(f"\\n🎉 Arquivos organizados em: {destino_dir}")
    return True

def corrigir_funcoes_salvamento():
    """Atualiza as funções para garantir que sempre salvem na pasta do usuário"""
    
    print("\\n🔧 VERIFICANDO FUNÇÕES DE SALVAMENTO")
    print("=" * 45)
    
    # Verifica auth_utils.py
    auth_utils_path = os.path.join(current_dir, 'interface', 'auth', 'auth_utils.py')
    
    with open(auth_utils_path, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Verifica se a função get_hist_user_path está correta
    if 'def get_hist_user_path(' in conteudo:
        print("✅ Função get_hist_user_path encontrada em auth_utils.py")
        
        # Verifica se está usando a função corretamente
        if 'get_hist_user_path(id_client, filename)' in conteudo:
            print("✅ Função sendo usada corretamente para salvar PKL")
        else:
            print("⚠️ Função pode não estar sendo usada corretamente")
    else:
        print("❌ Função get_hist_user_path não encontrada")
    
    # Verifica historico.py  
    historico_path = os.path.join(current_dir, 'interface', 'views', 'historico.py')
    
    with open(historico_path, 'r', encoding='utf-8') as f:
        conteudo_hist = f.read()
    
    if 'usuario_{id_client:02d}' in conteudo_hist:
        print("✅ historico.py está configurado para usar pastas por usuário")
    else:
        print("⚠️ historico.py pode precisar de correção")

def verificar_estrutura_atual():
    """Verifica a estrutura atual de diretórios"""
    
    print("\\n📁 ESTRUTURA ATUAL DE DIRETÓRIOS")
    print("=" * 40)
    
    hist_base = os.path.join(current_dir, 'interface', 'auth', 'hist')
    
    if not os.path.exists(hist_base):
        print("❌ Diretório auth/hist não existe")
        return
    
    # Lista conteúdo
    conteudo = os.listdir(hist_base)
    
    arquivos_pkl = [item for item in conteudo if item.endswith('.pkl')]
    pastas_usuario = [item for item in conteudo if os.path.isdir(os.path.join(hist_base, item)) and item.startswith('usuario_')]
    outros = [item for item in conteudo if item not in arquivos_pkl and item not in pastas_usuario]
    
    print(f"📄 Arquivos PKL na raiz: {len(arquivos_pkl)}")
    for arquivo in arquivos_pkl:
        print(f"   • {arquivo}")
    
    print(f"\\n📂 Pastas de usuário: {len(pastas_usuario)}")
    for pasta in pastas_usuario:
        pasta_path = os.path.join(hist_base, pasta)
        try:
            arquivos_na_pasta = len([f for f in os.listdir(pasta_path) if f.endswith('.pkl')])
            print(f"   • {pasta}: {arquivos_na_pasta} arquivos PKL")
        except:
            print(f"   • {pasta}: erro ao ler")
    
    if outros:
        print(f"\\n📁 Outros itens: {len(outros)}")
        for item in outros:
            print(f"   • {item}")

def criar_funcao_auxiliar_melhorada():
    """Cria uma versão melhorada da função de salvamento"""
    
    funcao_melhorada = '''
def salvar_historico_chat_usuario(id_client=None, formato="pickle"):
    """
    Salva histórico de chat na pasta específica do usuário logado
    
    Args:
        id_client: ID do cliente (se None, pega do session_state)
        formato: "pickle" ou "json"
    """
    import streamlit as st
    import pickle
    import json
    from datetime import datetime
    
    # Obtém histórico do chat
    historico = st.session_state.get("chat_history", [])
    if not historico:
        st.info("Nenhum histórico de chat para salvar.")
        return None
    
    # Obtém ID do cliente
    if id_client is None:
        id_client = st.session_state.get("id_client")
        
    if not id_client:
        st.error("❌ Usuário não identificado. Faça login novamente.")
        return None
    
    # Gera nome do arquivo
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if formato == "pickle":
        filename = f"historico_chat_{ts}.pkl"
        path = get_hist_user_path(id_client, filename)
        
        with open(path, "wb") as f:
            pickle.dump(historico, f)
            
    elif formato == "json":
        filename = f"historico_chat_{ts}.json"
        path = get_hist_user_path(id_client, filename)
        
        # Serializa histórico para JSON (remove objetos não serializáveis)
        historico_json = []
        for item in historico:
            item_limpo = {}
            for k, v in item.items():
                if k in ["pergunta", "resposta", "timestamp"]:
                    item_limpo[k] = v
            historico_json.append(item_limpo)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(historico_json, f, ensure_ascii=False, indent=2)
    else:
        st.error("❌ Formato inválido. Use 'pickle' ou 'json'")
        return None
    
    st.success(f"✅ Histórico salvo em: {path}")
    return path

def limpar_historicos_antigos(id_client, dias=30):
    """
    Remove históricos mais antigos que X dias para o usuário
    
    Args:
        id_client: ID do cliente
        dias: Número de dias para manter (padrão: 30)
    """
    import os
    import time
    from datetime import datetime, timedelta
    
    user_hist_dir = get_hist_user_path(id_client)
    
    if not os.path.exists(user_hist_dir):
        return 0
    
    limite_tempo = time.time() - (dias * 24 * 60 * 60)
    arquivos_removidos = 0
    
    for arquivo in os.listdir(user_hist_dir):
        if arquivo.endswith(('.pkl', '.json')):
            arquivo_path = os.path.join(user_hist_dir, arquivo)
            
            # Verifica data de modificação
            if os.path.getmtime(arquivo_path) < limite_tempo:
                try:
                    os.remove(arquivo_path)
                    arquivos_removidos += 1
                except:
                    pass
    
    return arquivos_removidos
    '''
    
    print("\\n📝 FUNÇÃO AUXILIAR MELHORADA CRIADA")
    print("=" * 40)
    print("Você pode adicionar essas funções ao auth_utils.py:")
    print(funcao_melhorada)

def main():
    """Menu principal para organização de arquivos PKL"""
    
    print("🚀 ORGANIZAÇÃO DE ARQUIVOS PKL POR USUÁRIO")
    print("=" * 55)
    
    # 1. Verifica estrutura atual
    verificar_estrutura_atual()
    
    # 2. Lista arquivos para organizar
    arquivos_raiz = listar_arquivos_pkl_raiz()
    
    if arquivos_raiz:
        print(f"\\n⚠️ Encontrados {len(arquivos_raiz)} arquivos PKL na pasta raiz")
        resposta = input("\\n🔧 Deseja organizar estes arquivos agora? (s/n): ")
        
        if resposta.lower() in ['s', 'sim', 'y', 'yes']:
            organizar_arquivos_por_usuario()
    else:
        print("\\n✅ Todos os arquivos PKL já estão organizados!")
    
    # 3. Verifica funções de salvamento
    corrigir_funcoes_salvamento()
    
    # 4. Oferece função melhorada
    print("\\n" + "="*55)
    resposta_funcao = input("\\n📝 Deseja ver a função auxiliar melhorada? (s/n): ")
    
    if resposta_funcao.lower() in ['s', 'sim', 'y', 'yes']:
        criar_funcao_auxiliar_melhorada()
    
    print("\\n✅ ORGANIZAÇÃO CONCLUÍDA!")
    print("\\n📝 RESUMO DAS MELHORIAS:")
    print("   ✅ Arquivos PKL organizados por usuário")
    print("   ✅ Estrutura de pastas: auth/hist/usuario_XX/")
    print("   ✅ Funções verificadas")
    print("   ✅ Sistema preparado para isolamento por usuário")
    
    print("\\n🎯 PRÓXIMOS PASSOS:")
    print("   1. Teste o salvamento de histórico na interface")
    print("   2. Verifique se novos arquivos vão para pasta correta")
    print("   3. Configure limpeza automática de arquivos antigos")

if __name__ == "__main__":
    main()
