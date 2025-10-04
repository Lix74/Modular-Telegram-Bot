# =============================================================================
# CONFIGURAZIONE BOT - FILE DI ESEMPIO
# =============================================================================
# Copia questo file come config.py e modifica i valori secondo le tue esigenze

# Token del bot Telegram (ottienilo da @BotFather)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Configurazioni opzionali
BOT_CONFIG = {
    # Nome del bot (opzionale)
    "bot_name": "My Telegram Bot",
    
    # Messaggio di benvenuto personalizzato
    "welcome_message": "Benvenuto! Usa i pulsanti per navigare.",
    
    # ID degli amministratori (opzionale, può essere configurato via /admin)
    "admin_users": [],
    
    # Impostazioni database
    "database_file": "bot_database.json",
    "users_file": "users_database.json",
    "analytics_file": "analytics_database.json",
    
    # Impostazioni logging
    "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    
    # Impostazioni backup
    "auto_backup": True,
    "backup_interval": 300,  # secondi
    
    # Impostazioni sicurezza
    "max_buttons_per_page": 10,
    "max_pages": 100,
    "max_actions": 50,
}

# Messaggi personalizzati
MESSAGES = {
    "admin_denied": "❌ Non hai i permessi per accedere al pannello admin.",
    "editor_denied": "❌ Non hai i permessi per accedere all'editor.",
    "analytics_denied": "❌ Non hai i permessi per visualizzare le analytics.",
    "users_denied": "❌ Non hai i permessi per gestire gli utenti.",
    "error_general": "❌ Si è verificato un errore. Riprova più tardi.",
    "success_saved": "✅ Modifiche salvate con successo!",
    "success_created": "✅ Elemento creato con successo!",
    "success_deleted": "✅ Elemento eliminato con successo!",
}

# Esempi di pagine predefinite
DEFAULT_PAGES = {
    "main": {
        "title": "🏠 Menu Principale",
        "content": "Benvenuto! Scegli un'opzione dal menu qui sotto.",
        "buttons": [
            {"text": "ℹ️ Informazioni", "action": "info"},
            {"text": "📞 Contatti", "action": "contacts"},
            {"text": "⚙️ Impostazioni", "action": "settings"},
        ]
    },
    "info": {
        "title": "ℹ️ Informazioni",
        "content": "Questo è un bot Telegram personalizzabile.\n\nUsa /editor per configurare il bot.",
        "buttons": [
            {"text": "🔙 Indietro", "action": "back_to_main"},
        ]
    }
}

# Esempi di azioni predefinite
DEFAULT_ACTIONS = {
    "info": {
        "type": "page",
        "content": "info",
        "description": "Mostra pagina informazioni"
    },
    "contacts": {
        "type": "message",
        "content": "📞 **Contatti**\n\nEmail: info@example.com\nTelefono: +39 123 456 7890",
        "description": "Mostra informazioni di contatto"
    },
    "settings": {
        "type": "message",
        "content": "⚙️ **Impostazioni**\n\nQui puoi configurare le tue preferenze.",
        "description": "Mostra impostazioni"
    },
    "back_to_main": {
        "type": "page",
        "content": "main",
        "description": "Torna al menu principale"
    }
}
