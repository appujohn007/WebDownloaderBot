# web_dl.py
import os
import re
import sys
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

class urlDownloader(object):
    """Download the webpage components based on the input URL."""
    def __init__(self, imgFlg=True, linkFlg=True, scriptFlg=True, file_size_limit=None, max_retries=3, auth=None):
        self.soup = None
        self.imgFlg = imgFlg
        self.linkFlg = linkFlg
        self.scriptFlg = scriptFlg
        self.file_size_limit = file_size_limit
        self.max_retries = max_retries
        self.auth = auth
        self.linkType = ('css', 'png', 'ico', 'jpg', 'jpeg', 'mov', 'ogg', 'gif', 'xml', 'js')
        self.session = requests.Session()
        self.summary = {
            'images': 0,
            'links': 0,
            'scripts': 0
        }

    def savePage(self, url, pagefolder='page'):
        """Save the web page components based on the input URL and dir name."""
        try:
            response = self.session.get(url, auth=self.auth)
            response.raise_for_status()
            self.soup = BeautifulSoup(response.text, features="lxml")
            if not os.path.exists(pagefolder):
                os.mkdir(pagefolder)
            if self.imgFlg:
                self._soupfindnSave(url, pagefolder, tag2find='img', inner='src', category='images')
            if self.linkFlg:
                self._soupfindnSave(url, pagefolder, tag2find='link', inner='href', category='links')
            if self.scriptFlg:
                self._soupfindnSave(url, pagefolder, tag2find='script', inner='src', category='scripts')
            with open(os.path.join(pagefolder, 'page.html'), 'wb') as file:
                file.write(self.soup.prettify('utf-8'))
            summary = f"Downloaded: {self.summary['images']} images, {self.summary['links']} links, {self.summary['scripts']} scripts."
            return True, summary
        except Exception as e:
            print(f"> savePage(): Create files failed: {str(e)}.", file=sys.stderr)
            return False, None

    def _download_file(self, fileurl, filepath):
        """Download a file with retry mechanism."""
        for attempt in range(self.max_retries):
            try:
                filebin = self.session.get(fileurl, stream=True, auth=self.auth)
                filebin.raise_for_status()
                if self.file_size_limit and int(filebin.headers.get('content-length', 0)) > self.file_size_limit:
                    print(f"File {fileurl} exceeds the size limit.", file=sys.stderr)
                    return False
                with open(filepath, 'wb') as file:
                    for chunk in filebin.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                print(f"Successfully downloaded {fileurl} to {filepath}")  # Debug statement
                return True
            except requests.RequestException as exc:
                print(f"Attempt {attempt + 1} failed for {fileurl}: {exc}", file=sys.stderr)
        return False

    def _soupfindnSave(self, url, pagefolder, tag2find='img', inner='src', category='images'):
        """Saves on specified pagefolder all tag2find objects."""
        pagefolder = os.path.join(pagefolder, tag2find)
        if not os.path.exists(pagefolder):
            os.mkdir(pagefolder)
        elements = self.soup.findAll(tag2find)
        if not elements:
            print(f"No {tag2find} elements found.", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for res in tqdm(elements, desc=f"Downloading {tag2find}"):
                if not res.has_attr(inner):
                    continue
                filename = re.sub(r'\W+', '.', os.path.basename(res[inner]))
                if tag2find == 'link' and (not any(ext in filename for ext in self.linkType)):
                    filename += '.html'
                fileurl = urljoin(url, res.get(inner))
                filepath = os.path.join(pagefolder, filename)
                res[inner] = os.path.join(os.path.basename(pagefolder), filename)
                if not os.path.isfile(filepath):
                    print(f"Downloading {fileurl} to {filepath}")  # Debug statement
                    futures.append(executor.submit(self._download_file, fileurl, filepath))
            for future in futures:
                if future.result():
                    self.summary[category] += 1
        print(f"Completed downloading {tag2find} elements. Total: {self.summary[category]}")  # Debug statement

# main.py
import os
import sys
import shutil
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    parts = m.text.split()
    url = parts[0]
    components = parts[1:]  # Extract components from the message
    download_directly = False

    if not url.startswith('http'):
        return await m.reply("The URL must start with 'http' or 'https'")

    if not is_valid_url(url):
        return await m.reply("The URL is invalid or inaccessible")

    # Check if components are specified in the message
    if components:
        imgFlg, linkFlg, scriptFlg = parse_components(' '.join(components))
        print(f"Flags - img: {imgFlg}, link: {linkFlg}, script: {scriptFlg}")  # Debug statement
    else:
        # No components specified, prompt user with options
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("HTML", callback_data="html"),
                    InlineKeyboardButton("CSS", callback_data="css"),
                    InlineKeyboardButton("Images", callback_data="images")
                ],
                [
                    InlineKeyboardButton("XML", callback_data="xml"),
                    InlineKeyboardButton("Video", callback_data="video"),
                    InlineKeyboardButton("JavaScript", callback_data="js")
                ]
            ]
        )
        await m.reply("Please select which components to download:", reply_markup=keyboard)
        return

    name = dir = str(m.chat.id)
    if not os.path.isdir(dir):
        os.makedirs(dir)

    obj = urlDownloader(imgFlg=imgFlg, linkFlg=linkFlg, scriptFlg=scriptFlg, file_size_limit=10*1024*1024, auth=auth)
    res, summary = obj.savePage(url, dir)
    if not res:
        return await m.reply('Something went wrong!')

    shutil.make_archive(name, 'zip', base_dir=dir)
    await m.reply_document(name+'.zip', caption=summary)

    shutil.rmtree(dir)
    os.remove(name+'.zip')

    print("Download completed successfully!")  # Debug statement

def parse_components(text):
    components = text.split()
    imgFlg = 'img' in components
    linkFlg = 'css' in components
    scriptFlg = 'script' in components
    return imgFlg, linkFlg, scriptFlg

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
