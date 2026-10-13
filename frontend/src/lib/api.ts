/**
 * InvoicePilot AI — API client
 *
 * All backend communication goes through this module.
 */

const API_BASE = "/api"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `Request failed: ${res.status}`)
  }

  // Handle empty responses (204 No Content, etc.)
  const text = await res.text()
  if (!text) return {} as T
  return JSON.parse(text)
}

// ── Types ──

export interface DocumentListItem {
  id: string
  original_filename: string
  file_type: string
  file_size: number
  status: string
  upload_time: string
  vendor_name?: string | null
  total_amount?: number | null
  currency?: string | null
  expense_category?: string | null
  review_status?: string | null
}

export interface LineItem {
  id: string
  description?: string | null
  quantity?: number | null
  unit_price?: number | null
  tax_amount?: number | null
  line_total?: number | null
}

export interface InvoiceData {
  id: string
  document_id: string
  vendor_name?: string | null
  vendor_address?: string | null
  invoice_number?: string | null
  invoice_date?: string | null
  due_date?: string | null
  currency?: string | null
  subtotal?: number | null
  tax_amount?: number | null
  discount?: number | null
  total_amount?: number | null
  amount_paid?: number | null
  outstanding_amount?: number | null
  payment_status?: string | null
  expense_category?: string | null
  document_type?: string | null
  confidence?: number | null
  review_status: string
  validation_notes?: string | null
  user_edited: boolean
  line_items: LineItem[]
  created_at: string
  updated_at: string
}

export interface DocumentDetail {
  id: string
  original_filename: string
  file_type: string
  file_size: number
  status: string
  error_message?: string | null
  upload_time: string
  processed_time?: string | null
  invoice?: InvoiceData | null
  created_at: string
  updated_at: string
}

export interface CurrencySummary {
  currency: string
  total_amount: number
  outstanding_amount: number
  count: number
}

export interface CategoryBreakdown {
  category: string
  total: number
  count: number
  currency: string
}

export interface MonthlyTrend {
  month: string
  total: number
  count: number
  currency: string
}

export interface DashboardData {
  total_documents: number
  processed_count: number
  review_count: number
  failed_count: number
  currency_summaries: CurrencySummary[]
  category_breakdown: CategoryBreakdown[]
  monthly_trend: MonthlyTrend[]
  recent_documents: DocumentListItem[]
}

export interface AIHealth {
  status: string
  model: string
  ollama_url: string
  message?: string | null
}

export interface ExpenseGroup {
  category: string
  currency: string
  total: number
  count: number
  invoices: Array<{
    id: string
    vendor_name?: string
    invoice_number?: string
    invoice_date?: string
    total_amount?: number
  }>
}

export interface ExpenseReport {
  groups: ExpenseGroup[]
  total_invoices: number
}

// ── API Functions ──

export const api = {
  // Health
  health: () => request<{ status: string }>("/health"),
  aiHealth: () => request<AIHealth>("/health/ai"),

  // Dashboard
  dashboard: (months = 12) => request<DashboardData>(`/dashboard/summary?months=${months}`),

  // Documents
  listDocuments: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : ""
    return request<DocumentListItem[]>(`/documents${qs}`)
  },
  getDocument: (id: string) => request<DocumentDetail>(`/documents/${id}`),
  uploadDocuments: async (files: File[]) => {
    const form = new FormData()
    files.forEach(f => form.append("files", f))
    const res = await fetch(`${API_BASE}/documents/upload`, { method: "POST", body: form })
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(error.detail || "Upload failed")
    }
    return res.json() as Promise<DocumentDetail[]>
  },
  processDocument: (id: string) => request<{ message: string }>(`/documents/${id}/process`, { method: "POST" }),
  retryDocument: (id: string) => request<{ message: string }>(`/documents/${id}/retry`, { method: "POST" }),
  updateDocument: (id: string, data: Partial<InvoiceData>) =>
    request<DocumentDetail>(`/documents/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteDocument: (id: string) => request<{ message: string }>(`/documents/${id}`, { method: "DELETE" }),

  // Reports
  expenseReport: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : ""
    return request<ExpenseReport>(`/reports/expenses${qs}`)
  },

  // Exports
  exportCsv: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : ""
    return window.open(`${API_BASE}/exports/csv${qs}`, "_blank")
  },
  exportXlsx: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : ""
    return window.open(`${API_BASE}/exports/xlsx${qs}`, "_blank")
  },
}
