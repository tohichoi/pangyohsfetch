import unittest
import pickle
import unittest
from pprint import pprint

from bs4 import BeautifulSoup

from main import get_html, urls, check_new_article, old_articles, make_message


class MyTestCase(unittest.TestCase):

    def test_something(self):
        urls = {
            'notice': ['http://www.pangyo.hs.kr/board.list?mcode=1110&cate=1110', 'http://www.pangyo.hs.kr/board.list?mcode=1110&cate=1110', 13],
            'family_notice': ['http://www.kumdo.org/deahan_kumdo/d-kumdo6.php', 'http://www.kumdo.org/deahan_kumdo/', 16],
        }

        htmls = dict()
        new_articles = dict()

        for board_name, url in urls.items():
            if board_name not in htmls:
                htmls[board_name] = get_html(url[0])

            # htmls[board_name] = get_html(url[0])

            soup = BeautifulSoup(htmls[board_name], features="html.parser")
            elm = soup.find('table', 'boardList')
            tr = elm.find_all('tr')
            # skip th
            for r in tr[1:]:
                # print(r.text.strip().replace("\n", ' '))
                td = r.find_all('td')
                # td[0] : 번호
                # td[1] : 제목
                # td[2] : 작성자
                # td[3] : 등록일
                # td[4] : 조회
                # td[5] : 파일
                # for d in td:
                #     print(d.text.strip())
                num = td[0].text.strip()
                board_key = board_name + num
                if len(num) > 0 and num.isnumeric() and board_key not in o_articles:
                    new_articles[board_key] = (
                        td[1].text.strip(), urls[board_name][1] + td[1].find('a').attrs['href'].strip())

        pprint(new_articles)
        self.assertGreater(len(new_articles))


class TestSaveHtml(unittest.TestCase):
    def test_save_html(self):
        htmls = dict()
        for board_name, url in urls.items():
            htmls[board_name] = get_html(url[0])
        with open('htmls.pickle', 'wb+') as fd:
            pickle.dump(htmls, fd)

    def test_parse(self):
        with open('htmls.pickle', 'rb') as fd:
            htmls = pickle.load(fd)

        new_articles = check_new_article(old_articles, htmls)
        msgs = make_message(new_articles)
        pprint(msgs)


if __name__ == '__main__':
    unittest.main()
