import os
import shutil
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from web_dl import urlDownloader
from auth import add_credentials, get_credentials, remove_credentials

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
Use /remove_auth to remove your authentication credentials.
Use /view_auth to view your stored authentication credentials.
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

@Bot.on_message(filters.command(["remove_auth"]))
async def remove_auth(bot, update):
    success = remove_credentials(update.from_user.id)
    if success:
        await update.reply_text("Credentials removed successfully.")
    else:
        await update.reply_text("No credentials found to remove.")

@Bot.on_message(filters.command(["view_auth"]))
async def view_auth(bot, update):
    creds = get_credentials(update.from_user.id)
    if creds:
        await update.reply_text(f"Your credentials:\nUsername: {creds['username']}\nPassword: {creds['password']}")
    else:
        await update.reply_text("No credentials found.")

@Bot.on_message(filters.private & filters.text & ~filters.regex('/start|/auth|/remove_auth|/view_auth'))
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
                InlineKeyboardButton("HTML", callback_data=f"h|{url[:50]}"),
                InlineKeyboardButton("CSS", callback_data=f"c|{url[:50]}"),
                InlineKeyboardButton("Images", callback_data=f"i|{url[:50]}")
            ],
            [
                InlineKeyboardButton("XML", callback_data=f"x|{url[:50]}"),
                InlineKeyboardButton("Video", callback_data=f"v|{url[:50]}"),
                InlineKeyboardButton("JS", callback_data=f"j|{url[:50]}")
            ]
        ]
    )
    await m.reply("Please select which components to download:", reply_markup=keyboard)

@Bot.on_callback_query()
async def callback_query_handler(bot, update: CallbackQuery):
    data = update.data
    component, url = data.split('|', 1)

    imgFlg = component == 'i'
    linkFlg = component == 'c'
    scriptFlg = component == 'j'
    videoFlg = component == 'v'
    xmlFlg = component == 'x'

    name = dir = str(update.message.chat.id)
    if not os.path.isdir(dir):
        os.makedirs(dir)

    auth = get_credentials(update.from_user.id)
    obj = urlDownloader(imgFlg=imgFlg, linkFlg=linkFlg, scriptFlg=scriptFlg, videoFlg=videoFlg, xmlFlg=xmlFlg, file_size_limit=10*1024*1024, auth=auth)
    res, summary = obj.savePage(url, dir)
    if not res:
        return await update.message.reply('Something went wrong!')

    zip_filename = f"{name}.zip"
    shutil.make_archive(name, 'zip', base_dir=dir)

    try:
        await update.message.reply_document(zip_filename, caption=summary)
    except Exception as e:
        print(f"Failed to send document: {e}")

    try:
        shutil.rmtree(dir)
    except Exception as e:
        print(f"Failed to remove directory {dir}: {e}")

    try:
        os.remove(zip_filename)
    except Exception as e:
        print(f"Failed to remove zip file {zip_filename}: {e}")

    print("Download completed successfully!")  # Debug statement

def is_valid_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            return True
        print(f"HEAD request failed with status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        # Fallback to GET request if HEAD fails
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            return True
        print(f"GET request failed with status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
    except requests.RequestException as e:
        print(f"Request exception: {e}")
    return False

Bot.run()
