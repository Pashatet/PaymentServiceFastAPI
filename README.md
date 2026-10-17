# Payment Service API

Асинхронный сервис платежей на FastAPI. Код приложения находится в app/: доменные правила — в app/domain/, модуль платежей — в app/payments/ (dao.py, models.py, router.py, schemas.py, service.py), общие настройки и подключение к базе — в app/config.py и app/database.py. Используются PostgreSQL, SQLAlchemy 2 async и Alembic.

## Структура приложения

~~~text
app/
├── __init__.py
├── config.py
├── database.py
├── main.py
├── domain/
└── payments/
    ├── __init__.py
    ├── dao.py
    ├── dependencies.py
    ├── models.py
    ├── router.py
    ├── schemas.py
    ├── security.py
    └── service.py
~~~

## Запуск в Docker

Нужен установленный Docker с Docker Compose.

1. В корне проекта выполните:

   ~~~bash
   docker compose up --build
   ~~~

2. Откройте Swagger UI: http://localhost:8000/docs
3. Остановка: Ctrl+C; удаление контейнеров: docker compose down.

База данных хранится в named volume postgres_data. Compose читает параметры из .env в корне проекта; файл .env не добавляется в Git. Перед внешним размещением замените локальные пароль PostgreSQL и ключ вебхука.

При старте приложения выполняется Alembic upgrade head, после чего приложение добавляет отсутствующие тарифы: basic, standard и premium.

## Локальный запуск

Нужен Python 3.11 или новее и доступный PostgreSQL.

1. Создайте и активируйте виртуальное окружение.
2. Установите зависимости: pip install -r requirements-dev.txt
3. Скопируйте .env.example в .env и при необходимости измените параметры PostgreSQL, DATABASE_URL и WEBHOOK_SECRET. Для Docker Compose DATABASE_URL должен использовать хост db; при прямом запуске uvicorn на компьютере замените хост db на localhost.
4. Примените миграции: alembic upgrade head
5. Запустите API: uvicorn app.main:app --reload

## Деньги и правила оплаты

Все суммы передаются и хранятся целым числом копеек. Например, тариф standard стоит 1 990 000 копеек. Промокод KVITTO10 нечувствителен к регистру и уменьшает стоимость на 10 процентов. График рассрочки делит сумму без потери копеек: остаток распределяется по одному в первые платежи.

Поддерживаемые способы оплаты: card, sbp и installment. Для installment обязателен срок 3, 6 или 12 месяцев. Новый платёж имеет статус pending. Разрешены только переходы pending -> succeeded, pending -> failed и succeeded -> refunded.

Повтор с тем же заголовком Idempotency-Key возвращает исходный платёж с кодом 200. Новый запрос без существующего ключа возвращает код 201.

## Примеры запросов

Список тарифов:

~~~bash
curl.exe http://localhost:8000/tariffs
~~~

Создание платежа:

~~~bash
curl.exe -X POST http://localhost:8000/payments -H "Content-Type: application/json" -H "Idempotency-Key: order-1001" -d "{\"tariff_id\":\"standard\",\"email\":\"student@example.com\",\"method\":\"installment\",\"installment_months\":3,\"promo_code\":\"kvittO10\"}"
~~~

Получение платежа по id:

~~~bash
curl.exe http://localhost:8000/payments/PASTE_PAYMENT_UUID_HERE
~~~

Фильтры по email и статусу:

~~~bash
curl.exe "http://localhost:8000/payments?email=student@example.com&status=pending"
~~~

## Подпись банковского вебхука

POST /webhooks/bank принимает JSON с payment_id и status. Заголовок X-Signature должен содержать hex HMAC-SHA256 от точного тела запроса и WEBHOOK_SECRET. Неверная или отсутствующая подпись возвращает 401. Допустимые переходы применяются атомарно; запрещённый переход возвращает 409 и не меняет состояние платежа.

Пример для PowerShell, если переменная body содержит точное JSON-тело:

~~~powershell
$body = '{"payment_id":"PASTE_PAYMENT_UUID_HERE","status":"succeeded"}'
$secret = 'local-development-secret'
$hmac = [System.Security.Cryptography.HMACSHA256]::new([Text.Encoding]::UTF8.GetBytes($secret))
$signature = [Convert]::ToHexString($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($body))).ToLower()
curl.exe -X POST http://localhost:8000/webhooks/bank -H "Content-Type: application/json" -H "X-Signature: $signature" --data-raw $body
~~~

## Проверка качества

Установка тестовых и lint-зависимостей:

~~~bash
pip install -r requirements-dev.txt
~~~

Запуск обязательных сценариев:

~~~bash
pytest
~~~

Проверка Ruff:

~~~bash
ruff check .
~~~

Тесты используют SQLite in-memory, поэтому для проверки не нужен отдельный сервер PostgreSQL. Папка .github/workflows запускает Ruff и pytest при push и pull request.
