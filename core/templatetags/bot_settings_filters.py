from django import template
from django.db.models import Q

register = template.Library()


@register.filter(name='by_city')
def by_city(value, city_id):
    if city_id:
        return value.filter(city__id_in_kaspi__in=city_id)
    else:
        return value


@register.filter(name='by_min_max_price')
def by_min_max_price(value, min_max_price):
    if min_max_price[0] and not min_max_price[1] and not min_max_price[2] and not min_max_price[3]:
        return value.exclude(Q(min_price=0) | Q(min_price=None))
    if not min_max_price[0] and min_max_price[1] and not min_max_price[2] and not min_max_price[3]:
        return value.exclude(min_price__gt=0)
    if not min_max_price[0] and not min_max_price[1] and min_max_price[2] and not min_max_price[3]:
        return value.exclude(Q(max_price=0) | Q(max_price=None))
    if not min_max_price[0] and not min_max_price[1] and not min_max_price[2] and min_max_price[3]:
        return value.exclude(max_price__gt=0)
    return value
