
import json
from decimal import Decimal
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import Category, Product, CustomerProfile, Cart, CartItem

WHATSAPP_NUMBER = "918297243999"


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _cart_summary(cart):
    items = []
    total = Decimal("0.00")
    count = 0

    for item in cart.items.select_related("product", "product__category").all():
        product = item.product
        line_total = product.price * item.quantity
        total += line_total
        count += item.quantity

        try:
            image_url = product.image.url if product.image else ""
        except (ValueError, OSError):
            image_url = ""

        items.append({
            "id": item.id,
            "item_id": item.id,
            "product_id": product.id,
            "name": product.name,
            "brand": product.brand,
            "slug": product.slug,
            "price": str(product.price),
            "quantity": item.quantity,
            "unit": product.unit,
            "line_total": str(line_total),
            "image": image_url,
            "image_url": image_url,
            "stock_quantity": product.stock_quantity,
        })

    return {"items": items, "count": count, "total": str(total)}


def _read_json(request):
    try:
        data = json.loads(request.body or "{}")
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _auth_error(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            "ok": False,
            "error": "Please log in to access your cart.",
        }, status=401)
    return None


def _cart_response(cart):
    return JsonResponse({"ok": True, **_cart_summary(cart)})


def home(request):
    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True).select_related("category")[:12]
    return render(request, "store/home.html", {
        "categories": categories,
        "products": products,
        "featured_products": products,
    })


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related("category")
    query = request.GET.get("q", "").strip()
    category_filter = request.GET.get("category", "").strip()

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(brand__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        )

    if category_filter:
        products = products.filter(category__category_type=category_filter)

    return render(request, "store/product_list.html", {
        "products": products,
        "categories": Category.objects.all(),
        "query": query,
        "selected_category": category_filter,
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(
        category=category, is_active=True
    ).select_related("category")
    return render(request, "store/category_detail.html", {
        "category": category, "products": products
    })


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category"),
        slug=slug,
        is_active=True,
    )
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(pk=product.pk)[:4]
    return render(request, "store/product_detail.html", {
        "product": product, "related_products": related_products
    })


@login_required
def cart_view(request):
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
    auth_error = _auth_error(request)
    if auth_error:
        return auth_error

    cart = _get_cart(request.user)

    if request.method == "GET":
        return _cart_response(cart)

    data = _read_json(request)
    if data is None:
        return JsonResponse({"ok": False, "error": "Invalid JSON."}, status=400)

    try:
        product_id = int(data.get("product_id"))
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return JsonResponse({
            "ok": False, "error": "Invalid product or quantity."
        }, status=400)

    action = data.get("action", "add")
    if action not in ("add", "update", "remove"):
        return JsonResponse({"ok": False, "error": "Invalid cart action."}, status=400)

    product = Product.objects.filter(pk=product_id, is_active=True).first()
    if not product:
        return JsonResponse({"ok": False, "error": "Product unavailable."}, status=404)

    cart_item = cart.items.filter(product=product).first()

    if action == "remove":
        if cart_item:
            cart_item.delete()
    else:
        if quantity < 1:
            return JsonResponse({"ok": False, "error": "Quantity must be at least 1."}, status=400)

        new_quantity = (
            cart_item.quantity + quantity
            if action == "add" and cart_item
            else quantity
        )

        if new_quantity > product.stock_quantity:
            return JsonResponse({
                "ok": False,
                "error": f"Only {product.stock_quantity} unit(s) are available."
            }, status=400)

        if cart_item:
            cart_item.quantity = new_quantity
            cart_item.save(update_fields=["quantity"])
        else:
            CartItem.objects.create(cart=cart, product=product, quantity=new_quantity)

    cart.updated_at = timezone.now()
    cart.save(update_fields=["updated_at"])
    return _cart_response(cart)


@require_POST
def cart_api_update(request):
    auth_error = _auth_error(request)
    if auth_error:
        return auth_error

    data = _read_json(request)
    if data is None:
        return JsonResponse({"ok": False, "error": "Invalid JSON."}, status=400)

    cart = _get_cart(request.user)
    try:
        item = None
        if data.get("item_id") not in (None, ""):
            item = cart.items.select_related("product").filter(
                pk=int(data["item_id"])
            ).first()
        if item is None and data.get("product_id") not in (None, ""):
            item = cart.items.select_related("product").filter(
                product_id=int(data["product_id"])
            ).first()
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Invalid item ID."}, status=400)

    if not item:
        return JsonResponse({"ok": False, "error": "Cart item not found."}, status=404)

    action = data.get("action", "update")
    if action == "remove":
        item.delete()
    elif action == "update":
        try:
            quantity = int(data.get("quantity"))
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "Invalid quantity."}, status=400)

        if quantity < 1:
            return JsonResponse({"ok": False, "error": "Quantity must be at least 1."}, status=400)
        if quantity > item.product.stock_quantity:
            return JsonResponse({
                "ok": False,
                "error": f"Only {item.product.stock_quantity} unit(s) are available."
            }, status=400)

        item.quantity = quantity
        item.save(update_fields=["quantity"])
    else:
        return JsonResponse({"ok": False, "error": "Invalid cart action."}, status=400)

    cart.updated_at = timezone.now()
    cart.save(update_fields=["updated_at"])
    return _cart_response(cart)


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("store:home")

    if request.method == "POST":
        name = (
            request.POST.get("name", "").strip()
            or request.POST.get("full_name", "").strip()
            or request.POST.get("customer_name", "").strip()
        )
        phone = (
            request.POST.get("phone_number", "").strip()
            or request.POST.get("phone", "").strip()
            or request.POST.get("mobile_number", "").strip()
        )
        password = request.POST.get("password", "") or request.POST.get("password1", "")
        confirm = (
            request.POST.get("confirm_password", "")
            or request.POST.get("password2", "")
            or request.POST.get("confirm_password1", "")
        )

        if not name or not phone or not password or not confirm:
            messages.error(request, "Please fill in all required fields.")
        elif not phone.isdigit() or not 10 <= len(phone) <= 15:
            messages.error(request, "Enter a valid mobile number using digits only.")
        elif password != confirm:
            messages.error(request, "Passwords do not match.")
        elif len(password) < 8:
            messages.error(request, "Password must contain at least 8 characters.")
        elif User.objects.filter(username=phone).exists() or CustomerProfile.objects.filter(phone_number=phone).exists():
            messages.error(request, "This mobile number is already registered. Please log in.")
        else:
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=phone, password=password, first_name=name[:150]
                    )
                    CustomerProfile.objects.create(user=user, phone_number=phone)
                    Cart.objects.get_or_create(user=user)

                user = authenticate(request, username=phone, password=password)
                if user:
                    login(request, user)
                    messages.success(request, "Your account has been created successfully!")
                    return redirect("store:home")
                return redirect("store:login")
            except IntegrityError:
                messages.error(request, "This mobile number is already registered.")

    return render(request, "store/register.html")


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("store:home")

    if request.method == "POST":
        phone = (
            request.POST.get("phone_number", "").strip()
            or request.POST.get("phone", "").strip()
            or request.POST.get("mobile_number", "").strip()
        )
        password = request.POST.get("password", "")
        user = authenticate(request, username=phone, password=password) if phone and password else None

        if user is None and phone and password:
            try:
                profile = CustomerProfile.objects.select_related("user").get(phone_number=phone)
                user = authenticate(request, username=profile.user.username, password=password)
            except CustomerProfile.DoesNotExist:
                user = None

        if user:
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect("store:home")

        messages.error(request, "Incorrect phone number or password.")

    return render(request, "store/login.html")


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("store:home")


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
        name = request.POST.get("customer_name", "").strip() or request.user.first_name or request.user.username
        phone = request.POST.get("phone_number", "").strip() or saved_phone
        address = request.POST.get("address", "").strip()
        notes = request.POST.get("notes", "").strip()

        if not phone or not address:
            messages.error(request, "Please provide your phone number and delivery address.")
        else:
            lines = [
                "Vijaya Lakshmi Agro Agencies",
                "Order enquiry / quotation request",
                "",
                f"Customer: {name}",
                f"Phone: {phone}",
                f"Address: {address}",
                "",
                "Items:",
            ]
            for item in summary["items"]:
                lines.append(
                    f"- {item['name']} x {item['quantity']} {item['unit']} = ₹{item['line_total']}"
                )
            lines.extend([
                "",
                f"Estimated total: ₹{summary['total']}",
                "Please confirm availability and final bill.",
            ])
            if notes:
                lines.extend(["", f"Notes: {notes}"])
            lines.extend(["", "This is an enquiry; no online payment has been taken."])

            return redirect(
                f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(chr(10).join(lines))}"
            )

    return render(request, "store/checkout.html", {
        "items": summary["items"],
        "cart_items": cart.items.select_related("product").all(),
        "cart_total": summary["total"],
        "cart_count": summary["count"],
        "customer_name": request.user.first_name,
        "phone_number": saved_phone,
    })


@require_GET
def health(request):
    return JsonResponse({"status": "ok", "service": "Vijaya Lakshmi Agro Agencies"})
