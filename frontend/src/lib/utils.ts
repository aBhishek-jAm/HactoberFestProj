import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount: number | null | undefined, currency: string = "USD"): string {
  if (amount == null) return "—"
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,
      minimumFractionDigits: 2,
    }).format(amount)
  } catch {
    return `${currency} ${amount.toFixed(2)}`
  }
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—"
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })
  } catch {
    return dateStr
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function getStatusColor(status: string): string {
  switch (status) {
    case "completed": return "text-emerald-500"
    case "processing": return "text-blue-500"
    case "failed": return "text-red-500"
    case "uploaded": return "text-amber-500"
    default: return "text-gray-500"
  }
}

export function getReviewBadge(status: string): { label: string; className: string } {
  switch (status) {
    case "reviewed":
      return { label: "Reviewed", className: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" }
    case "flagged":
      return { label: "Flagged", className: "bg-red-500/10 text-red-500 border-red-500/20" }
    case "pending":
    default:
      return { label: "Pending Review", className: "bg-amber-500/10 text-amber-500 border-amber-500/20" }
  }
}
