document.addEventListener('DOMContentLoaded', () => {
    const titleEl = document.getElementById('khutba-title');
    const metaEl = document.getElementById('khutba-meta');
    const contentEl = document.getElementById('khutba-content');
    const downloadEl = document.getElementById('khutba-download');
    const pdfWrap = document.getElementById('khutba-pdf-wrap');
    const pdfIframe = document.getElementById('khutba-pdf');

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text ?? '';
        return div.innerHTML;
    }

    function getId() {
        const params = new URLSearchParams(window.location.search);
        return (params.get('id') || '').trim();
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

    async function load() {
        const id = getId();
        if (!id) {
            renderError('لم يتم تحديد خطبة لعرضها.');
            return;
        }

        // Default: hide download until we confirm access.
        if (downloadEl) downloadEl.style.display = 'none';

        try {
            const res = await fetch('data/khutab_written.json', { cache: 'no-cache' });
            if (!res.ok) throw new Error('Failed to load khutab JSON');
            const raw = await res.json();
            const items = Array.isArray(raw) ? raw : (raw.items || []);

            const latest = computeLatestItem(items);
            if (latest && latest.id && id !== latest.id) {
                const latestUrl = `khutba-view.html?id=${encodeURIComponent(latest.id)}`;
                titleEl.innerHTML = `<span class="title-icon"><i class="fas fa-lock"></i></span> ${escapeHtml('غير متاح حالياً')}`;
                metaEl.textContent = '';
                contentEl.innerHTML = `
                    <div class="khutab-empty">
                        هذه الخطبة غير متاحة للعرض حالياً. المتاح الآن: أحدث خطبة فقط.
                        <div style="margin-top: 0.75rem;">
                            <a class="btn btn-outline" href="${latestUrl}">عرض أحدث خطبة</a>
                            <a class="btn" href="khutab-written.html" style="margin-right: 0.5rem;">العودة للأرشيف</a>
                        </div>
                    </div>
                `;
                return;
            }

            const item = items.find(x => x.id === id);
            if (!item) {
                renderError('تعذر العثور على هذه الخطبة.');
                return;
            }

            const title = item.title || 'خطبة';
            const dateDisplay = getDisplayDate(item);
            const author = item.author || '';

            titleEl.innerHTML = `<span class="title-icon"><i class="fas fa-file-lines"></i></span> ${escapeHtml(title)}`;
            metaEl.textContent = [dateDisplay, author].filter(Boolean).join(' • ');

            // Render extracted content (HTML preferred, fallback to text)
            if (item.content_html) {
                contentEl.innerHTML = `
                    <article class="khutba-article">
                        <div class="khutba-body">
                            ${item.content_html}
                        </div>
                    </article>
                `;
            } else if (item.content_text) {
                // Fallback: render plain text as paragraphs
                const paragraphs = item.content_text
                    .split(/\n{2,}/)
                    .map(p => p.trim())
                    .filter(Boolean)
                    .map(p => `<p class="khutba-paragraph">${escapeHtml(p)}</p>`)
                    .join('');

                contentEl.innerHTML = `
                    <article class="khutba-article">
                        <div class="khutba-body">
                            ${paragraphs}
                        </div>
                    </article>
                `;
            } else {
                contentEl.innerHTML = '<div class="khutab-empty">لم يتم استخراج نص الخطبة بعد.</div>';
            }

            // Local PDF download button ONLY (no embed)
            const pdfLocal = item.pdf_local || item.pdf_path || item.pdf_url_local || '';
            if (pdfLocal) {
                // Encode Arabic/space paths safely for the browser
                downloadEl.href = encodeURI(pdfLocal);
                downloadEl.style.display = 'inline-flex';
            }

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
