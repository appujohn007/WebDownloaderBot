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
