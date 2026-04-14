from django.urls import path
from .views import ProductListView, UserDetailView, RegisterView, block_or_restore_vendor, clear_cart, create_order, customer_dashboard, get_categories, get_saved_products, update_cart_item_quantity, view_cart, add_to_cart, view_orders
from .views import get_all_customers, block_or_restore_customer, get_all_vendors, block_or_restore_vendor, create_product, get_vendor_products


urlpatterns = [
    path('products/', ProductListView.as_view(), name='product-list'),
    path('user/me/', UserDetailView.as_view(), name='user-detail'),
    path("register/", RegisterView.as_view(), name="register"),
    path("customers/", get_all_customers, name="get_all_customers"),
    path("customers/<int:user_id>/block_restore/", block_or_restore_customer, name="block_or_restore_customer"),
    path("vendors/", get_all_vendors, name="get_all_vendors"),
    path("vendors/<int:user_id>/block_restore/", block_or_restore_vendor, name="block_or_restore_vendor"),
    path("products/create/", create_product, name="create_product"),
    path("products/vendor/", get_vendor_products, name="get_vendor_products"),
    path("categories/", get_categories, name="get_categories"),
    path("cart/add/", add_to_cart, name="add_to_cart"),
    path("cart/", view_cart, name="view_cart"),
    path("cart/update/", update_cart_item_quantity, name="update_cart_item_quantity"),
    path('api/products/', ProductListView.as_view(), name='product-list'),
    path("saved-products/", get_saved_products, name="get_saved_products"),
    path("cart/clear/", clear_cart, name="clear_cart"),
    path("orders/", create_order, name="create_order"),
    path("orders/view/", view_orders, name="view_orders"),
    path("dashboard/", customer_dashboard, name="customer_dashboard"),
]