from dotenv import load_dotenv
load_dotenv()  # .env faylidan muhit o'zgaruvchilarini yuklaydi

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
SELECTING_ACTION, ADDING_PRODUCT, ADDING_QUANTITY, BUYING_PRODUCT, BUYING_QUANTITY = range(5)

# Dictionary to store products and their quantities
products = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask user what they want to do."""
    keyboard = [
        [InlineKeyboardButton("Mahsulot qo'shish", callback_data='add')],
        [InlineKeyboardButton("Mahsulot sotib olish", callback_data='buy')],
        [InlineKeyboardButton("Mahsulotlar ro'yxati", callback_data='list')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Assalomu alaykum! Mahsulotlar sonini kuzatuvchi botga xush kelibsiz!\n"
        "Nima qilmoqchisiz?",
        reply_markup=reply_markup
    )
    return SELECTING_ACTION

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'add':
        await query.edit_message_text("Qo'shmoqchi bo'lgan mahsulot nomini kiriting:")
        return ADDING_PRODUCT
    
    elif query.data == 'buy':
        if not products:
            keyboard = [[InlineKeyboardButton("Orqaga", callback_data='back')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Mahsulotlar mavjud emas. Avval mahsulot qo'shing.", reply_markup=reply_markup)
            return SELECTING_ACTION
        
        keyboard = []
        for product in products:
            keyboard.append([InlineKeyboardButton(f"{product} ({products[product]})", callback_data=f"buy_{product}")])
        keyboard.append([InlineKeyboardButton("Orqaga", callback_data='back')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Qaysi mahsulotni sotib olmoqchisiz?", reply_markup=reply_markup)
        return BUYING_PRODUCT
    
    elif query.data == 'list':
        if not products:
            text = "Mahsulotlar ro'yxati bo'sh."
        else:
            text = "Mahsulotlar ro'yxati:\n"
            for product, quantity in products.items():
                text += f"- {product}: {quantity} dona\n"
        
        keyboard = [[InlineKeyboardButton("Orqaga", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return SELECTING_ACTION
    
    elif query.data == 'back':
        keyboard = [
            [InlineKeyboardButton("Mahsulot qo'shish", callback_data='add')],
            [InlineKeyboardButton("Mahsulot sotib olish", callback_data='buy')],
            [InlineKeyboardButton("Mahsulotlar ro'yxati", callback_data='list')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Nima qilmoqchisiz?",
            reply_markup=reply_markup
        )
        return SELECTING_ACTION
    
    elif query.data.startswith('buy_'):
        product = query.data[4:]
        context.user_data['product_to_buy'] = product
        await query.edit_message_text(f"{product} dan necha dona sotib olmoqchisiz? (Jami: {products[product]} dona)")
        return BUYING_QUANTITY
    
    return SELECTING_ACTION

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store product name and ask for quantity."""
    product_name = update.message.text
    context.user_data['product_name'] = product_name
    await update.message.reply_text(f"{product_name} uchun miqdorni kiriting (raqam):")
    return ADDING_QUANTITY

async def add_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store product quantity and go back to selection."""
    try:
        quantity = int(update.message.text)
        if quantity <= 0:
            await update.message.reply_text("Iltimos, musbat son kiriting.")
            return ADDING_QUANTITY
            
        product_name = context.user_data['product_name']
        if product_name in products:
            products[product_name] += quantity
            await update.message.reply_text(f"{product_name} miqdori {quantity} dona qo'shildi. Jami: {products[product_name]} dona")
        else:
            products[product_name] = quantity
            await update.message.reply_text(f"{product_name} {quantity} dona miqdorida qo'shildi.")
        
    except ValueError:
        await update.message.reply_text("Iltimos, raqam kiriting.")
        return ADDING_QUANTITY
    
    keyboard = [
        [InlineKeyboardButton("Mahsulot qo'shish", callback_data='add')],
        [InlineKeyboardButton("Mahsulot sotib olish", callback_data='buy')],
        [InlineKeyboardButton("Mahsulotlar ro'yxati", callback_data='list')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Nima qilmoqchisiz?", reply_markup=reply_markup)
    return SELECTING_ACTION

async def buy_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process buying products and update inventory."""
    try:
        quantity = int(update.message.text)
        product = context.user_data['product_to_buy']
        
        if quantity <= 0:
            await update.message.reply_text("Iltimos, musbat son kiriting.")
            return BUYING_QUANTITY
            
        if product in products:
            if quantity > products[product]:
                await update.message.reply_text(f"Kechirasiz, omborda faqat {products[product]} dona {product} mavjud.")
            else:
                products[product] -= quantity
                await update.message.reply_text(f"{quantity} dona {product} sotib olindi. Qolgan miqdor: {products[product]} dona")
                
                # If quantity becomes 0, remove the product
                if products[product] == 0:
                    del products[product]
                    await update.message.reply_text(f"{product} tugadi va ro'yxatdan olib tashlandi.")
        else:
            await update.message.reply_text(f"Kechirasiz, {product} mahsuloti mavjud emas.")
        
    except ValueError:
        await update.message.reply_text("Iltimos, raqam kiriting.")
        return BUYING_QUANTITY
    
    keyboard = [
        [InlineKeyboardButton("Mahsulot qo'shish", callback_data='add')],
        [InlineKeyboardButton("Mahsulot sotib olish", callback_data='buy')],
        [InlineKeyboardButton("Mahsulotlar ro'yxati", callback_data='list')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Nima qilmoqchisiz?", reply_markup=reply_markup)
    return SELECTING_ACTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End the conversation."""
    await update.message.reply_text("Xayr! Bot ishini tugatdi.")
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    # Get bot token from environment variable
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("No TELEGRAM_TOKEN environment variable found!")
        return

    # Create the Application
    application = Application.builder().token(token).build()

    # Set up conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(button_handler)
            ],
            ADDING_PRODUCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product)
            ],
            ADDING_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_quantity)
            ],
            BUYING_PRODUCT: [
                CallbackQueryHandler(button_handler)
            ],
            BUYING_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, buy_quantity)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
