export function formatMoney(value: number | string | null | undefined) {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function toApiMoney(value: number) {
  return value.toFixed(2);
}

export function toApiQuantity(value: number) {
  return value.toFixed(3);
}
