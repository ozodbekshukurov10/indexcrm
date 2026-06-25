import { create } from "zustand";
import { persist } from "zustand/middleware";

import { Product } from "@/services/api/types";

export type CartItem = {
  product: Product;
  quantity: number;
  price: number;
  discount: number;
};

type CartState = {
  items: CartItem[];
  addProduct: (product: Product, quantity?: number) => void;
  setQuantity: (productId: string, quantity: number) => void;
  setDiscount: (productId: string, discount: number) => void;
  removeItem: (productId: string) => void;
  clearCart: () => void;
  getSubtotal: () => number;
  getTotal: () => number;
};

function toMoney(value: number) {
  return Math.round(value * 100) / 100;
}

function lineTotal(item: CartItem) {
  return Math.max(0, toMoney(item.quantity * item.price - item.discount));
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      addProduct: (product, quantity = 1) => {
        set((state) => {
          const existing = state.items.find((item) => item.product.id === product.id);
          if (existing) {
            return {
              items: state.items.map((item) =>
                item.product.id === product.id
                  ? { ...item, quantity: item.quantity + quantity }
                  : item,
              ),
            };
          }
          return {
            items: [
              ...state.items,
              {
                product,
                quantity,
                price: Number(product.selling_price),
                discount: 0,
              },
            ],
          };
        });
      },
      setQuantity: (productId, quantity) => {
        if (quantity <= 0) {
          get().removeItem(productId);
          return;
        }
        set((state) => ({
          items: state.items.map((item) =>
            item.product.id === productId ? { ...item, quantity } : item,
          ),
        }));
      },
      setDiscount: (productId, discount) => {
        set((state) => ({
          items: state.items.map((item) =>
            item.product.id === productId
              ? { ...item, discount: Math.max(0, discount) }
              : item,
          ),
        }));
      },
      removeItem: (productId) => {
        set((state) => ({
          items: state.items.filter((item) => item.product.id !== productId),
        }));
      },
      clearCart: () => set({ items: [] }),
      getSubtotal: () =>
        toMoney(
          get().items.reduce((total, item) => total + item.quantity * item.price, 0),
        ),
      getTotal: () =>
        toMoney(get().items.reduce((total, item) => total + lineTotal(item), 0)),
    }),
    {
      name: "index-pos-cart",
    },
  ),
);

export function getCartLineTotal(item: CartItem) {
  return lineTotal(item);
}
