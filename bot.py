import os
import logging
from datetime import datetime, time
import pytz

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from horario import HORARIO, EMOJIS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ZONA_HORARIA = pytz.timezone("America/Santiago")

DIAS_ES = {
    0: "lunes",
    1: "martes",
    2: "miercoles",
    3: "jueves",
    4: "viernes",
    5: "sabado",
    6: "domingo",
}

DIAS_BONITO = {
    "lunes":     "Lunes",
    "martes":    "Martes",
    "miercoles": "Miércoles",
    "jueves":    "Jueves",
    "viernes":   "Viernes",
    "sabado":    "Sábado",
    "domingo":   "Domingo",
}

TECLADO = ReplyKeyboardMarkup(
    [
        ["📅 Hoy", "📆 Mañana"],
        ["📋 Semana completa"],
        ["Lunes", "Martes", "Miércoles"],
        ["Jueves", "Viernes", "Sábado"],
    ],
    resize_keyboard=True,
)


# ── helpers ────────────────────────────────────────────────────────────────────
def formatear_dia(dia_key: str) -> str:
    clases = HORARIO.get(dia_key, [])
    nombre = DIAS_BONITO.get(dia_key, dia_key.capitalize())
    if not clases:
        return f"*{nombre}*\n_Sin clases_ 🎉"
    lineas = [f"*{nombre}*"]
    for c in clases:
        emoji = EMOJIS.get(c["ramo"], "📚")
        lineas.append(f"  {emoji} `{c['hora']}` — {c['ramo']}")
    return "\n".join(lineas)


def dia_hoy() -> str:
    return DIAS_ES[datetime.now(ZONA_HORARIA).weekday()]


def dia_manana() -> str:
    return DIAS_ES[(datetime.now(ZONA_HORARIA).weekday() + 1) % 7]


def parsear_hora_inicio(hora_str: str):
    """Extrae h, m del inicio de un string como '9:50 - 11:00'."""
    inicio = hora_str.split(" - ")[0].strip()
    h, m = map(int, inicio.split(":"))
    return h, m


def minutos_hasta(h: int, m: int) -> float:
    """Minutos que faltan desde ahora hasta h:m (hora chilena)."""
    ahora = datetime.now(ZONA_HORARIA)
    clase_dt = ahora.replace(hour=h, minute=m, second=0, microsecond=0)
    return (clase_dt - ahora).total_seconds() / 60


# ── recordatorios ──────────────────────────────────────────────────────────────
async def programar_recordatorios_hoy(app: Application):
    """Agenda los jobs de recordatorio para todas las clases de hoy."""
    chat_id = os.environ.get("CHAT_ID")
    if not chat_id:
        logger.warning("CHAT_ID no configurado — recordatorios desactivados.")
        return

    dia = dia_hoy()
    clases = HORARIO.get(dia, [])

    # Eliminar jobs de clases anteriores (no el de medianoche)
    for job in app.job_queue.jobs():
        if job.name != "reagendar_medianoche":
            job.schedule_removal()

    contador = 0
    for clase in clases:
        h, m = parsear_hora_inicio(clase["hora"])
        emoji = EMOJIS.get(clase["ramo"], "📚")

        for minutos_antes, icono, sufijo in [
            (40, "⏰", "Prepara tus cosas 🎒"),
            (10, "🔔", "¡Ya es hora de salir! 🏃"),
        ]:
            mins_restantes = minutos_hasta(h, m) - minutos_antes
            if mins_restantes > 0:
                texto = (
                    f"{icono} *En {minutos_antes} minutos:*\n"
                    f"{emoji} {clase['ramo']}\n"
                    f"🕐 `{clase['hora']}`\n"
                    f"_{sufijo}_"
                )

                # Capturar variables correctamente con argumentos por defecto
                async def enviar(ctx, t=texto, cid=chat_id):
                    await ctx.bot.send_message(
                        chat_id=cid, text=t, parse_mode="Markdown"
                    )

                app.job_queue.run_once(
                    callback=enviar,
                    when=mins_restantes * 60,
                    name=f"{dia}_{clase['ramo']}_{minutos_antes}min",
                )
                contador += 1
                logger.info(
                    f"  → {clase['ramo']} en {mins_restantes:.0f} min "
                    f"(aviso {minutos_antes} min antes)"
                )

    logger.info(f"Recordatorios agendados hoy ({dia}): {contador}")


async def reagendar_a_medianoche(context: ContextTypes.DEFAULT_TYPE):
    """Corre a medianoche para reagendar el día siguiente."""
    await programar_recordatorios_hoy(context.application)
    logger.info("Recordatorios reagendados para el nuevo día ✅")


# ── handlers ───────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.effective_user.first_name
    await update.message.reply_text(
        f"¡Hola {nombre}! 👋\n"
        "Soy tu bot de horario universitario.\n\n"
        "📌 Escribe /miid para obtener tu Chat ID\n"
        "y activar los recordatorios automáticos.",
        reply_markup=TECLADO,
    )


async def mi_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🆔 Tu Chat ID es:\n\n`{chat_id}`\n\n"
        "Cópialo y agrégalo en Railway como variable:\n"
        "`CHAT_ID` = ese número\n\n"
        "Luego reinicia el servicio y los recordatorios se activarán 🎉",
        parse_mode="Markdown",
        reply_markup=TECLADO,
    )


async def hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dia = dia_hoy()
    ahora = datetime.now(ZONA_HORARIA)
    texto = f"📅 *Hoy es {DIAS_BONITO[dia]}* ({ahora.strftime('%d/%m/%Y')})\n\n"
    texto += formatear_dia(dia)
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=TECLADO)


async def manana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dia = dia_manana()
    texto = f"📆 *Mañana — {DIAS_BONITO[dia]}*\n\n"
    texto += formatear_dia(dia)
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=TECLADO)


async def semana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orden = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]
    partes = ["📋 *Semana completa*\n"]
    for d in orden:
        partes.append(formatear_dia(d))
    await update.message.reply_text(
        "\n\n".join(partes), parse_mode="Markdown", reply_markup=TECLADO
    )


async def dia_especifico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mapa = {
        "lunes":     "lunes",
        "martes":    "martes",
        "miércoles": "miercoles",
        "miercoles": "miercoles",
        "jueves":    "jueves",
        "viernes":   "viernes",
        "sábado":    "sabado",
        "sabado":    "sabado",
    }
    dia_key = mapa.get(update.message.text.strip().lower())
    if dia_key:
        await update.message.reply_text(
            formatear_dia(dia_key), parse_mode="Markdown", reply_markup=TECLADO
        )
    else:
        await update.message.reply_text(
            "No entendí ese día 😅 Usa los botones del menú.", reply_markup=TECLADO
        )


async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if texto == "📅 Hoy":
        await hoy(update, context)
    elif texto == "📆 Mañana":
        await manana(update, context)
    elif texto == "📋 Semana completa":
        await semana(update, context)
    else:
        await dia_especifico(update, context)


# ── post_init ──────────────────────────────────────────────────────────────────
async def post_init(app: Application):
    # Recordatorios para hoy al arrancar
    await programar_recordatorios_hoy(app)

    # Job diario a medianoche para el día siguiente
    app.job_queue.run_daily(
        callback=reagendar_a_medianoche,
        time=time(hour=0, minute=0, second=0, tzinfo=ZONA_HORARIA),
        name="reagendar_medianoche",
    )
    logger.info("Job de medianoche registrado ✅")


# ── main ───────────────────────────────────────────────────────────────────────
def main():
    token = os.environ["BOT_TOKEN"]
    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("miid", mi_id))
    app.add_handler(CommandHandler("hoy", hoy))
    app.add_handler(CommandHandler("manana", manana))
    app.add_handler(CommandHandler("semana", semana))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_botones))

    logger.info("Bot corriendo con recordatorios automáticos ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
