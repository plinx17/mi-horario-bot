# 🎓 Bot de Horario Universitario

Bot de Telegram que muestra tu horario de clases.

## Comandos disponibles

| Comando / Botón | Descripción |
|---|---|
| `/start` | Inicia el bot y muestra el menú |
| `📅 Hoy` | Clases de hoy |
| `📆 Mañana` | Clases de mañana |
| `📋 Semana completa` | Todo el horario semanal |
| `Lunes … Sábado` | Día específico |

## Cómo correrlo localmente

1. Clona el repo y entra a la carpeta
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Crea tu archivo `.env` copiando `.env.example`:
   ```bash
   cp .env.example .env
   ```
4. Edita `.env` y pega tu token de BotFather
5. Corre el bot:
   ```bash
   python bot.py
   ```

## Deploy en Railway

1. Sube el proyecto a GitHub
2. En [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. En **Variables** agrega: `BOT_TOKEN` = tu token
4. Railway detecta el `Procfile` y lo corre automáticamente ✅
