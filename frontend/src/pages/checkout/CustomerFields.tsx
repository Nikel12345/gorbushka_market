import { Link } from 'react-router'
import type { FieldErrors, User } from '@/shared/api'
import { formatPhone } from '@/shared/lib'
import { Field } from '@/shared/ui'

export interface CustomerValue {
  email: string
  password: string
  phone: string
}

interface CustomerFieldsProps {
  /** null — гость */
  user: User | null
  value: CustomerValue
  onChange: (value: CustomerValue) => void
  errors: FieldErrors
}

/**
 * «Данные покупателя». Гость указывает почту и пароль: есть аккаунт с этой почтой — заказ оформится
 * в него (пароль должен подойти), нет — создастся новый. Вошедшему показываем почту и телефон из профиля;
 * телефона нет — поле, введённый номер сохранится в профиль.
 */
export function CustomerFields({ user, value, onChange, errors }: CustomerFieldsProps) {
  const set = (patch: Partial<CustomerValue>) => onChange({ ...value, ...patch })

  const phoneField = (
    <Field label="Телефон" hint="Необязательно. Сохраним в профиле — чтобы связаться по заказу." errors={errors.phone}>
      <input
        className="ui-input"
        type="tel"
        value={value.phone}
        onChange={(event) => set({ phone: event.target.value })}
        placeholder="+7 999 123-45-67"
        autoComplete="tel"
        maxLength={30}
        aria-invalid={Boolean(errors.phone)}
      />
    </Field>
  )

  if (user) {
    return (
      <section className="checkout-section">
        <h2 className="checkout-section__title">Данные покупателя</h2>
        <dl className="checkout-customer">
          <div>
            <dt>Почта</dt>
            <dd>{user.email}</dd>
          </div>
          {user.phone && (
            <div>
              <dt>Телефон</dt>
              <dd>{formatPhone(user.phone)}</dd>
            </div>
          )}
        </dl>
        {!user.phone && phoneField}
      </section>
    )
  }

  return (
    <section className="checkout-section">
      <h2 className="checkout-section__title">Данные покупателя</h2>
      <p className="checkout-section__hint">
        Создадим аккаунт — в нём будут ваши заказы. Уже есть аккаунт — укажите его почту и пароль или{' '}
        <Link to="/login" state={{ from: '/checkout' }}>
          войдите
        </Link>
        .
      </p>
      <div className="checkout-customer__fields">
        <Field label="Почта" errors={errors.email}>
          <input
            className="ui-input"
            type="email"
            value={value.email}
            onChange={(event) => set({ email: event.target.value })}
            autoComplete="email"
            aria-invalid={Boolean(errors.email)}
          />
        </Field>
        <Field label="Пароль" hint="Для нового аккаунта — не короче 8 символов." errors={errors.password}>
          <input
            className="ui-input"
            type="password"
            value={value.password}
            onChange={(event) => set({ password: event.target.value })}
            autoComplete="current-password"
            aria-invalid={Boolean(errors.password)}
          />
        </Field>
      </div>
      {phoneField}
    </section>
  )
}
