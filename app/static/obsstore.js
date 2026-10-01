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

  function applyFilters() {
    const term = searchInput.value.trim().toLowerCase();
    let count = 0;
    cards.forEach(card => {
      const matchesCategory = category === "Todos" || card.dataset.category === category;
      const matchesSearch = !term || card.dataset.name.includes(term) || card.dataset.category.toLowerCase().includes(term);
      const visible = matchesCategory && matchesSearch;
      card.hidden = !visible;
      if (visible) count += 1;
    });
    visibleCount.textContent = count;
    emptyState.hidden = count !== 0;
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
      total += item.price;
      const row = document.createElement("div");
      row.className = "cart-item";
      row.innerHTML = `
        <div class="cart-item__visual"></div>
        <div><strong>${item.name}</strong><small>${money(item.price)}</small></div>
        <button type="button" aria-label="Remover ${item.name}" data-remove="${index}">×</button>
      `;
      cartItems.appendChild(row);
    });

    cartItems.querySelectorAll("[data-remove]").forEach(button => {
      button.addEventListener("click", () => {
        cart.splice(Number(button.dataset.remove), 1);
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
      button.classList.add("loading");
      const card = button.closest(".product-card");
      const product = { id: card.dataset.productId, name: button.dataset.product, price: Number(button.dataset.price) };
      try {
        const response = await fetch("/carrinho/adicionar");
        if (!response.ok) throw new Error("Falha ao registrar carrinho");
        cart.push(product);
        renderCart();
        button.classList.remove("loading");
        button.classList.add("added");
        button.textContent = "Adicionado";
        showToast(`${product.name} adicionado ao carrinho`);
        window.setTimeout(() => {
          button.classList.remove("added");
          button.textContent = "Adicionar ao carrinho";
        }, 1300);
      } catch (error) {
        button.classList.remove("loading");
        showToast("Não foi possível adicionar o produto.");
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

  renderCart();
})();
