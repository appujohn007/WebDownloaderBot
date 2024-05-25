import os
import sys
import shutil
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from web_dl import urlDownloader
from auth import add_credentials, get_credentials
import asyncio

# Bot configuration using environment variables
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
    url = m.text.strip()

    if not url.startswith('http'):
        return await m.reply("The URL must start with 'http' or 'https'")

    if not is_valid_url(url):
        return await m.reply("The URL is invalid or inaccessible")

    # Show buttons for selecting components to download
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("HTML", callback_data=f"html|{url}"),
                InlineKeyboardButton("CSS", callback_data=f"css|{url}"),
                InlineKeyboardButton("Images", callback_data=f"img|{url}")
            ],
            [
                InlineKeyboardButton("XML", callback_data=f"xml|{url}"),
                InlineKeyboardButton("Video", callback_data=f"video|{url}"),
                InlineKeyboardButton("JavaScript", callback_data=f"script|{url}")
            ]
        ]
    )
    await m.reply("Please select which components to download:", reply_markup=keyboard)

@Bot.on_callback_query()
async def callback_query_handler(bot, update: CallbackQuery):
    data = update.data
    component, url = data.split('|', 1)

    imgFlg = component == 'img'
    linkFlg = component == 'css'
    scriptFlg = component == 'script'
    videoFlg = component == 'video'
    xmlFlg = component == 'xml'

    name = dir = str(update.message.chat.id)
    if not os.path.isdir(dir):
        os.makedirs(dir)

    auth = get_credentials(update.from_user.id)
    obj = urlDownloader(imgFlg=imgFlg, linkFlg=linkFlg, scriptFlg=scriptFlg, videoFlg=videoFlg, xmlFlg=xmlFlg, file_size_limit=10*1024*1024, auth=auth)
    res, summary = obj.savePage(url, dir)
    if not res:
        return await update.message.reply('Something went wrong!')

    shutil.make_archive(name, 'zip', base_dir=dir)
    await update.message.reply_document(name+'.zip', caption=summary)

    shutil.rmtree(dir)
    os.remove(name+'.zip')

    print("Download completed successfully!")  # Debug statement

def parse_components(text):
    components = text.split()
    imgFlg = 'img' in components
    linkFlg = 'css' in components
    scriptFlg = 'script' in components
    videoFlg = 'video' in components
    xmlFlg = 'xml' in components
    return imgFlg, linkFlg, scriptFlg, videoFlg, xmlFlg

def is_valid_url(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

async def send_progress(msg, chat_id, initial_text):
    try:
        for i in range(10):
            await asyncio.sleep(1)
            try:
                await Bot.edit_message_text(chat_id=chat_id, message_id=msg.id, text=f"{initial_text}\nProgress: {i*10}%")
            except Exception as e:
                if "MESSAGE_ID_INVALID" in str(e):
                    print(f"Message ID invalid: {e}", file=sys.stderr)
                    break
                print(f"Error updating progress: {e}", file=sys.stderr)
                continue
    except Exception as e:
        print(f"Error in send_progress loop: {e}", file=sys.stderr)

Bot.run()
