import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Toaster } from "sonner"
import { Layout } from "@/components/Layout"
import { DashboardPage } from "@/pages/Dashboard"
import { UploadPage } from "@/pages/Upload"
import { InvoicesPage } from "@/pages/Invoices"
import { InvoiceDetailPage } from "@/pages/InvoiceDetail"
import { ReportsPage } from "@/pages/Reports"
import { SettingsPage } from "@/pages/Settings"

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        richColors
        closeButton
        toastOptions={{
          style: {
            borderRadius: "0.625rem",
            fontSize: "13px",
          },
        }}
      />
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/invoices" element={<InvoicesPage />} />
          <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
