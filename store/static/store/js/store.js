
(() => {
  const CART_API = "/api/cart/";
  const CART_UPDATE_API = "/api/cart/update/";

  const money = (n) =>
    "₹" + Number(n).toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });

  const escapeHtml = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[c]));

  let cart = [];
  let cartLoaded = false;
  let cartRequest = Promise.resolve();

  function getCookie(name) {
    const prefix = name + "=";
    const cookie = document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(prefix));

    return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : "";
  }

  function updateCount() {
    const count = cart.reduce(
      (sum, item) => sum + Number(item.quantity || 0),
      0
    );

    const el = document.getElementById("cart-count");
    if (el) el.textContent = count;
  }

  function updateCheckoutButton() {
    const button = document.querySelector(
      '#checkout-form button[type="submit"]'
    );

    if (button && cartLoaded) {
      button.disabled = cart.length === 0;
    }
  }

  async function apiRequest(url, options = {}) {
    const headers = {
      "Accept": "application/json",
      ...(options.headers || {})
    };

    if (options.method === "POST") {
      headers["Content-Type"] = "application/json";
      headers["X-CSRFToken"] = getCookie("csrftoken");
    }

    const response = await fetch(url, {
      credentials: "same-origin",
      ...options,
      headers
    });

    if (response.redirected) {
      window.location.href = "/login/";
      throw new Error("Please log in to use your cart.");
    }

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Something went wrong.");
    }

    return result;
  }

  function applyCart(data) {
    cart = (data.items || []).map((item) => ({
      id: Number(item.id),
      name: item.name,
      price: Number(item.price),
      unit: item.unit || "pack",
      quantity: Number(item.quantity),
      image: item.image || ""
    }));

    cartLoaded = true;
    updateCount();
    renderCart();
    renderCheckout();
    updateCheckoutButton();
  }

  async function loadCart() {
    try {
      const data = await apiRequest(CART_API);
      applyCart(data);
    } catch (error) {
      if (error.message !== "Please log in to use your cart.") {
        cartLoaded = false;
        updateCount();
        showCartError(error.message);
      }
    }
  }

  function showCartError(message) {
    const holder = document.getElementById("cart-items");
    if (holder) {
      holder.innerHTML =
        '<p class="error-message">' + escapeHtml(message) + "</p>";
    }
  }

  function showFeedback(message) {
    let notice = document.getElementById("cart-notice");

    if (!notice) {
      notice = document.createElement("div");
      notice.id = "cart-notice";
      notice.className = "wrap";
      notice.setAttribute("role", "status");

      const header = document.querySelector(".site-header");
      if (header) header.insertAdjacentElement("afterend", notice);
      else document.body.prepend(notice);
    }

    notice.textContent = message;
  }

  async function updateCart(action, id, quantity = 1) {
    const data = await apiRequest(CART_UPDATE_API, {
      method: "POST",
      body: JSON.stringify({ action, id, quantity })
    });

    applyCart(data);
    return data;
  }

  function renderCart() {
    const holder = document.getElementById("cart-items");
    if (!holder) return;

    if (!cartLoaded) {
      holder.innerHTML = "<p>Loading your cart…</p>";
      return;
    }

    if (!cart.length) {
      holder.innerHTML =
        '<div class="empty-state">' +
        "<span>🧺</span>" +
        "<h3>Your cart is empty</h3>" +
        "<p>Explore products and add the items you need.</p>" +
        '<a class="btn btn-primary" href="/products/">Browse products</a>' +
        "</div>";
    } else {
      holder.innerHTML = cart.map((item) => `
        <article class="cart-row">
          <div class="cart-product-mark">✳</div>
          <div class="cart-product-name">
            <strong>${escapeHtml(item.name)}</strong>
            <small>${money(item.price)} / ${escapeHtml(item.unit)}</small>
          </div>
          <label class="qty-label">
            Qty
            <input
              type="number"
              min="1"
              max="999"
              value="${item.quantity}"
              data-change-qty="${item.id}"
            >
          </label>
          <strong>${money(item.price * item.quantity)}</strong>
          <button
            class="remove-btn"
            type="button"
            data-remove-cart="${item.id}"
            aria-label="Remove ${escapeHtml(item.name)}"
          >×</button>
        </article>
      `).join("");
    }

    const total = cart.reduce(
      (sum, item) => sum + item.price * item.quantity,
      0
    );

    const subtotal = document.getElementById("cart-subtotal");
    if (subtotal) subtotal.textContent = money(total);

    const link = document.getElementById("checkout-link");
    if (link) {
      link.style.opacity = cart.length ? "1" : ".5";
      link.style.pointerEvents = cart.length ? "auto" : "none";
    }
  }

  function renderCheckout() {
    const holder = document.getElementById("checkout-summary");
    if (!holder) return;

    if (!cartLoaded) {
      holder.innerHTML = "<p>Loading your order…</p>";
      return;
    }

    if (!cart.length) {
      holder.innerHTML =
        '<p>Your cart is empty. <a href="/products/">Browse products</a>.</p>';
    } else {
      holder.innerHTML = cart.map((item) => `
        <div class="summary-line">
          <span>${escapeHtml(item.name)} × ${item.quantity}</span>
          <strong>${money(item.price * item.quantity)}</strong>
        </div>
      `).join("");
    }

    const total = cart.reduce(
      (sum, item) => sum + item.price * item.quantity,
      0
    );

    const totalElement = document.getElementById("checkout-total");
    if (totalElement) totalElement.textContent = money(total);

    updateCheckoutButton();
  }

  // Product add-to-cart buttons.
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-add-cart]");

    if (button && !button.disabled) {
      event.preventDefault();

      const quantityInput = document.getElementById("detail-qty");
      const quantity = quantityInput
        ? Math.max(1, Math.min(999, Number(quantityInput.value) || 1))
        : 1;

      const product = {
        id: Number(button.dataset.id),
        name: button.dataset.name
      };

      button.disabled = true;

      try {
        await updateCart("add", product.id, quantity);
        showFeedback(product.name + " added to your cart ✓");
      } catch (error) {
        if (error.message !== "Please log in to use your cart.") {
          showFeedback(error.message);
        }
      } finally {
        button.disabled = false;
      }
    }

    const removeButton = event.target.closest("[data-remove-cart]");

    if (removeButton) {
      try {
        await updateCart("remove", Number(removeButton.dataset.removeCart));
      } catch (error) {
        showFeedback(error.message);
      }
    }
  });

  // Quantity updates are sent to the database.
  document.addEventListener("change", async (event) => {
    const input = event.target.closest("[data-change-qty]");
    if (!input) return;

    const quantity = Math.max(
      1,
      Math.min(999, Number(input.value) || 1)
    );

    input.value = quantity;

    try {
      await updateCart(
        "update",
        Number(input.dataset.changeQty),
        quantity
      );
    } catch (error) {
      showFeedback(error.message);
      await loadCart();
    }
  });

  // Language selector.
  const translations = {
    en: {
      home: "Home", products: "Products", cart: "Cart",
      trusted: "YOUR TRUSTED AGRICULTURE PARTNER",
      heroTitle: "Growing better harvests, together.",
      heroDesc: "Quality seeds, fertilizers and crop protection essentials for every season.",
      shopProducts: "Explore products", browse: "BROWSE OUR RANGE",
      shopByCategory: "Shop by category", viewAll: "View all products →",
      category: "CATEGORY", seeds: "Seeds", fertilizers: "Fertilizers",
      pesticides: "Pesticides", seedsDesc: "Start strong, grow well",
      fertDesc: "Nourish every crop", pestDesc: "Crop care essentials",
      handpicked: "HANDPICKED FOR YOUR FARM", featured: "Featured products"
    },
    te: {
      home: "హోమ్", products: "ఉత్పత్తులు", cart: "కార్ట్",
      trusted: "మీ నమ్మకమైన వ్యవసాయ భాగస్వామి",
      heroTitle: "మెరుగైన పంటలు కలిసి పండిద్దాం.",
      heroDesc: "ప్రతి సీజన్‌కు నాణ్యమైన విత్తనాలు, ఎరువులు మరియు పంట సంరక్షణ ఉత్పత్తులు.",
      shopProducts: "ఉత్పత్తులను చూడండి", browse: "మా ఉత్పత్తుల శ్రేణి",
      shopByCategory: "వర్గాల వారీగా చూడండి", viewAll: "అన్ని ఉత్పత్తులు →",
      category: "వర్గం", seeds: "విత్తనాలు", fertilizers: "ఎరువులు",
      pesticides: "పురుగుమందులు", seedsDesc: "మంచి ప్రారంభం, మంచి పెరుగుదల",
      fertDesc: "ప్రతి పంటకు పోషణ", pestDesc: "పంట సంరక్షణ ఉత్పత్తులు",
      handpicked: "మీ పొలం కోసం ఎంపిక చేసినవి", featured: "ప్రత్యేక ఉత్పత్తులు"
    },
    hi: {
      home: "होम", products: "उत्पाद", cart: "कार्ट",
      trusted: "आपका भरोसेमंद कृषि साथी",
      heroTitle: "बेहतर फसलें, मिलकर उगाएँ।",
      heroDesc: "हर मौसम के लिए गुणवत्तापूर्ण बीज, उर्वरक और फसल सुरक्षा उत्पाद।",
      shopProducts: "उत्पाद देखें", browse: "हमारी उत्पाद श्रेणियाँ",
      shopByCategory: "श्रेणी के अनुसार खरीदें", viewAll: "सभी उत्पाद →",
      category: "श्रेणी", seeds: "बीज", fertilizers: "उर्वरक",
      pesticides: "कीटनाशक", seedsDesc: "मजबूत शुरुआत, अच्छी बढ़त",
      fertDesc: "हर फसल को पोषण", pestDesc: "फसल सुरक्षा के उत्पाद",
      handpicked: "आपके खेत के लिए चुने गए", featured: "विशेष उत्पाद"
    }
  };

  function applyLanguage(lang) {
    const dict = translations[lang] || translations.en;

    document.querySelectorAll("[data-i18n]").forEach((element) => {
      const key = element.dataset.i18n;
      if (dict[key]) {
        if (key === "heroTitle") {
          element.textContent = dict[key];
        } else {
          element.textContent = dict[key];
        }
      }
    });

    document.documentElement.lang = lang;
    localStorage.setItem("vla_lang", lang);
  }

  const languageSelect = document.getElementById("language-select");

  if (languageSelect) {
    const savedLanguage = localStorage.getItem("vla_lang") || "en";
    languageSelect.value = savedLanguage;
    applyLanguage(savedLanguage);

    languageSelect.addEventListener("change", () => {
      applyLanguage(languageSelect.value);
    });
  }

  // WhatsApp checkout uses the server-side database cart.
  const checkoutForm = document.getElementById("checkout-form");

  if (checkoutForm) {
    checkoutForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const errorElement = document.getElementById("checkout-error");
      if (errorElement) errorElement.textContent = "";

      if (!cartLoaded || !cart.length) {
        if (errorElement) errorElement.textContent = "Your cart is empty.";
        return;
      }

      const formData = new FormData(checkoutForm);
      const customer = {
        name: formData.get("name"),
        phone: formData.get("phone"),
        address: formData.get("address"),
        notes: formData.get("notes")
      };

      if (customer.notes) {
        customer.address += "\nNotes: " + customer.notes;
      }

      const button = checkoutForm.querySelector('button[type="submit"]');
      const originalText = button ? button.textContent : "";

      if (button) {
        button.disabled = true;
        button.textContent = "Preparing WhatsApp message…";
      }

      try {
        const response = await fetch("/checkout/", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
            "Accept": "application/json"
          },
          body: JSON.stringify({ customer })
        });

        if (response.redirected) {
          window.location.href = "/login/";
          return;
        }

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.error || "Could not prepare order.");
        }

        window.location.href = result.whatsapp_url;
      } catch (error) {
        if (errorElement) {
          errorElement.textContent = error.message || "Please try again.";
        }

        if (button) {
          button.disabled = false;
          button.textContent = originalText;
        }
      }
    });
  }

  // Load the cart belonging to the currently logged-in customer.
  updateCount();
  loadCart();
})();
