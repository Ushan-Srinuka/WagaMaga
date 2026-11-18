export type Notification = {
  id: string
  event_type: 'role_changed' | 'account_reenabled' | 'password_changed'
  title: string
  body: string
  created_at: string
  read_at: string | null
}

export type NotificationPage = {
  items: Notification[]
  total: number
  unread_count: number
  page: number
  page_size: number
}
