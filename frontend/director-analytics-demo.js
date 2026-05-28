(function () {
    const STEM_COLORS = { S: '#22c55e', T: '#f43f5e', E: '#f97316', M: '#3b82f6' };
    const STEM_LABELS_UK = { S: 'Наука', T: 'Технології', E: 'Інженерія', M: 'Математика' };
    function stemChartAxisLabel(code) {
        return STEM_LABELS_UK[code] || code;
    }
    const CHART_ANIM_MS = 780;

    const DIRECTOR_DEMO_ANALYTICS = {
        school_name: 'ЗЗСО №204',
        school_id: 'a0000000-0000-0000-0000-000000000204',
        survey_id: 'b0000000-0000-0000-0000-000000000001',
        classes: [
            { name: '5-А', grade: 5, class_id: 'c01', s_avg: 5.1, t_avg: 4.2, e_avg: 4.6, m_avg: 5.4, ranking: 'M-S-E-T', response_count: 26 },
            { name: '6-Б', grade: 6, class_id: 'c02', s_avg: 4.8, t_avg: 4.5, e_avg: 4.9, m_avg: 4.3, ranking: 'E-S-T-M', response_count: 24 },
            { name: '7-А', grade: 7, class_id: 'c03', s_avg: 5.2, t_avg: 4.0, e_avg: 4.4, m_avg: 5.1, ranking: 'M-S-E-T', response_count: 22 },
            { name: '8-Б', grade: 8, class_id: 'c04', s_avg: 4.6, t_avg: 4.8, e_avg: 4.2, m_avg: 4.7, ranking: 'T-M-S-E', response_count: 27 },
            { name: '9-А', grade: 9, class_id: 'c05', s_avg: 5.0, t_avg: 4.3, e_avg: 4.8, m_avg: 4.9, ranking: 'S-M-E-T', response_count: 25 },
            { name: '10-Б', grade: 10, class_id: 'c06', s_avg: 4.9, t_avg: 4.6, e_avg: 4.1, m_avg: 4.8, ranking: 'S-T-M-E', response_count: 21 },
            { name: '11-А', grade: 11, class_id: 'c07', s_avg: 5.3, t_avg: 4.9, e_avg: 4.0, m_avg: 5.0, ranking: 'S-M-T-E', response_count: 23 },
            { name: '12-Б', grade: 12, class_id: 'c08', s_avg: 5.1, t_avg: 5.2, e_avg: 4.5, m_avg: 4.9, ranking: 'T-S-M-E', response_count: 20 }
        ],
        discipline_summary: [],
        disciplines: []
    };

    function escHtml(s) {
        if (s == null || s === undefined) return '';
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
    }

    function disciplineSummaryFromClasses(rows) {
        const keys = [
            ['S', 's_avg'],
            ['T', 't_avg'],
            ['E', 'e_avg'],
            ['M', 'm_avg']
        ];
        const vals = {};
        for (let ki = 0; ki < keys.length; ki++) {
            const code = keys[ki][0];
            const k = keys[ki][1];
            const nums = [];
            for (let ri = 0; ri < rows.length; ri++) {
                const row = rows[ri];
                const v = row[k];
                if (v != null && v !== '') {
                    const f = Number(v);
                    if (!Number.isNaN(f)) nums.push(f);
                }
            }
            if (nums.length) vals[code] = nums.reduce(function (a, b) { return a + b; }, 0) / nums.length;
        }
        const codes = Object.keys(vals);
        if (!codes.length) return [];
        const total = codes.reduce(function (acc, c) { return acc + vals[c]; }, 0);
        const sorted = codes.slice().sort(function (a, b) { return vals[b] - vals[a]; });
        return sorted.map(function (code, i) {
            return {
                code: code,
                label: STEM_LABELS_UK[code] || code,
                avg: Math.round(vals[code] * 100) / 100,
                pct_share: total > 0 ? Math.round((vals[code] / total) * 1000) / 10 : 0,
                rank: i + 1
            };
        });
    }

    function splitClassesBySchoolTier(all) {
        const middle = [];
        const high = [];
        const other = [];
        (all || []).forEach(function (c) {
            const g = c.grade;
            if (g == null) { other.push(c); return; }
            if (g >= 5 && g <= 9) middle.push(c);
            else if (g >= 10 && g <= 12) high.push(c);
            else other.push(c);
        });
        return { middle: middle, high: high, other: other };
    }

    function classHasStem(c) {
        return c.s_avg != null || c.t_avg != null || c.e_avg != null || c.m_avg != null;
    }

    function destroySchoolAnalyticsCharts(root) {
        if (!root || typeof Chart === 'undefined') return;
        root.querySelectorAll('canvas[data-chart]').forEach(function (cv) {
            const ch = Chart.getChart(cv);
            if (ch) ch.destroy();
        });
    }

    function mountSchoolAnalyticsCharts(root, data) {
        if (!root || typeof Chart === 'undefined') return;
        destroySchoolAnalyticsCharts(root);
        const classes = data.classes || [];
        const donutLegendPos =
            typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(max-width: 900px)').matches
                ? 'bottom'
                : 'right';
        const narrow =
            typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(max-width: 520px)').matches;

        root.querySelectorAll('canvas[data-chart="donut"][data-school-tier]').forEach(function (donutEl) {
            const tier = donutEl.getAttribute('data-school-tier');
            let tierClasses = classes;
            if (tier === 'middle') {
                tierClasses = classes.filter(function (c) { return c.grade != null && c.grade >= 5 && c.grade <= 9; });
            } else if (tier === 'high') {
                tierClasses = classes.filter(function (c) { return c.grade != null && c.grade >= 10 && c.grade <= 12; });
            } else if (tier === 'other') {
                tierClasses = classes.filter(function (c) {
                    const g = c.grade;
                    return g == null || g < 5 || g > 12;
                });
            }
            const summary = disciplineSummaryFromClasses(tierClasses.filter(classHasStem));
            if (!summary.length) return;
            new Chart(donutEl.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: summary.map(function (d) { return stemChartAxisLabel(d.code); }),
                    datasets: [
                        {
                            data: summary.map(function (d) { return d.pct_share != null ? d.pct_share : 0; }),
                            backgroundColor: summary.map(function (d) { return STEM_COLORS[d.code] || '#64748b'; }),
                            borderColor: '#ffffff',
                            borderWidth: 2,
                            hoverOffset: 10
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: CHART_ANIM_MS, easing: 'easeOutQuart' },
                    cutout: '52%',
                    layout: { padding: { top: 4, right: 8, bottom: 4, left: 4 } },
                    interaction: { mode: 'nearest', intersect: true },
                    plugins: {
                        legend: { position: donutLegendPos, labels: { boxWidth: 14, padding: 14, font: { size: narrow ? 10 : 11 } } },
                        tooltip: {
                            clip: false,
                            caretPadding: 10,
                            maxWidth: 260,
                            bodySpacing: 4,
                            callbacks: {
                                label: function (ctx) {
                                    const i = ctx.dataIndex;
                                    const s = summary[i];
                                    if (!s) return '';
                                    return (
                                        ' середнє ' +
                                        (s.avg != null ? s.avg : '—') +
                                        ', частка ' +
                                        (s.pct_share != null ? s.pct_share + '%' : '—')
                                    );
                                },
                                afterLabel: function (ctx) {
                                    const i = ctx.dataIndex;
                                    const s = summary[i];
                                    if (!s) return '';
                                    return 'місце ' + s.rank;
                                }
                            }
                        }
                    }
                }
            });
        });

        root.querySelectorAll('canvas[data-chart="radar"][data-school-tier]').forEach(function (radarEl) {
            const tier = radarEl.getAttribute('data-school-tier');
            let tierClasses = classes;
            if (tier === 'middle') {
                tierClasses = classes.filter(function (c) { return c.grade != null && c.grade >= 5 && c.grade <= 9; });
            } else if (tier === 'high') {
                tierClasses = classes.filter(function (c) { return c.grade != null && c.grade >= 10 && c.grade <= 12; });
            } else if (tier === 'other') {
                tierClasses = classes.filter(function (c) {
                    const g = c.grade;
                    return g == null || g < 5 || g > 12;
                });
            }
            const summary = disciplineSummaryFromClasses(tierClasses.filter(classHasStem));
            if (!summary.length) return;
            const STEM_ORDER = [
                { code: 'S', labelUa: 'Наука' },
                { code: 'T', labelUa: 'Технології' },
                { code: 'E', labelUa: 'Інженерія' },
                { code: 'M', labelUa: 'Математика' }
            ];
            const dataVals = STEM_ORDER.map(function (o) {
                var row = null;
                for (var si = 0; si < summary.length; si++) {
                    if (summary[si].code === o.code) {
                        row = summary[si];
                        break;
                    }
                }
                return row && row.avg != null ? Number(row.avg) : 4;
            });
            const labelsUa = STEM_ORDER.map(function (o) { return stemChartAxisLabel(o.code); });
            new Chart(radarEl.getContext('2d'), {
                type: 'radar',
                data: {
                    labels: labelsUa,
                    datasets: [
                        {
                            label: 'Середнє по зрізу (1–7)',
                            data: dataVals,
                            borderColor: 'rgba(0, 212, 170, 0.98)',
                            backgroundColor: 'rgba(0, 212, 170, 0.18)',
                            pointBackgroundColor: dataVals.map(function (_, i) {
                                return STEM_COLORS[STEM_ORDER[i].code] || '#64748b';
                            }),
                            pointBorderColor: '#ffffff',
                            pointHoverBackgroundColor: '#ffffff',
                            pointRadius: narrow ? 3 : 4,
                            borderWidth: 2
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: CHART_ANIM_MS, easing: 'easeOutQuart' },
                    scales: {
                        r: {
                            angleLines: { color: 'rgba(148, 163, 184, 0.25)' },
                            grid: { color: 'rgba(148, 163, 184, 0.2)' },
                            pointLabels: {
                                font: {
                                    size: narrow ? 10 : 11,
                                    family: "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
                                },
                                centerPointLabels: true,
                            },
                            suggestedMin: 1,
                            suggestedMax: 7,
                            ticks: { stepSize: 1, backdropColor: 'transparent', font: { size: 10 } }
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function (ctx) {
                                    const idx = ctx.dataIndex;
                                    const ua = STEM_ORDER[idx].labelUa;
                                    return ' ' + ua + ': ' + (dataVals[idx] != null ? dataVals[idx].toFixed(2) : '—');
                                }
                            }
                        }
                    }
                }
            });
        });

        root.querySelectorAll('canvas[data-chart="bars"]').forEach(function (barEl) {
            const tier = barEl.getAttribute('data-school-tier');
            let tierClasses = classes;
            if (tier === 'middle') {
                tierClasses = classes.filter(function (c) { return c.grade != null && c.grade >= 5 && c.grade <= 9; });
            } else if (tier === 'high') {
                tierClasses = classes.filter(function (c) { return c.grade != null && c.grade >= 10 && c.grade <= 12; });
            } else if (tier === 'other') {
                tierClasses = classes.filter(function (c) {
                    const g = c.grade;
                    return g == null || g < 5 || g > 12;
                });
            }
            if (!tierClasses.length || !tierClasses.some(classHasStem)) return;
            const box = barEl.closest('.analytics-canvas-box');
            if (box) {
                const h = Math.min(880, Math.max(240, tierClasses.length * 34));
                box.style.height = h + 'px';
            }
            new Chart(barEl.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: tierClasses.map(function (c) { return c.name; }),
                    datasets: [
                        { label: 'S', data: tierClasses.map(function (c) { return c.s_avg != null ? Number(c.s_avg) : null; }), backgroundColor: STEM_COLORS.S, borderRadius: 4 },
                        { label: 'T', data: tierClasses.map(function (c) { return c.t_avg != null ? Number(c.t_avg) : null; }), backgroundColor: STEM_COLORS.T, borderRadius: 4 },
                        { label: 'E', data: tierClasses.map(function (c) { return c.e_avg != null ? Number(c.e_avg) : null; }), backgroundColor: STEM_COLORS.E, borderRadius: 4 },
                        { label: 'M', data: tierClasses.map(function (c) { return c.m_avg != null ? Number(c.m_avg) : null; }), backgroundColor: STEM_COLORS.M, borderRadius: 4 }
                    ]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: CHART_ANIM_MS, easing: 'easeOutQuart' },
                    layout: { padding: { top: narrow ? 18 : 8, right: 14, bottom: 10, left: 6 } },
                    interaction: { mode: 'index', intersect: false, axis: 'y' },
                    scales: {
                        x: {
                            type: 'linear',
                            min: 1,
                            max: 7,
                            ticks: { stepSize: 1, font: { size: narrow ? 10 : 11 } },
                            title: { display: false },
                            grid: { color: 'rgba(148, 163, 184, 0.22)' }
                        },
                        y: {
                            type: 'category',
                            offset: true,
                            ticks: { font: { size: narrow ? 9 : 11 }, autoSkip: false, padding: 8 },
                            grid: { display: false }
                        }
                    },
                    plugins: {
                        legend: { position: narrow ? 'bottom' : 'top', labels: { boxWidth: 12, font: { size: 10 }, padding: 10 } },
                        tooltip: {
                            clip: false,
                            caretPadding: 8,
                            animation: { duration: 180 },
                            callbacks: {
                                title: function (items) {
                                    if (!items.length) return '';
                                    const row = tierClasses[items[0].dataIndex];
                                    return row ? row.name : '';
                                },
                                label: function (ctx) {
                                    const lbl = ctx.dataset && ctx.dataset.label ? ctx.dataset.label : '';
                                    const raw = ctx.raw;
                                    if (raw == null || Number.isNaN(Number(raw))) return lbl + ': —';
                                    return lbl + ': ' + Number(raw).toFixed(1).replace('.', ',');
                                }
                            }
                        }
                    }
                }
            });
        });
    }

    function htmlSchoolAnalyticsViz(data, opts) {
        opts = opts || {};
        const showTitle = opts.showTitle !== false;
        const classes = data.classes || [];
        let html = '<div class="school-analytics-viz director-demo-school-viz">';
        if (showTitle) {
            const shownRaw =
                typeof window !== 'undefined' && window.stemDisplaySchoolName
                    ? window.stemDisplaySchoolName(data.school_name || '')
                    : String(data.school_name || '')
                          .replace(/ЗНЗ([\s\u00a0\u202f·]*)?[№#]/gi, 'ЗЗСО №')
                          .replace(/ЗОШ([\s\u00a0\u202f·]*)?[№#]/gi, 'ЗЗСО №');
            const shown = escHtml(shownRaw);
            html += '<p class="analytics-school-title"><strong>' + shown + '</strong></p>';
        }
        if (!classes.length) {
            html += '<p class="form-error analytics-empty-msg">Немає класів для відображення.</p></div>';
            return html;
        }
        const split = splitClassesBySchoolTier(classes);
        const tierDefs = [];
        if (split.middle.length) tierDefs.push({ key: 'middle', label: '5–9 класи (середня школа)', list: split.middle });
        if (split.high.length) tierDefs.push({ key: 'high', label: '10–12 класи', list: split.high });
        if (split.other.length) tierDefs.push({ key: 'other', label: 'Інші класи (за наявності)', list: split.other });
        const hasStem = classes.some(classHasStem);
        if (!hasStem) {
            html += '<div class="analytics-chart-placeholder analytics-viz-empty" style="margin-bottom:1rem"><p>Немає даних STEM для цього зведення.</p></div>';
        } else {
            html += '<div class="analytics-tiers-visual">';
            tierDefs.forEach(function (td) {
                const tierHasStem = td.list.some(classHasStem);
                html += '<h5 class="analytics-tier-heading">' + escHtml(td.label) + '</h5>';
                if (!tierHasStem) {
                    html += '<div class="analytics-chart-placeholder analytics-tier-skip"><p>У цьому зрізі немає даних.</p></div>';
                    return;
                }
                html += '<div class="analytics-tier-visual-row">';
                html += '<section class="analytics-chart-card analytics-chart-card--tier-donut">';
                html += '<h6 class="analytics-chart-subheading">STEM-дисципліни</h6>';
                html +=
                    '<div class="analytics-canvas-box analytics-canvas-box--donut"><canvas data-chart="donut" data-school-tier="' +
                    escHtml(td.key) +
                    '" role="img"></canvas></div>';
                html += '</section>';
                html += '<section class="analytics-chart-card analytics-chart-card--tier-radar">';
                html += '<h6 class="analytics-chart-subheading">Діаграма «Профіль STEM»</h6>';
                html +=
                    '<div class="analytics-canvas-box analytics-canvas-box--radar"><canvas data-chart="radar" data-school-tier="' +
                    escHtml(td.key) +
                    '" role="img"></canvas></div>';
                html += '</section>';
                html += '<section class="analytics-chart-card analytics-chart-card--tier-bars">';
                html += '<h6 class="analytics-chart-subheading">Середнє значення</h6>';
                html +=
                    '<div class="analytics-canvas-box analytics-canvas-box--bars"><canvas data-chart="bars" data-school-tier="' +
                    escHtml(td.key) +
                    '" role="img"></canvas></div>';
                html += '</section>';
                html += '</div>';
            });
            html += '</div>';
        }
        html += '<h3 class="analytics-table-heading">Таблиця</h3>';
        tierDefs.forEach(function (td) {
            html += '<h4 class="analytics-table-tier">' + escHtml(td.label) + '</h4>';
            html +=
                '<div class="analytics-table-wrap"><table class="analytics-data-table"><thead><tr><th>Клас</th><th>S</th><th>T</th><th>E</th><th>M</th><th>Ранг</th><th title="Проходжень опитування по класу">n</th></tr></thead><tbody>';
            td.list.forEach(function (c) {
                const n = c.response_count != null ? c.response_count : '—';
                html +=
                    '<tr><td data-label="Клас">' +
                    escHtml(c.name) +
                    '</td><td data-label="S">' +
                    (c.s_avg != null ? c.s_avg : '—') +
                    '</td><td data-label="T">' +
                    (c.t_avg != null ? c.t_avg : '—') +
                    '</td><td data-label="E">' +
                    (c.e_avg != null ? c.e_avg : '—') +
                    '</td><td data-label="M">' +
                    (c.m_avg != null ? c.m_avg : '—') +
                    '</td><td data-label="Ранг">' +
                    escHtml(c.ranking || '—') +
                    '</td><td data-label="n">' +
                    n +
                    '</td></tr>';
            });
            html += '</tbody></table></div>';
        });
        html += '</div>';
        return html;
    }

    function initDirectorDemo() {
        const mount = document.getElementById('directorDemoVizMount');
        if (!mount || mount.dataset.stemInited === '1') return;
        try {
            mount.innerHTML = htmlSchoolAnalyticsViz(DIRECTOR_DEMO_ANALYTICS, { showTitle: true });
            const root = mount.querySelector('.school-analytics-viz');
            if (root) mountSchoolAnalyticsCharts(root, DIRECTOR_DEMO_ANALYTICS);
            mount.dataset.stemInited = '1';
        } catch (e) {
            mount.innerHTML =
                '<p class="form-error analytics-empty-msg">Не вдалося побудувати демо-аналітику. Оновіть сторінку або перевірте, чи підвантажився Chart.js.</p>';
        }
    }

    /** Після зняття hidden у деяких браузерах канвас матиме нульовий розмір, якщо ініціалізувати Chart одразу. */
    function runDirectorChartsAfterReveal(btn, panel) {
        if (panel) {
            panel.hidden = false;
            panel.removeAttribute('hidden');
        }
        if (btn) {
            btn.setAttribute('aria-expanded', 'true');
            btn.textContent = 'Сховати демо для директора';
        }
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                initDirectorDemo();
                resizeDirectorDemoCharts();
                requestAnimationFrame(resizeDirectorDemoCharts);
            });
        });
    }

    function hideDirectorDemo(btn, panel) {
        if (!panel) return;
        panel.hidden = true;
        panel.setAttribute('hidden', '');
        if (btn) {
            btn.setAttribute('aria-expanded', 'false');
            btn.textContent = 'Демо для директора';
        }
    }

    function resizeDirectorDemoCharts() {
        const Chart = typeof window !== 'undefined' ? window.Chart : null;
        if (!Chart) return;
        const mount = document.getElementById('directorDemoVizMount');
        if (!mount) return;
        mount.querySelectorAll('canvas').forEach(function (canvas) {
            const ch = Chart.getChart(canvas);
            if (ch) ch.resize();
        });
    }

    function openDirectorDashboardFromHash(btn, panel) {
        if (!btn || !panel) return false;
        if (typeof window.location.hash !== 'string' || window.location.hash !== '#director-dashboard')
            return false;
        runDirectorChartsAfterReveal(btn, panel);
        requestAnimationFrame(function () {
            var dock = typeof document !== 'undefined' ? document.getElementById('director-dashboard') : null;
            try {
                (dock || panel).scrollIntoView({ behavior: 'smooth', block: 'start' });
            } catch (e) {
                try {
                    panel.scrollIntoView();
                } catch (e2) {}
            }
        });
        return true;
    }

    function bindDirectorReveal() {
        const btn = document.getElementById('directorDemoToggle');
        const panel = document.getElementById('directorDemoCollapsible');
        const toggle = function () {
            if (!btn || !panel) return;
            const willShow = !!panel.hidden;
            if (willShow) {
                runDirectorChartsAfterReveal(btn, panel);
            } else {
                hideDirectorDemo(btn, panel);
            }
        };
        if (btn && panel) {
            btn.addEventListener('click', toggle);
            openDirectorDashboardFromHash(btn, panel);
            window.addEventListener('hashchange', function () {
                openDirectorDashboardFromHash(btn, panel);
            });
            return true;
        }
        return false;
    }

    function stemBootDirectorReveal() {
        bindDirectorReveal();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', stemBootDirectorReveal);
    } else {
        stemBootDirectorReveal();
    }
})();
