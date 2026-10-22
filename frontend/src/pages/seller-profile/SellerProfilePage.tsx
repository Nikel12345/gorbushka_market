import { useAuth } from '@/features/auth'
import { formatDate, formatPersonName } from '@/shared/lib'
import { Avatar, Card } from '@/shared/ui'
import './SellerProfilePage.css'

/** Профиль сотрудника: данные пользователя (User). Профиль магазина — в разделе «Магазин». */
export function SellerProfilePage() {
  const { user } = useAuth()
  if (!user) return null
  const name = formatPersonName(user)

  return (
    <>
      <section className="profile-hero">
        <Avatar name={name} size={72} />
        <div className="profile-hero__text">
          <h1 className="profile-hero__name">{name}</h1>
          <p className="profile-hero__meta">
            {user.email} · с нами с {formatDate(user.date_joined)}
          </p>
        </div>
      </section>

      <Card title="Личные данные">
        <dl className="ui-props">
          <dt>Email</dt>
          <dd>{user.email}</dd>
          <dt>Имя</dt>
          <dd>{user.first_name || <span className="ui-muted">не указано</span>}</dd>
          <dt>Фамилия</dt>
          <dd>{user.last_name || <span className="ui-muted">не указана</span>}</dd>
          <dt>Дата регистрации</dt>
          <dd>{formatDate(user.date_joined)}</dd>
        </dl>
      </Card>

    </>
  )
}
