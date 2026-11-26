export type PdfMetadata = {
  publisher: string
  language: string
  crop: string
  region: string
  published_on: string | null
  valid_until: string | null
  access: 'admin' | 'farmers'
  source_url?: string | null
  reuse_basis?: string | null
}

export default function PdfMetadataFields({
  previous,
  screened = false,
}: {
  previous?: PdfMetadata | null
  screened?: boolean
}) {
  return (
    <fieldset>
      <legend>Reviewed library metadata</legend>
      <label className="field">
        Publisher
        <input
          name="publisher"
          required
          maxLength={160}
          defaultValue={previous?.publisher}
        />
      </label>
      <label className="field">
        Language
        <select name="language" defaultValue={previous?.language ?? 'en'}>
          <option value="en">English</option>
          <option value="si">Sinhala</option>
          <option value="ta">Tamil</option>
        </select>
      </label>
      <label className="field">
        Crop code
        <input
          name="crop"
          required
          pattern="[a-z][a-z0-9_]{0,39}"
          defaultValue={previous?.crop ?? 'chilli'}
        />
      </label>
      <label className="field">
        District or Sri Lanka
        <input
          name="region"
          required
          maxLength={100}
          defaultValue={previous?.region ?? 'Anuradhapura'}
        />
      </label>
      <label className="field">
        Publication date (leave blank if unknown)
        <input
          type="date"
          name="published_on"
          defaultValue={previous?.published_on ?? ''}
        />
      </label>
      <label className="field">
        Valid until (leave blank if unspecified)
        <input
          type="date"
          name="valid_until"
          defaultValue={previous?.valid_until ?? ''}
        />
      </label>
      <label className="field">
        Library access after publication
        <select name="access" defaultValue={previous?.access ?? 'admin'}>
          <option value="admin">Administrators only</option>
          <option value="farmers">Farmers with a matching cultivation</option>
        </select>
      </label>
      {screened && (
        <>
          <label className="field">
            Original source URL
            <input
              name="source_url"
              type="url"
              required
              maxLength={300}
              defaultValue={previous?.source_url ?? ''}
            />
          </label>
          <label className="field">
            Reuse basis
            <input
              name="reuse_basis"
              required
              maxLength={240}
              defaultValue={previous?.reuse_basis ?? ''}
            />
          </label>
        </>
      )}
    </fieldset>
  )
}
