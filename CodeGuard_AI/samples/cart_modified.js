/* Basket utilities - renamed and partly rewritten */
function newBasket() {
  return { lines: [], promo: null };
}

function put(basket, label, cost, count) {
  const found = basket.lines.find((line) => line.label === label);
  if (found) {
    found.count += count;
  } else {
    basket.lines.push({ label: label, cost: cost, count: count });
  }
  return basket;
}

function grandTotal(basket) {
  let acc = 0;
  for (const line of basket.lines) {
    acc += line.cost * line.count;
  }
  if (basket.promo === "HALF") {
    acc = acc / 2;
  }
  return acc;
}

const basket = newBasket();
put(basket, "pen", 1.5, 4);
put(basket, "book", 12, 1);
console.log(grandTotal(basket));
