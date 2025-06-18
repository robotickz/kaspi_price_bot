import json
from urllib import parse

import pandas as pd
import requests
import time
# from playwright.sync_api import sync_playwright

from django.conf import settings

from .models import Product, City, BotSetting, PickupPoint, Integration, ProductInIntegration, BotIpAddress


def strip_text(text: str) -> str:
    rules = [
        ('\n', ''),
        ('\t', ''),
        ('\xa0', ' '),
    ]
    for old, new in rules:
        text = text.replace(old, new)

    return text


def get_kaspi_auth_headers(integration_id):
    integration = Integration.objects.get(pk=integration_id)
    headers = {'User-Agent': 'Mozilla/5.0'}
    payload = {'username': integration.username, 'password': integration.password}
    post_auth = requests.post('https://kaspi.kz/mc/api/login', headers=headers, data=payload)
    auth_cookies = ''
    for key, value in post_auth.cookies.get_dict().items():
        auth_cookies += f"{key}={value}; "
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Cookie": auth_cookies
    }
    return headers

def update_product_price(headers, payload, integration_id):
    # post_update = requests.post('https://mc.shop.kaspi.kz/pricefeed/upload/merchant/process/process/batch',
    #                             headers=headers,
    #                             json=payload)
    try:
        for _ in range(5):
            response = requests.post(
                f'https://mc.shop.kaspi.kz/pricefeed/upload/merchant/process/process/batch',
                headers=headers,
                json=payload
            )
            print(f"Status {response.status_code }")
            if response.status_code != 200:
                time.sleep(10)
                integration = Integration.objects.get(pk=integration_id)
                headers = get_kaspi_auth_headers(integration_id)
                integration.auth_cookie = headers.get("Cookie")
                print(integration.auth_cookie)
                integration.save()
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                    "Content-Type": "application/json; charset = utf-8",
                    "Cookie": integration.auth_cookie
                }
                response = requests.post(
                    f'https://mc.shop.kaspi.kz/pricefeed/upload/merchant/process/process/batch',
                    headers=headers,
                    json=payload
                )
            if response.status_code == 200:
                return response.status_code
            continue
    except:
        pass
    return {}

# def get_company_name(integration) -> list:
#     headers = get_kaspi_auth_headers(integration.id)
#     integration.auth_cookie = headers.get('Cookie')
#     integration.save()
#     print(headers)
#     company_info_request = requests.get(
#         'https://mc.shop.kaspi.kz/s/m',
#         headers=headers
#     )
#     print(dict(company_info_request))
#     company_info_request = company_info_request.json()
#     uid = company_info_request['merchants'][0]['uid']
#     print(uid)
#     company_settings_request = requests.get(
#         f'https://kaspi.kz/merchantcabinet/api/merchant/settings?_m={uid}',
#         headers=headers
#     ).json()
#     return [company_settings_request['name'], company_settings_request['hybrisUid']]


def get_data_from_kaspi(url, headers, json=None, data=None):
    try:
        for _ in range(5):
            response = requests.post(
                f'http://nc.robotic.kz:5000/parse_data_from_kaspi',
                data=json.dumps({'url': url, 'headers': headers.get('Cookie'), 'data': data, 'json': json}),
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            continue
    except:
        pass
    return {}

def get_company_name(integration) -> list:
    headers = get_kaspi_auth_headers(integration.id)
    integration.auth_cookie = headers.get('Cookie')
    integration.save()
    print(headers)
    company_info_request = get_data_from_kaspi(
        'https://mc.shop.kaspi.kz/s/m',
        headers=headers
    )
    print(company_info_request)
    # company_info_request = company_info_request.json()
    uid = company_info_request['merchants'][0]['uid']
    print(uid)
    company_settings_request = requests.get(
        f'https://kaspi.kz/merchantcabinet/api/merchant/settings?_m={uid}',
        headers=headers
    ).json()
    return [company_settings_request['name'], company_settings_request['hybrisUid']]


def add_or_update_product(integration, product, headers):
    if not product.get('sku'):
        print("Product sku is none")
        return
    product_request = get_data_from_kaspi(
        f"https://mc.shop.kaspi.kz/bff/offer-view/details?m={integration.partner_id}&s={parse.quote_plus(product.get('sku'))}",
        headers
    )
    if not product_request:
        print(f"Product request error with sku: {product.get('sku')}")
        return
    if not product_request.get('masterSku', ''):
        print("Product masterSku is none")
        return
    new_product, created = Product.objects.get_or_create(
        kaspi_code=product_request.get('masterSku')
    )
    new_product.name = product_request.get('title', '')
    new_product.brand = product_request.get('masterProduct', {}).get('card', {}).get('promoConditions', {}).get('brand')
    if product_request.get('masterProduct', {}).get('galleryImages', []):
        new_product.image_url = product_request.get('masterProduct', {}).get('galleryImages', [])[0].get('small')
    new_product.kaspi_url = product_request.get('masterProduct', {}).get('card', {}).get('shopLink')
    new_product.save()

    try:
        new_product_in_integration, created = ProductInIntegration.objects.get_or_create(
            product=new_product,
            integration=integration,
            sku=product_request.get('sku')
        )
    except:
        return

    city_list = City.objects.all()
    bot_setting_list = BotSetting.objects.filter(
        product_in_integration__integration=integration,
        product_in_integration=new_product_in_integration
    )
    for city in product_request.get('cityInfo', []):
        if not city.get('id', False):
            continue
        if city_list.filter(id_in_kaspi=city.get('id')).exists():
            new_city = city_list.get(id_in_kaspi=city.get('id'))
            if not new_city.name:
                new_city.name = city.get('name', '')
                new_city.save()
        else:
            new_city = City.objects.create(
                id_in_kaspi=city.get('id'),
                name=city.get('name', '')
            )

        if bot_setting_list.filter(
                city=new_city,
                product_in_integration=new_product_in_integration
        ).exists():
            new_bot_setting = bot_setting_list.get(
                city=new_city,
                product_in_integration=new_product_in_integration
            )
        else:
            new_bot_setting = BotSetting.objects.create(
                city=new_city,
                product_in_integration=new_product_in_integration
            )
        if city.get('price'):
            new_bot_setting.current_price = city.get('price')

        pickup_points = {'points': []}
        for pickup_point in city.get('pickupPoints', []):
            if pickup_point.get('available'):
                pickup_points['available'] = True
            if city.get('price'):
                pickup_points['price'] = city.get('price')
            pickup_points['points'].append({
                'name': pickup_point.get('displayName'),
                'available': 'yes' if pickup_point.get('available') else 'no'
            })
        if pickup_points.get('available', False):
            new_bot_setting.active = True
            if not new_product.name:
                referer = new_product.kaspi_url if 'kaspi.kz' in new_product.kaspi_url \
                    else f"https://kaspi.kz/shop{new_product.kaspi_url}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                    "Content-Type": "application/json",
                    "Referer": f"{referer}"
                }
                data = {
                    "cityId": f"{new_city.id_in_kaspi}",
                    "referer": referer
                }
                try:
                    shop_product_request = get_data_from_kaspi(
                        f'https://kaspi.kz/yml/offer-view/offers/{new_product.kaspi_code}',
                        headers=headers,
                        data=data
                    )
                    for offer in shop_product_request.get('offers', []):
                        if offer.get('merchantId', 0) == integration.partner_id:
                            new_product.name = offer.get('title', '-NoName-')
                            new_product.save()
                except:
                    pass

        else:
            new_bot_setting.active = False
        new_bot_setting.pickup_points = pickup_points
        new_bot_setting.save()


def get_all_company_products(integration_id):
    print("Start parsing all products")
    integration = Integration.objects.get(pk=integration_id)
    headers = get_kaspi_auth_headers(integration_id)
    integration.auth_cookie = headers.get('Cookie')
    print("Headers gained")
    print(integration.partner_id)
    product_count_request = get_data_from_kaspi(
        f'https://mc.shop.kaspi.kz/bff/offer-view/list?m={integration.partner_id}&p=0&l=1&a=true',
        headers
    )
    print(product_count_request.get('total', 0))
    if product_count_request:
        print('Start parsing products')
        active_products_amount = product_count_request.get('total', 0)
        if active_products_amount:
            integration.disable_all_bot_settings()
        integration.in_parsing_process = True
        integration.save()
        print("Parsing process set")
        current_parsed = 0
        while current_parsed < active_products_amount:
            print(f'Currently parsed - {current_parsed}')
            products_request = get_data_from_kaspi(
                f'https://mc.shop.kaspi.kz/bff/offer-view/list?m={integration.partner_id}&p={int(current_parsed / 100)}&l=100&a=true',
                headers
            )
            integration.parsing_progress = current_parsed
            integration.save()
            current_parsed += 100

            for product in products_request.get('data', []):
                add_or_update_product(integration, product, headers)
        integration.in_parsing_process = False
        integration.save()


def import_products_from_file(integration):
    df = pd.read_excel(
        str(settings.BASE_DIR) + f'/media/{integration.shop_name}_{integration.partner_id}.xlsx'
    )
    data = df.to_dict(orient='split')["data"]
    bot_settings = BotSetting.objects.filter(product_in_integration__integration=integration)
    for prod in data:
        try:
            bot_setting = bot_settings.get(
                city__id_in_kaspi=prod[4],
                product_in_integration__product__kaspi_code=prod[0]
            )

            bot_setting.current_price = prod[5]
            bot_setting.min_price = prod[6]
            bot_setting.max_price = prod[7]
            bot_setting.save()
        except:
            print(f'{prod[0]} - not found')

    print('End import')


# def set_xml_in_kaspi_cabinet(username, password, shop_name, partner_id):
#     with sync_playwright() as pw:
#         browser = pw.chromium.launch(headless=True)
#         context = browser.new_context()
#         page = context.new_page()
#         page.goto("https://kaspi.kz/mc/#/login", wait_until="networkidle")
#         page.locator("a").filter(has_text="Email").click()
#         page.get_by_placeholder("Email").click()
#         page.get_by_placeholder("Email").fill(username)
#         page.get_by_role("button", name="Продолжить").click()
#         page.get_by_placeholder("Пароль").click()
#         page.get_by_placeholder("Пароль").fill(password)
#         page.get_by_role("button", name="Войти").click()
#         page.wait_for_timeout(7000)
#         page.get_by_role("link", name="download Загрузить прайс-лист").click()
#         page.locator("a").filter(has_text="Автоматическая загрузка").click()
#         page.wait_for_timeout(1000)
#         page.get_by_role("textbox").first.click()
#         page.get_by_role("textbox").first.fill(
#             f"http://185.111.106.217/media/{shop_name}_{partner_id}.xml"
#         )
#         page.get_by_role("button", name="Проверить").click()
#         page.wait_for_timeout(3000)
#         page.get_by_role("button", name="OK").click()
#         page.get_by_role("button", name="Сохранить").click()
#         context.close()
#         browser.close()
