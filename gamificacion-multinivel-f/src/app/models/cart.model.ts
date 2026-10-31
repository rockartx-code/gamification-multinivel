export interface CartItem {
  id: string;
  name: string;
  price: number;
  qty: number;
  note: string;
  img: string;
}

export interface CartUserSummary {
  monthSpendActual: number;
  activeSpendTarget: number;
}

export interface CartData {
  countdownLabel: string;
  shipping: number;
  discountPct: number;
  user: CartUserSummary;
  items: CartItem[];
  suggestedItem: CartItem;
}
