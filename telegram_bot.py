#!/usr/bin/env python3
"""
Bot Telegram Modulare con Editor Integrato
Un bot completamente configurabile con navigazione a pulsanti e database JSON
"""

# =============================================================================
# CONFIGURAZIONE BOT
# =============================================================================
# Inserisci qui il token del tuo bot Telegram ottenuto da @BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# =============================================================================
# IMPORTS
# =============================================================================

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Configurazione logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBotEditor:
    """Classe principale per il bot Telegram con editor integrato"""
    
    def __init__(self, token: str):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.database_file = "bot_database.json"
        self.users_file = "users_database.json"
        self.analytics_file = "analytics_database.json"
        self.admin_users = set()
        self.editor_mode = {}
        self.button_counter = 0  # Contatore per ID univoci pulsanti
        self.user_states = {}  # Gestione stati utenti con timestamp
        
        # Carica database esistente
        self.load_database()
        self.load_users_database()
        self.load_analytics_database()
        
        # Sincronizza sistemi admin
        self._sync_admin_users()
        
        # Inizializza contatore pulsanti
        self._initialize_button_counter()
        
        # Setup handlers
        self.setup_handlers()
    
    def _initialize_button_counter(self):
        """Inizializza il contatore pulsanti basato sui pulsanti esistenti"""
        max_id = 0
        for page in self.database.get('pages', {}).values():
            for button in page.get('buttons', []):
                if 'id' in button:
                    try:
                        button_id = int(button['id'])
                        max_id = max(max_id, button_id)
                    except (ValueError, TypeError):
                        pass
        self.button_counter = max_id + 1
    
    def _generate_button_id(self) -> str:
        """Genera un ID univoco per un pulsante"""
        button_id = f"btn_{self.button_counter}"
        self.button_counter += 1
        return button_id
    
    def _find_button_by_id(self, button_id: str):
        """Trova un pulsante per ID e restituisce (page_id, button)"""
        for page_id, page_data in self.database.get('pages', {}).items():
            for button in page_data.get('buttons', []):
                if button.get('id') == button_id:
                    return page_id, button
        return None
    
    def _set_user_state(self, user_id: int, state: str, data: dict = None):
        """Imposta lo stato di un utente con timestamp"""
        self.user_states[user_id] = {
            'state': state,
            'timestamp': datetime.now(),
            'data': data or {}
        }
    
    def _get_user_state(self, user_id: int) -> str:
        """Ottiene lo stato corrente di un utente"""
        if user_id in self.user_states:
            return self.user_states[user_id]['state']
        return 'waiting'
    
    def _clear_user_state(self, user_id: int):
        """Pulisce lo stato di un utente"""
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    def _cleanup_expired_states(self, timeout_minutes: int = 30):
        """Pulisce gli stati scaduti"""
        current_time = datetime.now()
        expired_users = []
        
        for user_id, state_data in self.user_states.items():
            if (current_time - state_data['timestamp']).total_seconds() > timeout_minutes * 60:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.user_states[user_id]
            if user_id in self.editor_mode:
                del self.editor_mode[user_id]
            logger.info(f"Stato scaduto per utente {user_id}")
    
    def _is_state_valid(self, user_id: int, expected_state: str) -> bool:
        """Verifica se lo stato dell'utente è valido"""
        if user_id not in self.user_states:
            return False
        
        current_state = self.user_states[user_id]['state']
        return current_state == expected_state
    
    def _validate_page_id(self, page_id: str) -> bool:
        """Valida un ID pagina"""
        if not page_id or not isinstance(page_id, str):
            return False
        # Controlla caratteri validi (alfanumerici, underscore, trattini)
        return bool(page_id.replace('_', '').replace('-', '').isalnum())
    
    def _validate_button_text(self, text: str) -> tuple[bool, str]:
        """Valida il testo di un pulsante"""
        if not text or not isinstance(text, str):
            return False, "Testo pulsante non valido"
        
        if len(text.strip()) == 0:
            return False, "Testo pulsante vuoto"
        
        if len(text) > 64:
            return False, "Testo pulsante troppo lungo (max 64 caratteri)"
        
        return True, ""
    
    def _validate_action(self, action: str) -> tuple[bool, str]:
        """Valida un'azione"""
        if not action or not isinstance(action, str):
            return False, "Azione non valida"
        
        if len(action.strip()) == 0:
            return False, "Azione vuota"
        
        if len(action) > 128:
            return False, "Azione troppo lunga (max 128 caratteri)"
        
        return True, ""
    
    def _validate_content(self, content: str, max_length: int = 4096) -> tuple[bool, str]:
        """Valida contenuto generico"""
        if not content or not isinstance(content, str):
            return False, "Contenuto non valido"
        
        if len(content.strip()) == 0:
            return False, "Contenuto vuoto"
        
        if len(content) > max_length:
            return False, f"Contenuto troppo lungo (max {max_length} caratteri)"
        
        return True, ""
    
    def _sanitize_input(self, text: str) -> str:
        """Pulisce l'input dell'utente"""
        if not text:
            return ""
        
        # Rimuovi caratteri di controllo
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Limita lunghezza
        return text[:4096]
    
    async def _handle_validation_error(self, update: Update, error_message: str):
        """Gestisce errori di validazione"""
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(f"❌ {error_message}")
            else:
                await update.message.reply_text(f"❌ {error_message}")
        except Exception as e:
            logger.error(f"Errore nel gestire errore validazione: {e}")
    
    async def _handle_general_error(self, update: Update, error: Exception, context: str = ""):
        """Gestisce errori generali"""
        logger.error(f"Errore {context}: {error}")
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "❌ Si è verificato un errore. Riprova più tardi."
                )
            else:
                await update.message.reply_text(
                    "❌ Si è verificato un errore. Riprova più tardi."
                )
        except Exception as e:
            logger.error(f"Errore nel gestire errore generale: {e}")
    
    def load_database(self):
        """Carica il database JSON"""
        try:
            if os.path.exists(self.database_file):
                with open(self.database_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.database = data.get('database', {})
                    self.admin_users = set(data.get('admin_users', []))
            else:
                self.database = {
                    'pages': {},
                    'buttons': {},
                    'actions': {},
                    'settings': {
                        'welcome_message': 'Benvenuto! Usa i pulsanti per navigare.',
                        'main_menu': 'main'
                    }
                }
                self.save_database()
        except Exception as e:
            logger.error(f"Errore nel caricamento database: {e}")
            self.database = {
                'pages': {},
                'buttons': {},
                'actions': {},
                'settings': {
                    'welcome_message': 'Benvenuto! Usa i pulsanti per navigare.',
                    'main_menu': 'main'
                }
            }
    
    def save_database(self):
        """Salva il database JSON"""
        try:
            data = {
                'database': self.database,
                'admin_users': list(self.admin_users),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.database_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Errore nel salvataggio database: {e}")
    
    def load_users_database(self):
        """Carica il database utenti"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.users_database = json.load(f)
            else:
                self.users_database = {
                    'users': {},
                    'roles': {
                        'user': {'permissions': ['view_pages']},
                        'staff': {'permissions': ['view_pages', 'edit_content', 'view_analytics']},
                        'admin': {'permissions': ['all']}
                    },
                    'last_updated': datetime.now().isoformat()
                }
                self.save_users_database()
        except Exception as e:
            logger.error(f"Errore nel caricamento database utenti: {e}")
            self.users_database = {
                'users': {},
                'roles': {
                    'user': {'permissions': ['view_pages']},
                    'staff': {'permissions': ['view_pages', 'edit_content', 'view_analytics']},
                    'admin': {'permissions': ['all']}
                },
                'last_updated': datetime.now().isoformat()
            }
    
    def save_users_database(self):
        """Salva il database utenti"""
        try:
            self.users_database['last_updated'] = datetime.now().isoformat()
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users_database, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Errore nel salvataggio database utenti: {e}")
    
    def load_analytics_database(self):
        """Carica il database analytics"""
        try:
            if os.path.exists(self.analytics_file):
                with open(self.analytics_file, 'r', encoding='utf-8') as f:
                    self.analytics_database = json.load(f)
            else:
                self.analytics_database = {
                    'page_views': {},
                    'button_clicks': {},
                    'user_activity': {},
                    'daily_stats': {},
                    'last_updated': datetime.now().isoformat()
                }
                self.save_analytics_database()
        except Exception as e:
            logger.error(f"Errore nel caricamento database analytics: {e}")
            self.analytics_database = {
                'page_views': {},
                'button_clicks': {},
                'user_activity': {},
                'daily_stats': {},
                'last_updated': datetime.now().isoformat()
            }
    
    def save_analytics_database(self):
        """Salva il database analytics"""
        try:
            self.analytics_database['last_updated'] = datetime.now().isoformat()
            with open(self.analytics_file, 'w', encoding='utf-8') as f:
                json.dump(self.analytics_database, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Errore nel salvataggio database analytics: {e}")
    
    def register_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None, role: str = 'user'):
        """Registra un nuovo utente"""
        if str(user_id) not in self.users_database['users']:
            self.users_database['users'][str(user_id)] = {
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'role': role,
                'registered_at': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'total_interactions': 0,
                'pages_visited': [],
                'buttons_clicked': []
            }
            self.save_users_database()
            logger.info(f"Nuovo utente registrato: {user_id} ({username})")
    
    def update_user_activity(self, user_id: int, action: str, data: dict = None):
        """Aggiorna l'attività dell'utente con ottimizzazioni"""
        try:
            user_id_str = str(user_id)
            if user_id_str not in self.users_database['users']:
                return
            
            user = self.users_database['users'][user_id_str]
            current_time = datetime.now().isoformat()
            user['last_seen'] = current_time
            user['total_interactions'] = user.get('total_interactions', 0) + 1
            
            # Aggiorna contatori specifici per azione
            if action == 'page_view':
                self._track_page_view(user, data, current_time)
            elif action == 'button_click':
                self._track_button_click(user, data, current_time)
            elif action == 'command_used':
                self._track_command_usage(user, data, current_time)
            
            # Salva solo se necessario (evita salvataggi eccessivi)
            self._schedule_database_save()
            
        except Exception as e:
            logger.error(f"Errore nel tracking attività utente {user_id}: {e}")
    
    def _track_page_view(self, user: dict, data: dict, timestamp: str):
        """Traccia visualizzazione pagina"""
        page_id = data.get('page_id')
        if not page_id:
            return
        
        # Aggiorna lista pagine visitate (max 50 per evitare overflow)
        pages_visited = user.get('pages_visited', [])
        if page_id not in pages_visited:
            pages_visited.append(page_id)
            if len(pages_visited) > 50:
                pages_visited.pop(0)  # Rimuovi il più vecchio
            user['pages_visited'] = pages_visited
        
        # Aggiorna contatori globali
        if page_id not in self.analytics_database['page_views']:
            self.analytics_database['page_views'][page_id] = 0
        self.analytics_database['page_views'][page_id] += 1
            
    def _track_button_click(self, user: dict, data: dict, timestamp: str):
        """Traccia clic pulsante"""
        button_text = data.get('button_text', 'unknown')
        if not button_text:
            return
        
        # Aggiorna lista pulsanti cliccati (max 100)
        buttons_clicked = user.get('buttons_clicked', [])
        if button_text not in buttons_clicked:
            buttons_clicked.append(button_text)
            if len(buttons_clicked) > 100:
                buttons_clicked.pop(0)
            user['buttons_clicked'] = buttons_clicked
        
        # Aggiorna contatori globali
        if button_text not in self.analytics_database['button_clicks']:
            self.analytics_database['button_clicks'][button_text] = 0
        self.analytics_database['button_clicks'][button_text] += 1
        
    def _track_command_usage(self, user: dict, data: dict, timestamp: str):
        """Traccia uso comandi"""
        command = data.get('command', 'unknown')
        if not command:
            return
        
        # Aggiorna contatori comandi
        commands_used = user.get('commands_used', {})
        commands_used[command] = commands_used.get(command, 0) + 1
        user['commands_used'] = commands_used
    
    def _schedule_database_save(self):
        """Programma il salvataggio del database (debouncing)"""
        # Implementa un sistema di debouncing per evitare troppi salvataggi
        if not hasattr(self, '_save_timer'):
            self._save_timer = None
        
        # Se c'è già un timer, non crearne un altro
        if self._save_timer is not None:
            return
        
        # Programma il salvataggio tra 5 secondi
        import threading
        def delayed_save():
            import time
            time.sleep(5)
            try:
                self.save_users_database()
                self.save_analytics_database()
            except Exception as e:
                logger.error(f"Errore nel salvataggio ritardato: {e}")
            finally:
                self._save_timer = None
        
        self._save_timer = threading.Thread(target=delayed_save, daemon=True)
        self._save_timer.start()
    
    def get_user_role(self, user_id: int) -> str:
        """Ottiene il ruolo di un utente"""
        user_id_str = str(user_id)
        if user_id_str in self.users_database['users']:
            return self.users_database['users'][user_id_str]['role']
        return 'user'
    
    def set_user_role(self, user_id: int, role: str):
        """Imposta il ruolo di un utente"""
        user_id_str = str(user_id)
        if user_id_str in self.users_database['users']:
            self.users_database['users'][user_id_str]['role'] = role
            self.save_users_database()
            
            # Sincronizza con admin_users
            self._sync_admin_users()
            
            logger.info(f"Ruolo utente {user_id} cambiato a: {role}")
    
    def _sync_admin_users(self):
        """Sincronizza admin_users con il sistema ruoli"""
        # Trova tutti gli utenti con ruolo admin
        admin_users_from_roles = set()
        for user_id_str, user_data in self.users_database['users'].items():
            if user_data.get('role') == 'admin':
                admin_users_from_roles.add(int(user_id_str))
        
        # Aggiorna admin_users
        self.admin_users = admin_users_from_roles
        
        # Salva nel database principale
        self.save_database()
    
    def has_permission(self, user_id: int, permission: str) -> bool:
        """Verifica se un utente ha un permesso"""
        role = self.get_user_role(user_id)
        if role == 'admin':
            return True
        if role in self.users_database['roles']:
            permissions = self.users_database['roles'][role]['permissions']
            return 'all' in permissions or permission in permissions
        return False
    
    def is_admin(self, user_id: int) -> bool:
        """Verifica se l'utente è admin"""
        # Controlla sia il sistema admin_users che il sistema ruoli
        return (user_id in self.admin_users or 
                self.get_user_role(user_id) == 'admin')
    
    def setup_handlers(self):
        """Configura tutti i gestori di comandi e messaggi"""
        # Comandi base
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("admin", self.admin_command))
        self.app.add_handler(CommandHandler("editor", self.editor_command))
        self.app.add_handler(CommandHandler("analytics", self.analytics_command))
        self.app.add_handler(CommandHandler("users", self.users_command))
        
        # Gestori per editor
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Gestore errori globale
        self.app.add_error_handler(self.error_handler)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestore errori globale"""
        logger.error(f"Errore non gestito: {context.error}")
        
        # Invia messaggio di errore all'utente se possibile
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Si è verificato un errore. Riprova più tardi."
                )
        except Exception as e:
            logger.error(f"Errore nel gestore errori: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        user_id = update.effective_user.id
        user = update.effective_user
        
        # Tracking comando
        self.update_user_activity(user_id, 'command_used', {'command': 'start'})
        
        # Registra l'utente se non esiste
        self.register_user(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            role='user'
        )
        
        # Se è la prima volta, aggiungi come admin
        if not self.admin_users:
            self.admin_users.add(user_id)
            self.set_user_role(user_id, 'admin')
            self.save_database()
            await update.message.reply_text(
                "🎉 Benvenuto! Sei stato automaticamente aggiunto come amministratore.\n"
                "Usa /editor per configurare il bot.\n"
                "Usa /analytics per vedere le statistiche."
            )
            return
        
        # Aggiorna attività utente
        self.update_user_activity(user_id, 'page_view', {'page_id': 'main'})
        
        # Mostra menu principale
        await self.show_page(update, context, 'main')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        help_text = """
🤖 **Bot Telegram Modulare**

**Comandi disponibili:**
/start - Avvia il bot
/help - Mostra questo messaggio
/admin - Pannello amministratore
/editor - Editor configurazione

**Per amministratori:**
- Usa /editor per configurare pagine e pulsanti
- Crea pagine con contenuti personalizzati
- Aggiungi pulsanti con azioni personalizzate
- Gestisci la navigazione del bot

**Navigazione:**
- Usa i pulsanti per navigare tra le pagine
- Ogni pulsante può avere azioni personalizzate
- Il bot ricorda la tua posizione
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def analytics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /analytics"""
        user_id = update.effective_user.id
        
        if not self.has_permission(user_id, 'view_analytics'):
            if update.message:
                await update.message.reply_text("❌ Non hai i permessi per visualizzare le analytics.")
            else:
                await update.callback_query.edit_message_text("❌ Non hai i permessi per visualizzare le analytics.")
            return
        
        # Calcola statistiche
        total_users = len(self.users_database['users'])
        total_page_views = sum(self.analytics_database['page_views'].values())
        total_button_clicks = sum(self.analytics_database['button_clicks'].values())
        
        # Pulsanti più cliccati
        top_buttons = sorted(
            self.analytics_database['button_clicks'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Pagine più visitate
        top_pages = sorted(
            self.analytics_database['page_views'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Utenti attivi (ultimi 7 giorni)
        active_users = 0
        seven_days_ago = datetime.now().timestamp() - (7 * 24 * 60 * 60)
        for user_data in self.users_database['users'].values():
            last_seen = datetime.fromisoformat(user_data['last_seen']).timestamp()
            if last_seen > seven_days_ago:
                active_users += 1
        
        text = f"""
📊 **Analytics Bot**

**👥 Utenti:**
• Totale: {total_users}
• Attivi (7 giorni): {active_users}

**📈 Interazioni:**
• Visualizzazioni pagine: {total_page_views}
• Clic pulsanti: {total_button_clicks}

**🔥 Pulsanti più cliccati:**
"""
        
        for i, (button, clicks) in enumerate(top_buttons, 1):
            text += f"{i}. {button}: {clicks} clic\n"
        
        text += "\n**📄 Pagine più visitate:**\n"
        for i, (page_id, views) in enumerate(top_pages, 1):
            page_title = self.database['pages'].get(page_id, {}).get('title', page_id)
            text += f"{i}. {page_title}: {views} visite\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Report Dettagliato", callback_data="analytics_detailed")],
            [InlineKeyboardButton("👥 Gestione Utenti", callback_data="users_manage")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /users"""
        try:
            user_id = update.effective_user.id
            
            if not self.has_permission(user_id, 'view_analytics'):
                if update.message:
                    await update.message.reply_text("❌ Non hai i permessi per visualizzare gli utenti.")
                else:
                    await update.callback_query.edit_message_text("❌ Non hai i permessi per visualizzare gli utenti.")
                return
        
            users = self.users_database['users']
            total_users = len(users)
            
            # Conta utenti per ruolo
            role_counts = {'user': 0, 'staff': 0, 'admin': 0}
            for user_data in users.values():
                role = user_data.get('role', 'user')
                if role in role_counts:
                    role_counts[role] += 1
            
            text = f"""
👥 **Gestione Utenti**

**📊 Statistiche:**
• Totale utenti: {total_users}
• Utenti: {role_counts['user']}
• Staff: {role_counts['staff']}
• Admin: {role_counts['admin']}

**🔍 Ultimi 5 utenti registrati:**
"""
            
            # Ultimi 5 utenti
            sorted_users = sorted(
                users.items(),
                key=lambda x: x[1]['registered_at'],
                reverse=True
            )[:5]
            
            for user_id_str, user_data in sorted_users:
                username = user_data.get('username', 'N/A')
                role = user_data.get('role', 'user')
                # Escape caratteri speciali per Markdown
                username_escaped = username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
                text += f"• @{username_escaped} ({role})\n"
            
            keyboard = [
                [InlineKeyboardButton("👥 Lista Completa", callback_data="users_list")],
                [InlineKeyboardButton("🔍 Cerca Utente", callback_data="users_search")],
                [InlineKeyboardButton("📊 Analytics", callback_data="analytics_detailed")],
                [InlineKeyboardButton("🔙 Indietro", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.message:
                await update.message.reply_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.callback_query.edit_message_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logger.error(f"Errore nel comando users: {e}")
            if update.message:
                await update.message.reply_text("❌ Errore nel caricamento della gestione utenti.")
            else:
                await update.callback_query.edit_message_text("❌ Errore nel caricamento della gestione utenti.")
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /admin"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            if update.message:
                await update.message.reply_text("❌ Non hai i permessi per accedere al pannello admin.")
            else:
                await update.callback_query.edit_message_text("❌ Non hai i permessi per accedere al pannello admin.")
            return
        
        keyboard = [
            [InlineKeyboardButton("📝 Editor Pagine", callback_data="admin_editor")],
            [InlineKeyboardButton("📊 Analytics", callback_data="admin_analytics")],
            [InlineKeyboardButton("👥 Gestione Utenti", callback_data="admin_users_manage")],
            [InlineKeyboardButton("⚙️ Impostazioni", callback_data="admin_settings")],
            [InlineKeyboardButton("📈 Statistiche", callback_data="admin_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                "🔧 **Pannello Amministratore**\n\n"
                "Scegli un'opzione dal menu:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.callback_query.edit_message_text(
                "🔧 **Pannello Amministratore**\n\n"
                "Scegli un'opzione dal menu:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def editor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /editor"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            if update.message:
                await update.message.reply_text("❌ Non hai i permessi per accedere all'editor.")
            else:
                await update.callback_query.edit_message_text("❌ Non hai i permessi per accedere all'editor.")
            return
        
        self.editor_mode[user_id] = True
        
        keyboard = [
            [InlineKeyboardButton("📄 Crea Pagina", callback_data="editor_create_page")],
            [InlineKeyboardButton("✏️ Modifica Pagina", callback_data="editor_edit_page")],
            [InlineKeyboardButton("🔘 Gestisci Pulsanti", callback_data="editor_buttons")],
            [InlineKeyboardButton("⚡ Gestisci Azioni", callback_data="editor_actions")],
            [InlineKeyboardButton("🏠 Menu Principale", callback_data="editor_main_menu")],
            [InlineKeyboardButton("📊 Analytics", callback_data="admin_analytics")],
            [InlineKeyboardButton("👥 Utenti", callback_data="admin_users_manage")],
            [InlineKeyboardButton("❌ Esci Editor", callback_data="editor_exit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                "🎨 **Editor Configurazione**\n\n"
                "Benvenuto nell'editor! Scegli cosa vuoi fare:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.callback_query.edit_message_text(
                "🎨 **Editor Configurazione**\n\n"
                "Benvenuto nell'editor! Scegli cosa vuoi fare:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce i messaggi di testo"""
        user_id = update.effective_user.id
        
        # Se l'utente è in modalità editor
        if user_id in self.editor_mode and self.editor_mode[user_id]:
            await self.handle_editor_message(update, context)
            return
        
        # Gestione normale dei messaggi
        await self.show_page(update, context, 'main')
    
    async def handle_editor_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce i messaggi durante la modalità editor"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # Pulisci stati scaduti
        self._cleanup_expired_states()
        
        # Controlla se l'utente sta cercando un utente
        if context.user_data.get(f"searching_user_{user_id}"):
            await self.search_user(update, context, text)
            return
        
        # Ottieni stato corrente
        state = self._get_user_state(user_id)
        
        # Verifica validità stato
        if not self._is_state_valid(user_id, state):
            await update.message.reply_text("❌ Stato non valido. Usa i pulsanti dell'editor per navigare.")
            self._clear_user_state(user_id)
            return
        
        # Gestisci i diversi stati
        if state == "creating_page":
            await self.create_page_from_text(update, context, text)
        elif state == "editing_page":
            await self.edit_page_from_text(update, context, text)
        elif state == "creating_button":
            await self.create_button_from_text(update, context, text)
        elif state == "editing_button":
            await self.edit_button_from_text(update, context, text)
        elif state == "creating_action":
            await self.create_action_from_text(update, context, text)
        elif state == "editing_action":
            await self.edit_action_from_text(update, context, text)
        elif state == "editing_welcome":
            await self.edit_welcome_from_text(update, context, text)
        elif state == "adding_admin":
            await self.add_admin_from_text(update, context, text)
        else:
            await update.message.reply_text("Usa i pulsanti dell'editor per navigare.")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce i callback dei pulsanti inline"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            data = query.data
            
            logger.info(f"Callback ricevuto: {data} da utente {user_id}")
            
            # Routing migliorato con priorità specifiche
            if data.startswith("admin_"):
                await self.handle_admin_callback(update, context, data)
            elif data.startswith("analytics_"):
                await self.handle_analytics_callback(update, context, data)
            elif data.startswith("users_"):
                await self.handle_users_callback(update, context, data)
            elif (data.startswith("editor_") or data.startswith("edit_") or 
                data.startswith("manage_") or data.startswith("add_") or 
                data.startswith("delete_") or data.startswith("create_") or 
                data.startswith("list_") or data.startswith("set_") or
                data.startswith("user_") or data.startswith("change_") or
                data == "admin_back"):
                await self.handle_editor_callback(update, context, data)
            elif data.startswith("page_") or data == "back_to_main":
                await self.handle_navigation_callback(update, context, data)
            else:
                # Gestione azioni personalizzate
                await self.handle_custom_action(update, context, data)
                
        except Exception as e:
            logger.error(f"Errore nel gestione callback: {e}")
            try:
                await update.callback_query.edit_message_text(
                    "❌ Errore nel gestione del comando. Riprova."
                )
            except:
                pass
    
    async def handle_editor_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Gestisce i callback dell'editor"""
        try:
            user_id = update.effective_user.id
            
            if data == "editor_create_page":
                await self.start_create_page(update, context)
            elif data == "editor_edit_page":
                await self.start_edit_page(update, context)
            elif data == "editor_buttons":
                await self.manage_buttons(update, context)
            elif data == "editor_actions":
                await self.manage_actions(update, context)
            elif data == "editor_main_menu":
                await self.set_main_menu(update, context)
            elif data == "editor_exit":
                self.editor_mode[user_id] = False
                await update.callback_query.edit_message_text("✅ Editor chiuso.")
            elif data.startswith("edit_page_"):
                page_id = data.replace("edit_page_", "")
                await self.start_edit_specific_page(update, context, page_id)
            elif data.startswith("manage_buttons_"):
                page_id = data.replace("manage_buttons_", "")
                await self.manage_page_buttons(update, context, page_id)
            elif data.startswith("set_main_"):
                page_id = data.replace("set_main_", "")
                await self.set_main_menu_page(update, context, page_id)
            elif data.startswith("add_button_"):
                page_id = data.replace("add_button_", "")
                await self.start_add_button(update, context, page_id)
            elif data.startswith("edit_button_"):
                button_id = data.replace("edit_button_", "")
                await self.start_edit_button(update, context, button_id)
            elif data.startswith("delete_button_"):
                button_id = data.replace("delete_button_", "")
                await self.delete_button(update, context, button_id)
            elif data.startswith("edit_action_"):
                action_id = data.replace("edit_action_", "")
                await self.start_edit_action(update, context, action_id)
            elif data.startswith("delete_action_"):
                action_id = data.replace("delete_action_", "")
                await self.delete_action(update, context, action_id)
            elif data == "create_action":
                await self.start_create_action(update, context)
            elif data == "list_actions":
                await self.list_actions(update, context)
            elif data == "admin_back":
                await self.admin_command(update, context)
            else:
                # Callback non riconosciuto
                await update.callback_query.edit_message_text(
                    f"❌ Callback non riconosciuto: {data}\n\nUsa i pulsanti dell'editor per navigare."
                )
        except Exception as e:
            logger.error(f"Errore nel gestione editor callback: {e}")
            try:
                await update.callback_query.edit_message_text(
                    "❌ Errore nel gestione del comando. Riprova."
                )
            except:
                pass
    
    async def start_create_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inizia la creazione di una nuova pagina"""
        user_id = update.effective_user.id
        self._set_user_state(user_id, "creating_page")
        
        await update.callback_query.edit_message_text(
            "📄 **Crea Nuova Pagina**\n\n"
            "Invia il contenuto della pagina nel formato:\n"
            "`ID_PAGINA|Titolo|Contenuto`\n\n"
            "Esempio: `about|Chi Siamo|Siamo un team di sviluppatori...`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def create_page_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Crea una pagina dal testo inviato con validazione"""
        user_id = update.effective_user.id
        
        try:
            # Pulisci input
            text = self._sanitize_input(text)
            
            parts = text.split('|', 2)
            if len(parts) != 3:
                await self._handle_validation_error(update, "Formato non valido. Usa: ID_PAGINA|Titolo|Contenuto")
                return
            
            page_id, title, content = parts
            
            # Valida input
            if not self._validate_page_id(page_id.strip()):
                await self._handle_validation_error(update, "ID pagina non valido. Usa solo lettere, numeri, underscore e trattini.")
                return
            
            is_valid_title, title_error = self._validate_content(title.strip(), 100)
            if not is_valid_title:
                await self._handle_validation_error(update, f"Titolo non valido: {title_error}")
                return
            
            is_valid_content, content_error = self._validate_content(content.strip())
            if not is_valid_content:
                await self._handle_validation_error(update, f"Contenuto non valido: {content_error}")
                return
            
            # Controlla se la pagina esiste già
            if page_id.strip() in self.database.get('pages', {}):
                await self._handle_validation_error(update, "Una pagina con questo ID esiste già.")
                return
            
            # Crea la pagina
            self.database['pages'][page_id.strip()] = {
                'title': title.strip(),
                'content': content.strip(),
                'buttons': [],
                'created_at': datetime.now().isoformat()
            }
            
            self.save_database()
            self._clear_user_state(user_id)
            
            await update.message.reply_text(
                f"✅ Pagina '{title.strip()}' creata con successo!\n"
                f"ID: `{page_id.strip()}`",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await self._handle_general_error(update, e, "creazione pagina")
    
    async def start_edit_specific_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page_id: str):
        """Inizia la modifica di una pagina specifica"""
        user_id = update.effective_user.id
        
        if page_id not in self.database['pages']:
            await update.callback_query.edit_message_text("❌ Pagina non trovata.")
            return
        
        page = self.database['pages'][page_id]
        context.user_data[f"editing_page_{user_id}"] = page_id
        self._set_user_state(user_id, "editing_page", {'page_id': page_id})
        
        await update.callback_query.edit_message_text(
            f"✏️ **Modifica Pagina: {page['title']}**\n\n"
            f"**Contenuto attuale:**\n{page['content']}\n\n"
            f"Invia il nuovo contenuto nel formato:\n"
            f"`NUOVO_TITOLO|NUOVO_CONTENUTO`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def edit_page_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Modifica una pagina dal testo inviato"""
        user_id = update.effective_user.id
        
        try:
            parts = text.split('|', 1)
            if len(parts) != 2:
                await update.message.reply_text(
                    "❌ Formato non valido. Usa: `NUOVO_TITOLO|NUOVO_CONTENUTO`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            title, content = parts
            page_id = context.user_data.get(f"editing_page_{user_id}")
            
            if not page_id or page_id not in self.database['pages']:
                await update.message.reply_text("❌ Pagina non trovata.")
                return
            
            # Aggiorna la pagina
            self.database['pages'][page_id]['title'] = title.strip()
            self.database['pages'][page_id]['content'] = content.strip()
            self.database['pages'][page_id]['updated_at'] = datetime.now().isoformat()
            
            self.save_database()
            self._clear_user_state(user_id)
            del context.user_data[f"editing_page_{user_id}"]
            
            await update.message.reply_text(
                f"✅ Pagina '{title}' aggiornata con successo!",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Errore nella modifica: {e}")
    
    async def manage_page_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page_id: str):
        """Gestisce i pulsanti di una pagina specifica"""
        if page_id not in self.database['pages']:
            await update.callback_query.edit_message_text("❌ Pagina non trovata.")
            return
        
        page = self.database['pages'][page_id]
        buttons = page.get('buttons', [])
        
        text = f"🔘 **Pulsanti per: {page['title']}**\n\n"
        
        if not buttons:
            text += "Nessun pulsante presente.\n"
        else:
            for i, button in enumerate(buttons):
                button_id = button.get('id', f'btn_{i}')
                text += f"{i+1}. {button['text']} → {button['action']} (ID: {button_id})\n"
        
        keyboard = []
        keyboard.append([InlineKeyboardButton("➕ Aggiungi Pulsante", callback_data=f"add_button_{page_id}")])
        
        for i, button in enumerate(buttons):
            button_id = button.get('id', f'btn_{i}')
            keyboard.append([
                InlineKeyboardButton(f"✏️ {button['text']}", callback_data=f"edit_button_{button_id}"),
                InlineKeyboardButton("🗑️", callback_data=f"delete_button_{button_id}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="editor_buttons")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def start_add_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page_id: str):
        """Inizia l'aggiunta di un pulsante"""
        user_id = update.effective_user.id
        context.user_data[f"adding_button_{user_id}"] = page_id
        self._set_user_state(user_id, "creating_button", {'page_id': page_id})
        
        await update.callback_query.edit_message_text(
            f"➕ **Aggiungi Pulsante a: {self.database['pages'][page_id]['title']}**\n\n"
            f"Invia il pulsante nel formato:\n"
            f"`TESTO_PULSANTE|AZIONE`\n\n"
            f"Esempi di azioni:\n"
            f"- `page_about` (va alla pagina about)\n"
            f"- `action_contact` (esegue azione contact)\n"
            f"- `back_to_main` (torna al menu principale)",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def create_button_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Crea un pulsante dal testo inviato con validazione"""
        user_id = update.effective_user.id
        
        try:
            # Pulisci input
            text = self._sanitize_input(text)
            
            parts = text.split('|', 1)
            if len(parts) != 2:
                await self._handle_validation_error(update, "Formato non valido. Usa: TESTO_PULSANTE|AZIONE")
                return
            
            button_text, action = parts
            page_id = context.user_data.get(f"adding_button_{user_id}")
            
            if not page_id or page_id not in self.database['pages']:
                await self._handle_validation_error(update, "Pagina non trovata.")
                return
            
            # Valida input
            is_valid_text, text_error = self._validate_button_text(button_text.strip())
            if not is_valid_text:
                await self._handle_validation_error(update, f"Testo pulsante non valido: {text_error}")
                return
            
            is_valid_action, action_error = self._validate_action(action.strip())
            if not is_valid_action:
                await self._handle_validation_error(update, f"Azione non valida: {action_error}")
                return
            
            # Controlla se esiste già un pulsante con lo stesso testo nella pagina
            existing_buttons = self.database['pages'][page_id].get('buttons', [])
            for existing_button in existing_buttons:
                if existing_button['text'].strip() == button_text.strip():
                    await self._handle_validation_error(update, "Un pulsante con questo testo esiste già in questa pagina.")
                    return
            
            # Aggiungi il pulsante con ID univoco
            button = {
                'id': self._generate_button_id(),
                'text': button_text.strip(),
                'action': action.strip(),
                'created_at': datetime.now().isoformat()
            }
            
            if 'buttons' not in self.database['pages'][page_id]:
                self.database['pages'][page_id]['buttons'] = []
            
            self.database['pages'][page_id]['buttons'].append(button)
            self.save_database()
            
            self._clear_user_state(user_id)
            del context.user_data[f"adding_button_{user_id}"]
            
            await update.message.reply_text(
                f"✅ Pulsante '{button_text.strip()}' aggiunto con successo!",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await self._handle_general_error(update, e, "creazione pulsante")
    
    async def edit_welcome_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Modifica il messaggio di benvenuto dal testo inviato"""
        user_id = update.effective_user.id
        
        try:
            # Pulisci input
            text = self._sanitize_input(text)
            
            # Valida contenuto
            is_valid, error = self._validate_content(text.strip(), 1000)
            if not is_valid:
                await self._handle_validation_error(update, f"Messaggio non valido: {error}")
                return
            
            # Aggiorna messaggio di benvenuto
            if 'settings' not in self.database:
                self.database['settings'] = {}
            
            self.database['settings']['welcome_message'] = text.strip()
            self.save_database()
            self._clear_user_state(user_id)
            
            await update.message.reply_text(
                f"✅ Messaggio di benvenuto aggiornato con successo!\n\n"
                f"**Nuovo messaggio:**\n{text.strip()}",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await self._handle_general_error(update, e, "modifica messaggio benvenuto")
    
    async def add_admin_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Aggiunge un amministratore dal testo inviato"""
        user_id = update.effective_user.id
        
        try:
            # Pulisci input
            text = self._sanitize_input(text).strip()
            
            if not text:
                await self._handle_validation_error(update, "Input vuoto.")
                return
            
            # Pulisci username se necessario
            if text.startswith('@'):
                text = text[1:]
            
            # Cerca utente per username o ID
            target_user_id = None
            target_username = None
            
            # Prima prova come ID numerico
            try:
                target_user_id = int(text)
                if str(target_user_id) in self.users_database['users']:
                    target_username = self.users_database['users'][str(target_user_id)].get('username', 'N/A')
            except ValueError:
                # Cerca per username
                for user_id_str, user_data in self.users_database['users'].items():
                    if user_data.get('username', '').lower() == text.lower():
                        target_user_id = int(user_id_str)
                        target_username = user_data.get('username', 'N/A')
                        break
            
            if not target_user_id:
                await self._handle_validation_error(update, f"Utente '{text}' non trovato nel database.")
                return
            
            # Controlla se è già admin
            if target_user_id in self.admin_users:
                await self._handle_validation_error(update, f"L'utente {target_username} è già un amministratore.")
                return
            
            # Aggiungi come admin
            self.set_user_role(target_user_id, 'admin')
            self._clear_user_state(user_id)
            
            await update.message.reply_text(
                f"✅ Amministratore aggiunto con successo!\n\n"
                f"**Utente:** {target_username} (ID: {target_user_id})\n"
                f"**Ruolo:** admin",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await self._handle_general_error(update, e, "aggiunta amministratore")
    
    async def edit_button_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Modifica un pulsante dal testo inviato"""
        user_id = update.effective_user.id
        
        try:
            parts = text.split('|', 1)
            if len(parts) != 2:
                await update.message.reply_text(
                    "❌ Formato non valido. Usa: `NUOVO_TESTO|NUOVA_AZIONE`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            button_text, action = parts
            button_id = context.user_data.get(f"editing_button_{user_id}")
            
            if not button_id:
                await update.message.reply_text("❌ Informazioni pulsante non trovate.")
                return
            
            # Trova il pulsante per ID
            button_data = self._find_button_by_id(button_id)
            if not button_data:
                await update.message.reply_text("❌ Pulsante non trovato.")
                return
            
            page_id, button = button_data
            
            # Aggiorna il pulsante
            button['text'] = button_text.strip()
            button['action'] = action.strip()
            button['updated_at'] = datetime.now().isoformat()
            
            self.save_database()
            self._clear_user_state(user_id)
            del context.user_data[f"editing_button_{user_id}"]
            
            await update.message.reply_text(
                f"✅ Pulsante aggiornato con successo!",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Errore nella modifica: {e}")
    
    async def start_edit_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE, button_id: str):
        """Inizia la modifica di un pulsante"""
        user_id = update.effective_user.id
        
        try:
            # Trova il pulsante per ID
            button_data = self._find_button_by_id(button_id)
            if not button_data:
                await update.callback_query.edit_message_text("❌ Pulsante non trovato.")
                return
            
            page_id, button = button_data
            context.user_data[f"editing_button_{user_id}"] = button_id
            self._set_user_state(user_id, "editing_button", {'button_id': button_id})
            
            await update.callback_query.edit_message_text(
                f"✏️ **Modifica Pulsante**\n\n"
                f"**Pulsante attuale:** {button['text']} → {button['action']}\n"
                f"**ID:** {button_id}\n\n"
                f"Invia il nuovo pulsante nel formato:\n"
                f"`NUOVO_TESTO|NUOVA_AZIONE`",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await update.callback_query.edit_message_text(f"❌ Errore: {e}")
    
    async def delete_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE, button_id: str):
        """Elimina un pulsante"""
        try:
            # Trova il pulsante per ID
            button_data = self._find_button_by_id(button_id)
            if not button_data:
                await update.callback_query.edit_message_text("❌ Pulsante non trovato.")
                return
            
            page_id, button = button_data
            button_text = button['text']
            
            # Rimuovi il pulsante dalla pagina
            buttons = self.database['pages'][page_id]['buttons']
            buttons.remove(button)
            
            self.save_database()
            
            await update.callback_query.edit_message_text(
                f"✅ Pulsante '{button_text}' eliminato con successo!"
            )
            
        except Exception as e:
            await update.callback_query.edit_message_text(f"❌ Errore: {e}")
    
    async def start_create_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inizia la creazione di un'azione"""
        user_id = update.effective_user.id
        self._set_user_state(user_id, "creating_action")
        
        await update.callback_query.edit_message_text(
            "⚡ **Crea Nuova Azione**\n\n"
            "Invia l'azione nel formato:\n"
            "`ID_AZIONE|TIPO|CONTENUTO`\n\n"
            "**Tipi disponibili:**\n"
            "- `message` - Mostra un messaggio\n"
            "- `page` - Va a una pagina (usa ID pagina)\n"
            "- `url` - Apre un link (usa URL completo)\n"
            "- `command` - Esegue comando interno\n\n"
            "**Esempi:**\n"
            "- `contact|message|Contattaci su Telegram: @username`\n"
            "- `go_about|page|about`\n"
            "- `website|url|https://example.com`\n"
            "- `show_stats|command|show_analytics`\n\n"
            "**Variabili disponibili:**\n"
            "- `{user_id}` - ID utente\n"
            "- `{timestamp}` - Data/ora corrente\n"
            "- `{param}` - Parametro per azioni dinamiche",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def create_action_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Crea un'azione dal testo inviato"""
        user_id = update.effective_user.id
        
        try:
            parts = text.split('|', 2)
            if len(parts) != 3:
                await update.message.reply_text(
                    "❌ Formato non valido. Usa: `ID_AZIONE|TIPO|CONTENUTO`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            action_id, action_type, content = parts
            
            if action_type not in ['message', 'page', 'url', 'command']:
                await update.message.reply_text(
                    "❌ Tipo non valido. Usa: message, page, url, o command",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Crea l'azione
            action = {
                'type': action_type.strip(),
                'content': content.strip(),
                'created_at': datetime.now().isoformat()
            }
            
            if action_type == 'url':
                action['url'] = content.strip()
            
            self.database['actions'][action_id.strip()] = action
            self.save_database()
            
            self._clear_user_state(user_id)
            
            await update.message.reply_text(
                f"✅ Azione '{action_id}' creata con successo!",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Errore nella creazione: {e}")
    
    async def list_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista tutte le azioni"""
        actions = self.database.get('actions', {})
        
        if not actions:
            text = "⚡ **Azioni**\n\nNessuna azione presente."
            keyboard = [[InlineKeyboardButton("🔙 Indietro", callback_data="editor_actions")]]
        else:
            text = "⚡ **Azioni Disponibili**\n\n"
            for action_id, action_data in actions.items():
                text += f"• **{action_id}** ({action_data['type']})\n"
                text += f"  {action_data['content'][:50]}...\n\n"
            
            keyboard = []
            for action_id in actions.keys():
                keyboard.append([
                    InlineKeyboardButton(f"✏️ {action_id}", callback_data=f"edit_action_{action_id}"),
                    InlineKeyboardButton("🗑️", callback_data=f"delete_action_{action_id}")
                ])
            keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="editor_actions")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def delete_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_id: str):
        """Elimina un'azione"""
        if action_id not in self.database.get('actions', {}):
            await update.callback_query.edit_message_text("❌ Azione non trovata.")
            return
        
        del self.database['actions'][action_id]
        self.save_database()
        
        await update.callback_query.edit_message_text(
            f"✅ Azione '{action_id}' eliminata con successo!"
        )
    
    async def start_edit_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_id: str):
        """Inizia la modifica di un'azione"""
        user_id = update.effective_user.id
        
        if action_id not in self.database.get('actions', {}):
            await update.callback_query.edit_message_text("❌ Azione non trovata.")
            return
        
        action = self.database['actions'][action_id]
        context.user_data[f"editing_action_{user_id}"] = action_id
        self._set_user_state(user_id, "editing_action", {'action_id': action_id})
        
        await update.callback_query.edit_message_text(
            f"✏️ **Modifica Azione: {action_id}**\n\n"
            f"**Azione attuale:**\n"
            f"Tipo: {action['type']}\n"
            f"Contenuto: {action['content']}\n\n"
            f"Invia la nuova azione nel formato:\n"
            f"`NUOVO_TIPO|NUOVO_CONTENUTO`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def edit_action_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Modifica un'azione dal testo inviato"""
        user_id = update.effective_user.id
        
        try:
            parts = text.split('|', 1)
            if len(parts) != 2:
                await update.message.reply_text(
                    "❌ Formato non valido. Usa: `NUOVO_TIPO|NUOVO_CONTENUTO`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            action_type, content = parts
            action_id = context.user_data.get(f"editing_action_{user_id}")
            
            if not action_id or action_id not in self.database.get('actions', {}):
                await update.message.reply_text("❌ Azione non trovata.")
                return
            
            if action_type not in ['message', 'page', 'url', 'command']:
                await update.message.reply_text(
                    "❌ Tipo non valido. Usa: message, page, url, o command",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Aggiorna l'azione
            self.database['actions'][action_id]['type'] = action_type.strip()
            self.database['actions'][action_id]['content'] = content.strip()
            self.database['actions'][action_id]['updated_at'] = datetime.now().isoformat()
            
            if action_type == 'url':
                self.database['actions'][action_id]['url'] = content.strip()
            
            self.save_database()
            self._clear_user_state(user_id)
            del context.user_data[f"editing_action_{user_id}"]
            
            await update.message.reply_text(
                f"✅ Azione '{action_id}' aggiornata con successo!",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Errore nella modifica: {e}")
    
    async def show_detailed_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra analytics dettagliate"""
        user_id = update.effective_user.id
        
        if not self.has_permission(user_id, 'view_analytics'):
            await update.callback_query.edit_message_text("❌ Non hai i permessi per visualizzare le analytics dettagliate.")
            return
        
        # Statistiche dettagliate
        users = self.users_database['users']
        total_users = len(users)
        
        # Utenti per ruolo
        role_stats = {'user': 0, 'staff': 0, 'admin': 0}
        for user_data in users.values():
            role = user_data.get('role', 'user')
            if role in role_stats:
                role_stats[role] += 1
        
        # Attività per giorno (ultimi 7 giorni)
        daily_activity = {}
        for i in range(7):
            date = datetime.now().date() - timedelta(days=i)
            daily_activity[date.isoformat()] = 0
        
        for user_data in users.values():
            last_seen = datetime.fromisoformat(user_data['last_seen']).date()
            if last_seen in daily_activity:
                daily_activity[last_seen] += 1
        
        # Top 10 pulsanti
        top_buttons = sorted(
            self.analytics_database['button_clicks'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        text = f"""
📊 **Analytics Dettagliate**

**👥 Utenti per Ruolo:**
• Utenti: {role_stats['user']} ({role_stats['user']/total_users*100:.1f}%)
• Staff: {role_stats['staff']} ({role_stats['staff']/total_users*100:.1f}%)
• Admin: {role_stats['admin']} ({role_stats['admin']/total_users*100:.1f}%)

**📅 Attività Ultimi 7 Giorni:**
"""
        
        for date, count in sorted(daily_activity.items(), reverse=True):
            text += f"• {date}: {count} utenti attivi\n"
        
        text += "\n**🔥 Top 10 Pulsanti:**\n"
        for i, (button, clicks) in enumerate(top_buttons, 1):
            text += f"{i}. {button}: {clicks} clic\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Analytics Base", callback_data="analytics_base")],
            [InlineKeyboardButton("👥 Utenti", callback_data="users_manage")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_users_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra lista completa utenti"""
        user_id = update.effective_user.id
        
        if not self.has_permission(user_id, 'view_analytics'):
            await update.callback_query.edit_message_text("❌ Non hai i permessi per visualizzare la lista utenti.")
            return
        
        users = self.users_database['users']
        
        if not users:
            await update.callback_query.edit_message_text("❌ Nessun utente registrato.")
            return
        
        # Pagina utenti (max 10 per volta)
        page = context.user_data.get('users_page', 0)
        users_list = list(users.items())
        start_idx = page * 10
        end_idx = start_idx + 10
        page_users = users_list[start_idx:end_idx]
        
        text = f"👥 **Lista Utenti (Pagina {page + 1})**\n\n"
        
        for user_id_str, user_data in page_users:
            username = user_data.get('username', 'N/A')
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')
            role = user_data.get('role', 'user')
            last_seen = user_data.get('last_seen', 'N/A')
            interactions = user_data.get('total_interactions', 0)
            
            name = f"{first_name} {last_name}".strip() or username
            # Escape caratteri speciali per Markdown
            name_escaped = name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
            username_escaped = username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
            text += f"• **{name_escaped}** (@{username_escaped})\n"
            text += f"  Ruolo: {role} | Interazioni: {interactions}\n"
            text += f"  Ultimo accesso: {last_seen[:10]}\n\n"
        
        keyboard = []
        if page > 0:
            keyboard.append([InlineKeyboardButton("⬅️ Pagina Precedente", callback_data="users_page_prev")])
        if end_idx < len(users_list):
            keyboard.append([InlineKeyboardButton("➡️ Pagina Successiva", callback_data="users_page_next")])
        
        keyboard.extend([
            [InlineKeyboardButton("🔍 Cerca Utente", callback_data="users_search")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="users_manage")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def start_user_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inizia la ricerca di un utente"""
        user_id = update.effective_user.id
        context.user_data[f"searching_user_{user_id}"] = True
        
        await update.callback_query.edit_message_text(
            "🔍 **Cerca Utente**\n\n"
            "Invia l'username o l'ID dell'utente che vuoi cercare.\n"
            "Esempi:\n"
            "• @username\n"
            "• 123456789\n"
            "• nome utente"
        )
    
    async def search_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, search_term: str):
        """Cerca un utente"""
        user_id = update.effective_user.id
        context.user_data[f"searching_user_{user_id}"] = False
        
        users = self.users_database['users']
        found_users = []
        
        # Pulisci il termine di ricerca
        if not search_term:
            await update.message.reply_text("❌ Termine di ricerca non valido.")
            return
            
        search_term = search_term.strip().lower()
        if search_term.startswith('@'):
            search_term = search_term[1:]
        
        # Cerca per username, ID, o nome
        for user_id_str, user_data in users.items():
            username = (user_data.get('username') or '').lower()
            first_name = (user_data.get('first_name') or '').lower()
            last_name = (user_data.get('last_name') or '').lower()
            full_name = f"{first_name} {last_name}".strip().lower()
            
            if (search_term in username or 
                search_term in first_name or 
                search_term in last_name or 
                search_term in full_name or
                search_term == user_id_str):
                found_users.append((user_id_str, user_data))
        
        if not found_users:
            await update.message.reply_text("❌ Nessun utente trovato.")
            return
        
        if len(found_users) == 1:
            # Mostra dettagli utente singolo
            user_id_str, user_data = found_users[0]
            await self.show_user_details(update, context, user_id_str, user_data)
        else:
            # Mostra lista risultati
            search_term_escaped = search_term.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
            text = f"🔍 **Risultati ricerca per '{search_term_escaped}'**\n\n"
            for i, (user_id_str, user_data) in enumerate(found_users[:10], 1):
                username = user_data.get('username', 'N/A')
                first_name = user_data.get('first_name', '')
                last_name = user_data.get('last_name', '')
                role = user_data.get('role', 'user')
                
                name = f"{first_name} {last_name}".strip() or username
                # Escape caratteri speciali per Markdown
                name_escaped = name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
                username_escaped = username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
                text += f"{i}. **{name_escaped}** (@{username_escaped}) - {role}\n"
            
            if len(found_users) > 10:
                text += f"\n... e altri {len(found_users) - 10} risultati"
            
            keyboard = []
            for i, (user_id_str, user_data) in enumerate(found_users[:5], 1):
                username = user_data.get('username', 'N/A')
                # Escape caratteri speciali per il testo del pulsante
                username_escaped = username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
                keyboard.append([InlineKeyboardButton(
                    f"👤 {username_escaped}",
                    callback_data=f"user_details_{user_id_str}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="users_manage")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def show_user_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_str: str, user_data: dict):
        """Mostra dettagli di un utente"""
        username = user_data.get('username', 'N/A')
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        role = user_data.get('role', 'user')
        registered_at = user_data.get('registered_at', 'N/A')
        last_seen = user_data.get('last_seen', 'N/A')
        interactions = user_data.get('total_interactions', 0)
        pages_visited = user_data.get('pages_visited', [])
        buttons_clicked = user_data.get('buttons_clicked', [])
        
        name = f"{first_name} {last_name}".strip() or username
        
        # Escape caratteri speciali per Markdown
        name_escaped = name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
        username_escaped = username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
        
        text = f"""
👤 **Dettagli Utente**

**📋 Informazioni:**
• Nome: {name_escaped}
• Username: @{username_escaped}
• ID: {user_id_str}
• Ruolo: {role}

**📊 Attività:**
• Registrato: {registered_at[:10]}
• Ultimo accesso: {last_seen[:10]}
• Interazioni totali: {interactions}

**📄 Pagine visitate:** {len(pages_visited)}
**🔘 Pulsanti cliccati:** {len(buttons_clicked)}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Cambia Ruolo", callback_data=f"change_role_{user_id_str}")],
            [InlineKeyboardButton("📊 Attività Dettagliata", callback_data=f"user_activity_{user_id_str}")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="users_list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def start_change_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_str: str):
        """Inizia il cambio ruolo di un utente"""
        user_id = update.effective_user.id
        context.user_data[f"changing_role_{user_id}"] = user_id_str
        
        if user_id_str not in self.users_database['users']:
            await update.callback_query.edit_message_text("❌ Utente non trovato.")
            return
        
        user_data = self.users_database['users'][user_id_str]
        current_role = user_data.get('role', 'user')
        
        keyboard = [
            [InlineKeyboardButton("👤 User", callback_data=f"set_role_{user_id_str}_user")],
            [InlineKeyboardButton("👨‍💼 Staff", callback_data=f"set_role_{user_id_str}_staff")],
            [InlineKeyboardButton("👑 Admin", callback_data=f"set_role_{user_id_str}_admin")],
            [InlineKeyboardButton("🔙 Indietro", callback_data=f"user_details_{user_id_str}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            f"🔄 **Cambia Ruolo Utente**\n\n"
            f"Utente: {user_data.get('username', 'N/A')}\n"
            f"Ruolo attuale: {current_role}\n\n"
            f"Scegli il nuovo ruolo:",
            reply_markup=reply_markup
        )
    
    async def show_user_activity(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_str: str):
        """Mostra attività dettagliata di un utente"""
        if user_id_str not in self.users_database['users']:
            await update.callback_query.edit_message_text("❌ Utente non trovato.")
            return
        
        user_data = self.users_database['users'][user_id_str]
        pages_visited = user_data.get('pages_visited', [])
        buttons_clicked = user_data.get('buttons_clicked', [])
        interactions = user_data.get('total_interactions', 0)
        
        username = user_data.get('username', 'N/A')
        # Escape caratteri speciali per Markdown
        username_escaped = username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
        
        text = f"""
📊 **Attività Dettagliata**

**👤 Utente:** {username_escaped}
**📈 Interazioni totali:** {interactions}

**📄 Pagine visitate ({len(pages_visited)}):**
"""
        
        for page_id in pages_visited[:10]:  # Mostra max 10
            page_title = self.database['pages'].get(page_id, {}).get('title', page_id)
            # Escape caratteri speciali per Markdown
            page_title_escaped = page_title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
            text += f"• {page_title_escaped}\n"
        
        if len(pages_visited) > 10:
            text += f"... e altre {len(pages_visited) - 10} pagine\n"
        
        text += f"\n**🔘 Pulsanti cliccati ({len(buttons_clicked)}):**\n"
        for button in buttons_clicked[:10]:  # Mostra max 10
            # Escape caratteri speciali per Markdown
            button_escaped = button.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`').replace('(', '\\(').replace(')', '\\)')
            text += f"• {button_escaped}\n"
        
        if len(buttons_clicked) > 10:
            text += f"... e altri {len(buttons_clicked) - 10} pulsanti\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Indietro", callback_data=f"user_details_{user_id_str}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def change_user_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_str: str, new_role: str):
        """Cambia il ruolo di un utente"""
        if user_id_str not in self.users_database['users']:
            await update.callback_query.edit_message_text("❌ Utente non trovato.")
            return
        
        if new_role not in ['user', 'staff', 'admin']:
            await update.callback_query.edit_message_text("❌ Ruolo non valido.")
            return
        
        # Cambia il ruolo
        self.set_user_role(int(user_id_str), new_role)
        
        user_data = self.users_database['users'][user_id_str]
        username = user_data.get('username', 'N/A')
        
        await update.callback_query.edit_message_text(
            f"✅ Ruolo utente **{username}** cambiato a **{new_role}**",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def set_main_menu_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page_id: str):
        """Imposta una pagina come menu principale"""
        if page_id not in self.database['pages']:
            await update.callback_query.edit_message_text("❌ Pagina non trovata.")
            return
        
        self.database['settings']['main_menu'] = page_id
        self.save_database()
        
        page_title = self.database['pages'][page_id]['title']
        await update.callback_query.edit_message_text(
            f"✅ Menu principale impostato su: **{page_title}**",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def start_edit_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inizia la modifica di una pagina"""
        if not self.database['pages']:
            await update.callback_query.edit_message_text("❌ Nessuna pagina disponibile per la modifica.")
            return
        
        keyboard = []
        for page_id, page_data in self.database['pages'].items():
            keyboard.append([InlineKeyboardButton(
                f"📄 {page_data['title']} ({page_id})",
                callback_data=f"edit_page_{page_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "✏️ **Seleziona Pagina da Modificare**",
            reply_markup=reply_markup
        )
    
    async def manage_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce i pulsanti delle pagine"""
        if not self.database['pages']:
            await update.callback_query.edit_message_text("❌ Nessuna pagina disponibile.")
            return
        
        keyboard = []
        for page_id, page_data in self.database['pages'].items():
            keyboard.append([InlineKeyboardButton(
                f"🔘 {page_data['title']} - Pulsanti",
                callback_data=f"manage_buttons_{page_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "🔘 **Gestisci Pulsanti**\n\nSeleziona una pagina:",
            reply_markup=reply_markup
        )
    
    async def manage_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce le azioni dei pulsanti"""
        keyboard = [
            [InlineKeyboardButton("➕ Crea Azione", callback_data="create_action")],
            [InlineKeyboardButton("📋 Lista Azioni", callback_data="list_actions")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="editor_buttons")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "⚡ **Gestisci Azioni**\n\nScegli un'opzione:",
            reply_markup=reply_markup
        )
    
    async def set_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Imposta il menu principale"""
        if not self.database['pages']:
            await update.callback_query.edit_message_text("❌ Nessuna pagina disponibile.")
            return
        
        keyboard = []
        for page_id, page_data in self.database['pages'].items():
            keyboard.append([InlineKeyboardButton(
                f"🏠 {page_data['title']}",
                callback_data=f"set_main_{page_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "🏠 **Imposta Menu Principale**\n\nSeleziona la pagina principale:",
            reply_markup=reply_markup
        )
    
    async def handle_analytics_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Gestisce i callback delle analytics"""
        try:
            if data == "analytics_detailed":
                await self.show_detailed_analytics(update, context)
            elif data == "analytics_base":
                await self.analytics_command(update, context)
            else:
                await update.callback_query.edit_message_text("❌ Callback analytics non riconosciuto.")
        except Exception as e:
            logger.error(f"Errore nel gestione analytics callback: {e}")
            await update.callback_query.edit_message_text("❌ Errore nel gestione analytics.")

    async def handle_users_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Gestisce i callback della gestione utenti"""
        try:
            if data == "users_list":
                await self.show_users_list(update, context)
            elif data == "users_search":
                await self.start_user_search(update, context)
            elif data == "users_manage":
                await self.users_command(update, context)
            elif data == "users_page_prev":
                context.user_data['users_page'] = max(0, context.user_data.get('users_page', 0) - 1)
                await self.show_users_list(update, context)
            elif data == "users_page_next":
                context.user_data['users_page'] = context.user_data.get('users_page', 0) + 1
                await self.show_users_list(update, context)
            elif data.startswith("user_details_"):
                user_id_str = data.replace("user_details_", "")
                if user_id_str in self.users_database['users']:
                    user_data = self.users_database['users'][user_id_str]
                    await self.show_user_details(update, context, user_id_str, user_data)
                else:
                    await update.callback_query.edit_message_text("❌ Utente non trovato.")
            elif data.startswith("change_role_"):
                user_id_str = data.replace("change_role_", "")
                await self.start_change_role(update, context, user_id_str)
            elif data.startswith("user_activity_"):
                user_id_str = data.replace("user_activity_", "")
                await self.show_user_activity(update, context, user_id_str)
            elif data.startswith("set_role_"):
                parts = data.replace("set_role_", "").split("_", 1)
                if len(parts) == 2:
                    user_id_str, new_role = parts
                    await self.change_user_role(update, context, user_id_str, new_role)
            else:
                await update.callback_query.edit_message_text("❌ Callback utenti non riconosciuto.")
        except Exception as e:
            logger.error(f"Errore nel gestione users callback: {e}")
            await update.callback_query.edit_message_text("❌ Errore nel gestione utenti.")
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Gestisce i callback del pannello admin"""
        try:
            if data == "admin_editor":
                await self.editor_command(update, context)
            elif data == "admin_analytics":
                await self.analytics_command(update, context)
            elif data == "admin_users_manage":
                await self.users_command(update, context)
            elif data == "admin_settings":
                await self.show_settings(update, context)
            elif data == "admin_stats":
                await self.show_stats(update, context)
            elif data == "admin_users":
                await self.manage_users(update, context)
            elif data == "admin_back":
                await self.admin_command(update, context)
            elif data == "edit_welcome":
                await self.start_edit_welcome(update, context)
            elif data == "add_admin":
                await self.start_add_admin(update, context)
            else:
                await update.callback_query.edit_message_text("❌ Callback admin non riconosciuto.")
        except Exception as e:
            logger.error(f"Errore nel gestione admin callback: {e}")
            await update.callback_query.edit_message_text("❌ Errore nel gestione admin.")
    
    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra le impostazioni"""
        settings = self.database.get('settings', {})
        
        text = f"""
⚙️ **Impostazioni Bot**

**Messaggio di benvenuto:**
{settings.get('welcome_message', 'Non impostato')}

**Menu principale:**
{settings.get('main_menu', 'Non impostato')}

**Pagine create:** {len(self.database.get('pages', {}))}
**Pulsanti totali:** {sum(len(page.get('buttons', [])) for page in self.database.get('pages', {}).values())}
        """
        
        keyboard = [
            [InlineKeyboardButton("✏️ Modifica Benvenuto", callback_data="edit_welcome")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra le statistiche"""
        pages_count = len(self.database.get('pages', {}))
        buttons_count = sum(len(page.get('buttons', [])) for page in self.database.get('pages', {}).values())
        actions_count = len(self.database.get('actions', {}))
        
        text = f"""
📊 **Statistiche Bot**

**Pagine:** {pages_count}
**Pulsanti:** {buttons_count}
**Azioni:** {actions_count}
**Amministratori:** {len(self.admin_users)}

**Ultimo aggiornamento:**
{self.database.get('last_updated', 'Mai')}
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Indietro", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def manage_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce gli utenti admin"""
        text = "👥 **Gestione Amministratori**\n\n"
        
        for admin_id in self.admin_users:
            # Trova info utente
            user_info = "N/A"
            for user_id_str, user_data in self.users_database['users'].items():
                if int(user_id_str) == admin_id:
                    username = user_data.get('username', 'N/A')
                    first_name = user_data.get('first_name', '')
                    last_name = user_data.get('last_name', '')
                    name = f"{first_name} {last_name}".strip() or username
                    user_info = f"{name} (@{username})"
                    break
            text += f"• Admin ID: {admin_id} - {user_info}\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Aggiungi Admin", callback_data="add_admin")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def start_edit_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inizia la modifica del messaggio di benvenuto"""
        user_id = update.effective_user.id
        self._set_user_state(user_id, "editing_welcome")
        
        current_welcome = self.database.get('settings', {}).get('welcome_message', 'Benvenuto! Usa i pulsanti per navigare.')
        
        await update.callback_query.edit_message_text(
            f"✏️ **Modifica Messaggio di Benvenuto**\n\n"
            f"**Messaggio attuale:**\n{current_welcome}\n\n"
            f"Invia il nuovo messaggio di benvenuto:",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def start_add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inizia l'aggiunta di un amministratore"""
        user_id = update.effective_user.id
        self._set_user_state(user_id, "adding_admin")
        
        await update.callback_query.edit_message_text(
            "➕ **Aggiungi Amministratore**\n\n"
            "Invia l'ID utente o l'username dell'utente da aggiungere come amministratore.\n\n"
            "**Esempi:**\n"
            "• `123456789` (ID utente)\n"
            "• `@username` (username)\n"
            "• `username` (username senza @)",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_navigation_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Gestisce la navigazione normale"""
        if data.startswith("page_"):
            page_id = data.replace("page_", "")
            await self.show_page(update, context, page_id)
        elif data == "back_to_main":
            await self.show_page(update, context, 'main')
        else:
            # Gestisci azioni personalizzate
            await self.handle_custom_action(update, context, data)
    
    async def show_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page_id: str):
        """Mostra una pagina specifica con logica semplificata"""
        try:
            # Valida e ottieni la pagina
            page = self._get_valid_page(page_id)
            if not page:
                await self._handle_page_not_found(update, context)
                return
            
            # Tracking attività utente
            if update.effective_user:
                user_id = update.effective_user.id
                self.update_user_activity(user_id, 'page_view', {'page_id': page_id})
            
            # Crea contenuto e pulsanti
            content = self._format_page_content(page)
            keyboard = self._create_page_keyboard(page, page_id)
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            # Invia messaggio
            await self._send_page_message(update, content, reply_markup)
            
        except Exception as e:
            logger.error(f"Errore nel mostrare pagina {page_id}: {e}")
            await self._handle_page_error(update, context)
    
    def _get_valid_page(self, page_id: str):
        """Ottiene una pagina valida, con fallback al menu principale"""
        # Controlla se la pagina esiste
        if page_id in self.database.get('pages', {}):
            return self.database['pages'][page_id]
        
        # Fallback al menu principale
        main_menu = self.database.get('settings', {}).get('main_menu', 'main')
        if main_menu in self.database.get('pages', {}):
            return self.database['pages'][main_menu]
        
        # Crea pagina di default se necessario
        return self._create_default_page()
    
    def _create_default_page(self):
        """Crea una pagina di default"""
        default_page = {
            'title': 'Menu Principale',
            'content': 'Benvenuto! Usa /editor per configurare il bot.',
            'buttons': [],
            'created_at': datetime.now().isoformat()
        }
        self.database['pages']['main'] = default_page
        self.save_database()
        return default_page
    
    def _format_page_content(self, page: dict) -> str:
        """Formatta il contenuto della pagina in modo sicuro"""
        return self._create_safe_markdown_text(page['title'], page['content'])
    
    def _create_page_keyboard(self, page: dict, page_id: str) -> list:
        """Crea la tastiera per la pagina"""
        keyboard = []
        
        # Aggiungi pulsanti della pagina
        for button in page.get('buttons', []):
            keyboard.append([InlineKeyboardButton(
                button['text'],
                callback_data=button['action']
            )])
        
        # Aggiungi pulsante "Indietro" se non è la pagina principale
        main_menu = self.database.get('settings', {}).get('main_menu', 'main')
        if page_id != main_menu:
            keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="back_to_main")])
        
        return keyboard
        
    async def _send_page_message(self, update: Update, content: str, reply_markup):
        """Invia il messaggio della pagina"""
        if update.callback_query:
            await update.callback_query.edit_message_text(
                content,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                content,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _handle_page_not_found(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce il caso di pagina non trovata"""
        await update.callback_query.edit_message_text(
            "❌ Pagina non trovata. Torno al menu principale.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu Principale", callback_data="back_to_main")
            ]])
        )
    
    async def _handle_page_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce errori nella visualizzazione delle pagine"""
        try:
            await update.callback_query.edit_message_text(
                "❌ Errore nel caricamento della pagina. Riprova.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Riprova", callback_data="back_to_main")
                ]])
            )
        except:
            pass
    
    async def handle_custom_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
        """Gestisce azioni personalizzate con supporto parametri dinamici"""
        try:
            # Tracking clic pulsante
            if update.effective_user:
                user_id = update.effective_user.id
                button_text = self._find_button_text_by_action(action)
                self.update_user_activity(user_id, 'button_click', {'button_text': button_text})
            
            # Gestione azioni con parametri (formato: action_name:param1:param2)
            if ':' in action:
                action_parts = action.split(':', 1)
                action_name = action_parts[0]
                action_params = action_parts[1] if len(action_parts) > 1 else ""
                
                if action_name in self.database.get('actions', {}):
                    await self._execute_action_with_params(update, context, action_name, action_params)
                    return
            
            # Gestione azioni standard
            if action in self.database.get('actions', {}):
                await self._execute_standard_action(update, context, action)
            elif action.startswith('page_'):
                page_id = action.replace('page_', '')
                await self.show_page(update, context, page_id)
            elif action == 'back_to_main':
                main_menu = self.database.get('settings', {}).get('main_menu', 'main')
                await self.show_page(update, context, main_menu)
            else:
                await update.callback_query.edit_message_text("❌ Azione non trovata.")
                
        except Exception as e:
            logger.error(f"Errore nell'esecuzione azione {action}: {e}")
            await update.callback_query.edit_message_text("❌ Errore nell'esecuzione dell'azione.")

    def _find_button_text_by_action(self, action: str) -> str:
        """Trova il testo del pulsante dato l'action"""
        for page in self.database.get('pages', {}).values():
            for button in page.get('buttons', []):
                if button['action'] == action:
                    return button['text']
        return "Unknown"
        
    async def _execute_standard_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
        """Esegue un'azione standard"""
        action_data = self.database['actions'][action]
        action_type = action_data.get('type', 'message')
        
        if action_type == 'message':
            content = self._process_message_content(action_data['content'], context)
            await update.callback_query.edit_message_text(content, parse_mode=ParseMode.MARKDOWN)
        elif action_type == 'page':
            await self.show_page(update, context, action_data['content'])
        elif action_type == 'url':
            url = action_data.get('url', action_data['content'])
            text = action_data.get('text', 'Apri Link')
            await update.callback_query.edit_message_text(
                f"🔗 [{text}]({url})",
                parse_mode=ParseMode.MARKDOWN
            )
        elif action_type == 'command':
            # Esegue un comando interno
            command = action_data['content']
            if command == 'show_analytics':
                await self.analytics_command(update, context)
            elif command == 'show_users':
                await self.users_command(update, context)
        else:
                await update.callback_query.edit_message_text(f"Comando: {command}")

    async def _execute_action_with_params(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_name: str, params: str):
        """Esegue un'azione con parametri"""
        action_data = self.database['actions'][action_name]
        action_type = action_data.get('type', 'message')
        
        if action_type == 'message':
            # Sostituisce {param} nel contenuto
            content = action_data['content'].replace('{param}', params)
            content = self._process_message_content(content, context)
            await update.callback_query.edit_message_text(content, parse_mode=ParseMode.MARKDOWN)
        elif action_type == 'page':
            # Usa il parametro come page_id
            await self.show_page(update, context, params)
        elif action_type == 'url':
            # Costruisce URL con parametri
            base_url = action_data.get('url', action_data['content'])
            url = f"{base_url}{params}" if not base_url.endswith('/') else f"{base_url}{params}"
            text = action_data.get('text', 'Apri Link')
            await update.callback_query.edit_message_text(
                f"🔗 [{text}]({url})",
                parse_mode=ParseMode.MARKDOWN
            )

    def _process_message_content(self, content: str, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Processa il contenuto del messaggio con variabili dinamiche"""
        # Sostituisce variabili comuni
        user_id = context.user_data.get('user_id', 'Unknown')
        content = content.replace('{user_id}', str(user_id))
        content = content.replace('{timestamp}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Escape caratteri Markdown se necessario
        return self._escape_markdown(content)

    def _escape_markdown(self, text: str) -> str:
        """Escape caratteri speciali Markdown in modo intelligente"""
        if not text:
            return text
        
        # Caratteri che devono essere escaped in Markdown V2
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        # Escape solo se necessario (evita double escaping)
        for char in escape_chars:
            if char in text and f'\\{char}' not in text:
                text = text.replace(char, f'\\{char}')
        
        return text
    
    def _format_markdown_safe(self, text: str, parse_mode: str = ParseMode.MARKDOWN) -> str:
        """Formatta il testo in modo sicuro per Markdown"""
        if not text:
            return text
        
        if parse_mode == ParseMode.MARKDOWN_V2:
            return self._escape_markdown(text)
        elif parse_mode == ParseMode.MARKDOWN:
            # Per Markdown normale, escape solo caratteri problematici
            problem_chars = ['*', '_', '`', '[', ']']
            for char in problem_chars:
                if char in text and f'\\{char}' not in text:
                    text = text.replace(char, f'\\{char}')
            return text
        else:
            return text
    
    def _create_safe_markdown_text(self, title: str, content: str) -> str:
        """Crea testo Markdown sicuro per titolo e contenuto"""
        safe_title = self._format_markdown_safe(title)
        safe_content = self._format_markdown_safe(content)
        return f"**{safe_title}**\n\n{safe_content}"
    
    def run(self):
        """Avvia il bot"""
        logger.info("Avvio del bot...")
        self.app.run_polling()

def main():
    """Funzione principale"""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Errore: Devi inserire il tuo token del bot in BOT_TOKEN")
        print("Ottieni il token da @BotFather su Telegram")
        print("Modifica la variabile BOT_TOKEN all'inizio del file telegram_bot.py")
        return
    
    bot = TelegramBotEditor(BOT_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()

