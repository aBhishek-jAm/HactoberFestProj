import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import {
  FileText,
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingUp,
  Upload,
} from "lucide-react"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts"
import { api, type DashboardData } from "@/lib/api"
import { StatsCard, Card, CardHeader, CardTitle, CardContent, Badge, Button, Skeleton, EmptyState, Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui"
import { formatCurrency, formatDate, formatFileSize, getStatusColor, getReviewBadge, cn } from "@/lib/utils"

const PIE_COLORS = [
  "#3B82F6", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981",
  "#06B6D4", "#EF4444", "#6366F1", "#F97316", "#14B8A6",
]

export function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.dashboard()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}><CardContent className="p-6"><Skeleton className="h-16" /></CardContent></Card>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card><CardContent className="p-6"><Skeleton className="h-64" /></CardContent></Card>
          <Card><CardContent className="p-6"><Skeleton className="h-64" /></CardContent></Card>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <EmptyState
        icon={<XCircle className="h-12 w-12" />}
        title="Failed to load dashboard"
        description={error}
        action={<Button onClick={() => window.location.reload()}>Retry</Button>}
      />
    )
  }

  if (!data || data.total_documents === 0) {
    return (
      <EmptyState
        icon={<FileText className="h-16 w-16 opacity-30" />}
        title="Welcome to InvoicePilot AI"
        description="Upload your first invoice or receipt to get started. We'll extract key data using AI and organize your expenses."
        action={
          <Link to="/upload">
            <Button className="gap-2"><Upload className="h-4 w-4" /> Upload Documents</Button>
          </Link>
        }
      />
    )
  }

  const primaryCurrency = data.currency_summaries[0]

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Invoices"
          value={data.total_documents}
          subtitle={`${data.processed_count} processed`}
          icon={<FileText className="h-6 w-6" />}
        />
        <StatsCard
          title={`Total Amount${primaryCurrency ? ` (${primaryCurrency.currency})` : ""}`}
          value={primaryCurrency ? formatCurrency(primaryCurrency.total_amount, primaryCurrency.currency) : "—"}
          subtitle={data.currency_summaries.length > 1 ? `${data.currency_summaries.length} currencies` : undefined}
          icon={<TrendingUp className="h-6 w-6" />}
        />
        <StatsCard
          title="Needs Review"
          value={data.review_count}
          icon={<AlertTriangle className="h-6 w-6" />}
        />
        <StatsCard
          title="Processing Status"
          value={`${data.processed_count}/${data.total_documents}`}
          subtitle={data.failed_count > 0 ? `${data.failed_count} failed` : "All good"}
          icon={<CheckCircle className="h-6 w-6" />}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Trend */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-[hsl(var(--primary))]" />
              Monthly Expenses
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.monthly_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={data.monthly_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="total" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-sm text-[hsl(var(--muted-foreground))]">
                No monthly data yet
              </div>
            )}
          </CardContent>
        </Card>

        {/* Category Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="h-5 w-5 text-[hsl(var(--primary))]" />
              Expense Categories
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.category_breakdown.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={data.category_breakdown}
                    dataKey="total"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    innerRadius={50}
                    paddingAngle={2}
                    label={(props: any) => `${props.category || ''} ${((props.percent || 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {data.category_breakdown.map((_, index) => (
                      <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-sm text-[hsl(var(--muted-foreground))]">
                No categories yet
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Documents */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Documents</CardTitle>
          <Link to="/invoices">
            <Button variant="ghost" size="sm">View all</Button>
          </Link>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>File</TableHead>
                <TableHead>Vendor</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Uploaded</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.recent_documents.map(doc => {
                const reviewBadge = doc.review_status ? getReviewBadge(doc.review_status) : null
                return (
                  <TableRow key={doc.id}>
                    <TableCell>
                      <Link to={`/invoices/${doc.id}`} className="font-medium hover:text-[hsl(var(--primary))] transition-colors">
                        {doc.original_filename}
                      </Link>
                    </TableCell>
                    <TableCell>{doc.vendor_name || "—"}</TableCell>
                    <TableCell className="font-mono">
                      {doc.total_amount != null ? formatCurrency(doc.total_amount, doc.currency || "USD") : "—"}
                    </TableCell>
                    <TableCell>
                      <span className={cn("text-xs font-medium capitalize", getStatusColor(doc.status))}>
                        {doc.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-[hsl(var(--muted-foreground))]">
                      {formatDate(doc.upload_time)}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
