import os
import re
import requests
from Crypto.Cipher import AES
import base64
from flask import make_response
import mimetypes
from threading import Thread
from queue import Queue
import argparse

ThreadMax = 6


class HttpRequest:
    """
    http请求（后期便于统一加上代理）
    """
    @staticmethod
    def get(url, content_type='content', **kwargs):
        response = requests.get(url, **kwargs)
        if not response.ok:
            raise ConnectionError(f'链接失败\t{response.status_code}')
        return getattr(response, content_type, 'content')

    @staticmethod
    def get_json(url, **kwargs):
        response = requests.get(url, **kwargs)
        if not response.ok:
            raise ConnectionError(f'链接失败\t{response.status_code}')
        return response.json()

    @staticmethod
    def post(url, data, **kwargs):
        response = requests.post(url, data=data, **kwargs)
        if not response.ok:
            raise ConnectionError(f'链接失败\t{response.status_code}')
        return response


class BaseMusic:
    headers = {
        'Cookie': 'appver=1.5.0.75771;',
        'Referer': 'http://music.163.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'
    }

    def __init__(self):
        self.http = HttpRequest()
        self.q = Queue(ThreadMax)

    @staticmethod
    def save_file(name, content, path):
        # 替换掉音乐名称里的/和\，防止名称里出现报错
        name = re.sub(r'[/, \\]', '-', name)
        filename = f'{path}/{name}.mp3'
        print(f'开始下载\t{name}')
        with open(filename, 'wb') as f:
            f.write(content)

    @staticmethod
    def check_path(path):
        if not path:
            path = f'{os.getcwd()}/music'
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    @staticmethod
    def filter_reg_data(pattern, data):
        """
        过滤出所匹配的第一条数据
        :param pattern: 正则表达式
        :param data: 待过滤的数据
        :return: 匹配的第一条数据
        """
        data = re.compile(pattern).findall(data)
        return data.pop() if data else None

    def _check_music_type(self, music_url, music_type):
        # 'https://music.163.com/#/playlist?id=967260532'
        types = self.filter_reg_data(r'#/(\w+)\?id', music_url)
        return True if music_type == types else False


class PlayList(BaseMusic):
    """
    网易云音乐歌单下载
    """
    detail_api = 'https://music.163.com/api/playlist/detail?id={id}'

    def __init__(self, music_url):
        super().__init__()
        status = self._check_music_type(music_url, 'playlist')
        if not status:
            raise TypeError(f'{music_url}\t不是歌单')
        self.playlist_id = self.filter_reg_data(r'\?id=(\d+)', music_url)

    def _get_json(self, playlist_id):
        url = self.detail_api.format(id=playlist_id)
        response = self.http.get_json(url, headers=self.headers)
        response = response.get('result', None)
        data = {
            'title': response.get('name', '未知'),
            'author': response['creator']['nickname'],
            'tracks': response['tracks'],
            'count': response['trackCount']
        }
        return data

    def down_playlist(self, path=None):
        data = self._get_json(self.playlist_id)
        if not path:
            path = f'{os.getcwd()}/music/{data["title"]}'
        if not os.path.exists(path):
            os.makedirs(path)
        print(f'歌单：{data["title"]}\t作者：{data["author"]}\t 歌曲数量：{data["count"]}')
        print('开始下载歌单....')
        music = NetMusic()
        for track in data['tracks']:
            self.q.put(track)
            t = DownAsync(music, track, path, self.q)
            t.start()
        self.q.join()


class NetMusic(BaseMusic):
    # api = 'http://music.163.com/song/media/outer/url?id='

    def __init__(self):
        super().__init__()

    def get_content(self, url, content_type='content', **kwargs):
        """
        获取音乐内容和id
        :param url: 网易云音乐链接
        :param content_type: 下载文件类型
        :param kwargs:
        :return: 下载文件内容， 音乐id
        """
        music_id = self.filter_reg_data(r'\?id=(\d+)', url)
        music_real_url = self.get_real_url(music_id)
        try:
            content = self.http.get(music_real_url, **kwargs)
        except Exception as e:
            raise ValueError(f'{music_real_url} 文件下载失败')
        return content, music_id

    def _get_music_name(self, id):
        """
        获取音乐名称
        :param id: 音乐id
        :return: 音乐名称
        """
        url = f'http://music.163.com/api/song/detail/?ids=[{id}]'
        ret = self.http.get_json(url, headers=self.headers)
        name = ret['songs'][0].get('name', id)
        return name

    def send_music_file(self, music_url):
        """
        发送音乐响应内容（web网页用。。。flask）
        :param music_url: 网易云音乐链接
        :return: 媒体流文件
        """
        content, music_id = self.get_content(music_url)
        filename = self._get_music_name(music_id)
        filename = f'{filename}.mp3'
        response = make_response(content)
        mime_type = mimetypes.guess_type(filename)[0]
        response.headers['Content-Type'] = mime_type
        response.headers['Content-Disposition'] = 'attachment; filename={}'.format(filename.encode().decode('latin-1'))
        return response

    def download_by_url(self, music_url, **kwargs):
        """
        下载音乐文件
        :param music_url: 网易云音乐链接
        :param kwargs:
        :return: None
        """
        content, music_id = self.get_content(music_url, **kwargs)
        name = self._get_music_name(music_id)
        path = kwargs.setdefault('path', None)
        path = self.check_path(path)
        self.save_file(name, content, path)

    def download_by_id(self, music_id, name=None, content_type='content', path=None, **kwargs):
        """
        通过id下载歌曲（主要用于歌单下载）
        :param music_id: 音乐id
        :param name: 音乐名称
        :param content_type: 音乐类型（默认为content）
        :param path: 音乐保存路径
        :param kwargs:
        :return:
        """
        music_real_url = self.get_real_url(music_id)
        if not name:
            name = self._get_music_name(music_id)
        try:
            content = self.http.get(music_real_url, content_type, **kwargs)
        except Exception as e:
            raise ValueError(f'{music_real_url} 文件下载失败')
        path = self.check_path(path)
        self.save_file(name, content, path)

    @staticmethod
    def get_post_params(music_id):
        """
        获取加密后的post参数
        :param music_id:
        :return:
        """
        crypt = Decrypt()
        data = crypt.get_post_params(music_id)
        return data

    def get_real_url(self, music_id):
        """
        获取音乐真实链接（可直接播放）
        :param music_id: 音乐id
        :return: url音乐链接
        """
        post_url = 'https://music.163.com/weapi/song/enhance/player/url?csrf_token='
        post_data = self.get_post_params(music_id)
        response = self.http.post(post_url, headers=self.headers, data=post_data).json()
        try:
            url = response['data'][0].get('url')
        except Exception as e:
            raise ValueError('url获取失败')
        return url


class Decrypt:
    """
    用于伪造网易云发送的参数
    """

    def _get_params(self, music_id):
        # br 为音乐转码率（越高音质越好)
        first_param = "{\"ids\":\"[%d]\",\"br\":320000,\"csrf_token\":\"\"}" % int(music_id)
        iv = "0102030405060708"
        first_key = "0CoJUm6Qyw8W8jud"
        second_key = 16 * 'F'
        h_enc_text = self._AES_encrypt(first_param, first_key, iv)
        h_enc_text = self._AES_encrypt(h_enc_text, second_key, iv)
        return h_enc_text

    @staticmethod
    def _get_encecKey():
        encSecKey = "257348aecb5e556c066de214e531faadd1c55d814f9be95fd06d6bff9f4c7a41f831f6394d5a3fd2e3881736d94a02ca919d952872e7d0a50ebfa1769a7a62d512f5f1ca21aec60bc3819a9c3ffca5eca9a0dba6d6f7249b06f5965ecfff3695b54e1c28f3f624750ed39e7de08fc8493242e26dbc4484a01c76f739e135637c"
        return encSecKey

    @staticmethod
    def _AES_encrypt(text, key, iv):
        pad = 16 - len(text) % 16
        if isinstance(text, str):
            text = text + pad * chr(pad)
        else:
            text = text.decode('utf-8') + pad * chr(pad)
        encryptor = AES.new(key, AES.MODE_CBC, iv)
        encrypt_text = encryptor.encrypt(text)
        encrypt_text = base64.b64encode(encrypt_text)
        return encrypt_text

    def get_post_params(self, music_id):
        data = {
            "params": self._get_params(music_id),
            "encSecKey": self._get_encecKey()
        }
        return data


class DownAsync(Thread):
    def __init__(self, music, track, path, queue):
        super().__init__()
        self.queue = queue
        self.name = track.get('name', '未知')
        self.music = music
        self.id = track.get('id')
        self.path = path

    def run(self):
        try:
            self.music.download_by_id(self.id, self.name, path=self.path)
        except Exception as e:
            print(e)
        finally:
            self.queue.get()
            self.queue.task_done()


def music_cli():
    args = argparse.ArgumentParser(description='网易云音乐下载工具')
    args.add_argument('-u', '--url', default=None, help='单个音乐下载，后接音乐链接')
    args.add_argument('-p', '--playlist', default=None, help='音乐歌单下载，后接音乐链接')
    arg = args.parse_args()
    if arg.playlist:
        playlist = PlayList(arg.playlist)
        playlist.down_playlist()
    if arg.url:
        music = NetMusic()
        music.download_by_url(arg.url)


def main():
    music_cli()
    # 歌曲下载
    # url = 'https://music.163.com/#/song?id=1313052711'
    # music = NetMusic()
    # music.download_by_url(url)
    # 歌单下载
    # playlist_url = 'https://music.163.com/#/playlist?id=2428607226'
    # playlist = PlayList(playlist_url)
    # playlist.down_playlist()


if __name__ == '__main__':
    main()
