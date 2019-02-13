from bs4 import BeautifulSoup
import requests


class BaseMovie:
    def __init__(self):
        self.domain = 'https://www.360kan.com'

    @classmethod
    def _get_html(cls, url, content_type='text'):
        content = requests.get(url)
        soup = BeautifulSoup(getattr(content, content_type, ''), 'lxml')
        return soup

    def get_index_list(self):
        url = f'{self.domain}/dianshi/list.php?cat=101&year=all&area=all&act=all'
        soup = self._get_html(url)
        return soup.text


if __name__ == '__main__':
    m = BaseMovie()
    m.get_index_list()