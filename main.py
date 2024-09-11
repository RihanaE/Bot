from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, MessageHandler, filters
)
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from http import HTTPStatus
import os
import uvicorn


# Load environment variables from the .env file
load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')


# Define states for the conversation
DEPARTMENT, YEAR, SEMESTER = range(3)

# FastAPI app
app = FastAPI()

# Initialize the bot application
telegram_bot = Application.builder().token(token).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(update, token)
    intro_message = (
        "Welcome to 5k AAiT Jem'a Course Info Bot!\n\n"
        "This bot helps you find links to your department's Telegram channels based on your year and semester.\n\n"
        "To get started, please click the button below to choose your department. You can stop the conversation at any time by sending /stop."
    )
    await update.message.reply_text(intro_message)
    return await choose_department(update, context)

async def choose_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("CBME (Biomedical)", callback_data='CBME')],
        [InlineKeyboardButton("SCBE (Chemical)", callback_data='SCBE')],
        [InlineKeyboardButton("SCEE (Civil)", callback_data='SCEE')],
        [InlineKeyboardButton("SECE (Electrical)", callback_data='SECE')],
        [InlineKeyboardButton("SMiE (Mechanical)", callback_data='SMiE')],
        [InlineKeyboardButton("SiTE (Software)", callback_data='SiTE')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text('Please choose your department:', reply_markup=reply_markup)
    else:
        query = update.callback_query
        await query.edit_message_text(text="Please choose your department:", reply_markup=reply_markup)
    return DEPARTMENT

async def department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['department'] = query.data

    keyboard = [
        [InlineKeyboardButton("Second year", callback_data='Second')],
        [InlineKeyboardButton("Third year", callback_data='Third')],
        [InlineKeyboardButton("Fourth year", callback_data='Fourth')],
        [InlineKeyboardButton("Fifth year", callback_data='Fifth')],
        [InlineKeyboardButton("Back", callback_data='back_department')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Please choose your year:", reply_markup=reply_markup)
    return YEAR

async def year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == 'back_department':
        return await choose_department(update, context)

    context.user_data['year'] = query.data

    if context.user_data['year'] == 'Second':
        keyboard = [
            [InlineKeyboardButton("2nd semester", callback_data='2nd')],
            [InlineKeyboardButton("Back", callback_data='back_year')],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("1st semester", callback_data='1st')],
            [InlineKeyboardButton("2nd semester", callback_data='2nd')],
            [InlineKeyboardButton("Back", callback_data='back_year')],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Please choose your semester:", reply_markup=reply_markup)
    return SEMESTER

async def semester(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == 'back_year':
        return await year(update, context)

    context.user_data['semester'] = query.data

    department = context.user_data['department']
    year = context.user_data['year']
    semester = context.user_data['semester']

    env_key = f"{department.upper()}_{year.upper()}_YEAR_{semester.upper()}_SEM"

    link = os.getenv(env_key, "https://t.me/your_default_channel")
    await query.edit_message_text(text=f"Here is your link: [Go to Channel]({link})", parse_mode='MarkdownV2')
    return ConversationHandler.END

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("The conversation has been stopped. To start again, type /start.")
    return ConversationHandler.END



# FastAPI route for webhook
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_bot.bot)  # Correct the bot reference here
    await telegram_bot.process_update(update)
    return Response(status_code=HTTPStatus.OK)

# FastAPI startup and shutdown events
@app.on_event("startup")
async def on_startup():
    await telegram_bot.initialize()
    await telegram_bot.start()
    webhook_url = f"{os.getenv('WEBHOOK_URL')}"
    print(token, webhook_url)
    await telegram_bot.bot.set_webhook(webhook_url)

@app.on_event("shutdown")
async def on_shutdown():
    await telegram_bot.stop()

if __name__ == "__main__":
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],  # Trigger start on /start command
    states={
        DEPARTMENT: [CallbackQueryHandler(department)],  # Handle department selection
        YEAR: [CallbackQueryHandler(year)],  # Handle year selection
        SEMESTER: [CallbackQueryHandler(semester)],  # Handle semester selection
    },
    fallbacks=[CommandHandler('stop', stop)]  # Allow stopping the conversation with /stop
   )

    telegram_bot.add_handler(conv_handler)
    uvicorn.run(app, host="0.0.0.0", port=8000)
