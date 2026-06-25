export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type Product = {
  id: string;
  category: string;
  name: string;
  sku: string;
  barcode: string;
  category_name: string;
  brand: string | null;
  brand_name: string | null;
  cost_price: string;
  selling_price: string;
  min_price: string;
  unit: string;
  unit_short_name: string;
  image: string | null;
  is_active: boolean;
  has_expiry_date: boolean;
  barcodes?: Array<{
    id: string;
    code: string;
    barcode_type: string;
  }>;
};

export type Category = {
  id: string;
  name: string;
  slug: string;
  parent: string | null;
  parent_name: string | null;
  is_active: boolean;
};

export type Brand = {
  id: string;
  name: string;
  description: string;
};

export type Unit = {
  id: string;
  name: string;
  short_name: string;
};

export type Stock = {
  id: string;
  warehouse: string;
  warehouse_name: string;
  product: string;
  product_name: string;
  product_sku: string;
  quantity: string;
  reserved_quantity: string;
  available_quantity: string;
  low_stock_limit: string;
  is_low_stock: boolean;
  updated_at: string;
};

export type Branch = {
  id: string;
  store: string;
  store_name: string;
  name: string;
  address: string;
  phone: string;
  manager: string | null;
  is_active: boolean;
};

export type CashDesk = {
  id: string;
  branch: string;
  branch_name: string;
  name: string;
  code: string;
  is_active: boolean;
};

export type Warehouse = {
  id: string;
  branch: string;
  branch_name: string;
  name: string;
  is_active: boolean;
};

export type Customer = {
  id: string;
  full_name: string;
  phone: string;
  extra_phone: string;
  address: string;
  balance: string;
  bonus_balance: string;
  is_active: boolean;
  notes: string;
};

export type Supplier = {
  id: string;
  company_name: string;
  full_name: string;
  phone: string;
  extra_phone: string;
  email: string;
  address: string;
  inn_or_tax_number: string;
  notes: string;
  balance: string;
  is_active: boolean;
};

export type SalePaymentMethod = "CASH" | "CARD" | "CLICK" | "PAYME" | "DEBT" | "MIXED";

export type SalePayload = {
  branch: string;
  warehouse: string;
  idempotency_key?: string;
  customer?: string | null;
  discount_amount?: string;
  tax_amount?: string;
  note?: string;
  items: Array<{
    product: string;
    quantity: string;
    price: string;
    discount: string;
  }>;
  payments: Array<{
    payment_method: SalePaymentMethod;
    amount: string;
    note?: string;
  }>;
};

export type Sale = {
  id: string;
  branch: string;
  branch_name: string;
  warehouse: string;
  warehouse_name: string;
  cashier: string;
  cashier_email: string;
  customer: string | null;
  customer_name: string | null;
  receipt_number: string;
  sale_date: string;
  status: "DRAFT" | "COMPLETED" | "CANCELLED" | "REFUNDED";
  subtotal: string;
  discount_amount: string;
  tax_amount: string;
  total_amount: string;
  paid_amount: string;
  remaining_amount: string;
  items: Array<{
    id: string;
    product: string;
    product_name: string;
    product_sku: string;
    quantity: string;
    price: string;
    discount: string;
    total_price: string;
  }>;
  payments: Array<{
    id: string;
    payment_method: SalePaymentMethod;
    amount: string;
    note: string;
    paid_at: string;
  }>;
};

export type ReceiptData = {
  receipt_number: string;
  sale_date: string;
  branch: Record<string, unknown>;
  warehouse: Record<string, unknown>;
  cashier: Record<string, unknown>;
  customer: Record<string, unknown> | null;
  items: Array<Record<string, unknown>>;
  payments: Array<Record<string, unknown>>;
  totals: Record<string, unknown>;
  qr_code: string | null;
  fiscal: Record<string, unknown>;
};

export type CashierShift = {
  id: string;
  cashier: string;
  cashier_email: string;
  branch: string;
  branch_name: string;
  opened_at: string;
  closed_at: string | null;
  opening_balance: string;
  closing_balance: string;
  expected_balance: string;
  difference: string;
};

export type CashBox = {
  id: string;
  branch: string;
  branch_name: string;
  name: string;
  current_balance: string;
  is_active: boolean;
};

export type Expense = {
  id: string;
  cashbox: string;
  cashbox_name: string;
  category_name: string;
  amount: string;
  note: string;
  expense_date: string;
};

export type UserProfile = {
  id: string;
  user: string;
  user_email: string;
  avatar: string | null;
  employee_code: string;
  position: string;
  branch: string | null;
  branch_name: string | null;
  language: string;
  timezone: string;
  theme: string;
  employee_status: string;
};

export type UserAccount = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  role: string;
  is_active: boolean;
  profile: UserProfile | null;
};

export type AIChatMessage = {
  id?: string;
  session?: string;
  role: "user" | "assistant" | "system";
  content: string;
  intent?: string;
  confidence?: number;
  entities?: Record<string, unknown>;
  source?: string;
  created_at?: string;
};

export type AIChatResponse = {
  answer: string;
  intent: string;
  confidence: number;
  entities: Record<string, unknown>;
  source: string;
  session_id: string | number | null;
  suggestions?: string[];
  clarification_required?: boolean;
  display_type?: string;
  items?: unknown;
};

export type AIChatSession = {
  id: string;
  title: string;
  is_active?: boolean;
  created_at: string;
  updated_at: string;
  message_count?: number;
  last_message_preview?: string;
};

export type AIChatSessionDetail = AIChatSession & {
  messages: AIChatMessage[];
};
