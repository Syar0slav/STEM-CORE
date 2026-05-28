/**
 * Графіки кабінету вчителя: стовпчики за профільною лінією (або усередненням)
 * і коло «≥6 / <6». Якщо axisToggleHostId не передано — лише один показник по домену вчителя.
 * Залежить від Chart.js (глобально Chart).
 */
(function (global) {
    var Chart = global.Chart;
    if (!Chart) return;

    var AVG_PROP = { S: 's_avg', T: 't_avg', E: 'e_avg', M: 'm_avg' };
    var STEM_ORDER = ['S', 'T', 'E', 'M'];
    /** Підписи без латинських літер у дужках, окрім математики (M). */
    var DOMAIN_LABEL = {
        S: 'Наука',
        T: 'Технології',
        E: 'Інженерія',
        M: 'Математика (M)',
    };
    var BAR_COLOR = {
        S: 'rgba(239, 83, 80, 0.88)',
        T: 'rgba(66, 165, 245, 0.88)',
        E: 'rgba(171, 71, 188, 0.88)',
        M: 'rgba(102, 187, 106, 0.88)',
    };
    var DONUT_SALAD = '#9CCC65';
    var DONUT_BLUE = '#42A5F6';
    /** Підписи сегментів кола (у легенді й підказках). */
    var DONUT_LABEL_INTEREST = 'Класи з зацікавленням';
    var DONUT_LABEL_WORK = 'Класи з необхідним доопрацюванням';

    /**
     * Підказка donut Chart.js не переносить довгі рядки за шириною canvas.
     * Ліміти: DONUT_TOOLTIP_MAX_CHARS_PER_LINE (48), заголовок і пояс — по 2 логічні рядки.
     */
    var DONUT_TOOLTIP_MAX_CHARS_PER_LINE = 48;
    /** Максимум рядків для заголовка й для пояснення в секції підказки. */
    var DONUT_TOOLTIP_TITLE_MAX_LINES = 2;
    var DONUT_TOOLTIP_EXPL_MAX_LINES = 2;

    /** Один логічний рядок підказки; довший текст обрізається з …. */
    function clipOneTooltipLine(text, maxLen) {
        text = String(text == null ? '' : text).trim();
        if (!text.length) return '';
        if (maxLen < 12) maxLen = 48;
        if (text.length <= maxLen) return text;
        var snip = text.slice(0, maxLen - 1).trimEnd();
        var sp = snip.lastIndexOf(' ');
        if (sp > Math.floor(maxLen * 0.35)) snip = snip.slice(0, sp).trimEnd();
        return snip + '…';
    }

    /**
     * Абзац у кілька логічних рядків для підказки (Chart.js малює кожен окремо).
     */
    function wrapTooltipParagraph(text, maxLen, maxLines) {
        text = String(text == null ? '' : text).replace(/\s+/g, ' ').trim();
        if (!text.length) return [];
        if (maxLen < 16) maxLen = DONUT_TOOLTIP_MAX_CHARS_PER_LINE;
        maxLines = Math.max(1, Math.floor(Number(maxLines) || 2));
        var words = text.split(' ');
        var raw = [];
        var line = '';
        for (var wi = 0; wi < words.length; wi++) {
            var w = words[wi];
            var next = line ? line + ' ' + w : w;
            if (next.length <= maxLen) line = next;
            else {
                if (line) raw.push(line);
                line = w.length > maxLen ? clipOneTooltipLine(w, maxLen) : w;
            }
        }
        if (line) raw.push(line);

        if (raw.length <= maxLines) {
            return raw.map(function (ln) {
                return clipOneTooltipLine(ln, maxLen);
            });
        }
        var head = raw.slice(0, maxLines - 1).map(function (ln) {
            return clipOneTooltipLine(ln, maxLen);
        });
        head.push(clipOneTooltipLine(raw.slice(maxLines - 1).join(' '), maxLen));
        return head;
    }

    function klassWord(n) {
        var nAbs = Math.abs(Math.floor(Number(n))) % 100;
        var n10 = nAbs % 10;
        if (nAbs > 10 && nAbs < 20) return 'класів';
        if (n10 === 1) return 'клас';
        if (n10 >= 2 && n10 <= 4) return 'класи';
        return 'класів';
    }

    function classDisplayForTooltip(c) {
        return (
            (c.name != null ? String(c.name) : '') +
            ', ' +
            (c.grade != null ? String(c.grade) : '?') +
            '-й клас'
        );
    }

    function destroyChart(canvas) {
        if (!canvas) return;
        var ch = Chart.getChart(canvas);
        if (ch) ch.destroy();
    }

    function scoreForSpecialty(model, letter) {
        if (!model) return null;
        var L = String(letter || '').toUpperCase();
        if (L && AVG_PROP[L]) {
            var v = model[AVG_PROP[L]];
            return v != null && v !== '' ? Number(v) : null;
        }
        var vals = STEM_ORDER.map(function (k) {
            var x = model[AVG_PROP[k]];
            return x != null && x !== '' ? Number(x) : null;
        }).filter(function (x) {
            return x != null && !Number.isNaN(x);
        });
        if (!vals.length) return null;
        var s = 0;
        for (var i = 0; i < vals.length; i++) s += vals[i];
        return s / vals.length;
    }

    function Mount(opts) {
        this.opts = opts || {};
        this.classes = opts.classes || [];
        this.modelsByClassId = opts.modelsByClassId || {};
        this.specialty = String(opts.specialtyLetter || '').toUpperCase();
        /** Без axisToggleHostId — один домен вчителя (або усереднений профіль). */
        this.singleSubjectBars = !this.opts.axisToggleHostId;
        this.barChart = null;
        this.donutChart = null;
        this.excluded = {};
        this.axesShown = { S: true, T: true, E: true, M: true };
        this.donutSalad = true;
        this.donutBlue = true;
        this._buildClassToggles();
        this._buildAxisToggles();
        this._wireDonutChecks();
        this.render();
    }

    Mount.prototype.getIncludedClasses = function () {
        return this._includedClasses().slice();
    };

    Mount.prototype.setStatus = function (msg) {
        var el = document.getElementById(this.opts.statusElId);
        if (el) el.textContent = msg || '';
    };

    Mount.prototype.setClasses = function (classes) {
        this.classes = classes || [];
        this.excluded = {};
        this._buildClassToggles();
        this.render();
    };

    Mount.prototype.setModels = function (map) {
        this.modelsByClassId = map || {};
        this.render();
    };

    Mount.prototype.setSpecialty = function (letter) {
        this.specialty = String(letter || '').toUpperCase();
        if (!this.singleSubjectBars) this._buildAxisToggles();
        this.render();
    };

    Mount.prototype._includedClasses = function () {
        var self = this;
        return this.classes.filter(function (c) {
            return !self.excluded[c.id];
        });
    };

    /**
     * Кругова діаграма та підпис «класів — N»: той самий набір, що й галочки «Класи».
     */
    Mount.prototype._donutPopulationClasses = function () {
        return this._includedClasses();
    };

    /**
     * Стовпчикова діаграма: галочки «Класи» + ті самі категорії, що перемикачі зліва секції donut (≥6 / <6).
     */
    Mount.prototype._classesForBarChart = function () {
        var self = this;
        var saladOn = !!self.donutSalad;
        var blueOn = !!self.donutBlue;
        if (!saladOn && !blueOn) return [];

        var fromCheckboxes = self._includedClasses();
        if (saladOn && blueOn) return fromCheckboxes.slice();

        return fromCheckboxes.filter(function (c) {
            var sc = scoreForSpecialty(self.modelsByClassId[c.id], self.specialty);
            if (sc == null || Number.isNaN(sc)) return false;
            return saladOn ? sc >= 6 : sc < 6;
        });
    };

    Mount.prototype._buildClassToggles = function () {
        var host = document.getElementById(this.opts.classListHostId);
        if (!host) return;
        host.innerHTML = '';
        var self = this;
        if (!this.classes.length) {
            host.innerHTML =
                '<span class="teacher-hub-chart-quiet">Немає класів для відображення.</span>';
            return;
        }
        this.classes.forEach(function (c) {
            var id = 'tc-inc-' + String(c.id).replace(/[^a-zA-Z0-9_-]/g, '');
            var label = document.createElement('label');
            label.className = 'teacher-hub-class-toggle';
            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = !self.excluded[c.id];
            cb.id = id;
            cb.addEventListener('change', function () {
                if (cb.checked) delete self.excluded[c.id];
                else self.excluded[c.id] = true;
                self.render();
            });
            label.appendChild(cb);
            var text =
                ' ' +
                (c.name != null ? String(c.name) : '') +
                ', ' +
                (c.grade != null ? String(c.grade) : '?') +
                '-й клас';
            label.appendChild(document.createTextNode(text));
            host.appendChild(label);
        });
    };

    Mount.prototype._buildAxisToggles = function () {
        if (this.singleSubjectBars) return;
        var host = document.getElementById(this.opts.axisToggleHostId);
        if (!host) return;
        host.innerHTML = '';
        var self = this;
        STEM_ORDER.forEach(function (axis) {
            var label = document.createElement('label');
            label.className = 'teacher-hub-axis-toggle';
            if (self.specialty === axis) label.classList.add('teacher-hub-axis-toggle--specialty');
            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = !!self.axesShown[axis];
            cb.addEventListener('change', function () {
                self.axesShown[axis] = cb.checked;
                self.render();
            });
            label.appendChild(cb);
            label.appendChild(document.createTextNode(' ' + DOMAIN_LABEL[axis]));
            host.appendChild(label);
        });
    };

    Mount.prototype._wireDonutChecks = function () {
        var self = this;
        var salad = document.getElementById(this.opts.donutSaladCheckId);
        var blue = document.getElementById(this.opts.donutBlueCheckId);
        if (salad) {
            self.donutSalad = salad.checked;
            salad.addEventListener('change', function () {
                self.donutSalad = salad.checked;
                self.render();
            });
        }
        if (blue) {
            self.donutBlue = blue.checked;
            blue.addEventListener('change', function () {
                self.donutBlue = blue.checked;
                self.render();
            });
        }
    };

    Mount.prototype.renderBar = function () {
        var canvas = document.getElementById(this.opts.barCanvasId);
        if (!canvas) return;
        destroyChart(canvas);
        var inc = this._classesForBarChart();
        var labels = inc.map(function (c) {
            return (c.name != null ? String(c.name) : '') + ' (' + (c.grade != null ? String(c.grade) : '?') + ')';
        });
        var datasets = [];
        var self = this;

        if (this.singleSubjectBars) {
            var spec = self.specialty && AVG_PROP[self.specialty] ? self.specialty : null;
            var dsLabel;
            var bg;
            var rowData = inc.map(function (c) {
                var m = self.modelsByClassId[c.id] || {};
                if (spec) {
                    var v = m[AVG_PROP[spec]];
                    return v != null && v !== '' ? Number(v) : null;
                }
                return scoreForSpecialty(m, '');
            });
            if (spec) {
                dsLabel = DOMAIN_LABEL[spec];
                bg = BAR_COLOR[spec];
            } else {
                dsLabel = 'Усереднений бал STEM';
                bg = 'rgba(102, 187, 106, 0.88)';
            }
            datasets.push({
                label: dsLabel,
                data: rowData,
                backgroundColor: bg,
                borderRadius: 6,
                borderSkipped: false,
            });
        } else {
            STEM_ORDER.forEach(function (axis) {
                if (!self.axesShown[axis]) return;
                datasets.push({
                    label: DOMAIN_LABEL[axis],
                    data: inc.map(function (c) {
                        var m = self.modelsByClassId[c.id] || {};
                        var v = m[AVG_PROP[axis]];
                        return v != null && v !== '' ? Number(v) : null;
                    }),
                    backgroundColor: BAR_COLOR[axis],
                    borderRadius: 6,
                    borderSkipped: false,
                });
            });
        }

        if (!datasets.length || !labels.length) return;

        this.barChart = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: { labels: labels, datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 0,
                        suggestedMax: 7,
                        title: { display: true, text: 'Середній бал' },
                    },
                    x: {},
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        display: datasets.length > 1,
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                var v = ctx.raw;
                                return v == null || Number.isNaN(Number(v))
                                    ? ctx.dataset.label + ': немає даних'
                                    : ctx.dataset.label + ': ' + Number(v).toFixed(2);
                            },
                        },
                    },
                },
            },
        });
    };

    Mount.prototype.renderDonut = function () {
        var canvas = document.getElementById(this.opts.donutCanvasId);
        var cap = document.getElementById(this.opts.donutCaptionId);
        if (!canvas) return;
        destroyChart(canvas);

        var inc = this._donutPopulationClasses();
        var nodata = 0;
        var strongDetails = [];
        var weakDetails = [];
        var self = this;
        var hasProfileLine = !!(self.specialty && DOMAIN_LABEL[self.specialty]);
        inc.forEach(function (c) {
            var sc = scoreForSpecialty(self.modelsByClassId[c.id], self.specialty);
            var row = { displayName: classDisplayForTooltip(c), score: sc };
            if (sc == null || Number.isNaN(sc)) nodata++;
            else if (sc >= 6) strongDetails.push(row);
            else weakDetails.push(row);
        });

        var donutSegmentMeta = [];
        var labels = [];
        var data = [];
        var colors = [];
        if (self.donutSalad && strongDetails.length > 0) {
            labels.push(DONUT_LABEL_INTEREST);
            data.push(strongDetails.length);
            colors.push(DONUT_SALAD);
            donutSegmentMeta.push({
                items: strongDetails,
                explanation: hasProfileLine
                    ? 'За результатами опитування та вашою профільною лінією середні бали класів відповідають високій зацікавленості учнів.'
                    : 'За результатами опитування середні бали класів за усередненим профілем STEM відповідають високій зацікавленості учнів.',
            });
        }
        if (self.donutBlue && weakDetails.length > 0) {
            labels.push(DONUT_LABEL_WORK);
            data.push(weakDetails.length);
            colors.push(DONUT_BLUE);
            donutSegmentMeta.push({
                items: weakDetails,
                explanation: hasProfileLine
                    ? 'За результатами опитування та вашою профільною лінією для цих класів доречно запланувати додаткову роботу з підвищення залученості.'
                    : 'За усередненим профілем STEM для цих класів доречно запланувати додаткову роботу з підвищення залученості.',
            });
        }

        if (cap) {
            var capLead = hasProfileLine
                ? 'Показник «' + DOMAIN_LABEL[self.specialty] + '»'
                : 'Усереднений профіль STEM';
            cap.textContent =
                capLead + ': класів — ' + inc.length + ', без даних — ' + nodata + '.';
        }

        if (!data.length) return;

        var metaRef = donutSegmentMeta;

        this.donutChart = new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '',
                        data: data,
                        backgroundColor: colors,
                        borderWidth: 2,
                        borderColor: '#ffffff',
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        displayColors: true,
                        caretPadding: 10,
                        padding: 12,
                        callbacks: {
                            title: function (tooltipItems) {
                                if (!tooltipItems.length) return '';
                                var ti = tooltipItems[0];
                                var seg = metaRef[ti.dataIndex];
                                if (!seg) return '';
                                var titleBase =
                                    ti.chart.data.labels && ti.chart.data.labels[ti.dataIndex]
                                        ? String(ti.chart.data.labels[ti.dataIndex])
                                        : '';
                                var n = seg.items.length;
                                var full = titleBase + ': ' + n + ' ' + klassWord(n);
                                var chunks = wrapTooltipParagraph(
                                    full,
                                    DONUT_TOOLTIP_MAX_CHARS_PER_LINE,
                                    DONUT_TOOLTIP_TITLE_MAX_LINES
                                );
                                return chunks.length ? chunks : full;
                            },
                            label: function (ctx) {
                                var seg = metaRef[ctx.dataIndex];
                                if (!seg || !seg.items.length) return '';
                                var lines = seg.items.map(function (it) {
                                    var row =
                                        it.displayName +
                                        ': середній бал ' +
                                        Number(it.score).toFixed(2);
                                    return clipOneTooltipLine(row, DONUT_TOOLTIP_MAX_CHARS_PER_LINE);
                                });
                                lines.push('');
                                wrapTooltipParagraph(
                                    seg.explanation,
                                    DONUT_TOOLTIP_MAX_CHARS_PER_LINE,
                                    DONUT_TOOLTIP_EXPL_MAX_LINES
                                ).forEach(function (ln) {
                                    lines.push(ln);
                                });
                                return lines;
                            },
                        },
                    },
                },
            },
        });
    };

    Mount.prototype.render = function () {
        var sig = this._includedClasses()
            .map(function (c) {
                return c.id;
            })
            .join('\u0001');
        this.renderBar();
        this.renderDonut();
        var cbInc = this.opts.onIncludedClassesChange;
        if (typeof cbInc === 'function' && sig !== this._includedNotifySig) {
            this._includedNotifySig = sig;
            var snapshot = this._includedClasses().slice();
            global.setTimeout(function () {
                cbInc(snapshot);
            }, 0);
        }
    };

    global.StemTeacherChartsAPI = {
        mount: function (opts) {
            return new Mount(opts);
        },
        scoreForSpecialty: scoreForSpecialty,
        DOMAIN_LABEL: DOMAIN_LABEL,
    };
})(typeof window !== 'undefined' ? window : this);
