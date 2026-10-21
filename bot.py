import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytz
from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, ChannelInvalid, ChannelPrivate
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore


# -------------------- CONFIGURATION --------------------

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
DATA_DIR = Path(".").resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "jobs.sqlite"

logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("black_bat_auto_post")

app = Client(
    "clone_post_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir=str(DATA_DIR),
)

scheduler = AsyncIOScheduler(
    jobstores={
        "default": SQLAlchemyJobStore(url=f"sqlite:///{DB_PATH.as_posix()}")
    },
    timezone=IST,
)

# In-memory bulk session: it will reset when the process restarts.
BULK = {}


# -------------------- HELPERS --------------------

def parse_time(date_text: str, time_text: str) -> datetime:
    return IST.localize(datetime.strptime(
        f"{date_text} {time_text}", "%Y-%m-%d %H:%M"
    ))


def fmt_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    return dt.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def check_future(dt: datetime) -> None:
    if dt <= datetime.now(IST):
        raise ValueError("Time must be in the future (India/IST).")


def normalize_target(channel: str) -> str:
    channel = channel.strip()
    if not channel:
        raise ValueError("Channel username/ID is empty.")
    if channel.startswith("https://t.me/"):
        channel = channel.rstrip("/").split("/")[-1]
    if channel.startswith("@"):
        channel = channel[1:]
    return f"@{channel}" if not channel.startswith("-100") else channel


async def check_user_joined(client: Client, user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True

    for channel in REQUIRED_CHANNELS:
        try:
            member = await client.get_chat_member(f"@{channel}", user_id)
            status = str(member.status).lower()
            if "left" in status or "kicked" in status or "banned" in status:
                return False
        except UserNotParticipant:
            return False
        except (ChannelInvalid, ChannelPrivate, ChatAdminRequired) as exc:
            log.warning("Cannot verify membership for @%s: %s", channel, exc)
            return False
        except Exception:
            log.exception("Membership verification failed for @%s", channel)
            return False
    return True


async def save_post(message) -> int:
    try:
        copied = await message.copy(DB_CHANNEL_ID)
    except Exception:
        log.exception("copy() failed; trying forward()")
        copied = await message.forward(DB_CHANNEL_ID)
    return copied.id


async def send_scheduled_post(target_channels, message_id: int) -> None:
    channels = target_channels if isinstance(target_channels, list) else str(target_channels).split(",")
    targets = [normalize_target(str(ch)) for ch in channels if str(ch).strip()]
    success = 0

    for target in targets:
        try:
            await app.copy_message(
                chat_id=target,
                from_chat_id=DB_CHANNEL_ID,
                message_id=int(message_id),
            )
            success += 1
            log.info("Scheduled post %s delivered to %s", message_id, target)
        except Exception:
            log.exception("Scheduled post %s failed for %s", message_id, target)

    log.info("Scheduled delivery: %s/%s successful", success, len(targets))


def join_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💀 HACKING CHANNEL", url="https://t.me/blackbathacker001")],
        [InlineKeyboardButton("😎 MODSZ CHANNEL", url="https://t.me/bathackermodzzz")],
        [InlineKeyboardButton("💀 VIP PANEL", url="https://t.me/batsvvippanelll")],
        [InlineKeyboardButton("💀 BOMBER CHANNEL", url="https://t.me/blackbatlightbomberrr")],
        [InlineKeyboardButton("💀 ANIMATION VIDEOS", url="https://t.me/batanimationvideos")],
        [InlineKeyboardButton("🛡️ BACKUP / SUPPORT", url="https://t.me/blackbathackergroup")],
        [InlineKeyboardButton("✅ Verify / सत्यापन करें", callback_data="verify_joined")],
        [InlineKeyboardButton("👑 OWNER", url="https://t.me/blackbatowner")],
    ])


def main_keyboard() -> InlineKeyboardMarkup:
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


def welcome(name: str) -> str:
    return (
        f"👋 **Welcome {name}!**\n\n"
        "🤖 **Black Bat Auto Post & Bulk Queue Scheduler Bot**\n\n"
        "**Admin commands:**\n"
        "• `/schedule @channel YYYY-MM-DD HH:MM` (reply to post)\n"
        "• `/interval @channel YYYY-MM-DD HH:MM Count GapDays` (reply to post)\n"
        "• `/multiinterval YYYY-MM-DD HH:MM Count` (reply to post; all channels, 2-day gap)\n"
        "• `/postnow` (reply to post; publish to all required channels)\n"
        "• `/bulk_schedule YYYY-MM-DD HH:MM GapDays @channel1 @channel2` then send posts\n"
        "• `/done_bulk`, `/list`, `/cancel job_ID`, `/reschedule job_ID YYYY-MM-DD HH:MM`\n\n"
        "All schedule times use India Standard Time (IST)."
    )


# -------------------- USER COMMANDS --------------------

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message):
    if not message.from_user:
        return

    if not await check_user_joined(client, message.from_user.id):
        await message.reply_text(
            "⚔️ **B.A.T HACKER NETWORK** ⚔️\n\n"
            "Bot use karne se pehle neeche diye gaye sabhi required channels join karein, "
            "phir **✅ Verify** dabayein.\n\n"
            "Join all required channels and press **✅ Verify**.",
            reply_markup=join_keyboard(),
            disable_web_page_preview=True,
        )
        return

    await message.reply_text(
        welcome(message.from_user.first_name or "there"),
        reply_markup=main_keyboard(),
        disable_web_page_preview=True,
    )


@app.on_callback_query(filters.regex(r"^verify_joined$"))
async def verify_handler(client: Client, query: CallbackQuery):
    if await check_user_joined(client, query.from_user.id):
        await query.answer("✅ Verification successful!", show_alert=True)
        if query.message:
            await query.message.edit_text(
                welcome(query.from_user.first_name or "there"),
                reply_markup=main_keyboard(),
                disable_web_page_preview=True,
            )
    else:
        await query.answer(
            "❌ Sabhi required channels join karein. Agar join kar chuke hain, "
            "bot ko har channel mein admin bana kar dobara verify karein.",
            show_alert=True,
        )


@app.on_callback_query(filters.regex(r"^clone_info$"))
async def clone_handler(client: Client, query: CallbackQuery):
    await query.answer()
    if query.message:
        await query.message.reply_text(
            "🌀 **Clone bot setup**\n\n"
            "1. `@BotFather` par `/newbot` bhejein.\n"
            "2. Naya bot token private rakhein.\n"
            "3. Setup help ke liye owner se contact karein."
        )


# -------------------- ADMIN COMMANDS --------------------

@app.on_message(filters.command("postnow") & filters.private & filters.user(ADMIN_ID))
async def postnow_handler(client: Client, message):
    if not message.reply_to_message:
        await message.reply_text("❌ Kisi post ko reply karke `/postnow` bhejein.")
        return

    try:
        db_id = await save_post(message.reply_to_message)
        status_msg = await message.reply_text("⏳ Sabhi required channels par post bhej raha hoon...")
        success = 0

        for channel in REQUIRED_CHANNELS:
            target = normalize_target(channel)
            try:
                await app.copy_message(
                    chat_id=target,
                    from_chat_id=DB_CHANNEL_ID,
                    message_id=db_id,
                )
                success += 1
            except Exception:
                log.exception("Instant post failed for %s", target)

        await status_msg.edit_text(
            f"✅ **Instant post complete:** {success}/{len(REQUIRED_CHANNELS)} channels."
        )
    except Exception as exc:
        log.exception("postnow failed")
        await message.reply_text(f"❌ Error: `{type(exc).__name__}: {exc}`")


@app.on_message(filters.command("schedule") & filters.private & filters.user(ADMIN_ID))
async def schedule_handler(client: Client, message):
    try:
        if not message.reply_to_message:
            await message.reply_text("❌ Post ko reply karke command bhejein.")
            return

        args = (message.text or "").split()
        if len(args) != 4:
            await message.reply_text("Format: `/schedule @channel YYYY-MM-DD HH:MM`")
            return

        target = normalize_target(args[1])
        run_date = parse_time(args[2], args[3])
        check_future(run_date)
        db_id = await save_post(message.reply_to_message)
        job_id = f"job_{db_id}_{int(run_date.timestamp())}"

        scheduler.add_job(
            send_scheduled_post,
            trigger="date",
            run_date=run_date,
            args=[[target], db_id],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600,
        )
        await message.reply_text(
            f"✅ **Post scheduled!**\n🆔 Job: `{job_id}`\n"
            f"📢 Target: `{target}`\n⏰ Time: `{fmt_time(run_date)}`\n"
            f"🗄️ DB message: `{db_id}`"
        )
    except Exception as exc:
        log.exception("schedule failed")
        await message.reply_text(f"❌ Error: `{type(exc).__name__}: {exc}`")


@app.on_message(filters.command("interval") & filters.private & filters.user(ADMIN_ID))
async def interval_handler(client: Client, message):
    try:
        if not message.reply_to_message:
            await message.reply_text("❌ Post ko reply karke command bhejein.")
            return

        args = (message.text or "").split()
        if len(args) != 6:
            await message.reply_text(
                "Format: `/interval @channel YYYY-MM-DD HH:MM Count GapDays`"
            )
            return

        target = normalize_target(args[1])
        first = parse_time(args[2], args[3])
        count, gap = int(args[4]), int(args[5])

        if not 1 <= count <= 500:
            raise ValueError("Count 1–500 hona chahiye.")
        if gap < 1:
            raise ValueError("GapDays kam se kam 1 hona chahiye.")
        check_future(first)

        db_id = await save_post(message.reply_to_message)
        for i in range(count):
            run_date = first + timedelta(days=i * gap)
            scheduler.add_job(
                send_scheduled_post,
                trigger="date",
                run_date=run_date,
                args=[[target], db_id],
                id=f"job_interval_{db_id}_{i + 1}",
                replace_existing=True,
                misfire_grace_time=3600,
            )

        await message.reply_text(
            f"✅ **Interval jobs created:** `{count}`\n📢 Target: `{target}`\n"
            f"🗓️ Gap: `{gap}` day(s)\n⏰ First: `{fmt_time(first)}`"
        )
    except Exception as exc:
        log.exception("interval failed")
        await message.reply_text(f"❌ Error: `{type(exc).__name__}: {exc}`")


@app.on_message(filters.command("multiinterval") & filters.private & filters.user(ADMIN_ID))
async def multiinterval_handler(client: Client, message):
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
                target = normalize_target(channel)
                scheduler.add_job(
                    send_scheduled_post,
                    trigger="date",
                    run_date=run_date,
                    args=[[target], db_id],
                    id=f"job_multi_{db_id}_{channel_index}_{i + 1}",
                    replace_existing=True,
                    misfire_grace_time=3600,
                )
                jobs += 1

        await message.reply_text(
            f"🚀 **Multi-channel schedule created!**\n📊 Jobs: `{jobs}`\n"
            f"📢 Channels: `{len(REQUIRED_CHANNELS)}`\n"
            f"⏰ First: `{fmt_time(first)}`\n🗓️ Repeat gap: 2 days"
        )
    except Exception as exc:
        log.exception("multiinterval failed")
        await message.reply_text(f"❌ Error: `{type(exc).__name__}: {exc}`")


@app.on_message(filters.command("bulk_schedule") & filters.private & filters.user(ADMIN_ID))
async def bulk_schedule_handler(client: Client, message):
    try:
        args = (message.text or "").split()
        if len(args) < 5:
            await message.reply_text(
                "Format: `/bulk_schedule YYYY-MM-DD HH:MM GapDays @channel1 @channel2`"
            )
            return

        first = parse_time(args[1], args[2])
        gap = int(args[3])
        channels = [normalize_target(x) for x in args[4:]]
        if gap < 1:
            raise ValueError("GapDays kam se kam 1 hona chahiye.")
        check_future(first)

        BULK[message.from_user.id] = {
            "start": first,
            "gap": gap,
            "channels": channels,
            "count": 0,
        }
        await message.reply_text(
            f"🚀 **Bulk collector active!**\n📅 Start: `{fmt_time(first)}`\n"
            f"🗓️ Gap: `{gap}` day(s)\n📢 Targets: `{', '.join(channels)}`\n"
            "Ab posts ek-ek karke bhejein. Finish: `/done_bulk`"
        )
    except Exception as exc:
        log.exception("bulk_schedule failed")
        await message.reply_text(f"❌ Error: `{type(exc).__name__}: {exc}`")


@app.on_message(filters.command("done_bulk") & filters.private & filters.user(ADMIN_ID))
async def done_bulk_handler(client: Client, message):
    session = BULK.pop(message.from_user.id, None)
    if session is None:
        await message.reply_text("ℹ️ Koi active bulk session nahi hai.")
    else:
        await message.reply_text(
            f"🎉 Bulk collector stopped. Queued posts: **{session['count']}**."
        )


@app.on_message(filters.command("list") & filters.private & filters.user(ADMIN_ID))
async def list_handler(client: Client, message):
    jobs = sorted(
        scheduler.get_jobs(),
        key=lambda job: job.next_run_time or datetime.max.replace(tzinfo=IST),
    )
    if not jobs:
        await message.reply_text("ℹ️ Koi scheduled post nahi hai.")
        return

    lines = [f"📋 **Scheduled Posts: {len(jobs)}**\n"]
    for job in jobs[:20]:
        target = job.args[0] if job.args else "Unknown"
        next_run = job.next_run_time
        lines.append(
            f"🔹 **Job:** `{job.id}`\n📢 Target: `{target}`\n"
            f"⏰ `{fmt_time(next_run) if next_run else 'No next run'}`\n"
        )
    if len(jobs) > 20:
        lines.append(f"Showing first 20 of {len(jobs)} jobs.")
    await message.reply_text("\n".join(lines))


@app.on_message(filters.command("cancel") & filters.private & filters.user(ADMIN_ID))
async def cancel_handler(client: Client, message):
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
async def reschedule_handler(client: Client, message):
    try:
        args = (message.text or "").split()
        if len(args) != 4:
            await message.reply_text(
                "Format: `/reschedule job_ID YYYY-MM-DD HH:MM`"
            )
            return

        job = scheduler.get_job(args[1])
        if not job:
            await message.reply_text("❌ Job ID nahi mili.")
            return

        run_date = parse_time(args[2], args[3])
        check_future(run_date)
        scheduler.modify_job(args[1], next_run_time=run_date)
        await message.reply_text(
            f"✅ Rescheduled `{args[1]}` to `{fmt_time(run_date)}`"
        )
    except Exception as exc:
        log.exception("reschedule failed")
        await message.reply_text(f"❌ Error: `{type(exc).__name__}: {exc}`")


@app.on_message(filters.private & filters.user(ADMIN_ID) & ~filters.command([
    "start", "schedule", "interval", "multiinterval", "bulk_schedule",
    "done_bulk", "list", "cancel", "reschedule", "postnow"
]))
async def bulk_collector_handler(client: Client, message):
    user_id = message.from_user.id if message.from_user else None
    if user_id not in BULK:
        return

    try:
        session = BULK[user_id]
        run_date = session["start"] + timedelta(days=session["count"] * session["gap"])
        check_future(run_date)
        db_id = await save_post(message)
        job_id = f"job_queue_{db_id}_{int(run_date.timestamp())}"

        scheduler.add_job(
            send_scheduled_post,
            trigger="date",
            run_date=run_date,
            args=[session["channels"], db_id],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=3600,
        )
        session["count"] += 1
        await message.reply_text(
            f"✅ **Post #{session['count']} queued!**\n⏰ `{fmt_time(run_date)}`\n"
            f"🆔 Job: `{job_id}`\nSend next post or `/done_bulk`."
        )
    except Exception as exc:
        log.exception("bulk collection failed")
        await message.reply_text(f"❌ Queue error: `{type(exc).__name__}: {exc}`")


# -------------------- STARTUP / SHUTDOWN --------------------

async def main():
    scheduler.start()
    try:
        await app.start()
        log.info("Bot started. Database path: %s", DB_PATH)

        try:
            await app.get_chat(DB_CHANNEL_ID)
            log.info("Database channel is accessible.")
        except Exception:
            log.exception(
                "Cannot access DB channel %s. Add the bot to the DB channel "
                "and ensure it can read/copy messages there.",
                DB_CHANNEL_ID,
            )

        for channel in REQUIRED_CHANNELS:
            try:
                await app.get_chat(f"@{channel}")
            except Exception:
                log.exception(
                    "Required channel @%s is not accessible to the bot.", channel
                )

        await asyncio.Event().wait()
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        if app.is_connected:
            await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped by keyboard interrupt.")
