import os
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

class urlDownloader:
    def __init__(self, imgFlg=True, linkFlg=True, scriptFlg=True, videoFlg=True, xmlFlg=True, htmlFlg=False, file_size_limit=None, max_retries=3, auth=None):
        self.soup = None
        self.imgFlg = imgFlg
        self.linkFlg = linkFlg
        self.scriptFlg = scriptFlg
        self.videoFlg = videoFlg
        self.xmlFlg = xmlFlg
        self.htmlFlg = htmlFlg
        self.file_size_limit = file_size_limit
        self.max_retries = max_retries
        self.auth = auth
        self.linkType = ('css', 'png', 'ico', 'jpg', 'jpeg', 'mov', 'ogg', 'gif', 'xml', 'js')
        self.videoType = ('mp4', 'webm', 'ogg')
        self.session = requests.Session()
        self.summary = {
            'images': 0,
            'links': 0,
            'scripts': 0,
            'videos': 0,
            'xmls': 0,
            'htmls': 0
        }

    def savePage(self, url, pagefolder='page'):
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
            if self.videoFlg:
                self._soupfindnSave(url, pagefolder, tag2find='video', inner='src', category='videos')
            if self.xmlFlg:
                self._soupfindnSave(url, pagefolder, tag2find='xml', inner='src', category='xmls')
            if self.htmlFlg:
                with open(os.path.join(pagefolder, 'page.html'), 'wb') as file:
                    file.write(self.soup.prettify('utf-8'))
                self.summary['htmls'] += 1
            summary = self.generate_summary()
            return True, summary
        except Exception as e:
            print(f"> savePage(): Create page error: {str(e)}")
            return False, str(e)

    def _soupfindnSave(self, url, pagefolder, tag2find='img', inner='src', category='images'):
        folder = os.path.join(pagefolder, category)
        if not os.path.exists(folder):
            os.mkdir(folder)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for tag in self.soup.find_all(tag2find):
                try:
                    turl = tag.get(inner)
                    if turl is None:
                        continue
                    turl = turl.split('?')[0]
                    filename = os.path.basename(turl).strip().replace(" ", "_")
                    if len(filename) > 25:
                        filename = filename[-25:]
                    savepath = os.path.join(folder, filename)
                    if not turl.startswith("http"):
                        turl = urljoin(url, turl)
                    futures.append(executor.submit(self._download_file, turl, savepath, category))
                except Exception as e:
                    print(f"> _soupfindnSave(): Inner exception: {str(e)}")
            for future in tqdm(futures, desc=f"Downloading {category}"):
                try:
                    future.result()
                except Exception as e:
                    print(f"> _soupfindnSave(): Future exception: {str(e)}")

    def _download_file(self, url, savepath, category):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = self.session.get(url, headers=headers, stream=True, auth=self.auth)
            response.raise_for_status()
            if self.file_size_limit and int(response.headers.get('content-length', 0)) > self.file_size_limit:
                print(f"Skipping {url} due to size limit.")
                return
            with open(savepath, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            self.summary[category] += 1
        except Exception as e:
            print(f"> _download_file(): Download error for {url}: {str(e)}")

    def generate_summary(self):
        components = [f"{count} {name}" for name, count in self.summary.items() if count > 0]
        return f"Downloaded: {', '.join(components)}."
