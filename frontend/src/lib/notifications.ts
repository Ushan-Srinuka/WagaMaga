export type Notification = {
  id: string
  event_type:
    | 'role_changed'
    | 'account_reenabled'
    | 'password_changed'
    | 'support_updated'
    | 'weather_review'
    | 'advisor_review'
    | 'task_due'
    | 'task_overdue'
  title: string
  body: string
  created_at: string
  read_at: string | null
  review_plan_id?: string | null
}

export type NotificationPage = {
  items: Notification[]
  total: number
  unread_count: number
  page: number
  page_size: number
}
