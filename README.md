# 🤖 Telegram Bot Editor

Un bot Telegram completamente configurabile con editor integrato, sistema di navigazione a pulsanti personalizzabili e pannello amministrativo avanzato.

## ✨ Caratteristiche

### 🎯 **Funzionalità Principali**
- **Editor Integrato**: Configura il bot direttamente da Telegram
- **Navigazione a Pulsanti**: Sistema di menu personalizzabili
- **Azioni Personalizzate**: Messaggi, pagine, URL, comandi
- **Pannello Admin**: Gestione completa del bot
- **Analytics**: Statistiche dettagliate degli utenti
- **Database JSON**: Archiviazione locale semplice e affidabile

### 🛠️ **Sistema di Gestione**
- **Pagine Dinamiche**: Crea e modifica pagine in tempo reale
- **Pulsanti Personalizzati**: Aggiungi pulsanti con azioni specifiche
- **Gestione Utenti**: Sistema di ruoli (admin, staff, user)
- **Tracking Attività**: Monitora visualizzazioni e interazioni
- **Backup Automatico**: Salvataggio automatico dei dati

### 🎨 **Interfaccia Utente**
- **Markdown Support**: Formattazione avanzata dei messaggi
- **Inline Keyboards**: Pulsanti integrati nei messaggi
- **Navigazione Intuitiva**: Menu chiari e organizzati
- **Responsive Design**: Ottimizzato per tutti i dispositivi

## 🚀 Installazione

### Prerequisiti
- Python 3.8 o superiore
- Token del bot Telegram (ottienilo da [@BotFather](https://t.me/BotFather))

### 1. Clona il Repository
```bash
git clone https://github.com/tuousername/telegram-bot-editor.git
cd telegram-bot-editor
```

### 2. Installa le Dipendenze
```bash
pip install -r requirements.txt
```

### 3. Configura il Bot
1. Apri `telegram_bot.py`
2. Sostituisci `YOUR_BOT_TOKEN_HERE` con il tuo token:
```python
BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
```

### 4. Avvia il Bot
```bash
python telegram_bot.py
```

## 📖 Guida all'Uso

### Comandi Principali
- `/start` - Avvia il bot e mostra il menu principale
- `/admin` - Pannello amministrativo (solo admin)
- `/editor` - Editor per configurare il bot (solo admin/staff)
- `/analytics` - Visualizza statistiche (solo admin)
- `/users` - Gestione utenti (solo admin)

### Editor Integrato
1. Usa `/editor` per accedere all'editor
2. Crea pagine con contenuti personalizzati
3. Aggiungi pulsanti con azioni specifiche
4. Configura azioni personalizzate (messaggi, URL, comandi)
5. Salva le modifiche in tempo reale

### Sistema di Azioni
- **Messaggio**: Invia un messaggio personalizzato
- **Pagina**: Naviga a una pagina specifica
- **URL**: Apri un link esterno
- **Comando**: Esegui un comando interno

## 🔧 Configurazione Avanzata

### Gestione Ruoli Utenti
```python
# Nel pannello admin puoi:
- Aggiungere/rimuovere amministratori
- Gestire i ruoli degli utenti
- Monitorare l'attività
```

### Personalizzazione Database
I database vengono creati automaticamente:
- `bot_database.json` - Configurazione bot e pagine
- `users_database.json` - Dati utenti e ruoli
- `analytics_database.json` - Statistiche e tracking

### Variabili Dinamiche
Nelle azioni puoi usare:
- `{user_id}` - ID dell'utente
- `{timestamp}` - Data e ora corrente
- `{param}` - Parametri dell'azione

## 📊 Analytics e Statistiche

### Metriche Disponibili
- **Visualizzazioni Pagine**: Conteggio per ogni pagina
- **Clic Pulsanti**: Statistiche per ogni pulsante
- **Utenti Attivi**: Lista utenti e loro attività
- **Comandi Utilizzati**: Frequenza d'uso dei comandi

### Pannello Analytics
- Grafici interattivi
- Esportazione dati
- Filtri per periodo
- Statistiche in tempo reale

## 🛡️ Sicurezza

### Sistema di Permessi
- **Admin**: Accesso completo a tutte le funzioni
- **Staff**: Accesso all'editor e gestione contenuti
- **User**: Accesso limitato alle funzioni pubbliche

### Protezione Dati
- Database locali (nessun dato inviato a server esterni)
- Validazione input utente
- Sanitizzazione contenuti
- Backup automatico

## 🔄 Aggiornamenti e Manutenzione

### Backup
I database vengono salvati automaticamente ogni 5 secondi dopo le modifiche.

### Log
Il sistema genera log dettagliati per monitoraggio e debug:
```bash
# I log mostrano:
- Attività utenti
- Errori e warning
- Operazioni di database
- Performance del bot
```

## 🤝 Contribuire

### Come Contribuire
1. Fai un fork del progetto
2. Crea un branch per la tua feature (`git checkout -b feature/AmazingFeature`)
3. Commit le tue modifiche (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

### Segnalazione Bug
Usa la sezione [Issues](https://github.com/tuousername/telegram-bot-editor/issues) per segnalare bug o richiedere nuove funzionalità.

## 📝 Licenza

Questo progetto è distribuito sotto licenza MIT. Vedi il file `LICENSE` per maggiori dettagli.

## 🙏 Ringraziamenti

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Framework Telegram
- [Telegram Bot API](https://core.telegram.org/bots/api) - API ufficiale Telegram

## 📞 Supporto

- **Documentazione**: [Wiki del progetto](https://github.com/tuousername/telegram-bot-editor/wiki)
- **Issues**: [GitHub Issues](https://github.com/tuousername/telegram-bot-editor/issues)
- **Discussioni**: [GitHub Discussions](https://github.com/tuousername/telegram-bot-editor/discussions)

---

⭐ **Se questo progetto ti è utile, lascia una stella su GitHub!**

## 🚀 Quick Start

```bash
# 1. Clona e installa
git clone https://github.com/tuousername/telegram-bot-editor.git
cd telegram-bot-editor
pip install -r requirements.txt

# 2. Configura il token
# Modifica BOT_TOKEN in telegram_bot.py

# 3. Avvia il bot
python telegram_bot.py

# 4. Usa /admin per configurare il bot
```

**Buon coding! 🎉**