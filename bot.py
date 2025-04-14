from dotenv import load_dotenv
load_dotenv() 

import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

SELECTING_ACTION, ADDING_PRODUCT, ADDING_QUANTITY_AND_UNIT, BUYING_PRODUCT, BUYING_QUANTITY_AND_UNIT = range(5)

# Foydalanuvchilar ma'lumotlari
user_products = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask user what they want to do."""
    user_id = update.effective_user.id
    if user_id not in user_products:
        user_products[user_id] = {}
    
    keyboard = [
        [InlineKeyboardButton("Mahsulot qo'shish", callback_data='add')],
        [InlineKeyboardButton("Mahsulot sotib olish", callback_data='buy')],
        [InlineKeyboardButton("Mahsulotlar ro'yxati", callback_data='list')],
        [InlineKeyboardButton("Mahsulotni o'chirish", callback_data='delete')]
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
    user_id = query.from_user.id
    
    if user_id not in user_products:
        user_products[user_id] = {}
    
    if query.data == 'add':
        await query.edit_message_text("Qo'shmoqchi bo'lgan mahsulot nomini kiriting:")
        return ADDING_PRODUCT
    
    elif query.data == 'buy':
        if not user_products[user_id]:
            keyboard = [[InlineKeyboardButton("Orqaga", callback_data='back')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Mahsulotlar mavjud emas. Avval mahsulot qo'shing.", reply_markup=reply_markup)
            return SELECTING_ACTION
        
        keyboard = []
        for product, details in user_products[user_id].items():
            quantity = details['quantity']
            unit = details['unit']
            keyboard.append([InlineKeyboardButton(f"{product} ({quantity} {unit})", callback_data=f"buy_{product}")])
        keyboard.append([InlineKeyboardButton("Orqaga", callback_data='back')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Qaysi mahsulotni sotib olmoqchisiz?", reply_markup=reply_markup)
        return BUYING_PRODUCT
    
    elif query.data == 'list':
        if not user_products[user_id]:
            text = "Mahsulotlar ro'yxati bo'sh."
        else:
            text = "Mahsulotlar ro'yxati:\n"
            for product, details in user_products[user_id].items():
                quantity = details['quantity']
                unit = details['unit']
                text += f"- {product}: {quantity} {unit}\n"
        
        keyboard = [[InlineKeyboardButton("Orqaga", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return SELECTING_ACTION
    
    elif query.data == 'delete':
        if not user_products[user_id]:
            keyboard = [[InlineKeyboardButton("Orqaga", callback_data='back')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Mahsulotlar mavjud emas. Avval mahsulot qo'shing.", reply_markup=reply_markup)
            return SELECTING_ACTION
        
        keyboard = []
        for product in user_products[user_id]:
            keyboard.append([InlineKeyboardButton(f"{product} o'chirish", callback_data=f"delete_{product}")])
        keyboard.append([InlineKeyboardButton("Orqaga", callback_data='back')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Qaysi mahsulotni o'chirmoqchisiz?", reply_markup=reply_markup)
        return SELECTING_ACTION
    
    elif query.data == 'back':
        keyboard = [
            [InlineKeyboardButton("Mahsulot qo'shish", callback_data='add')],
            [InlineKeyboardButton("Mahsulot sotib olish", callback_data='buy')],
            [InlineKeyboardButton("Mahsulotlar ro'yxati", callback_data='list')],
            [InlineKeyboardButton("Mahsulotni o'chirish", callback_data='delete')]
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
        quantity = user_products[user_id][product]['quantity']
        unit = user_products[user_id][product]['unit']
        await query.edit_message_text(f"{product} dan qancha miqdor sotib olmoqchisiz? (Jami: {quantity} {unit})\n"
                                      f"Misal: 5 {unit}")
        return BUYING_QUANTITY_AND_UNIT
    
    elif query.data.startswith('delete_'):
        product = query.data[7:]
        if product in user_products[user_id]:
            del user_products[user_id][product]
            await query.edit_message_text(f"{product} mahsuloti o'chirildi.")
        else:
            await query.edit_message_text(f"{product} mahsuloti topilmadi.")
            
        keyboard = [
            [InlineKeyboardButton("Mahsulot qo'shish", callback_data='add')],
            [InlineKeyboardButton("Mahsulot sotib olish", callback_data='buy')],
            [InlineKeyboardButton("Mahsulotlar ro'yxati", callback_data='list')],
            [InlineKeyboardButton("Mahsulotni o'chirish", callback_data='delete')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Nima qilmoqchisiz?",
            reply_markup=reply_markup
        )
        return SELECTING_ACTION
    
    return SELECTING_ACTION

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store product name and ask for quantity."""
    product_name = update.message.text
    if not product_name or product_name.strip() == "":
        await update.message.reply_text("Iltimos, to'g'ri mahsulot nomini kiriting.")
        return ADDING_PRODUCT
        
    context.user_data['product_name'] = product_name
    await update.message.reply_text(f"{product_name} uchun miqdorni va birlikni kiriting (misal: 5 kg, 10 dona, 500 g):")
    return ADDING_QUANTITY_AND_UNIT

async def add_quantity_and_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store product quantity, unit and go back to selection."""
    user_id = update.effective_user.id
    input_text = update.message.text.strip()
    
    # Miqdor va birlik ajratish uchun regex
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(.+)$', input_text)
    
    if not match:
        await update.message.reply_text("Iltimos, to'g'ri formatda kiriting (misal: 5 kg, 10 dona, 500 g)")
        return ADDING_QUANTITY_AND_UNIT
    
    quantity = float(match.group(1))
    unit = match.group(2).strip()
    
    # Quantity must be positive
    if quantity <= 0:
        await update.message.reply_text("Iltimos, musbat son kiriting.")
        return ADDING_QUANTITY_AND_UNIT
    
    # Valid units
    valid_units = ['dona', 'kg', 'g', 'l', 'ml']
    if unit not in valid_units:
        unit_list = ", ".join(valid_units)
        await update.message.reply_text(f"Iltimos, to'g'ri birlik kiriting. Quyidagi birliklardan foydalaning: {unit_list}")
        return ADDING_QUANTITY_AND_UNIT
        
    product_name = context.user_data.get('product_name')
    if not product_name:
        await update.message.reply_text("Xatolik yuz berdi. Qaytadan boshlang.")
        return ConversationHandler.END
        
    if product_name in user_products[user_id]:
        # Check if units match
        if user_products[user_id][product_name]['unit'] != unit:
            await update.message.reply_text(f"Xatolik! {product_name} mahsuloti uchun avval {user_products[user_id][product_name]['unit']} "
                                           f"birligidan foydalanilgan. Iltimos, bir xil birlikdan foydalaning.")
            return ADDING_QUANTITY_AND_UNIT
            
        user_products[user_id][product_name]['quantity'] += quantity
        await update.message.reply_text(f"{product_name} miqdori {quantity} {unit} qo'shildi. "
                                       f"Jami: {user_products[user_id][product_name]['quantity']} {unit}")
    else:
        user_products[user_id][product_name] = {'quantity': quantity, 'unit': unit}
        await update.message.reply_text(f"{product_name} {quantity} {unit} miqdorida qo'shildi.")
    
    keyboard = [
        [InlineKeyboardButton("Mahsulot qo'shish", callback_data='add')],
        [InlineKeyboardButton("Mahsulot sotib olish", callback_data='buy')],
        [InlineKeyboardButton("Mahsulotlar ro'yxati", callback_data='list')],
        [InlineKeyboardButton("Mahsulotni o'chirish", callback_data='delete')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Nima qilmoqchisiz?", reply_markup=reply_markup)
    return SELECTING_ACTION

async def buy_quantity_and_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process buying products and update inventory."""
    user_id = update.effective_user.id
    input_text = update.message.text.strip()
    
    # Miqdor va birlik ajratish uchun regex
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(.*)$', input_text)
    
    if not match:
        await update.message.reply_text("Iltimos, to'g'ri formatda kiriting (misal: 5 kg, 10 dona)")
        return BUYING_QUANTITY_AND_UNIT
    
    quantity = float(match.group(1))
    
    product = context.user_data.get('product_to_buy')
    if not product:
        await update.message.reply_text("Xatolik yuz berdi. Qaytadan boshlang.")
        return ConversationHandler.END
    
    if quantity <= 0:
        await update.message.reply_text("Iltimos, musbat son kiriting.")
        return BUYING_QUANTITY_AND_UNIT
    
    if product in user_products[user_id]:
        current_quantity = user_products[user_id][product]['quantity']
        unit = user_products[user_id][product]['unit']
        
        if quantity > current_quantity:
            await update.message.reply_text(f"Kechirasiz, omborda faqat {current_quantity} {unit} {product} mavjud.")
            return BUYING_QUANTITY_AND_UNIT
        else:
            user_products[user_id][product]['quantity'] -= quantity
            await update.message.reply_text(f"{quantity} {unit} {product} sotib olindi. "
                                          f"Qolgan miqdor: {user_products[user_id][product]['quantity']} {unit}")
            
            # If quantity becomes 0, remove the product
            if user_products[user_id][product]['quantity'] == 0:
                del user_products[user_id][product]
                await update.message.reply_text(f"{product} tugadi va ro'yxatdan olib tashlandi.")
    else:
        await update.message.reply_text(f"Kechirasiz, {product} mahsuloti mavjud emas.")
        
    keyboard = [
        [InlineKeyboardButton("Mahsulot qo'shish", callback_data='add')],
        [InlineKeyboardButton("Mahsulot sotib olish", callback_data='buy')],
        [InlineKeyboardButton("Mahsulotlar ro'yxati", callback_data='list')],
        [InlineKeyboardButton("Mahsulotni o'chirish", callback_data='delete')]
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
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("No TELEGRAM_TOKEN environment variable found!")
        return

    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(button_handler)
            ],
            ADDING_PRODUCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product)
            ],
            ADDING_QUANTITY_AND_UNIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_quantity_and_unit)
            ],
            BUYING_PRODUCT: [
                CallbackQueryHandler(button_handler)
            ],
            BUYING_QUANTITY_AND_UNIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, buy_quantity_and_unit)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
