type LoaderOverlayProps = {
  show: boolean
  message?: string
}

export default function LoaderOverlay({ show, message = 'Processing your request…' }: LoaderOverlayProps) {
  if (!show) return null

  return (
    <div className="loader-overlay" role="status" aria-live="polite" aria-busy="true">
      <div className="loader-card">
        <span className="spinner" aria-hidden="true" />
        <p>{message}</p>
      </div>
    </div>
  )
}
