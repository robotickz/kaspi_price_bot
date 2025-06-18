from django.contrib import admin

from .models import (
    BotIpAddress,
    Product,
    ProductInIntegration,
    BotSetting,
    City,
    Integration
)


class ProductInIntegrationAdmin(admin.ModelAdmin):
    list_display = ["product", "integration"]


class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "id_in_kaspi"]
    list_display_links = ["name", "id_in_kaspi"]


class BotSettingAdmin(admin.ModelAdmin):
    list_display = ["product_in_integration", "city", "active"]


admin.site.register(BotIpAddress)
admin.site.register(Product)
admin.site.register(ProductInIntegration, ProductInIntegrationAdmin)
admin.site.register(BotSetting, BotSettingAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Integration)
