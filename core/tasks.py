# from django_toosimple_q.decorators import register_task
from django.utils import timezone
import random

from .models import BotSetting, Integration
from .parser import get_all_company_products, get_kaspi_auth_headers, update_product_price


# @register_task()
def update_bot_settings(bot_settings, step, percent):
    if step != '':
        for bot_setting in bot_settings:
            bot_setting.step = int(step)
        BotSetting.objects.bulk_update(bot_settings, ['step'], batch_size=500)
    if percent != '':
        for bot_setting in bot_settings:
            try:
                if bot_setting.current_price:
                    bot_setting.min_price = bot_setting.current_price - (
                            bot_setting.current_price / 100 * int(percent)
                    )
            except:
                pass
        BotSetting.objects.bulk_update(bot_settings, ['min_price'], batch_size=500)
    print('finished')


# @register_task()
def add_data_to_db_from_parser(data):
    for product in data.get('product_list', []):
        try:
            bot_settings = BotSetting.objects.filter(
                product_in_integration__product__kaspi_code=product['kaspi_code']
            ).prefetch_related('product_in_integration__integration')
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                "Content-Type": "application/json; charset = utf-8",
                "Cookie": bot_settings[0].product_in_integration.integration.auth_cookie
            }
            merchant_uid = bot_settings[0].product_in_integration.integration.partner_id
            payload = [
                {
                    "merchantUid": merchant_uid,
                    "sku": bot_settings[0].product_in_integration.sku,
                    "availabilities": [],
                    "model": bot_settings[0].product_in_integration.product.name,
                    "cityPrices": []
                }
            ]
            for city in product['cities']:
                if city['offers']:
                    for bot_setting in bot_settings.filter(city__id_in_kaspi=city['city_id']):
                        # print(bot_setting.pickup_points, bot_setting.product_in_integration.integration.partner_id, bot_setting.product_in_integration.sku)
                        bot_setting.first_place_price = city['offers'][0]['price']
                        if len(city['offers']) > 1:
                            bot_setting.second_place_price = city['offers'][1]['price']
                        else:
                            bot_setting.second_place_price = city['offers'][0]['price']
                        bot_setting.last_place_price = city['offers'][-1]['price']
                        my_offer = next(
                            ((i, offer) for i, offer in enumerate(city['offers']) if
                             offer["shop_name"] == bot_setting.product_in_integration.integration.shop_name),
                            None
                        )
                        if my_offer is not None:
                            bot_setting.current_place_in_city = my_offer[0] + 1
                            bot_setting.current_price = my_offer[1]['price']
                        bot_setting.last_update = timezone.now()
                        bot_setting.last_price_update += random.randint(0, 2)
                        if bot_setting.last_price_update > 15:
                            bot_setting.last_price_update = 0
                        rand_number = bot_setting.last_price_update
                        bot_setting.save()
                        if bot_setting.product_in_integration.is_any_active and bot_setting.min_price > 0:
                            current_price = bot_setting.current_price
                            for pickup_point in bot_setting.pickup_points['points']:
                                available = pickup_point['available']
                                if not bot_setting.active:
                                    available = 'no'
                                payload[0]['availabilities'] += [
                                    {
                                        "available": available,
                                        "storeId": f"{merchant_uid}_{pickup_point['name']}"
                                    }
                                ]
                            try:
                                new_price = bot_setting.current_price if bot_setting.current_price else bot_setting.pickup_points.price
                            except:
                                new_price = 0
                            if bot_setting.first_place_price and bot_setting.second_place_price:
                                new_lowest_price = bot_setting.first_place_price - bot_setting.step
                                new_higher_price = bot_setting.second_place_price - bot_setting.step
                                min_price = bot_setting.min_price or 0
                                max_price = bot_setting.max_price or 0
                                first_place_price = bot_setting.first_place_price
                                second_place_price = bot_setting.second_place_price or bot_setting.last_place_price
                                if bot_setting.current_price:
                                    if bot_setting.current_price > first_place_price or bot_setting.current_price < min_price:
                                        if min_price > 0:
                                            if new_lowest_price >= min_price:
                                                new_price = new_lowest_price
                                            else:
                                                new_price = min_price
                                    elif bot_setting.current_price + bot_setting.step < second_place_price:
                                        if max_price > 0 and min_price > 0:
                                            if min_price <= new_higher_price <= max_price:
                                                new_price = new_higher_price
                                    elif first_place_price == second_place_price:
                                        if my_offer[0] == 1:
                                            if new_lowest_price >= min_price:
                                                new_price = new_lowest_price
                                            else:
                                                new_price = min_price
                                        elif max_price:
                                            new_price = max_price
                                        elif min_price:
                                            new_price = min_price
                            payload[0]['cityPrices'] += [
                                {
                                    "cityId": f"{bot_setting.city.id_in_kaspi}",
                                    "value": new_price
                                }
                            ]
            if new_price != current_price and rand_number == 0:
                integration = Integration.objects.get(pk=bot_settings[0].product_in_integration.integration.id)
                print(payload)
                if integration.status:
                    post_update = update_product_price(headers, payload, integration_id=integration.id)
                    print(f"Success {post_update}")
                    # if post_update.get('status') != 200:
                    #     headers = get_kaspi_auth_headers(integration.id)
                    #     integration.auth_cookie = headers.get("Cookie")
                    #     integration.save()
                    #     headers = {
                    #         "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                    #         "Content-Type": "application/json; charset = utf-8",
                    #         "Cookie": integration.auth_cookie
                    #     }
                    #     post_update = get_data_from_kaspi('https://mc.shop.kaspi.kz/pricefeed/upload/merchant/process/process/batch',
                    #                                   headers,
                    #                                   json=payload
                    #                                   )
                    #     print(f"Success {post_update.get('status') }")
                    # else:
                    #     print(f"Success {post_update.get('status') }")


        except Exception as e:
            pass


# @register_task()
def get_all_products_from_company(integration_id):
    get_all_company_products(integration_id)
