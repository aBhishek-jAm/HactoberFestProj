import { useEffect, useState } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import {
  ArrowLeft, Save, Trash2, RefreshCcw, CheckCircle, AlertTriangle,
  FileText, Calendar, Building2, Hash, CreditCard, Tag, Loader2
} from "lucide-react"
import { api, type DocumentDetail } from "@/lib/api"
import {
  Card, CardHeader, CardTitle, CardContent, Button, Input, Label, Select,
  Badge, Separator, Skeleton, EmptyState, Table, TableHeader, TableBody,
  TableRow, TableHead, TableCell,
} from "@/components/ui"
import { formatCurrency, formatDate, getReviewBadge, cn } from "@/lib/utils"
import { toast } from "sonner"

const CATEGORIES = [
  "Office Supplies", "Software & Subscriptions", "Travel", "Food & Meals",
  "Utilities", "Marketing", "Professional Services", "Equipment", "Rent", "Insurance", "Other",
]

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [doc, setDoc] = useState<DocumentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editData, setEditData] = useState<Record<string, any>>({})

  const fetchDoc = () => {
    if (!id) return
    setLoading(true)
    api.getDocument(id)
      .then(d => {
        setDoc(d)
        if (d.invoice) {
          setEditData({
            vendor_name: d.invoice.vendor_name || "",
            vendor_address: d.invoice.vendor_address || "",
            invoice_number: d.invoice.invoice_number || "",
            invoice_date: d.invoice.invoice_date || "",
            due_date: d.invoice.due_date || "",
            currency: d.invoice.currency || "USD",
            subtotal: d.invoice.subtotal ?? "",
            tax_amount: d.invoice.tax_amount ?? "",
            discount: d.invoice.discount ?? 0,
            total_amount: d.invoice.total_amount ?? "",
            amount_paid: d.invoice.amount_paid ?? "",
            outstanding_amount: d.invoice.outstanding_amount ?? "",
            payment_status: d.invoice.payment_status || "",
            expense_category: d.invoice.expense_category || "",
            document_type: d.invoice.document_type || "invoice",
            review_status: d.invoice.review_status || "pending",
          })
        }
      })
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchDoc() }, [id])

  const handleSave = async () => {
    if (!id || !doc?.invoice) return
    setSaving(true)
    try {
      const update: Record<string, any> = {}
      for (const [key, value] of Object.entries(editData)) {
        if (value === "") {
          update[key] = null
        } else if (["subtotal", "tax_amount", "discount", "total_amount", "amount_paid", "outstanding_amount"].includes(key)) {
          update[key] = value === "" ? null : parseFloat(value)
        } else {
          update[key] = value
        }
      }
      await api.updateDocument(id, update)
      toast.success("Invoice updated successfully")
      fetchDoc()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!id || !confirm("Delete this document and all extracted data?")) return
    try {
      await api.deleteDocument(id)
      toast.success("Document deleted")
      navigate("/invoices")
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleRetry = async () => {
    if (!id) return
    try {
      await api.retryDocument(id)
      toast.success("Retry started — check back shortly")
      setTimeout(fetchDoc, 3000)
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const updateField = (key: string, value: any) => {
    setEditData(prev => ({ ...prev, [key]: value }))
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <Skeleton className="h-10 w-48" />
        <Card><CardContent className="p-6"><Skeleton className="h-64" /></CardContent></Card>
      </div>
    )
  }

  if (!doc) {
    return (
      <EmptyState
        icon={<FileText className="h-12 w-12" />}
        title="Document not found"
        action={<Link to="/invoices"><Button>Back to Invoices</Button></Link>}
      />
    )
  }

  const invoice = doc.invoice
  const validationIssues = invoice?.validation_notes ? JSON.parse(invoice.validation_notes) : []
  const reviewBadge = invoice ? getReviewBadge(invoice.review_status) : null
  const confidence = invoice?.confidence ?? 0

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/invoices">
            <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
          </Link>
          <div>
            <h2 className="text-xl font-bold">{doc.original_filename}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className={cn("text-xs font-medium capitalize", doc.status === "completed" ? "text-emerald-500" : doc.status === "failed" ? "text-red-500" : "text-amber-500")}>
                ● {doc.status}
              </span>
              {reviewBadge && (
                <Badge className={cn("text-[10px] border", reviewBadge.className)}>
                  {reviewBadge.label}
                </Badge>
              )}
              {invoice && (
                <span className="text-xs text-[hsl(var(--muted-foreground))]">
                  Confidence: {(confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {doc.status === "failed" && (
            <Button variant="outline" onClick={handleRetry} className="gap-2">
              <RefreshCcw className="h-4 w-4" /> Retry
            </Button>
          )}
          <Button variant="destructive" size="sm" onClick={handleDelete} className="gap-2">
            <Trash2 className="h-4 w-4" /> Delete
          </Button>
        </div>
      </div>

      {/* Error state */}
      {doc.status === "failed" && doc.error_message && (
        <Card className="border-red-500/30 bg-red-500/5">
          <CardContent className="p-4 flex gap-3">
            <AlertTriangle className="h-5 w-5 text-red-500 shrink-0" />
            <div>
              <p className="font-medium text-red-500">Processing Failed</p>
              <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{doc.error_message}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Validation Issues */}
      {validationIssues.length > 0 && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2 text-amber-600">
              <AlertTriangle className="h-4 w-4" /> Validation Notes ({validationIssues.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {validationIssues.map((issue: any, i: number) => (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className={cn(
                    "text-xs font-mono px-1.5 py-0.5 rounded shrink-0 mt-0.5",
                    issue.severity === "error" ? "bg-red-500/10 text-red-500" :
                    issue.severity === "warning" ? "bg-amber-500/10 text-amber-600" :
                    "bg-blue-500/10 text-blue-500"
                  )}>
                    {issue.severity}
                  </span>
                  <span className="text-[hsl(var(--muted-foreground))]">
                    <span className="font-medium text-[hsl(var(--foreground))]">{issue.field}:</span> {issue.message}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Edit Form */}
      {invoice && (
        <>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5 text-[hsl(var(--primary))]" />
                Invoice Details
              </CardTitle>
              <Button onClick={handleSave} disabled={saving} className="gap-2">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save Changes
              </Button>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="vendor_name">Vendor Name</Label>
                  <Input id="vendor_name" value={editData.vendor_name} onChange={e => updateField("vendor_name", e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="invoice_number">Invoice Number</Label>
                  <Input id="invoice_number" value={editData.invoice_number} onChange={e => updateField("invoice_number", e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="invoice_date">Invoice Date</Label>
                  <Input id="invoice_date" type="date" value={editData.invoice_date} onChange={e => updateField("invoice_date", e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="due_date">Due Date</Label>
                  <Input id="due_date" type="date" value={editData.due_date} onChange={e => updateField("due_date", e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="currency">Currency</Label>
                  <Input id="currency" value={editData.currency} onChange={e => updateField("currency", e.target.value)} className="mt-1" maxLength={3} />
                </div>
                <div>
                  <Label htmlFor="document_type">Document Type</Label>
                  <Select id="document_type" value={editData.document_type} onChange={e => updateField("document_type", e.target.value)} className="mt-1">
                    <option value="invoice">Invoice</option>
                    <option value="receipt">Receipt</option>
                    <option value="credit_note">Credit Note</option>
                    <option value="other">Other</option>
                  </Select>
                </div>
              </div>

              <Separator className="my-6" />

              <h4 className="font-semibold mb-4 flex items-center gap-2">
                <CreditCard className="h-4 w-4 text-[hsl(var(--primary))]" /> Financial Details
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="subtotal">Subtotal</Label>
                  <Input id="subtotal" type="number" step="0.01" value={editData.subtotal} onChange={e => updateField("subtotal", e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="tax_amount">Tax Amount</Label>
                  <Input id="tax_amount" type="number" step="0.01" value={editData.tax_amount} onChange={e => updateField("tax_amount", e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="discount">Discount</Label>
                  <Input id="discount" type="number" step="0.01" value={editData.discount} onChange={e => updateField("discount", e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="total_amount">Total Amount</Label>
                  <Input id="total_amount" type="number" step="0.01" value={editData.total_amount} onChange={e => updateField("total_amount", e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="amount_paid">Amount Paid</Label>
                  <Input id="amount_paid" type="number" step="0.01" value={editData.amount_paid} onChange={e => updateField("amount_paid", e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="outstanding_amount">Outstanding</Label>
                  <Input id="outstanding_amount" type="number" step="0.01" value={editData.outstanding_amount} onChange={e => updateField("outstanding_amount", e.target.value)} className="mt-1" />
                </div>
              </div>

              <Separator className="my-6" />

              <h4 className="font-semibold mb-4 flex items-center gap-2">
                <Tag className="h-4 w-4 text-[hsl(var(--primary))]" /> Classification
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="expense_category">Category</Label>
                  <Select id="expense_category" value={editData.expense_category} onChange={e => updateField("expense_category", e.target.value)} className="mt-1">
                    <option value="">Select category</option>
                    {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </Select>
                </div>
                <div>
                  <Label htmlFor="payment_status">Payment Status</Label>
                  <Select id="payment_status" value={editData.payment_status} onChange={e => updateField("payment_status", e.target.value)} className="mt-1">
                    <option value="">Unknown</option>
                    <option value="paid">Paid</option>
                    <option value="unpaid">Unpaid</option>
                    <option value="partial">Partial</option>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="review_status">Review Status</Label>
                  <Select id="review_status" value={editData.review_status} onChange={e => updateField("review_status", e.target.value)} className="mt-1">
                    <option value="pending">Pending</option>
                    <option value="reviewed">Reviewed</option>
                    <option value="flagged">Flagged</option>
                  </Select>
                </div>
              </div>

              <div className="mt-4">
                <Label htmlFor="vendor_address">Vendor Address</Label>
                <Input id="vendor_address" value={editData.vendor_address} onChange={e => updateField("vendor_address", e.target.value)} className="mt-1" />
              </div>
            </CardContent>
          </Card>

          {/* Line Items */}
          {invoice.line_items.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Hash className="h-5 w-5 text-[hsl(var(--primary))]" />
                  Line Items ({invoice.line_items.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Description</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">Unit Price</TableHead>
                      <TableHead className="text-right">Tax</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {invoice.line_items.map(item => (
                      <TableRow key={item.id}>
                        <TableCell>{item.description || "—"}</TableCell>
                        <TableCell className="text-right font-mono">{item.quantity ?? "—"}</TableCell>
                        <TableCell className="text-right font-mono">
                          {item.unit_price != null ? formatCurrency(item.unit_price, invoice.currency || "USD") : "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {item.tax_amount != null ? formatCurrency(item.tax_amount, invoice.currency || "USD") : "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono font-medium">
                          {item.line_total != null ? formatCurrency(item.line_total, invoice.currency || "USD") : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Processing/Uploaded state */}
      {!invoice && doc.status === "processing" && (
        <Card>
          <CardContent className="p-12 flex flex-col items-center">
            <Loader2 className="h-10 w-10 animate-spin text-[hsl(var(--primary))] mb-4" />
            <p className="font-medium">Processing document...</p>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">This may take a minute depending on your AI model</p>
            <Button variant="outline" size="sm" className="mt-4" onClick={fetchDoc}>Refresh Status</Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
