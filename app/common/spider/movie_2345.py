from common.helper import BaseSpider


class BaseMovie(BaseSpider):

    def __init__(self):
        # self.http = HttpRequest()
        pass

    @staticmethod
    def splicing_url(cate, movie_type, page):
        if cate == 'movie':
            return f'http://dianying.2345.com/list/{movie_type}------{page}.html'
        if cate == 'tv':
            return f'http://{cate}.2345.com/{movie_type}---{page}.html'
        if cate == 'dongman':
            return f'http://{cate}.2345.com/ltlx{movie_type}/{page}'
        if cate == 'zongyi':
            return f'http://kan.2345.com/{cate}/llx{movie_type}/{page}'

    def get_page_list(self, cate, movie_type='', page='1'):
        """
        获取列表页数据
        :param cate: 列表类型（电影，电视剧等）
        :param movie_type: 视频类型（热血，玄幻等）
        :return: list
        """
        url = self.splicing_url(cate, movie_type, page)
        soup = self._get_html(url)
        items = soup.select('#contentList li[class!="item-gg"]')
        datas = [self._parse_page_item(item) for item in items]
        return datas

    @staticmethod
    def _parse_page_item(item):
        stars = item.select_one('.sTit + span')
        title = item.select_one('.sTit')
        img_src = item.select_one('.pic > img')
        detail_href = item.select_one('.aPlayBtn')
        score = item.select_one('.pRightBottom')
        data = {
            'title': title.text.strip() if title else '未知',
            'stars': stars.text if stars else '未知',
            'img_src': img_src.get('data-src'),
            'detail_href': detail_href.get('href'),
            'score': score.text or ''
        }
        return data

    # 只适用于电视剧，动漫
    def enter_detail(self, detail_url):
        soup = self._get_html(detail_url)
        desc = soup.select_one('.pIntro span').text
        sites = soup.select('.wholeTxt .v_conBox')
        play_num_list = [self._parse_detail_item(site) for site in sites]
        data = {
            'desc': desc,
            'play_list': play_num_list
        }
        return data

    def _parse_detail_item(self, item):
        play_num_list = {}
        nums = []
        sitename = item.get('id')
        sitename = self.filter_reg_data(r'(\w+)_', sitename)
        play_list = item.select('.playNumList > a[href^="http"]')
        for play in play_list:
            data = {
                'num': play.select_one('.num').text,
                'href': play.get('href'),
                'title': play.get('title') or ''
            }
            nums.append(data)
        play_num_list[sitename] = nums
        return play_num_list

    def search(self, kw, page='1'):
        url = f'http://so.kan.2345.com/search_{kw}/{page}'
        soup = self._get_html(url)
        items = soup.select('.itemList .item')
        datas = [self._parse_search_item(item) for item in items]
        return datas

    @staticmethod
    def _parse_search_item(item):
        title = item.select_one('.tit h2 a')
        stars = item.select_one('.txtList .liActor')
        img_src = item.select_one('.pic > img')
        detail_href = item.select_one('.tit h2 a')
        score = item.select_one('.pRightBottom')
        cate = item.select_one('')
        data = {
            'title': title.get('title') if title else '未知',
            'stars': stars.text if stars else '未知',
            'img_src': img_src.get('data-src'),
            'detail_href': detail_href.get('href'),
            'score': score.text or ''
        }
        return data


class ZongYi(BaseMovie):
    def enter_detail(self, detail_url):
        soup = self._get_html(detail_url)
        desc = soup.select_one('.pIntro span').text
        sitename = soup.select_one('.playSourceTab a').get('apiname')
        playlist = soup.select('#contentList')
        play_num_list = [self._parse_detail_item(item, sitename) for item in playlist]

        detail_data = {
            'desc': desc,
            'play_list': play_num_list
        }
        return detail_data

    def _parse_detail_item(self, item, sitename):
        nums = []
        play_num_list = {}
        playlist = item.select('li')
        for play in playlist:
            data = {
                'href': play.select_one('.txt a').get('href'),
                'title': play.select_one('.txt a').get('title') or '',
                'num': play.select_one('.pRightBottom').text
            }
            nums.append(data)
        play_num_list[sitename] = nums
        return play_num_list


class Movie(BaseMovie):
    def enter_detail(self, detail_url):
        soup = self._get_html(detail_url)
        desc = soup.select_one('.pIntro span').text
        sites = soup.select('.playSource a')
        play_num_list = [self._parse_detail_item(site) for site in sites]
        data = {
            'desc': desc,
            'play_list': play_num_list
        }
        return data

    def _parse_detail_item(self, item):
        play_num_list = {}
        sitename = item.get('data')
        sitename = self.filter_reg_data(r'(\w+)_', sitename)
        play_num_list[sitename] = [{
            'href': item.get('href'),
            'num': item.text.strip(),
            'title': item.get('title') or ''
        }]
        return play_num_list


class MovieModel:
    title = ''  # 标题
    img_src = ''  # 图片链接
    update_nums = ''  # 更新集数
    play_nums = {}  # 播放具体集数{title：‘’， play_href:''}
    stars = ''  # 明星（导演，主演）
    _detail_href = ''  # 详情页面地址
    desc = ''  # 描述

    def __init__(self, item):
        self.title = item['title']


if __name__ == '__main__':
    # detail_url = 'http://dianying.2345.com/list/------.html'
    # detail_url = 'http://tv.2345.com/detail/55274.html'
    # detail_url = 'http://dongman.2345.com/dm/74725.html'
    # detail_url = 'http://kan.2345.com/zongyi/zy_12/'
    # detail_url = 'http://dianying.2345.com/detail/195593.html'
    # m.get_page_list('movie')
    # m.get_page_list('dongman')
    # m.get_page_list('tv')
    # m.get_page_list('zongyi')
    # m.enter_tv_detail(detail_url)
    # m.enter_movie_detail(detail_url)

    d = BaseMovie()
    # d.enter_detail(detail_url)

    # zy = ZongYi()
    # zy.enter_detail(detail_url)

    # m = Movie()
    # m.enter_detail(detail_url)
    d.search('斗破苍穹')
