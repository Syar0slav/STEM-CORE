const STEM_API_LS = 'stem_api_base';

/** База URL API без завершального слешу; порожній рядок = той самий origin, що й сторінка. */
function resolveApiBase() {
    if (typeof window === 'undefined' || !window.location) return '';
    try {
        const params = new URLSearchParams(window.location.search);
        const q = params.get('stem_api_base') || params.get('api_base');
        if (q) {
            const normalized = q.replace(/\/$/, '');
            try {
                localStorage.setItem(STEM_API_LS, normalized);
            } catch (e) { /* private mode */ }
            return normalized;
        }
    } catch (e) { /* ignore */ }
    try {
        const stored = localStorage.getItem(STEM_API_LS);
        if (stored) return stored.replace(/\/$/, '');
    } catch (e) { /* ignore */ }
    const p = window.location.protocol;
    if (p === 'file:' || p === 'null:') {
        return 'http://127.0.0.1:8000';
    }
    return '';
}

const API_BASE = resolveApiBase();
window.API_BASE = API_BASE;

/** Для TypeError / мережевих збоїв fetch — зрозуміле повідомлення українською */
function isNetworkishError(err) {
    if (!err) return false;
    if (err.name === 'TypeError') return true;
    const m = String(err.message || '');
    return /network|fetch|load failed|failed to fetch/i.test(m);
}
window.formatFetchError = function formatFetchError(err, fallback) {
    if (isNetworkishError(err)) {
        return 'Не вдалося з’єднатися з сервером. Запустіть API (uvicorn або docker compose) і відкрийте сайт за http://127.0.0.1:8000/, а не як файл із диска. Якщо фронт на іншому порті — додайте до адреси ?stem_api_base=http://127.0.0.1:8000';
    }
    return fallback != null ? fallback : (err && err.message) ? err.message : 'Сталася помилка';
};

/** Поширені коди помилок API (англ.) → українська для UI */
window.API_ERROR_UK = {
    'Invalid credentials': 'Невірний email або пароль',
    'Not authenticated': 'Потрібна авторизація',
    'Too many requests': 'Забагато запитів. Спробуйте пізніше.',
    'Too many failed attempts': 'Забагато невдалих спроб. Спробуйте пізніше.',
    'Email already registered': 'Цей email уже зареєстровано',
    'Invalid or missing invite': 'Невірний або відсутній код запрошення',
    'Only students can access personal recommendations': 'Персональні рекомендації лише для учнів',
    'Insufficient permissions': 'Недостатньо прав',
    'Survey not found': 'Опитування не знайдено',
    'Already submitted': 'Ви вже надіслали відповіді на це опитування',
    'New password must be at least 8 characters': 'Новий пароль має бути не коротшим за 8 символів',
    'Current password is incorrect': 'Поточний пароль введено невірно',
    'School name required': 'Вкажіть назву школи',
    'Invalid name': 'Некоректна назва',
    'User not found': 'Користувача не знайдено',
    'School not found': 'Школу не знайдено',
    'Invalid student in bulk list': 'У списку є рядок з некоректним учнем (потрібна роль student)',
    'Class not found': 'Клас не знайдено',
    'No fields to update': 'Немає полів для оновлення',
    'Invalid role': 'Некоректна роль',
    'Invalid CSV row': 'Некоректний рядок CSV',
    'Invalid CSV encoding': 'Некоректне кодування CSV',
    'No rows in CSV': 'У CSV немає рядків даних',
    'Internal Server Error': 'Внутрішня помилка сервера',
    'Registration rate limited':
        'З однієї IP-адреси можна зареєструватися не частіше ніж раз на 10 хвилин. Почекайте і спробуйте знову.',
    'Resend verification rate limited': 'Забагато запитів на повторне надсилання листа. Почекайте.',
    'Passwords do not match': 'Паролі не збігаються',
    'Email not verified': 'Спочатку підтвердіть email за посиланням з листа',
    'Invalid captcha': 'Невірна відповідь на капчу',
    'Invalid or expired captcha': 'Капча застаріла або некоректна. Натисніть «Інше завдання».',
    'Password too short': 'Пароль закороткий (мінімум 8 символів)',
    'Password too long': 'Пароль задовгий',
    'Password needs uppercase': 'Додайте хоча б одну велику літеру',
    'Password needs lowercase': 'Додайте хоча б одну малу літеру',
    'Password needs digit': 'Додайте хоча б одну цифру',
    'Password needs special character': 'Додайте спецсимвол (!@#$%^&*…)',
    'Invalid or expired verification link': 'Посилання недійсне або застаріле',
    'Email verification not configured': 'Підтвердження пошти не налаштовано на сервері',
    'Database schema outdated':
        'База даних не відповідає коду: застосуйте міграції (у каталозі проєкту: docker compose run --rm api alembic upgrade head або docker compose up --build).',
    'Database unavailable': 'База даних тимчасово недоступна (перевірте, що контейнер db запущений і DATABASE_URL коректний).',
    'Invalid school_id': 'Вказано некоректний ідентифікатор школи. Залиште поле порожнім або оберіть існуючу школу.',
};

function translateApiDetail(detail) {
    if (detail == null || detail === '') return 'Сталася помилка';
    if (typeof detail === 'string') {
        return window.API_ERROR_UK[detail] || detail;
    }
    if (Array.isArray(detail)) {
        if (!detail.length) return 'Сталася помилка';
        return detail
            .map((e) => {
                if (typeof e === 'string') return e;
                if (e && typeof e.msg === 'string') return e.msg;
                if (e && typeof e.message === 'string') return e.message;
                try {
                    return JSON.stringify(e);
                } catch {
                    return '';
                }
            })
            .filter(Boolean)
            .join('; ');
    }
    if (typeof detail === 'object' && detail !== null) {
        if (typeof detail.msg === 'string') return detail.msg;
        try {
            return JSON.stringify(detail);
        } catch {
            return '';
        }
    }
    return String(detail);
}
window.translateApiDetail = translateApiDetail;

function messageForHttpError(status, statusText, detailText) {
    const hasUsableDetail = (function () {
        if (detailText === undefined || detailText === null) return false;
        if (typeof detailText === 'string' && detailText.length === 0) return false;
        if (Array.isArray(detailText) && detailText.length === 0) return false;
        return true;
    })();

    if (hasUsableDetail) {
        const raw = translateApiDetail(detailText);
        const generic = raw === 'Сталася помилка' || (typeof raw === 'string' && raw.trim() === '');
        if (!generic) return raw;
    }

    if (status === 503) {
        if (typeof detailText === 'string' && window.API_ERROR_UK[detailText]) {
            return window.API_ERROR_UK[detailText];
        }
        return 'Сервіс або база даних тимчасово недоступні. Перевірте docker compose logs api та виконайте alembic upgrade head.';
    }
    if (status === 500) {
        return 'Помилка сервера (500). Найчастіше: база даних недоступна або не застосовані міграції. Перегляньте логи: docker compose logs api';
    }
    if (status === 422) {
        return 'Некоректні дані (перевірте email і пароль не коротший за 8 символів).';
    }
    if (status === 429) {
        if (typeof detailText === 'string' && window.API_ERROR_UK[detailText]) {
            return window.API_ERROR_UK[detailText];
        }
        return window.API_ERROR_UK['Too many requests'] || 'Забагато запитів. Спробуйте пізніше.';
    }
    const line = [String(status), statusText || ''].filter(Boolean).join(' ').trim();
    return line ? `Помилка ${line}` : 'Сталася помилка';
}

const STEM_TOKEN_KEY = 'token';

function getToken() {
    return localStorage.getItem(STEM_TOKEN_KEY);
}
window.getToken = getToken;

/** Оновлення сесії в інших вкладках (localStorage) + BroadcastChannel у межах origin */
(function initCrossTabAuth() {
    try {
        const ch = new BroadcastChannel('stem-auth');
        ch.addEventListener('message', (ev) => {
            if (ev.data && ev.data.type === 'stem-token' && typeof ev.data.token === 'string') {
                try {
                    localStorage.setItem(STEM_TOKEN_KEY, ev.data.token);
                } catch (e) { /* ignore */ }
            }
        });
        window.__stemAuthChannel = ch;
    } catch (e) { /* no BroadcastChannel */ }
    window.addEventListener('storage', (e) => {
        if (e.key === STEM_TOKEN_KEY) {
            try {
                window.dispatchEvent(new CustomEvent('stem-token-changed', { detail: { newValue: e.newValue } }));
            } catch (err) { /* ignore */ }
        }
    });
})();

window.setAuthToken = function setAuthToken(token) {
    try {
        localStorage.setItem(STEM_TOKEN_KEY, token);
        if (window.__stemAuthChannel) {
            window.__stemAuthChannel.postMessage({ type: 'stem-token', token });
        }
    } catch (e) { /* private mode */ }
};

window.clearAuthToken = function clearAuthToken() {
    try {
        localStorage.removeItem(STEM_TOKEN_KEY);
        if (window.__stemAuthChannel) {
            window.__stemAuthChannel.postMessage({ type: 'stem-token', token: '' });
        }
    } catch (e) { /* ignore */ }
};

/** JSON-запит з токеном; при помилці кидає Error з перекладеним повідомленням */
async function apiJson(path, options = {}) {
    let res;
    try {
        res = await apiFetch(path, options);
    } catch (err) {
        throw new Error(window.formatFetchError(err));
    }
    const text = await res.text();
    let data = {};
    if (text) {
        try {
            data = JSON.parse(text);
        } catch {
            data = { _nonJsonBody: text.slice(0, 400) };
        }
    }
    if (!res.ok) {
        const detail =
            data.detail !== undefined
                ? data.detail
                : data.message !== undefined
                  ? data.message
                  : data._nonJsonBody;
        const msg = messageForHttpError(res.status, res.statusText, detail);
        const err = new Error(msg);
        err.status = res.status;
        err.raw = data;
        throw err;
    }
    return data;
}
window.apiJson = apiJson;

function isPublicAuthPath(path) {
    return (
        path === '/api/auth/login' ||
        path === '/api/auth/register' ||
        path === '/api/auth/register-staff' ||
        path === '/api/auth/register-captcha' ||
        path === '/api/auth/verify-email' ||
        path === '/api/auth/resend-verification'
    );
}

function apiFetch(path, options = {}) {
    const token = getToken();
    const sendAuth = token && !isPublicAuthPath(path);
    const headers = {
        'Content-Type': 'application/json',
        ...(sendAuth && { Authorization: 'Bearer ' + token }),
        ...options.headers,
    };
    return fetch(API_BASE + path, { ...options, headers });
}

/** Кнопка «Показати» / «Приховати» для поля пароля */
function wirePasswordToggle(button, input) {
    if (!button || !input) return;
    function sync() {
        const hidden = input.getAttribute('type') === 'password';
        button.setAttribute('aria-pressed', hidden ? 'false' : 'true');
        button.setAttribute('aria-label', hidden ? 'Показати пароль' : 'Приховати пароль');
        button.textContent = hidden ? 'Показати' : 'Приховати';
    }
    button.addEventListener('click', () => {
        const next = input.getAttribute('type') === 'password' ? 'text' : 'password';
        input.setAttribute('type', next);
        sync();
    });
    sync();
}
window.wirePasswordToggle = wirePasswordToggle;

/**
 * Сесія зберігається в localStorage між сторінками. Оновлює посилання «Увійти» / «Реєстрація»
 * у шапці та на головній: для авторизованих — «Кабінет» / «Обліковий запис».
 */
window.stemApplyPublicNavAuth = async function stemApplyPublicNavAuth() {
    const tok = getToken();
    let cabinet = null;
    if (tok) {
        try {
            const res = await fetch(API_BASE + '/api/me', {
                headers: { Authorization: 'Bearer ' + tok },
            });
            if (res.status === 401) {
                clearAuthToken();
            } else if (res.ok) {
                const u = await res.json();
                cabinet =
                    u.account_kind === 'student' ? 'student-hub.html' : 'dashboard.html';
            } else {
                cabinet = 'dashboard.html';
            }
        } catch (e) {
            /* мережа: залишаємо посилання на вхід, токен не чіпаємо */
        }
    }

    document.querySelectorAll('a.stem-auth-login').forEach((a) => {
        if (cabinet) {
            a.setAttribute('href', cabinet);
            a.textContent = a.getAttribute('data-stem-label-in') || 'Кабінет';
        } else {
            a.setAttribute('href', 'login.html');
            a.textContent = a.getAttribute('data-stem-label-out') || 'Увійти';
        }
    });

    document.querySelectorAll('a.stem-auth-register').forEach((a) => {
        if (cabinet) {
            a.setAttribute('href', 'account.html');
            a.textContent = a.getAttribute('data-stem-reg-in') || 'Обліковий запис';
        } else {
            a.setAttribute('href', 'register.html');
            a.textContent = a.getAttribute('data-stem-reg-out') || 'Реєстрація';
        }
    });

    document.querySelectorAll('a.stem-auth-inline').forEach((a) => {
        if (cabinet) {
            a.setAttribute('href', 'account.html');
            const t = a.getAttribute('data-stem-text-in');
            if (t) a.textContent = t;
        } else {
            a.setAttribute('href', 'register.html');
            const t = a.getAttribute('data-stem-text-out');
            if (t) a.textContent = t;
        }
    });
};

/** Якщо вже є валідна сесія — одразу в кабінет (сторінки login / register). */
window.stemRedirectIfLoggedIn = async function stemRedirectIfLoggedIn() {
    const tok = getToken();
    if (!tok) return;
    try {
        const res = await fetch(API_BASE + '/api/me', {
            headers: { Authorization: 'Bearer ' + tok },
        });
        if (res.status === 401) {
            clearAuthToken();
            return;
        }
        if (!res.ok) return;
        const u = await res.json();
        const href =
            u.account_kind === 'student' ? 'student-hub.html' : 'dashboard.html';
        window.location.replace(href);
    } catch (e) {
        /* залишити на сторінці входу */
    }
};

(function initStemPublicAuthUi() {
    function run() {
        if (
            document.querySelector(
                'a.stem-auth-login, a.stem-auth-register, a.stem-auth-inline'
            )
        ) {
            stemApplyPublicNavAuth();
        }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', run);
    } else {
        run();
    }
    window.addEventListener('stem-token-changed', () => {
        stemApplyPublicNavAuth();
    });
})();

/** Меню в шапці на вузьких екранах (☰) */
function wireMobileNav() {
    const toggle = document.querySelector('.mobile-toggle');
    const nav = document.querySelector('.header .nav');
    if (!toggle || !nav) return;
    toggle.addEventListener('click', () => {
        const open = nav.classList.toggle('open');
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.querySelectorAll('a').forEach((a) => {
        a.addEventListener('click', () => {
            nav.classList.remove('open');
            toggle.setAttribute('aria-expanded', 'false');
        });
    });
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireMobileNav);
} else {
    wireMobileNav();
}
