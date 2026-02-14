(function () {
    const HTML2PDF_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
    const HTML2CANVAS_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
    const JSPDF_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
    let html2pdfLoader = null;
    const scriptLoaders = new Map();

    function loadScript(src) {
        if (scriptLoaders.has(src)) return scriptLoaders.get(src);

        const loader = new Promise((resolve, reject) => {
            const existing = document.querySelector(`script[src="${src}"]`);
            if (existing) {
                if (existing.dataset.loaded === '1') {
                    resolve();
                    return;
                }
                existing.addEventListener('load', () => resolve(), { once: true });
                existing.addEventListener('error', () => reject(new Error(`Failed to load script: ${src}`)), { once: true });
                return;
            }

            const script = document.createElement('script');
            script.src = src;
            script.async = true;
            script.onload = () => {
                script.dataset.loaded = '1';
                resolve();
            };
            script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
            document.head.appendChild(script);
        });

        scriptLoaders.set(src, loader);
        return loader;
    }

    function loadHtml2Pdf() {
        if (window.html2pdf) return Promise.resolve();
        if (html2pdfLoader) return html2pdfLoader;

        html2pdfLoader = loadScript(HTML2PDF_CDN);

        return html2pdfLoader;
    }

    async function ensurePdfDependencies() {
        if (!window.jspdf?.jsPDF) {
            await loadScript(JSPDF_CDN);
        }

        if (!window.html2pdf) {
            await loadHtml2Pdf().catch(() => {});
        }

        if (!window.html2canvas) {
            await loadScript(HTML2CANVAS_CDN).catch(() => {});
        }
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
        const doc = parser.parseFromString(rawHtml || '', 'text/html');
        const blocks = [];

        doc.querySelectorAll('script,style,iframe,object,embed,form,button,nav,header,footer,aside,canvas,svg,video,audio,noscript').forEach(el => el.remove());

        doc.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,blockquote,pre,.list-item,.quran-box,.hadith-box,.poetry-box').forEach((node) => {
            if (node.closest('.list-item,.quran-box,.hadith-box,.poetry-box') && !node.matches('.list-item,.quran-box,.hadith-box,.poetry-box')) {
                return;
            }

            const tag = node.tagName.toLowerCase();
            const text = (node.textContent || '').replace(/\s+/g, ' ').trim();
            if (!text) return;

            if (node.matches('.list-item')) {
                blocks.push(`<p class="pdf-bullet">• ${escapeHtml(text)}</p>`);
                return;
            }

            if (node.matches('.quran-box,.hadith-box,.poetry-box')) {
                blocks.push(`<blockquote>${escapeHtml(text)}</blockquote>`);
                return;
            }

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

    function extractFallbackBodyHtml(doc) {
        const clone = doc.body ? doc.body.cloneNode(true) : null;
        if (!clone) return '';

        clone.querySelectorAll('script,style,link,noscript,iframe,object,embed,canvas,svg,video,audio').forEach((el) => el.remove());
        clone.querySelectorAll('header,nav,footer,.navbar,.nav-menu,.footer,.page-back-button,.back-btn,.btn,.book-actions,.mushaf-pagination').forEach((el) => el.remove());

        const candidateHtml = clone.innerHTML || '';
        return buildReadableContentHtml(candidateHtml);
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

    function normalizeComparableText(value) {
        return String(value || '')
            .replace(/[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g, '')
            .replace(/ـ/g, '')
            .replace(/[إأآٱ]/g, 'ا')
            .replace(/ى/g, 'ي')
            .replace(/ة/g, 'ه')
            .replace(/["“”'`’:,؛.،!?؟()\[\]{}]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim()
            .toLowerCase();
    }

    function similarityScore(textA, textB) {
        const a = normalizeComparableText(textA)
            .replace(/^(المقدمه|القصه باختصار|الدروس والعبر|الخاتمه)\s+/, '')
            .trim();
        const b = normalizeComparableText(textB)
            .replace(/^(المقدمه|القصه باختصار|الدروس والعبر|الخاتمه)\s+/, '')
            .trim();

        if (!a || !b) return 0;
        if (a === b) return 1;

        const minLen = Math.min(a.length, b.length);
        const maxLen = Math.max(a.length, b.length);
        if (minLen >= 28 && (a.includes(b) || b.includes(a))) {
            return minLen / maxLen;
        }

        const aTokens = new Set(a.split(' ').filter(Boolean));
        const bTokens = new Set(b.split(' ').filter(Boolean));
        let common = 0;
        aTokens.forEach((token) => {
            if (bTokens.has(token)) common += 1;
        });

        return common / Math.max(aTokens.size, bTokens.size, 1);
    }

    function dedupeSequentialTextBlocks(blocks) {
        if (!Array.isArray(blocks) || blocks.length < 2) return blocks || [];

        const result = [];
        for (const block of blocks) {
            const prev = result[result.length - 1];
            if (!prev) {
                result.push(block);
                continue;
            }

            const score = similarityScore(block.text, prev.text);
            const isCurrentParagraph = block.kind === 'paragraph';
            const isCurrentHeading = block.kind === 'heading';
            const normalizedCurrent = normalizeComparableText(block.text);
            const normalizedPrev = normalizeComparableText(prev.text);
            const minLen = Math.min(normalizedCurrent.length, normalizedPrev.length);
            const maxLen = Math.max(normalizedCurrent.length, normalizedPrev.length);
            const strictContains = minLen >= 24 && maxLen > 0 && (normalizedCurrent.includes(normalizedPrev) || normalizedPrev.includes(normalizedCurrent)) && (minLen / maxLen >= 0.92);

            if ((isCurrentParagraph && (score >= 0.95 || strictContains)) || (isCurrentHeading && (score >= 0.97 || strictContains))) {
                continue;
            }

            result.push(block);
        }

        return result;
    }

    function getBookCoverSubtitle({ type, title, subtitle }) {
        if (type !== 'book') return subtitle || '';
        if (String(subtitle || '').trim()) return subtitle;

        const normalizedTitle = normalizeComparableText(title);
        if (normalizedTitle === 'قصص الانبياء') {
            return 'رحلة إيمانية في سير الأنبياء، نستخلص منها الدروس والعبر لبناء النفس والمجتمع.';
        }

        return '';
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

    function canvasLooksBlank(canvas) {
        try {
            const context = canvas.getContext('2d', { willReadFrequently: true });
            if (!context) return false;
            const width = canvas.width;
            const height = canvas.height;
            if (!width || !height) return true;

            const samplePoints = [
                [Math.floor(width * 0.1), Math.floor(height * 0.1)],
                [Math.floor(width * 0.5), Math.floor(height * 0.5)],
                [Math.floor(width * 0.9), Math.floor(height * 0.9)],
                [Math.floor(width * 0.2), Math.floor(height * 0.8)],
                [Math.floor(width * 0.8), Math.floor(height * 0.2)]
            ];

            let nonWhiteCount = 0;
            for (const [x, y] of samplePoints) {
                const pixel = context.getImageData(x, y, 1, 1).data;
                const [r, g, b, a] = pixel;
                const isWhiteLike = a > 0 && r >= 250 && g >= 250 && b >= 250;
                if (!isWhiteLike) nonWhiteCount += 1;
            }
            return nonWhiteCount === 0;
        } catch {
            return false;
        }
    }

    function collectTextBlocksFromHtml(contentHtml) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(contentHtml || '', 'text/html');
        const blocks = [];

        doc.querySelectorAll('h1,h2,h3,h4,h5,h6,p,blockquote,pre').forEach((node) => {
            const text = (node.textContent || '').replace(/\s+/g, ' ').trim();
            if (!text) return;
            const tag = node.tagName.toLowerCase();
            if (tag.startsWith('h')) {
                blocks.push({ kind: 'heading', text, level: Number(tag.slice(1)) || 3 });
                return;
            }
            if (tag === 'blockquote') {
                blocks.push({ kind: 'quote', text: `❝ ${text} ❞` });
                return;
            }
            if (tag === 'pre') {
                blocks.push({ kind: 'pre', text });
                return;
            }
            blocks.push({ kind: 'paragraph', text });
        });

        if (blocks.length) return blocks;

        const plain = (doc.body.textContent || '').replace(/\s+/g, ' ').trim();
        if (!plain) return [];
        return plain.split(/\s{2,}/).filter(Boolean).map((text) => ({ kind: 'paragraph', text }));
    }

    function wrapTextLines(ctx, text, maxWidth) {
        const words = String(text || '').split(' ').filter(Boolean);
        if (!words.length) return [];

        const lines = [];
        let currentLine = '';

        for (const word of words) {
            const trial = currentLine ? `${currentLine} ${word}` : word;
            if (ctx.measureText(trial).width <= maxWidth) {
                currentLine = trial;
            } else {
                if (currentLine) lines.push(currentLine);
                currentLine = word;
            }
        }

        if (currentLine) lines.push(currentLine);
        return lines;
    }

    function createPdfPageCanvas({ premiumBook = false } = {}) {
        const canvas = document.createElement('canvas');
        canvas.width = 1240;
        canvas.height = 1754;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#f7f3ea';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const patternColor = 'rgba(201, 162, 39, 0.065)';
        for (let y = 34; y < canvas.height; y += 66) {
            for (let x = 34; x < canvas.width; x += 66) {
                ctx.fillStyle = patternColor;
                ctx.beginPath();
                ctx.arc(x, y, 1.45, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        const panelX = 52;
        const panelY = 246;
        const panelW = canvas.width - 104;
        const panelH = canvas.height - 326;
        ctx.fillStyle = 'rgba(255, 255, 255, 0.93)';
        ctx.strokeStyle = 'rgba(201, 162, 39, 0.35)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(panelX, panelY, panelW, panelH, 24);
        ctx.fill();
        ctx.stroke();

        ctx.strokeStyle = 'rgba(26, 95, 74, 0.12)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(panelX + 12, panelY + 12, panelW - 24, panelH - 24, 20);
        ctx.stroke();

        if (premiumBook) {
            const ribbon = ctx.createLinearGradient(panelX, panelY, panelX + panelW, panelY);
            ribbon.addColorStop(0, 'rgba(26, 95, 74, 0.16)');
            ribbon.addColorStop(1, 'rgba(201, 162, 39, 0.18)');
            ctx.fillStyle = ribbon;
            ctx.beginPath();
            ctx.roundRect(panelX + 18, panelY + 18, panelW - 36, 16, 8);
            ctx.fill();

            ctx.fillStyle = 'rgba(26, 95, 74, 0.12)';
            ctx.beginPath();
            ctx.arc(panelX + 30, panelY + 40, 3, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.arc(panelX + panelW - 30, panelY + 40, 3, 0, Math.PI * 2);
            ctx.fill();
        }

        return { canvas, ctx };
    }

    function createPdfOutroCanvas(payload, outroLine = '') {
        const canvas = document.createElement('canvas');
        canvas.width = 1240;
        canvas.height = 1754;
        const ctx = canvas.getContext('2d');

        const outroGradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        outroGradient.addColorStop(0, '#1a5f4a');
        outroGradient.addColorStop(0.55, '#145341');
        outroGradient.addColorStop(1, '#0f3d2f');
        ctx.fillStyle = outroGradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.strokeStyle = 'rgba(212, 175, 55, 0.85)';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.roundRect(86, 94, canvas.width - 172, canvas.height - 188, 28);
        ctx.stroke();

        ctx.direction = 'rtl';
        ctx.textAlign = 'center';

        ctx.fillStyle = '#d4af37';
        ctx.font = 'bold 54px Cairo, Tahoma, Arial';
        ctx.fillText('تم بحمد الله', canvas.width / 2, 500);

        const safeOutro = String(outroLine || '').replace(/\s+/g, ' ').trim();
        if (safeOutro) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.93)';
            ctx.font = '32px Cairo, Tahoma, Arial';
            const lines = wrapTextLines(ctx, safeOutro, 860).slice(0, 3);
            let y = 650;
            for (const line of lines) {
                ctx.fillText(line, canvas.width / 2, y);
                y += 56;
            }
        }

        ctx.fillStyle = 'rgba(212, 175, 55, 0.98)';
        ctx.font = '700 30px Cairo, Tahoma, Arial';
        ctx.fillText(typeLabel(payload.type), canvas.width / 2, 1320);

        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.font = '700 36px Cairo, Tahoma, Arial';
        ctx.fillText('الشيخ أحمد إسماعيل الفشني', canvas.width / 2, 1480);

        return canvas;
    }

    function createPdfCoverCanvas(payload, coverCenterLines = []) {
        const canvas = document.createElement('canvas');
        canvas.width = 1240;
        canvas.height = 1754;
        const ctx = canvas.getContext('2d');

        const coverGradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        coverGradient.addColorStop(0, '#0f3d2f');
        coverGradient.addColorStop(0.55, '#1a5f4a');
        coverGradient.addColorStop(1, '#2b7b62');
        ctx.fillStyle = coverGradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = 'rgba(212, 175, 55, 0.1)';
        for (let y = 44; y < canvas.height; y += 90) {
            for (let x = 44; x < canvas.width; x += 90) {
                ctx.beginPath();
                ctx.arc(x, y, 2.2, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        const frameX = 88;
        const frameY = 96;
        const frameW = canvas.width - 176;
        const frameH = canvas.height - 192;

        ctx.strokeStyle = 'rgba(212, 175, 55, 0.86)';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.roundRect(frameX, frameY, frameW, frameH, 28);
        ctx.stroke();

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.35)';
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.roundRect(frameX + 16, frameY + 16, frameW - 32, frameH - 32, 22);
        ctx.stroke();

        ctx.direction = 'rtl';
        ctx.textAlign = 'center';

        ctx.fillStyle = '#d4af37';
        ctx.font = 'bold 30px Cairo, Tahoma, Arial';
        ctx.fillText(typeLabel(payload.type), canvas.width / 2, 370);

        const title = String(payload.title || 'محتوى').replace(/\s+/g, ' ').trim();
        const subtitle = String(payload.subtitle || '').replace(/\s+/g, ' ').trim();
        const maxTitleWidth = 860;
        const baseTitleSize = title.length > 80 ? 58 : title.length > 52 ? 64 : 72;

        ctx.fillStyle = '#ffffff';
        ctx.font = `bold ${baseTitleSize}px Cairo, Tahoma, Arial`;
        const titleLines = wrapTextLines(ctx, title, maxTitleWidth).slice(0, 3);
        let titleY = 500;
        const titleLineHeight = Math.round(baseTitleSize * 1.25);
        for (const line of titleLines) {
            ctx.fillText(line, canvas.width / 2, titleY);
            titleY += titleLineHeight;
        }

        if (subtitle) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.92)';
            ctx.font = '34px Cairo, Tahoma, Arial';
            const subtitleLines = wrapTextLines(ctx, subtitle, 920).slice(0, 2);
            titleY += 28;
            for (const line of subtitleLines) {
                ctx.fillText(line, canvas.width / 2, titleY);
                titleY += 52;
            }
        }

        if (payload.meta) {
            ctx.fillStyle = 'rgba(212, 175, 55, 0.95)';
            ctx.font = '28px Cairo, Tahoma, Arial';
            const metaLines = wrapTextLines(ctx, String(payload.meta), 930).slice(0, 2);
            let metaY = Math.min(1220, titleY + 120);
            for (const line of metaLines) {
                ctx.fillText(line, canvas.width / 2, metaY);
                metaY += 44;
            }
        }

        if (coverCenterLines.length) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.92)';
            ctx.font = '32px Cairo, Tahoma, Arial';
            const centerLines = coverCenterLines
                .map(line => String(line || '').replace(/\s+/g, ' ').trim())
                .filter(Boolean)
                .slice(0, 2);
            let centerY = 980;
            for (const line of centerLines) {
                const wrapped = wrapTextLines(ctx, line, 860).slice(0, 2);
                for (const chunk of wrapped) {
                    ctx.fillText(chunk, canvas.width / 2, centerY);
                    centerY += 52;
                }
                centerY += 18;
            }
        }

        const hasAuthorInMeta = /أحمد\s+إسماعيل\s+الفشني/.test(String(payload.meta || ''));
        if (!hasAuthorInMeta) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
            ctx.font = '700 34px Cairo, Tahoma, Arial';
            ctx.fillText('الشيخ أحمد إسماعيل الفشني', canvas.width / 2, 1530);
        }

        return canvas;
    }

    function drawPageHeader(ctx, payload, pageNumber) {
        const width = 1240;
        const headHeight = 184;
        const gradient = ctx.createLinearGradient(0, 0, width, headHeight);
        gradient.addColorStop(0, '#145341');
        gradient.addColorStop(1, '#1f7a5a');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(46, 42, width - 92, headHeight, 18);
        ctx.fill();

        ctx.direction = 'rtl';
        ctx.textAlign = 'right';

        const badgeX = 80;
        const badgeY = 66;
        const badgeW = 136;
        const badgeH = 44;
        ctx.fillStyle = '#d4af37';
        ctx.beginPath();
        ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 22);
        ctx.fill();

        ctx.fillStyle = '#1a5f4a';
        ctx.font = 'bold 22px Cairo, Tahoma, Arial';
        ctx.textAlign = 'center';
        ctx.fillText(typeLabel(payload.type), badgeX + (badgeW / 2), 93);
        ctx.textAlign = 'right';

        ctx.fillStyle = '#ffffff';
        const normalizedTitle = String(payload.title || 'محتوى').replace(/\s+/g, ' ').trim().slice(0, 220);
        const isKhutba = payload.type === 'khutba';
        const titleFontSize = isKhutba
            ? (normalizedTitle.length > 110 ? 32 : normalizedTitle.length > 85 ? 34 : normalizedTitle.length > 60 ? 36 : 40)
            : (normalizedTitle.length > 110 ? 34 : normalizedTitle.length > 85 ? 36 : normalizedTitle.length > 60 ? 38 : 42);
        const titleLineHeight = Math.round(titleFontSize * 1.2);
        const titleMaxLines = 3;
        const titleMaxWidth = width - 230;

        ctx.font = `bold ${titleFontSize}px Cairo, Tahoma, Arial`;
        const wrappedTitleLines = wrapTextLines(ctx, normalizedTitle, titleMaxWidth);
        const titleLines = wrappedTitleLines.slice(0, titleMaxLines);

        if (wrappedTitleLines.length > titleMaxLines && titleLines.length) {
            let lastLine = titleLines[titleLines.length - 1];
            while (lastLine.length > 4 && ctx.measureText(`${lastLine}…`).width > titleMaxWidth) {
                lastLine = lastLine.slice(0, -1).trim();
            }
            titleLines[titleLines.length - 1] = `${lastLine}…`;
        }

        let titleY = 136;
        for (const line of titleLines) {
            ctx.fillText(line, width - 80, titleY);
            titleY += titleLineHeight;
        }

        if (payload.subtitle) {
            ctx.font = '24px Cairo, Tahoma, Arial';
            const subtitleY = Math.min(titleY + 8, 226);
            ctx.fillText(String(payload.subtitle).slice(0, 160), width - 80, subtitleY);
        }

    }

    function drawPageFooter(ctx, pageNumber, payload) {
        const width = 1240;
        const y = 1708;
        ctx.strokeStyle = 'rgba(201, 162, 39, 0.35)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(80, y - 34);
        ctx.lineTo(width - 80, y - 34);
        ctx.stroke();

        ctx.direction = 'rtl';
        ctx.textAlign = 'center';
        const isBook = payload?.type === 'book';
        ctx.fillStyle = isBook ? '#4b5f57' : '#666';
        ctx.font = '20px Cairo, Tahoma, Arial';
        ctx.fillText('الشيخ أحمد إسماعيل الفشني', width / 2, y);

        ctx.textAlign = 'left';
        ctx.fillText(String(pageNumber), 90, y);
    }

    function renderPayloadToCanvases(payload) {
        let blocks = dedupeSequentialTextBlocks(collectTextBlocksFromHtml(payload.contentHtml || ''));
        const canvases = [];
        const isBook = payload.type === 'book';
        const chapterPerPage = payload.layoutMode === 'chapter-per-page';
        const storyPerPage = payload.layoutMode === 'story-per-page';
        const isKhatraHeading = (block) => block.kind === 'heading' && /الخاطرة\s*\(/.test(String(block.text || ''));
        const isCoverBoundaryHeading = (text) => /^(\d+[\)\-\.]|أولاً|ثانياً|ثالثاً|رابعاً|خامساً|سادساً|المجلس|الدرس|الفصل|الباب|المقدمة|الخاتمة|تمهيد|شرح|الخاطرة)/.test(String(text || '').trim());
        const normalizeArabic = (text) => String(text || '')
            .replace(/[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g, '')
            .replace(/ـ/g, '')
            .replace(/[إأآٱ]/g, 'ا')
            .replace(/ى/g, 'ي')
            .replace(/ة/g, 'ه')
            .replace(/\s+/g, ' ')
            .trim();
        const isIntroHeading = (text) => {
            const normalized = normalizeArabic(text);
            return /^(المقدمه|مقدمه)(\s+الكتاب)?$/.test(normalized);
        };
        const isCoverCandidateIntroLine = (text) => {
            const normalized = String(text || '').replace(/\s+/g, ' ').trim();
            if (!normalized) return false;
            if (/^بسم\s+الله/.test(normalized)) return false;
            if (/^(بقلم|أحمد\s+إسماعيل\s+الفشني)/.test(normalized)) return false;
            return normalized.length >= 24 && normalized.length <= 260;
        };

        let coverCenterLines = [];
        if (payload.type === 'book') {
            const leadingIntroBlocks = [];
            for (const block of blocks) {
                if (block.kind === 'heading' && isCoverBoundaryHeading(block.text)) break;
                leadingIntroBlocks.push(block);
                if (leadingIntroBlocks.length >= 14) break;
            }

            coverCenterLines = leadingIntroBlocks
                .filter(block => block.kind === 'paragraph' && isCoverCandidateIntroLine(block.text))
                .map(block => block.text)
                .slice(0, 2);
        }

        if (coverCenterLines.length) {
            for (const line of coverCenterLines) {
                const idx = blocks.findIndex(block => block.kind === 'paragraph' && block.text === line);
                if (idx >= 0) blocks.splice(idx, 1);
            }
        }

        let introSectionBlocks = [];
        if (isBook && blocks.length) {
            const firstHeadingIndex = blocks.findIndex((block) => block.kind === 'heading');
            if (firstHeadingIndex >= 0 && isIntroHeading(blocks[firstHeadingIndex].text)) {
                const nextHeadingIndex = blocks.findIndex((block, idx) => idx > firstHeadingIndex && block.kind === 'heading');
                const introEndIndex = nextHeadingIndex >= 0 ? nextHeadingIndex - 1 : blocks.length - 1;
                introSectionBlocks = blocks.slice(0, introEndIndex + 1);
                blocks = blocks.slice(introEndIndex + 1);
            }
        }

        const extractOutroLine = () => {
            for (let i = blocks.length - 1; i >= 0; i -= 1) {
                const block = blocks[i];
                if (block.kind !== 'paragraph' && block.kind !== 'quote') continue;
                const line = String(block.text || '').replace(/\s+/g, ' ').trim();
                if (!line) continue;
                if (line.length < 30 || line.length > 240) continue;
                if (/^(بقلم|أحمد\s+إسماعيل\s+الفشني|هذا\s+وما|والله\s+ورسوله)/.test(line)) continue;
                return line;
            }
            return '';
        };
        const outroLine = isBook ? extractOutroLine() : '';

        canvases.push(createPdfCoverCanvas(payload, coverCenterLines));

        let pageNumber = 1;
        let page = createPdfPageCanvas({ premiumBook: isBook });
        drawPageHeader(page.ctx, payload, pageNumber);

        const marginX = 100;
        const maxWidth = page.canvas.width - (marginX * 2);
        const contentTop = 320;
        const contentBottom = 1585;
        let y = contentTop;

        const newPage = ({ centerContinuation = false } = {}) => {
            drawPageFooter(page.ctx, pageNumber, payload);
            canvases.push(page.canvas);
            pageNumber += 1;
            page = createPdfPageCanvas({ premiumBook: isBook });
            drawPageHeader(page.ctx, payload, pageNumber);
            y = centerContinuation ? 720 : contentTop;
        };

        const isMajorHeading = (text) => {
            const normalized = String(text || '').trim();
            if (!normalized) return false;
            return isCoverBoundaryHeading(normalized);
        };

        const refinedStyle = isBook
            ? {
                heading: { font: 'bold 30px Cairo, Tahoma, Arial', color: '#145341', lineHeight: 44, gapBefore: 13, gapAfter: 10 },
                quote: { font: '23px Cairo, Tahoma, Arial', color: '#2f765a', lineHeight: 36, gapBefore: 8, gapAfter: 8 },
                pre: { font: '21px Cairo, Tahoma, Arial', color: '#333', lineHeight: 32, gapBefore: 6, gapAfter: 6 },
                paragraph: { font: '23px Cairo, Tahoma, Arial', color: '#1f2c2a', lineHeight: 35, gapBefore: 5, gapAfter: 7 }
            }
            : {
                heading: { font: 'bold 34px Cairo, Tahoma, Arial', color: '#1a5f4a', lineHeight: 48, gapBefore: 14, gapAfter: 12 },
                quote: { font: '26px Cairo, Tahoma, Arial', color: '#2e7d32', lineHeight: 40, gapBefore: 10, gapAfter: 10 },
                pre: { font: '24px Cairo, Tahoma, Arial', color: '#333', lineHeight: 36, gapBefore: 8, gapAfter: 8 },
                paragraph: { font: '26px Cairo, Tahoma, Arial', color: '#222', lineHeight: 40, gapBefore: 6, gapAfter: 8 }
            };

        const introBase = {
            heading: { weight: 'bold', size: 42, color: '#145341', lineHeight: 60, gapBefore: 18, gapAfter: 16 },
            quote: { weight: '', size: 32, color: '#2f765a', lineHeight: 50, gapBefore: 12, gapAfter: 12 },
            pre: { weight: '', size: 28, color: '#333', lineHeight: 45, gapBefore: 10, gapAfter: 10 },
            paragraph: { weight: '', size: 34, color: '#1f2c2a', lineHeight: 54, gapBefore: 10, gapAfter: 12 }
        };

        const introStyleFor = (kind, scale) => {
            const base = introBase[kind] || introBase.paragraph;
            const px = Math.max(14, Math.round(base.size * scale));
            const lineHeight = Math.max(22, Math.round(base.lineHeight * scale));
            const gapBefore = Math.max(2, Math.round(base.gapBefore * scale));
            const gapAfter = Math.max(3, Math.round(base.gapAfter * scale));
            return {
                font: `${base.weight ? `${base.weight} ` : ''}${px}px Cairo, Tahoma, Arial`,
                color: base.color,
                lineHeight,
                gapBefore,
                gapAfter
            };
        };

        const measureFittedIntroHeight = (sectionBlocks, scale, sectionMaxWidth) => {
            let total = 0;
            for (const block of sectionBlocks) {
                const style = introStyleFor(block.kind, scale);
                page.ctx.font = style.font;
                const lines = wrapTextLines(page.ctx, block.text, sectionMaxWidth);
                total += style.gapBefore + (lines.length * style.lineHeight) + style.gapAfter;
            }
            return total;
        };

        const renderIntroAsSinglePage = (sectionBlocks) => {
            if (!isBook || !sectionBlocks.length) return false;

            const sectionMaxWidth = Math.min(maxWidth, 900);
            const availableHeight = contentBottom - contentTop;
            const targetHeight = availableHeight * 0.985;

            let low = 0.28;
            let high = 2.2;
            for (let i = 0; i < 16; i += 1) {
                const mid = (low + high) / 2;
                const needed = measureFittedIntroHeight(sectionBlocks, mid, sectionMaxWidth);
                if (needed <= targetHeight) low = mid;
                else high = mid;
            }

            const scale = low;
            const neededHeight = measureFittedIntroHeight(sectionBlocks, scale, sectionMaxWidth);
            y = contentTop + Math.max(0, (availableHeight - neededHeight) / 2);

            for (const block of sectionBlocks) {
                const style = introStyleFor(block.kind, scale);
                y += style.gapBefore;

                page.ctx.direction = 'rtl';
                page.ctx.textAlign = 'center';
                page.ctx.font = style.font;
                page.ctx.fillStyle = style.color;

                const lines = wrapTextLines(page.ctx, block.text, sectionMaxWidth);
                for (const line of lines) {
                    page.ctx.fillText(line, page.canvas.width / 2, y);
                    y += style.lineHeight;
                }
                y += style.gapAfter;
            }

            return true;
        };

        if (!chapterPerPage && !storyPerPage) {
            const renderedIntroPage = renderIntroAsSinglePage(introSectionBlocks);
            if (renderedIntroPage && blocks.length) {
                newPage();
            }

            for (let index = 0; index < blocks.length; index += 1) {
                const block = blocks[index];
                if (block.kind === 'heading' && isMajorHeading(block.text) && y > 1320) {
                    newPage();
                }

                const style = refinedStyle[block.kind] || refinedStyle.paragraph;
                y += style.gapBefore;
                page.ctx.direction = 'rtl';
                page.ctx.textAlign = 'right';
                page.ctx.font = style.font;
                page.ctx.fillStyle = style.color;

                const lines = wrapTextLines(page.ctx, block.text, maxWidth);
                for (const line of lines) {
                    if (y > contentBottom) {
                        newPage();
                        page.ctx.direction = 'rtl';
                        page.ctx.textAlign = 'right';
                        page.ctx.font = style.font;
                        page.ctx.fillStyle = style.color;
                    }
                    page.ctx.fillText(line, page.canvas.width - marginX, y);
                    y += style.lineHeight;
                }
                y += style.gapAfter;
            }

            drawPageFooter(page.ctx, pageNumber, payload);
            canvases.push(page.canvas);
            if (isBook) {
                canvases.push(createPdfOutroCanvas(payload, outroLine));
            }
            return canvases;
        }

        const chapterBase = isBook
            ? {
                heading: { weight: 'bold', size: 29, color: '#145341', lineHeight: 41, gapBefore: 11, gapAfter: 9 },
                quote: { weight: '', size: 22, color: '#2f765a', lineHeight: 33, gapBefore: 8, gapAfter: 7 },
                pre: { weight: '', size: 20, color: '#333', lineHeight: 30, gapBefore: 6, gapAfter: 6 },
                paragraph: { weight: '', size: 21, color: '#1f2c2a', lineHeight: 31, gapBefore: 5, gapAfter: 6 }
            }
            : {
                heading: { weight: 'bold', size: 32, color: '#1a5f4a', lineHeight: 46, gapBefore: 14, gapAfter: 12 },
                quote: { weight: '', size: 25, color: '#2e7d32', lineHeight: 38, gapBefore: 10, gapAfter: 10 },
                pre: { weight: '', size: 23, color: '#333', lineHeight: 34, gapBefore: 8, gapAfter: 8 },
                paragraph: { weight: '', size: 24, color: '#222', lineHeight: 36, gapBefore: 6, gapAfter: 8 }
            };

        const chapterStyleFor = (kind, scale) => {
            const base = chapterBase[kind] || chapterBase.paragraph;
            const px = Math.max(17, Math.round(base.size * scale));
            const lineHeight = Math.max(24, Math.round(base.lineHeight * scale));
            const gapBefore = Math.max(3, Math.round(base.gapBefore * scale));
            const gapAfter = Math.max(4, Math.round(base.gapAfter * scale));
            return {
                font: `${base.weight ? `${base.weight} ` : ''}${px}px Cairo, Tahoma, Arial`,
                color: base.color,
                lineHeight,
                gapBefore,
                gapAfter
            };
        };

        const measureSectionHeight = (sectionBlocks, scale, sectionMaxWidth) => {
            let total = 0;
            for (const block of sectionBlocks) {
                const style = chapterStyleFor(block.kind, scale);
                page.ctx.font = style.font;
                const lines = wrapTextLines(page.ctx, block.text, sectionMaxWidth);
                total += style.gapBefore + (lines.length * style.lineHeight) + style.gapAfter;
            }
            return total;
        };

        const introBlocks = [];
        const contentSections = [];
        let activeSection = null;

        const isStorySectionStart = (block) => {
            if (!storyPerPage || block.kind !== 'heading') return false;
            const normalized = normalizeArabic(block.text);
            return (Number(block.level || 3) <= 2) || /^((ال)?قصه\s+\S+|سلسله|الحلقه\s+\S+)/.test(normalized);
        };

        for (const block of blocks) {
            if (isKhatraHeading(block) || isStorySectionStart(block)) {
                activeSection = [block];
                contentSections.push(activeSection);
                continue;
            }

            if (activeSection) activeSection.push(block);
            else introBlocks.push(block);
        }

        if (coverCenterLines.length) {
            let removed = 0;
            for (let i = 0; i < introBlocks.length && removed < coverCenterLines.length; i += 1) {
                const block = introBlocks[i];
                if (block.kind !== 'paragraph') continue;
                if (block.text !== coverCenterLines[removed]) continue;
                introBlocks.splice(i, 1);
                removed += 1;
                i -= 1;
            }
        }

        const centeredIntroBlocks = introSectionBlocks.length ? introSectionBlocks : introBlocks;

        const renderSection = (sectionBlocks, { centered = false, forceNewPage = false } = {}) => {
            if (!sectionBlocks.length) return;

            if (forceNewPage && y > contentTop + 2) {
                newPage();
            }

            const sectionMaxWidth = centered ? Math.min(maxWidth, 860) : maxWidth;
            const availableHeight = contentBottom - contentTop;
            const scales = centered
                ? [1, 0.95, 0.9, 0.86, 0.82, 0.78]
                : [1, 0.95, 0.9, 0.86, 0.82, 0.78, 0.74, 0.7, 0.66, 0.62, 0.58, 0.54, 0.5];

            let selectedScale = scales[scales.length - 1];
            for (const scale of scales) {
                const neededHeight = measureSectionHeight(sectionBlocks, scale, sectionMaxWidth);
                if (neededHeight <= availableHeight) {
                    selectedScale = scale;
                    break;
                }
            }

            y = contentTop;
            for (const block of sectionBlocks) {
                const style = chapterStyleFor(block.kind, selectedScale);
                y += style.gapBefore;

                page.ctx.direction = 'rtl';
                page.ctx.textAlign = centered ? 'center' : 'right';
                page.ctx.font = style.font;
                page.ctx.fillStyle = style.color;

                const lines = wrapTextLines(page.ctx, block.text, sectionMaxWidth);
                for (const line of lines) {
                    if (y > contentBottom) {
                        newPage({ centerContinuation: centered });
                        y = centered ? 720 : contentTop;
                        page.ctx.direction = 'rtl';
                        page.ctx.textAlign = centered ? 'center' : 'right';
                        page.ctx.font = style.font;
                        page.ctx.fillStyle = style.color;
                    }

                    page.ctx.fillText(line, centered ? (page.canvas.width / 2) : (page.canvas.width - marginX), y);
                    y += style.lineHeight;
                }
                y += style.gapAfter;
            }
        };

        const renderedIntroPage = renderIntroAsSinglePage(centeredIntroBlocks);
        if (renderedIntroPage && contentSections.length) {
            newPage();
        }
        contentSections.forEach((section) => renderSection(section, { centered: false, forceNewPage: true }));

        if (!contentSections.length && introBlocks.length && !introSectionBlocks.length) {
            renderSection(introBlocks, { centered: false, forceNewPage: false });
        }

        drawPageFooter(page.ctx, pageNumber, payload);
        canvases.push(page.canvas);
        if (isBook) {
            canvases.push(createPdfOutroCanvas(payload, outroLine));
        }
        return canvases;
    }

    async function renderShellToCanvas(shell, scale) {
        if (!window.html2canvas) {
            throw new Error('html2canvas is unavailable');
        }
        return window.html2canvas(shell, {
            scale,
            useCORS: true,
            backgroundColor: '#ffffff',
            windowWidth: 794,
            scrollX: 0,
            scrollY: 0,
            removeContainer: true,
            logging: false
        });
    }

    function saveCanvasAsPdf(canvas, filename) {
        const JsPdfCtor = window.jspdf?.jsPDF;
        if (!JsPdfCtor) {
            throw new Error('jsPDF is unavailable');
        }

        const pdf = new JsPdfCtor({ unit: 'mm', format: 'a4', orientation: 'portrait' });
        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();
        const margin = 8;
        const printableWidth = pageWidth - (margin * 2);
        const printableHeight = pageHeight - (margin * 2);

        const imageData = canvas.toDataURL('image/jpeg', 0.98);
        const imageHeight = (canvas.height * printableWidth) / canvas.width;

        let heightLeft = imageHeight;
        let yPosition = margin;

        pdf.addImage(imageData, 'JPEG', margin, yPosition, printableWidth, imageHeight);
        heightLeft -= printableHeight;

        while (heightLeft > 0) {
            yPosition = margin - (imageHeight - heightLeft);
            pdf.addPage();
            pdf.addImage(imageData, 'JPEG', margin, yPosition, printableWidth, imageHeight);
            heightLeft -= printableHeight;
        }

        pdf.save(filename);
    }

    function saveCanvasesAsPdf(canvases, filename) {
        const JsPdfCtor = window.jspdf?.jsPDF;
        if (!JsPdfCtor) {
            throw new Error('jsPDF is unavailable');
        }

        const pdf = new JsPdfCtor({ unit: 'mm', format: 'a4', orientation: 'portrait' });
        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();

        canvases.forEach((canvas, index) => {
            const imageData = canvas.toDataURL('image/jpeg', 0.95);
            if (index > 0) pdf.addPage();
            pdf.addImage(imageData, 'JPEG', 0, 0, pageWidth, pageHeight);
        });

        pdf.save(filename);
    }

    function extractContentFromDocument(doc) {
        const contentRoot = doc.querySelector(
            '.book-container, .khutba-content, .newspaper-article, .article-body, .content-card, .text-content, .book-content, .article-content, .content-section main, .content-section, main, article'
        );
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

        const primaryContent = buildReadableContentHtml(contentRoot ? contentRoot.innerHTML : '');
        const fallbackContent = extractFallbackBodyHtml(doc);
        const finalContent = primaryContent || fallbackContent || '<p>لا يوجد محتوى متاح للتصدير.</p>';

        return {
            title,
            subtitle,
            meta,
            contentHtml: finalContent
        };
    }

    async function exportPayload(payload, filenameHint) {
        await ensurePdfDependencies();
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
            try {
                const templateCanvases = renderPayloadToCanvases(payload);
                if (!templateCanvases.length || templateCanvases.every((canvas) => canvasLooksBlank(canvas))) {
                    throw new Error('Template pipeline produced blank output');
                }
                saveCanvasesAsPdf(templateCanvases, filename);
            } catch (primaryError) {
                console.warn('Template PDF pipeline failed, trying visual capture fallback.', primaryError);
                if (!window.html2canvas) {
                    throw primaryError;
                }

                let canvas = await renderShellToCanvas(shell, 2);
                if (canvasLooksBlank(canvas)) {
                    canvas = await renderShellToCanvas(shell, 1.35);
                }

                if (canvasLooksBlank(canvas)) {
                    throw new Error('Rendered canvas is blank');
                }

                saveCanvasAsPdf(canvas, filename);
            }
        } finally {
            shell.remove();
        }
    }

    async function exportFromCurrentPage(options = {}) {
        const extracted = extractContentFromDocument(document);
        const resolvedType = options.type || 'content';
        const resolvedTitle = options.title || extracted.title;
        const resolvedSubtitle = options.subtitle ?? extracted.subtitle;
        return exportPayload({
            ...extracted,
            type: resolvedType,
            title: resolvedTitle,
            subtitle: getBookCoverSubtitle({ type: resolvedType, title: resolvedTitle, subtitle: resolvedSubtitle }),
            meta: options.meta ?? extracted.meta,
            layoutMode: options.layoutMode || extracted.layoutMode
        }, options.filename || resolvedTitle);
    }

    async function exportFromUrl(url, options = {}) {
        const res = await fetch(url, { cache: 'no-cache' });
        if (!res.ok) throw new Error('تعذر تحميل الصفحة للتصدير');

        const html = await res.text();
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const extracted = extractContentFromDocument(doc);
        const resolvedType = options.type || 'content';
        const resolvedTitle = options.title || extracted.title;
        const resolvedSubtitle = options.subtitle ?? extracted.subtitle;

        return exportPayload({
            ...extracted,
            type: resolvedType,
            title: resolvedTitle,
            subtitle: getBookCoverSubtitle({ type: resolvedType, title: resolvedTitle, subtitle: resolvedSubtitle }),
            meta: options.meta ?? extracted.meta,
            layoutMode: options.layoutMode || extracted.layoutMode
        }, options.filename || resolvedTitle);
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
        btn.className = `${className} pdf-action-btn`;
        btn.innerHTML = `<i class="fas fa-download"></i> ${label}`;
        return btn;
    }

    function ensureActionGroup(readBtn) {
        if (!readBtn) return null;

        const existingGroup = readBtn.closest('.pdf-action-group');
        if (existingGroup) {
            readBtn.classList.add('pdf-action-btn');
            return existingGroup;
        }

        const parent = readBtn.parentElement;
        if (parent && parent.classList.contains('book-actions')) {
            parent.classList.add('pdf-action-group');
            readBtn.classList.add('pdf-action-btn');
            return parent;
        }

        const group = document.createElement('div');
        group.className = 'pdf-action-group';
        readBtn.insertAdjacentElement('beforebegin', group);
        group.appendChild(readBtn);
        readBtn.classList.add('pdf-action-btn');
        return group;
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
                    const isHowTheyLivedBook = /how-they-lived-how-we-live\.html$/i.test(href);
                    const isStoriesOfProphetsBook = /stories-of-prophets\.html$/i.test(href);
                    await exportFromUrl(new URL(href, window.location.href).href, {
                        type: 'book',
                        layoutMode: isHowTheyLivedBook
                            ? 'chapter-per-page'
                            : (isStoriesOfProphetsBook ? 'story-per-page' : undefined)
                    });
                } catch (err) {
                    console.error(err);
                    alert('تعذر إنشاء ملف PDF حالياً.');
                } finally {
                    btn.style.pointerEvents = '';
                    btn.innerHTML = '<i class="fas fa-download"></i> تحميل PDF';
                }
            });

            const group = ensureActionGroup(readBtn);
            group?.appendChild(btn);
        });
    }

    function appendButtonsOnArticlesPage() {
        document.querySelectorAll('.newspaper-content .btn, .featured-content .btn').forEach((readBtn) => {
            if (readBtn.parentElement?.querySelector('.js-download-pdf')) return;
            const href = readBtn.getAttribute('href');
            if (!href || !href.endsWith('.html')) return;

            const btn = makeButton('تحميل PDF', readBtn.className + ' js-download-pdf');

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

            const group = ensureActionGroup(readBtn);
            group?.appendChild(btn);
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
                const path = (window.location.pathname || '').toLowerCase();
                const isStoriesOfProphetsBook = /stories-of-prophets\.html$/.test(path);
                await exportFromCurrentPage({
                    type: 'book',
                    layoutMode: isStoriesOfProphetsBook ? 'story-per-page' : undefined
                });
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
