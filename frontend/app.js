const API = "/api/v1";
const state = {
  categories: [],
  sellers: [],
  products: [],
  sellerProducts: [],
  cart: null,
  user: null,
  activeView: "catalog",
  editingProductId: null,
  editingCategoryId: null,
  noticeTimer: null,
  activeActions: new WeakSet(),
  loadingProducts: false,
  scrollPositions: { catalog: 0 },
  productDialogScrollY: null,
  productDialogOpener: null,
};

const elements = {
  notice: document.querySelector("#notice"),
  grid: document.querySelector("#product-grid"),
  catalogEmpty: document.querySelector("#catalog-empty"),
  search: document.querySelector("#search-input"),
  categoryFilter: document.querySelector("#category-filter"),
  sellerFilter: document.querySelector("#seller-filter"),
  cartCount: document.querySelector("#cart-count"),
  cartDialog: document.querySelector("#cart-dialog"),
  cartItems: document.querySelector("#cart-items"),
  cartTotalItems: document.querySelector("#cart-total-items"),
  cartTotal: document.querySelector("#cart-total"),
  checkout: document.querySelector("#checkout-button"),
  ordersList: document.querySelector("#orders-list"),
  ordersEmpty: document.querySelector("#orders-empty"),
  categorySelect: document.querySelector("#product-category"),
  categoryAdminList: document.querySelector("#category-admin-list"),
  productAdminList: document.querySelector("#product-admin-list"),
  productForm: document.querySelector("#product-form"),
  productFormTitle: document.querySelector("#product-form-title"),
  productSubmit: document.querySelector("#product-submit"),
  cancelEdit: document.querySelector("#cancel-edit"),
  categoryForm: document.querySelector("#category-form"),
  categoryFormTitle: document.querySelector("#category-form-title"),
  categorySubmit: document.querySelector("#category-submit"),
  categoryCancel: document.querySelector("#category-cancel"),
  productDialog: document.querySelector("#product-dialog"),
  productDetail: document.querySelector("#product-detail-content"),
  cartButton: document.querySelector("#open-cart"),
  ordersNav: document.querySelector("#orders-nav"),
  manageNav: document.querySelector("#manage-nav"),
  profileNav: document.querySelector("#profile-nav"),
  accountName: document.querySelector("#account-name"),
  loginOpen: document.querySelector("#login-open"),
  registerOpen: document.querySelector("#register-open"),
  logoutButton: document.querySelector("#logout-button"),
  loginDialog: document.querySelector("#login-dialog"),
  registerDialog: document.querySelector("#register-dialog"),
  loginForm: document.querySelector("#login-form"),
  registerForm: document.querySelector("#register-form"),
  profileForm: document.querySelector("#profile-form"),
  sellerProfileCard: document.querySelector("#seller-profile-card"),
  sellerProfileForm: document.querySelector("#seller-profile-form"),
  clientProfileCard: document.querySelector("#client-profile-card"),
  passwordForm: document.querySelector("#password-form"),
  sellerRegistrationFields: document.querySelector("#seller-registration-fields"),
  registerSubmit: document.querySelector("#register-submit"),
  catalogFeedback: document.querySelector("#catalog-feedback"),
  clearCatalogFilters: document.querySelector("#clear-catalog-filters"),
  productAdminEmpty: document.querySelector("#product-admin-empty"),
  siteHeader: document.querySelector("#site-header"),
};

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail;
    const error = new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join(", ") : detail || "A solicitação não foi concluída.");
    error.status = response.status;
    throw error;
  }
  return payload;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function safeImageUrl(value) {
  if (!value) return "";
  try {
    const url = new URL(value, window.location.origin);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}

function money(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(value || 0));
}

function showNotice(message, isError = false) {
  clearTimeout(state.noticeTimer);
  elements.notice.textContent = message;
  elements.notice.classList.toggle("error", isError);
  elements.notice.setAttribute("role", isError ? "alert" : "status");
  elements.notice.hidden = false;
  elements.notice.classList.remove("notice-visible");
  requestAnimationFrame(() => elements.notice.classList.add("notice-visible"));
  state.noticeTimer = setTimeout(() => {
    elements.notice.classList.remove("notice-visible");
    elements.notice.hidden = true;
  }, 4200);
}

async function run(action, trigger = null, loadingText = "Processando...") {
  if (trigger && state.activeActions.has(trigger)) return;
  const originalMarkup = trigger?.innerHTML;
  const wasDisabled = trigger?.disabled;
  if (trigger) {
    state.activeActions.add(trigger);
    trigger.disabled = true;
    trigger.setAttribute("aria-busy", "true");
    trigger.textContent = loadingText;
  }
  try {
    await action();
  } catch (error) {
    showNotice(error.message || "Não foi possível concluir a operação.", true);
  } finally {
    if (trigger) {
      state.activeActions.delete(trigger);
      trigger.disabled = wasDisabled;
      trigger.removeAttribute("aria-busy");
      trigger.innerHTML = originalMarkup;
    }
  }
}

function showSkeletonProducts() {
  elements.grid.innerHTML = Array.from({ length: 4 }, () => `
    <article class="product-card skeleton-card" aria-hidden="true">
      <div class="skeleton skeleton-image"></div>
      <div class="skeleton skeleton-line"></div>
      <div class="skeleton skeleton-line short"></div>
    </article>`).join("");
}

function fieldMessage(field) {
  const validity = field.validity;
  if (validity.valueMissing) return "Preencha este campo.";
  if (validity.typeMismatch) return "Informe um formato válido.";
  if (validity.badInput) return "Informe um valor válido.";
  if (validity.tooShort) return `Use pelo menos ${field.minLength} caracteres.`;
  if (validity.tooLong) return `Use no máximo ${field.maxLength} caracteres.`;
  if (validity.rangeUnderflow) return `O valor mínimo é ${field.min}.`;
  if (validity.rangeOverflow) return `O valor máximo é ${field.max}.`;
  if (validity.stepMismatch) return "Informe um valor no formato indicado.";
  if (validity.patternMismatch) return field.title || "Confira o formato informado.";
  if (
    (field.name === "new_password" || (field.name === "password" && field.form.id === "register-form"))
    && field.value
    && !(/[a-z]/.test(field.value) && /[A-Z]/.test(field.value) && /\d/.test(field.value))
  ) {
    return "Inclua ao menos uma letra maiúscula, uma minúscula e um número.";
  }
  if (field.name === "business_phone" && field.value.trim()) {
    const digits = field.value.replace(/\D/g, "");
    if (!/^[+()0-9 .-]{8,30}$/.test(field.value) || digits.length < 8 || digits.length > 15) {
      return "Informe um telefone com DDD e de 8 a 15 dígitos.";
    }
  }
  if (validity.customError) return field.validationMessage;
  if (!validity.valid) return "Confira o valor informado.";
  return "";
}

function updateConfirmValidity(field) {
  if (field.name !== "confirm_password") return;
  const password = field.form.querySelector('input[name="new_password"], input[name="password"]');
  field.setCustomValidity(
    password && field.value && password.value !== field.value
      ? "As senhas não correspondem."
      : "",
  );
}

function updateFieldState(field, { showEmpty = false } = {}) {
  if (!field.willValidate) return true;
  updateConfirmValidity(field);
  const message = fieldMessage(field);
  const errorId = `${field.id}-error`;
  let error = document.getElementById(errorId);
  const shouldShow = Boolean(message) && (showEmpty || field.value !== "");

  if (shouldShow) {
    if (!error) {
      error = document.createElement("small");
      error.className = "field-error";
      error.id = errorId;
      error.setAttribute("aria-live", "polite");
      const wrapper = field.closest(".password-field");
      (wrapper || field).insertAdjacentElement("afterend", error);
    }
    error.textContent = message;
    field.setAttribute("aria-invalid", "true");
    field.classList.add("is-invalid");
    field.classList.remove("is-valid");
    const describedBy = new Set((field.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean));
    describedBy.add(errorId);
    field.setAttribute("aria-describedby", [...describedBy].join(" "));
  } else {
    if (error) error.remove();
    field.removeAttribute("aria-invalid");
    field.classList.remove("is-invalid");
    if (field.value && field.validity.valid) field.classList.add("is-valid");
    else field.classList.remove("is-valid");
    const describedBy = (field.getAttribute("aria-describedby") || "")
      .split(/\s+/)
      .filter((id) => id && id !== errorId);
    if (describedBy.length) field.setAttribute("aria-describedby", describedBy.join(" "));
    else field.removeAttribute("aria-describedby");
  }
  return !message;
}

function prepareForms() {
  document.querySelectorAll("form").forEach((form) => {
    form.noValidate = true;
    form.querySelectorAll("input, textarea, select").forEach((field, index) => {
      if (!field.id) field.id = `${form.id || "form"}-${field.name || "field"}-${index}`;
    });
    form.querySelectorAll("input[required], textarea[required], select[required]").forEach((field) => {
      const label = field.closest("label");
      if (label && !label.querySelector(".required-marker")) {
        const marker = document.createElement("span");
        marker.className = "required-marker";
        marker.textContent = "Obrigatório";
        marker.setAttribute("aria-hidden", "true");
        label.append(marker);
      }
    });

    form.addEventListener("input", (event) => {
      if (event.target.matches("input, textarea, select")) {
        updateFieldState(event.target);
        const confirmation = form.querySelector('input[name="confirm_password"]');
        if (confirmation?.value) updateFieldState(confirmation);
      }
    });
    form.addEventListener("change", (event) => {
      if (event.target.matches("input, textarea, select")) updateFieldState(event.target);
    });
    form.addEventListener("blur", (event) => {
      if (event.target.matches("input, textarea, select")) {
        updateFieldState(event.target, { showEmpty: true });
      }
    }, true);
    form.addEventListener("submit", (event) => {
      const fields = [...form.querySelectorAll("input, textarea, select")]
        .filter((field) => field.willValidate);
      const invalidFields = fields.filter(
        (field) => !updateFieldState(field, { showEmpty: true }),
      );
      if (invalidFields.length) {
        event.preventDefault();
        event.stopImmediatePropagation();
        invalidFields[0].focus();
        showNotice("Revise os campos destacados antes de continuar.", true);
      }
    }, true);
    form.addEventListener("reset", () => {
      requestAnimationFrame(() => {
        form.querySelectorAll(".field-error").forEach((error) => error.remove());
        form.querySelectorAll("[aria-invalid]").forEach((field) => field.removeAttribute("aria-invalid"));
        form.querySelectorAll(".is-invalid, .is-valid").forEach((field) => {
          field.classList.remove("is-invalid", "is-valid");
        });
        form.querySelectorAll("[aria-describedby]").forEach((field) => field.removeAttribute("aria-describedby"));
      });
    });
  });
}

function installPasswordToggles() {
  document.querySelectorAll('input[type="password"]').forEach((field) => {
    const wrapper = document.createElement("span");
    wrapper.className = "password-field";
    field.parentNode.insertBefore(wrapper, field);
    wrapper.append(field);
    const toggle = document.createElement("button");
    toggle.className = "password-toggle";
    toggle.type = "button";
    toggle.setAttribute("aria-label", "Mostrar senha");
    toggle.setAttribute("aria-pressed", "false");
    toggle.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"></path><circle cx="12" cy="12" r="3"></circle></svg>';
    toggle.addEventListener("click", () => {
      const visible = field.type === "password";
      field.type = visible ? "text" : "password";
      toggle.setAttribute("aria-pressed", String(visible));
      toggle.setAttribute("aria-label", visible ? "Ocultar senha" : "Mostrar senha");
      toggle.title = visible ? "Ocultar senha" : "Mostrar senha";
      field.focus();
    });
    wrapper.append(toggle);
  });
}

function maskBusinessPhone(field) {
  const oldValue = field.value;
  const cursor = field.selectionStart ?? oldValue.length;
  const digitsBeforeCursor = oldValue.slice(0, cursor).replace(/\D/g, "").length;
  let digits = oldValue.replace(/\D/g, "");
  const hasBrazilPrefix = digits.startsWith("55") && digits.length > 11;
  const countryCode = hasBrazilPrefix ? "+55 " : "";
  if (hasBrazilPrefix) digits = digits.slice(2, 13);
  else if (digits.length > 11) return;
  if (digits.length < 3) return;
  const area = digits.slice(0, 2);
  const subscriber = digits.slice(2);
  const split = subscriber.length > 8 ? subscriber.length - 4 : Math.max(subscriber.length - 4, 0);
  const formattedSubscriber = split > 0
    ? `${subscriber.slice(0, split)}-${subscriber.slice(split)}`
    : subscriber;
  const formatted = `${countryCode}(${area}) ${formattedSubscriber}`;
  field.value = formatted;
  let newCursor = 0;
  let countedDigits = 0;
  while (newCursor < formatted.length && countedDigits < digitsBeforeCursor) {
    if (/\d/.test(formatted[newCursor])) countedDigits += 1;
    newCursor += 1;
  }
  field.setSelectionRange(newCursor, newCursor);
}

document.querySelectorAll('input[type="tel"][name="business_phone"]').forEach((field) => {
  field.addEventListener("input", () => maskBusinessPhone(field));
});
installPasswordToggles();
prepareForms();

async function loadCategories() {
  const response = await api("/categories");
  state.categories = response.items;
  renderCategoryOptions();
  renderCategoryAdmin();
}

function renderCategoryOptions() {
  const selectedFilter = elements.categoryFilter.value;
  const selectedProduct = elements.categorySelect.value;
  const options = state.categories
    .map((category) => `<option value="${escapeHtml(category.name)}">${escapeHtml(category.name)}</option>`)
    .join("");
  elements.categoryFilter.innerHTML = `<option value="">Todas</option>${options}`;
  elements.categorySelect.innerHTML = `<option value="">Selecione uma categoria</option>${options}`;
  if (state.categories.some((category) => category.name === selectedFilter)) {
    elements.categoryFilter.value = selectedFilter;
  }
  if (state.categories.some((category) => category.name === selectedProduct)) {
    elements.categorySelect.value = selectedProduct;
  }
}

function renderSellerOptions() {
  const selectedFilter = elements.sellerFilter.value;
  const options = state.sellers
    .map((seller) => `<option value="${escapeHtml(seller.id)}">${escapeHtml(seller.name)}</option>`)
    .join("");
  elements.sellerFilter.innerHTML = `<option value="">Todos</option>${options}`;
  if (state.sellers.some((seller) => seller.id === selectedFilter)) {
    elements.sellerFilter.value = selectedFilter;
  }
}

async function loadSellers() {
  const response = await api("/auth/sellers");
  state.sellers = response;
  renderSellerOptions();
}

async function loadProducts(useCatalogFilters = true) {
  const params = new URLSearchParams({ limit: "100" });
  const search = elements.search.value.trim();
  const category = elements.categoryFilter.value;
  const sellerId = elements.sellerFilter.value;
  if (useCatalogFilters && search) params.set("search", search);
  if (useCatalogFilters && category) params.set("category", category);
  if (useCatalogFilters && sellerId) params.set("seller_id", sellerId);
  const endpoint = useCatalogFilters ? "/products" : "/products/mine";
  if (useCatalogFilters && state.products.length === 0) {
    elements.grid.setAttribute("aria-busy", "true");
    showSkeletonProducts();
  }
  try {
    const response = await api(`${endpoint}?${params}`);
    if (useCatalogFilters) {
      state.products = response.items;
      renderProducts();
      const count = response.total ?? response.items.length;
      elements.catalogFeedback.textContent = `${count} ${count === 1 ? "produto encontrado" : "produtos encontrados"}.`;
    } else {
      state.sellerProducts = response.items;
    }
    renderProductAdmin();
  } finally {
    if (useCatalogFilters) elements.grid.setAttribute("aria-busy", "false");
  }
}

function updateClearCatalogFiltersVisibility() {
  elements.clearCatalogFilters.hidden = !(
    elements.search.value.trim()
    || elements.categoryFilter.value
    || elements.sellerFilter.value
  );
}

async function reloadSellerAndCatalog() {
  await loadProducts(false);
  await loadProducts();
}

function renderProducts() {
  elements.catalogEmpty.hidden = state.products.length !== 0;
  elements.grid.innerHTML = state.products.map((product) => {
    const image = safeImageUrl(product.image_url);
    const imageMarkup = image
      ? `<img class="product-image" src="${escapeHtml(image)}" alt="${escapeHtml(product.name)}" loading="lazy">`
      : `<div class="product-placeholder" aria-hidden="true">L</div>`;
    const available = product.status === "active" && product.stock > 0;
    const canBuy = state.user?.role === "client";
    return `
      <article class="product-card" data-product-id="${escapeHtml(product.id)}" tabindex="0" aria-label="Ver detalhes de ${escapeHtml(product.name)}">
        <div class="product-image-wrap">
          ${imageMarkup}
          ${available && canBuy ? `<button class="quick-add" type="button" data-add="${escapeHtml(product.id)}" aria-label="Adicionar ${escapeHtml(product.name)} à sacola">+</button>` : ""}
        </div>
        <div class="product-meta">
          <div>
            <p class="product-category">${escapeHtml(product.category)}</p>
            <span class="product-name">${escapeHtml(product.name)}</span>
          </div>
          <p class="product-price">${money(product.price)}</p>
        </div>
        <p class="product-description">${escapeHtml(product.description)}</p>
      </article>`;
  }).join("");
}

async function loadCart() {
  if (state.user?.role !== "client") {
    state.cart = null;
    renderCart();
    return;
  }
  state.cart = await api("/carts");
  renderCart();
}

function renderCart() {
  const cart = state.cart || { items: [], total_items: 0, total: 0 };
  elements.cartCount.textContent = String(cart.total_items);
  elements.cartTotalItems.textContent = String(cart.total_items);
  elements.cartTotal.textContent = money(cart.total);
  elements.checkout.disabled = !state.user || cart.items.length === 0;
  if (!cart.items.length) {
    elements.cartItems.innerHTML = '<p class="cart-empty">Sua sacola Linx está esperando por uma boa escolha.</p>';
    return;
  }
  elements.cartItems.innerHTML = cart.items.map((item) => {
    const image = safeImageUrl(item.image_url);
    return `
      <article class="cart-line">
        <div class="cart-thumb">${image ? `<img src="${escapeHtml(image)}" alt="">` : "L"}</div>
        <div>
          <h3>${escapeHtml(item.name)}</h3>
          <p>${item.available ? `${money(item.unit_price)} cada` : "Remova este item para continuar."}</p>
          ${item.available ? `<div class="cart-quantity">
            <button type="button" data-quantity="${escapeHtml(item.product_id)}" data-value="${item.quantity - 1}" aria-label="Diminuir quantidade">−</button>
            <span>${item.quantity}</span>
            <button type="button" data-quantity="${escapeHtml(item.product_id)}" data-value="${item.quantity + 1}" aria-label="Aumentar quantidade">+</button>
          </div>` : `<p>Quantidade: ${item.quantity}</p>`}
        </div>
        <div class="cart-line-end">
          <strong>${money(item.subtotal)}</strong>
          <button type="button" data-remove="${escapeHtml(item.product_id)}">Remover</button>
        </div>
      </article>`;
  }).join("");
  if (cart.has_unavailable_items) {
    elements.cartItems.insertAdjacentHTML(
      "afterbegin",
      '<p class="cart-warning">Alguns itens não estão mais disponíveis e não fazem parte do total.</p>',
    );
  }
}

async function addToCart(productId, quantity = 1) {
  if (state.user?.role !== "client") {
    elements.loginDialog.showModal();
    return;
  }
  state.cart = await api("/carts/items", {
    method: "POST",
    body: JSON.stringify({ product_id: productId, quantity }),
  });
  renderCart();
  showNotice("Produto adicionado à sua sacola Linx.");
}

async function loadOrders() {
  const response = await api("/orders?limit=100");
  elements.ordersEmpty.hidden = response.items.length !== 0;
  elements.ordersList.innerHTML = response.items.map((order) => {
    const statusText = order.status === "confirmed" ? "Confirmado" : "Cancelado";
    const items = order.items.map((item) => `
      <div>${item.quantity} × ${escapeHtml(item.name)} <span>· ${money(item.unit_price)} cada</span></div>
    `).join("");
    const cancelButton = order.status === "confirmed"
      ? `<button class="text-button danger" type="button" data-cancel-order="${escapeHtml(order.id)}">Cancelar pedido</button>`
      : "";
    return `
      <article class="order-card">
        <div class="order-topline">
          <span class="order-id">Pedido ${escapeHtml(order.id.slice(0, 8).toUpperCase())} · ${new Date(order.created_at).toLocaleDateString("pt-BR")}</span>
          <span class="order-status ${order.status}">${statusText}</span>
        </div>
        <div class="order-items">${items}</div>
        <div class="order-bottom"><span>${cancelButton}</span><strong>${money(order.total)}</strong></div>
      </article>`;
  }).join("");
}

async function loadCategoryAdmin() {
  await loadCategories();
}

function renderCategoryAdmin() {
  elements.categoryAdminList.innerHTML = state.categories.map((category) => `
    <li class="category-admin-item">
      <span>${escapeHtml(category.name)}<small>${escapeHtml(category.description || "Sem descrição")}</small></span>
      <span class="table-actions">
        <button class="text-button" type="button" data-edit-category="${escapeHtml(category.id)}">Editar</button>
        <button class="text-button danger" type="button" data-delete-category="${escapeHtml(category.id)}" aria-label="Excluir categoria ${escapeHtml(category.name)}">Excluir</button>
      </span>
    </li>`).join("");
}

function resetCategoryForm() {
  state.editingCategoryId = null;
  elements.categoryForm.reset();
  elements.categoryFormTitle.textContent = "Categorias";
  elements.categorySubmit.textContent = "Adicionar";
  elements.categoryCancel.hidden = true;
}

function editCategory(categoryId) {
  const category = state.categories.find((item) => item.id === categoryId);
  if (!category) return;
  state.editingCategoryId = category.id;
  document.querySelector("#category-name").value = category.name;
  document.querySelector("#category-description").value = category.description || "";
  elements.categoryFormTitle.textContent = "Editar categoria";
  elements.categorySubmit.textContent = "Salvar alterações";
  elements.categoryCancel.hidden = false;
  elements.categoryForm.scrollIntoView({ behavior: "smooth", block: "center" });
}

function renderProductAdmin() {
  elements.productAdminList.innerHTML = state.sellerProducts.map((product) => `
    <tr>
      <td>${escapeHtml(product.name)}</td>
      <td>${escapeHtml(product.category)}</td>
      <td>${money(product.price)}</td>
      <td>${product.stock}</td>
      <td><span class="status-tag ${product.status}">${product.status === "active" ? "Ativo" : "Inativo"}</span></td>
      <td><div class="table-actions">
        <button class="text-button" type="button" data-edit-product="${escapeHtml(product.id)}">Editar</button>
        <button class="text-button danger" type="button" data-delete-product="${escapeHtml(product.id)}">Excluir</button>
      </div></td>
    </tr>`).join("");
}

function resetProductForm() {
  state.editingProductId = null;
  elements.productForm.reset();
  elements.productFormTitle.textContent = "Novo produto";
  elements.productSubmit.textContent = "Cadastrar produto";
  elements.cancelEdit.hidden = true;
}

function editProduct(productId) {
  const product = state.sellerProducts.find((item) => item.id === productId);
  if (!product) return;
  state.editingProductId = product.id;
  document.querySelector("#product-name").value = product.name;
  document.querySelector("#product-description").value = product.description;
  elements.categorySelect.value = product.category;
  document.querySelector("#product-price").value = product.price;
  document.querySelector("#product-stock").value = product.stock;
  document.querySelector("#product-image").value = product.image_url || "";
  document.querySelector("#product-status").value = product.status;
  elements.productFormTitle.textContent = "Editar produto";
  elements.productSubmit.textContent = "Salvar alterações";
  elements.cancelEdit.hidden = false;
  elements.productForm.scrollIntoView({ behavior: "smooth", block: "center" });
}

function showProductDetails(productId, opener = null) {
  const product = state.products.find((item) => item.id === productId);
  if (!product) return;
  state.productDialogScrollY = window.scrollY;
  state.productDialogOpener = opener;
  const image = safeImageUrl(product.image_url);
  elements.productDetail.innerHTML = `
    <div class="detail-layout">
      ${image ? `<img class="detail-image" src="${escapeHtml(image)}" alt="${escapeHtml(product.name)}">` : '<div class="detail-image product-placeholder">L</div>'}
      <div class="detail-content">
        <p class="eyebrow">${escapeHtml(product.category)}</p>
        <h2>${escapeHtml(product.name)}</h2>
        <p>${escapeHtml(product.description)}</p>
        <strong class="detail-price">${money(product.price)}</strong>
        <p class="detail-stock">${product.stock > 0 && product.status === "active" ? `${product.stock} unidades disponíveis` : "Indisponível no momento"}</p>
        ${product.stock > 0 && product.status === "active" && state.user?.role === "client" ? `<button class="button button-dark" type="button" data-add="${escapeHtml(product.id)}">Adicionar à sacola <span>→</span></button>` : ""}
      </div>
    </div>`;
  elements.productDialog.showModal();
  elements.productDialog.querySelector("[data-close]")?.focus({ preventScroll: true });
  requestAnimationFrame(() => {
    window.scrollTo({ top: state.productDialogScrollY, behavior: "instant" });
  });
}

elements.productDialog.addEventListener("close", () => {
  const scrollY = state.productDialogScrollY;
  const opener = state.productDialogOpener;
  state.productDialogScrollY = null;
  state.productDialogOpener = null;
  requestAnimationFrame(() => {
    opener?.focus({ preventScroll: true });
    if (scrollY !== null) window.scrollTo({ top: scrollY, behavior: "instant" });
  });
});

async function switchView(viewName) {
  if (viewName === "orders" && state.user?.role !== "client") {
    elements.loginDialog.showModal();
    return;
  }
  if (viewName === "manage" && state.user?.role !== "seller") {
    elements.loginDialog.showModal();
    return;
  }
  if (viewName === "profile" && !state.user) {
    elements.loginDialog.showModal();
    return;
  }
  const previousView = state.activeView;
  if (viewName !== previousView) {
    state.scrollPositions[previousView] = window.scrollY;
  }
  state.activeView = viewName;
  document.querySelectorAll(".nav-link").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewName);
    if (button.dataset.view === viewName) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  document.querySelectorAll(".view").forEach((view) => {
    const active = view.id === `${viewName}-view`;
    view.hidden = !active;
    view.classList.toggle("active", active);
  });
  if (viewName === "orders") await loadOrders();
  if (viewName === "manage") {
    await loadCategories();
    await reloadSellerAndCatalog();
  }
  if (viewName === "profile") await loadProfile();
  if (viewName !== previousView) {
    window.scrollTo({
      top: state.scrollPositions[viewName] || 0,
      behavior: "smooth",
    });
  }
}

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => run(
    () => switchView(button.dataset.view),
    button,
    "Carregando...",
  ));
});
document.querySelectorAll("[data-close]").forEach((button) => {
  button.addEventListener("click", () => document.getElementById(button.dataset.close).close());
});
document.querySelector("#open-cart").addEventListener("click", () => elements.cartDialog.showModal());

elements.search.addEventListener("input", () => {
  updateClearCatalogFiltersVisibility();
  clearTimeout(elements.searchTimer);
  elements.searchTimer = setTimeout(() => run(loadProducts), 220);
});
elements.categoryFilter.addEventListener("change", () => {
  updateClearCatalogFiltersVisibility();
  run(loadProducts);
});
elements.sellerFilter.addEventListener("change", () => {
  updateClearCatalogFiltersVisibility();
  run(loadProducts);
});
elements.clearCatalogFilters.addEventListener("click", () => {
  clearTimeout(elements.searchTimer);
  elements.search.value = "";
  elements.categoryFilter.value = "";
  elements.sellerFilter.value = "";
  updateClearCatalogFiltersVisibility();
  elements.search.focus({ preventScroll: true });
  run(loadProducts);
});

elements.grid.addEventListener("click", (event) => {
  const addButton = event.target.closest("[data-add]");
  if (addButton) {
    run(() => addToCart(addButton.dataset.add), addButton, "Adicionando...");
    return;
  }
  const productCard = event.target.closest(".product-card[data-product-id]");
  if (productCard) showProductDetails(productCard.dataset.productId, productCard);
});
elements.grid.addEventListener("keydown", (event) => {
  const productCard = event.target.closest(".product-card[data-product-id]");
  if (
    !productCard
    || event.target !== productCard
    || (event.key !== "Enter" && event.key !== " ")
  ) return;
  event.preventDefault();
  showProductDetails(productCard.dataset.productId, productCard);
});

elements.productDetail.addEventListener("click", (event) => {
  const addButton = event.target.closest("[data-add]");
  if (!addButton) return;
  run(async () => {
    await addToCart(addButton.dataset.add);
    elements.productDialog.close();
  }, addButton, "Adicionando...");
});

elements.cartItems.addEventListener("click", (event) => {
  const removeButton = event.target.closest("[data-remove]");
  const quantityButton = event.target.closest("[data-quantity]");
  if (removeButton) {
    run(async () => {
      await api(`/carts/items/${removeButton.dataset.remove}`, { method: "DELETE" });
      await loadCart();
    }, removeButton, "Removendo...");
  }
  if (quantityButton) {
    const quantity = Number(quantityButton.dataset.value);
    run(async () => {
      if (quantity <= 0) {
        await api(`/carts/items/${quantityButton.dataset.quantity}`, { method: "DELETE" });
      } else {
        await api(`/carts/items/${quantityButton.dataset.quantity}`, {
          method: "PUT",
          body: JSON.stringify({ quantity }),
        });
      }
      await loadCart();
    }, quantityButton, "Atualizando...");
  }
});

elements.checkout.addEventListener("click", (event) => {
  if (!window.confirm("Confirmar este pedido? O estoque será atualizado.")) return;
  run(async () => {
  const order = await api("/orders", { method: "POST" });
  elements.cartDialog.close();
  await loadCart();
  await switchView("orders");
  showNotice(`Pedido ${order.id.slice(0, 8).toUpperCase()} confirmado. Obrigado por escolher a Linx!`);
  }, event.currentTarget, "Finalizando...");
});

elements.ordersList.addEventListener("click", (event) => {
  const cancelButton = event.target.closest("[data-cancel-order]");
  if (!cancelButton) return;
  if (!window.confirm("Deseja cancelar este pedido? O estoque será devolvido.")) return;
  run(async () => {
    await api(`/orders/${cancelButton.dataset.cancelOrder}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: "cancelled" }),
    });
    await loadOrders();
    await loadProducts();
    showNotice("Pedido cancelado e estoque devolvido.");
  }, cancelButton, "Cancelando...");
});

elements.productForm.addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const body = {
      name: document.querySelector("#product-name").value,
      description: document.querySelector("#product-description").value,
      category: elements.categorySelect.value,
      price: document.querySelector("#product-price").value,
      stock: Number(document.querySelector("#product-stock").value),
      image_url: document.querySelector("#product-image").value || null,
      status: document.querySelector("#product-status").value,
    };
    const path = state.editingProductId
      ? `/products/${state.editingProductId}`
      : "/products";
    await api(path, {
      method: state.editingProductId ? "PUT" : "POST",
      body: JSON.stringify(body),
    });
    resetProductForm();
    await reloadSellerAndCatalog();
    showNotice("Produto salvo com sucesso.");
  }, event.submitter || elements.productSubmit, "Salvando...");
});

elements.cancelEdit.addEventListener("click", resetProductForm);

elements.productAdminList.addEventListener("click", (event) => {
  const editButton = event.target.closest("[data-edit-product]");
  const deleteButton = event.target.closest("[data-delete-product]");
  if (editButton) editProduct(editButton.dataset.editProduct);
  if (deleteButton && window.confirm("Excluir este produto? Esta ação não pode ser desfeita.")) run(async () => {
    await api(`/products/${deleteButton.dataset.deleteProduct}`, { method: "DELETE" });
    await reloadSellerAndCatalog();
    showNotice("Produto excluído.");
  }, deleteButton, "Excluindo...");
});

elements.categoryForm.addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const path = state.editingCategoryId
      ? `/categories/${state.editingCategoryId}`
      : "/categories";
    await api(path, {
      method: state.editingCategoryId ? "PUT" : "POST",
      body: JSON.stringify({
        name: document.querySelector("#category-name").value,
        description: document.querySelector("#category-description").value,
      }),
    });
    resetCategoryForm();
    await loadCategories();
    await reloadSellerAndCatalog();
    showNotice("Categoria salva com sucesso.");
  }, event.submitter || elements.categorySubmit, "Salvando...");
});

elements.categoryCancel.addEventListener("click", resetCategoryForm);

elements.categoryAdminList.addEventListener("click", (event) => {
  const editButton = event.target.closest("[data-edit-category]");
  const deleteButton = event.target.closest("[data-delete-category]");
  if (editButton) editCategory(editButton.dataset.editCategory);
  if (!deleteButton || !window.confirm("Excluir esta categoria? Esta ação não pode ser desfeita.")) return;
  run(async () => {
    await api(`/categories/${deleteButton.dataset.deleteCategory}`, { method: "DELETE" });
    await loadCategories();
    await reloadSellerAndCatalog();
    showNotice("Categoria excluída.");
  }, deleteButton, "Excluindo...");
});

function renderProfile() {
  if (!state.user) return;
  const isSeller = state.user.role === "seller";
  document.querySelector("#profile-full-name").value = state.user.full_name;
  document.querySelector("#profile-email").value = state.user.email;
  document.querySelector("#profile-role").textContent = isSeller ? "Vendedor" : "Cliente";
  document.querySelector("#profile-created-at").textContent =
    new Date(state.user.created_at).toLocaleDateString("pt-BR");
  elements.sellerProfileCard.hidden = !isSeller;
  elements.clientProfileCard.hidden = isSeller;
  if (isSeller) {
    document.querySelector("#seller-store-name").value = state.user.store_name || "";
    document.querySelector("#seller-store-description").value =
      state.user.store_description || "";
    document.querySelector("#seller-business-phone").value =
      state.user.business_phone || "";
  }
}

async function loadProfile() {
  if (!state.user) return;
  renderProfile();
  if (state.user.role === "seller") {
    const firstPage = await api("/products/mine?limit=100&offset=0");
    let activeCount = firstPage.items.filter((product) => product.status === "active").length;
    for (let offset = 100; offset < firstPage.total; offset += 100) {
      const page = await api(`/products/mine?limit=100&offset=${offset}`);
      activeCount += page.items.filter((product) => product.status === "active").length;
    }
    document.querySelector("#seller-product-count").textContent =
      String(firstPage.total);
    document.querySelector("#seller-active-count").textContent =
      String(activeCount);
    return;
  }
  const [orders, cart] = await Promise.all([
    api("/orders?limit=100"),
    api("/carts"),
  ]);
  state.cart = cart;
  renderCart();
  document.querySelector("#client-order-count").textContent =
    String(orders.total);
  document.querySelector("#client-cart-count").textContent =
    String(cart.total_items);
}

function applyUser(user) {
  state.user = user;
  const signedIn = Boolean(user);
  const isClient = user?.role === "client";
  const isSeller = user?.role === "seller";
  elements.accountName.hidden = !signedIn;
  elements.accountName.textContent = signedIn
    ? `${user.full_name} · ${isSeller ? "Vendedor" : "Cliente"}`
    : "";
  elements.loginOpen.hidden = signedIn;
  elements.registerOpen.hidden = signedIn;
  elements.logoutButton.hidden = !signedIn;
  elements.profileNav.hidden = !signedIn;
  elements.ordersNav.hidden = !isClient;
  elements.manageNav.hidden = !isSeller;
  elements.cartButton.hidden = !isClient;
  if (!isSeller) state.sellerProducts = [];
  if (state.activeView === "orders" && !isClient) {
    void switchView("catalog");
  }
  if (state.activeView === "manage" && !isSeller) {
    void switchView("catalog");
  }
}

async function logout() {
  await api("/auth/logout", { method: "POST" });
  applyUser(null);
  state.cart = null;
  await loadCategories();
  await Promise.all([loadProducts(), loadCart()]);
  if (state.activeView !== "catalog") await switchView("catalog");
  showNotice("Você saiu da sua conta.");
}

elements.loginOpen.addEventListener("click", () => elements.loginDialog.showModal());
elements.registerOpen.addEventListener("click", () => elements.registerDialog.showModal());
elements.logoutButton.addEventListener("click", () => run(logout));
document.querySelector("#profile-logout").addEventListener("click", () => run(logout));
document.querySelector("#profile-open-cart").addEventListener("click", () => {
  elements.cartDialog.showModal();
});
document.querySelectorAll("[data-profile-view]").forEach((button) => {
  button.addEventListener("click", () => run(() => switchView(button.dataset.profileView)));
});

elements.profileForm.addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const user = await api("/auth/profile", {
      method: "PATCH",
      body: JSON.stringify({
        full_name: document.querySelector("#profile-full-name").value,
        email: document.querySelector("#profile-email").value,
      }),
    });
    applyUser(user);
    renderProfile();
    showNotice("Seus dados pessoais foram atualizados.");
  }, event.submitter || elements.profileForm.querySelector('[type="submit"]'), "Salvando...");
});

elements.sellerProfileForm.addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const user = await api("/auth/seller-profile", {
      method: "PATCH",
      body: JSON.stringify({
        store_name: document.querySelector("#seller-store-name").value,
        store_description: document.querySelector("#seller-store-description").value,
        business_phone: document.querySelector("#seller-business-phone").value || null,
      }),
    });
    applyUser(user);
    renderProfile();
    await loadSellers();
    showNotice("Os dados da sua loja foram atualizados.");
  }, event.submitter || elements.sellerProfileForm.querySelector('[type="submit"]'), "Salvando...");
});

elements.passwordForm.addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const formData = new FormData(elements.passwordForm);
    if (formData.get("new_password") !== formData.get("confirm_password")) {
      showNotice("A confirmação da nova senha não corresponde.", true);
      return;
    }
    await api("/auth/password", {
      method: "POST",
      body: JSON.stringify({
        current_password: formData.get("current_password"),
        new_password: formData.get("new_password"),
      }),
    });
    elements.passwordForm.reset();
    showNotice("Senha alterada com segurança.");
  }, event.submitter || elements.passwordForm.querySelector('[type="submit"]'), "Atualizando...");
});

function updateRegistrationRole() {
  const role = elements.registerForm.querySelector('input[name="role"]:checked').value;
  const isSeller = role === "seller";
  elements.sellerRegistrationFields.hidden = !isSeller;
  elements.sellerRegistrationFields
    .querySelectorAll("input, textarea")
    .forEach((field) => {
      field.disabled = !isSeller;
      field.required = isSeller && field.id !== "register-business-phone";
    });
  elements.registerSubmit.textContent = isSeller
    ? "Criar conta de vendedor"
    : "Criar conta de cliente";
  elements.registerForm.querySelectorAll(".account-type-card").forEach((card) => {
    card.classList.toggle(
      "selected",
      card.querySelector('input[name="role"]').checked,
    );
  });
}

elements.registerForm.querySelectorAll('input[name="role"]').forEach((input) => {
  input.addEventListener("change", updateRegistrationRole);
});
updateRegistrationRole();

elements.loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const formData = new FormData(elements.loginForm);
    const user = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: formData.get("email"),
        password: formData.get("password"),
      }),
    });
    applyUser(user);
    elements.loginDialog.close();
    elements.loginForm.reset();
    await loadCategories();
    await Promise.all([loadProducts(), loadCart()]);
    showNotice(`Boas-vindas à Linx, ${user.full_name}.`);
  }, event.submitter || elements.loginForm.querySelector('[type="submit"]'), "Entrando...");
});

elements.registerForm.addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const formData = new FormData(elements.registerForm);
    const role = formData.get("role");
    const password = formData.get("password");
    if (password !== formData.get("confirm_password")) {
      showNotice("A confirmação da senha não corresponde.", true);
      return;
    }
    const credentials = {
      full_name: formData.get("full_name"),
      email: formData.get("email"),
      password,
      role,
    };
    if (role === "seller") {
      credentials.store_name = formData.get("store_name");
      credentials.store_description = formData.get("store_description");
      credentials.business_phone = formData.get("business_phone") || null;
    }
    await api("/auth/register", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
    const user = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: credentials.email,
        password: credentials.password,
      }),
    });
    applyUser(user);
    elements.registerDialog.close();
    elements.registerForm.reset();
    updateRegistrationRole();
    await loadCategories();
    await Promise.all([loadProducts(), loadCart(), loadSellers()]);
    showNotice(`Conta criada. Boas-vindas à Linx, ${user.full_name}.`);
  }, event.submitter || elements.registerSubmit, "Criando conta...");
});

async function initialize() {
  try {
    try {
      applyUser(await api("/auth/me"));
    } catch (error) {
      if (error.status !== 401) throw error;
      applyUser(null);
    }
    await loadCategories();
    await Promise.all([loadProducts(), loadCart(), loadSellers()]);
  } catch (error) {
    showNotice(`Não foi possível carregar a loja: ${error.message}`, true);
  }
}

initialize();
