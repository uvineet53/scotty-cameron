import requests
from bs4 import BeautifulSoup
import logging
import dotenv
import datetime
import json
import time
import urllib3
import urllib.parse as urlparse
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, HardwareType
# from fp.fp import FreeProxy

logging.basicConfig(filename='test.log', filemode='a', format='%(asctime)s - %(name)s - %(message)s',
                    level=logging.DEBUG)

software_names = [SoftwareName.CHROME.value]
hardware_type = [HardwareType.MOBILE__PHONE]
user_agent_rotator = UserAgent(
    software_names=software_names, hardware_type=hardware_type)
CONFIG = dotenv.dotenv_values()

# proxyObject = FreeProxy(country_id=[CONFIG['LOCATION']], rand=True)

INSTOCK = []


def url_fix(s):
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urlparse.quote(path, '/%')
    qs = urlparse.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))


def scrape_main_site(headers):
    items = []
    hdrs = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.scottycameron.com/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Cache-Control': 'max-age=0',
    }

    response = requests.get(
        'https://www.scottycameron.com/store/', headers=hdrs)
    soup = BeautifulSoup(response.text.replace('id', 'ref').replace(
        'data-test-selector', 'id'), 'html.parser')
    products = soup.find_all('article', {'class': "product-item"})
    print(len(products))
    for product in products:
        item = [
            product.find('h4', {'id': 'hdgProductName'}).text,
            product.find('a', {'id': 'linkProductURL'})['href'],
            product.find('span', {'id': "spanPrice"}).text,
            product.find('img', {'id': "imgProductImage"})['data-src'],
        ]
        items.append(item)
    print(items)
    return items


def discord_webhook(product_item):
    data = {}
    data["username"] = CONFIG['USERNAME']
    data["avatar_url"] = CONFIG['AVATAR_URL']
    data["embeds"] = []
    embed = {}
    if product_item == 'initial':
        embed["author"] = {'name': "CONNECTED @ SCOTTY CAMERON", 'url': 'https://www.scottycameron.com/',
                           'icon_url': 'https://i.imgur.com/XEnzpi6.png'}
        embed["description"] = "Cache Cleared Successfully!"
    else:
        embed["author"] = {'name': "UPDATE @ SCOTTY CAMERON", 'url': 'https://www.scottycameron.com/store/',
                           'icon_url': 'https://i.imgur.com/XEnzpi6.png'}
        embed["title"] = product_item[0]
        embed["description"] = f'**Price: **{product_item[2]}'
        embed['url'] = product_item[1]
        embed['thumbnail'] = {'url': url_fix(product_item[3])}

    embed["color"] = int(CONFIG['COLOUR'])
    embed["footer"] = {'text': 'SCOTTY CAMERON',
                       'icon_url': 'https://i.imgur.com/XEnzpi6.png'}
    embed["fields"] = [{'name': 'Quick Links: ', 'value': '[New](https://www.scottycameron.com/)' +
                        ' | ' + '[Accessories](https://www.scottycameron.com/store/accessories/)', 'inline': True}]
    embed["timestamp"] = str(datetime.datetime.utcnow())
    data["embeds"].append(embed)

    result = requests.post(CONFIG['WEBHOOK'], data=json.dumps(
        data), headers={"Content-Type": "application/json"})

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err)
        logging.error(msg=err)
    else:
        print("Payload delivered successfully, code {}.".format(result.status_code))
        logging.info("Payload delivered successfully, code {}.".format(
            result.status_code))


def checker(item):
    for product in INSTOCK:
        if product == item:
            return True
    return False


def remove_duplicates(mylist):
    return [list(t) for t in set(tuple(element) for element in mylist)]


def comparitor(item, start):
    if not checker(item):
        INSTOCK.append(item)
        if start == 0:
            discord_webhook(item)


def monitor():
    print('STARTING MONITOR')
    logging.info(msg='Successfully started monitor')
    discord_webhook('initial')
    start = 1
    proxy_no = 0

    # proxy_list = CONFIG['PROXY'].split('%')
    # proxy = {"http": proxyObject.get()} if proxy_list[0] == "" else {
    #     "http": f"http://{proxy_list[proxy_no]}"}
    headers = {'User-Agent': user_agent_rotator.get_random_user_agent()}
    keywords = CONFIG['KEYWORDS'].split('%')
    negative_keywords = CONFIG['NEG_KEYWORDS'].split('%')
    while True:
        try:
            items = remove_duplicates(scrape_main_site(headers))
            print(len(items))
            for item in items:
                check = False
                neg_check = False
                if keywords == '':
                    comparitor(item, start)
                else:
                    for key in keywords:
                        if key.lower() in item[0].lower():
                            check = True
                            break
                    if negative_keywords == '':
                        neg_check = False
                    else:
                        for neg_key in negative_keywords:
                            if neg_key.lower() in item[0].lower():
                                if neg_key == '':
                                    neg_check = False
                                    break
                                else:
                                    neg_check = True
                                    break
                    if check and not neg_check:
                        comparitor(item, start)
            time.sleep(float(CONFIG['DELAY']))
            start = 0
        except Exception as e:
            print(f"Exception found '{e}' - Rotating proxy and user-agent")
            logging.error(e)
            headers = {'User-Agent': user_agent_rotator.get_random_user_agent()}
            # if CONFIG['PROXY'] == "":
            #     proxy = {"http": proxyObject.get()}
            # else:
            #     proxy_no = 0 if proxy_no == (
            #         len(proxy_list) - 1) else proxy_no + 1
            #     proxy = {"http": f"http://{proxy_list[proxy_no]}"}


if __name__ == '__main__':
    urllib3.disable_warnings()
    monitor()
