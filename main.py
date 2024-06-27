import os
import shutil
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from web_dl import urlDownloader
from config import API_HASH, API_ID, BOT_TOKEN


BOT_TOKEN = BOT_TOKEN
API_ID = API_ID
API_HASH = API_HASH

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
    htmlFlg = component == 'h'  # Adding HTML flag here

    name = dir = str(update.message.chat.id)
    if not os.path.isdir(dir):
        os.makedirs(dir)

  
    obj = urlDownloader(imgFlg=imgFlg, linkFlg=linkFlg, scriptFlg=scriptFlg, videoFlg=videoFlg, xmlFlg=xmlFlg, htmlFlg=htmlFlg, file_size_limit=10*1024*1024)
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
