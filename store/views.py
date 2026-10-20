
import json
from decimal import Decimal
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import Category, Product, CustomerProfile, Cart, CartItem


WHATSAPP_NUMBER = "918297243999"


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _cart_summary(cart):
    result = []
    total = Decimal("0.00")
    count = 0

    items = cart.items.select_related("product", "product__category").all()

    for item in items:
        product = item.product
        line_total = product.price * item.quantity
        total += line_total
        count += item.quantity

        result.append({
            "id": item.id,
            "product_id": product.id,
            "name": product.name,
            "brand": product.brand,
            "slug": product.slug,
            "price": str(product.price),
            "quantity": item.quantity,
            "unit": product.unit,
            "line_total": str(line_total),
            "image": product.image.url if product.image else "",
            "stock_quantity": product.stock_quantity,
        })

    return {
        "items": result,
        "count": count,
        "total": str(total),
    }


def _json_body(request):
    try:
        data = json.loads(request.body or "{}")
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _api_login_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            "ok": False,
            "error": "Please log in to access your cart.",
            "login_url": reverse("store:login"),
        }, status=401)
    return None


# --------------------------------------------------
# Homepage and products
# --------------------------------------------------

def home(request):
    categories = Category.objects.all()
    featured_products = Product.objects.filter(
        is_active=True,
        featured=True,
    ).select_related("category")[:12]

    products = Product.objects.filter(
        is_active=True,
    ).select_related("category")[:12]

    return render(request, "store/home.html", {
        "categories": categories,
        "featured_products": featured_products,
        "products": products,
    })


def product_list(request):
    products = Product.objects.filter(
        is_active=True,
    ).select_related("category")

    query = request.GET.get("q", "").strip()

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(brand__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        )

    return render(request, "store/product_list.html", {
        "products": products,
        "categories": Category.objects.all(),
        "query": query,
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)

    products = Product.objects.filter(
        category=category,
        is_active=True,
    ).select_related("category")

    return render(request, "store/category_detail.html", {
        "category": category,
        "products": products,
    })


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category"),
        slug=slug,
        is_active=True,
    )

    related_products = Product.objects.filter(
        category=product.category,
        is_active=True,
    ).exclude(pk=product.pk)[:4]

    return render(request, "store/product_detail.html", {
        "product": product,
        "related_products": related_products,
    })


# --------------------------------------------------
# Cart
# --------------------------------------------------

def cart_view(request):
    if not request.user.is_authenticated:
        return redirect("store:login")

    cart = _get_cart(request.user)
    summary = _cart_summary(cart)

    return render(request, "store/cart.html", {
        "cart": cart,
        "items": cart.items.select_related("product").all(),
        "cart_items": summary["items"],
        "cart_count": summary["count"],
        "cart_total": summary["total"],
    })


@require_http_methods(["GET", "POST"])
def cart_api(request):
    auth_error = _api_login_required(request)
    if auth_error:
        return auth_error

    cart = _get_cart(request.user)

    if request.method == "GET":
        return JsonResponse({"ok": True, **_cart_summary(cart)})

    data = _json_body(request)
    if data is None:
        return JsonResponse(
            {"ok": False, "error": "Invalid JSON."},
            status=400,
        )

    try:
        product_id = int(data.get("product_id"))
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return JsonResponse(
            {"ok": False, "error": "Invalid product or quantity."},
            status=400,
        )

    action = data.get("action", "add")

    if action not in ("add", "update", "remove"):
        return JsonResponse(
            {"ok": False, "error": "Unknown cart action."},
            status=400,
        )

    if quantity < 1:
        return JsonResponse(
            {"ok": False, "error": "Quantity must be at least 1."},
            status=400,
        )

    product = get_object_or_404(
        Product,
        pk=product_id,
        is_active=True,
    )

    if action == "remove":
        cart.items.filter(product=product).delete()
    else:
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )

        new_quantity = quantity if created or action == "update" else item.quantity + quantity

        if new_quantity > product.stock_quantity:
            if created:
                item.delete()
            return JsonResponse({
                "ok": False,
                "error": f"Only {product.stock_quantity} unit(s) are available.",
            }, status=400)

        if not created:
            item.quantity = new_quantity
            item.save(update_fields=["quantity"])

    cart.updated_at = timezone.now()
    cart.save(update_fields=["updated_at"])

    return JsonResponse({"ok": True, **_cart_summary(cart)})


@require_POST
def cart_api_update(request):
    auth_error = _api_login_required(request)
    if auth_error:
        return auth_error

    data = _json_body(request)
    if data is None:
        return JsonResponse(
            {"ok": False, "error": "Invalid JSON."},
            status=400,
        )

    try:
        item_id = int(data.get("item_id"))
    except (TypeError, ValueError):
        return JsonResponse(
            {"ok": False, "error": "Invalid cart item."},
            status=400,
        )

    cart = _get_cart(request.user)
    item = get_object_or_404(
        CartItem.objects.select_related("product"),
        pk=item_id,
        cart=cart,
    )

    action = data.get("action", "update")

    if action == "remove":
        item.delete()
    elif action == "update":
        try:
            quantity = int(data.get("quantity"))
        except (TypeError, ValueError):
            return JsonResponse(
                {"ok": False, "error": "Invalid quantity."},
                status=400,
            )

        if quantity < 1:
            return JsonResponse(
                {"ok": False, "error": "Quantity must be at least 1."},
                status=400,
            )

        if quantity > item.product.stock_quantity:
            return JsonResponse({
                "ok": False,
                "error": f"Only {item.product.stock_quantity} unit(s) are available.",
            }, status=400)

        item.quantity = quantity
        item.save(update_fields=["quantity"])
    else:
        return JsonResponse(
            {"ok": False, "error": "Unknown cart action."},
            status=400,
        )

    cart.updated_at = timezone.now()
    cart.save(update_fields=["updated_at"])

    return JsonResponse({"ok": True, **_cart_summary(cart)})


# --------------------------------------------------
# Registration
# --------------------------------------------------

@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("store:home")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone_number", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not name or not phone or not password:
            messages.error(request, "Please fill in all required fields.")
        elif not phone.isdigit() or not 10 <= len(phone) <= 15:
            messages.error(request, "Enter a valid phone number using digits only.")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif len(password) < 8:
            messages.error(request, "Password must contain at least 8 characters.")
        elif CustomerProfile.objects.filter(phone_number=phone).exists():
            messages.error(request, "This phone number is already registered.")
        else:
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=phone,
                        password=password,
                        first_name=name[:150],
                    )
                    CustomerProfile.objects.create(
                        user=user,
                        phone_number=phone,
                    )
                    Cart.objects.get_or_create(user=user)

                user = authenticate(
                    request,
                    username=phone,
                    password=password,
                )

                if user is not None:
                    login(request, user)
                    messages.success(request, "Your account has been created.")
                    return redirect("store:home")

                messages.success(request, "Account created. Please log in.")
                return redirect("store:login")

            except IntegrityError:
                messages.error(
                    request,
                    "That phone number is already registered. Please log in.",
                )

    return render(request, "store/register.html")


# --------------------------------------------------
# Login using phone number and password
# --------------------------------------------------

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("store:home")

    if request.method == "POST":
        phone = request.POST.get("phone_number", "").strip()
        password = request.POST.get("password", "")

        # Try the phone number directly as the Django username.
        user = authenticate(
            request,
            username=phone,
            password=password,
        )

        # Also support accounts linked through CustomerProfile.
        if user is None:
            try:
                profile = CustomerProfile.objects.select_related(
                    "user"
                ).get(phone_number=phone)

                user = authenticate(
                    request,
                    username=profile.user.username,
                    password=password,
                )
            except CustomerProfile.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)

            next_url = (
                request.POST.get("next")
                or request.GET.get("next")
            )

            if (
                next_url
                and next_url.startswith("/")
                and not next_url.startswith("//")
            ):
                return redirect(next_url)

            return redirect("store:home")

        messages.error(request, "Incorrect phone number or password.")

    return render(request, "store/login.html")


# --------------------------------------------------
# Logout
# --------------------------------------------------

@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("store:home")


# --------------------------------------------------
# WhatsApp checkout — no online payment
# --------------------------------------------------

@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    cart = _get_cart(request.user)
    summary = _cart_summary(cart)

    if not summary["items"]:
        messages.info(request, "Your cart is empty.")
        return redirect("store:cart")

    try:
        saved_phone = request.user.customer_profile.phone_number
    except CustomerProfile.DoesNotExist:
        saved_phone = ""

    if request.method == "POST":
        customer_name = (
            request.POST.get("customer_name", "").strip()
            or request.user.first_name
            or request.user.username
        )
        customer_phone = (
            request.POST.get("phone_number", "").strip()
            or saved_phone
        )
        address = request.POST.get("address", "").strip()
        notes = request.POST.get("notes", "").strip()

        if not customer_phone:
            messages.error(request, "Please enter your phone number.")
        elif not address:
            messages.error(request, "Please enter your delivery address.")
        else:
            lines = [
                "Vijaya Lakshmi Agro Agencies",
                "Order enquiry / quotation request",
                "",
                f"Customer: {customer_name}",
                f"Phone: {customer_phone}",
                f"Address: {address}",
                "",
                "Items:",
            ]

            for item in summary["items"]:
                lines.append(
                    f"- {item['name']} x {item['quantity']} "
                    f"{item['unit']} = ₹{item['line_total']}"
                )

            lines.extend([
                "",
                f"Estimated total: ₹{summary['total']}",
                "Please confirm availability and final bill.",
            ])

            if notes:
                lines.extend(["", f"Notes: {notes}"])

            lines.extend([
                "",
                "This is a quotation request, not an online payment.",
            ])

            whatsapp_url = (
                f"https://wa.me/{WHATSAPP_NUMBER}"
                f"?text={quote(chr(10).join(lines))}"
            )
            return redirect(whatsapp_url)

    return render(request, "store/checkout.html", {
        "items": summary["items"],
        "cart_items": cart.items.select_related("product").all(),
        "cart_total": summary["total"],
        "cart_count": summary["count"],
        "customer_name": request.user.first_name,
        "phone_number": saved_phone,
    })


# --------------------------------------------------
# Health check
# --------------------------------------------------

@require_GET
def health(request):
    return JsonResponse({
        "status": "ok",
        "service": "Vijaya Lakshmi Agro Agencies",
    })
