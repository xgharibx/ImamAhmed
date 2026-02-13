(function () {
    const HTML2PDF_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
    let html2pdfLoader = null;

    function loadHtml2Pdf() {
        if (window.html2pdf) return Promise.resolve();
        if (html2pdfLoader) return html2pdfLoader;

        html2pdfLoader = new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = HTML2PDF_CDN;
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error('Failed to load html2pdf library'));
            document.head.appendChild(script);
        });

        return html2pdfLoader;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    function sanitizeHtml(rawHtml) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(rawHtml || '', 'text/html');
        doc.querySelectorAll('script,style,iframe,object,embed,form,button,nav,header,footer,aside,canvas,svg,video,audio,noscript').forEach(el => el.remove());
        doc.querySelectorAll('*').forEach((el) => {
            [...el.attributes].forEach((attr) => {
                const name = attr.name.toLowerCase();
                if (
                    name.startsWith('on') ||
                    name === 'style' ||
                    name === 'class' ||
                    name === 'id' ||
                    name === 'role' ||
                    name.startsWith('aria-') ||
                    name.startsWith('data-')
                ) {
                    el.removeAttribute(attr.name);
                }
            });
        });
        return doc.body.innerHTML;
    }

    function buildReadableContentHtml(rawHtml) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(sanitizeHtml(rawHtml || ''), 'text/html');
        const blocks = [];

        doc.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,blockquote,pre').forEach((node) => {
            const tag = node.tagName.toLowerCase();
            const text = (node.textContent || '').replace(/\s+/g, ' ').trim();
            if (!text) return;

            if (tag === 'li') {
                blocks.push(`<p class="pdf-bullet">• ${escapeHtml(text)}</p>`);
                return;
            }

            if (tag === 'blockquote') {
                blocks.push(`<blockquote>${escapeHtml(text)}</blockquote>`);
                return;
            }

            if (tag === 'pre') {
                blocks.push(`<pre>${escapeHtml(node.textContent || '').trim()}</pre>`);
                return;
            }

            if (tag.startsWith('h')) {
                blocks.push(`<h2>${escapeHtml(text)}</h2>`);
                return;
            }

            blocks.push(`<p>${escapeHtml(text)}</p>`);
        });

        if (blocks.length > 0) {
            return blocks.join('');
        }

        const plain = (doc.body.textContent || '').trim();
        if (!plain) return '';

        return plain
            .split(/\n{2,}/)
            .map((segment) => segment.trim())
            .filter(Boolean)
            .map((segment) => `<p>${escapeHtml(segment)}</p>`)
            .join('');
    }

    function slugify(text) {
        return (text || 'document')
            .toString()
            .trim()
            .replace(/[\s\/\\:|"'<>?*]+/g, '-')
            .replace(/-+/g, '-')
            .replace(/^-|-$/g, '')
            .slice(0, 80) || 'document';
    }

    function typeLabel(type) {
        if (type === 'book') return 'كتاب';
        if (type === 'article') return 'مقال';
        if (type === 'khutba') return 'خطبة';
        return 'محتوى';
    }

    function buildPdfShell({ title, subtitle, meta, contentHtml, type }) {
        const wrapper = document.createElement('div');
        wrapper.setAttribute('dir', 'rtl');
        wrapper.lang = 'ar';
        wrapper.style.width = '794px';
        wrapper.style.background = '#ffffff';
        wrapper.style.color = '#1b1b1b';
        wrapper.style.fontFamily = '"Cairo", "Tajawal", sans-serif';
        wrapper.style.padding = '26px';
        wrapper.style.boxSizing = 'border-box';
        wrapper.style.position = 'fixed';
        wrapper.style.left = '0';
        wrapper.style.top = '0';
        wrapper.style.zIndex = '2147483000';
        wrapper.style.opacity = '1';
        wrapper.style.pointerEvents = 'none';

        const label = typeLabel(type);
        const safeTitle = escapeHtml(title || '');
        const safeSubtitle = escapeHtml(subtitle || '');
        const safeMeta = escapeHtml(meta || '');

        wrapper.innerHTML = `
            <style>
                .pdf-card { border: 1px solid #e6e6e6; border-radius: 14px; overflow: hidden; background: #fff; }
                .pdf-head { background: linear-gradient(135deg, #1a5f4a, #1f7a5a); color: #fff; padding: 18px 20px; }
                .pdf-tag { display:inline-block; background:#d4af37; color:#1a5f4a; border-radius:999px; padding: 4px 12px; font-size: 12px; font-weight:700; margin-bottom: 10px; }
                .pdf-title { margin:0; font-size: 28px; line-height: 1.6; font-weight: 800; }
                .pdf-subtitle { margin: 8px 0 0; font-size: 16px; opacity: .95; }
                .pdf-meta { margin-top: 10px; font-size: 13px; opacity: .92; }
                .pdf-body { padding: 22px; font-size: 17px; line-height: 2.0; }
                .pdf-body, .pdf-body * { max-width: 100%; box-sizing: border-box; overflow-wrap: anywhere; }
                .pdf-body h1,.pdf-body h2,.pdf-body h3,.pdf-body h4 { color: #1a5f4a; line-height: 1.7; page-break-after: avoid; margin: 1.1rem 0 .7rem; }
                .pdf-body p,.pdf-body li,.pdf-body blockquote,.pdf-body pre { page-break-inside: avoid; margin: 0 0 .9rem; }
                .pdf-body .pdf-bullet { padding-inline-start: .2rem; }
                .pdf-body blockquote { border-right: 4px solid #d4af37; margin: 1rem 0; padding: .6rem 1rem; background: #faf8f0; border-radius: 8px; }
                .pdf-body pre { background: #f6f7f8; border: 1px solid #e8ebee; border-radius: 8px; padding: .8rem; white-space: pre-wrap; }
                .pdf-body img { display: block; height: auto; border-radius: 10px; margin: .8rem auto; }
                .pdf-body *[hidden] { display: none !important; }
                .pdf-body table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
                .pdf-body th, .pdf-body td { border: 1px solid #e5e7eb; padding: .45rem; text-align: right; }
                .pdf-foot { margin-top: 20px; text-align:center; color:#4d4d4d; font-size:12px; border-top:1px solid #efefef; padding-top:12px; }
            </style>
            <div class="pdf-card">
                <div class="pdf-head">
                    <div class="pdf-tag">${label}</div>
                    <h1 class="pdf-title">${safeTitle}</h1>
                    ${safeSubtitle ? `<p class="pdf-subtitle">${safeSubtitle}</p>` : ''}
                    ${safeMeta ? `<div class="pdf-meta">${safeMeta}</div>` : ''}
                </div>
                <div class="pdf-body">${contentHtml || ''}</div>
            </div>
            <div class="pdf-foot">الشيخ أحمد إسماعيل الفشني</div>
        `;

        return wrapper;
    }

    function extractContentFromDocument(doc) {
        const contentRoot = doc.querySelector('.book-container, .khutba-content, .newspaper-article, .content-section main, .content-section, main');
        const title =
            doc.querySelector('.main-title')?.textContent?.trim() ||
            doc.querySelector('#khutba-title')?.textContent?.trim() ||
            doc.querySelector('.page-title')?.textContent?.trim() ||
            doc.querySelector('h1')?.textContent?.trim() ||
            doc.title ||
            'محتوى';

        const subtitle =
            doc.querySelector('.sub-title')?.textContent?.trim() ||
            doc.querySelector('.page-subtitle')?.textContent?.trim() ||
            '';

        const meta =
            doc.querySelector('#khutba-meta')?.textContent?.trim() ||
            doc.querySelector('.author-name')?.textContent?.trim() ||
            '';

        return {
            title,
            subtitle,
            meta,
            contentHtml: buildReadableContentHtml(contentRoot ? contentRoot.innerHTML : '') || '<p>لا يوجد محتوى متاح للتصدير.</p>'
        };
    }

    async function exportPayload(payload, filenameHint) {
        await loadHtml2Pdf();
        const shell = buildPdfShell(payload);
        document.body.appendChild(shell);

        const images = Array.from(shell.querySelectorAll('img'));
        if (images.length) {
            await Promise.all(images.map((img) => {
                if (img.complete) return Promise.resolve();
                return new Promise((resolve) => {
                    img.addEventListener('load', resolve, { once: true });
                    img.addEventListener('error', resolve, { once: true });
                    setTimeout(resolve, 1200);
                });
            }));
        }

        if (document.fonts?.ready) {
            await Promise.race([
                document.fonts.ready,
                new Promise(resolve => setTimeout(resolve, 1200))
            ]);
        }

        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));

        const filename = `${slugify(filenameHint || payload.title)}.pdf`;
        try {
            const runExport = (scale) => window.html2pdf()
                .set({
                    margin: [8, 8, 8, 8],
                    filename,
                    image: { type: 'jpeg', quality: 0.98 },
                    html2canvas: {
                        scale,
                        useCORS: true,
                        backgroundColor: '#ffffff',
                        windowWidth: 794,
                        scrollX: 0,
                        scrollY: 0,
                        removeContainer: true,
                        logging: false
                    },
                    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
                    pagebreak: { mode: ['css', 'legacy'] }
                })
                .from(shell)
                .save();

            try {
                await runExport(2);
            } catch (firstError) {
                console.warn('Primary PDF render failed, retrying with lower scale.', firstError);
                await new Promise((resolve) => setTimeout(resolve, 200));
                await runExport(1.35);
            }
        } finally {
            shell.remove();
        }
    }

    async function exportFromCurrentPage(options = {}) {
        const extracted = extractContentFromDocument(document);
        return exportPayload({
            ...extracted,
            type: options.type || 'content',
            title: options.title || extracted.title,
            subtitle: options.subtitle ?? extracted.subtitle,
            meta: options.meta ?? extracted.meta
        }, options.filename || extracted.title);
    }

    async function exportFromUrl(url, options = {}) {
        const res = await fetch(url, { cache: 'no-cache' });
        if (!res.ok) throw new Error('تعذر تحميل الصفحة للتصدير');

        const html = await res.text();
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const extracted = extractContentFromDocument(doc);

        return exportPayload({
            ...extracted,
            type: options.type || 'content',
            title: options.title || extracted.title,
            subtitle: options.subtitle ?? extracted.subtitle,
            meta: options.meta ?? extracted.meta
        }, options.filename || extracted.title);
    }

    async function exportKhutbaItem(item) {
        const title = item?.title || 'خطبة';
        const dateDisplay = item?.date?.display || item?.date_display || item?.date || '';
        const author = item?.author || '';
        const meta = [dateDisplay, author].filter(Boolean).join(' • ');

        const contentHtml = sanitizeHtml(item?.content_html || '') || (item?.content_text
            ? item.content_text
                .split(/\n{2,}/)
                .map(p => `<p>${escapeHtml(p)}</p>`)
                .join('')
            : '<p>لا يوجد نص متاح للتصدير.</p>');

        const normalizedContent = buildReadableContentHtml(contentHtml) || '<p>لا يوجد نص متاح للتصدير.</p>';

        return exportPayload({
            title,
            subtitle: 'خطب منبرية',
            meta,
            contentHtml: normalizedContent,
            type: 'khutba'
        }, title);
    }

    function makeButton(label, className) {
        const btn = document.createElement('a');
        btn.href = '#';
        btn.className = className;
        btn.innerHTML = `<i class="fas fa-download"></i> ${label}`;
        return btn;
    }

    function appendButtonsOnBooksPage() {
        document.querySelectorAll('.book-actions a.btn-book').forEach((readBtn) => {
            if (readBtn.parentElement?.querySelector('.js-download-pdf')) return;
            const href = readBtn.getAttribute('href');
            if (!href) return;

            const btn = makeButton('تحميل PDF', 'btn-book btn-read js-download-pdf');
            btn.style.background = '#d4af37';
            btn.style.color = '#1a5f4a';

            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                btn.style.pointerEvents = 'none';
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جارِ التحضير...';
                try {
                    await exportFromUrl(new URL(href, window.location.href).href, { type: 'book' });
                } catch (err) {
                    console.error(err);
                    alert('تعذر إنشاء ملف PDF حالياً.');
                } finally {
                    btn.style.pointerEvents = '';
                    btn.innerHTML = '<i class="fas fa-download"></i> تحميل PDF';
                }
            });

            readBtn.parentElement.appendChild(btn);
        });
    }

    function appendButtonsOnArticlesPage() {
        document.querySelectorAll('.newspaper-content .btn, .featured-content .btn').forEach((readBtn) => {
            if (readBtn.parentElement?.querySelector('.js-download-pdf')) return;
            const href = readBtn.getAttribute('href');
            if (!href || !href.endsWith('.html')) return;

            const btn = makeButton('تحميل PDF', readBtn.className + ' js-download-pdf');
            btn.style.marginInlineStart = '0.5rem';

            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                btn.style.pointerEvents = 'none';
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جارِ التحضير...';
                try {
                    await exportFromUrl(new URL(href, window.location.href).href, { type: 'article' });
                } catch (err) {
                    console.error(err);
                    alert('تعذر إنشاء ملف PDF حالياً.');
                } finally {
                    btn.style.pointerEvents = '';
                    btn.innerHTML = '<i class="fas fa-download"></i> تحميل PDF';
                }
            });

            readBtn.parentElement.appendChild(btn);
        });
    }

    function appendButtonOnBookDetailPage() {
        const navContainer = document.querySelector('.nav-container');
        if (!navContainer || navContainer.querySelector('.js-book-download-top')) return;

        const btn = makeButton('تحميل PDF', 'btn-back js-book-download-top');
        btn.style.marginInlineStart = '0.75rem';

        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            btn.style.pointerEvents = 'none';
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جارِ التحضير...';
            try {
                await exportFromCurrentPage({ type: 'book' });
            } catch (err) {
                console.error(err);
                alert('تعذر إنشاء ملف PDF حالياً.');
            } finally {
                btn.style.pointerEvents = '';
                btn.innerHTML = '<i class="fas fa-download"></i> تحميل PDF';
            }
        });

        const backBtn = navContainer.querySelector('.btn-back');
        if (backBtn) {
            backBtn.insertAdjacentElement('afterend', btn);
        } else {
            navContainer.appendChild(btn);
        }

        const params = new URLSearchParams(window.location.search);
        if (params.get('autopdf') === '1') {
            setTimeout(() => btn.click(), 200);
        }
    }

    function pageKind() {
        const path = window.location.pathname.toLowerCase();
        if (path.endsWith('/books.html') || path.endsWith('books.html')) return 'books-list';
        if (path.endsWith('/articles.html') || path.endsWith('articles.html')) return 'articles-list';
        if (path.includes('/books/') && path.endsWith('.html')) return 'book-detail';
        return 'other';
    }

    const SheikhPdfExporter = {
        exportFromCurrentPage,
        exportFromUrl,
        exportKhutbaItem
    };

    window.SheikhPdfExporter = SheikhPdfExporter;

    document.addEventListener('DOMContentLoaded', () => {
        const kind = pageKind();
        if (kind === 'books-list') appendButtonsOnBooksPage();
        if (kind === 'articles-list') appendButtonsOnArticlesPage();
        if (kind === 'book-detail') appendButtonOnBookDetailPage();
    });
})();
