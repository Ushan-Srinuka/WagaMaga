import { ApiError, forgetSession, request } from './accounts'

export type Page<T> = {
  items: T[]
  total: number
  page: number
  page_size: number
}
export type Unit = 'ha' | 'acre' | 'm2'
export type FarmDeleted = { id: string; deleted: true; message: string }
export type Farm = {
  id: string
  farmer_id: string
  name: string
  location: string
  timezone: string
  latitude: string | null
  longitude: string | null
  area_value: string | null
  area_unit: Unit | null
  archived_at: string | null
  effective_archived: boolean
  version: number
  created_at: string
  updated_at: string
}
export type Cultivation = {
  id: string
  farm_id: string
  crop_type_id: string
  planting_date: string
  area_value: string
  area_unit: Unit
  soil_notes: string | null
  estimated_stage: string | null
  confirmed_stage: string | null
  confirmed_by: string | null
  confirmed_at: string | null
  archived_at: string | null
  effective_archived: boolean
  planned: boolean
  version: number
  created_at: string
  updated_at: string
}
export type Observation = {
  id: string
  cultivation_id: string
  observed_at: string
  notes: string
  recorded_by: string
  version: number
  created_at: string
  updated_at: string
  effective_archived: boolean
}
export type Crop = {
  id: string
  code: string
  display_name: string
  supported: boolean
}
export type Revision = {
  id: string
  version: number
  changed_at: string
  changed_by: string
  snapshot: Record<string, string | number | null>
}

export async function farmRead<T>(path: string): Promise<T> {
  try {
    return await request<T>(path)
  } catch (error) {
    expire(error)
    throw error
  }
}
export async function farmWrite<T>(
  path: string,
  method: 'POST' | 'PATCH',
  body: unknown,
): Promise<T> {
  try {
    return await request<T>(
      path,
      { method, body: JSON.stringify(body) },
      { retryUnauthorized: false },
    )
  } catch (error) {
    expire(error)
    throw error
  }
}
function expire(error: unknown) {
  if (error instanceof ApiError && error.status === 401) {
    forgetSession()
    window.dispatchEvent(new Event('account-expired'))
  }
}
export function failureText(error: unknown) {
  if (error instanceof ApiError) {
    if (error.code === 'INVALID_TIMEZONE')
      return 'Choose a valid farm timezone, such as Asia/Colombo.'
    if (error.code === 'UNSUPPORTED_CROP')
      return 'The selected crop is no longer supported. Refresh the page to update the crop list.'
    if (error.code === 'FUTURE_OBSERVATION')
      return 'Observation time cannot be in the future. Check the date, time and device timezone.'
    if (error.status === 404)
      return 'This record is unavailable or does not belong to your account.'
    if (error.status === 403)
      return 'Your account cannot access these farm records.'
    if (error.status === 409)
      return 'The record changed or was archived. Your draft has not been saved. Reload the latest record and review it before saving again.'
    if (error.status === 503 || error.status === 0)
      return 'The save could not be confirmed. It may already have been saved. Review the records before trying again.'
  }
  return error instanceof Error
    ? error.message
    : 'The request could not be completed.'
}
export function timestamp(value: string, timezone = 'Asia/Colombo') {
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: timezone,
  }).format(new Date(value))
}
export function area(value: string | number | null, unit: string | null) {
  return value === null
    ? 'Not recorded'
    : `${value} ${unit === 'm2' ? 'm²' : (unit ?? '')}`
}
export function areaError(value: string) {
  let normalized = value.replace(/^0+(?=\d)/, '')
  if (normalized.includes('.'))
    normalized = normalized.replace(/0+$/, '').replace(/\.$/, '')
  return !/^\d{1,12}(\.\d{1,6})?$/.test(normalized) || !/[1-9]/.test(value)
    ? 'Enter a positive area with up to six decimal places and fewer than 13 whole-number digits.'
    : ''
}
export function cropName(id: string, crops: Crop[]) {
  return (
    crops.find((crop) => crop.id === id)?.display_name ??
    'Previously recorded crop'
  )
}
