
import json
from decimal import Decimal
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .models import Category, Product, CustomerProfile, Cart, CartItem


OWNER_WHATSAPP = "918297243999"


def _categories():
    return Category.objects.all()


def _normalize_phone(phone):
    phone = phone.strip().replace(" ", "").replace("-", "")

    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]

    if (
        len(phone) == 10
        and phone.isdigit()
        and phone[0] in "6789"
    ):
        return phone

    return None


def _get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _cart_data(cart):
    items = []
    total = Decimal("0.00")

    cart_items = cart.items.select_related("product").filter(
        product__is_active=True
    )

    for item in cart_items:
        product = item.product
        line_total = product.price * item.quantity
        total += line_total

        items.append({
            "id": product.id,
            "name": product.name,
            "price": str(product.price),
            "unit": product.unit,
            "quantity": item.quantity,
            "image": product.image.url if product.image else "",
            "line_total": str(line_total),
        })

    return {
        "items": items,
        "total": str(total),
        "count": sum(item["quantity"] for item in items),
    }


def home(request):
    categories = _categories()
    products = (
        Product.objects.filter(is_active=True, featured=True)
        .select_related("category")[:8]
    )

    if not products.exists():
        products = (
            Product.objects.filter(is_active=True)
            .select_related("category")[:8]
        )

    return render(
        request,
        "store/home.html",
        {"categories": categories, "products": products},
    )


def product_list(request):
    products = Product.objects.filter(
        is_active=True
    ).select_related("category")

    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    if query:
        products = products.filter(name__icontains=query) | products.filter(
            brand__icontains=query
        )

    if category:
        products = products.filter(category__category_type=category)

    return render(
        request,
        "store/product_list.html",
        {
            "products": products.distinct(),
            "categories": _categories(),
            "query": query,
            "selected_category": category,
        },
    )


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(is_active=True)

    return render(
        request,
        "store/product_list.html",
        {
            "products": products,
            "categories": _categories(),
            "current_category": category,
            "selected_category": category.category_type,
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product,
        slug=slug,
        is_active=True,
    )
    return render(
        request,
        "store/product_detail.html",
        {"product": product},
    )


@login_required
def cart_view(request):
    return render(request, "store/cart.html")


@login_required
@require_GET
def cart_api(request):
    cart = _get_user_cart(request.user)
    return JsonResponse(_cart_data(cart))


@login_required
@require_POST
def cart_api_update(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid request."}, status=400)

    action = data.get("action")
    cart = _get_user_cart(request.user)

    try:
        product_id = int(data.get("id", 0))
    except (TypeError, ValueError):
        product_id = 0

    if action == "clear":
        cart.items.all().delete()
        return JsonResponse(_cart_data(cart))

    if action not in ("add", "update", "remove"):
        return JsonResponse({"error": "Unknown cart action."}, status=400)

    product = Product.objects.filter(
        pk=product_id,
        is_active=True,
    ).first()

    if product is None:
        return JsonResponse({"error": "Product not found."}, status=404)

    item = cart.items.filter(product=product).first()

    if action == "remove":
        if item:
            item.delete()
        return JsonResponse(_cart_data(cart))

    try:
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid quantity."}, status=400)

    if quantity < 1 or quantity > 999:
        return JsonResponse(
            {"error": "Quantity must be between 1 and 999."},
            status=400,
        )

    if action == "add":
        if item:
            item.quantity = min(999, item.quantity + quantity)
            item.save(update_fields=["quantity"])
        else:
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
            )
    else:
        if item:
            item.quantity = quantity
            item.save(update_fields=["quantity"])
        else:
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
            )

    return JsonResponse(_cart_data(cart))


def register_view(request):
    if request.user.is_authenticated:
        return redirect("store:home")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()[:150]
        phone = _normalize_phone(request.POST.get("phone", ""))
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not name:
            messages.error(request, "Please enter your name.")
        elif not phone:
            messages.error(
                request,
                "Enter a valid 10-digit Indian mobile number.",
            )
        elif len(password) < 8:
            messages.error(
                request,
                "Password must contain at least 8 characters.",
            )
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif CustomerProfile.objects.filter(phone_number=phone).exists():
            messages.error(
                request,
                "This phone number is already registered.",
            )
        else:
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=f"phone_{phone}",
                        password=password,
                        first_name=name,
                    )
                    CustomerProfile.objects.create(
                        user=user,
                        phone_number=phone,
                    )
                    Cart.objects.create(user=user)

                login(request, user)
                messages.success(request, "Your account has been created.")
                return redirect("store:home")

            except Exception:
                messages.error(
                    request,
                    "We couldn't create your account. Please try again.",
                )

    return render(request, "store/register.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("store:home")

    if request.method == "POST":
        phone = _normalize_phone(request.POST.get("phone", ""))
        password = request.POST.get("password", "")

        user = None
        if phone:
            user = authenticate(
                request,
                username=f"phone_{phone}",
                password=password,
            )

        if user is not None:
            login(request, user)
            _get_user_cart(user)
            messages.success(request, "You are now logged in.")
            return redirect("store:home")

        messages.error(request, "Invalid phone number or password.")

    return render(request, "store/login.html")


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("store:home")


@login_required
def checkout(request):
    if request.method != "POST":
        return render(request, "store/checkout.html")

    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid checkout details."}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid checkout details."}, status=400)

    customer = data.get("customer", {})
    if not isinstance(customer, dict):
        return JsonResponse({"error": "Invalid customer details."}, status=400)

    name = str(customer.get("name", "")).strip()[:100]
    phone = str(customer.get("phone", "")).strip()[:30]
    address = str(customer.get("address", "")).strip()[:500]

    if not name or not phone or not address:
        return JsonResponse(
            {"error": "Please enter your name, phone and delivery address."},
            status=400,
        )

    cart = _get_user_cart(request.user)
    cart_items = list(
        cart.items.select_related("product").filter(
            product__is_active=True
        )
    )

    if not cart_items:
        return JsonResponse({"error": "Your cart is empty."}, status=400)

    lines = [
        "*New order enquiry — Vijaya Lakshmi Agro Agencies*",
        "",
        f"Customer: {name}",
        f"Phone: {phone}",
        f"Delivery address: {address}",
        "",
        "*Items*",
    ]

    total = Decimal("0.00")

    for item in cart_items:
        product = item.product
        line_total = product.price * item.quantity
        total += line_total
        lines.append(
            f"- {product.name} x {item.quantity} {product.unit} "
            f"— ₹{line_total:.2f}"
        )

    lines.extend([
        "",
        f"*Estimated subtotal: ₹{total:.2f}*",
        "Delivery charges and final availability to be confirmed by the shop.",
        "Payment to be arranged directly with the shop.",
    ])

    whatsapp_url = (
        f"https://wa.me/{OWNER_WHATSAPP}?text={quote(chr(10).join(lines))}"
    )

    return JsonResponse({"whatsapp_url": whatsapp_url})


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
