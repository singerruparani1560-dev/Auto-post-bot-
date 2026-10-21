import asyncio
import pytz
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant, ChannelInvalid, ChannelPrivate
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta

# Telegram API & Bot Configuration
API_ID = 35327931
API_HASH = "5f3faae927a7c7490a5d986f6f75f35b"
BOT_TOKEN = "8777786687:AAGXRR5WUDpjyVhYghN1-Qr0PWomIqAkhKk"

ADMIN_ID = 8144348712
DB_CHANNEL_ID = -1004455628529

REQUIRED_CHANNELS = [
    "blackbathacker001",
    "bathackermodzzz",
    "batsvvippanelll",
    "blackbatlightbomberrr",
    "batanimationvideos",
    "blackbathackergroup"
]

IST = pytz.timezone("Asia/Kolkata")

# SQLite Database for 24/7 Permanent Job Storage
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}

app = Client("clone_post_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=IST)

USER_BULK_SESSION = {}

# Check User Joined Required Channels (Owner Auto-Bypass)
async def check_user_joined(client, user_id):
    if user_id == ADMIN_ID:
        return True
    for ch in REQUIRED_CHANNELS:
        try:
            member = await client.get_chat_member(f"@{ch}", user_id)
            if member.status in ["kicked", "banned"]:
                return False
        except UserNotParticipant:
            return False
        except (ChannelInvalid, ChannelPrivate):
            continue
        except Exception as e:
            print(f"Verification Check Error for @{ch}: {e}")
            continue
    return True

# Save/Copy Message Safely to Private Database
async def safe_copy_to_db(message):
    try:
        msg = await message.copy(DB_CHANNEL_ID)
        return msg.id
    except Exception as e:
        print(f"DB Copy Error: {e}")
        msg = await message.forward(DB_CHANNEL_ID)
        return msg.id

# Force Join Keyboard Layout
def get_join_keyboard():
    buttons = [
        [InlineKeyboardButton("💀 HACKING CHANNEL", url="https://t.me/blackbathacker001")],
        [InlineKeyboardButton("😎 MODSZ CHANNEL", url="https://t.me/bathackermodzzz")],
        [InlineKeyboardButton("💀 VIP PANEL", url="https://t.me/batsvvippanelll")],
        [InlineKeyboardButton("💀 BOMBER CHANNEL", url="https://t.me/blackbatlightbomberrr")],
        [InlineKeyboardButton("💀 ANIMATION VIDEOS", url="https://t.me/batanimationvideos")],
        [InlineKeyboardButton("🛡️ BACKUP / SUPPORT", url="https://t.me/blackbathackergroup")],
        [InlineKeyboardButton("✅ Verify / सत्यापन करें", callback_data="verify_joined")],
        [
            InlineKeyboardButton("👑 OWNER", url="https://t.me/blackbatowner"),
            InlineKeyboardButton("🫵 MY BEST FRIEND", url="tg://settings")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# Main Menu Keyboard Layout
def get_main_keyboard():
    buttons = [
        [
            InlineKeyboardButton("📢 Main Channel", url="https://t.me/blackbathacker001"),
            InlineKeyboardButton("💬 Support Group", url="https://t.me/blackbathackergroup")
        ],
        [
            InlineKeyboardButton("🌀 Clone This Bot", callback_data="clone_info"),
            InlineKeyboardButton("👑 Owner", url="https://t.me/blackbatowner")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# /start Command Handler
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    user_id = message.from_user.id
    is_joined = await check_user_joined(client, user_id)
    
    if not is_joined:
        text = (
            "⚔️ **B.A.T HACKER NETWORK** ⚔️\n\n"
            "🍿 **HELLO GUYS** 🍿\n\n"
            "───────────────\n"
            "🇮🇳 **HINGLISH:**\n"
            "⚠️ **Access Denied!** Bot ko start karne ke liye pehle niche diye gaye **sabhi 6 channels ko join karna compulsory hai.** Join karne ke baad **'✅ Verify'** button par click karein.\n\n"
            "🇮🇳 **HINDI:**\n"
            "⚠️ **एक्सेस अस्वीकृत!** बोट को शुरू करने के लिए नीचे दिए गए **सभी 6 चैनलों को ज्वाइन करना अनिवार्य है।** ज्वाइन करने के बाद **'✅ Verify'** बटन पर क्लिक करें।\n\n"
            "🇬🇧 **ENGLISH:**\n"
            "⚠️ **Access Denied!** To start using this bot, you must **join all 6 channels listed below.** After joining, click on the **'✅ Verify'** button.\n"
            "───────────────"
        )
        await message.reply_text(text, reply_markup=get_join_keyboard(), disable_web_page_preview=True)
        return

    welcome_text = (
        f"👋 **Welcome {message.from_user.first_name}!**\n\n"
        f"🤖 **Black Bat Auto Post & Bulk Queue Scheduler Bot**\n\n"
        f"📖 **Command Usages:**\n"
        f"1️⃣ Single Schedule: `/schedule @channel YYYY-MM-DD HH:MM`\n"
        f"2️⃣ 1-Day Gap Interval: `/interval @channel StartDate StartTime Count`\n"
        f"3️⃣ All 6 Channels Schedule: `/multiinterval StartDate StartTime Count`\n"
        f"4️⃣ Instant Post All Channels: `/postnow` (Reply Required)\n"
        f"5️⃣ Bulk Queue Schedule:\n"
        f"   `/bulk_schedule StartDate StartTime GapInDays @channel1 @channel2 ...`\n\n"
        f"🛠️ **Other Commands:**\n"
        f"• `/list` - Scheduled jobs dekhein.\n"
        f"• `/cancel job_ID` - Job cancel karein.\n"
        f"• `/reschedule job_ID YYYY-MM-DD HH:MM` - Time badlein."
    )
    await message.reply_text(welcome_text, reply_markup=get_main_keyboard())

# Callback Query Verification Handler
@app.on_callback_query(filters.regex("verify_joined"))
async def verify_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    is_joined = await check_user_joined(client, user_id)

    if is_joined:
        await callback_query.answer("✅ Verification Successful! Welcome!", show_alert=True)
        welcome_text = f"👋 **Welcome {callback_query.from_user.first_name}!**\n\n✅ Account Verified! Aap ab bot use kar sakte hain."
        await callback_query.message.edit_text(welcome_text, reply_markup=get_main_keyboard())
    else:
        await callback_query.answer("❌ Aapne abhi tak saare 6 channels join nahi kiye hain!", show_alert=True)

# Clone Info Callback
@app.on_callback_query(filters.regex("clone_info"))
async def clone_callback(client, callback_query: CallbackQuery):
    clone_text = (
        "🌀 **Apna Clone Bot Kaise Banayein?**\n\n"
        "1️⃣ `@BotFather` par jaakar `/newbot` se naya bot banayein.\n"
        "2️⃣ BotFather se **BOT TOKEN** copy karein.\n"
        "3️⃣ Owner (`@blackbatowner`) ko token bhej kar apna clone bot set karwayein!\n\n"
        "🛡️ *Powered by Black Bat Auto Post Engine.*"
    )
    await callback_query.answer()
    await callback_query.message.reply_text(clone_text)

# Execution Function for Sending Scheduled Post
async def send_scheduled_post(target_channels, message_id):
    try:
        channels_list = target_channels.split(",")
        for ch in channels_list:
            ch = ch.strip()
            if ch:
                await app.copy_message(chat_id=ch, from_chat_id=DB_CHANNEL_ID, message_id=message_id)
                print(f"[{datetime.now(IST)}] Post successfully uploaded to {ch}")
    except Exception as e:
        print(f"Error sending post: {e}")

# /postnow Command - Instant Upload to All 6 Channels
@app.on_message(filters.command("postnow") & filters.user(ADMIN_ID))
async def post_now_handler(client, message):
    try:
        if not message.reply_to_message:
            await message.reply_text("❌ **Kripya post ko REPLY karke `/postnow` command dein!**")
            return

        db_msg_id = await safe_copy_to_db(message.reply_to_message)
        await message.reply_text("⏳ **Sabhi 6 Channels me Upload ho rha hai...**")

        success_count = 0
        for ch in REQUIRED_CHANNELS:
            target_ch = f"@{ch}"
            try:
                await app.copy_message(chat_id=target_ch, from_chat_id=DB_CHANNEL_ID, message_id=db_msg_id)
                success_count += 1
            except Exception as e:
                print(f"Failed for {target_ch}: {e}")

        await message.reply_text(f"✅ **Instant Post Done!**\n📢 Total **{success_count}/6 Channels** me post upload ho gaya.")

    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)}`")

# /schedule Command - Single Channel Schedule
@app.on_message(filters.command("schedule") & filters.user(ADMIN_ID))
async def schedule_handler(client, message):
    try:
        if not message.reply_to_message:
            await message.reply_text("❌ **Kripya post ko REPLY karke command dein!**")
            return

        args = message.text.split(" ")
        if len(args) < 4:
            await message.reply_text("❌ **Format:** `/schedule @channel_username YYYY-MM-DD HH:MM`")
            return

        target_channel = args[1]
        date_str = args[2]
        time_str = args[3]

        full_time_str = f"{date_str} {time_str}"
        naive_date = datetime.strptime(full_time_str, "%Y-%m-%d %H:%M")
        run_date = IST.localize(naive_date)

        db_msg_id = await safe_copy_to_db(message.reply_to_message)
        job_id = f"job_{db_msg_id}"

        scheduler.add_job(
            send_scheduled_post,
            'date',
            run_date=run_date,
            args=[target_channel, db_msg_id],
            id=job_id,
            replace_existing=True
        )

        await message.reply_text(
            f"✅ **Post Schedule Ho Gaya!**\n\n"
            f"🆔 **Job ID:** `{job_id}`\n"
            f"📢 **Target:** {target_channel}\n"
            f"⏰ **Time (IST):** {full_time_str}\n"
            f"🗄️ **DB Msg ID:** `{db_msg_id}`"
        )

    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)}`")

# /multiinterval Command - All 6 Channels Schedule
@app.on_message(filters.command("multiinterval") & filters.user(ADMIN_ID))
async def multi_interval_schedule_handler(client, message):
    try:
        if not message.reply_to_message:
            await message.reply_text("❌ **Kripya post ko REPLY karke command dein!**")
            return

        args = message.text.split(" ")
        if len(args) < 4:
            await message.reply_text("❌ **Format:** `/multiinterval StartDate StartTime RepeatCount`\nExample: `/multiinterval 2026-10-22 14:00 1`")
            return

        start_date_str = args[1]
        start_time_str = args[2]
        repeat_count = int(args[3])

        start_full_time = f"{start_date_str} {start_time_str}"
        base_datetime = datetime.strptime(start_full_time, "%Y-%m-%d %H:%M")

        db_msg_id = await safe_copy_to_db(message.reply_to_message)
        total_scheduled = 0

        for ch_index, ch in enumerate(REQUIRED_CHANNELS):
            target_ch = f"@{ch}"
            for i in range(repeat_count):
                scheduled_dt = base_datetime + timedelta(days=i * 2)
                run_date = IST.localize(scheduled_dt)
                
                job_id = f"job_multi_{db_msg_id}_{ch_index+1}_{i+1}"

                scheduler.add_job(
                    send_scheduled_post,
                    'date',
                    run_date=run_date,
                    args=[target_ch, db_msg_id],
                    id=job_id,
                    replace_existing=True
                )
                total_scheduled += 1

        await message.reply_text(
            f"🚀 **Multi-Channel Schedule Set Ho Gaya!**\n\n"
            f"📊 **Total Jobs Created:** {total_scheduled}\n"
            f"⏰ **First Post Time:** `{start_full_time}`\n"
            f"🗄️ **DB Msg ID:** `{db_msg_id}`"
        )

    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)}`")

# /bulk_schedule Command
@app.on_message(filters.command("bulk_schedule") & filters.user(ADMIN_ID))
async def bulk_schedule_handler(client, message):
    try:
        args = message.text.split(" ")
        if len(args) < 5:
            await message.reply_text("❌ **Format:** `/bulk_schedule StartDate StartTime GapInDays @channel1 @channel2 ...`")
            return

        start_date_str = args[1]
        start_time_str = args[2]
        gap_days = int(args[3])
        target_channels = ",".join(args[4:])

        start_full_time = f"{start_date_str} {start_time_str}"
        base_datetime = datetime.strptime(start_full_time, "%Y-%m-%d %H:%M")

        USER_BULK_SESSION[message.from_user.id] = {
            "start_dt": base_datetime,
            "gap_days": gap_days,
            "channels": target_channels,
            "count": 0
        }

        await message.reply_text(
            f"🚀 **Bulk Queue Collector Active!**\n\n"
            f"📅 **Start Date:** `{start_full_time}`\n"
            f"🗓️ **Gap:** Har `{gap_days}` Din Baad\n"
            f"📢 **Targets:** `{target_channels}`\n\n"
            f"👉 Posts bhejte rahein. Mode stop karne ke liye `/done_bulk` bhein."
        )

    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)}`")

# Bulk Message Collector Listener
@app.on_message(filters.private & filters.user(ADMIN_ID) & ~filters.command(["start", "schedule", "interval", "multiinterval", "bulk_schedule", "done_bulk", "list", "cancel", "reschedule", "postnow"]))
async def bulk_collector_listener(client, message):
    user_id = message.from_user.id
    if user_id in USER_BULK_SESSION:
        session = USER_BULK_SESSION[user_id]
        
        post_index = session["count"]
        scheduled_dt = session["start_dt"] + timedelta(days=post_index * session["gap_days"])
        run_date = IST.localize(scheduled_dt)

        db_msg_id = await safe_copy_to_db(message)
        job_id = f"job_queue_{db_msg_id}"

        scheduler.add_job(
            send_scheduled_post,
            'date',
            run_date=run_date,
            args=[session["channels"], db_msg_id],
            id=job_id,
            replace_existing=True
        )

        session["count"] += 1
        await message.reply_text(
            f"✅ **Post #{session['count']} Queue Me Set Ho Gaya!**\n"
            f"⏰ **Scheduled Time:** `{scheduled_dt.strftime('%Y-%m-%d %H:%M')}`\n"
            f"🆔 **Job ID:** `{job_id}`\n\n"
            f"*(Agle posts bhejte rahein, ya finish karne ke liye `/done_bulk` likhein)*"
        )

# /done_bulk Command
@app.on_message(filters.command("done_bulk") & filters.user(ADMIN_ID))
async def done_bulk_handler(client, message):
    user_id = message.from_user.id
    if user_id in USER_BULK_SESSION:
        total = USER_BULK_SESSION[user_id]["count"]
        del USER_BULK_SESSION[user_id]
        await message.reply_text(f"🎉 **Bulk Collector Off!** Total **{total} Naye Posts** successfully schedule ho gaye!")
    else:
        await message.reply_text("ℹ️ Koi active bulk session nahi mila.")

# /list Command
@app.on_message(filters.command("list") & filters.user(ADMIN_ID))
async def list_jobs(client, message):
    jobs = scheduler.get_jobs()
    if not jobs:
        await message.reply_text("ℹ️ Abhi koi bhi post schedule me nahi hai.")
        return

    text = f"📋 **Scheduled Posts List ({len(jobs)} Total Jobs):**\n\n"
    for job in jobs[:10]:
        target = job.args[0]
        time_str = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
        text += f"🔹 **Job ID:** `{job.id}`\n📢 **Target:** {target}\n⏰ **Time:** {time_str}\n\n"

    if len(jobs) > 10:
        text += f"*(Total {len(jobs)} jobs set hain)*"

    await message.reply_text(text)

# /cancel Command
@app.on_message(filters.command("cancel") & filters.user(ADMIN_ID))
async def cancel_job(client, message):
    try:
        args = message.text.split(" ")
        if len(args) < 2:
            await message.reply_text("❌ **Format:** `/cancel job_ID`")
            return

        job_id = args[1]
        job = scheduler.get_job(job_id)

        if job:
            scheduler.remove_job(job_id)
            await message.reply_text(f"🗑️ Post cancel ho gaya! 🆔 `{job_id}`")
        else:
            await message.reply_text("❌ Job ID nahi mili.")

    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)}`")

# Main Startup Function
async def main():
    scheduler.start()
    await app.start()
    
    try:
        await app.get_chat(DB_CHANNEL_ID)
        print("DB Channel successfully initialized!")
    except Exception as e:
        print(f"Warning: Could not fetch DB Channel directly: {e}")

    print("Bot is running successfully with all features...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
