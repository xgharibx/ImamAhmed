document.addEventListener('DOMContentLoaded', () => {
    const state = {
        all: [],
        filtered: [],
        currentPage: 1,
        perPage: 12,
        query: '',
        latestId: '',
        latestReadableIds: new Set()
    };

    const listEl = document.getElementById('khutab-list');
    const loadMoreBtn = document.getElementById('khutab-load-more');
    const searchInput = document.getElementById('khutab-search');
    const statsEl = document.getElementById('khutab-stats');

    if (!listEl) {
        return;
    }

    // Access notice for currently readable khutab.
    const toolbarEl = document.querySelector('.khutab-toolbar');
    const latestOnlyNoteEl = document.createElement('div');
    latestOnlyNoteEl.className = 'soon-note';
    latestOnlyNoteEl.textContent = 'متاح حالياً آخر 5 خطب.';

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
        const id = String(item?.id || '').trim();
        return `khutba-view.html?id=${encodeURIComponent(id)}`;
    }

    function getItemId(item) {
        return String(item?.id || '').trim();
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
        return getItemId(best);
    }

    function computeLatestReadableIds(items, limit = 5) {
        const list = (Array.isArray(items) ? items : []).slice();
        const hasIsoDates = list.some((item) => !!getIsoDate(item));

        if (!hasIsoDates) {
            return new Set(list.slice(0, limit).map(getItemId).filter(Boolean));
        }

        list.sort((a, b) => {
            const isoA = getIsoDate(a) || '';
            const isoB = getIsoDate(b) || '';
            return isoB.localeCompare(isoA);
        });
        return new Set(list.slice(0, limit).map(getItemId).filter(Boolean));
    }

    function normalizeItems(raw) {
        const list = Array.isArray(raw) ? raw : (raw?.items || []);
        return list
            .filter((item) => item && typeof item === 'object')
            .map((item, index) => ({
                id: String(item.id ?? index + 1),
                title: item.title || 'خطبة',
                author: item.author || 'الشيخ أحمد الفشني',
                excerpt: item.excerpt || '',
                date: item.date || item.date_display || '',
                date_display: item.date_display,
                date_iso: item.date_iso,
                content_html: item.content_html,
                content_text: item.content_text
            }));
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
        const itemId = getItemId(item);
        const isReadable = !!itemId && state.latestReadableIds.has(itemId);
        const hasExportContent = !!(item?.content_html || item?.content_text);

        const actionLabel = isReadable ? 'قراءة الخطبة' : 'قريباً';
        const actionHref = isReadable ? detailUrl : '#';
        const actionAttrs = isReadable
            ? ''
            : ' aria-disabled="true" tabindex="-1"';
        const actionClasses = isReadable
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
                ${isReadable && hasExportContent ? '<button type="button" class="btn btn-sm khutba-download-btn"><i class="fas fa-download"></i> تحميل PDF</button>' : ''}
            </div>
        `;

        if (!isReadable) {
            const a = div.querySelector('a');
            a?.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, true);
        }

        if (isReadable) {
            div.addEventListener('dblclick', () => {
                window.location.href = detailUrl;
            });

            const downloadButton = div.querySelector('.khutba-download-btn');
            downloadButton?.addEventListener('click', async (event) => {
                event.preventDefault();
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
            });
        }

        return div;
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
            const candidateUrls = ['data/khutab_written.json', './data/khutab_written.json', '/data/khutab_written.json'];
            let json = null;

            for (const url of candidateUrls) {
                try {
                    const res = await fetch(url, { cache: 'no-cache' });
                    if (!res.ok) continue;
                    json = await res.json();
                    break;
                } catch {
                }
            }

            if (!json) throw new Error('Failed to load JSON');
            state.all = normalizeItems(json);

            if (!state.all.length) {
                throw new Error('No khutab items found in data source');
            }

            state.latestId = computeLatestId(state.all);
            state.latestReadableIds = computeLatestReadableIds(state.all, 5);

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
            if (loadMoreBtn) loadMoreBtn.style.display = 'none';
        }
    }

    wireUi();
    loadData();
});
