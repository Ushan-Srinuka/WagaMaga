import { ApiError, forgetSession, request } from './accounts'
import type { Page } from './farms'

export type Category = 'account' | 'farm_records' | 'technical' | 'feedback'
export type SupportStatus = 'open' | 'in_progress' | 'resolved'
export type Ticket = {
  id: string
  farmer_id: string
  category: Category
  subject: string
  status: SupportStatus
  version: number
  created_at: string
  updated_at: string
  requester_name: string
  requester_available: boolean
}
export type Message = {
  id: string
  author_role: 'farmer' | 'administrator'
  body: string
  ticket_version: number
  created_at: string
}
export type TicketPage = Page<Ticket>
export type MessagePage = Page<Message>
export const categories: Record<Category, string> = {
  account: 'Account and access',
  farm_records: 'Using farm records',
  technical: 'Website problem',
  feedback: 'Feedback or suggestion',
}
export const statuses: Record<SupportStatus, string> = {
  open: 'Open',
  in_progress: 'In progress',
  resolved: 'Resolved',
}

function expired(error: unknown) {
  if (error instanceof ApiError && error.status === 401) {
    forgetSession()
    window.dispatchEvent(new Event('account-expired'))
  }
}
export async function supportRead<T>(path: string): Promise<T> {
  try {
    return await request<T>(path)
  } catch (error) {
    expired(error)
    throw error
  }
}
export async function supportWrite<T>(path: string, body: unknown): Promise<T> {
  try {
    return await request<T>(
      path,
      { method: 'POST', body: JSON.stringify(body) },
      { retryUnauthorized: false },
    )
  } catch (error) {
    expired(error)
    throw error
  }
}
export function supportError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 404)
      return 'This support request is unavailable or does not belong to your account.'
    if (error.status === 403)
      return 'Your account cannot perform this support action.'
    if (error.status === 409)
      return 'This request changed, was resolved or cannot receive replies. Your message has not been sent. Reload and review the conversation.'
    if (error.status === 0 || error.status === 503)
      return 'The result could not be confirmed. Your request or message may already be saved. Review saved requests before sending again.'
    if (error.status === 429)
      return 'Too many support actions. Please wait before trying again.'
  }
  return error instanceof Error
    ? error.message
    : 'Support could not be reached. Try again.'
}
