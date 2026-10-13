import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Search, Filter, FileText, Download, Trash2, ExternalLink, RefreshCcw } from "lucide-react"
import { api, type DocumentListItem } from "@/lib/api"
import {
  Card, CardHeader, CardTitle, CardContent, Button, Input, Select, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
  EmptyState, Skeleton,
} from "@/components/ui"
import { formatCurrency, formatDate, formatFileSize, getStatusColor, getReviewBadge, cn } from "@/lib/utils"
import { toast } from "sonner"

const CATEGORIES = [
  "", "Office Supplies", "Software & Subscriptions", "Travel", "Food & Meals",
  "Utilities", "Marketing", "Professional Services", "Equipment", "Rent", "Insurance", "Other",
]

export function InvoicesPage() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [category, setCategory] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const fetchDocuments = () => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (search) params.search = search
    if (category) params.category = category
    if (statusFilter) params.status = statusFilter

    api.listDocuments(params)
      .then(setDocuments)
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchDocuments() }, [category, statusFilter])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    fetchDocuments()
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this document and all extracted data?")) return
    try {
      await api.deleteDocument(id)
      toast.success("Document deleted")
      fetchDocuments()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleRetry = async (id: string) => {
    try {
      await api.retryDocument(id)
      toast.success("Retry started")
      fetchDocuments()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const exportSelected = (format: "csv" | "xlsx") => {
    const params: Record<string, string> = {}
    if (selected.size > 0) {
      // Get invoice IDs for selected documents — we'll just pass document ids for now
      // The API expects invoice_ids but for simplicity we use the document IDs
      // In a full implementation, we'd map document IDs to invoice IDs
    }
    if (category) params.category = category

    if (format === "csv") api.exportCsv(params)
    else api.exportXlsx(params)
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Search & Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-3">
            <form onSubmit={handleSearch} className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[hsl(var(--muted-foreground))]" />
                <Input
                  placeholder="Search by vendor or invoice number..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="pl-10"
                  aria-label="Search invoices"
                />
              </div>
            </form>
            <Select value={category} onChange={e => setCategory(e.target.value)} className="w-48" aria-label="Filter by category">
              <option value="">All Categories</option>
              {CATEGORIES.filter(Boolean).map(c => <option key={c} value={c}>{c}</option>)}
            </Select>
            <Select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="w-40" aria-label="Filter by status">
              <option value="">All Statuses</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
              <option value="uploaded">Uploaded</option>
            </Select>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => exportSelected("csv")} className="gap-1.5">
                <Download className="h-3.5 w-3.5" /> CSV
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportSelected("xlsx")} className="gap-1.5">
                <Download className="h-3.5 w-3.5" /> Excel
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 space-y-3">
              {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-12" />)}
            </div>
          ) : documents.length === 0 ? (
            <EmptyState
              icon={<FileText className="h-12 w-12" />}
              title="No invoices found"
              description={search || category || statusFilter
                ? "Try adjusting your search or filters"
                : "Upload some documents to get started"
              }
              action={
                <Link to="/upload">
                  <Button className="gap-2"><FileText className="h-4 w-4" /> Upload Documents</Button>
                </Link>
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8">
                    <input
                      type="checkbox"
                      onChange={e => {
                        if (e.target.checked) setSelected(new Set(documents.map(d => d.id)))
                        else setSelected(new Set())
                      }}
                      checked={selected.size === documents.length && documents.length > 0}
                      aria-label="Select all"
                      className="rounded"
                    />
                  </TableHead>
                  <TableHead>Document</TableHead>
                  <TableHead>Vendor</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Review</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="w-20">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map(doc => {
                  const reviewBadge = doc.review_status ? getReviewBadge(doc.review_status) : null
                  return (
                    <TableRow key={doc.id} className={cn(selected.has(doc.id) && "bg-[hsl(var(--accent))]")}>
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selected.has(doc.id)}
                          onChange={() => toggleSelect(doc.id)}
                          aria-label={`Select ${doc.original_filename}`}
                          className="rounded"
                        />
                      </TableCell>
                      <TableCell>
                        <Link
                          to={`/invoices/${doc.id}`}
                          className="font-medium hover:text-[hsl(var(--primary))] transition-colors flex items-center gap-1.5"
                        >
                          <FileText className="h-3.5 w-3.5 shrink-0" />
                          <span className="truncate max-w-[180px]">{doc.original_filename}</span>
                        </Link>
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">
                          {formatFileSize(doc.file_size)}
                        </span>
                      </TableCell>
                      <TableCell>{doc.vendor_name || "—"}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {doc.total_amount != null ? formatCurrency(doc.total_amount, doc.currency || "USD") : "—"}
                      </TableCell>
                      <TableCell>
                        {doc.expense_category ? (
                          <Badge variant="secondary" className="text-xs">{doc.expense_category}</Badge>
                        ) : "—"}
                      </TableCell>
                      <TableCell>
                        <span className={cn("text-xs font-medium capitalize", getStatusColor(doc.status))}>
                          ● {doc.status}
                        </span>
                      </TableCell>
                      <TableCell>
                        {reviewBadge ? (
                          <Badge className={cn("text-[10px] border", reviewBadge.className)}>
                            {reviewBadge.label}
                          </Badge>
                        ) : "—"}
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {formatDate(doc.upload_time)}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Link to={`/invoices/${doc.id}`}>
                            <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="View details">
                              <ExternalLink className="h-3.5 w-3.5" />
                            </Button>
                          </Link>
                          {doc.status === "failed" && (
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleRetry(doc.id)} aria-label="Retry">
                              <RefreshCcw className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500 hover:text-red-600" onClick={() => handleDelete(doc.id)} aria-label="Delete">
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
