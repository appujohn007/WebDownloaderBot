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
    def __init__(self, imgFlg=True, linkFlg=True, scriptFlg=True, videoFlg=True, xmlFlg=True, htmlFlg=True, file_size_limit=None, max_retries=3, auth=None):
        self.soup = None
        self.imgFlg = imgFlg
        self.linkFlg = linkFlg
        self.scriptFlg = scriptFlg
        self.videoFlg = videoFlg
        self.xmlFlg = xmlFlg
        self.htmlFlg = htmlFlg
        self.file_size_limit = file_size_limit
        self.max_retries = max_retries
        self.linkType = ('css', 'png', 'ico', 'jpg', 'jpeg', 'mov', 'ogg', 'gif', 'xml', 'js')
        self.videoType = ('mp4', 'webm', 'ogg', 'mkv')
        self.summary = {
            'images': 0,
            'links': 0,
            'scripts': 0,
            'videos': 0,
            'xmls': 0,
            'htmls': 0
        }
        self.session = requests.Session()

    def savePage(self, url, pagefolder='page'):
        """Save the web page components based on the input URL and dir name."""
        try:
            response = self.session.get(url)
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
            if self.videoFlg:
                self._soupfindnSave(url, pagefolder, tag2find='video', inner='src', category='videos')
            if self.xmlFlg:
                self._soupfindnSave(url, pagefolder, tag2find='xml', inner='src', category='xmls')
            if self.htmlFlg:
                self._soupfindnSave(url, pagefolder, tag2find='html', inner='src', category='htmls')
            with open(os.path.join(pagefolder, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(self.soup.prettify())
            summary_text = "\n".join([f"{k}: {v}" for k, v in self.summary.items()])
            return True, summary_text
        except Exception as e:
            print(f"Error saving page: {e}")
            return False, ""

    def _soupfindnSave(self, url, pagefolder, tag2find='img', inner='src', category='images'):
        """Find and save specific elements in the soup."""
        tags = self.soup.find_all(tag2find)
        print(f"Found {len(tags)} {category} tags")  # Debug statement
        urls = [tag.get(inner) for tag in tags]
        urls = [urljoin(url, u) for u in urls]
        urls = list(set(urls))
        self.summary[category] += len(urls)
        folder = os.path.join(pagefolder, category)
        if not os.path.exists(folder):
            os.mkdir(folder)
        with ThreadPoolExecutor(max_workers=10) as executor:
            for u in urls:
                executor.submit(self._savefile, folder, u)

    def _savefile(self, folder, fileurl):
        """Save the file content from the URL to the given folder."""
        if not fileurl:
            return
        name = re.sub(r'\W+', '', os.path.basename(fileurl))
        filename = os.path.join(folder, name)
        print(f"Downloading {fileurl} to {filename}")  # Debug statement
        try:
            response = self.session.get(fileurl, stream=True)
            response.raise_for_status()
            content_length = response.headers.get('Content-Length')
            if content_length and self.file_size_limit and int(content_length) > self.file_size_limit:
                print(f"Skipping {fileurl}, file size {content_length} exceeds limit {self.file_size_limit}")
                return
            with open(filename, 'wb') as f:
                for chunk in tqdm(response.iter_content(chunk_size=1024)):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            print(f"Error downloading {fileurl}: {e}")
            if os.path.exists(filename):
                os.remove(filename)
