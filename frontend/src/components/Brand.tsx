import './brand.css'

export default function Brand() {
  return (
    <>
      <span className="logo-square" aria-hidden="true">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M19 4C9 3 3 8 5 15c2 7 13 6 14-11ZM5 20 15 10M9 16v-5M9 16h5" />
        </svg>
      </span>
      <span className="brand-name">WagaMaga</span>
      <span className="brand-ai">AI</span>
    </>
  )
}
