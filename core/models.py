from django.db import models


class Integration(models.Model):
    company = models.ForeignKey(
        'account.Company',
        on_delete=models.CASCADE,
        related_name='integrations'
    )
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    api_token = models.CharField(max_length=500)
    partner_id = models.CharField(max_length=100, null=True)
    shop_name = models.CharField(max_length=100)
    launch_interval = models.IntegerField(default=20)
    status = models.BooleanField(default=False)
    last_update = models.DateTimeField(auto_now=True)
    is_xml_link_set = models.BooleanField(default=False)
    in_parsing_process = models.BooleanField(default=False)
    parsing_progress = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    admin_enabled = models.BooleanField(default=True)
    auth_cookie = models.CharField(max_length=500, null=True)

    def disable_all_bot_settings(self):
        for product_in_integration in self.products_in_integration.prefetch_related('bot_settings').all():
            bot_settings = product_in_integration.bot_settings.all()
            for bot_setting in bot_settings:
                bot_setting.active = False
            BotSetting.objects.bulk_update(bot_settings, ['active'], batch_size=500)

    def __str__(self):
        return self.shop_name


class Product(models.Model):
    name = models.CharField(max_length=250, null=True, blank=True)
    last_category = models.CharField(max_length=250, null=True)
    brand = models.CharField(max_length=250, null=True)
    kaspi_code = models.CharField(max_length=250)
    kaspi_url = models.URLField(null=True)
    image_url = models.URLField(null=True)

    def __str__(self):
        return str(self.name)


class City(models.Model):
    name = models.CharField(max_length=100)
    id_in_kaspi = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class PickupPoint(models.Model):
    name = models.CharField(max_length=50)
    available = models.BooleanField(default=False)
    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        related_name='pickup_points'
    )
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)


class ProductInIntegration(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    integration = models.ForeignKey(
        Integration,
        models.CASCADE,
        related_name='products_in_integration'
    )
    sku = models.CharField(max_length=250, null=True)

    def __str__(self):
        return str(self.product.name)

    @property
    def is_current_price_exist(self):
        for bot_setting in self.bot_settings.all():
            if bot_setting.current_price:
                return True

        return False

    @property
    def is_any_active(self):
        for bot_setting in self.bot_settings.all():
            if bot_setting.active:
                return True

        return False


class BotSetting(models.Model):
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)
    product_in_integration = models.ForeignKey(
        ProductInIntegration,
        on_delete=models.CASCADE,
        related_name='bot_settings'
    )
    current_place_in_city = models.IntegerField(null=True)
    first_place_price = models.IntegerField(null=True)
    second_place_price = models.IntegerField(null=True)
    last_place_price = models.IntegerField(null=True)
    current_price = models.IntegerField(null=True)
    min_price = models.IntegerField(null=True)
    max_price = models.IntegerField(null=True)
    step = models.IntegerField(default=1)
    active = models.BooleanField(default=False)
    last_update = models.DateTimeField(null=True)
    pickup_points = models.JSONField(null=True)
    last_price_update = models.IntegerField(null=True)

    def __str__(self):
        return f'{self.product_in_integration.product.name} in {self.city.name}'

    class Meta:
        ordering = ['city__name', 'active']


class Worker(models.Model):
    timestamp = models.DateTimeField(auto_now=True)


class BotIpAddress(models.Model):
    ip = models.CharField(max_length=100)

    def __str__(self):
        return str(self.ip)
