import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '@/features/auth'
import { getFieldErrors, type FieldErrors } from '@/shared/api'
import { FieldError } from '@/shared/ui'

const initialForm = { email: '', password: '', first_name: '', last_name: '' }

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState(initialForm)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [submitting, setSubmitting] = useState(false)

  const update = (field: keyof typeof initialForm) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setErrors({})
    try {
      await register(form)
      navigate('/', { replace: true })
    } catch (error) {
      setErrors(getFieldErrors(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <h1>Регистрация</h1>
      <FieldError messages={errors.non_field_errors} />

      <label>
        Email
        <input type="email" autoComplete="email" value={form.email} onChange={update('email')} required />
      </label>
      <FieldError messages={errors.email} />

      <label>
        Пароль
        <input
          type="password"
          autoComplete="new-password"
          value={form.password}
          onChange={update('password')}
          required
        />
      </label>
      <FieldError messages={errors.password} />

      <label>
        Имя
        <input autoComplete="given-name" value={form.first_name} onChange={update('first_name')} />
      </label>
      <FieldError messages={errors.first_name} />

      <label>
        Фамилия
        <input autoComplete="family-name" value={form.last_name} onChange={update('last_name')} />
      </label>
      <FieldError messages={errors.last_name} />

      <button type="submit" disabled={submitting}>
        {submitting ? 'Создаём аккаунт…' : 'Зарегистрироваться'}
      </button>
      <p>
        Уже есть аккаунт? <Link to="/login">Войти</Link>
      </p>
    </form>
  )
}
