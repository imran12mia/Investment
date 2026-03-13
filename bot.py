import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# বট টোকেন - @BotFather থেকে আপনার টোকেন এখানে দিন
BOT_TOKEN = "8263367529:AAEyovHbcyeF1tAptufF4b_mf2B-RAi5hFI" 

# এডমিন ইউজার আইডি - এডমিনের Telegram ইউজার আইডি দিন (যেমন: 6220609091)
# এডমিন ইউজার আইডি পেতে, @userinfobot এ গিয়ে আপনার আইডি দেখতে পারেন।
ADMIN_USER_ID = YOUR_ADMIN_TELEGRAM_ID_HERE # যেমন: 6220609091

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ব্যবহারকারীর ডেটা সংরক্ষণের জন্য একটি ডামি স্টোরেজ (প্রকৃতপক্ষে ডেটাবেস ব্যবহার করতে হবে) ---
# এটি শুধুমাত্র এই উদাহরণের জন্য। বাস্তব প্রকল্পে একটি ডেটাবেস ব্যবহার করুন।
user_data = {} # {chat_id: {'balance': 0, 'vip_status': 'None', 'last_deposit_id': None, 'last_withdraw_amount': None, 'last_withdraw_number': None}}

def get_user_data(user_id):
    if user_id not in user_data:
        user_data[user_id] = {'balance': 0, 'vip_status': 'None', 'vip_expiry': None}
    return user_data[user_id]

# --- কমান্ড হ্যান্ডলার ফাংশন ---

async def start(update: Update, context) -> None:
    """বট শুরু হলে স্বাগত বার্তা এবং প্রধান মেনু দেখায়।"""
    user = update.effective_user
    await update.message.reply_html(
        f"👋 স্বাগতম, {user.mention_html()}! আপনার পছন্দের অপশনটি বেছে নিন:",
        reply_markup=main_menu_keyboard()
    )

def main_menu_keyboard():
    """প্রধান মেনুর জন্য ইনলাইন কীবোর্ড তৈরি করে।"""
    keyboard = [
        [
            InlineKeyboardButton("💰 ডিপোজিট", callback_data='deposit'),
            InlineKeyboardButton("💸 উত্তোলন", callback_data='withdraw')
        ],
        [
            InlineKeyboardButton("🌟 ভিআইপি প্যাকেজ", callback_data='vip_packages'),
            InlineKeyboardButton("📊 আমার ব্যালেন্স", callback_data='my_balance')
        ],
        [
            InlineKeyboardButton("📞 সাপোর্ট", callback_data='support')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_callback_query(update: Update, context) -> None:
    """ইনলাইন কীবোর্ড বাটনে ক্লিক হ্যান্ডেল করে।"""
    query = update.callback_query
    await query.answer() # ক্যোয়ারী অ্যানসার করুন যাতে লোডিং স্পিনার চলে যায়

    if query.data == 'deposit':
        await send_deposit_instructions(query)
    elif query.data == 'withdraw':
        await send_withdraw_instructions(query)
    elif query.data == 'vip_packages':
        await send_vip_packages(query)
    elif query.data == 'my_balance':
        await send_my_balance(query)
    elif query.data == 'support':
        await send_support_info(query)
    elif query.data.startswith('activate_vip_'):
        await activate_vip_package(query, context, query.data.replace('activate_vip_', ''))
    elif query.data == 'back_to_main':
        await query.edit_message_text(
            text="👋 আপনার পছন্দের অপশনটি বেছে নিন:",
            reply_markup=main_menu_keyboard()
        )

# --- ডিপোজিট ফাংশন ---
async def send_deposit_instructions(query: Update.callback_query) -> None:
    """ডিপোজিট নির্দেশাবলী পাঠায় এবং ইনপুট সংগ্রহ করে।"""
    await query.edit_message_text(
        text="💰 ডিপোজিট করতে নিচের ধাপগুলো অনুসরণ করুন:\n\n"
             "১. আমাদের বিকাশ/নগদ নাম্বারে সেন্ড মানি করুন: `01919302814`\n"
             "২. কত টাকা ডিপোজিট করেছেন, তা লিখুন।\n"
             "৩. সেন্ড মানি করার পর প্রাপ্ত ট্রানজেকশন আইডি (Txn ID) লিখুন।\n\n"
             "আপনার ডিপোজিটটি এডমিন কর্তৃক যাচাইয়ের পর আপনার ব্যালেন্সে যোগ করা হবে।\n\n"
             "প্রথমে আপনার ডিপোজিট অ্যামাউন্ট লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মূল মেনু", callback_data='back_to_main')]])
    )
    context.user_data['state'] = 'awaiting_deposit_amount'

async def handle_deposit_input(update: Update, context) -> None:
    """ব্যবহারকারীর ডিপোজিট অ্যামাউন্ট এবং ট্রানজেকশন আইডি হ্যান্ডেল করে।"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text

    if context.user_data.get('state') == 'awaiting_deposit_amount':
        try:
            amount = float(text)
            if amount <= 0:
                await update.message.reply_text("পরিমাণ ০ এর বেশি হতে হবে। আবার চেষ্টা করুন।")
                return
            context.user_data['deposit_amount'] = amount
            context.user_data['state'] = 'awaiting_transaction_id'
            await update.message.reply_text("এখন আপনার ট্রানজেকশন আইডি (Txn ID) দিন:")
        except ValueError:
            await update.message.reply_text("ভুল পরিমাণ। শুধুমাত্র সংখ্যা লিখুন।")
    elif context.user_data.get('state') == 'awaiting_transaction_id':
        txn_id = text
        deposit_amount = context.user_data.get('deposit_amount')

        await update.message.reply_text(
            f"✅ আপনার ডিপোজিট রিকোয়েস্ট জমা দেওয়া হয়েছে!\n"
            f"পরিমাণ: {deposit_amount} টাকা\n"
            f"ট্রানজেকশন আইডি: `{txn_id}`\n\n"
            "এডমিন আপনার রিকোয়েস্ট দ্রুত যাচাই করবেন। ধন্যবাদ!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মূল মেনু", callback_data='back_to_main')]])
        )
        context.user_data.clear() # স্টেট রিসেট করুন

        # এডমিনকে নোটিফিকেশন পাঠান
        admin_message = (
            f"🔔 নতুন ডিপোজিট রিকোয়েস্ট!\n"
            f"ইউজার আইডি: `{user_id}`\n"
            f"ইউজারনেম: @{update.effective_user.username or 'N/A'}\n"
            f"পরিমাণ: {deposit_amount} টাকা\n"
            f"ট্রানজেকশন আইডি: `{txn_id}`\n"
            f"বিকাশ/নগদ নাম্বার: `01919302814`" # এখানে আপনার নির্দিষ্ট নাম্বার দিন
        )
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)

    else:
        # যদি কোনো নির্দিষ্ট স্টেট না থাকে, তাহলে এটি একটি সাধারণ টেক্সট মেসেজ
        await update.message.reply_text("আমি বুঝতে পারছি না। মূল মেনুতে ফিরে যেতে /start টাইপ করুন।")


# --- উত্তোলন ফাংশন ---
async def send_withdraw_instructions(query: Update.callback_query) -> None:
    """উত্তোলনের নির্দেশাবলী পাঠায় এবং ইনপুট সংগ্রহ করে।"""
    await query.edit_message_text(
        text="💸 টাকা উত্তোলন করতে নিচের তথ্যগুলো দিন:\n\n"
             "১. আপনি কত টাকা উত্তোলন করতে চান? (ন্যূনতম উত্তোলন: ১০০ টাকা)\n"
             "২. আপনার বিকাশ/নগদ নাম্বার দিন যেখানে টাকা পাঠাতে হবে।\n\n"
             "প্রথমে আপনার উত্তোলনের পরিমাণ লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মূল মেনু", callback_data='back_to_main')]])
    )
    context.user_data['state'] = 'awaiting_withdraw_amount'

async def handle_withdraw_input(update: Update, context) -> None:
    """ব্যবহারকারীর উত্তোলনের পরিমাণ এবং নাম্বার হ্যান্ডেল করে।"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text
    user_data_obj = get_user_data(user_id) # ব্যবহারকারীর ব্যালেন্স অ্যাক্সেস করতে

    if context.user_data.get('state') == 'awaiting_withdraw_amount':
        try:
            amount = float(text)
            if amount <= 0:
                await update.message.reply_text("পরিমাণ ০ এর বেশি হতে হবে। আবার চেষ্টা করুন।")
                return
            if amount < 100:
                await update.message.reply_text("ন্যূনতম উত্তোলন ১০০ টাকা। অনুগ্রহ করে আরও টাকা লিখুন।")
                return
            # এখানে ব্যালেন্স চেক করা হবে (যদি ডেটাবেস থাকে)
            if amount > user_data_obj['balance']: # ডামি ব্যালেন্স চেক
                await update.message.reply_text(f"আপনার পর্যাপ্ত ব্যালেন্স নেই। আপনার বর্তমান ব্যালেন্স: {user_data_obj['balance']} টাকা।")
                context.user_data.clear()
                return

            context.user_data['withdraw_amount'] = amount
            context.user_data['state'] = 'awaiting_withdraw_number'
            await update.message.reply_text("এখন আপনার বিকাশ/নগদ নাম্বার দিন:")
        except ValueError:
            await update.message.reply_text("ভুল পরিমাণ। শুধুমাত্র সংখ্যা লিখুন।")
    elif context.user_data.get('state') == 'awaiting_withdraw_number':
        withdraw_number = text
        withdraw_amount = context.user_data.get('withdraw_amount')

        await update.message.reply_text(
            f"✅ আপনার উত্তোলন রিকোয়েস্ট জমা দেওয়া হয়েছে!\n"
            f"পরিমাণ: {withdraw_amount} টাকা\n"
            f"নাম্বার: `{withdraw_number}`\n\n"
            "এডমিন আপনার রিকোয়েস্ট দ্রুত যাচাই করবেন এবং টাকা পাঠিয়ে দেবেন।\n"
            "আপনার ব্যালেন্স থেকে (উত্তোলন পরিমাণ + ফি) টাকা কেটে নেওয়া হবে।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মূল মেনু", callback_data='back_to_main')]])
        )
        context.user_data.clear() # স্টেট রিসেট করুন

        # এডমিনকে নোটিফিকেশন পাঠান
        admin_message = (
            f"🔔 নতুন উত্তোলন রিকোয়েস্ট!\n"
            f"ইউজার আইডি: `{user_id}`\n"
            f"ইউজারনেম: @{update.effective_user.username or 'N/A'}\n"
            f"পরিমাণ: {withdraw_amount} টাকা\n"
            f"উত্তোলন নাম্বার: `{withdraw_number}`\n"
            f"বর্তমান ব্যালেন্স (ইউজার): {user_data_obj['balance']} টাকা"
        )
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)

    else:
        # যদি কোনো নির্দিষ্ট স্টেট না থাকে
        await update.message.reply_text("আমি বুঝতে পারছি না। মূল মেনুতে ফিরে যেতে /start টাইপ করুন।")


# --- ভিআইপি প্যাকেজ ফাংশন ---
async def send_vip_packages(query: Update.callback_query) -> None:
    """ভিআইপি প্যাকেজের তালিকা দেখায়।"""
    keyboard = [
        [InlineKeyboardButton("👑 VIP One (500 টাকা)", callback_data='activate_vip_1')],
        [InlineKeyboardButton("👑 VIP Two (1000 টাকা)", callback_data='activate_vip_2')],
        [InlineKeyboardButton("👑 VIP Three (2000 টাকা)", callback_data='activate_vip_3')],
        [InlineKeyboardButton("👑 VIP Four (3000 টাকা)", callback_data='activate_vip_4')],
        [InlineKeyboardButton("👑 VIP Five (4000 টাকা)", callback_data='activate_vip_5')],
        [InlineKeyboardButton("🔙 মূল মেনু", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="🌟 আমাদের ভিআইপি প্যাকেজগুলো দেখে নিন:\n\n"
             "👑 ভিআইপি ওয়ান:\n৫০০ টাকা ডিপোজিট করলে প্রতিদিন ৫ টাকা পাবে। মেয়াদ: ৩৬৫ দিন।\n\n"
             "👑 ভিআইপি টু:\n১০০০ টাকা ডিপোজিট করলে প্রতিদিন ১০ টাকা ইনকাম। মেয়াদ: ৩৬৫ দিন।\n\n"
             "👑 ভিআইপি থ্রি:\n২০০০ টাকা ডিপোজিট করলে প্রতিদিন ২০ টাকা ইনকাম। মেয়াদ: ৩৬৫ দিন।\n\n"
             "👑 ভিআইপি ফোর:\n৩০০০ টাকা ডিপোজিট করলে প্রতিদিন ২৫ টাকা ইনকাম। মেয়াদ: ৩৬৫ দিন।\n\n"
             "👑 ভিআইপি ফাইভ:\n৪০০০ টাকা ডিপোজিট করলে প্রতিদিন ৪০ টাকা ইনকাম। মেয়াদ: ৩৬৫ দিন।\n\n"
             "আপনার ব্যালেন্স থেকে প্যাকেজের মূল্য স্বয়ংক্রিয়ভাবে কেটে নেওয়া হবে।",
        reply_markup=reply_markup
    )

async def activate_vip_package(query: Update.callback_query, context, vip_level: str) -> None:
    """ভিআইপি প্যাকেজ সক্রিয় করে (ব্যালেন্স চেক সহ)।"""
    user_id = query.from_user.id
    user_data_obj = get_user_data(user_id)

    vip_packages_info = {
        '1': {'cost': 500, 'daily_income': 5, 'name': 'VIP One'},
        '2': {'cost': 1000, 'daily_income': 10, 'name': 'VIP Two'},
        '3': {'cost': 2000, 'daily_income': 20, 'name': 'VIP Three'},
        '4': {'cost': 3000, 'daily_income': 25, 'name': 'VIP Four'},
        '5': {'cost': 4000, 'daily_income': 40, 'name': 'VIP Five'},
    }

    package_info = vip_packages_info.get(vip_level)

    if not package_info:
        await query.edit_message_text("অকার্যকর ভিআইপি প্যাকেজ।", reply_markup=main_menu_keyboard())
        return

    cost = package_info['cost']
    package_name = package_info['name']

    if user_data_obj['balance'] >= cost:
        user_data_obj['balance'] -= cost # ডামি ব্যালেন্স বিয়োগ
        user_data_obj['vip_status'] = package_name
        # এখানে মেয়াদ যোগ করার লজিক আসবে (datetime ব্যবহার করে)
        # user_data_obj['vip_expiry'] = datetime.now() + timedelta(days=365) 

        await query.edit_message_text(
            f"🎉 অভিনন্দন! আপনার {package_name} প্যাকেজটি সক্রিয় করা হয়েছে।\n"
            f"আপনার বর্তমান ব্যালেন্স: {user_data_obj['balance']} টাকা।\n"
            f"আপনি প্রতিদিন {package_info['daily_income']} টাকা ইনকাম পাবেন (এই ফাংশনটি নিজে বাস্তবায়ন করতে হবে)।\n"
            f"মেয়াদ: ৩৬৫ দিন।", # এখানে প্রকৃত মেয়াদ দেখাবে যখন ডেটটাইম লজিক যোগ হবে
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মূল মেনু", callback_data='back_to_main')]])
        )
        # এডমিনকে ভিআইপি সক্রিয়করণের নোটিফিকেশন
        admin_message = (
            f"🔔 ভিআইপি প্যাকেজ সক্রিয়করণ!\n"
            f"ইউজার আইডি: `{user_id}`\n"
            f"ইউজারনেম: @{query.from_user.username or 'N/A'}\n"
            f"প্যাকেজ: {package_name}\n"
            f"প্যাকেজ মূল্য: {cost} টাকা\n"
            f"বর্তমান ব্যালেন্স (ইউজার): {user_data_obj['balance']} টাকা"
        )
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)

    else:
        await query.edit_message_text(
            f"দুঃখিত! আপনার ব্যালেন্স পর্যাপ্ত নয়।\n"
            f"আপনার বর্তমান ব্যালেন্স: {user_data_obj['balance']} টাকা।\n"
            f"{package_name} সক্রিয় করতে আরও {cost - user_data_obj['balance']} টাকা ডিপোজিট করুন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 ডিপোজিট", callback_data='deposit'),
                                               InlineKeyboardButton("🔙 মূল মেনু", callback_data='back_to_main')]])
        )

# --- আমার ব্যালেন্স ফাংশন ---
async def send_my_balance(query: Update.callback_query) -> None:
    """ব্যবহারকারীর বর্তমান ব্যালেন্স এবং ভিআইপি স্ট্যাটাস দেখায়।"""
    user_id = query.from_user.id
    user_data_obj = get_user_data(user_id)
    
    balance_text = (
        f"📊 আপনার বর্তমান ব্যালেন্স: {user_data_obj['balance']} টাকা।\n"
        f"👑 আপনার ভিআইপি স্ট্যাটাস: {user_data_obj['vip_status']}"
    )
    # যদি ভিআইপি মেয়াদ থাকে, তবে সেটিও যোগ করুন
    # if user_data_obj['vip_expiry']:
    #     balance_text += f" (মেয়াদ: {user_data_obj['vip_expiry'].strftime('%Y-%m-%d')})"
    
    await query.edit_message_text(
        text=balance_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মূল মেনু", callback_data='back_to_main')]])
    )

# --- সাপোর্ট ফাংশন ---
async def send_support_info(query: Update.callback_query) -> None:
    """সাপোর্ট যোগাযোগের তথ্য দেখায়।"""
    await query.edit_message_text(
        text="📞 আমাদের সাপোর্ট টিমের সাথে যোগাযোগ করুন:\n"
             "টেলিগ্রাম ইউজারনেম: `@আপনার_সাপোর্ট_ইউজারনেম` (এখানে আপনার সাপোর্ট ইউজারনেম দিন)\n"
             "অথবা\n"
             "ইমেইল: `support@yourdomain.com` (এখানে আপনার ইমেইল দিন)\n\n"
             "দ্রুত সহায়তার জন্য আপনার ইউজার আইডিটি উল্লেখ করুন: `{query.from_user.id}`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মূল মেনু", callback_data='back_to_main')]])
    )

# --- প্রধান ফাংশন ---
async def main() -> None:
    """বট শুরু করার জন্য প্রধান এন্ট্রি পয়েন্ট।"""
    application = Application.builder().token(BOT_TOKEN).build()

    # হ্যান্ডলার যোগ করুন
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_deposit_input)) # ডিপোজিট/উত্তোলন ইনপুট হ্যান্ডেল করার জন্য

    logger.info("Bot started polling.")
    # পোলিং শুরু করুন
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__':
    import asyncio
    asyncio.run(main())
