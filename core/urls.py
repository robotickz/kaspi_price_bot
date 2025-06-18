from django.views.generic import TemplateView
from django.urls import path

from . import views


app_name = 'core'
urlpatterns = [
    path("", views.index_view, name="index-view"),
    path("integration/", views.integration_view, name="integration-view"),
    path("integration/add", views.integration_add_view, name="integration-add-view"),
    path("integration/update/<int:integration_id>", views.integration_update, name="integration-update"),
    path("integration/delete/<int:integration_id>", views.integration_delete, name="integration-delete"),
    path(
        "integration/update_products/<int:integration_id>",
        views.integration_update_products,
        name="integration-update-products"
    ),
    path("integration/export/<int:integration_id>", views.export_to_file, name="export_to_file"),
    path("integration/import/<int:integration_id>", views.import_from_file, name="import_from_file"),
    path("product/update/<int:product_id>", views.update_product, name="update-product"),
    path("products/", views.products_view, name="products-view"),
    path("products/<int:integration_id>", views.products_view, name="integration-products-view"),
    path("bot_setting/update/<int:bot_id>", views.update_bot_setting, name="update-bot-setting"),
    path("bot_setting/update-all/", views.update_all_bot_setting, name="update-all-bot-setting"),
    path("staff/", views.staff_view, name="staff-view"),
    path("get_products_for_parsing/", views.get_products_for_parsing, name="get-products-for-parsing"),
    path("parse_from_client/", views.parse_from_client, name="parse-from-client"),
    path("parse_client/", TemplateView.as_view(template_name='core/parser.html'), name="parse-client"),
    path("save_bot_ip_address", views.save_bot_ip_address, name="save-bot-ip-address"),
]
