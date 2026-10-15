import type { ButtonHTMLAttributes } from 'react'
import { Link, type LinkProps } from 'react-router'

export type ButtonVariant = 'primary' | 'default' | 'text' | 'danger'

function buttonClassName(variant: ButtonVariant, className?: string) {
  return ['ui-button', `ui-button--${variant}`, className].filter(Boolean).join(' ')
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
}

export function Button({ variant = 'default', type = 'button', className, ...rest }: ButtonProps) {
  return <button type={type} className={buttonClassName(variant, className)} {...rest} />
}

interface LinkButtonProps extends LinkProps {
  variant?: ButtonVariant
}

/** Ссылка, которая выглядит как кнопка. */
export function LinkButton({ variant = 'default', className, ...rest }: LinkButtonProps) {
  return <Link className={buttonClassName(variant, className)} {...rest} />
}
