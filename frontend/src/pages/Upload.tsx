import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { useNavigate } from "react-router-dom"
import { Upload, FileText, Image, CheckCircle, XCircle, Loader2, AlertCircle } from "lucide-react"
import { api } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent, Button, Badge } from "@/components/ui"
import { cn, formatFileSize } from "@/lib/utils"
import { toast } from "sonner"

const ACCEPTED_TYPES = {
  "application/pdf": [".pdf"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
}
const MAX_SIZE = 20 * 1024 * 1024 // 20MB

interface FileWithStatus {
  file: File
  status: "pending" | "uploading" | "completed" | "failed"
  error?: string
  documentId?: string
}

export function UploadPage() {
  const [files, setFiles] = useState<FileWithStatus[]>([])
  const [uploading, setUploading] = useState(false)
  const navigate = useNavigate()

  const onDrop = useCallback((acceptedFiles: File[], rejections: any[]) => {
    // Add accepted files
    const newFiles: FileWithStatus[] = acceptedFiles.map(f => ({
      file: f,
      status: "pending" as const,
    }))

    // Report rejections
    rejections.forEach((r: any) => {
      const errors = r.errors.map((e: any) => e.message).join(", ")
      toast.error(`${r.file.name}: ${errors}`)
    })

    setFiles(prev => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    multiple: true,
  })

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const uploadAll = async () => {
    const pendingFiles = files.filter(f => f.status === "pending")
    if (pendingFiles.length === 0) {
      toast.info("No files to upload")
      return
    }

    setUploading(true)
    setFiles(prev => prev.map(f => f.status === "pending" ? { ...f, status: "uploading" } : f))

    try {
      const rawFiles = pendingFiles.map(f => f.file)
      const results = await api.uploadDocuments(rawFiles)

      setFiles(prev => prev.map(f => {
        if (f.status === "uploading") {
          return { ...f, status: "completed" }
        }
        return f
      }))

      toast.success(`${results.length} document${results.length > 1 ? "s" : ""} uploaded and queued for processing`)
    } catch (err: any) {
      setFiles(prev => prev.map(f => {
        if (f.status === "uploading") {
          return { ...f, status: "failed", error: err.message }
        }
        return f
      }))
      toast.error(err.message || "Upload failed")
    } finally {
      setUploading(false)
    }
  }

  const getFileIcon = (file: File) => {
    if (file.type === "application/pdf") return <FileText className="h-5 w-5 text-red-500" />
    return <Image className="h-5 w-5 text-blue-500" />
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "uploading": return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
      case "completed": return <CheckCircle className="h-4 w-4 text-emerald-500" />
      case "failed": return <XCircle className="h-4 w-4 text-red-500" />
      default: return null
    }
  }

  const pendingCount = files.filter(f => f.status === "pending").length
  const completedCount = files.filter(f => f.status === "completed").length

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-500">
      {/* Drop Zone */}
      <Card>
        <CardContent className="p-0">
          <div
            {...getRootProps()}
            className={cn(
              "flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-300",
              isDragActive
                ? "border-[hsl(var(--primary))] bg-[hsl(var(--primary))]/5 scale-[1.01]"
                : "border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]/50 hover:bg-[hsl(var(--accent))]/50"
            )}
          >
            <input {...getInputProps()} aria-label="Upload documents" />
            <div className={cn(
              "h-16 w-16 rounded-2xl flex items-center justify-center mb-4 transition-all duration-300",
              isDragActive ? "bg-[hsl(var(--primary))]/20 scale-110" : "bg-[hsl(var(--muted))]"
            )}>
              <Upload className={cn(
                "h-8 w-8 transition-colors",
                isDragActive ? "text-[hsl(var(--primary))]" : "text-[hsl(var(--muted-foreground))]"
              )} />
            </div>
            <h3 className="text-lg font-semibold mb-1">
              {isDragActive ? "Drop files here" : "Upload Invoices & Receipts"}
            </h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))] text-center max-w-md">
              Drag and drop PDF, PNG, or JPG files, or click to browse.
              <br />
              <span className="text-xs">Max {MAX_SIZE / 1024 / 1024}MB per file</span>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* File List */}
      {files.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">
              Files ({files.length})
              {completedCount > 0 && (
                <span className="ml-2 text-sm font-normal text-emerald-500">
                  {completedCount} uploaded
                </span>
              )}
            </CardTitle>
            <div className="flex gap-2">
              {completedCount > 0 && (
                <Button variant="outline" size="sm" onClick={() => navigate("/invoices")}>
                  View Invoices
                </Button>
              )}
              <Button
                size="sm"
                onClick={uploadAll}
                disabled={uploading || pendingCount === 0}
                className="gap-2"
              >
                {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                {uploading ? "Uploading..." : `Upload ${pendingCount > 0 ? pendingCount : ""} File${pendingCount !== 1 ? "s" : ""}`}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {files.map((f, i) => (
                <div
                  key={i}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-lg border transition-colors",
                    f.status === "completed" ? "bg-emerald-500/5 border-emerald-500/20" :
                    f.status === "failed" ? "bg-red-500/5 border-red-500/20" :
                    "border-[hsl(var(--border))]"
                  )}
                >
                  {getFileIcon(f.file)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{f.file.name}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {formatFileSize(f.file.size)} · {f.file.type.split("/")[1]?.toUpperCase()}
                      {f.error && <span className="text-red-500 ml-2">{f.error}</span>}
                    </p>
                  </div>
                  {getStatusIcon(f.status)}
                  {f.status === "pending" && (
                    <button
                      onClick={() => removeFile(i)}
                      className="text-[hsl(var(--muted-foreground))] hover:text-red-500 transition-colors"
                      aria-label={`Remove ${f.file.name}`}
                    >
                      <XCircle className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tips */}
      <Card className="bg-[hsl(var(--primary))]/5 border-[hsl(var(--primary))]/20">
        <CardContent className="p-4 flex gap-3">
          <AlertCircle className="h-5 w-5 text-[hsl(var(--primary))] shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-[hsl(var(--primary))] mb-1">Processing Tips</p>
            <ul className="text-[hsl(var(--muted-foreground))] space-y-0.5 list-disc list-inside">
              <li>Clear, high-resolution scans produce better results</li>
              <li>Text-based PDFs are processed faster than scanned images</li>
              <li>All extracted data can be reviewed and corrected before export</li>
              <li>Processing uses your local AI model — documents stay on your machine</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
