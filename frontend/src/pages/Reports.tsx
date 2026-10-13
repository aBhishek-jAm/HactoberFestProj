import { useEffect, useState } from "react"
import { PieChart, Download, Filter } from "lucide-react"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RechartsPie, Pie, Cell,
} from "recharts"
import { api, type ExpenseReport } from "@/lib/api"
import {
  Card, CardHeader, CardTitle, CardContent, Button, Select, Input,
  EmptyState, Skeleton, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui"
import { formatCurrency, cn } from "@/lib/utils"
import { toast } from "sonner"

const PIE_COLORS = [
  "#3B82F6", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981",
  "#06B6D4", "#EF4444", "#6366F1", "#F97316", "#14B8A6",
]

export function ReportsPage() {
  const [report, setReport] = useState<ExpenseReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [currency, setCurrency] = useState("")

  const fetchReport = () => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    if (currency) params.currency = currency

    api.expenseReport(params)
      .then(setReport)
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchReport() }, [])

  const handleFilter = () => fetchReport()

  const chartData = report?.groups.map(g => ({
    name: g.category,
    value: g.total,
    count: g.count,
  })) || []

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] block mb-1">From</label>
              <Input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="w-40" aria-label="Date from" />
            </div>
            <div>
              <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] block mb-1">To</label>
              <Input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="w-40" aria-label="Date to" />
            </div>
            <div>
              <label className="text-xs font-medium text-[hsl(var(--muted-foreground))] block mb-1">Currency</label>
              <Input placeholder="e.g. USD" value={currency} onChange={e => setCurrency(e.target.value)} className="w-28" aria-label="Currency" />
            </div>
            <Button onClick={handleFilter} className="gap-2">
              <Filter className="h-4 w-4" /> Apply Filters
            </Button>
            <div className="ml-auto flex gap-2">
              <Button variant="outline" size="sm" onClick={() => api.exportCsv()} className="gap-1.5">
                <Download className="h-3.5 w-3.5" /> CSV
              </Button>
              <Button variant="outline" size="sm" onClick={() => api.exportXlsx()} className="gap-1.5">
                <Download className="h-3.5 w-3.5" /> Excel
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card><CardContent className="p-6"><Skeleton className="h-64" /></CardContent></Card>
          <Card><CardContent className="p-6"><Skeleton className="h-64" /></CardContent></Card>
        </div>
      ) : !report || report.groups.length === 0 ? (
        <EmptyState
          icon={<PieChart className="h-12 w-12" />}
          title="No expense data"
          description="Upload and process some invoices to see expense reports"
        />
      ) : (
        <>
          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader><CardTitle>By Category</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 80 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis type="number" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                    <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={80} stroke="hsl(var(--muted-foreground))" />
                    <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                    <Bar dataKey="value" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Distribution</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <RechartsPie>
                    <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={110} innerRadius={60}>
                      {chartData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }} />
                  </RechartsPie>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Breakdown Table */}
          <Card>
            <CardHeader>
              <CardTitle>Expense Breakdown ({report.total_invoices} invoices)</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Category</TableHead>
                    <TableHead>Currency</TableHead>
                    <TableHead className="text-right">Invoices</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.groups.map((g, i) => (
                    <TableRow key={i}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="h-3 w-3 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                          <span className="font-medium">{g.category}</span>
                        </div>
                      </TableCell>
                      <TableCell><Badge variant="outline">{g.currency}</Badge></TableCell>
                      <TableCell className="text-right">{g.count}</TableCell>
                      <TableCell className="text-right font-mono font-medium">
                        {formatCurrency(g.total, g.currency)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
