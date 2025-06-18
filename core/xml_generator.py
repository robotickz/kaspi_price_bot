import os

import xml.etree.cElementTree as ET

# from .parser import set_xml_in_kaspi_cabinet


def generate_xml(integration):
    if os.path.isfile(f"media/{integration.shop_name}_{integration.partner_id}.xml"):
        print(f"File {integration.shop_name}_{integration.partner_id}.xml deleted")
        os.remove(f"media/{integration.shop_name}_{integration.partner_id}.xml")
    ET.register_namespace('', "kaspiShopping")
    tree = ET.parse('template.xml')
    root = tree.getroot()
    root.find('{kaspiShopping}company').text = integration.shop_name
    root.find('{kaspiShopping}merchantid').text = integration.partner_id
    offers = root.find('{kaspiShopping}offers')
    for product_in_integration in integration.products_in_integration.prefetch_related(
            'product'
    ).all():
        if product_in_integration.is_any_active:
            offer = ET.SubElement(offers, "{kaspiShopping}offer", sku=product_in_integration.sku)
            ET.SubElement(offer, "{kaspiShopping}model").text = product_in_integration.product.name
            ET.SubElement(offer, "{kaspiShopping}brand")
            availabilities = ET.SubElement(offer, "{kaspiShopping}availabilities")

            cityprices = ET.SubElement(offer, "{kaspiShopping}cityprices")
            for bot_setting in product_in_integration.bot_settings.prefetch_related('city'):
                for pickup_point in bot_setting.pickup_points['points']:
                    available = pickup_point['available']
                    if not bot_setting.active:
                        available = 'no'
                    ET.SubElement(
                        availabilities,
                        "{kaspiShopping}availability",
                        available=available,
                        storeId=pickup_point['name']
                    )
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
                            if max_price:
                                new_price = max_price
                            elif min_price:
                                new_price = min_price

                ET.SubElement(
                    cityprices,
                    "{kaspiShopping}cityprice",
                    cityId=f"{bot_setting.city.id_in_kaspi}"
                ).text = str(new_price)

    ET.indent(tree, space="\t", level=0)
    tree.write(
        f"media/{integration.shop_name}_{integration.partner_id}.xml",
        xml_declaration=True, encoding='utf-8',
        default_namespace=None
    )

    # if not integration.is_xml_link_set:
    #     set_xml_in_kaspi_cabinet(
    #         integration.username,
    #         integration.password,
    #         integration.shop_name,
    #         integration.partner_id
    #     )
    #     integration.is_xml_link_set = True
    #     integration.save()
