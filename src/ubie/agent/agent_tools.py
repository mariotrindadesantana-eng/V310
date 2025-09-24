#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MÓDULO 4: Cinto de Ferramentas do Agente
Objetivo: Fornecer funções para interação com o sistema local, como leitura de arquivos, 
pausa/retomada de fluxos e ajuste de parâmetros.

⚠️ AVISO DE PRIVACIDADE:
Este módulo processa dados localmente, mas o processamento de IA ocorre via Google Gemini Cloud.

🔒 SEGURANÇA:
- Todos os caminhos são validados para evitar directory traversal
- Somente arquivos dentro da pasta da sessão podem ser acessados
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .session_state_manager import session_manager

logger = logging.getLogger(__name__)

class AgentTools:
    """
    Conjunto de ferramentas para o agente interagir com o sistema local.
    
    Funções principais:
    - get_system_status(session_id): Retorna o status da sessão
    - pause_workflow(session_id): Pausa a análise em execução
    - resume_workflow(session_id): Prepara a sessão para ser retomada
    - get_file_content(session_id, filename): Lê conteúdo de arquivos locais com validação
    - refine_search_query(session_id, new_query): Atualiza a query de busca no config.json
    """
    
    def __init__(self):
        """Inicializa as ferramentas do agente."""
        self.analyses_base_dir = os.getenv('ANALYSES_BASE_DIR', 'analyses_data')
        logger.info("🛠️ AgentTools inicializado")

    def get_system_status(self, session_id: str) -> Dict[str, Any]:
        """
        Retorna o status completo da sessão de análise.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dicionário com status detalhado da sessão
        """
        try:
            # Status básico da sessão
            session_status = session_manager.get_status(session_id)
            
            if not session_status:
                return {
                    'status': 'error',
                    'message': f'Sessão {session_id} não encontrada',
                    'session_exists': False
                }
            
            # Informações adicionais do sistema
            session_dir = session_manager.get_session_directory(session_id)
            
            # Lista arquivos da sessão
            session_files = []
            if session_dir and os.path.exists(session_dir):
                try:
                    for file in os.listdir(session_dir):
                        file_path = os.path.join(session_dir, file)
                        if os.path.isfile(file_path):
                            file_info = {
                                'name': file,
                                'size': os.path.getsize(file_path),
                                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                            }
                            session_files.append(file_info)
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao listar arquivos da sessão: {e}")
            
            # Verifica saúde do sistema
            system_health = self._check_system_health()
            
            return {
                'status': 'success',
                'session_status': session_status,
                'session_directory': session_dir,
                'session_files': session_files,
                'system_health': system_health,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter status do sistema para sessão {session_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'session_id': session_id
            }

    def pause_workflow(self, session_id: str, reason: str = "Pausado pelo usuário") -> Dict[str, Any]:
        """
        Pausa a análise em execução para a sessão especificada.
        
        Args:
            session_id: ID da sessão
            reason: Motivo da pausa
            
        Returns:
            Dicionário com resultado da operação
        """
        try:
            # Verifica se sessão existe
            current_status = session_manager.get_status(session_id)
            if not current_status:
                return {
                    'status': 'error',
                    'message': f'Sessão {session_id} não encontrada'
                }
            
            # Verifica se está executando
            if current_status.get('status') != 'running':
                return {
                    'status': 'warning',
                    'message': f'Sessão {session_id} não está executando. Status atual: {current_status.get("status")}'
                }
            
            # Pausa a sessão
            success = session_manager.set_status(
                session_id, 
                'paused',
                additional_data={
                    'pause_reason': reason,
                    'paused_at': datetime.now().isoformat()
                }
            )
            
            if success:
                # Adiciona entrada no log
                session_manager.add_error_log(
                    session_id,
                    f"Workflow pausado: {reason}",
                    "AgentTools"
                )
                
                logger.info(f"⏸️ Workflow pausado para sessão {session_id}: {reason}")
                
                return {
                    'status': 'success',
                    'message': f'Workflow pausado com sucesso',
                    'session_id': session_id,
                    'reason': reason
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Falha ao pausar workflow'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao pausar workflow para sessão {session_id}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def resume_workflow(self, session_id: str) -> Dict[str, Any]:
        """
        Prepara a sessão para ser retomada (muda status para idle).
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dicionário com resultado da operação
        """
        try:
            # Verifica se sessão existe
            current_status = session_manager.get_status(session_id)
            if not current_status:
                return {
                    'status': 'error',
                    'message': f'Sessão {session_id} não encontrada'
                }
            
            # Verifica se está pausada
            if current_status.get('status') != 'paused':
                return {
                    'status': 'warning',
                    'message': f'Sessão {session_id} não está pausada. Status atual: {current_status.get("status")}'
                }
            
            # Prepara para retomar (status idle)
            success = session_manager.set_status(
                session_id, 
                'idle',
                additional_data={
                    'resume_prepared_at': datetime.now().isoformat(),
                    'ready_to_resume': True
                }
            )
            
            if success:
                logger.info(f"▶️ Sessão {session_id} preparada para retomar")
                
                return {
                    'status': 'success',
                    'message': 'Sessão preparada para retomar. Use o sistema principal para reiniciar a análise.',
                    'session_id': session_id,
                    'next_step': current_status.get('current_step', 0)
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Falha ao preparar sessão para retomar'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao preparar retomada para sessão {session_id}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def get_file_content(self, session_id: str, filename: str, max_size: int = 1024*1024) -> Dict[str, Any]:
        """
        Lê conteúdo de arquivos locais com validação de caminho de segurança.
        
        Args:
            session_id: ID da sessão
            filename: Nome do arquivo (sem caminho)
            max_size: Tamanho máximo em bytes (padrão: 1MB)
            
        Returns:
            Dicionário com conteúdo do arquivo ou erro
        """
        try:
            # Validação de segurança - evita directory traversal
            if not self._is_safe_filename(filename):
                return {
                    'status': 'error',
                    'message': 'Nome de arquivo inválido ou não seguro'
                }
            
            # Verifica se sessão existe
            session_dir = session_manager.get_session_directory(session_id)
            if not session_dir:
                return {
                    'status': 'error',
                    'message': f'Sessão {session_id} não encontrada'
                }
            
            # Constrói caminho seguro
            file_path = os.path.join(session_dir, filename)
            
            # Validação adicional - garante que o arquivo está dentro da pasta da sessão
            if not self._is_path_within_session(file_path, session_dir):
                return {
                    'status': 'error',
                    'message': 'Acesso negado: arquivo fora da pasta da sessão'
                }
            
            # Verifica se arquivo existe
            if not os.path.exists(file_path):
                return {
                    'status': 'error',
                    'message': f'Arquivo {filename} não encontrado na sessão'
                }
            
            # Verifica tamanho do arquivo
            file_size = os.path.getsize(file_path)
            if file_size > max_size:
                return {
                    'status': 'error',
                    'message': f'Arquivo muito grande ({file_size} bytes). Máximo: {max_size} bytes'
                }
            
            # Lê conteúdo do arquivo
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_info = {
                    'name': filename,
                    'size': file_size,
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                    'encoding': 'utf-8'
                }
                
                logger.info(f"📄 Arquivo lido: {filename} ({file_size} bytes)")
                
                return {
                    'status': 'success',
                    'content': content,
                    'file_info': file_info,
                    'session_id': session_id
                }
                
            except UnicodeDecodeError:
                # Tenta ler como binário se UTF-8 falhar
                with open(file_path, 'rb') as f:
                    binary_content = f.read()
                
                return {
                    'status': 'success',
                    'content': binary_content.hex(),  # Retorna em hexadecimal
                    'file_info': {
                        'name': filename,
                        'size': file_size,
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                        'encoding': 'binary'
                    },
                    'session_id': session_id,
                    'note': 'Arquivo binário retornado em formato hexadecimal'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao ler arquivo {filename} da sessão {session_id}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def refine_search_query(self, session_id: str, new_query: str) -> Dict[str, Any]:
        """
        Atualiza a query de busca no config.json da sessão.
        
        Args:
            session_id: ID da sessão
            new_query: Nova query de busca
            
        Returns:
            Dicionário com resultado da operação
        """
        try:
            # Validação da query
            if not new_query or not new_query.strip():
                return {
                    'status': 'error',
                    'message': 'Query não pode estar vazia'
                }
            
            new_query = new_query.strip()
            
            # Verifica se sessão existe
            session_dir = session_manager.get_session_directory(session_id)
            if not session_dir:
                return {
                    'status': 'error',
                    'message': f'Sessão {session_id} não encontrada'
                }
            
            # Atualiza no session manager
            success = session_manager.set_status(
                session_id,
                session_manager.get_status(session_id).get('status', 'idle'),
                additional_data={
                    'query': new_query,
                    'query_updated_at': datetime.now().isoformat()
                }
            )
            
            if success:
                logger.info(f"🔍 Query atualizada para sessão {session_id}: {new_query}")
                
                return {
                    'status': 'success',
                    'message': 'Query de busca atualizada com sucesso',
                    'session_id': session_id,
                    'new_query': new_query,
                    'previous_query': session_manager.get_status(session_id).get('query', '')
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Falha ao atualizar query'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar query da sessão {session_id}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def list_session_files(self, session_id: str) -> Dict[str, Any]:
        """
        Lista todos os arquivos disponíveis na sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dicionário com lista de arquivos
        """
        try:
            session_dir = session_manager.get_session_directory(session_id)
            if not session_dir:
                return {
                    'status': 'error',
                    'message': f'Sessão {session_id} não encontrada'
                }
            
            if not os.path.exists(session_dir):
                return {
                    'status': 'error',
                    'message': 'Diretório da sessão não existe'
                }
            
            files = []
            for item in os.listdir(session_dir):
                item_path = os.path.join(session_dir, item)
                if os.path.isfile(item_path):
                    file_info = {
                        'name': item,
                        'size': os.path.getsize(item_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat(),
                        'extension': os.path.splitext(item)[1].lower()
                    }
                    files.append(file_info)
            
            # Ordena por data de modificação (mais recente primeiro)
            files.sort(key=lambda x: x['modified'], reverse=True)
            
            return {
                'status': 'success',
                'files': files,
                'total_files': len(files),
                'session_id': session_id,
                'session_directory': session_dir
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar arquivos da sessão {session_id}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def get_analysis_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Retorna um resumo da análise em andamento ou concluída.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dicionário com resumo da análise
        """
        try:
            session_status = session_manager.get_status(session_id)
            if not session_status:
                return {
                    'status': 'error',
                    'message': f'Sessão {session_id} não encontrada'
                }
            
            # Busca por arquivo de relatório
            session_dir = session_manager.get_session_directory(session_id)
            report_files = []
            
            if session_dir and os.path.exists(session_dir):
                for file in os.listdir(session_dir):
                    if any(keyword in file.lower() for keyword in ['report', 'summary', 'analysis', 'resultado']):
                        report_files.append(file)
            
            summary = {
                'session_id': session_id,
                'status': session_status.get('status'),
                'query': session_status.get('query', ''),
                'created_at': session_status.get('created_at'),
                'updated_at': session_status.get('updated_at'),
                'progress': session_status.get('analysis_progress', {}),
                'total_errors': len(session_status.get('error_log', [])),
                'report_files': report_files,
                'module_results': session_status.get('module_results', {})
            }
            
            return {
                'status': 'success',
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter resumo da análise {session_id}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _is_safe_filename(self, filename: str) -> bool:
        """
        Valida se o nome do arquivo é seguro (evita directory traversal).
        
        Args:
            filename: Nome do arquivo
            
        Returns:
            bool: True se seguro
        """
        # Caracteres e padrões proibidos
        forbidden_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        forbidden_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
        
        # Verifica caracteres proibidos
        for char in forbidden_chars:
            if char in filename:
                return False
        
        # Verifica nomes reservados (Windows)
        base_name = os.path.splitext(filename)[0].upper()
        if base_name in forbidden_names:
            return False
        
        # Verifica se não é vazio e não começa/termina com espaço ou ponto
        if not filename or filename.startswith('.') or filename.startswith(' ') or filename.endswith(' '):
            return False
        
        return True

    def _is_path_within_session(self, file_path: str, session_dir: str) -> bool:
        """
        Verifica se o caminho do arquivo está dentro do diretório da sessão.
        
        Args:
            file_path: Caminho do arquivo
            session_dir: Diretório da sessão
            
        Returns:
            bool: True se dentro do diretório
        """
        try:
            # Resolve caminhos absolutos
            abs_file_path = os.path.abspath(file_path)
            abs_session_dir = os.path.abspath(session_dir)
            
            # Verifica se o arquivo está dentro do diretório da sessão
            return abs_file_path.startswith(abs_session_dir)
            
        except Exception:
            return False

    def _check_system_health(self) -> Dict[str, Any]:
        """
        Verifica a saúde geral do sistema.
        
        Returns:
            Dicionário com informações de saúde
        """
        try:
            health = {
                'analyses_directory_exists': os.path.exists(self.analyses_base_dir),
                'analyses_directory_writable': os.access(self.analyses_base_dir, os.W_OK),
                'total_sessions': len(session_manager.list_sessions()),
                'active_sessions': len(session_manager.list_sessions('running')),
                'paused_sessions': len(session_manager.list_sessions('paused')),
                'timestamp': datetime.now().isoformat()
            }
            
            # Verifica espaço em disco
            try:
                statvfs = os.statvfs(self.analyses_base_dir)
                free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
                health['free_disk_space_gb'] = round(free_space_gb, 2)
                health['disk_space_adequate'] = free_space_gb > 1.0  # Pelo menos 1GB livre
            except:
                health['free_disk_space_gb'] = 'unknown'
                health['disk_space_adequate'] = True
            
            return health
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar saúde do sistema: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

# Instância global das ferramentas do agente
agent_tools = AgentTools()