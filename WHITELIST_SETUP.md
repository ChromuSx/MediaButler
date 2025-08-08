# Configurazione Whitelist - Bot Sicuro

## Come funziona la sicurezza

Il bot ora ha un sistema di **whitelist** che permette l'accesso solo agli utenti autorizzati.

## 🚀 Setup Rapido (Prima volta)

### 1. Avvia il bot SENZA modificare nulla
```bash
python telegram_media_bot_secure.py
```

### 2. Vai su Telegram e usa `/start`
Il bot ti risponderà con:
```
🔐 Primo accesso - Admin Mode
Sei stato aggiunto come amministratore!
Il tuo ID: 123456789

Per aggiungere altri utenti, modifica AUTHORIZED_USERS nel codice.
```

### 3. Copia il tuo ID e aggiungilo al codice
Apri il file e modifica questa sezione:
```python
AUTHORIZED_USERS = [
    123456789,  # Il tuo ID (sostituisci con quello vero)
]
```

### 4. Riavvia il bot
Ora solo tu puoi usarlo!

## 👥 Aggiungere altri utenti

### Metodo 1: Chiedi il loro ID
1. Fai provare a usare `/start` al nuovo utente
2. Il bot gli mostrerà il suo ID nel messaggio di errore
3. Aggiungi quell'ID alla lista:

```python
AUTHORIZED_USERS = [
    123456789,  # Giovanni (admin)
    987654321,  # Mario
    555555555,  # Anna
]
```

### Metodo 2: Usa il comando `/users`
Solo l'admin (primo utente) può vedere la lista completa degli utenti autorizzati.

## 🔐 Funzionalità di sicurezza

### Per tutti gli utenti autorizzati:
- ✅ Possono scaricare file
- ✅ Possono usare tutti i comandi base
- ✅ Possono gestire i propri download

### Solo per l'admin (primo utente):
- 👑 Può usare `/stop` per fermare il bot
- 👑 Può vedere `/users` per la lista completa
- 👑 Può decidere chi aggiungere

### Protezioni aggiuntive:
- ❌ Utenti non autorizzati vedono "Accesso Negato"
- ❌ Non possono cliccare sui bottoni
- ❌ Ogni tentativo viene loggato
- ✅ Ogni utente può gestire solo i propri download

## 📝 Esempio di configurazione multi-utente

```python
# Famiglia
AUTHORIZED_USERS = [
    123456789,  # Giovanni (admin)
    987654321,  # Partner
    555555555,  # Fratello
]

# Solo personale
AUTHORIZED_USERS = [
    123456789,  # Solo io
]

# Test con amici fidati
AUTHORIZED_USERS = [
    123456789,  # Giovanni (admin)
    111111111,  # Marco
    222222222,  # Luca
]
```

## ⚠️ Note importanti

1. **Il primo utente è sempre l'admin** - ha privilegi extra
2. **Backup la lista** - se perdi gli ID, dovrai ricominciare
3. **Non condividere il file** con la lista degli ID
4. **Cambia username del bot** se vuoi extra sicurezza

## 🛡️ Sicurezza extra (opzionale)

Per ancora più sicurezza, puoi:

1. **Cambiare l'username del bot** in BotFather:
   ```
   /setname
   Scegli: @mediabot_x7k9p2m_2024_bot
   ```

2. **Non condividere mai** il link del bot

3. **Monitora i log** per tentativi di accesso:
   ```bash
   grep "non autorizzato" bot.log
   ```

## 🆘 Troubleshooting

**"Ho perso il mio ID admin"**
- Elimina `AUTHORIZED_USERS = [...]` (lasciala vuota)
- Riavvia il bot
- Fai `/start` - sarai di nuovo admin

**"Voglio rimuovere un utente"**
- Rimuovi il suo ID dalla lista
- Riavvia il bot

**"Il bot dice che non sono autorizzato"**
- Verifica che il tuo ID sia nella lista
- Controlla di non aver spazi o virgole sbagliate
- Riavvia il bot dopo le modifiche