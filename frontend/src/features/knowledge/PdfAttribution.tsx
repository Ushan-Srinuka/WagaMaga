export type PdfProvenance = {
  source_url?: string | null
  reuse_basis?: string | null
}

export default function PdfAttribution({ source }: { source: PdfProvenance }) {
  if (!source.source_url && !source.reuse_basis) return null
  return (
    <p className="record-note">
      {source.reuse_basis}
      {source.reuse_basis && source.source_url && ' · '}
      {source.source_url && (
        <a href={source.source_url} target="_blank" rel="noreferrer">
          Open original source
        </a>
      )}
    </p>
  )
}
