#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MÓDULO 1: Gerenciador de Estado de Sessão
Objetivo: Manter registro em memória do estado das análises, com persistência de estado em disco 
para sobreviver a restarts do servidor.

⚠️ AVISO DE PRIVACIDADE:
Este módulo armazena dados localmente, mas o processamento de IA ocorre via Google Gemini Cloud.
"""

import os
import json
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class SessionStateManager:
    """
    Singleton Thread-Safe para gerenciar estado das sessões de análise.
    
    Funcionalidades:
    - Singleton Thread-Safe: Garante uma única instância, mesmo em ambientes concorrentes
    - Persistência de Estado: Salva estado em config.json dentro de analyses_data/<session_id>
    - Registro de Sessão: Cria novas sessões com estado inicial 'idle' 
    - Controle de Status: Atualiza status (idle, running, paused) e etapa atual
    - Consulta de Estado: Retorna status sem campos não serializáveis (threads)
    """
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SessionStateManager, cls).__new__(cls)
                    cls._instance.sessions = {}
                    cls._instance.analyses_base_dir = os.getenv('ANALYSES_BASE_DIR', 'analyses_data')
                    cls._instance._load_sessions_from_disk()
                    logger.info("✅ SessionStateManager inicializado como Singleton")
        return cls._instance

    def _load_sessions_from_disk(self):
        """Carrega sessões existentes do disco no startup."""
        if not os.path.exists(self.analyses_base_dir):
            os.makedirs(self.analyses_base_dir, exist_ok=True)
            logger.info(f"📁 Diretório de análises criado: {self.analyses_base_dir}")
            return
        
        loaded_sessions = 0
        for session_id in os.listdir(self.analyses_base_dir):
            session_dir = os.path.join(self.analyses_base_dir, session_id)
            if not os.path.isdir(session_dir):
                continue
                
            config_path = os.path.join(session_dir, "config.json")
            if not os.path.exists(config_path):
                logger.warning(f"⚠️ Sessão {session_id} sem config.json, ignorando")
                continue
                
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Carrega apenas estado essencial (não salva threads)
                self.sessions[session_id] = {
                    'session_id': session_id,
                    'status': config.get('status', 'idle'),
                    'current_step': config.get('current_step', 0),
                    'created_at': config.get('created_at', datetime.now().isoformat()),
                    'updated_at': datetime.now().isoformat(),
                    'query': config.get('query', ''),
                    'module_results': config.get('module_results', {}),
                    'analysis_progress': config.get('analysis_progress', {}),
                    'error_log': config.get('error_log', []),
                    'config_path': config_path,
                    'session_dir': session_dir
                }
                loaded_sessions += 1
                
            except Exception as e:
                logger.error(f"❌ Erro ao carregar sessão {session_id}: {e}")
                continue
        
        logger.info(f"📄 {loaded_sessions} sessões carregadas do disco")

    def register_session(self, session_id: str, query: str = "", initial_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Registra uma nova sessão de análise.
        
        Args:
            session_id: Identificador único da sessão
            query: Query inicial de pesquisa 
            initial_data: Dados iniciais opcionais
            
        Returns:
            bool: True se criado com sucesso
        """
        try:
            with self._lock:
                if session_id in self.sessions:
                    logger.warning(f"⚠️ Sessão {session_id} já existe")
                    return False
                
                # Cria diretório da sessão
                session_dir = os.path.join(self.analyses_base_dir, session_id)
                os.makedirs(session_dir, exist_ok=True)
                
                # Estado inicial
                session_data = {
                    'session_id': session_id,
                    'status': 'idle',
                    'current_step': 0,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'query': query,
                    'module_results': {},
                    'analysis_progress': {
                        'total_steps': 0,
                        'completed_steps': 0,
                        'current_module': '',
                        'progress_percentage': 0
                    },
                    'error_log': [],
                    'config_path': os.path.join(session_dir, "config.json"),
                    'session_dir': session_dir
                }
                
                # Adiciona dados iniciais se fornecidos
                if initial_data:
                    session_data.update(initial_data)
                
                # Salva em memória
                self.sessions[session_id] = session_data
                
                # Persiste no disco
                self._save_session_to_disk(session_id)
                
                logger.info(f"✅ Nova sessão registrada: {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao registrar sessão {session_id}: {e}")
            return False

    def set_status(self, session_id: str, status: str, step: Optional[int] = None, 
                   additional_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Atualiza o status e etapa de uma sessão.
        
        Args:
            session_id: ID da sessão
            status: Novo status (idle, running, paused, completed, error)
            step: Etapa atual (opcional)
            additional_data: Dados adicionais (opcional)
            
        Returns:
            bool: True se atualizado com sucesso
        """
        try:
            with self._lock:
                if session_id not in self.sessions:
                    logger.warning(f"⚠️ Sessão {session_id} não encontrada")
                    return False
                
                # Atualiza dados
                self.sessions[session_id]['status'] = status
                self.sessions[session_id]['updated_at'] = datetime.now().isoformat()
                
                if step is not None:
                    self.sessions[session_id]['current_step'] = step
                
                if additional_data:
                    self.sessions[session_id].update(additional_data)
                
                # Persiste no disco
                self._save_session_to_disk(session_id)
                
                logger.info(f"🔄 Status da sessão {session_id} atualizado para: {status}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar status da sessão {session_id}: {e}")
            return False

    def get_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retorna o status de uma sessão sem campos não serializáveis.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dict com status da sessão ou None se não encontrada
        """
        try:
            with self._lock:
                if session_id not in self.sessions:
                    return None
                
                # Cria cópia sem campos não serializáveis
                session_copy = self.sessions[session_id].copy()
                
                # Remove campos que não devem ser expostos
                excluded_fields = ['thread', 'lock', 'session_dir', 'config_path']
                for field in excluded_fields:
                    session_copy.pop(field, None)
                
                return session_copy
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter status da sessão {session_id}: {e}")
            return None

    def update_progress(self, session_id: str, current_module: str, 
                       completed_steps: int, total_steps: int) -> bool:
        """
        Atualiza o progresso de análise de uma sessão.
        
        Args:
            session_id: ID da sessão
            current_module: Módulo atual sendo processado
            completed_steps: Passos concluídos
            total_steps: Total de passos
            
        Returns:
            bool: True se atualizado com sucesso
        """
        try:
            with self._lock:
                if session_id not in self.sessions:
                    return False
                
                progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
                
                self.sessions[session_id]['analysis_progress'] = {
                    'total_steps': total_steps,
                    'completed_steps': completed_steps,
                    'current_module': current_module,
                    'progress_percentage': round(progress_percentage, 2)
                }
                
                self.sessions[session_id]['updated_at'] = datetime.now().isoformat()
                
                # Persiste no disco
                self._save_session_to_disk(session_id)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar progresso da sessão {session_id}: {e}")
            return False

    def add_error_log(self, session_id: str, error_message: str, module_name: str = "") -> bool:
        """
        Adiciona entrada no log de erros da sessão.
        
        Args:
            session_id: ID da sessão
            error_message: Mensagem de erro
            module_name: Nome do módulo onde ocorreu o erro
            
        Returns:
            bool: True se adicionado com sucesso
        """
        try:
            with self._lock:
                if session_id not in self.sessions:
                    return False
                
                error_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'module': module_name,
                    'message': error_message
                }
                
                if 'error_log' not in self.sessions[session_id]:
                    self.sessions[session_id]['error_log'] = []
                
                self.sessions[session_id]['error_log'].append(error_entry)
                
                # Mantém apenas os últimos 50 erros
                if len(self.sessions[session_id]['error_log']) > 50:
                    self.sessions[session_id]['error_log'] = self.sessions[session_id]['error_log'][-50:]
                
                self.sessions[session_id]['updated_at'] = datetime.now().isoformat()
                
                # Persiste no disco
                self._save_session_to_disk(session_id)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar log de erro para sessão {session_id}: {e}")
            return False

    def list_sessions(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lista todas as sessões, opcionalmente filtradas por status.
        
        Args:
            status_filter: Status para filtrar (opcional)
            
        Returns:
            Lista de sessões
        """
        try:
            with self._lock:
                sessions_list = []
                
                for session_id, session_data in self.sessions.items():
                    if status_filter and session_data.get('status') != status_filter:
                        continue
                    
                    # Cria cópia sem campos internos
                    session_copy = session_data.copy()
                    excluded_fields = ['thread', 'lock', 'session_dir', 'config_path']
                    for field in excluded_fields:
                        session_copy.pop(field, None)
                    
                    sessions_list.append(session_copy)
                
                # Ordena por data de criação (mais recente primeiro)
                sessions_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                
                return sessions_list
                
        except Exception as e:
            logger.error(f"❌ Erro ao listar sessões: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """
        Remove uma sessão da memória e disco.
        
        Args:
            session_id: ID da sessão a ser removida
            
        Returns:
            bool: True se removida com sucesso
        """
        try:
            with self._lock:
                if session_id not in self.sessions:
                    logger.warning(f"⚠️ Sessão {session_id} não encontrada para remoção")
                    return False
                
                session_dir = self.sessions[session_id].get('session_dir')
                
                # Remove da memória
                del self.sessions[session_id]
                
                # Remove diretório do disco se existir
                if session_dir and os.path.exists(session_dir):
                    import shutil
                    shutil.rmtree(session_dir)
                    logger.info(f"🗑️ Diretório da sessão removido: {session_dir}")
                
                logger.info(f"✅ Sessão {session_id} removida com sucesso")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao remover sessão {session_id}: {e}")
            return False

    def _save_session_to_disk(self, session_id: str):
        """Salva dados da sessão no disco."""
        try:
            if session_id not in self.sessions:
                return
            
            session_data = self.sessions[session_id].copy()
            
            # Remove campos não serializáveis
            excluded_fields = ['thread', 'lock', 'session_dir', 'config_path']
            for field in excluded_fields:
                session_data.pop(field, None)
            
            config_path = self.sessions[session_id]['config_path']
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Erro ao salvar sessão {session_id} no disco: {e}")

    def get_session_directory(self, session_id: str) -> Optional[str]:
        """
        Retorna o diretório da sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Caminho do diretório ou None se não encontrado
        """
        if session_id in self.sessions:
            return self.sessions[session_id].get('session_dir')
        return None

# Instância global singleton
session_manager = SessionStateManager()