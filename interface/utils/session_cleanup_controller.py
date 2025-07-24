#!/usr/bin/env python3
"""
Sistema de controle de sessão otimizado - apenas para interface
Evita repetições desnecessárias de salvamento e limpeza
"""

import streamlit as st
import time
import threading
from datetime import datetime

class SessionCleanupController:
    """Controlador único para salvamento e limpeza por sessão"""
    
    def __init__(self):
        self.cleanup_executed = False
        self.user_id = None
        self.is_monitoring = False
    
    def should_execute_cleanup(self, current_user_id):
        """Verifica se deve executar cleanup para este usuário"""
        
        # Se mudou de usuário, resetar controle
        if self.user_id != current_user_id:
            self.cleanup_executed = False
            self.user_id = current_user_id
            
        return not self.cleanup_executed
    
    def execute_session_cleanup(self, force=False):
        """
        Executa salvamento + limpeza filtrada UMA ÚNICA VEZ por sessão
        
        Args:
            force: Se True, força execução mesmo se já foi feita
        """
        
        current_user = st.session_state.get("id_client")
        
        if not current_user:
            print("⚠️ [CLEANUP] Nenhum usuário identificado")
            return False
            
        # Verifica se já foi executado para este usuário
        if not force and not self.should_execute_cleanup(current_user):
            print(f"✅ [CLEANUP] Já executado para usuário {current_user}")
            return True
            
        print(f"🔄 [CLEANUP] Iniciando para usuário {current_user}")
        
        try:
            # SOLUÇÃO CORRETA: limpar_data_training já faz salvamento + limpeza
            success = self._smart_cleanup(current_user)
            
            if success:
                self.cleanup_executed = True
                print(f"✅ [CLEANUP] Concluído para usuário {current_user}")
                return True
            else:
                print(f"❌ [CLEANUP] Falha para usuário {current_user}")
                return False
                
        except Exception as e:
            print(f"❌ [CLEANUP] Erro: {e}")
            return False
    
    def _smart_cleanup(self, user_id):
        """
        Limpeza inteligente que usa DatabaseManager para persistência PostgreSQL
        """
        try:
            if not hasattr(st.session_state, 'vanna') or not st.session_state.vanna:
                print("⚠️ [SMART_CLEAN] Vanna não disponível")
                return True
                
            # Configura path para vanna_core e database_manager
            import sys
            import os
            src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
            if src_path not in sys.path:
                sys.path.append(src_path)
                
            try:
                from database_manager import db_manager
                print("✅ [SMART_CLEAN] DatabaseManager importado com sucesso")
                use_db_manager = True
            except ImportError as e:
                print(f"⚠️ [SMART_CLEAN] DatabaseManager não disponível: {e}")
                use_db_manager = False
                
            vanna = st.session_state.vanna
            
            print(f"🧠 [SMART_CLEAN] Executando limpeza inteligente para usuário {user_id}")
            
            if use_db_manager:
                print("�️ [SMART_CLEAN] Usando DatabaseManager (PostgreSQL):")
                print("   1. Obtém dados atuais do modelo Vanna")
                print("   2. Filtra apenas dados novos da sessão")
                print("   3. Salva no PostgreSQL")
                print("   4. Remove dados temporários do modelo")
                
                try:
                    # 1. Obter dados atuais do modelo Vanna
                    training_data = vanna.get_training_data()
                    if training_data is not None and not training_data.empty:
                        
                        # 2. Converter para formato compatível com DatabaseManager
                        training_data_dict = training_data.to_dict(orient='records')
                        
                        # 3. Usar helper para garantir formato correto
                        formatted_data = db_manager.format_training_data_batch(training_data_dict, user_id)
                        
                        print(f"📋 [SMART_CLEAN] Formatados {len(formatted_data)} registros para salvamento")
                        
                        # 3. Salvar no PostgreSQL usando DatabaseManager
                        success = db_manager.save_training_data(user_id, formatted_data)
                        
                        if success:
                            print(f"✅ [SMART_CLEAN] {len(formatted_data)} registros salvos no PostgreSQL")
                            print("✔ Dados salvos no PostgreSQL")
                        else:
                            print("⚠️ [SMART_CLEAN] Falha ao salvar no PostgreSQL")
                    else:
                        print("ℹ️ [SMART_CLEAN] Nenhum dado novo para salvar")
                    
                    # 4. Limpeza inteligente do modelo (preserva dados do backup)
                    try:
                        backup_ids = db_manager.get_training_data_ids(None)  # Dados globais
                        current_data = vanna.get_training_data()
                        
                        if current_data is not None and not current_data.empty:
                            current_ids = current_data["id"].tolist()
                            
                            # Remove apenas IDs que não estão no backup
                            removed_count = 0
                            for data_id in current_ids:
                                if data_id not in backup_ids:
                                    try:
                                        vanna.remove_training_data(id=data_id)
                                        removed_count += 1
                                    except Exception as e:
                                        print(f"⚠️ [SMART_CLEAN] Erro ao remover ID {data_id}: {e}")
                            
                            print(f"🧹 [SMART_CLEAN] {removed_count} registros temporários removidos do modelo")
                        
                    except Exception as cleanup_error:
                        print(f"⚠️ [SMART_CLEAN] Erro na limpeza do modelo: {cleanup_error}")
                    
                    print(f"✅ [SMART_CLEAN] Limpeza PostgreSQL concluída para usuário {user_id}")
                    return True
                    
                except Exception as db_error:
                    print(f"⚠️ [SMART_CLEAN] Erro no DatabaseManager: {db_error}")
                    return False
            
        except Exception as e:
            print(f"❌ [SMART_CLEAN] Erro na limpeza inteligente: {e}")
            return False
    
    def start_session_monitor(self):
        """Inicia monitor leve de sessão (apenas para encerramento inesperado)"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        monitor_thread = threading.Thread(target=self._monitor_session, daemon=True)
        monitor_thread.start()
        print("🔍 [MONITOR] Monitor de sessão iniciado")
    
    def _monitor_session(self):
        """Monitor leve - verifica apenas a cada 10 segundos"""
        last_check = time.time()
        
        while self.is_monitoring:
            try:
                time.sleep(10)  # Verifica a cada 10s (menos frequente)
                
                # Verifica se sessão ainda existe
                if not self._session_still_active():
                    print("🚨 [MONITOR] Sessão encerrada inesperadamente")
                    self._emergency_cleanup()
                    break
                    
                last_check = time.time()
                
            except Exception as e:
                print(f"⚠️ [MONITOR] Erro no monitoramento: {e}")
                self._emergency_cleanup()
                break
    
    def _session_still_active(self):
        """Verifica se a sessão ainda está ativa"""
        try:
            return (hasattr(st, 'session_state') and 
                   st.session_state and 
                   st.session_state.get("logado", False))
        except:
            return False
    
    def _emergency_cleanup(self):
        """Cleanup de emergência para encerramento inesperado"""
        try:
            user_id = getattr(st.session_state, 'id_client', None) if hasattr(st, 'session_state') else None
            
            if user_id:
                print(f"🚨 [EMERGENCY] Cleanup para usuário {user_id}")
                self.execute_session_cleanup(force=True)
            
            self.is_monitoring = False
            
        except Exception as e:
            print(f"❌ [EMERGENCY] Erro crítico: {e}")

# Instância global do controlador
session_controller = SessionCleanupController()

def register_session_cleanup():
    """
    Registra sistema de cleanup otimizado (CHAME APENAS UMA VEZ)
    """
    if st.session_state.get("cleanup_system_registered"):
        return
        
    import atexit
    
    # Registra cleanup para encerramento normal
    atexit.register(lambda: session_controller.execute_session_cleanup(force=False))
    
    # Inicia monitor leve
    session_controller.start_session_monitor()
    
    st.session_state.cleanup_system_registered = True
    print("🔧 [INIT] Sistema de cleanup otimizado registrado")

def execute_logout_cleanup():
    """
    Executa cleanup no logout (CHAME NO LOGOUT)
    """
    user_id = st.session_state.get("id_client")
    
    if not user_id:
        print("⚠️ [LOGOUT] Nenhum usuário para cleanup")
        return False
    
    # Salva histórico de chat
    try:
        from auth.auth_utils import salvar_historico_chat_pickle
        salvar_historico_chat_pickle()
        print("💾 [LOGOUT] Histórico salvo")
    except Exception as e:
        print(f"⚠️ [LOGOUT] Erro ao salvar histórico: {e}")
    
    # Executa salvamento + limpeza filtrada
    success = session_controller.execute_session_cleanup(force=False)
    
    if success:
        print(f"✅ [LOGOUT] Cleanup completo para usuário {user_id}")
    else:
        print(f"❌ [LOGOUT] Falha no cleanup para usuário {user_id}")
    
    return success

def execute_user_change_cleanup(old_user_id, new_user_id):
    """
    Executa cleanup na mudança de usuário (CHAME NA MUDANÇA)
    """
    if old_user_id == new_user_id:
        return True
        
    print(f"👤 [USER_CHANGE] {old_user_id} → {new_user_id}")
    
    # Executa cleanup para usuário anterior
    if old_user_id:
        # Temporariamente define o usuário anterior para cleanup
        temp_user = st.session_state.get("id_client")
        st.session_state.id_client = old_user_id
        
        success = session_controller.execute_session_cleanup(force=False)
        
        # Restaura usuário atual
        st.session_state.id_client = temp_user
        
        if success:
            print(f"✅ [USER_CHANGE] Cleanup do usuário anterior {old_user_id}")
        else:
            print(f"❌ [USER_CHANGE] Falha no cleanup do usuário {old_user_id}")
        
        return success
    
    return True

def force_manual_cleanup():
    """
    Força cleanup manual (PARA TESTES OU ENCERRAMENTO MANUAL)
    """
    user_id = st.session_state.get("id_client")
    
    print(f"🔧 [MANUAL] Forçando cleanup para usuário {user_id}")
    
    success = session_controller.execute_session_cleanup(force=True)
    
    if success:
        print(f"✅ [MANUAL] Cleanup forçado concluído")
    else:
        print(f"❌ [MANUAL] Falha no cleanup forçado")
    
    return success

def get_cleanup_status():
    """
    Retorna status atual do sistema de cleanup
    """
    return {
        "cleanup_executed": session_controller.cleanup_executed,
        "current_user": session_controller.user_id,
        "is_monitoring": session_controller.is_monitoring,
        "system_registered": st.session_state.get("cleanup_system_registered", False)
    }

# Exemplo de uso na interface:
"""
# NO app.py main():
from session_cleanup_controller import register_session_cleanup

def main():
    # Registra sistema APENAS UMA VEZ
    register_session_cleanup()
    
    # ...resto do código...

# NO auth_utils.py logout():
from session_cleanup_controller import execute_logout_cleanup

def logout():
    execute_logout_cleanup()  # Em vez de múltiplas limpezas
    # ...resto do logout...

# PARA mudança de usuário:
from session_cleanup_controller import execute_user_change_cleanup

if "last_user" in st.session_state and st.session_state.last_user != current_user:
    execute_user_change_cleanup(st.session_state.last_user, current_user)
st.session_state.last_user = current_user
"""
