# STEM. Шкільний діагностичний інструмент

Цифрова платформа для діагностики зацікавленості учнів 5–9 класів у STEM-дисциплінах.

## Що реалізовано

- API: реєстрація, вхід, **зміна пароля** (`POST /api/auth/change-password`), опитування, модель класу, рекомендації для III–IV місць, перерахунок моделі, **персональні рекомендації учня** (`GET /api/me/recommendations`), **мережеві зведення по школах для admin** (`GET /api/admin/network-analytics`).
- **Admin API** (лише роль `admin`): CRUD шкіл, список користувачів і оновлення ролі/школи, bulk зв’язок учень–клас (`/api/admin/class-students/bulk` та CSV-варіант). Детально: [docs/ADMIN_API.md](docs/ADMIN_API.md).
- Після надсилання відповідей з `class_id` модель класу **зберігається** в таблиці `class_models`.
- Обмеження частоти запитів до входу/реєстрації (SlowAPI).
- Спостережуваність (опційно): `AUDIT_JSON`, `SLOW_REQUEST_THRESHOLD_MS`, `ACCESS_LOG` — див. `backend/.env.example` та [docs/ADMIN_API.md](docs/ADMIN_API.md).
- Ротація секрета JWT: [docs/SECRET_KEY_ROTATION.md](docs/SECRET_KEY_ROTATION.md).
- Продуктивність БД та індекси: [docs/PERFORMANCE.md](docs/PERFORMANCE.md).
- Модель загроз і чеклист перед продом: [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).
- Фронт: панель з вибором класу/опитування, для **admin** — блок адміністрування даних на дашборді, сторінка **Акаунт** (зміна пароля застосунку).
- Документація зміни пароля **PostgreSQL 16**: `docs/POSTGRESQL_PASSWORD_UA.md`, шаблон SQL: `database/postgresql_16_change_password.sql`.
- Шаблон Docker: `docker-compose.example.yml`.
- Шаблон оточення: `backend/.env.example`.

## Структура

```
STEM-CORE/
├── docs/ADMIN_API.md
├── docs/PERFORMANCE.md
├── docs/THREAT_MODEL.md
├── docs/SECRET_KEY_ROTATION.md
├── docs/POSTGRESQL_PASSWORD_UA.md
├── docker-compose.yml          # API + PostgreSQL
├── docker-compose.example.yml  # лише БД
├── .github/workflows/ci.yml
├── database/schema.sql, seed.sql, postgresql_16_change_password.sql
├── moodle/
├── backend/ (Alembic, pytest, Dockerfile)
├── frontend/
└── scripts/
```

## База даних

**Нові інсталяції:** у каталозі `backend` виконайте `alembic upgrade head` (потрібен налаштований `DATABASE_URL`). Це еквівалентно створенню таблиць за поточними моделями SQLAlchemy.

**Legacy / ручний відтворення:** варіант A — готовий SQL:

```powershell
psql -U postgres -d stem_diagnostic -f database/schema.sql
psql -U postgres -d stem_diagnostic -f database/seed.sql
```

Варіант B — `init_db.py` викликає `Base.metadata.create_all` (без історії міграцій). Для продакшну краще **Alembic**; `init_db.py` зручний для швидкого локального старту.

Потім за потреби виконайте `seed.sql` для школи, опитування та класу 5-А.

## Docker (одна команда)

З кореня репозиторію (задайте `STAFF_INVITE_SECRET` у `.env` або змінній оточення):

```powershell
docker compose up --build
```

API: http://localhost:8000 (образ збирає з `backend/Dockerfile`, стартує `alembic upgrade head` і uvicorn).

## Після деплою (потрібні дані замовника)

- Налаштувати реальний `DATABASE_URL`, секрети JWT і `STAFF_INVITE_SECRET`, HTTPS і DNS.
- Перевірити імпорт опитування в Moodle на вашому інстансі.
- За потреби узгодити з юридичною службою тексти для педагогів і політику приватності.

## Пароль PostgreSQL

Див. `docs/POSTGRESQL_PASSWORD_UA.md`. Після зміни пароля оновіть `DATABASE_URL` у `backend/.env`.

## Backend

```powershell
cd backend
copy .env.example .env
pip install -r requirements.txt
uvicorn main:app --reload
```

Для локальної розробки в `CORS_ORIGINS` можна залишити `*` або вказати `http://localhost:8000`. У продакшну задайте список доменів через кому (див. `backend/.env.example`). Опційно увімкніть `ACCESS_LOG=true` для рядкових access-логів (`stem.access`) у stderr.

Відкрийте http://localhost:8000

### Pre-commit (опційно)

З кореня репозиторію: `pip install pre-commit && pre-commit install` — перед комітом запускається ruff для `backend/`.

### Резервні копії БД

Див. [docs/BACKUP_POSTGRES.md](docs/BACKUP_POSTGRES.md).

## Пароль у веб-застосунку

Після входу: **Акаунт** → зміна пароля (не плутати з паролем PostgreSQL).

## Адміністратор (опційно)

Після `schema.sql` та `seed.sql`:

```powershell
cd scripts
py -3 create_admin.py admin@school.ua YourPassword12
```

## Демо: 1000 учнів, 2 школи

Після `schema.sql` (та за бажанням `seed.sql`):

```powershell
cd backend
pip install -r requirements.txt
cd ..\scripts
py -3 seed_demo_1000.py
```

Створює: **2 школи**, по **1 директору**, **5 завучів**, **20 класних** і **20 класів** (1–11 класи, 25 учнів у класі) на школу, **1000 учнів** загалом. Пароль усіх демо-акаунтів: **`Demo2026!`**.

Додатково: два опитування **І півріччя** та **ІІ півріччя 2025-2026**; для кожного з **1000 учнів** згенеровано повні відповіді (**25 оцінок** кожне), у **ІІ півріччі** середні трохи вищі (імітація зростання зацікавленості). Таблиця **`class_models`** заповнюється для **кожного класу** по обох опитуваннях. UUID опитувань скрипт виводить у консоль після виконання.

## Moodle

Імпорт: `moodle/stem_semantics_survey.xml` (див. `moodle/IMPORT_INSTRUCTIONS.md`).

## Контакти

support@stem-diagnostic.ua
