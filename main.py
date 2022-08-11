# Warning : the whole project is still developing please don't use it for working.
from __future__ import annotations

import itertools
import signal
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor

import multitasking
import requests
from retry import retry
from tqdm import tqdm

signal.signal(signal.SIGINT, multitasking.killall)


def split(start: int, end: int, step: int) -> list[tuple[int, int]]:
    parts = [(start, min(start + step, end))
             for start in range(0, end, step)]
    return parts


class ZipCracker:
    def __init__(self, maxNum: int, fileName: str):
        self.max_num = maxNum
        self.filename = fileName
        self.pwd = []
        start_t = time.time()
        print("Init ~~~")
        init_pool = ProcessPoolExecutor(8)
        for i in range(self.max_num):
            i += 1
            init_pool.submit(self.pre_guess_pwd(i))
        init_pool.shutdown(True)
        self.len_pwd = len(self.pwd)
        print("Cracking ~~~")
        pwd_list = [self.pwd[i:i + 100] for i in range(0, len(self.pwd), 100)]
        crack_pool = ProcessPoolExecutor(8)
        for i in pwd_list:
            crack_pool.submit(self.guess(i))
        crack_pool.shutdown(True)
        end_t = time.time()
        print("Cost :" + str(end_t - start_t))
        sys.exit(0)

    def pre_guess_pwd(self, guess_num: int):
        tmp = itertools.combinations("1234567890!@#$%^&*()-=_+~`qwertyuiop\\|asdfghjkl;zxcvbnm,./:<>?", guess_num)
        tmp_pwd = []
        for i in tmp:
            tmp_pwd.append("".join(i))

        self.pwd += tmp_pwd

    def unzip(self):
        file = zipfile.ZipFile(self.filename)
        file.extractall("./")

    def guess(self, pwd):
        file = zipfile.ZipFile(self.filename)
        for i in pwd:
            file.extractall(pwd=bytes(i.encode()))


class MultiThreadDownload:
    def __init__(self, url: str):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE'
        }
        self.MB = 1024 ** 2
        self.url = url
        self.file_name = url.split("/")[len(url.split("/")) - 1]
        self.download(self.url, self.file_name)

    def get_file_size(self, url: str, raise_error: bool = False) -> int:
        response = requests.head(url)
        file_size = response.headers.get('Content-Length')
        if file_size is None:
            if raise_error is True:
                raise ValueError('该文件不支持多线程分段下载！')
            return int(file_size)
        return int(file_size)

    def download(self, url: str, file_name: str, retry_times: int = 3,
                 each_size=16 * (1024 ** 2)) -> None:
        f = open(file_name, 'wb')
        file_size = self.get_file_size(url)

        @retry(tries=retry_times)
        @multitasking.task
        def start_download(start: int, end: int) -> None:
            _headers = self.headers.copy()
            _headers['Range'] = f'bytes={start}-{end}'
            response = session.get(url, headers=_headers, stream=True)
            chunk_size = self.MB
            chunks = []
            for chunk in response.iter_content(chunk_size=chunk_size):
                chunks.append(chunk)
                bar.update(chunk_size / self.MB)
            f.seek(start)
            for chunk in chunks:
                f.write(chunk)
            del chunks

        session = requests.Session()
        each_size = min(each_size, file_size)

        parts = split(0, file_size, int(each_size))
        print(f'分块数：{len(parts)}')
        bar = tqdm(total=file_size / self.MB, desc=f'下载文件：{file_name}', colour="green", unit="MB")
        for part in parts:
            start, end = part
            start_download(start, end)
        multitasking.wait_for_tasks()
        f.close()
        bar.close()


