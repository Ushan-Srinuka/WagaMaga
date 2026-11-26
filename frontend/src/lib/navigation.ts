import type { Role } from './accounts'

export function signedInHome(role: Role) {
  return role === 'farmer'
    ? '/'
    : role === 'administrator'
      ? '/admin/overview'
      : '/advisor'
}
