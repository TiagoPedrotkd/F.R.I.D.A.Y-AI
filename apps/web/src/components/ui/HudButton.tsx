import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { hudButtonVariants, type HudButtonVariant } from '@/styles/system'

export type HudButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: HudButtonVariant
}

/** Shared HUD button — uses design-system variants from `styles/system`. */
export const HudButton = forwardRef<HTMLButtonElement, HudButtonProps>(function HudButton(
  { variant = 'default', className = '', type = 'button', ...rest },
  ref,
) {
  const base = hudButtonVariants[variant]
  return (
    <button ref={ref} type={type} className={className ? `${base} ${className}` : base} {...rest} />
  )
})
