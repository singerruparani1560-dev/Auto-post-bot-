import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

# Pyrogram 2.x calls asyncio.get_event_loop() while importing.
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import pytz
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant, ChannelInvalid, ChannelPrivate
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore


def env_required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Set the {name} environment variable in Render.")
    return value


API_ID = int(env_required("35327931"))
API_HASH = env_required("5f3faae927a7c7490a5d986f6f75f35b")
BOT_TOKEN = env_required("8777786687:AAGXRR5WUDpjyVhYghN1-Qr0PWomIqAkhKk")
ADMIN_ID = int(env_required("8144348712"))
DB_CHANNEL_ID = int(env_required("-1004455628529"))

REQUIRED_CHANNELS = [
    x.strip().lstrip("@") for x in os.getenv(
        "REQUIRED_CHANNELS",
        "blackbathacker001,bathackermodzzz,batsvvippanelll,"
        "blackbatlightbomberrr,batanimationvideos,blackbathackergroup"
    ).split(",") if x.strip()
]
IST = pytz.timezone("Asia/Kolkata")
DATA_DIR = Path(os.getenv("DATA_DIR", ".")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Client(
    "clone_post_bot", api_id=API_ID, api_hash=API_HASH,
    bot_token=BOT_TOKEN, workdir=str(DATA_DIR)
)
scheduler = AsyncIOScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{DATA_DIR / 'jobs.sqlite'}")},
    timezone=IST,
)
BULK = {}


def parse_time(date_text, time_text):
    return IST.localize(datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M"))


def fmt_time(dt):
    return dt.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def check_future(dt):
    if dt <= datetime.now(IST):
        raise ValueError("Time must be in the future (India/IST).")


async def check_user_joined(client, user_id):
    if user_id == ADMIN_ID:
        return True
    for channel in REQUIRED_CHANNELS:
        try:
            member = await client.get_chat_member(f"@{channel}", user_id)
            status = str(member.status).lower()
            if status.endswith("kicked") or status.endswith("banned"):
                return False
        except UserNotParticipant:
            return False
        except (ChannelInvalid, ChannelPrivate) as exc:
            print(f"Cannot verify @{channel}: {exc}")
            return False
        except Exception as exc:
            print(f"Membership check failed for @{channel}: {exc}")
            return False
    return True


async def save_post(message):
    try:
        copied = await message.copy(DB_CHANNEL_ID)
    except Exception as exc:
        print(f"Copy failed; trying forward: {exc}")
        copied = await message.forward(DB_CHANNEL_ID)
    return copied.id


def join_keyboard():
    rows = [
        [InlineKeyboardButton("💀 HACKING CHANNEL", url="https://t.me/blackbathacker001")],
        [InlineKeyboardButton("😎 MODSZ CHANNEL", url="https://t.me/bathackermodzzz")],
        [InlineKeyboardButton("💀 VIP PANEL", url="https://t.me/batsvvippanelll")],
        [InlineKeyboardButton("💀 BOMBER CHANNEL", url="https://t.me/blackbatlightbomberrr")],
        [InlineKeyboardButton("💀 ANIMATION VIDEOS", url="https://t.me/batanimationvideos")],
        [InlineKeyboardButton("🛡️ BACKUP / SUPPORT", url="https://t.me/blackbathackergroup")],
        [InlineKeyboardButton("✅ Verify / सत्यापन करें", callback_data="verify_joined")],
        [InlineKeyboardButton("👑 OWNER", url="https://t.me/blackbatowner")],
    ]
    return InlineKeyboardMarkup(rows)


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Main Channel", url="https://t.me/blackbathacker001"),
            InlineKeyboardButton("💬 Support Group", url="https://t.me/blackbathackergroup"),
        ],
        [
            InlineKeyboardButton("🌀 Clone This Bot", callback_data="clone_info"),
            InlineKeyboardButton("👑 Owner", url="https://t.me/blackbatowner"),
        ],
    ])


def welcome(name):
    return (
        f"👋 **Welcome {name}!**\n\n"
        "🤖 **Black Bat Auto Post & Bulk Queue Scheduler Bot**\n\n"
        "**Admin commands:**\n"
        "• `/schedule @channel YYYY-MM-DD HH:MM` (reply to post)\n"
        "• `/interval @channel YYYY-MM-DD HH:MM Count GapDays` (reply to post)\n"
        "• `/multiinterval YYYY-MM-DD HH:MM Count` (reply to post; all channels, 2-day gap)\n"
        "• `/postnow` (reply to post; publish to all channels)\n"
        "• `/bulk_schedule YYYY-MM-DD HH:MM GapDays @channel1 @channel2` then send posts\n"
        "• `/done_bulk`, `/list`, `/cancel job_ID`, `/reschedule job_ID YYYY-MM-DD HH:MM`"
    )


@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    if not message.from_user:
        return
    if not await check_user_joined(client, message.from_user.id):
        await message.reply_text(
            "⚔️ **B.A.T HACKER NETWORK** ⚔️\n\n"
            "Bot use karne se pehle neeche diye gaye sabhi 6 channels join karein, "
            "phir **✅ Verify** dabayein.\n\n"
            "Join all 6 required channels and press **✅ Verify**.",
            reply_markup=join_keyboard(), disable_web_page_preview=True
        )
        return
    await message.reply_text(welcome(message.from_user.first_name or "there"),
                             reply_markup=main_keyboard())


@app.on_callback_query(filters.regex(r"^verify_joined$"))
async def verify_handler(client, query: CallbackQuery):
    if await check_user_joined(client, query.from_user.id):
        await query.answer("✅ Verification successful!", show_alert=True)
        await query.message.edit_text(welcome(query.from_user.first_name or "there"),
                                      reply_markup=main_keyboard())
    else:
        await query.answer("❌ Join all 6 channels first.", show_alert=True)


@app.on_callback_query(filters.regex(r"^clone_info$"))
async def clone_handler(client, query: CallbackQuery):
    await query.answer()
    await query.message.reply_text(
        "🌀 **Clone bot setup**\n\n"
        "1. Create a bot with `@BotFather` using `/newbot`.\n"
        "2. Keep its token private.\n"
        "3. Contact the owner for setup."
    )


async def send_scheduled_post(target_channels, message_id):
    channels = target_channels if isinstance(target_channels, list) else str(target_channels).split(",")
    total = sum(bool(str(ch).strip()) for ch in channels)
    success = 0
    for channel in channels:
        channel = str(channel).strip()
        if not channel:
            continue
        try:
            await app.copy_message(chat_id=channel, from_chat_id=DB_CHANNEL_ID,
                                   message_id=int(message_id))
            success += 1
            print(f"Post {message_id} sent to {channel}")
        except Exception as exc:
            print(f"Post {message_id} failed for {channel}: {exc}")
    print(f"Scheduled delivery: {success}/{total} successful.")


@app.on_message(filters.command("postnow") & filters.private & filters.user(ADMIN_ID))
async def postnow_handler(client, message):
    if not message.reply_to_message:
        await message.reply_text("❌ Kisi post ko reply karke `/postnow` bhejein.")
        return
    try:
        db_id = await save_post(message.reply_to_message)
        status_msg = await message.reply_text("⏳ Sabhi channels par post bhej raha hoon...")
        success = 0
        for channel in REQUIRED_CHANNELS:
            try:
                await app.copy_message(chat_id=f"@{channel}", from_chat_id=DB_CHANNEL_ID,
                                       message_id=db_id)
                success += 1
            except Exception as exc:
                print(f"Instant post failed for @{channel}: {exc}")
        await status_msg.edit_text(f"✅ **Instant post complete:** {success}/{len(REQUIRED_CHANNELS)} channels.")
    except Exception as exc:
        await message.reply_text(f"❌ Error: `{exc}`")


@app.on_message(filters.command("schedule") & filters.private & filters.user(ADMIN_ID))
async def schedule_handler(client, message):
    try:
        if not message.reply_to_message:
            await message.reply_text("❌ Post ko reply karke command bhejein.")
            return
        args = (message.text or "").split()
        if len(args) != 4:
            await message.reply_text("Format: `/schedule @channel YYYY-MM-DD HH:MM`")
            return
        channel = args[1]
        run_date = parse_time(args[2], args[3])
        check_future(run_date)
        db_id = await save_post(message.reply_to_message)
        job_id = f"job_{db_id}_{int(run_date.timestamp())}"
        scheduler.add_job(send_scheduled_post, "date", run_date=run_date,
                          args=[[channel], db_id], id=job_id, replace_existing=True)
        await message.reply_text(
            f"✅ **Post scheduled!**\n🆔 Job: `{job_id}`\n📢 Target: `{channel}`\n"
            f"⏰ Time: `{fmt_time(run_date)}`\n🗄️ DB message: `{db_id}`"
        )
    except Exception as exc:
        await message.reply_text(f"❌ Error: `{exc}`")


@app.on_message(filters.command("interval") & filters.private & filters.user(ADMIN_ID))
async def interval_handler(client, message):
    try:
        if not message.reply_to_message:
            await message.reply_text("❌ Post ko reply karke command bhejein.")
            return
        args = (message.text or "").split()
        if len(args) != 6:
            await message.reply_text("Format: `/interval @channel YYYY-MM-DD HH:MM Count GapDays`")
            return
        channel, date_text, time_text = args[1], args[2], args[3]
        count, gap = int(args[4]), int(args[5])
        if not 1 <= count <= 500 or gap < 1:
            raise ValueError("Count 1–500 aur GapDays >= 1 hona chahiye.")
        first = parse_time(date_text, time_text)
        check_future(first)
        db_id = await save_post(message.reply_to_message)
        for i in range(count):
            run_date = first + timedelta(days=i * gap)
            scheduler.add_job(send_scheduled_post, "date", run_date=run_date,
                              args=[[channel], db_id],
                              id=f"job_interval_{db_id}_{i+1}", replace_existing=True)
        await message.reply_text(
            f"✅ **Interval jobs created:** `{count}`\n📢 Target: `{channel}`\n"
            f"🗓️ Gap: `{gap}` day(s)\n⏰ First: `{fmt_time(first)}`"
        )
    except Exception as exc:
        await message.reply_text(f"❌ Error: `{exc}`")


@app.on_message(filters.command("multiinterval") & filters.private & filters.user(ADMIN_ID))
async def multiinterval_handler(client, message):
    try:
        if not message.reply_to_message:
            await message.reply_text("❌ Post ko reply karke command bhejein.")
            return
        args = (message.text or "").split()
        if len(args) != 4:
            await message.reply_text("Format: `/multiinterval YYYY-MM-DD HH:MM Count`")
            return
        first = parse_time(args[1], args[2])
        count = int(args[3])
        if not 1 <= count <= 500:
            raise ValueError("Count 1–500 hona chahiye.")
        check_future(first)
        db_id = await save_post(message.reply_to_message)
        jobs = 0
        for channel_index, channel in enumerate(REQUIRED_CHANNELS, start=1):
            for i in range(count):
                run_date = first + timedelta(days=i * 2)
                scheduler.add_job(send_scheduled_post, "date", run_date=run_date,
                                  args=[[f"@{channel}"], db_id],
                                  id=f"job_multi_{db_id}_{channel_index}_{i+1}",
                                  replace_existing=True)
                jobs += 1
        await message.reply_text(
            f"🚀 **Multi-channel schedule created!**\n📊 Jobs: `{jobs}`\n"
            f"📢 Channels: `{len(REQUIRED_CHANNELS)}`\n⏰ First: `{fmt_time(first)}`\n"
            f"🗓️ Repeat gap: 2 days"
        )
    except Exception as exc:
        await message.reply_text(f"❌ Error: `{exc}`")


@app.on_message(filters.command("bulk_schedule") & filters.private & filters.user(ADMIN_ID))
async def bulk_schedule_handler(client, message):
    try:
        args = (message.text or "").split()
        if len(args) < 5:
            await message.reply_text("Format: `/bulk_schedule YYYY-MM-DD HH:MM GapDays @channel1 @channel2`")
            return
        first = parse_time(args[1], args[2])
        gap = int(args[3])
        channels = args[4:]
        if gap < 1:
            raise ValueError("GapDays kam se kam 1 hona chahiye.")
        check_future(first)
        BULK[message.from_user.id] = {"start": first, "gap": gap, "channels": channels, "count": 0}
        await message.reply_text(
            f"🚀 **Bulk collector active!**\n📅 Start: `{fmt_time(first)}`\n"
            f"🗓️ Gap: `{gap}` day(s)\n📢 Targets: `{', '.join(channels)}`\n"
            "Ab posts ek-ek karke bhejein. Finish: `/done_bulk`"
        )
    except Exception as exc:
        await message.reply_text(f"❌ Error: `{exc}`")


COMMANDS = ["start", "schedule", "interval", "multiinterval", "bulk_schedule",
            "done_bulk", "list", "cancel", "reschedule", "postnow"]


@app.on_message(filters.private & filters.user(ADMIN_ID) & ~filters.command(COMMANDS))
async def bulk_collector_handler(client, message):
    user_id = message.from_user.id if message.from_user else None
    if user_id not in BULK:
        return
    try:
        session = BULK[user_id]
        run_date = session["start"] + timedelta(days=session["count"] * session["gap"])
        check_future(run_date)
        db_id = await save_post(message)
        job_id = f"job_queue_{db_id}_{int(run_date.timestamp())}"
        scheduler.add_job(send_scheduled_post, "date", run_date=run_date,
                          args=[session["channels"], db_id], id=job_id, replace_existing=True)
        session["count"] += 1
        await message.reply_text(
            f"✅ **Post #{session['count']} queued!**\n⏰ `{fmt_time(run_date)}`\n"
            f"🆔 Job: `{job_id}`\nSend next post or `/done_bulk`."
        )
    except Exception as exc:
        await message.reply_text(f"❌ Queue error: `{exc}`")


@app.on_message(filters.command("done_bulk") & filters.private & filters.user(ADMIN_ID))
async def done_bulk_handler(client, message):
    session = BULK.pop(message.from_user.id, None)
    if session is None:
        await message.reply_text("ℹ️ Koi active bulk session nahi hai.")
    else:
        await message.reply_text(f"🎉 Bulk collector stopped. Queued posts: **{session['count']}**.")


@app.on_message(filters.command("list") & filters.private & filters.user(ADMIN_ID))
async def list_handler(client, message):
    jobs = sorted(scheduler.get_jobs(), key=lambda j: j.next_run_time or datetime.max.replace(tzinfo=IST))
    if not jobs:
        await message.reply_text("ℹ️ Koi scheduled post nahi hai.")
        return
    lines = [f"📋 **Scheduled Posts: {len(jobs)}**\n"]
    for job in jobs[:20]:
        target = job.args[0] if job.args else "Unknown"
        lines.append(f"🔹 **Job:** `{job.id}`\n📢 Target: `{target}`\n⏰ `{fmt_time(job.next_run_time)}`\n")
    if len(jobs) > 20:
        lines.append(f"Showing first 20 of {len(jobs)} jobs.")
    await message.reply_text("\n".join(lines))


@app.on_message(filters.command("cancel") & filters.private & filters.user(ADMIN_ID))
async def cancel_handler(client, message):
    args = (message.text or "").split()
    if len(args) != 2:
        await message.reply_text("Format: `/cancel job_ID`")
        return
    try:
        scheduler.remove_job(args[1])
        await message.reply_text(f"🗑️ Job cancelled: `{args[1]}`")
    except Exception:
        await message.reply_text("❌ Job ID nahi mili ya job pehle hi complete ho chuki hai.")


@app.on_message(filters.command("reschedule") & filters.private & filters.user(ADMIN_ID))
async def reschedule_handler(client, message):
    try:
        args = (message.text or "").split()
        if len(args) != 4:
            await message.reply_text("Format: `/reschedule job_ID YYYY-MM-DD HH:MM`")
            return
        job = scheduler.get_job(args[1])
        if not job:
            await message.reply_text("❌ Job ID nahi mili.")
            return
        run_date = parse_time(args[2], args[3])
        check_future(run_date)
        scheduler.modify_job(args[1], next_run_time=run_date)
        await message.reply_text(f"✅ Rescheduled `{args[1]}` to `{fmt_time(run_date)}`")
    except Exception as exc:
        await message.reply_text(f"❌ Error: `{exc}`")


async def main():
    scheduler.start()
    try:
        await app.start()
        try:
            await app.get_chat(DB_CHANNEL_ID)
            print("Database channel is accessible.")
        except Exception as exc:
            print(f"WARNING: Cannot access DB channel {DB_CHANNEL_ID}: {exc}")
        print("Bot started successfully.")
        await asyncio.Event().wait()
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        if app.is_connected:
            await app.stop()


if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        if not loop.is_closed():
            loop.close()
