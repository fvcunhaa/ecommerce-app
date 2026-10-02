(() => {
  const grid = document.getElementById("productGrid");
  const cards = [...grid.querySelectorAll(".product-card")];
  const pills = [...document.querySelectorAll(".category-pill")];
  const searchForm = document.getElementById("searchForm");
  const searchInput = document.getElementById("searchInput");
  const visibleCount = document.getElementById("visibleCount");
  const emptyState = document.getElementById("emptyState");
  const cartTrigger = document.getElementById("cartTrigger");
  const cartDrawer = document.getElementById("cartDrawer");
  const cartClose = document.getElementById("cartClose");
  const drawerBackdrop = document.getElementById("drawerBackdrop");
  const cartItems = document.getElementById("cartItems");
  const cartEmpty = document.getElementById("cartEmpty");
  const cartCount = document.getElementById("cartCount");
  const cartTotal = document.getElementById("cartTotal");
  const toast = document.getElementById("toast");
  const checkoutButton = document.getElementById("checkoutButton");
  const checkoutModal = document.getElementById("checkoutModal");
  const checkoutBackdrop = document.getElementById("checkoutBackdrop");
  const checkoutClose = document.getElementById("checkoutClose");
  const checkoutForm = document.getElementById("checkoutForm");
  const checkoutTotal = document.getElementById("checkoutTotal");
  const checkoutResult = document.getElementById("checkoutResult");
  const favorites = document.querySelectorAll(".favorite");

  let category = "Todos";
  let cart = [];

  function money(value) {
    return Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  async function applyFilters() {
    const term = searchInput.value.trim();
    const params = new URLSearchParams();
    if (term) params.set("q", term);
    if (category && category !== "Todos") params.set("category", category);
    try {
      const response = await fetch("/api/catalog/search?" + params.toString());
      const payload = await response.json();
      const ids = new Set((payload.products || []).map(item => item.id));
      cards.forEach(card => card.hidden = !ids.has(card.dataset.productId));
      visibleCount.textContent = payload.count || 0;
      emptyState.hidden = (payload.count || 0) !== 0;
    } catch {
      visibleCount.textContent = cards.length;
    }
  }

  pills.forEach(pill => {
    pill.addEventListener("click", () => {
      category = pill.dataset.category;
      pills.forEach(item => item.classList.toggle("active", item === pill));
      applyFilters();
      document.getElementById("products").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  searchForm.addEventListener("submit", event => {
    event.preventDefault();
    applyFilters();
    document.getElementById("products").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  searchInput.addEventListener("input", applyFilters);

  function openCart() {
    cartDrawer.classList.add("open");
    drawerBackdrop.classList.add("open");
    cartDrawer.setAttribute("aria-hidden", "false");
  }

  function closeCart() {
    cartDrawer.classList.remove("open");
    drawerBackdrop.classList.remove("open");
    cartDrawer.setAttribute("aria-hidden", "true");
  }

  cartTrigger.addEventListener("click", openCart);
  cartClose.addEventListener("click", closeCart);
  drawerBackdrop.addEventListener("click", closeCart);

  function renderCart() {
    cartEmpty.hidden = cart.length > 0;
    cartItems.querySelectorAll(".cart-item").forEach(item => item.remove());
    let total = 0;

    cart.forEach((item, index) => {
      total += item.price * (item.quantity || 1);
      const row = document.createElement("div");
      row.className = "cart-item";
      row.innerHTML = `
        <div class="cart-item__visual"></div>
        <div><strong>${item.name}</strong><small>${item.quantity || 1} × ${money(item.price)}</small></div>
        <button type="button" aria-label="Remover ${item.name}" data-remove="${index}">×</button>
      `;
      cartItems.appendChild(row);
    });

    cartItems.querySelectorAll("[data-remove]").forEach(button => {
      button.addEventListener("click", async () => {
        const item = cart[Number(button.dataset.remove)];
        const response = await fetch("/api/cart/remove", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({product_id:item.product_id || item.id})
        });
        const payload = await response.json();
        cart = payload.items || [];
        renderCart();
      });
    });

    cartCount.textContent = cart.length;
    cartTotal.textContent = money(total);
    checkoutTotal.textContent = money(total);
    checkoutButton.disabled = cart.length === 0;
  }

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 1800);
  }

  document.querySelectorAll(".add-cart").forEach(button => {
    button.addEventListener("click", async () => {
      const card = button.closest(".product-card");
      button.classList.add("loading");
      try {
        const response = await fetch("/api/cart/add", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({product_id: card.dataset.productId, quantity: 1})
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.message || "Falha ao adicionar");
        cart = payload.items || [];
        renderCart();
        showToast(button.dataset.product + " adicionado ao carrinho");
      } catch (error) {
        showToast(error.message);
      } finally {
        button.classList.remove("loading");
      }
    });
  });

  function openCheckout() {
    if (!cart.length) return;
    closeCart();
    checkoutModal.classList.add("open");
    checkoutBackdrop.classList.add("open");
    checkoutModal.setAttribute("aria-hidden", "false");
    checkoutResult.textContent = "";
  }

  function closeCheckout() {
    checkoutModal.classList.remove("open");
    checkoutBackdrop.classList.remove("open");
    checkoutModal.setAttribute("aria-hidden", "true");
  }

  checkoutButton.addEventListener("click", openCheckout);
  checkoutClose.addEventListener("click", closeCheckout);
  checkoutBackdrop.addEventListener("click", closeCheckout);

  checkoutForm.addEventListener("submit", async event => {
    event.preventDefault();
    const submit = checkoutForm.querySelector(".checkout-submit");
    submit.disabled = true;
    checkoutResult.textContent = "Processando pedido...";

    const data = new FormData(checkoutForm);
    const grouped = new Map();
    cart.forEach(item => {
      const current = grouped.get(item.name) || { product_id: item.id, quantity: 0 };
      current.quantity += 1;
      grouped.set(item.name, current);
    });

    try {
      const response = await fetch("/api/store/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer: {
            name: data.get("name"),
            email: data.get("email"),
            state: data.get("state")
          },
          payment_method: data.get("payment_method"),
          source: "store",
          items: [...grouped.values()]
        })
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Falha no checkout");

      checkoutResult.innerHTML = `<strong>Pedido #${payload.order.order_id} confirmado!</strong><br>Total: ${money(payload.order.total)} · Transação ${payload.order.transaction_id}`;
      await fetch("/api/cart/clear", {method:"POST"});
      cart = [];
      renderCart();
      checkoutForm.reset();
      showToast("Compra confirmada com sucesso.");
    } catch (error) {
      checkoutResult.textContent = error.message;
    } finally {
      submit.disabled = false;
    }
  });

  favorites.forEach(button => {
    button.addEventListener("click", () => {
      button.classList.toggle("active");
      button.textContent = button.classList.contains("active") ? "♥" : "♡";
    });
  });

  async function loadCart() {
    try {
      const response = await fetch("/api/cart");
      const payload = await response.json();
      cart = payload.items || [];
    } finally {
      renderCart();
    }
  }

  loadCart();
})();
