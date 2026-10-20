
from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path(
        "category/<slug:slug>/",
        views.category_detail,
        name="category",
    ),
    path(
        "product/<slug:slug>/",
        views.product_detail,
        name="product_detail",
    ),
    path("cart/", views.cart_view, name="cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("health/", views.health, name="health"),

    # Customer accounts
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Customer-specific cart API
    path("api/cart/", views.cart_api, name="cart_api"),
    path("api/cart/update/", views.cart_api_update, name="cart_api_update"),
]
