# 警告： 本项目仍处于开发阶段，请勿要将其用于生产环境
# Warning : the whole project is still developing please don't use it for working.
from __future__ import annotations

import itertools
import signal
import sys
import os
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor

import PyPDF4
import multitasking
import requests
from retry import retry
from tqdm import tqdm

signal.signal(signal.SIGINT, multitasking.killall)


# 分割文件
# Func for splitting file
def split(start: int, end: int, step: int) -> list[tuple[int, int]]:
    parts = [(start, min(start + step, end))
             for start in range(0, end, step)]
    return parts


# Zip密码破解
# Zip password cracking
class ZipCracker:
    def __init__(self, maxNum: int, fileName: str):
        self.max_num = maxNum
        self.filename = fileName
        self.pwd = []
        start_t = time.time()
        print("Init 初始化密码~~~")
        # 获取所有可能的密码
        # Get all kinds of pwd in multiprocess way
        init_pool = ProcessPoolExecutor(os.cpu_count() * 2)
        for i in range(self.max_num):
            i += 1
            init_pool.submit(self.pre_guess_pwd(i))
        init_pool.shutdown(True)
        self.len_pwd = len(self.pwd)
        print("Cracking 正在破解~~~")
        # 尝试所有密码以解压文件
        # Try all password to unzip the zip file
        pwd_list = [self.pwd[i:i + 100] for i in range(0, len(self.pwd), 100)]
        crack_pool = ProcessPoolExecutor(os.cpu_count() * 2)
        for i in pwd_list:
            crack_pool.submit(self.guess(i))
        crack_pool.shutdown(True)
        end_t = time.time()
        print("Cost 耗时:" + str(end_t - start_t))

    # 全排列密码
    # Combinations all pwd
    def pre_guess_pwd(self, guess_num: int):
        tmp = itertools.combinations(r'1234567890!@#$%^&*()-=_+~`qwertyuiop\|asdfghjkl;zxcvbnm,./:<>?', guess_num)
        tmp_pwd = []
        for i in tmp:
            tmp_pwd.append("".join(i))

        self.pwd += tmp_pwd

    # 解压文件
    # Extract zip files
    def unzip(self):
        file = zipfile.ZipFile(self.filename)
        file.extractall("./")

    # 尝试密码
    # Try pwd
    def guess(self, pwd):
        file = zipfile.ZipFile(self.filename)
        for i in pwd:
            file.extractall(pwd=bytes(i.encode()))


# 多线程下载
# Multithread download
class MultiThreadDownload:
    def __init__(self, url: str):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE'
        }
        self.MB = 1024 ** 2
        self.url = url
        self.file_name = url.split("/")[len(url.split("/")) - 1]
        # 开始分段下载文件
        # Start downloading file in multithread way
        self.download(self.url, self.file_name)

    # 获取文件大小以进行分段操作
    # Get file size to make sure can we download this file in multithread way
    def get_file_size(self, url: str, raise_error: bool = False) -> int:
        response = requests.head(url)
        file_size = response.headers.get('Content-Length')
        if not file_size:
            if raise_error is True:
                raise ValueError('This file does not support multithread download, it may because '
                                 'it size is too small \n该文件不支持多线程分段下载！')
            return int(file_size)
        return int(file_size)

    # 分段多线程下载
    # Real multithread download func
    def download(self, url: str, file_name: str, retry_times: int = 3,
                 each_size=16 * (1024 ** 2)) -> None:
        f = open(file_name, 'wb')
        file_size = self.get_file_size(url)

        @retry(tries=retry_times)
        @multitasking.task
        # 顾名思义
        # Just like its name
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

        # 分割文件
        # Split file
        parts = split(0, file_size, int(each_size))
        print(f'Parts  numbers 分块数：{len(parts)}')
        bar = tqdm(total=file_size / self.MB, desc=f'Downloading file 下载文件：{file_name}', colour="green", unit="MB")
        for part in parts:
            start, end = part
            start_download(start, end)
        multitasking.wait_for_tasks()
        f.close()
        bar.close()
