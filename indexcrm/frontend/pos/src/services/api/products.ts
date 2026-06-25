import { apiRequest } from "./client";
import { Brand, Category, PaginatedResponse, Product, Unit } from "./types";

type ProductSearchParams = {
  search?: string;
  ordering?: string;
  isActive?: boolean;
};

export type ProductPayload = {
  category: string;
  brand?: string | null;
  name: string;
  description?: string;
  barcode?: string | null;
  sku?: string | null;
  cost_price: string;
  selling_price: string;
  min_price?: string;
  unit: string;
  is_active: boolean;
  has_expiry_date?: boolean;
};

export function searchProducts(params: ProductSearchParams) {
  return apiRequest<PaginatedResponse<Product>>(
    "/products/",
    {},
    {
      search: params.search,
      ordering: params.ordering ?? "name",
      is_active: params.isActive === false ? "false" : "true",
    },
  );
}

export function findProductByScan(code: string) {
  return searchProducts({ search: code, ordering: "name", isActive: true });
}

function normalizeCode(value: string) {
  return value.trim().toLowerCase();
}

export async function findProductByBarcode(code: string) {
  const result = await findProductByScan(code);
  const normalizedCode = normalizeCode(code);

  return (
    result.results.find((product) => {
      const productCodes = [
        product.barcode,
        product.sku,
        ...(product.barcodes?.map((barcode) => barcode.code) ?? []),
      ];
      return productCodes.some((productCode) => {
        return productCode && normalizeCode(productCode) === normalizedCode;
      });
    }) ?? null
  );
}

export function listProducts(params: ProductSearchParams = {}) {
  return searchProducts(params);
}

export function createProduct(payload: ProductPayload) {
  return apiRequest<Product>("/products/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProduct(productId: string, payload: ProductPayload) {
  return apiRequest<Product>(`/products/${productId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function listCategories() {
  return apiRequest<PaginatedResponse<Category>>(
    "/categories/",
    {},
    { is_active: "true", ordering: "name" },
  );
}

export function listBrands() {
  return apiRequest<PaginatedResponse<Brand>>(
    "/brands/",
    {},
    { ordering: "name" },
  );
}

export function listUnits() {
  return apiRequest<PaginatedResponse<Unit>>(
    "/units/",
    {},
    { ordering: "name" },
  );
}
