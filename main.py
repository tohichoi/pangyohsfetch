# This is a sample Python script.

import json
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import logging
import os
import pickle
import re
import urllib.request

from bs4 import BeautifulSoup
from telegram import Bot
from telegram.ext import Updater, CommandHandler
from telegram.utils.helpers import escape_markdown

old_articles = {}
urls = {
    'notice': ['http://www.pangyo.hs.kr/board.list?mcode=1110&cate=1110',
               'http://www.pangyo.hs.kr', 0],
    'family_notice': ['http://www.pangyo.hs.kr/board.list?mcode=1111&cate=1111',
                      'http://www.pangyo.hs.kr', 0],
}


def get_html(url):
    req = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
    )

    with urllib.request.urlopen(req) as response:
        data = response.read().decode('euc-kr')
        return data


def check_new_article(o_articles, preloaded_htmls=None):

    htmls = preloaded_htmls if preloaded_htmls else dict()

    # for k, u in urls.items():
    #     htmls[k] = get_html(u[0])
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
                # http://www.pangyo.hs.kr/board.list?mcode=1110&cate=1110
                # http://www.pangyo.hs.kr/board.read?mcode=1110&id=5475

                new_articles[board_key] = (
                    td[1].text.strip(), urls[board_name][1] + td[1].find('a').attrs['href'].strip())

    return new_articles


def get_title(board_key):
    if re.search('^notice[0-9]+$', board_key):
        return '[공지사항]'
    if re.search('^family_notice[0-9]+$', board_key):
        return '[가정통신문]'
    else:
        return ''


def make_message(articles):
    # msg = f'**{title}**\n'
    msgs = []
    m = ''
    for k, v in articles.items():
        # s = f'* \\[{k} {v[0]}\\]\\({v[1]}\\)\n'
        s = f'{get_title(k)} <a href="{v[1]}">{v[0]}</a>\n'
        if len(m) + len(s) > 4096:
            msgs.append(m)
            m = s
        else:
            m += s

    if len(m) > 0:
        msgs.append(m)

    return msgs


def fetch_articles(tbot, chatid, o_article, notify_empty_event=False):

    new_articles_sl = check_new_article(o_article)
    msgs = make_message(new_articles_sl)
    if len(msgs) > 0:
        for msg in msgs:
            tbot.send_message(chatid, msg, parse_mode='HTML')
    else:
        if notify_empty_event:
            tbot.send_message(chatid, "No new message", parse_mode='HTML')

    if len(new_articles_sl) > 0:
        o_article.update(**new_articles_sl)
        with open('old_articles.pickle', 'wb+') as fd:
            pickle.dump(o_article, fd)


def job_check(context):
    logging.info(f'{context}')

    tbot = context.bot
    chatid = context.job.context

    fetch_articles(tbot, chatid, old_articles)


# context: telegram.ext.CallbackContext
def callback_check(update, context):
    logging.info(f'{update.effective_message.text}')

    chatid = update.effective_chat.id

    fetch_articles(context.bot, chatid, old_articles, notify_empty_event=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        #    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                        format='%(asctime)s : %(funcName)s : %(message)s')

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    with open('bot.json') as fd:
        cf = json.load(fd)
        Bot(cf['bot_token'])

    if os.path.exists('old_articles.pickle'):
        with open('old_articles.pickle', 'rb') as fd:
            old_articles = pickle.load(fd)

    updater = Updater(token=cf['bot_token'], use_context=True)
    dispatcher = updater.dispatcher

    job_queue = updater.job_queue
    dispatcher.add_handler(CommandHandler('check', callback_check, pass_job_queue=True))

    updater.job_queue.run_repeating(job_check, interval=3600 * 2, first=1, context=cf['bot_chatid'])

    updater.start_polling()
