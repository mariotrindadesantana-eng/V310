#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MÓDULO 2: Memória de Conversação Persistente
Objetivo: Armazenar o histórico de conversas entre o usuário e o agente em um banco SQLite local.

⚠️ AVISO DE PRIVACIDADE:
Este módulo armazena conversas localmente, mas o processamento de IA ocorre via Google Gemini Cloud.
"""

import os
import sqlite3
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class ConversationMemory:
    """
    Gerenciador de memória persistente para conversas do agente.
    
    Características:
    - Persistência local com SQLite
    - Histórico de mensagens (usuário e modelo) por session_id  
    - Integração com AgentManager para manter contexto das conversas
    - Thread-safe para uso concorrente
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Inicializa o gerenciador de memória de conversação.
        
        Args:
            db_path: Caminho para o banco SQLite (opcional)
        """
        self.analyses_base_dir = os.getenv('ANALYSES_BASE_DIR', 'analyses_data')
        
        if db_path is None:
            # Cria banco na pasta analyses_data
            os.makedirs(self.analyses_base_dir, exist_ok=True)
            self.db_path = os.path.join(self.analyses_base_dir, 'conversation_memory.db')
        else:
            self.db_path = db_path
            
        self._lock = threading.Lock()
        self._init_database()
        
        logger.info(f"✅ ConversationMemory inicializado: {self.db_path}")
    
    def _init_database(self):
        """Inicializa as tabelas do banco de dados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tabela principal de conversas
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,  -- 'user' ou 'agent'
                        message TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        metadata TEXT,  -- JSON com dados adicionais
                        tokens_used INTEGER DEFAULT 0,
                        model_used TEXT DEFAULT '',
                        tool_calls TEXT,  -- JSON com chamadas de ferramentas
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Índices para performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_session_timestamp 
                    ON conversations(session_id, timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_session_role 
                    ON conversations(session_id, role)
                ''')
                
                # Tabela de resumos de sessões
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS session_summaries (
                        session_id TEXT PRIMARY KEY,
                        summary TEXT,
                        total_messages INTEGER DEFAULT 0,
                        total_tokens INTEGER DEFAULT 0,
                        first_message_at TEXT,
                        last_message_at TEXT,
                        status TEXT DEFAULT 'active',
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("🗄️ Tabelas de memória de conversação inicializadas")
                
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar banco de dados: {e}")
            raise

    def add_message(self, session_id: str, role: str, message: str, 
                   metadata: Optional[Dict[str, Any]] = None,
                   tokens_used: int = 0, model_used: str = '',
                   tool_calls: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Adiciona uma mensagem ao histórico da conversação.
        
        Args:
            session_id: ID da sessão
            role: 'user' ou 'agent'
            message: Conteúdo da mensagem
            metadata: Dados adicionais (opcional)
            tokens_used: Número de tokens utilizados
            model_used: Modelo de IA utilizado
            tool_calls: Chamadas de ferramentas realizadas
            
        Returns:
            bool: True se adicionado com sucesso
        """
        try:
            with self._lock:
                import json
                
                timestamp = datetime.now().isoformat()
                metadata_json = json.dumps(metadata) if metadata else None
                tool_calls_json = json.dumps(tool_calls) if tool_calls else None
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Insere mensagem
                    cursor.execute('''
                        INSERT INTO conversations 
                        (session_id, role, message, timestamp, metadata, tokens_used, model_used, tool_calls)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (session_id, role, message, timestamp, metadata_json, 
                         tokens_used, model_used, tool_calls_json))
                    
                    # Atualiza resumo da sessão
                    self._update_session_summary(cursor, session_id, timestamp, tokens_used)
                    
                    conn.commit()
                    
                logger.debug(f"💬 Mensagem adicionada para sessão {session_id}: {role}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar mensagem para sessão {session_id}: {e}")
            return False

    def get_conversation_history(self, session_id: str, limit: int = 50, 
                               include_metadata: bool = False) -> List[Dict[str, Any]]:
        """
        Recupera o histórico de conversação de uma sessão.
        
        Args:
            session_id: ID da sessão
            limit: Número máximo de mensagens
            include_metadata: Se deve incluir metadados
            
        Returns:
            Lista de mensagens ordenadas por timestamp
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Query básica
                    base_query = '''
                        SELECT id, session_id, role, message, timestamp, 
                               tokens_used, model_used, tool_calls
                    '''
                    
                    if include_metadata:
                        base_query += ', metadata'
                    
                    base_query += '''
                        FROM conversations 
                        WHERE session_id = ? 
                        ORDER BY timestamp ASC 
                        LIMIT ?
                    '''
                    
                    cursor.execute(base_query, (session_id, limit))
                    rows = cursor.fetchall()
                    
                    messages = []
                    for row in rows:
                        import json
                        
                        message_data = {
                            'id': row['id'],
                            'session_id': row['session_id'],
                            'role': row['role'],
                            'message': row['message'],
                            'timestamp': row['timestamp'],
                            'tokens_used': row['tokens_used'],
                            'model_used': row['model_used']
                        }
                        
                        # Adiciona tool_calls se existir
                        if row['tool_calls']:
                            try:
                                message_data['tool_calls'] = json.loads(row['tool_calls'])
                            except:
                                message_data['tool_calls'] = []
                        
                        # Adiciona metadata se solicitado
                        if include_metadata and row.get('metadata'):
                            try:
                                message_data['metadata'] = json.loads(row['metadata'])
                            except:
                                message_data['metadata'] = {}
                        
                        messages.append(message_data)
                    
                    logger.debug(f"📖 {len(messages)} mensagens recuperadas para sessão {session_id}")
                    return messages
                    
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar histórico da sessão {session_id}: {e}")
            return []

    def get_context_for_ai(self, session_id: str, context_limit: int = 10) -> List[Dict[str, str]]:
        """
        Recupera contexto formatado para o modelo de IA.
        
        Args:
            session_id: ID da sessão
            context_limit: Número de mensagens recentes para contexto
            
        Returns:
            Lista formatada para o modelo de IA (role + content)
        """
        try:
            messages = self.get_conversation_history(session_id, limit=context_limit)
            
            # Converte para formato do modelo de IA
            ai_context = []
            for msg in messages:
                ai_message = {
                    'role': 'user' if msg['role'] == 'user' else 'assistant',
                    'content': msg['message']
                }
                ai_context.append(ai_message)
            
            logger.debug(f"🤖 Contexto de IA preparado para sessão {session_id}: {len(ai_context)} mensagens")
            return ai_context
            
        except Exception as e:
            logger.error(f"❌ Erro ao preparar contexto de IA para sessão {session_id}: {e}")
            return []

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera resumo de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dados do resumo ou None se não encontrado
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT * FROM session_summaries WHERE session_id = ?
                    ''', (session_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar resumo da sessão {session_id}: {e}")
            return None

    def update_session_summary(self, session_id: str, summary: str) -> bool:
        """
        Atualiza o resumo de uma sessão.
        
        Args:
            session_id: ID da sessão
            summary: Novo resumo
            
        Returns:
            bool: True se atualizado com sucesso
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        UPDATE session_summaries 
                        SET summary = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE session_id = ?
                    ''', (summary, session_id))
                    
                    conn.commit()
                    
                logger.info(f"📝 Resumo atualizado para sessão {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar resumo da sessão {session_id}: {e}")
            return False

    def clear_session_history(self, session_id: str) -> bool:
        """
        Remove todo o histórico de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            bool: True se removido com sucesso
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Remove mensagens
                    cursor.execute('DELETE FROM conversations WHERE session_id = ?', (session_id,))
                    
                    # Remove resumo
                    cursor.execute('DELETE FROM session_summaries WHERE session_id = ?', (session_id,))
                    
                    conn.commit()
                    
                logger.info(f"🗑️ Histórico removido para sessão {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao remover histórico da sessão {session_id}: {e}")
            return False

    def get_active_sessions(self, days_back: int = 7) -> List[str]:
        """
        Recupera lista de sessões ativas nos últimos dias.
        
        Args:
            days_back: Número de dias para considerar
            
        Returns:
            Lista de session_ids ativos
        """
        try:
            from datetime import timedelta
            
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT DISTINCT session_id 
                        FROM conversations 
                        WHERE timestamp > ?
                        ORDER BY timestamp DESC
                    ''', (cutoff_date,))
                    
                    rows = cursor.fetchall()
                    return [row[0] for row in rows]
                    
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar sessões ativas: {e}")
            return []

    def _update_session_summary(self, cursor, session_id: str, timestamp: str, tokens_used: int):
        """Atualiza resumo da sessão (método interno)."""
        try:
            # Verifica se resumo já existe
            cursor.execute('SELECT session_id FROM session_summaries WHERE session_id = ?', (session_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Atualiza existente
                cursor.execute('''
                    UPDATE session_summaries 
                    SET total_messages = total_messages + 1,
                        total_tokens = total_tokens + ?,
                        last_message_at = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (tokens_used, timestamp, session_id))
            else:
                # Cria novo
                cursor.execute('''
                    INSERT INTO session_summaries 
                    (session_id, total_messages, total_tokens, first_message_at, last_message_at)
                    VALUES (?, 1, ?, ?, ?)
                ''', (session_id, tokens_used, timestamp, timestamp))
                
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar resumo da sessão {session_id}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Recupera estatísticas gerais do banco de conversações.
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Estatísticas básicas
                    cursor.execute('SELECT COUNT(*) FROM conversations')
                    total_messages = cursor.fetchone()[0]
                    
                    cursor.execute('SELECT COUNT(DISTINCT session_id) FROM conversations')
                    total_sessions = cursor.fetchone()[0]
                    
                    cursor.execute('SELECT SUM(tokens_used) FROM conversations')
                    total_tokens = cursor.fetchone()[0] or 0
                    
                    # Mensagens por role
                    cursor.execute('''
                        SELECT role, COUNT(*) 
                        FROM conversations 
                        GROUP BY role
                    ''')
                    messages_by_role = dict(cursor.fetchall())
                    
                    return {
                        'total_messages': total_messages,
                        'total_sessions': total_sessions,
                        'total_tokens': total_tokens,
                        'messages_by_role': messages_by_role,
                        'database_path': self.db_path
                    }
                    
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar estatísticas: {e}")
            return {}

# Instância global para facilitar o uso
conversation_memory = ConversationMemory()