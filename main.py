from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from typing import Optional, Dict, Any, List
from telegram.request import HTTPXRequest
from telegram import Update, constants
from datetime import datetime as DT
from tkinter import messagebox
from functools import wraps
import multiprocessing
import tkinter as tk
import subprocess
import threading
import platform
import telegram
import asyncio
import queue
import json
import sys
import csv
import os
import io

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    HAS_UI_AUTOMATION = True
except ImportError:
    HAS_UI_AUTOMATION = False
    pyautogui = None

CONFIG_FILE = "config.json"
CHAT_ID = ""
BOT_TOKEN = ""
IS_WINDOWS = platform.system() == "Windows"

try:
    with open(CONFIG_FILE, "r") as file:
        config = json.load(file)
        CHAT_ID = str(config.get("chat_id", ""))
        BOT_TOKEN = config.get("api_key", "")
        if not CHAT_ID or not BOT_TOKEN:
            raise ValueError("chat_id or api_key missing in config.json")
except FileNotFoundError:
    sys.exit(1)
except Exception:
    sys.exit(1)

USE_PROXY = os.environ.get('USE_PROXY', 'False').lower() in ('true', '1', 't')
V2RAY_PROXY = None
CONNECT_TIMEOUT = 60.0
READ_TIMEOUT = 120.0

def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.effective_chat or str(update.effective_chat.id) != CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🔒 <b>Access Denied.</b> This bot is configured for private use only.",
                    parse_mode=constants.ParseMode.HTML
                )
            except Exception:
                pass
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

def _parse_duration_to_seconds(duration_str: str) -> Optional[int]:
    duration_str = duration_str.lower().strip()
    if duration_str.isdigit():
        return int(duration_str)
    try:
        if duration_str.endswith('m'):
            return int(duration_str[:-1]) * 60
        if duration_str.endswith('h'):
            return int(duration_str[:-1]) * 3600
    except ValueError:
        return None
    return None

def _get_screenshot_sync(box: Optional[List[int]] = None) -> io.BytesIO:
    if not HAS_UI_AUTOMATION:
        return io.BytesIO(b"")
    try:
        region_tuple = tuple(box) if box and len(box) == 4 else None
        image = pyautogui.screenshot(region=region_tuple)
        bio = io.BytesIO()
        image.save(bio, 'JPEG', quality=85)
        bio.seek(0)
        return bio
    except Exception:
        return io.BytesIO(b"")

def _get_programs_windows_sync() -> str:
    if not IS_WINDOWS:
        return "Command only available on Windows."
    try:
        cmd = ["tasklist", "/v", "/fo", "csv", "/fi", "WINDOWTITLE ne N/A"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        lines = io.StringIO(result.stdout.strip())
        reader = csv.DictReader(lines)
        program_list = set()
        IMAGE_NAME_KEYS = ["Image Name", "ImageName"]
        WINDOW_TITLE_KEYS = ["Window Title", "WindowTitle"]
        def get_value(row, keys):
            for key in keys:
                if key in row:
                    return row[key].strip()
            return None
        for row in reader:
            image_name = get_value(row, IMAGE_NAME_KEYS)
            window_title = get_value(row, WINDOW_TITLE_KEYS)
            if not image_name or not window_title:
                continue
            if (window_title != 'N/A' and
                'tasklist' not in image_name.lower() and
                'pythonw' not in image_name.lower()):
                program_list.add(f"[{image_name.replace('.exe', '')}] - {window_title}")
        if not program_list:
            return "No visible applications detected in the active user sessions."
        return "\n".join(sorted(list(program_list)))
    except Exception as e:
        return f"Error executing tasklist for programs: {e}"

def _get_chrome_tabs_windows_sync() -> str:
    if not IS_WINDOWS:
        return "Command only available on Windows."
    try:
        cmd = ["tasklist", "/v", "/fo", "csv", "/fi", "IMAGENAME eq chrome.exe"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        lines = io.StringIO(result.stdout.strip())
        reader = csv.DictReader(lines)
        tab_titles = set()
        WINDOW_TITLE_KEYS = ["Window Title", "WindowTitle"]
        def get_value(row, keys):
            for key in keys:
                if key in row:
                    return row[key].strip()
            return None
        for row in reader:
            window_title = get_value(row, WINDOW_TITLE_KEYS)
            if window_title and window_title not in ['N/A', '', 'Google Chrome']:
                tab_titles.add(window_title)
        if not tab_titles:
            return "Chrome is running, but no active tab titles could be retrieved."
        return "\n".join(sorted(list(tab_titles)))
    except Exception as e:
        return f"Error retrieving Chrome tab info: {e}"

def show_desktop_notification_process(user_name: str, message_text: str):
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        timestamp = DT.now().strftime('%H:%M:%S')
        title = f"{user_name}"
        body = f"[{timestamp}]\n\n{message_text}"
        messagebox.showinfo(title, body)
    except Exception:
        pass
    finally:
        try:
            root.destroy()
        except Exception:
            pass

@restricted
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    user_name = update.effective_user.first_name or update.effective_user.username or "User"
    notification_process = multiprocessing.Process(
        target=show_desktop_notification_process,
        args=(user_name, message_text),
        daemon=True
    )
    notification_process.start()
    await update.message.reply_text(
        "Acknowledged! A new desktop notification pop-up has been launched."
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != CHAT_ID:
        await update.message.reply_text("🔒 <b>Access Denied.</b> This bot is configured for private use only.",
                                        parse_mode=constants.ParseMode.HTML)
        return
    user = update.effective_user
    proxy_status = 'N/A'
    if USE_PROXY:
        proxy_status = 'Configuration Required'
    welcome_message = (
        f"👋 Hello <b>{user.first_name}</b>!\n\n"
        "I'm your remote system assistant. Available commands:\n\n"
        "<b>System & Info</b>:\n"
        "<b>#=> /screenshot</b> - Take a full screenshot (or region: <code>/screenshot 100 100 500 500</code>).\n"
        f"<b>#=> /programs</b> - List visible open applications ({'Windows only' if IS_WINDOWS else 'Unsupported OS'}).\n"
        f"<b>#=> /chrometabs</b> - List active Chrome window titles ({'Windows only' if IS_WINDOWS else 'Unsupported OS'}).\n"
        "\n<b>Control (Requires UI/Windows)</b>:\n"
        "<b>#=> /shutdown &lt;time&gt;</b> - Schedule shutdown. E.g., <code>/shutdown 5m</code>.\n"
        "<b>#=> /cancelshutdown</b> - Cancel a pending shutdown.\n"
        "<b>#=> /lock</b> - Instantly lock the Windows session.\n"
        "<b>#=> /wake</b> - Press a key to wake the display/bring up the login prompt.\n"
        "<b>#=> /move &lt;x&gt; &lt;y&gt;</b> - Move the cursor.\n"
        "<b>#=> /click &lt;type&gt;</b> - Perform a click. Types: <code>left</code>, <code>right</code>, <code>double</code>.\n"
        "\n<b>Notification</b>:\n"
        "<b>#=></b> Send any <b>text message</b> to see a desktop notification.\n\n"
        f"Proxy Status: {proxy_status} (If enabled in environment variables)"
    )
    await update.message.reply_text(
        welcome_message,
        parse_mode=constants.ParseMode.HTML
    )

@restricted
async def send_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not HAS_UI_AUTOMATION:
        await update.message.reply_text("❌ UI automation/screenshotting is not available.")
        return
    box = None
    if context.args:
        if len(context.args) == 4:
            try:
                box = [int(arg) for arg in context.args]
            except ValueError:
                await update.message.reply_text("❌ <b>Invalid arguments.</b> Coordinates must be integers. Taking full screenshot.", parse_mode=constants.ParseMode.HTML)
        else:
            await update.message.reply_text("⚠️ <b>Invalid usage.</b> For region crop, use: <code>/screenshot &lt;left&gt; &lt;top&gt; &lt;width&gt; &lt;height&gt;</code>. Taking full screenshot.", parse_mode=constants.ParseMode.HTML)
    await context.bot.send_chat_action(chat_id=CHAT_ID, action=constants.ChatAction.UPLOAD_PHOTO)
    photo_io = await asyncio.to_thread(_get_screenshot_sync, box=box)
    if photo_io.getbuffer().nbytes == 0:
        await update.message.reply_text("❌ Screenshot failed. Display might be off or permission denied.")
        return
    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            await update.message.reply_photo(photo=photo_io, caption=f"🖥️ Screen at {DT.now().strftime('%H:%M:%S')}")
            return
        except telegram.error.TimedOut:
            if attempt < MAX_RETRIES - 1:
                photo_io.seek(0)
                await asyncio.sleep(2 ** attempt)
            else:
                await update.message.reply_text("❌ Failed to send screenshot after multiple retries due to timeout.")
                return
        except Exception as e:
            await update.message.reply_text(f"❌ An error occurred during photo upload: {e}")
            return

@restricted
async def list_open_programs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not IS_WINDOWS:
        await update.message.reply_text(f"❌ This command only supports Windows. Current OS is: <code>{platform.system()}</code>.", parse_mode=constants.ParseMode.HTML)
        return
    await context.bot.send_chat_action(chat_id=CHAT_ID, action=constants.ChatAction.TYPING)
    program_info = await asyncio.to_thread(_get_programs_windows_sync)
    await update.message.reply_text(
        text=f"🔍 <b>Open Programs</b>:\n\n<pre>\n{program_info}\n</pre>",
        parse_mode=constants.ParseMode.HTML
    )

@restricted
async def list_chrome_tabs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not IS_WINDOWS:
        await update.message.reply_text(f"❌ This command only supports Windows. Current OS is: <code>{platform.system()}</code>.", parse_mode=constants.ParseMode.HTML)
        return
    await context.bot.send_chat_action(chat_id=CHAT_ID, action=constants.ChatAction.TYPING)
    tab_info = await asyncio.to_thread(_get_chrome_tabs_windows_sync)
    await update.message.reply_text(
        text=f"🌐 <b>Chrome Tabs (Window Titles)</b>:\n\n<pre>\n{tab_info}\n</pre>",
        parse_mode=constants.ParseMode.HTML
    )

@restricted
async def shutdown_computer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not IS_WINDOWS:
        await update.message.reply_text("⚠️ Timed shutdown is Windows-specific. Attempting immediate shutdown via <code>sudo shutdown now</code>.", parse_mode=constants.ParseMode.HTML)
        try:
            await asyncio.to_thread(subprocess.run, ["sudo", "shutdown", "now"], check=True)
            await update.message.reply_text("✅ Immediate shutdown command sent.")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to execute shutdown command: {e}")
        return
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please specify a duration for the shutdown. E.g., <code>/shutdown 5m</code> (5 minutes) or <code>/shutdown 3600</code> (1 hour).", parse_mode=constants.ParseMode.HTML
        )
        return
    duration_str = context.args[0]
    seconds = _parse_duration_to_seconds(duration_str)
    if seconds is None or seconds < 10:
        await update.message.reply_text(
            "❌ Invalid duration format or duration too short. Minimum duration is 10 seconds."
        )
        return
    await asyncio.to_thread(subprocess.run, ["shutdown", "/s", "/t", str(seconds)], check=False)
    minutes = seconds / 60
    hours = seconds / 3600
    if minutes < 60:
        display_time = f"{minutes:.1f} minutes ({seconds} seconds)"
    else:
        display_time = f"{hours:.2f} hours ({seconds} seconds)"
    await update.message.reply_text(
        text=f"✅ <b>Shutdown scheduled</b> in {display_time}.",
        parse_mode=constants.ParseMode.HTML
    )

@restricted
async def cancel_shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not IS_WINDOWS:
        await update.message.reply_text(f"❌ This command is only supported on Windows. Current OS is: <code>{platform.system()}</code>.", parse_mode=constants.ParseMode.HTML)
        return
    try:
        result = await asyncio.to_thread(subprocess.run, ["shutdown", "/a"], check=False, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 or 'no shutdown' in result.stderr.lower() or 'no shutdown' in result.stdout.lower():
            await update.message.reply_text(
                text="🛑 <b>Pending shutdown cancelled</b> successfully (or none was scheduled).",
                parse_mode=constants.ParseMode.HTML
            )
        else:
             await update.message.reply_text(f"⚠️ Failed to cancel shutdown (Code: {result.returncode}). Output: {result.stdout.strip()} {result.stderr.strip()}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to execute cancel shutdown command: {e}")

@restricted
async def lock_windows_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not IS_WINDOWS:
        await update.message.reply_text(f"❌ The <code>/lock</code> command is only supported on Windows. Current OS is: <code>{platform.system()}</code>.", parse_mode=constants.ParseMode.HTML)
        return
    try:
        await asyncio.to_thread(subprocess.run, ["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
        await update.message.reply_text(
            text="🔒 <b>Windows session locked.</b>",
            parse_mode=constants.ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to lock session: {e}")

@restricted
async def wake_display(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not HAS_UI_AUTOMATION:
        await update.message.reply_text("❌ UI automation is not available for this command.")
        return
    try:
        await asyncio.to_thread(pyautogui.press, 'enter')
        await update.message.reply_text(
            text="💡 <b>Display Woken!</b> I pressed 'Enter' to bring up the login prompt.",
            parse_mode=constants.ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(
            text=f"❌ Failed to wake display/press key (Is a display connected?): {e}"
        )

@restricted
async def move_mouse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not HAS_UI_AUTOMATION:
        await update.message.reply_text("❌ UI automation is not available for this command.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("⚠️ Usage: <code>/move &lt;x_coordinate&gt; &lt;y_coordinate&gt;</code> (e.g., <code>/move 500 400</code>)", parse_mode=constants.ParseMode.HTML)
        return
    try:
        x = int(context.args[0])
        y = int(context.args[1])
        await asyncio.to_thread(pyautogui.moveTo, x, y, duration=0.2)
        await update.message.reply_text(
            text=f"🖱️ Moved cursor to screen coordinates: $({x}, {y})$"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid coordinates. Please ensure both arguments are integers.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to move mouse: {e}")

@restricted
async def click_mouse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not HAS_UI_AUTOMATION:
        await update.message.reply_text("❌ UI automation is not available for this command.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("⚠️ Usage: <code>/click &lt;type&gt;</code>. Types: <code>left</code>, <code>right</code>, <code>double</code>.", parse_mode=constants.ParseMode.HTML)
        return
    click_type = context.args[0].lower()
    message = ""
    try:
        if click_type == 'left':
            await asyncio.to_thread(pyautogui.click, button='left')
            message = "🖱️ Performed <b>LEFT</b> click."
        elif click_type == 'right':
            await asyncio.to_thread(pyautogui.click, button='right')
            message = "🖱️ Performed <b>RIGHT</b> click."
        elif click_type == 'double':
            await asyncio.to_thread(pyautogui.doubleClick, button='left')
            message = "🖱️ Performed <b>DOUBLE</b> click."
        else:
            await update.message.reply_text("❌ Invalid click type. Must be <code>left</code>, <code>right</code>, or <code>double</code>.", parse_mode=constants.ParseMode.HTML)
            return
        await update.message.reply_text(
            text=message,
            parse_mode=constants.ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to perform click: {e}")

async def post_init(application: Application):
    try:
        status_msg = "🔔 <b>Jarvis is online.</b>"
        await application.bot.send_message(
            chat_id=CHAT_ID,
            text=status_msg,
            parse_mode=constants.ParseMode.HTML
        )
    except Exception:
        pass

def main():
    if platform.system() == "Windows":
        multiprocessing.freeze_support()
    request_kwargs = {}
    request_obj = HTTPXRequest(
        read_timeout=READ_TIMEOUT,
        connect_timeout=CONNECT_TIMEOUT,
        **request_kwargs
    )
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).request(request_obj).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("screenshot", send_screenshot))
    application.add_handler(CommandHandler("programs", list_open_programs))
    application.add_handler(CommandHandler("chrometabs", list_chrome_tabs))
    application.add_handler(CommandHandler("shutdown", shutdown_computer))
    application.add_handler(CommandHandler("cancelshutdown", cancel_shutdown))
    application.add_handler(CommandHandler("lock", lock_windows_session))
    application.add_handler(CommandHandler("wake", wake_display))
    application.add_handler(CommandHandler("move", move_mouse))
    application.add_handler(CommandHandler("click", click_mouse))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    try:
        application.run_polling(poll_interval=1.0)
    except KeyboardInterrupt:
        pass
    except telegram.error.NetworkError:
        pass
    except Exception:
        pass

if __name__ == '__main__':
    main()
