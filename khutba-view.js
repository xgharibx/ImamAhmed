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
        return (params.get('id') || '').trim();
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

        const flushList = () => {
            if (!listBuffer.length) return;
            const items = listBuffer
                .map((item) => `<li>${escapeHtml(item)}</li>`)
                .join('');
            parts.push(`<ol class="khutba-list khutba-list-ordered">${items}</ol>`);
            listBuffer = [];
        };

        const isMainHeading = (line) => /^(عناصر الخطبة|عناصر الخطبه|عَنَاصِرُ الْخُطْبَةِ|الْخُطْبَةُ الْأُولَى|الْخُطْبَةُ الثَّانِيَة|الْخُطْبَةُ الثَّانِيَة|الدُّعَاءُ|الدعاء|الموضوع|الْمَوْضُوع)\s*[:：]?$/.test(line);
        const isSubHeading = (line) => /^(الْعُنْصَرُ|العنصر|أولاً|ثانياً|ثالثاً|رابعاً|خامساً|سادساً|سابعاً|ثامناً|تاسعاً|عاشراً)\b/.test(line);
        const isNumberedListItem = (line) => /^\s*[0-9٠-٩]+\s*[\)\-\.:،]?\s+/.test(line);

        lines.forEach((line, index) => {
            if (isMainHeading(line)) {
                flushList();
                parts.push(`<h2 class="khutba-heading">${escapeHtml(line.replace(/\s*[:：]\s*$/, ''))}</h2>`);
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

            flushList();
            const introClass = index < 3 ? ' khutba-intro-line' : '';
            parts.push(`<p class="khutba-paragraph${introClass}">${escapeHtml(line)}</p>`);
        });

        flushList();
        return parts.join('');
    }

    function renderError(msg) {
        contentEl.innerHTML = `<div class="khutab-empty">${escapeHtml(msg)}</div>`;
    }

    function getDisplayDate(item) {
        return item?.date?.display || item?.date_display || item?.date || '';
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

    function computeLatestReadableIds(items, limit = 5) {
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
            const res = await fetch('data/khutab_written.json', { cache: 'no-cache' });
            if (!res.ok) throw new Error('Failed to load khutab JSON');
            const raw = await res.json();
            const items = Array.isArray(raw) ? raw : (raw.items || []);

            const latest = computeLatestItem(items);
            const latestReadableIds = computeLatestReadableIds(items, 5);
            const latestId = getItemId(latest);
            if (latestId && !latestReadableIds.has(id)) {
                const latestUrl = `khutba-view.html?id=${encodeURIComponent(latestId)}`;
                titleEl.innerHTML = `<span class="title-icon"><i class="fas fa-lock"></i></span> ${escapeHtml('غير متاح حالياً')}`;
                metaEl.textContent = '';
                contentEl.innerHTML = `
                    <div class="khutab-empty">
                        هذه الخطبة غير متاحة للعرض حالياً. المتاح الآن: آخر 5 خطب فقط.
                        <div style="margin-top: 0.75rem;">
                            <a class="btn btn-outline" href="${latestUrl}">عرض أحدث خطبة</a>
                            <a class="btn" href="khutab-written.html" style="margin-right: 0.5rem;">العودة للأرشيف</a>
                        </div>
                    </div>
                `;
                return;
            }

            const item = items.find(x => getItemId(x) === id);
            if (!item) {
                renderError('تعذر العثور على هذه الخطبة.');
                return;
            }

            const title = item.title || 'خطبة';
            const dateDisplay = getDisplayDate(item);
            const author = item.author || '';

            titleEl.innerHTML = `<span class="title-icon"><i class="fas fa-file-lines"></i></span> ${escapeHtml(title)}`;
            metaEl.textContent = [dateDisplay, author].filter(Boolean).join(' • ');

            const sanitizedHtml = sanitizeKhutbaHtml(item.content_html);
            const plainText = (typeof item.content_text === 'string' && item.content_text.trim())
                ? item.content_text
                : htmlToPlainText(sanitizedHtml);
            const structuredHtml = buildStructuredKhutbaHtmlFromText(plainText);

            if (structuredHtml) {
                contentEl.innerHTML = `
                    <article class="khutba-article khutba-article-premium">
                        <div class="khutba-body">
                            ${structuredHtml}
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
