#!/usr/bin/env python3
"""
DEPRECIADO: Este arquivo foi substituído por session_cleanup_controller.py

Sistema antigo de cleanup - mantido apenas para referência.
Use session_cleanup_controller.py para controle otimizado de sessão.
"""

import streamlit as st
import time
import threading
from typing import Optional

class VannaCleanupMonitor:
    """
    Monitor para garantir limpeza dos dados de treinamento
    
    DEPRECIADO: Use SessionCleanupController em vez desta classe
    """
    
    def __init__(self):
        self.is_active = False
        self.last_check = time.time()
        
    def start_monitoring(self):
        """Inicia monitoramento da sessão"""
        if not self.is_active:
            self.is_active = True
            monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            monitor_thread.start()
            print("🔍 [MONITOR] Monitor de limpeza iniciado")
    
    def _monitor_loop(self):
        """Loop de monitoramento"""
        while self.is_active:
            try:
                time.sleep(3)  # Verifica a cada 3 segundos
                
                # Verifica se sessão ainda existe
                if not self._session_exists():
                    self._emergency_cleanup()
                    break
                    
                # Atualiza timestamp
                self.last_check = time.time()
                
            except Exception as e:
                print(f"⚠️ [MONITOR] Erro no monitoramento: {e}")
                self._emergency_cleanup()
                break
    
    def _session_exists(self) -> bool:
        """Verifica se a sessão ainda existe"""
        try:
            return hasattr(st, 'session_state') and bool(st.session_state)
        except:
            return False
    
    def _emergency_cleanup(self):
        """Limpeza de emergência"""
        try:
            print("🚨 [MONITOR] Executando limpeza de emergência...")
            
            if hasattr(st.session_state, 'vanna') and st.session_state.get('vanna'):
                vanna = st.session_state.vanna
                
                try:
                    import sys
                    import os
                    # Adiciona src ao path se não estiver
                    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
                    if src_path not in sys.path:
                        sys.path.append(src_path)
                    
                    from vanna_core import limpar_data_training
                    limpar_data_training(vanna)
                    print("✅ [MONITOR] Limpeza de emergência executada")
                except Exception as e:
                    print(f"❌ [MONITOR] Erro na limpeza de emergência: {e}")
            
            self.is_active = False
            
        except Exception as e:
            print(f"❌ [MONITOR] Erro crítico na limpeza de emergência: {e}")

# Instância global do monitor
cleanup_monitor = VannaCleanupMonitor()
