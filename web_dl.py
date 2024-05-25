import os
import re
import sys
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, Optional, Dict

class urlDownloader:
    """Download the webpage components based on the input URL."""

    def __init__(self, imgFlg: bool = True, linkFlg: bool = True, scriptFlg: bool = True, file_size_limit: Optional[int] = None, max_retries: int = 3, auth: Optional[Tuple[str, str]] = None):
        self.soup: Optional[BeautifulSoup] = None
        self.imgFlg = imgFlg
        self.linkFlg = linkFlg
        self.scriptFlg = scriptFlg
        self.file_size_limit = file_size_limit
        self.max_retries = max_retries
        self.auth = auth
        self.linkType = ('css', 'png', 'ico', 'jpg', 'jpeg', 'mov', 'ogg', 'gif', 'xml', 'js')
        self.session = requests.Session()
        self.summary: Dict[str, int] = {
            'images': 0,
            'links': 0,
            'scripts': 0
        }

    def savePage(self, url: str, pagefolder: str = 'page') -> Tuple[bool, Optional[str]]:
        """Save the web page components based on the input URL and dir name."""
        try:
            response = self.session.get(url, auth=self.auth)
            response.raise_for_status()
            self.soup = BeautifulSoup(response.text, 'lxml')
            os.makedirs(pagefolder, exist_ok=True)
            
            print(f"Starting to download components from {url}")

            if self.imgFlg:
                print("Downloading images...")
                self._soupfindnSave(url, pagefolder, 'img', 'src', 'images')
            if self.linkFlg:
                print("Downloading links...")
                self._soupfindnSave(url, pagefolder, 'link', 'href', 'links')
            if self.scriptFlg:
                print("Downloading scripts...")
                self._soupfindnSave(url, pagefolder, 'script', 'src', 'scripts')
                
            with open(os.path.join(pagefolder, 'page.html'), 'wb') as file:
                file.write(self.soup.prettify('utf-8'))
            
            summary = f"Downloaded: {self.summary['images']} images, {self.summary['links']} links, {self.summary['scripts']} scripts."
            print(summary)
            return True, summary
        except Exception as e:
            print(f"> savePage(): Create files failed: {str(e)}.", file=sys.stderr)
            return False, None

    def _download_file(self, fileurl: str, filepath: str) -> bool:
        """Download a file with retry mechanism."""
        for attempt in range(self.max_retries):
            try:
                filebin = self.session.get(fileurl, stream=True, auth=self.auth)
                filebin.raise_for_status()
                
                file_size = int(filebin.headers.get('content-length', 0))
                if self.file_size_limit and file_size > self.file_size_limit:
                    print(f"File {fileurl} exceeds the size limit of {self.file_size_limit} bytes.", file=sys.stderr)
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

    def _soupfindnSave(self, url: str, pagefolder: str, tag2find: str, inner: str, category: str) -> None:
        """Saves specified tag objects in the given folder."""
        folder_path = os.path.join(pagefolder, tag2find)
        os.makedirs(folder_path, exist_ok=True)
        
        elements = self.soup.find_all(tag2find)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for res in tqdm(elements, desc=f"Downloading {tag2find}"):
                if not res.has_attr(inner):
                    continue
                
                filename = self._sanitize_filename(res.get(inner))
                if tag2find == 'link' and not any(ext in filename for ext in self.linkType):
                    filename += '.html'
                
                fileurl = urljoin(url, res.get(inner))
                filepath = os.path.join(folder_path, filename)
                
                res[inner] = os.path.join(os.path.basename(folder_path), filename)
                
                if not os.path.isfile(filepath):
                    print(f"Downloading {fileurl} to {filepath}")  # Debug statement
                    futures.append(executor.submit(self._download_file, fileurl, filepath))
            
            for future in futures:
                if future.result():
                    self.summary[category] += 1

    def _sanitize_filename(self, url: str) -> str:
        """Sanitize the filename extracted from the URL."""
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        return re.sub(r'\W+', '.', filename)
