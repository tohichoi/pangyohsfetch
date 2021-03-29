# This is a sample Python script.
import datetime
import socket
import json
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import logging
import os
import pickle
import re
import time
import urllib.request
import html

import pendulum as pendulum
import requests

from bs4 import BeautifulSoup
from telegram import Bot
from telegram.ext import Updater, CommandHandler
from telegram.utils.helpers import escape_markdown

old_articles = {}
urls = {
    'notice': [r'http://www.pangyo.hs.kr/board.list', {'mcode': 1110, 'cate': 1110},
               'http://www.pangyo.hs.kr', 0],
    'family_notice': [r'http://www.pangyo.hs.kr/board.list', {'mcode': 1111, 'cate': 1111},
                      'http://www.pangyo.hs.kr', 0],
    'online_lecture': [r'http://www.pangyo.hs.kr/board.list', {'mcode': 2011, 'cate': 2011},
                       'http://www.pangyo.hs.kr', 0],
}

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "ko-KR,en-GB,en-US;q=0.9,en;q=0.8",
    "Dnt": "1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
}


def get_html(url: str, params: dict):
    logging.info(f'Started')
    retry = 0
    data = ''

    session = requests.Session()
    session.headers = headers

    while retry < 5:
        try:
            # logger.info(f'GET http://www.pangyo.hs.kr')
            # response = session.get(url, timeout=30)
            # logger.info(f'GET {url} {params}')
            session.headers.update({'Host': 'www.pangyo.hs.kr'})
            response = session.get(url, params=params, timeout=30)
            data = response.text
            # data=data.decode('euc-kr')
            logger.info(f'response: {response}')
            break
        except requests.exceptions.RequestException as e:
            logger.info(f'Exception(response) : {e.response}')
            logger.info(f'Exception(request)  : {e.request}')
            retry += 1

    logging.info(f'Tried {retry} times, finished with data length {len(data)}')

    return data


def check_new_article(o_articles, preloaded_htmls=None):
    logging.info(f'Started')

    htmls = preloaded_htmls if preloaded_htmls else dict()

    # for k, u in urls.items():
    #     htmls[k] = get_html(u[0])
    new_articles = dict()

    for board_name, url in urls.items():
        # if board_name not in htmls:
        logger.info(f'Requesting {board_name} with {url[0]}, {url[1]}')
        htmls[board_name] = get_html(url[0], url[1])

        # htmls[board_name] = get_html(url[0])
        logger.info(f'Parsing HTML : {board_name}')
        soup = BeautifulSoup(htmls[board_name], features="html.parser")
        elm = soup.find('table', 'boardList')
        if not elm:
            logging.info(f'Cannot find element "table, boardList"')
            break

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
                    td[1].text.strip(), urls[board_name][2] + td[1].find('a').attrs['href'].strip())

        time.sleep(5)

    logging.info(f'Finished. # of new articles = {len(new_articles)}')

    return new_articles


def get_title(board_key):
    if re.search('^notice[0-9]+$', board_key):
        return '[공지사항] '
    if re.search('^family_notice[0-9]+$', board_key):
        return '[가정통신문] '
    if re.search('^online_lecture[0-9]+$', board_key):
        return '[원격수업] '
    else:
        return ''


def make_message(articles):
    # msg = f'**{title}**\n'
    msgs = []
    m = ''
    for k, v in articles.items():
        # s = f'* \\[{k} {v[0]}\\]\\({v[1]}\\)\n'
        s = f'<b>{get_title(k)}</b><a href="{v[1]}">{html.escape(v[0])}</a>\n'
        if len(m) + len(s) > 4096:
            msgs.append(m)
            m = s
        else:
            m += s

    if len(m) > 0:
        msgs.append(m)

    return msgs


def fetch_articles(tbot, chatid, o_article, notify_empty_event=False):
    # tbot.send_message(chatid, "Checkng new article ...", parse_mode='HTML')
    new_articles_sl = check_new_article(o_article)
    msgs = make_message(new_articles_sl)
    if len(msgs) > 0:
        for msg in msgs:
            logger.info(f'{msg}')
            tbot.send_message(chatid, msg, parse_mode='HTML')
    else:
        if notify_empty_event:
            tbot.send_message(chatid, "No new message", parse_mode='HTML')

    if len(new_articles_sl) > 0:
        o_article.update(**new_articles_sl)
        with open('old_articles.pickle', 'wb+') as fd:
            pickle.dump(o_article, fd)


def job_check(context):
    logging.info(f'Starting job with {context}')

    tbot = context.bot
    chatid = context.job.context

    fetch_articles(tbot, chatid, old_articles, False)

    logging.info(f'Finished')


def callback_ping(update, context):
    logging.info(f'{update.effective_message.text}')

    tbot = context.bot
    chatid = update.effective_chat.id

    jt = context.job_queue.jobs()[0].next_t
    jt_local = pendulum.instance(jt).in_tz('Asia/Seoul')

    msg = f'PONG\n' \
          f'  - Next job : {jt_local.to_iso8601_string()}'
    tbot.send_message(chatid, msg)


# context: telegram.ext.CallbackContext
def callback_check(update, context):
    logging.info(f'{update.effective_message.text}')

    chatid = update.effective_chat.id

    # fetch_articles(context.bot, chatid, old_articles, notify_empty_event=True)
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
    dispatcher.add_handler(CommandHandler('ping', callback_ping, pass_job_queue=True))

    updater.job_queue.run_repeating(job_check, interval=3600 * 2, first=1, context=cf['bot_chatid'])
    # updater.job_queue.run_repeating(job_check, interval=60, first=1, context=cf['bot_chatid'])

    updater.start_polling()
