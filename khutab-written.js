document.addEventListener('DOMContentLoaded', () => {
    const state = {
        all: [],
        filtered: [],
        currentPage: 1,
        perPage: 12,
        query: '',
        latestId: ''
    };

    const listEl = document.getElementById('khutab-list');
    const loadMoreBtn = document.getElementById('khutab-load-more');
    const searchInput = document.getElementById('khutab-search');
    const statsEl = document.getElementById('khutab-stats');

    // Show a simple notice that only the newest khutba is available for viewing.
    const toolbarEl = document.querySelector('.khutab-toolbar');
    const latestOnlyNoteEl = document.createElement('div');
    latestOnlyNoteEl.className = 'soon-note';
    latestOnlyNoteEl.textContent = 'متاح حالياً أحدث خطبة فقط.';

    // We render a list page and navigate to an internal detail page (no external redirects)

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text ?? '';
        return div.innerHTML;
    }

    function normalizeArabicForSearch(text) {
        return (text || '')
            .toString()
            .normalize('NFKC')
            .replace(/[\u064B-\u0652\u0670]/g, '') // tashkeel
            .replace(/أ|إ|آ/g, 'ا')
            .replace(/ى/g, 'ي')
            .replace(/ة/g, 'ه')
            .replace(/\s+/g, ' ')
            .trim()
            .toLowerCase();
    }

    function toDetailUrl(item) {
        const id = (item?.id || '').trim();
        return `khutba-view.html?id=${encodeURIComponent(id)}`;
    }

    function getDisplayDate(item) {
        return item?.date?.display || item?.date_display || item?.date || '';
    }

    function getIsoDate(item) {
        return item?.date?.iso || item?.date_iso || '';
    }

    function computeLatestId(items) {
        const list = Array.isArray(items) ? items : [];
        if (list.length === 0) return '';

        // Prefer ISO date if present; fallback to current JSON order.
        let best = list[0];
        let bestIso = getIsoDate(best);

        for (const item of list) {
            const iso = getIsoDate(item);
            if (iso && (!bestIso || iso.localeCompare(bestIso) > 0)) {
                best = item;
                bestIso = iso;
            }
        }
        return (best?.id || '').trim();
    }

    function applyFilter() {
        const q = normalizeArabicForSearch(state.query);
        state.currentPage = 1;

        if (!q) {
            state.filtered = state.all.slice();
        } else {
            state.filtered = state.all.filter(item => {
                const haystack = normalizeArabicForSearch([item.title, item.author, item.excerpt].filter(Boolean).join(' '));
                return haystack.includes(q);
            });
        }

        // Default sort: newest first if ISO date is available
        state.filtered.sort((a, b) => {
            const da = getIsoDate(a);
            const db = getIsoDate(b);
            if (da && db) return db.localeCompare(da);
            return (b.title || '').localeCompare(a.title || '');
        });

        listEl.innerHTML = '';
        renderNext();
        updateStats();
    }

    function updateStats() {
        if (!statsEl) return;
        const total = state.all.length;
        const shown = state.filtered.length;
        statsEl.textContent = shown === total
            ? `عدد الخطب: ${total}`
            : `عدد الخطب: ${shown} من أصل ${total}`;
    }

    function renderNext() {
        const start = (state.currentPage - 1) * state.perPage;
        const end = start + state.perPage;
        const batch = state.filtered.slice(start, end);

        if (batch.length === 0 && state.currentPage === 1) {
            listEl.innerHTML = '<p class="khutab-empty">لا توجد نتائج مطابقة.</p>';
            loadMoreBtn.style.display = 'none';
            return;
        }

        batch.forEach(item => listEl.appendChild(createCard(item)));

        if (end >= state.filtered.length) {
            loadMoreBtn.style.display = 'none';
        } else {
            loadMoreBtn.style.display = 'inline-flex';
        }

        if (window.AOS) {
            setTimeout(() => AOS.refresh(), 60);
        }
    }

    function truncate(text, max) {
        const t = (text || '').toString();
        return t.length > max ? t.slice(0, max).trim() + '…' : t;
    }

    function createCard(item) {
        const div = document.createElement('div');
        div.className = 'khutab-item-card';
        div.setAttribute('data-aos', 'fade-up');

        const title = truncate(item.title || 'خطبة', 80);
        const author = item.author || '—';
        const dateDisplay = getDisplayDate(item);
        const detailUrl = toDetailUrl(item);
        const isLatest = !!state.latestId && (item?.id === state.latestId);

        const actionLabel = isLatest ? 'قراءة الخطبة' : 'قريباً';
        const actionHref = isLatest ? detailUrl : '#';
        const actionAttrs = isLatest
            ? ''
            : ' aria-disabled="true" tabindex="-1"';
        const actionClasses = isLatest
            ? 'btn btn-outline btn-sm'
            : 'btn btn-outline btn-sm is-disabled-link has-soon-badge';

        div.innerHTML = `
            <h3 class="khutab-item-title">${escapeHtml(title)}</h3>
            <div class="khutab-item-meta">
                <span><i class="fas fa-calendar"></i> ${escapeHtml(dateDisplay || 'بدون تاريخ')}</span>
                <span><i class="fas fa-user"></i> ${escapeHtml(author)}</span>
            </div>
            <p class="khutab-item-excerpt">${escapeHtml(item.excerpt || '').slice(0, 180)}${(item.excerpt || '').length > 180 ? '…' : ''}</p>
            <div class="khutab-item-actions">
                <a class="${actionClasses}" href="${actionHref}"${actionAttrs}>${escapeHtml(actionLabel)}</a>
            </div>
        `;

        if (!isLatest) {
            const a = div.querySelector('a');
            a?.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, true);
        }

        if (isLatest) {
            div.addEventListener('dblclick', () => {
                window.location.href = detailUrl;
            });
        }

        return div;
    }

    function openModal(item) {
        modalTitle.textContent = item.title || '';
        const dateDisplay = getDisplayDate(item);
        const author = item.author || '';
        modalMeta.textContent = [dateDisplay, author].filter(Boolean).join(' • ');

        const attachments = Array.isArray(item.attachments) ? item.attachments : [];
        const pdfUrl = item.pdf_url || attachments.find(a => a?.url && /\.pdf($|\?)/i.test(a.url))?.url || '';

        const parts = [];
        if (pdfUrl) {
            parts.push(`
                <div class="khutab-pdf-wrap">
                    <iframe class="khutab-pdf" src="${escapeHtml(pdfUrl)}" title="PDF"></iframe>
                    <p class="khutab-pdf-note">إذا لم يظهر الملف داخل الصفحة، استخدم زر "فتح المصدر" أو افتح رابط الـ PDF مباشرة.</p>
                </div>
            `);
        }
        modalMeta.textContent = '';
        modalBody.innerHTML = '';
        document.body.style.overflow = '';
    }

    function wireUi() {
        if (searchInput) {
            searchInput.addEventListener('input', () => {
                state.query = searchInput.value;
                applyFilter();
            });
        }

        loadMoreBtn?.addEventListener('click', () => {
            state.currentPage++;
            renderNext();
        });

        // No modal on list page
    }

    async function loadData() {
        try {
            const res = await fetch('data/khutab_written.json', { cache: 'no-cache' });
            if (!res.ok) throw new Error('Failed to load JSON');
            const json = await res.json();
            state.all = Array.isArray(json) ? json : (json.items || []);
            state.latestId = computeLatestId(state.all);

            // Show notice when we actually have more than one khutba.
            if (toolbarEl && state.all.length > 1) {
                // Avoid duplicates if loadData is called again.
                if (!toolbarEl.parentElement?.querySelector('.soon-note')) {
                    toolbarEl.parentElement?.insertBefore(latestOnlyNoteEl, toolbarEl.nextSibling);
                }
            }
            state.filtered = state.all.slice();
            applyFilter();
        } catch (err) {
            console.error('Error loading khutab:', err);
            listEl.innerHTML = '<p class="khutab-empty">عذراً، تعذر تحميل الخطب حالياً.</p>';
            loadMoreBtn.style.display = 'none';
        }
    }

    wireUi();
    loadData();
});
