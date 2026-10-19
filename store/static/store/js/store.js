(() => {
  const CART_KEY = "vla_cart_v1";
  const getCart = () => { try { return JSON.parse(localStorage.getItem(CART_KEY) || "[]"); } catch { return []; } };
  const saveCart = (cart) => { localStorage.setItem(CART_KEY, JSON.stringify(cart)); updateCount(); };
  const money = n => "₹" + Number(n).toLocaleString("en-IN", {minimumFractionDigits:2, maximumFractionDigits:2});
  const updateCount = () => {
    const count = getCart().reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    const el = document.getElementById("cart-count"); if (el) el.textContent = count;
  };
  const add = (data, quantity=1) => {
    const cart = getCart(), existing = cart.find(i => String(i.id) === String(data.id));
    if (existing) existing.quantity = Math.min(999, Number(existing.quantity) + quantity);
    else cart.push({...data, quantity});
    saveCart(cart);
    const btnText = "Added to cart ✓";
    document.querySelectorAll("[data-add-cart]").forEach(b => {
      if (String(b.dataset.id) === String(data.id)) {
        const old = b.textContent; b.textContent = btnText; setTimeout(() => b.textContent = old, 1200);
      }
    });
  };
  document.addEventListener("click", e => {
    const btn = e.target.closest("[data-add-cart]");
    if (btn && !btn.disabled) {
      const qtyInput = document.getElementById("detail-qty");
      const qty = qtyInput ? Math.max(1, Math.min(999, Number(qtyInput.value) || 1)) : 1;
      add({id: Number(btn.dataset.id), name: btn.dataset.name, price: Number(btn.dataset.price), unit: btn.dataset.unit}, qty);
    }
    const remove = e.target.closest("[data-remove-cart]");
    if (remove) { saveCart(getCart().filter(i => String(i.id) !== String(remove.dataset.removeCart))); renderCart(); }
    const change = e.target.closest("[data-change-qty]");
    if (change) {
      const cart = getCart(), item = cart.find(i => String(i.id) === String(change.dataset.changeQty));
      if (item) { item.quantity = Math.max(1, Math.min(999, Number(change.value) || 1)); saveCart(cart); renderCart(); }
    }
  });
  function renderCart() {
    const holder = document.getElementById("cart-items"); if (!holder) return;
    const cart = getCart();
    if (!cart.length) { holder.innerHTML = '<div class="empty-state"><span>🧺</span><h3>Your cart is empty</h3><p>Explore products and add the items you need.</p><a class="btn btn-primary" href="/products/">Browse products</a></div>'; }
    else holder.innerHTML = cart.map(i => `<article class="cart-row"><div class="cart-product-mark">✳</div><div class="cart-product-name"><strong>${escapeHtml(i.name)}</strong><small>${money(i.price)} / ${escapeHtml(i.unit || "unit")}</small></div><label class="qty-label">Qty <input type="number" min="1" max="999" value="${Number(i.quantity)}" data-change-qty="${Number(i.id)}"></label><strong>${money(i.price * i.quantity)}</strong><button class="remove-btn" type="button" data-remove-cart="${Number(i.id)}" aria-label="Remove ${escapeHtml(i.name)}">×</button></article>`).join("");
    const total = cart.reduce((s,i) => s + Number(i.price)*Number(i.quantity), 0);
    const subtotal = document.getElementById("cart-subtotal"); if (subtotal) subtotal.textContent = money(total);
    const link = document.getElementById("checkout-link"); if (link) { link.style.opacity = cart.length ? "1" : ".5"; link.style.pointerEvents = cart.length ? "auto" : "none"; }
  }
  function renderCheckout() {
    const holder = document.getElementById("checkout-summary"); if (!holder) return;
    const cart = getCart();
    if (!cart.length) { holder.innerHTML = '<p>Your cart is empty. <a href="/products/">Browse products</a>.</p>'; const btn = document.querySelector('#checkout-form button[type="submit"]'); if(btn) btn.disabled = true; return; }
    holder.innerHTML = cart.map(i => `<div class="summary-line"><span>${escapeHtml(i.name)} × ${Number(i.quantity)}</span><strong>${money(i.price*i.quantity)}</strong></div>`).join("");
    const total = cart.reduce((s,i) => s + Number(i.price)*Number(i.quantity), 0);
    document.getElementById("checkout-total").textContent = money(total);
  }
  const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const translations = {
    en: {home:"Home",products:"Products",cart:"Cart",trusted:"YOUR TRUSTED AGRICULTURE PARTNER",heroTitle:"Growing better harvests, together.",heroDesc:"Quality seeds, fertilizers and crop protection essentials for every season.",shopProducts:"Explore products",browse:"BROWSE OUR RANGE",shopByCategory:"Shop by category",viewAll:"View all products →",category:"CATEGORY",seeds:"Seeds",fertilizers:"Fertilizers",pesticides:"Pesticides",seedsDesc:"Start strong, grow well",fertDesc:"Nourish every crop",pestDesc:"Crop care essentials",handpicked:"HANDPICKED FOR YOUR FARM",featured:"Featured products"},
    te: {home:"హోమ్",products:"ఉత్పత్తులు",cart:"కార్ట్",trusted:"మీ నమ్మకమైన వ్యవసాయ భాగస్వామి",heroTitle:"మెరుగైన పంటలు కలిసి పండిద్దాం.",heroDesc:"ప్రతి సీజన్‌కు నాణ్యమైన విత్తనాలు, ఎరువులు మరియు పంట సంరక్షణ ఉత్పత్తులు.",shopProducts:"ఉత్పత్తులను చూడండి",browse:"మా ఉత్పత్తుల శ్రేణి",shopByCategory:"వర్గాల వారీగా చూడండి",viewAll:"అన్ని ఉత్పత్తులు →",category:"వర్గం",seeds:"విత్తనాలు",fertilizers:"ఎరువులు",pesticides:"పురుగుమందులు",seedsDesc:"మంచి ప్రారంభం, మంచి పెరుగుదల",fertDesc:"ప్రతి పంటకు పోషణ",pestDesc:"పంట సంరక్షణ ఉత్పత్తులు",handpicked:"మీ పొలం కోసం ఎంపిక చేసినవి",featured:"ప్రత్యేక ఉత్పత్తులు"},
    hi: {home:"होम",products:"उत्पाद",cart:"कार्ट",trusted:"आपका भरोसेमंद कृषि साथी",heroTitle:"बेहतर फसलें, मिलकर उगाएँ।",heroDesc:"हर मौसम के लिए गुणवत्तापूर्ण बीज, उर्वरक और फसल सुरक्षा उत्पाद।",shopProducts:"उत्पाद देखें",browse:"हमारी उत्पाद श्रेणियाँ",shopByCategory:"श्रेणी के अनुसार खरीदें",viewAll:"सभी उत्पाद →",category:"श्रेणी",seeds:"बीज",fertilizers:"उर्वरक",pesticides:"कीटनाशक",seedsDesc:"मजबूत शुरुआत, अच्छी बढ़त",fertDesc:"हर फसल को पोषण",pestDesc:"फसल सुरक्षा के उत्पाद",handpicked:"आपके खेत के लिए चुने गए",featured:"विशेष उत्पाद"}
  };
  const applyLanguage = lang => {
    const dict = translations[lang] || translations.en;
    document.querySelectorAll("[data-i18n]").forEach(el => { const key = el.dataset.i18n; if (dict[key]) { if (key === "heroTitle") el.innerHTML = escapeHtml(dict[key]).replace(" together.", " <em>together.</em>").replace(" కలిసి పండిద్దాం.", " <em>కలిసి పండిద్దాం.</em>").replace(" मिलकर उगाएँ।", " <em>मिलकर उगाएँ।</em>"); else el.textContent = dict[key]; } });
    document.documentElement.lang = lang;
    localStorage.setItem("vla_lang", lang);
  };
  const langSelect = document.getElementById("language-select");
  if (langSelect) { const saved = localStorage.getItem("vla_lang") || "en"; langSelect.value = saved; applyLanguage(saved); langSelect.addEventListener("change", () => applyLanguage(langSelect.value)); }
  const checkoutForm = document.getElementById("checkout-form");
  if (checkoutForm) checkoutForm.addEventListener("submit", async e => {
    e.preventDefault();
    const error = document.getElementById("checkout-error"); error.textContent = "";
    const cart = getCart(); if (!cart.length) { error.textContent = "Your cart is empty."; return; }
    const fd = new FormData(checkoutForm);
    const payload = {customer:{name:fd.get("name"),phone:fd.get("phone"),address:fd.get("address"),notes:fd.get("notes")},items:cart.map(i=>({id:i.id,quantity:i.quantity}))};
    if (payload.customer.notes) payload.customer.address += "\nNotes: " + payload.customer.notes;
    const btn = checkoutForm.querySelector('button[type="submit"]'); btn.disabled = true; btn.textContent = "Preparing WhatsApp message…";
    try {
      const response = await fetch("/checkout/", {method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":getCookie("csrftoken")},body:JSON.stringify(payload)});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not prepare order.");
      window.location.href = result.whatsapp_url;
    } catch (err) { error.textContent = err.message || "Please try again."; btn.disabled = false; btn.textContent = "Send order to WhatsApp ↗"; }
  });
  function getCookie(name) { const value = `; ${document.cookie}`; const parts = value.split(`; ${name}=`); return parts.length === 2 ? parts.pop().split(";").shift() : ""; }
  updateCount(); renderCart(); renderCheckout();
})(); 
