import { Link } from 'react-router'
import { useSeller } from '@/features/seller'
import { formatDate, formatPersonName } from '@/shared/lib'
import { Avatar, Card, EmptyState, LinkButton } from '@/shared/ui'
import './SellerProfilePage.css'

/** Профиль продавца: данные пользователя (User) и его магазины. */
export function SellerProfilePage() {
  const { profile } = useSeller()
  const name = formatPersonName(profile)

  return (
    <>
      <section className="profile-hero">
        <Avatar name={name} size={72} />
        <div className="profile-hero__text">
          <h1 className="profile-hero__name">{name}</h1>
          <p className="profile-hero__meta">
            {profile.email} · на площадке с {formatDate(profile.date_joined)}
          </p>
        </div>
      </section>

      <Card title="Личные данные">
        <dl className="ui-props">
          <dt>Email</dt>
          <dd>{profile.email}</dd>
          <dt>Имя</dt>
          <dd>{profile.first_name || <span className="ui-muted">не указано</span>}</dd>
          <dt>Фамилия</dt>
          <dd>{profile.last_name || <span className="ui-muted">не указана</span>}</dd>
          <dt>Дата регистрации</dt>
          <dd>{formatDate(profile.date_joined)}</dd>
        </dl>
      </Card>

      <Card title="Магазины" flush>
        {profile.shops.length === 0 ? (
          <EmptyState
            title="Магазинов пока нет"
            action={
              <LinkButton variant="primary" to="/seller">
                Создать магазин
              </LinkButton>
            }
          />
        ) : (
          <ul className="profile-shops">
            {profile.shops.map((shop) => (
              <li key={shop.id} className="profile-shops__item">
                <span className="profile-shops__name">{shop.name}</span>
                <Link to={`/seller/shops/${shop.id}/products`}>Товары</Link>
                <Link to={`/seller/shops/${shop.id}/orders`}>Заказы</Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}
