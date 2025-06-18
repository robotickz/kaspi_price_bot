import json
import threading
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .file_operations import (
    get_parsed_products_count,
    save_parsed_products_count
)
from .models import Integration, BotSetting, ProductInIntegration, City, Product, Worker, BotIpAddress
from .parser import (
    get_company_name,
    import_products_from_file
)
from .xlsx_generator import generate_xlsx
from .xml_generator import generate_xml
from account.models import Employee
from .tasks import update_bot_settings, add_data_to_db_from_parser, get_all_products_from_company

PARSED_PRODUCTS = 0


@login_required(login_url='/account/login/')
def index_view(request):
    if not request.user.is_authenticated:
        return redirect('account:login-view')

    workers = Worker.objects.filter(
        timestamp__gt=timezone.now() - timedelta(minutes=15)
    )
    active_workers_count = workers.count() * 2
    products_count = Product.objects.all().count()
    employee_list = Employee.objects.all().exclude(pk=2).order_by('pk')
    context = {
        'active_workers_count': active_workers_count,
        'products_count': products_count,
        'employee_list': employee_list
    }
    return render(request, 'core/index.html', context)


@login_required(login_url='/account/login/')
def staff_view(request):
    return render(request, 'core/staff.html', {})


@login_required(login_url='/account/login/')
def integration_view(request):
    return render(request, 'core/integrations.html', {})


@login_required(login_url='/account/login/')
def integration_add_view(request):
    if request.method == 'POST':
        integration = Integration.objects.create(
            company=request.user.employee.company.all().first(),
            username=request.POST.get('username'),
            password=request.POST.get('password'),
            api_token=request.POST.get('token'),
        )
        shop_name = get_company_name(integration)
        integration.shop_name = shop_name[0]
        integration.partner_id = shop_name[1]
        integration.save()
        get_all_products_from_company(integration.id)
        p = threading.Thread(target=get_all_products_from_company, args=(integration.id,))
        p.start()
        return redirect('core:integration-view')
    return render(request, 'core/add_integration.html', {})


@login_required(login_url='/account/login/')
def integration_update(request, integration_id):
    integration = Integration.objects.get(pk=integration_id)
    interval = request.GET.get("interval", '')
    status = request.GET.get("status", '')
    if interval != '':
        integration.launch_interval = int(interval)
        integration.save()
        return JsonResponse({"success": True})
    elif status != '':
        integration.status = True if status == 'true' else False
        integration.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False})


@login_required(login_url='/account/login/')
def integration_delete(request, integration_id):
    integration = Integration.objects.get(pk=integration_id)
    integration.delete()
    return redirect('core:integration-view')


@login_required(login_url='/account/login/')
def integration_update_products(request, integration_id):
    p = threading.Thread(target=get_all_products_from_company, args=(integration_id,))
    p.start()
    return redirect('core:integration-view')


@login_required(login_url='/account/login/')
def products_view(request, integration_id=0):
    integration = None
    if integration_id == 0:
        try:
            integration = Integration.objects.filter(company=request.user.employee.company.all().first()).first()
        except:
            redirect('core:integration-view')
    else:
        integration = Integration.objects.get(pk=integration_id)
    if not integration:
        return redirect('core:integration-view')
    page_number = request.GET.get("page", 1)
    search_query = request.GET.get("search", '')
    city_query = request.GET.get("city_ids", '')
    brand_query = request.GET.get("brands", '')
    min_price = request.GET.get("min_price", False)
    max_price = request.GET.get("max_price", False)
    not_min_price = request.GET.get("not_min_price", False)
    not_max_price = request.GET.get("not_max_price", False)
    city_ids = []
    brand_list = []
    if city_query:
        city_ids = city_query.split(';')
    if brand_query:
        brand_list = brand_query.split(';')
    if min_price == 'true':
        min_price = True
    if not_min_price == 'true':
        not_min_price = True
    if max_price == 'true':
        max_price = True
    if not_max_price == 'true':
        not_max_price = True
    if brand_list and not city_ids:
        products = ProductInIntegration.objects.prefetch_related(
            'product',
            'bot_settings',
            'bot_settings__city'
        ).filter(
            integration__id=integration.pk,
            bot_settings__active=True,
            product__brand__in=brand_list
        ).distinct().order_by('pk')
    elif brand_list and city_ids:
        products = ProductInIntegration.objects.prefetch_related(
            'product',
            'bot_settings',
            'bot_settings__city'
        ).filter(
            integration__id=integration.pk,
            bot_settings__active=True,
            product__brand__in=brand_list,
            bot_settings__city__id_in_kaspi__in=city_ids
        ).distinct().order_by('pk')
    elif not brand_list and city_ids:
        products = ProductInIntegration.objects.prefetch_related(
            'product',
            'bot_settings',
            'bot_settings__city'
        ).filter(
            integration__id=integration.pk,
            bot_settings__active=True,
            bot_settings__city__id_in_kaspi__in=city_ids
        ).distinct().order_by('pk')
    else:
        products = ProductInIntegration.objects.prefetch_related(
            'product',
            'bot_settings',
            'bot_settings__city'
        ).filter(
            integration__id=integration.pk,
            bot_settings__active=True
        ).distinct().order_by('pk')
    if search_query != '':
        products = products.filter(
            Q(product__name__icontains=search_query) |
            Q(product__brand__icontains=search_query) |
            Q(product__kaspi_code__icontains=search_query) |
            Q(sku__icontains=search_query)
        )

    if min_price and not not_min_price and not max_price and not not_max_price:
        products = products.filter(bot_settings__min_price__gt=0)
    if not min_price and not_min_price and not max_price and not not_max_price:
        products = products.filter(
            Q(bot_settings__min_price=0) | Q(bot_settings__min_price__isnull=True)
        )
    if not min_price and not not_min_price and max_price and not not_max_price:
        products = products.filter(bot_settings__max_price__gt=0)
    if not min_price and not not_min_price and not max_price and not_max_price:
        products = products.filter(Q(bot_settings__max_price=0) | Q(bot_settings__max_price__isnull=True))

    paginator = Paginator(products, 10)

    page_obj = paginator.get_page(page_number)

    published, archived = [0, 0]
    city_list = products.order_by(
        'bot_settings__city__name'
    ).values_list('bot_settings__city__name', 'bot_settings__city__id_in_kaspi').distinct()
    all_brands = ProductInIntegration.objects.order_by('product__brand').values_list('product__brand',
                                                                                     flat=True).distinct()
    context = {
        "integration": integration,
        "products_in_integration": page_obj,
        "published": published,
        "archived": archived,
        "city_ids": city_ids,
        "city_list": city_list,
        "all_brands": all_brands,
        "min_max_price": [min_price, not_min_price, max_price, not_max_price]
    }
    return render(request, 'core/products.html', context)


@login_required(login_url='/account/login/')
def update_product(request, product_id):
    active = request.GET.get("active", '')
    min_price = request.GET.get("min_price", 0)
    max_price = request.GET.get("max_price", 0)
    product = ProductInIntegration.objects.prefetch_related('bot_settings').get(pk=product_id)
    for bot_setting in product.bot_settings.all():
        if active:
            bot_setting.active = True if active == 'true' else False
            bot_setting.save()
        if min_price:
            bot_setting.min_price = int(min_price)
            bot_setting.save()
        if max_price:
            bot_setting.max_price = int(max_price)
            bot_setting.save()
    return JsonResponse({"success": True})


@login_required(login_url='/account/login/')
def update_bot_setting(request, bot_id):
    bot_setting = BotSetting.objects.get(pk=bot_id)
    min_price = request.GET.get("min_price", '')
    max_price = request.GET.get("max_price", '')
    step = request.GET.get("step", '')
    active = request.GET.get("active", '')
    if min_price != '':
        bot_setting.min_price = int(min_price)
        bot_setting.save()
        return JsonResponse({"success": True})
    elif max_price != '':
        bot_setting.max_price = int(max_price)
        bot_setting.save()
        return JsonResponse({"success": True})
    elif step != '':
        bot_setting.step = int(step)
        bot_setting.save()
        return JsonResponse({"success": True})
    elif active != '':
        bot_setting.active = True if active == 'true' else False
        bot_setting.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False})


@login_required(login_url='/account/login/')
def update_all_bot_setting(request):
    integration_id = request.GET.get("id")
    if integration_id:
        bot_settings = BotSetting.objects.filter(product_in_integration__integration__pk=integration_id)
        step = request.GET.get("step", '')
        min_price = request.GET.get("minPrice", '')
        p = threading.Thread(target=update_bot_settings, args=(bot_settings, step, min_price))
        p.start()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False})


@login_required(login_url='/account/login/')
def export_to_file(request, integration_id):
    integration = Integration.objects.get(pk=integration_id)
    generate_xlsx(integration)
    return redirect(f'/media/{integration.shop_name}_{integration.partner_id}.xlsx')


@login_required(login_url='/account/login/')
def import_from_file(request, integration_id):
    integration = Integration.objects.get(pk=integration_id)
    if request.method == 'POST':
        with open(
                f'media/{integration.shop_name}_{integration.partner_id}.xlsx',
                'wb+'
        ) as destination:
            for chunk in request.FILES['file'].chunks():
                destination.write(chunk)
        p = threading.Thread(target=import_products_from_file, args=(integration,))
        p.start()
        return redirect('core:products-view')
    return redirect('core:products-view')


@csrf_exempt
def parse_from_client(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        try:
            worker = Worker.objects.get(pk=int(data.get('worker_id', 0)))
            worker.save()
        except:
            pass
        p = threading.Thread(target=add_data_to_db_from_parser, args=(data,))
        p.start()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False})


def get_products_for_parsing(request):
    global PARSED_PRODUCTS
    worker_id = int(request.GET.get("worker_id", 0))
    if PARSED_PRODUCTS == 0:
        integrations = Integration.objects.all()
        for integration in integrations:
            if integration.status:
                p = threading.Thread(target=generate_xml, args=(integration,))
                p.start()
                integration.last_update = timezone.now()
                integration.save()

    PARSED_PRODUCTS = get_parsed_products_count()

    product_list = []

    products = Product.objects.all()[PARSED_PRODUCTS:PARSED_PRODUCTS + 10]
    for product in products:
        product_list.append({
            'product_url': product.kaspi_url,
            'product_code': product.kaspi_code
        })

    cities = City.objects.all()
    city_list = []
    for city in cities:
        city_list.append(city.id_in_kaspi)

    if products.count() == 10:
        PARSED_PRODUCTS += 10
    else:
        PARSED_PRODUCTS = 0
    save_parsed_products_count(PARSED_PRODUCTS)

    if not Worker.objects.filter(pk=worker_id).exists():
        worker = Worker.objects.create()
        worker_id = worker.pk

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    if ip:
        BotIpAddress.objects.get_or_create(ip=ip)
    return JsonResponse({
        'products': product_list,
        'cities': city_list,
        'worker_id': worker_id
    })


def save_bot_ip_address(request):
    return JsonResponse({'success': False})
