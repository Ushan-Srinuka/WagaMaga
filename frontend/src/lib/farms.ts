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
export type SoilMoisture = 'dry' | 'moist' | 'waterlogged'
export type Observation = {
  id: string
  cultivation_id: string
  observed_at: string
  notes: string
  soil_moisture?: SoilMoisture | null
  recorded_by: string
  version: number
  created_at: string
  updated_at: string
  effective_archived: boolean
}
export type TaskStatus = 'pending' | 'completed' | 'cancelled'
export type FarmTask = {
  id: string
  title: string
  due_date: string
  status: TaskStatus
  version: number
}
export type FarmTaskEvent = {
  task_id: string
  version: number
  title: string
  due_date: string
  action: 'created' | 'edited' | 'completed' | 'cancelled'
  occurred_at: string
}
export type PlanOutcome = 'accepted' | 'rejected'
export type TaskPlanDecision = {
  plan_id: string
  outcome: PlanOutcome
  task_id: string | null
  decided_at: string
}
export type TaskPlan = {
  id: string
  version: number
  action_hash: string
  title: string
  due_date: string
  evidence_text: string
  expires_at: string
  state: 'pending' | 'expired' | 'stale' | PlanOutcome
  decision: TaskPlanDecision | null
}
export type TaskPlanHistory = TaskPlanDecision & {
  title: string
  due_date: string
  evidence_text: string
  action_type: 'create_task' | 'reschedule_task'
  previous_due_date: string | null
}
export type DemoForecast = {
  source: 'fixture'
  location: string
  timezone: string
  forecast_date: string
  rainfall_mm: number
  review_due_on: string | null
}
export type ForecastDay = {
  date: string
  minimum_c: number
  maximum_c: number
  precipitation_mm: number
}
export type FarmWeather = {
  status:
    'needs_coordinates' | 'unfetched' | 'fresh' | 'stale' | 'provider_disabled'
  location: string
  timezone: string
  checked_at: string
  can_refresh: boolean
  forecast: {
    provider: 'open-meteo'
    fetched_at: string
    fresh_until: string
    days: ForecastDay[]
  } | null
}
export type WeatherAlertRule = { threshold_mm: number | null; version: number }
export type WeatherAlert = {
  task_id: string
  title: string
  due_date: string
  task_version: number
  rule_version: number
  threshold_mm: number
  precipitation_mm: number
  forecast_fetched_at: string
}
export type WeatherAlertPage = Page<WeatherAlert> & {
  rule: WeatherAlertRule
  can_edit: boolean
  forecast_fresh: boolean
}
export type ReschedulePlan = {
  id: string
  version: number
  action_hash: string
  title: string
  current_due_date: string
  proposed_due_date: string
  evidence_text: string
  forecast_fetched_at: string
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
  headers?: HeadersInit,
): Promise<T> {
  try {
    return await request<T>(
      path,
      { method, body: JSON.stringify(body), headers },
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
    if (error.code === 'TASK_CLOSED')
      return 'Completed and cancelled tasks cannot be changed.'
    if (error.code === 'PLAN_CONFLICT') return error.message
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
