import requests
from bs4 import BeautifulSoup
import logging
import dotenv
import datetime
import json
import time
import urllib3
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, HardwareType
from fp.fp import FreeProxy

logging.basicConfig(filename='test.log', filemode='a', format='%(asctime)s - %(name)s - %(message)s',
                    level=logging.DEBUG)

software_names = [SoftwareName.CHROME.value]
hardware_type = [HardwareType.MOBILE__PHONE]
user_agent_rotator = UserAgent(
    software_names=software_names, hardware_type=hardware_type)
CONFIG = dotenv.dotenv_values()

proxyObject = FreeProxy(country_id=[CONFIG['LOCATION']], rand=True)

INSTOCK = []


def scrape_main_site(headers, proxy):
    """
    Scrape the site and adds each item to an array
    :return:
    """
    items = []
    url = 'https://www.snipes.it/c/shoes?prefn1=isNew&prefv1=true&openCategory=true&specificCategory=new&sz=48'
    s = requests.Session()
    html = s.get(url=url, headers=headers,
                 proxies=proxy, verify=False, timeout=15)
    soup = BeautifulSoup(html.text, 'html.parser')
    products = soup.select('div[class="b-product-tile js-product-tile"]')
    for product in products:
        item = [str(product.find('span', {'class': 'b-product-tile-text'}).text).replace("\n", "").capitalize(),
                str(product.find(
                    'span', {'class': 'b-product-tile-link'}).text).replace("\n", "").capitalize(),
                str(product.select_one(
                    'span[class="b-product-tile-price-item"]').text).replace("\n", ""),
                product.select_one(
                    'a[class="b-product-tile-body-link"]')['href'],
                product.find(
                    'img', {'class': "b-dynamic_image_content"})['data-src'],
                ]
        items.append(item)
    print(f'{len(items)} items found!')
    return items


def discord_webhook(product_item):
    """
    Sends a Discord webhook notification to the specified webhook URL
    :param product_item: An array of the product's details
    :return: None
    """
    data = {}
    data["username"] = CONFIG['USERNAME']
    data["avatar_url"] = CONFIG['AVATAR_URL']
    data["embeds"] = []
    embed = {}
    if product_item == 'initial':
        embed["author"] = {'name': "CONNECTED @ SNIPES.IT", 'url': 'https://www.snipes.it/',
                           'icon_url': 'https://imgur.com/DMDTCRp.png'}
        embed["description"] = "This Snipes Monitor has been restarted or redployed by cloud. It should be working fine, don't worry."
    else:
        embed["author"] = {'name': "UPDATE @ SNIPES.IT", 'url': 'https://www.snipes.it/c/new',
                           'icon_url': 'https://imgur.com/DMDTCRp.png'}
        embed["title"] = product_item[0]   # Item
        embed["description"] = f'**Name: **{product_item[1]}\n**Price: **{product_item[2]}'
        embed['url'] = f'https://www.snipes.it{product_item[3]}'  # Item link
        embed['thumbnail'] = {'url': product_item[4]}  # Item Image

    embed["color"] = int(CONFIG['COLOUR'])
    embed["footer"] = {'text': 'Snipes.IT | VU x DropNation',
                       'icon_url': 'https://i.imgur.com/FX7wYR5.png'}
    embed["fields"] = [{'name': 'Quick Links: ', 'value': '[New](https://www.snipes.it/c/new)' + ' | ' + '[Scarpe](https://www.snipes.it/c/shoes)' +
                        ' | ' + '[Soon](https://www.snipes.it/c/soon)', 'inline': True}]
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
    """
    Determines whether the product status has changed
    :param item: list of item details
    :return: Boolean whether the status has changed or not
    """
    for product in INSTOCK:
        if product == item:
            return True
    return False


def remove_duplicates(mylist):
    """
    Removes duplicate values from a list
    :param mylist: list
    :return: list
    """
    return [list(t) for t in set(tuple(element) for element in mylist)]


def comparitor(item, start):
    if not checker(item):
        INSTOCK.append(item)
        if start == 0:
            discord_webhook(item)


def monitor():
    """
    Initiates monitor
    :return:
    """
    print('STARTING MONITOR')
    logging.info(msg='Successfully started monitor')
    discord_webhook('initial')
    start = 1
    proxy_no = 0

    proxy_list = CONFIG['PROXY'].split('%')
    proxy = {"http": proxyObject.get()} if proxy_list[0] == "" else {
        "http": f"http://{proxy_list[proxy_no]}"}
    headers = {'User-Agent': user_agent_rotator.get_random_user_agent()}
    keywords = CONFIG['KEYWORDS'].split('%')
    while True:
        try:
            items = remove_duplicates(scrape_main_site(headers, proxy))
            for item in items:
                check = False
                if keywords == '':
                    comparitor(item, start)
                else:
                    for key in keywords:
                        if key.lower() in item[0].lower():
                            check = True
                            break
                    if check:
                        comparitor(item, start)
            time.sleep(float(CONFIG['DELAY']))
            start = 0
        except Exception as e:
            print(f"Exception found '{e}' - Rotating proxy and user-agent")
            logging.error(e)
            headers = {'User-Agent': user_agent_rotator.get_random_user_agent()}
            if CONFIG['PROXY'] == "":
                proxy = {"http": proxyObject.get()}
            else:
                proxy_no = 0 if proxy_no == (
                    len(proxy_list) - 1) else proxy_no + 1
                proxy = {"http": f"http://{proxy_list[proxy_no]}"}


if __name__ == '__main__':
    urllib3.disable_warnings()
    monitor()
