import os
import sys  # Ensure sys is imported
import shutil
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from web_dl import urlDownloader
from auth import add_credentials, get_credentials
import asyncio

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")

Bot = Client(
    "WebDL-Bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

START_TXT = """
Hi {}, I am Web Downloader Bot.

I can download all the components (.html, .css, img, xml, video, javascript..) from URLs.

Send any URL, optionally with the components you want to download. For example:
'https://www.google.com img,css,script'

Use /auth username:password to add your authentication credentials.
"""

START_BTN = InlineKeyboardMarkup(
    [[
        InlineKeyboardButton('Source Code', url='https://github.com/samadii/WebDownloaderBot'),
    ]]
)

@Bot.on_message(filters.command(["start"]))
async def start(bot, update):
    text = START_TXT.format(update.from_user.mention)
    reply_markup = START_BTN
    await update.reply_text(
        text=text,
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

@Bot.on_message(filters.command(["auth"]))
async def auth(bot, update):
    if len(update.command) != 2 or ':' not in update.command[1]:
        return await update.reply_text("Please send your username and password in the format 'username:password'")
    
    username, password = update.command[1].split(":", 1)
    add_credentials(update.from_user.id, username, password)
    await update.reply_text("Credentials saved successfully.")

@Bot.on_message(filters.private & filters.text & ~filters.regex('/start|/auth'))
async def webdl(_, m):
    parts = m.text.split()
    url = parts[0]

    if not url.startswith('http'):
        return await m.reply("The URL must start with 'http' or 'https'")

    if not is_valid_url(url):
        return await m.reply("The URL is invalid or inaccessible")

    # Check if user has credentials saved
    credentials = get_credentials(m.chat.id)
    auth = (credentials['username'], credentials['password']) if credentials else None

    msg = await m.reply('Processing...')
    asyncio.create_task(send_progress(msg, m.chat.id, "Processing..."))

    imgFlg, linkFlg, scriptFlg = parse_components(m.text)
    name = dir = str(m.chat.id)
    if not os.path.isdir(dir):
        os.makedirs(dir)

    obj = urlDownloader(imgFlg=imgFlg, linkFlg=linkFlg, scriptFlg=scriptFlg, file_size_limit=10*1024*1024, auth=auth)
    res, summary = obj.savePage(url, dir)
    if not res:
        return await msg.edit_text('Something went wrong!')

    shutil.make_archive(name, 'zip', base_dir=dir)
    await m.reply_document(name+'.zip', caption=summary)
    await msg.delete()

    shutil.rmtree(dir)
    os.remove(name+'.zip')

def is_valid_url(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def parse_components(text):
    components = text.split()[1:]
    imgFlg = 'img' in components
    linkFlg = 'css' in components
    scriptFlg = 'script' in components
    return imgFlg, linkFlg, scriptFlg

async def send_progress(msg, chat_id, initial_text):
    try:
        for i in range(10):
            await asyncio.sleep(1)
            try:
                await Bot.edit_message_text(chat_id=chat_id, message_id=msg.id, text=f"{initial_text}\nProgress: {i*10}%")
            except Exception as e:
                print(f"Error updating progress: {e}", file=sys.stderr)
                break
    except Exception as e:
        print(f"Error in send_progress loop: {e}", file=sys.stderr)

Bot.run()
