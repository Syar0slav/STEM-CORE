/**
 * Демо інтерфейсу кабінету вчителя на головній сторінці (без API).
 */
document.addEventListener('DOMContentLoaded', function () {
    if (typeof StemTeacherChartsAPI === 'undefined') return;
    var bar = document.getElementById('demoTeacherStemBarCanvas');
    if (!bar) return;

    var gridEl = document.getElementById('demoTeacherMaterialsGrid');
    var statusEl = document.getElementById('demoTeacherMaterialsStatus');

    var DEMO_IP_MATERIALS = {
        'demo-5a': {
            items: [
                {
                    headline: 'Опори для уваги та малих кроків',
                    bullets: [
                        'Одне завдання — один малюночок: спочатку проговорити «що бачимо на малюнку», потім цифри.',
                        'Таймер усного приблизного рахунку (10–15 с) лише щоб наблизитись до відповіді, без перевірення «швидко/повільно».',
                    ],
                },
                {
                    headline: 'Звук і рух як підмога',
                    bullets: [
                        'Підспівувати лічильній послідовності вдвох із «пропуском» числа, яке доручає один учню.',
                        'Коротка фізактивізація між двома кроками задачі («два кроки вперед — два назад») без прив’язки до результату.',
                    ],
                },
            ],
        },
        'demo-5b': {
            items: [
                {
                    headline: 'Мова математики без страху запису',
                    bullets: [
                        'Ключові слова умови кольоровими маркерами: що «дають», що «просять», що «можна перевірити».',
                        'Перший запис задачі лише символами, другий усне пояснення своїми словами — потім узгодження.',
                    ],
                },
                {
                    headline: 'Підтримка самостійності',
                    bullets: [
                        'Посібник із двох смайл-позначок: «зрозуміло без підказки» / «просити слово-підказку» перед зверненням до вчителя.',
                        'Критерій маленького успіху: «назвав правильну дію, навіть якщо арифметика попливла».',
                    ],
                },
            ],
        },
        'demo-6a': {
            items: [
                {
                    headline: 'Структура таблиць і «чесні» одиниці',
                    bullets: [
                        'Заповнювати рядки таблички по одному без одночасного рахування великого результату.',
                        'Перед обчисленням повторити вголос одиницю вимірювання та що вона означає в конкретному прикладі.',
                    ],
                },
                {
                    headline: 'Помилки як навчальний матеріал',
                    bullets: [
                        'Один день на тиждень показуємо лише дороговказ «де може загубитись смисл», не оцінюємо.',
                        'Подвійна відповідь: «я би написав…» й «але є сумнів…» перед фінальною доробкою.',
                    ],
                },
            ],
        },
        'demo-6b': {
            items: [
                {
                    headline: 'Послідовність «розум → руки»',
                    bullets: [
                        'Спершу узгоджений план голосами, потім лише запис зупинено на першому переході.',
                        'Поділ дошкової задачі: один учень читає, інший малює, третій каже перевірний крок.',
                    ],
                },
                {
                    headline: 'Стабілізація темпу',
                    bullets: [
                        'Один «складний» крок робимо на половину уроку, решта часу закріплюємо знайомі патерни.',
                        'Подвоюємо задачу: та сама ситуація з меншими числами, щоб упевнитися у логіці.',
                    ],
                },
            ],
        },
        'demo-7a': {
            items: [
                {
                    headline: 'Переведення задачі словами в малюнок і таблицю',
                    bullets: [
                        'Спочатку схема, потім формула: одна задача двома доріжками (словами та «малюночком» у зошиті).',
                        'Коментоване читання умов у парах із підсвічуванням зайвих і пропущених даних.',
                    ],
                },
                {
                    headline: 'Підтримка через короткий цикл перевірки',
                    bullets: [
                        'Чеклист з трьох кроків: «що знайти → що є → який хід один» перед повним розв’язком.',
                        'Мікрозавдання на 5–7 хв з одним новим акцентом (одинець вимірювання, округлення тощо).',
                    ],
                },
            ],
        },
        'demo-7b': {
            items: [
                {
                    headline: 'Стабілізація надійності обчислень',
                    bullets: [
                        'Колонкові дії з орієнтиром на розряди плюс «контрольний приклад» однією перевіреною доріжкою.',
                        'Спільне розбирання типової помилки знака або переносу на дошці без оцінювання особистості.',
                    ],
                },
                {
                    headline: 'Зв’язок із побутом',
                    bullets: [
                        'Короткі сюжети «ціна-товар-сума», «розклад-час-дистанція» з реальністю класу або школи.',
                    ],
                },
            ],
        },
        'demo-8a': {
            items: [
                {
                    headline: 'Плавний перехід до абстракції',
                    bullets: [
                        'Від малюнка через числові приклади до узагальнення запису один раз за урок без поспіху.',
                        'Подвійний запис задачі як рівність і короткий коментар «що ми змінюємо в кроках».',
                    ],
                },
                {
                    headline: 'Самоперевірка',
                    bullets: [
                        'Два простих альтернативні способи оцінки розумності відповіді (підстановка або зворотна дія).',
                    ],
                },
            ],
        },
        'demo-9a': {
            items: [
                {
                    headline: 'Структуроване усне мислення перед записом',
                    bullets: [
                        'Коротка усна відповідь «план трьох речень» лише потім переведення рівності в символічний запис.',
                        'Спільне складання критерію успіху: «розв’язок готовий, коли…».',
                    ],
                },
                {
                    headline: 'Робота із завданням відкритого типу обмежено',
                    bullets: [
                        'Одне відкрите завдання на два уроки: перший урок лише здогадки та приклади, другий узгодження.',
                    ],
                },
            ],
        },
        'demo-10a': {
            items: [
                {
                    headline: 'Читання задачі під старшу школу',
                    bullets: [
                        'Виділити гіпотезу: «дано / знайти / припущення щодо зв’язку» перед будь-яким записом функції або рівняння.',
                        'Разом переписати умову власними термінами, потім узгодити одну офіційну формулівку класу.',
                    ],
                },
                {
                    headline: 'Кроки з пояснювальним мікротекстом',
                    bullets: [
                        'Після кожного переходу в рівність — один рядок тексту «чому ми мали право так зробити».',
                        'Підготовка до НМТ: два схожі завдання, одне робить один учень вголос без стирання чорновика іншими.',
                    ],
                },
            ],
        },
        'demo-10b': {
            items: [
                {
                    headline: 'Моделі та параметри без перегону',
                    bullets: [
                        'Одна змінна — один зміст: табличка із колонками «змінна», «сенс у словах», «одиниці», «діапазон».',
                        'Спільне малювання графа залежностей задачі лише як структури, без конкретних чисел першого заняття.',
                    ],
                },
                {
                    headline: 'Рефлексія результату',
                    bullets: [
                        'Останні 7 хв: «чи відповідає відповідь порядку величин у задачі й чи можливий інший шлях?» одним абзацом.',
                        'Артефакт для індивідуальної карти навчання: короткий чеклист «що робити першим завтра з цією темою».',
                    ],
                },
            ],
        },
        'demo-11a': {
            items: [
                {
                    headline: 'Профільність і смислові переходи',
                    bullets: [
                        'Оберіть задачу в двох трактуваннях (геометричному та алгебраїчному) навколо однієї ситуації на тиждень.',
                        'Короткі аргументи «чому наближене не дорівнює точному» з прикладом у контексті класних проєктів.',
                    ],
                },
                {
                    headline: 'Самопідготовка з опорним листком',
                    bullets: [
                        'Один еталон розв’язку й поруч місце для «мінімальної власної зміни параметра» із поясненням.',
                        'Перед контрольним — короткий список ключових обмежень з умов останніх трьох тематичних блоків.',
                    ],
                },
            ],
        },
        'demo-11b': {
            items: [
                {
                    headline: 'Паралелі математики з інженерним мисленням',
                    bullets: [
                        'Оформлення гіпотези й контр-доказів у двоколонковому тексті («я стверджую» / «що перевірити»).',
                        'Мініпроект: одна задача з реальною межею точності інструменту у класі (лінійка / додатки).',
                    ],
                },
                {
                    headline: 'Робота із стресом оцінювання',
                    bullets: [
                        'Два чорновики офіційно дозволені: перший із помилками не здається.',
                        'Після зошитного результату усне «доведення доречності знака або коренів» лише голосово в парі.',
                    ],
                },
            ],
        },
        'demo-12a': {
            items: [
                {
                    headline: 'Компактний дорожній лист перед вступом',
                    bullets: [
                        'Один аркуш із трьох тем із прогалинами («де я сильний», «де треба супровід», «перше джерело»).',
                        'Тренування узагальнювального тексту без «ідеально»: одна проблемна логіка теми описана за 90 сек.',
                    ],
                },
                {
                    headline: 'Відповідальність учня за траєкторію',
                    bullets: [
                        'Самопризначені мікроцілі на тиждень узгоджуються із консультантом із одним виміром успіху.',
                        'Публічна презентація одного задачового ходу лише аудиторії пари або трійки, не великого класу.',
                    ],
                },
            ],
        },
    };

    var DEMO_IP_FALLBACK_BLOCKS = JSON.parse(JSON.stringify(DEMO_IP_MATERIALS['demo-5a'].items));

    function demoStemModel(seed) {
        var u = (((seed ^ (seed >>> 4)) >>> 0) % 450) / 100;
        var m = Math.min(6.95, Math.max(4.45, 5.25 + ((seed % 19) / 17) + u / 17));
        return {
            s_avg: Math.round((4.5 + (seed % 7) * 0.22) * 100) / 100,
            t_avg: Math.round((4.7 + ((seed >> 3) % 6) * 0.21) * 100) / 100,
            e_avg: Math.round((5.1 + ((seed >> 5) % 5) * 0.26) * 100) / 100,
            m_avg: Math.round(m * 100) / 100,
        };
    }

    function escDemo(s) {
        var d = document.createElement('div');
        d.textContent = s == null ? '' : String(s);
        return d.innerHTML;
    }

    function renderDemoMaterials(included) {
        if (!gridEl) return;
        gridEl.innerHTML = '';
        if (statusEl) statusEl.textContent = '';
        if (!included.length) {
            if (statusEl) statusEl.textContent = 'Позначте хоч один клас вище.';
            return;
        }
        included.forEach(function (c) {
            var custom = DEMO_IP_MATERIALS[c.id];
            var items = custom && custom.items && custom.items.length ? custom.items : DEMO_IP_FALLBACK_BLOCKS;
            var panelId =
                'demoMatPanel-' +
                String(c.id).replace(/[^a-zA-Z0-9_-]/g, '');

            var folder = document.createElement('article');
            folder.className = 'teacher-hub-material-folder';

            var bar = document.createElement('div');
            bar.className = 'teacher-hub-material-folder-bar';

            var labelSpan = document.createElement('span');
            labelSpan.className = 'teacher-hub-material-folder-title';
            labelSpan.innerHTML =
                '<strong>' + escDemo(c.name) + '</strong>' + ', <span class="account-muted">' + escDemo(c.grade) + '-й клас</span>';

            var toggleBtn = document.createElement('button');
            toggleBtn.type = 'button';
            toggleBtn.className = 'btn btn-outline teacher-hub-material-folder-btn';
            toggleBtn.setAttribute('aria-expanded', 'false');
            toggleBtn.setAttribute('aria-controls', panelId);
            toggleBtn.textContent = 'Розгорнути план';

            var panel = document.createElement('div');
            panel.className = 'teacher-hub-material-folder-panel';
            panel.id = panelId;
            panel.hidden = true;
            panel.setAttribute('role', 'region');

            var bodyInner = document.createElement('div');
            bodyInner.className = 'teacher-hub-material-folder-body-inner';
            items.forEach(function (block) {
                var sec = document.createElement('section');
                sec.className = 'teacher-hub-material-block';
                sec.innerHTML =
                    '<h5 class="teacher-hub-material-h5">' + escDemo(block.headline) + '</h5>' +
                    '<ul class="teacher-hub-material-ul">' +
                    block.bullets
                        .map(function (ln) {
                            return '<li>' + escDemo(ln) + '</li>';
                        })
                        .join('') +
                    '</ul>';
                bodyInner.appendChild(sec);
            });
            panel.appendChild(bodyInner);

            var foot = document.createElement('div');
            foot.className = 'teacher-hub-material-folder-footer';
            var classPage = document.createElement('a');
            classPage.href = 'login.html';
            classPage.className = 'btn btn-outline teacher-hub-material-class-page-link';
            classPage.textContent = 'Особиста сторінка класу (матеріали, файли, відео)';
            foot.appendChild(classPage);
            panel.appendChild(foot);

            toggleBtn.addEventListener('click', function () {
                var willOpen = panel.hidden;
                panel.hidden = !willOpen;
                toggleBtn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
                toggleBtn.textContent = willOpen ? 'Згорнути' : 'Розгорнути план';
            });

            bar.appendChild(labelSpan);
            bar.appendChild(toggleBtn);
            folder.appendChild(bar);
            folder.appendChild(panel);
            gridEl.appendChild(folder);
        });
    }

    var demoClasses = [
        { id: 'demo-5a', name: '5-А', grade: 5 },
        { id: 'demo-5b', name: '5-Б', grade: 5 },
        { id: 'demo-6a', name: '6-А', grade: 6 },
        { id: 'demo-6b', name: '6-Б', grade: 6 },
        { id: 'demo-7a', name: '7-А', grade: 7 },
        { id: 'demo-7b', name: '7-Б', grade: 7 },
        { id: 'demo-8a', name: '8-А', grade: 8 },
        { id: 'demo-9a', name: '9-А', grade: 9 },
        { id: 'demo-10a', name: '10-А', grade: 10 },
        { id: 'demo-10b', name: '10-Б', grade: 10 },
        { id: 'demo-11a', name: '11-А', grade: 11 },
        { id: 'demo-11b', name: '11-Б', grade: 11 },
        { id: 'demo-12a', name: '12-А', grade: 12 },
    ];
    var demoModelsByClassId = {};
    demoClasses.forEach(function (c, i) {
        demoModelsByClassId[c.id] = demoStemModel(i * 17 + Number(c.grade || 0) + 41);
    });

    StemTeacherChartsAPI.mount({
        barCanvasId: 'demoTeacherStemBarCanvas',
        donutCanvasId: 'demoTeacherDonutCanvas',
        classListHostId: 'demoTeacherClassIncludeList',
        donutSaladCheckId: 'demoTeacherDonutSalad',
        donutBlueCheckId: 'demoTeacherDonutBlue',
        statusElId: 'demoTeacherChartStatus',
        donutCaptionId: 'demoTeacherDonutCaption',
        specialtyLetter: 'M',
        onIncludedClassesChange: renderDemoMaterials,
        classes: demoClasses,
        modelsByClassId: demoModelsByClassId,
    });
});
