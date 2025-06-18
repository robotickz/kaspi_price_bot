import json


def save_parsed_products_count(parsed_products_count):
    with open('parser.json', "w", encoding='utf-8') as jf:
        json.dump(parsed_products_count, jf, ensure_ascii=False)
        jf.close()


def get_parsed_products_count():
    try:
        with open('parser.json', encoding='utf-8') as jf:
            count = json.load(jf)
            jf.close()
    except:
        count = 0
    return count
