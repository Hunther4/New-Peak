import { memo } from "react"

const Card = memo(function Card({
  children,
  className = "",
  hover = false,
  interactive = false,
  ...props
}) {
  return (
    <div
      className={`card relative overflow-hidden ${hover ? "hover:border-white/[0.12]" : ""} ${interactive ? "cursor-pointer" : ""} ${className}`}
      {...props}
    >
      {children}
    </div>
  )
})

export default Card
