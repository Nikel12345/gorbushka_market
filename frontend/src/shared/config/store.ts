// Справочные данные о магазине для страницы «О магазине» и подвала. На бэке их нет — правятся здесь.

export const store = {
  mall: 'ТЦ «Горбушкин двор»',
  address: 'Москва, ул. Барклая, 8',
  metro: 'Багратионовская',
  hours: '10:00–21:00',
  mapUrl: `https://yandex.ru/maps/?text=${encodeURIComponent('Москва, улица Барклая, 8')}`,
} as const
