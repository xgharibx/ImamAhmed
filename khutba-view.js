document.addEventListener('DOMContentLoaded', () => {
    const titleEl = document.getElementById('khutba-title');
    const metaEl = document.getElementById('khutba-meta');
    const contentEl = document.getElementById('khutba-content');
    const actionsEl = document.querySelector('.khutba-actions');

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text ?? '';
        return div.innerHTML;
    }

    function getId() {
        const params = new URLSearchParams(window.location.search);
        const fromQuery = (params.get('id') || '').trim();
        if (fromQuery) return fromQuery;

        const fromGlobal = String(window.KHUTBA_ID || '').trim();
        if (fromGlobal) return fromGlobal;

        const fromBody = String(document.body?.dataset?.khutbaId || '').trim();
        return fromBody;
    }

    function getItemId(item) {
        return String(item?.id || '').trim();
    }

    function sanitizeKhutbaHtml(rawHtml) {
        if (typeof rawHtml !== 'string' || !rawHtml.trim()) return '';

        const parser = new DOMParser();
        const doc = parser.parseFromString(rawHtml, 'text/html');

        doc.querySelectorAll('script,style,iframe,object,embed,form').forEach(el => el.remove());

        doc.querySelectorAll('*').forEach((el) => {
            for (const attr of [...el.attributes]) {
                const name = attr.name.toLowerCase();
                const value = (attr.value || '').toLowerCase();
                if (name.startsWith('on')) {
                    el.removeAttribute(attr.name);
                    continue;
                }
                if ((name === 'href' || name === 'src') && value.startsWith('javascript:')) {
                    el.removeAttribute(attr.name);
                }
            }
        });

        return (doc.body?.innerHTML || '').trim();
    }

    function htmlToPlainText(rawHtml) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(rawHtml || '', 'text/html');
        return (doc.body?.textContent || '').replace(/\r/g, '').trim();
    }

    function normalizeArabic(value) {
        return String(value || '')
            .replace(/[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g, '')
            .replace(/ـ/g, '')
            .replace(/[إأآٱ]/g, 'ا')
            .replace(/ى/g, 'ي')
            .replace(/ة/g, 'ه')
            .replace(/["“”'`’]/g, '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function splitAtColon(line) {
        const match = String(line || '').match(/^([^:：]+)\s*[:：]\s*(.+)$/);
        if (!match) return { head: line, tail: '' };
        return { head: (match[1] || '').trim(), tail: (match[2] || '').trim() };
    }

    function buildStructuredKhutbaHtmlFromText(rawText) {
        const text = String(rawText || '').replace(/\r/g, '').trim();
        if (!text) return '';

        const lines = text
            .split(/\n+/)
            .map((line) => line.replace(/\s+/g, ' ').trim())
            .filter(Boolean);

        if (!lines.length) return '';

        const parts = [];
        let listBuffer = [];
        let currentSectionOpen = false;
        let currentSectionKey = '';

        const flushList = () => {
            if (!listBuffer.length) return;
            const items = listBuffer
                .map((item) => `<li>${escapeHtml(item)}</li>`)
                .join('');
            const listClass = currentSectionKey === 'anasir'
                ? 'khutba-list khutba-list-ordered khutba-elements-list'
                : 'khutba-list khutba-list-ordered';
            parts.push(`<ol class="${listClass}">${items}</ol>`);
            listBuffer = [];
        };

        const closeSection = () => {
            flushList();
            if (currentSectionOpen) {
                parts.push('</section>');
                currentSectionOpen = false;
                currentSectionKey = '';
            }
        };

        const openSection = (key, headingText) => {
            closeSection();
            const sectionClasses = key === 'anasir'
                ? 'khutba-section-card khutba-elements-card'
                : 'khutba-section-card';
            parts.push(`<section class="${sectionClasses}">`);
            parts.push(`<h2 class="khutba-heading">${escapeHtml(headingText)}</h2>`);
            currentSectionOpen = true;
            currentSectionKey = key;
        };

        const getMainHeadingKey = (line) => {
            const n = normalizeArabic(line).replace(/^[^\u0621-\u064A0-9]+/, '');
            if (!n) return '';
            if (n.includes('عناصر الخطبه')) return 'anasir';
            if (n.includes('الخطبه الاولي')) return 'first';
            if (n.includes('الخطبه الثانيه')) return 'second';
            if (n.startsWith('الدعاء')) return 'dua';
            if (n.startsWith('الموضوع')) return 'topic';
            return '';
        };

        const toMainHeadingLabel = (key) => {
            if (key === 'anasir') return 'عَنَاصِرُ الْخُطْبَةِ';
            if (key === 'first') return 'الْخُطْبَةُ الْأُولَى';
            if (key === 'second') return 'الْخُطْبَةُ الثَّانِيَة';
            if (key === 'dua') return 'الدُّعَاءُ';
            if (key === 'topic') return 'الْمَوْضُوع';
            return '';
        };

        const isSubHeading = (line) => /^(الْعُنْصَرُ|العنصر|أولاً|ثانياً|ثالثاً|رابعاً|خامساً|سادساً|سابعاً|ثامناً|تاسعاً|عاشراً)\b/.test(line);
        const isNumberedListItem = (line) => /^\s*[0-9٠-٩]+\s*[\)\-\.:،]?\s+/.test(line);
        const isKeyPhraseLabel = (head) => {
            const n = normalizeArabic(head);
            return /^(العنصر|اولا|ثانيا|ثالثا|رابعا|خامسا|سادسا|سابعا|ثامنا|تاسعا|عاشرا|فلسفه|جهاد|الكرم|موسوعه|البخل|المسؤوليه|خطه|النصيحه|الجانب|مشاهد|جدول)\b/.test(n);
        };

        lines.forEach((line, index) => {
            const split = splitAtColon(line);
            const mainKey = getMainHeadingKey(split.head) || getMainHeadingKey(line);
            if (mainKey) {
                openSection(mainKey, toMainHeadingLabel(mainKey));
                if (split.tail) {
                    if (mainKey === 'anasir') {
                        listBuffer.push(split.tail);
                    } else {
                        parts.push(`<p class="khutba-paragraph">${escapeHtml(split.tail)}</p>`);
                    }
                }
                return;
            }

            if (isSubHeading(line)) {
                flushList();
                parts.push(`<h3 class="khutba-subheading">${escapeHtml(line)}</h3>`);
                return;
            }

            if (isNumberedListItem(line)) {
                const cleanItem = line.replace(/^\s*[0-9٠-٩]+\s*[\)\-\.:،]?\s+/, '').trim();
                if (cleanItem) {
                    listBuffer.push(cleanItem);
                }
                return;
            }

            if (currentSectionKey === 'anasir' && line.length >= 10) {
                listBuffer.push(line.replace(/^[-•]\s*/, '').trim());
                return;
            }

            if (split.tail && isKeyPhraseLabel(split.head)) {
                flushList();
                const introClass = index < 3 ? ' khutba-intro-line' : '';
                parts.push(
                    `<p class="khutba-paragraph khutba-keyline${introClass}"><span class="khutba-keyline-lead">${escapeHtml(split.head)}:</span> ${escapeHtml(split.tail)}</p>`
                );
                return;
            }

            flushList();
            const introClass = index < 3 ? ' khutba-intro-line' : '';
            parts.push(`<p class="khutba-paragraph${introClass}">${escapeHtml(line)}</p>`);
        });

        closeSection();
        return parts.join('');
    }

    function renderError(msg) {
        contentEl.innerHTML = `<div class="khutab-empty">${escapeHtml(msg)}</div>`;
    }

    function getDisplayDate(item) {
        return item?.date?.display || item?.date_display || item?.date || '';
    }

    function toKhutbaSlugUrl(item) {
        const slug = buildShortKhutbaSlug(item);
        return buildKhutbaPath(slug);
    }

    function buildKhutbaPath(slug) {
        const encodedSlug = encodeURIComponent(slug);
        const inKhutabDirectory = /\/khutab\/[^/]+\.html?$/i.test(window.location.pathname);
        return inKhutabDirectory
            ? `${encodedSlug}.html`
            : `khutab/${encodedSlug}.html`;
    }

    function buildShortKhutbaSlug(item) {
        const iso = (getIsoDate(item) || '').replace(/[^0-9]/g, '').slice(0, 8);
        const seed = String(item?.id || item?.title || 'khutba').trim();
        const encoded = unescape(encodeURIComponent(seed));
        const compact = btoa(encoded)
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=+$/g, '')
            .toLowerCase()
            .slice(0, 12);
        return iso ? `k-${iso}-${compact}` : `k-${compact || 'x1'}`;
    }

    function getIsoDate(item) {
        return item?.date?.iso || item?.date_iso || '';
    }

    function ensureDownloadButton(item) {
        if (!actionsEl || !item) return;

        let downloadButton = document.getElementById('khutba-download-pdf');
        if (!downloadButton) {
            downloadButton = document.createElement('button');
            downloadButton.type = 'button';
            downloadButton.id = 'khutba-download-pdf';
            downloadButton.className = 'btn';
            downloadButton.innerHTML = '<i class="fas fa-download"></i> تحميل PDF';
            actionsEl.appendChild(downloadButton);
        }

        downloadButton.onclick = async () => {
            if (!window.SheikhPdfExporter?.exportKhutbaItem) {
                alert('ميزة تحميل PDF غير متاحة حالياً.');
                return;
            }

            const originalHtml = downloadButton.innerHTML;
            downloadButton.disabled = true;
            downloadButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جارِ التحضير...';
            try {
                await window.SheikhPdfExporter.exportKhutbaItem(item);
            } catch (error) {
                console.error(error);
                alert('تعذر إنشاء ملف PDF حالياً.');
            } finally {
                downloadButton.disabled = false;
                downloadButton.innerHTML = originalHtml;
            }
        };
    }

    function computeLatestItem(items) {
        const list = Array.isArray(items) ? items : [];
        if (list.length === 0) return null;

        // Prefer ISO date if present; fallback to current JSON order.
        let best = list[0];
        let bestIso = getIsoDate(best);
        for (const it of list) {
            const iso = getIsoDate(it);
            if (iso && (!bestIso || iso.localeCompare(bestIso) > 0)) {
                best = it;
                bestIso = iso;
            }
        }
        return best;
    }

    function computeLatestReadableIds(items, limit = 7) {
        const list = (Array.isArray(items) ? items : []).slice();
        list.sort((a, b) => {
            const isoA = getIsoDate(a) || '';
            const isoB = getIsoDate(b) || '';
            return isoB.localeCompare(isoA);
        });
        return new Set(list.slice(0, limit).map(getItemId).filter(Boolean));
    }

    async function load() {
        const id = getId();
        if (!id) {
            renderError('لم يتم تحديد خطبة لعرضها.');
            return;
        }

        try {
            const candidateUrls = [
                'data/khutab_written.json',
                './data/khutab_written.json',
                '../data/khutab_written.json',
                '/data/khutab_written.json'
            ];

            let raw = null;
            for (const url of candidateUrls) {
                try {
                    const res = await fetch(url, { cache: 'no-cache' });
                    if (!res.ok) continue;
                    raw = await res.json();
                    break;
                } catch {
                }
            }

            if (!raw) throw new Error('Failed to load khutab JSON');
            const items = Array.isArray(raw) ? raw : (raw.items || []);

            const item = items.find(x => getItemId(x) === id);
            if (!item) {
                renderError('تعذر العثور على هذه الخطبة.');
                return;
            }

            const currentFileName = decodeURIComponent((window.location.pathname.split('/').pop() || '').trim());
            // Do not force-redirect to a generated filename. Allow the current
            // file to display even if its name doesn't match the computed slug.
            // (Redirects caused 404s when filenames were generated earlier.)

            const title = item.title || 'خطبة';
            const dateDisplay = getDisplayDate(item);
            const author = item.author || '';

            titleEl.innerHTML = `<span class="title-icon"><i class="fas fa-file-lines"></i></span> ${escapeHtml(title)}`;
            metaEl.textContent = [dateDisplay, author].filter(Boolean).join(' • ');

            let finalHtml = '';
            if (item.content_html && item.content_html.trim()) {
                finalHtml = sanitizeKhutbaHtml(item.content_html);
            } else if (item.content_text && item.content_text.trim()) {
                finalHtml = buildStructuredKhutbaHtmlFromText(item.content_text);
            } else {
                const sanitizedHtml = sanitizeKhutbaHtml(item.content_html || '');
                const plainText = htmlToPlainText(sanitizedHtml);
                finalHtml = buildStructuredKhutbaHtmlFromText(plainText);
            }

            if (finalHtml) {
                contentEl.innerHTML = `
                    <article class="khutba-article khutba-article-premium">
                        <div class="khutba-body">
                            ${finalHtml}
                        </div>
                    </article>
                `;
            } else {
                contentEl.innerHTML = '<div class="khutab-empty">لم يتم استخراج نص الخطبة بعد.</div>';
            }

            ensureDownloadButton(item);

            if (window.AOS) {
                setTimeout(() => AOS.refresh(), 80);
            }
        } catch (e) {
            console.error(e);
            renderError('عذراً، حدث خطأ أثناء تحميل الخطبة.');
        }
    }

    load();
});
