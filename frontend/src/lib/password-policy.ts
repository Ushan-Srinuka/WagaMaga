export const PASSWORD_REQUIREMENTS =
  'Use 8–128 characters with at least one letter, one number and one symbol. Spaces do not count as a symbol.'

export function isSignupPasswordValid(password: string): boolean {
  const length = Array.from(password).length
  return (
    length >= 8 &&
    length <= 128 &&
    /\p{L}/u.test(password) &&
    /\p{Nd}/u.test(password) &&
    /[\p{P}\p{S}]/u.test(password)
  )
}
