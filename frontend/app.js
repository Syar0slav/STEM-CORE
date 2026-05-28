const STEM_API_LS = 'stem_api_base';

function resolveApiBase() {
    if (typeof window === 'undefined' || !window.location) return '';
    try {
        const params = new URLSearchParams(window.location.search);
        const q = params.get('stem_api_base') || params.get('api_base');
        if (q) {
            const normalized = q.replace(/\/$/, '');
            try {
                localStorage.setItem(STEM_API_LS, normalized);
            } catch (e) {}
            return normalized;
        }
    } catch (e) {}
    try {
        const stored = localStorage.getItem(STEM_API_LS);
        if (stored) return stored.replace(/\/$/, '');
    } catch (e) {}
    const p = window.location.protocol;
    if (p === 'file:' || p === 'null:') {
        return 'http://127.0.0.1:8000';
    }
    return '';
}

const API_BASE = resolveApiBase();
window.API_BASE = API_BASE;

window.stemDisplaySchoolName = function stemDisplaySchoolName(name) {
    if (name == null || name === undefined) return '';
    return String(name)
        .replace(/ЗНЗ([\s\u00a0\u202f·]*)?[№#]/gi, 'ЗЗСО №')
        .replace(/ЗОШ([\s\u00a0\u202f·]*)?[№#]/gi, 'ЗЗСО №');
};

function isNetworkishError(err) {
    if (!err) return false;
    if (err.name === 'TypeError') return true;
    const m = String(err.message || '');
    return /network|fetch|load failed|failed to fetch/i.test(m);
}

window.formatFetchError = function formatFetchError(err, fallback) {
    if (isNetworkishError(err)) {
        return 'Не вдалося з’єднатися з сервером. Перевірте підключення до мережі або зверніться до адміністратора платформи.';
    }
    return fallback != null ? fallback : (err && err.message) ? err.message : 'Сталася помилка';
};

window.API_ERROR_UK = {
    'Invalid credentials': 'Невірний email або пароль',
    'Not authenticated': 'Потрібна авторизація',
    'Too many requests': 'Забагато запитів. Спробуйте пізніше.',
    'Too many failed attempts': 'Забагато невдалих спроб. Спробуйте пізніше.',
    'Email already registered': 'Цей email уже зареєстровано',
    'Invalid or missing invite': 'Невірний або відсутній код запрошення',
    'Only students can access personal recommendations': 'Персональні рекомендації лише для учнів',
    'Insufficient permissions': 'Недостатньо прав',
    'Teacher profile available only for teaching accounts':
        'Профіль доступний лише для облікового запису вчителя (після прив’язки до класів)',
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
        'Сервіс тимчасово недоступний через налаштування бази даних. Зверніться до адміністратора.',
    'Database unavailable': 'База даних тимчасово недоступна. Спробуйте пізніше або зверніться до адміністратора.',
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
        return 'Сервіс тимчасово недоступний. Спробуйте пізніше або зверніться до адміністратора.';
    }
    if (status === 500) {
        return 'Помилка сервера. Спробуйте пізніше або зверніться до адміністратора.';
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

(function initCrossTabAuth() {
    try {
        const ch = new BroadcastChannel('stem-auth');
        ch.addEventListener('message', (ev) => {
            if (ev.data && ev.data.type === 'stem-token' && typeof ev.data.token === 'string') {
                try {
                    localStorage.setItem(STEM_TOKEN_KEY, ev.data.token);
                } catch (e) {}
            }
        });
        window.__stemAuthChannel = ch;
    } catch (e) {}
    window.addEventListener('storage', (e) => {
        if (e.key === STEM_TOKEN_KEY) {
            try {
                window.dispatchEvent(new CustomEvent('stem-token-changed', { detail: { newValue: e.newValue } }));
            } catch (err) {}
        }
    });
})();

window.setAuthToken = function setAuthToken(token) {
    try {
        localStorage.setItem(STEM_TOKEN_KEY, token);
        if (window.__stemAuthChannel) {
            window.__stemAuthChannel.postMessage({ type: 'stem-token', token });
        }
    } catch (e) {}
};

window.clearAuthToken = function clearAuthToken() {
    try {
        localStorage.removeItem(STEM_TOKEN_KEY);
        if (window.__stemAuthChannel) {
            window.__stemAuthChannel.postMessage({ type: 'stem-token', token: '' });
        }
    } catch (e) {}
};

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
                    u.account_kind === 'student'
                        ? 'student-hub.html'
                        : u.account_kind === 'teacher'
                          ? 'teacher-hub.html'
                          : 'dashboard.html';
            } else {
                cabinet = 'dashboard.html';
            }
        } catch (e) {}
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

window.stemCabinetHrefForAccountKind = function stemCabinetHrefForAccountKind(kind) {
    if (kind === 'student') return 'student-hub.html';
    if (kind === 'teacher') return 'teacher-hub.html';
    return 'dashboard.html';
};

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
            u.account_kind === 'student'
                ? 'student-hub.html'
                : u.account_kind === 'teacher'
                  ? 'teacher-hub.html'
                  : 'dashboard.html';
        window.location.replace(href);
    } catch (e) {}
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
