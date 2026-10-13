import { useEffect, useState } from "react"
import { Wifi, WifiOff, AlertCircle, Server, Brain, Shield, Info } from "lucide-react"
import { api, type AIHealth } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent, CardDescription, Badge, Button, Separator } from "@/components/ui"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

export function SettingsPage() {
  const [aiHealth, setAiHealth] = useState<AIHealth | null>(null)
  const [checking, setChecking] = useState(false)

  const checkAi = () => {
    setChecking(true)
    api.aiHealth()
      .then(setAiHealth)
      .catch(() => setAiHealth({ status: "disconnected", model: "unknown", ollama_url: "", message: "Backend unreachable" }))
      .finally(() => setChecking(false))
  }

  useEffect(() => { checkAi() }, [])

  const statusConfig = {
    connected: { icon: Wifi, color: "text-emerald-500", bg: "bg-emerald-500/10", label: "Connected" },
    demo_mode: { icon: AlertCircle, color: "text-amber-500", bg: "bg-amber-500/10", label: "Demo Mode" },
    disconnected: { icon: WifiOff, color: "text-red-500", bg: "bg-red-500/10", label: "Disconnected" },
  }

  const status = statusConfig[aiHealth?.status as keyof typeof statusConfig] || statusConfig.disconnected

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-500">
      {/* AI Model Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-[hsl(var(--primary))]" /> AI Model Configuration
          </CardTitle>
          <CardDescription>Local inference using Ollama</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg border border-[hsl(var(--border))]">
            <div className="flex items-center gap-3">
              <div className={cn("h-10 w-10 rounded-lg flex items-center justify-center", status.bg)}>
                <status.icon className={cn("h-5 w-5", status.color)} />
              </div>
              <div>
                <p className="font-medium">{status.label}</p>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  {aiHealth?.model || "Unknown model"}
                </p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={checkAi} disabled={checking}>
              {checking ? "Checking..." : "Refresh"}
            </Button>
          </div>

          {aiHealth?.message && (
            <div className="p-3 rounded-lg bg-[hsl(var(--muted))] text-sm text-[hsl(var(--muted-foreground))]">
              {aiHealth.message}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-[hsl(var(--muted-foreground))]">Model</p>
              <p className="font-mono font-medium">{aiHealth?.model || "—"}</p>
            </div>
            <div>
              <p className="text-[hsl(var(--muted-foreground))]">Ollama URL</p>
              <p className="font-mono font-medium">{aiHealth?.ollama_url || "—"}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Setup Instructions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5 text-[hsl(var(--primary))]" /> Setup Instructions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3 text-sm">
            <div className="flex gap-3">
              <div className="h-6 w-6 rounded-full bg-[hsl(var(--primary))]/10 flex items-center justify-center text-xs font-bold text-[hsl(var(--primary))] shrink-0">1</div>
              <div>
                <p className="font-medium">Install Ollama</p>
                <p className="text-[hsl(var(--muted-foreground))]">
                  Download from <a href="https://ollama.com" target="_blank" rel="noopener" className="text-[hsl(var(--primary))] hover:underline">ollama.com</a>
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="h-6 w-6 rounded-full bg-[hsl(var(--primary))]/10 flex items-center justify-center text-xs font-bold text-[hsl(var(--primary))] shrink-0">2</div>
              <div>
                <p className="font-medium">Pull the Gemma model</p>
                <code className="block mt-1 p-2 rounded bg-[hsl(var(--muted))] font-mono text-xs">
                  ollama pull gemma3:4b
                </code>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="h-6 w-6 rounded-full bg-[hsl(var(--primary))]/10 flex items-center justify-center text-xs font-bold text-[hsl(var(--primary))] shrink-0">3</div>
              <div>
                <p className="font-medium">Start Ollama</p>
                <code className="block mt-1 p-2 rounded bg-[hsl(var(--muted))] font-mono text-xs">
                  ollama serve
                </code>
                <p className="text-[hsl(var(--muted-foreground))] mt-1">
                  Ollama runs on port 11434 by default. No GPU required but recommended for speed.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Privacy */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-[hsl(var(--primary))]" /> Privacy & Security
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-[hsl(var(--muted-foreground))]">
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">✓</span>
              AI inference runs locally via Ollama — documents are not sent to external APIs
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">✓</span>
              Files are stored locally with randomized names
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">✓</span>
              No external telemetry or analytics
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">✓</span>
              Document text is not stored in application logs
            </li>
          </ul>
          <Separator className="my-4" />
          <div className="flex items-start gap-2 text-xs text-[hsl(var(--muted-foreground))]">
            <Info className="h-4 w-4 shrink-0 mt-0.5" />
            <p>
              Note: Local inference does not automatically guarantee full offline operation.
              OCR libraries, font rendering, and application hosting may still require
              network access or additional configuration for fully air-gapped environments.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
