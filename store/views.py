
import json
from decimal import Decimal
from urllib.parse import quote

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Category, Product


OWNER_WHATSAPP = "918297243999"


def _categories():
    return Category.objects.all()


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
        {
            "categories": categories,
            "products": products,
        },
    )


def product_list(request):
    products = Product.objects.filter(
        is_active=True
    ).select_related("category")

    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    if query:
        products = products.filter(
            name__icontains=query
        ) | products.filter(
            brand__icontains=query
        )

    if category:
        products = products.filter(
            category__category_type=category
        )

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


def cart_view(request):
    return render(request, "store/cart.html")


def checkout(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse(
                {"error": "Invalid checkout details."},
                status=400,
            )

        if not isinstance(data, dict):
            return JsonResponse(
                {"error": "Invalid checkout details."},
                status=400,
            )

        customer = data.get("customer", {})
        items = data.get("items", [])

        if not isinstance(customer, dict) or not isinstance(items, list):
            return JsonResponse(
                {"error": "Invalid checkout details."},
                status=400,
            )

        name = str(customer.get("name", "")).strip()[:100]
        phone = str(customer.get("phone", "")).strip()[:30]
        address = str(customer.get("address", "")).strip()[:500]

        if not name or not phone or not address or not items:
            return JsonResponse(
                {
                    "error": (
                        "Please enter your name, phone, address "
                        "and at least one product."
                    )
                },
                status=400,
            )

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
        valid_items = 0

        for item in items[:50]:
            if not isinstance(item, dict):
                continue

            try:
                product_id = int(item.get("id"))
                quantity = int(item.get("quantity"))
            except (TypeError, ValueError):
                continue

            if quantity < 1 or quantity > 999:
                continue

            product = Product.objects.filter(
                pk=product_id,
                is_active=True,
            ).first()

            if product is None:
                continue

            line_total = product.price * quantity
            total += line_total
            valid_items += 1

            lines.append(
                f"- {product.name} x {quantity} {product.unit} "
                f"— ₹{line_total:.2f}"
            )

        if valid_items == 0:
            return JsonResponse(
                {
                    "error": (
                        "No valid products found in your cart. "
                        "Please refresh and try again."
                    )
                },
                status=400,
            )

        lines.extend(
            [
                "",
                f"*Estimated subtotal: ₹{total:.2f}*",
                "Delivery charges and final availability to be confirmed by the shop.",
                "Payment to be arranged directly with the shop.",
            ]
        )

        message = "\n".join(lines)
        whatsapp_url = (
            f"https://wa.me/{OWNER_WHATSAPP}?text={quote(message)}"
        )

        return JsonResponse({"whatsapp_url": whatsapp_url})

    return render(request, "store/checkout.html")


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
