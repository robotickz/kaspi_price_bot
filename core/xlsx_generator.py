from django.utils import timezone

import xlsxwriter

from .models import BotSetting


def generate_xlsx(integration):
    data = []
    print(f'Start generate xlsx {timezone.now()}')
    bot_settings = BotSetting.objects.filter(
        product_in_integration__integration__pk=integration.pk
    ).prefetch_related(
        'product_in_integration',
        'product_in_integration__product',
        'city'
    ).order_by('product_in_integration__product__kaspi_code')
    for bot_setting in bot_settings:
        if bot_setting.current_price:
            data.append({
                'code': bot_setting.product_in_integration.product.kaspi_code,
                'name': bot_setting.product_in_integration.product.name,
                'sku': bot_setting.product_in_integration.sku,
                'city': bot_setting.city.name,
                'city_id_in_kaspi': bot_setting.city.id_in_kaspi,
                'price': bot_setting.current_price,
                'min_price': bot_setting.min_price if bot_setting.min_price else 0,
                'max_price': bot_setting.max_price if bot_setting.max_price else 0,
                'step': bot_setting.step
            })

    with xlsxwriter.Workbook(f'media/{integration.shop_name}_{integration.partner_id}.xlsx') as workbook:
        cell_format = workbook.add_format()
        cell_format.set_bold()
        cell_format.bg_color = '#eee'

        worksheet = workbook.add_worksheet()
        worksheet.write(0, 0, 'Код товара', cell_format)
        worksheet.write(0, 1, 'Товар', cell_format)
        worksheet.write(0, 2, 'Артикул', cell_format)
        worksheet.write(0, 3, 'Город', cell_format)
        worksheet.write(0, 4, 'Город id в Kaspi', cell_format)
        worksheet.write(0, 5, 'Цена', cell_format)
        worksheet.write(0, 6, 'Мин. цена', cell_format)
        worksheet.write(0, 7, 'Макс. цена', cell_format)
        worksheet.write(0, 8, 'Шаг', cell_format)

        for i, bot in enumerate(data, start=1):

            worksheet.write(i, 0, bot['code'])
            worksheet.write(i, 1, bot['name'])
            worksheet.write(i, 2, bot['sku'])
            worksheet.write(i, 3, bot['city'])
            worksheet.write(i, 4, bot['city_id_in_kaspi'])
            worksheet.write(i, 5, bot['price'])
            worksheet.write(i, 6, bot['min_price'])
            worksheet.write(i, 7, bot['max_price'])
            worksheet.write(i, 8, bot['step'])
    print(f'Stop generate xlsx {timezone.now()}')
