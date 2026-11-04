import { memo } from "react"

const VARIANTS = {
  primary:
    "bg-[#525252] text-white font-bold hover:bg-[#4a4a4a] active:bg-[#414141]",
  secondary:
    "bg-[#2fc2c2] text-[#142626] font-bold hover:bg-[#28a8a8] active:bg-[#208d8d]",
  tertiary:
    "bg-[#ebf5e6] text-[#2a3a2a] font-bold hover:bg-[#dbe8d0]",
  ghost:
    "bg-white/[0.04] text-neutral-300 border border-white/[0.08] hover:bg-white/[0.08] hover:text-white hover:border-white/[0.2]",
  danger:
    "bg-red-500/10 text-red-300 border border-red-500/25 hover:bg-red-500/20 hover:text-red-200",
  subtle:
    "bg-transparent text-neutral-500 hover:text-neutral-300 hover:bg-white/[0.04]",
}

const SIZES = {
  sm: "px-3 py-1.5 text-[11px] rounded-lg",
  md: "px-4 py-2 text-xs rounded-xl",
  lg: "px-6 py-3 text-sm rounded-xl",
}

const Button = memo(function Button({
  children,
  variant = "primary",
  size = "md",
  className = "",
  disabled,
  ...props
}) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 font-semibold transition-all duration-200 disabled:opacity-40 disabled:pointer-events-none ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  )
})

export default Button
