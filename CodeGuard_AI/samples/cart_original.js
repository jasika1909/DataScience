// Shopping cart helpers
function createCart() {
  return { items: [], coupon: null };
}

function addItem(cart, name, price, qty) {
  const existing = cart.items.find((item) => item.name === name);
  if (existing) {
    existing.qty += qty;
  } else {
    cart.items.push({ name: name, price: price, qty: qty });
  }
  return cart;
}

function subtotal(cart) {
  let sum = 0;
  for (const item of cart.items) {
    sum += item.price * item.qty;
  }
  return sum;
}

function total(cart) {
  const base = subtotal(cart);
  if (cart.coupon === "SAVE10") {
    return base * 0.9;
  }
  return base;
}

const cart = createCart();
addItem(cart, "pen", 1.5, 4);
addItem(cart, "book", 12, 1);
cart.coupon = "SAVE10";
console.log(total(cart));
