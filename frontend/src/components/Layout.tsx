import React, { useState, useEffect } from "react"
import { Link, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"
import { api, type AIHealth } from "@/lib/api"
import {
  LayoutDashboard,
  Upload,
  FileText,
  PieChart,
  Settings,
  Sun,
  Moon,
  Zap,
  Menu,
  X,
  ChevronRight,
  Wifi,
  WifiOff,
  AlertCircle,
} from "lucide-react"
import { Button, Badge } from "@/components/ui"

const navItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/upload", label: "Upload Documents", icon: Upload },
  { path: "/invoices", label: "All Invoices", icon: FileText },
  { path: "/reports", label: "Expense Reports", icon: PieChart },
  { path: "/settings", label: "Settings", icon: Settings },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const [dark, setDark] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("theme") === "dark" ||
        (!localStorage.getItem("theme") && window.matchMedia("(prefers-color-scheme: dark)").matches)
    }
    return false
  })
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [aiStatus, setAiStatus] = useState<AIHealth | null>(null)

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
    localStorage.setItem("theme", dark ? "dark" : "light")
  }, [dark])

  useEffect(() => {
    api.aiHealth().then(setAiStatus).catch(() =>
      setAiStatus({ status: "disconnected", model: "unknown", ollama_url: "", message: "Cannot reach backend" })
    )
  }, [])

  const aiStatusIcon = aiStatus?.status === "connected"
    ? <Wifi className="h-3.5 w-3.5 text-emerald-500" />
    : aiStatus?.status === "demo_mode"
    ? <AlertCircle className="h-3.5 w-3.5 text-amber-500" />
    : <WifiOff className="h-3.5 w-3.5 text-red-500" />

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 w-64 bg-[hsl(var(--card))] border-r border-[hsl(var(--border))] flex flex-col transition-transform duration-300 lg:static lg:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        {/* Logo */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-[hsl(var(--border))]">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-base tracking-tight">InvoicePilot</h1>
            <p className="text-[10px] text-[hsl(var(--muted-foreground))] font-medium uppercase tracking-wider">AI-Powered</p>
          </div>
          <button className="ml-auto lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map(item => {
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group",
                  isActive
                    ? "bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] shadow-sm"
                    : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--accent))] hover:text-[hsl(var(--foreground))]"
                )}
              >
                <item.icon className={cn("h-4.5 w-4.5 transition-transform duration-200", isActive && "scale-110")} />
                {item.label}
                {isActive && <ChevronRight className="ml-auto h-4 w-4 opacity-50" />}
              </Link>
            )
          })}
        </nav>

        {/* AI Status Footer */}
        <div className="p-4 border-t border-[hsl(var(--border))]">
          <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
            {aiStatusIcon}
            <span className="truncate">{aiStatus?.model || "Checking..."}</span>
          </div>
          {aiStatus?.status === "demo_mode" && (
            <Badge className="mt-2 bg-amber-500/10 text-amber-500 border border-amber-500/20 text-[10px]">Demo Mode</Badge>
          )}
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 flex items-center justify-between px-6 border-b border-[hsl(var(--border))] bg-[hsl(var(--card))]/80 backdrop-blur-sm sticky top-0 z-30">
          <div className="flex items-center gap-4">
            <button className="lg:hidden" onClick={() => setSidebarOpen(true)}>
              <Menu className="h-5 w-5" />
            </button>
            <h2 className="text-lg font-semibold">
              {navItems.find(n => n.path === location.pathname)?.label || "InvoicePilot AI"}
            </h2>
          </div>
          <Button variant="ghost" size="icon" onClick={() => setDark(!dark)} aria-label="Toggle theme">
            {dark ? <Sun className="h-4.5 w-4.5" /> : <Moon className="h-4.5 w-4.5" />}
          </Button>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
