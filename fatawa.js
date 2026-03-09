(function () {
    const searchUtils = window.SiteSearchUtils || null;

    function normalizeArabicForSearch(text) {
        if (searchUtils?.normalize) return searchUtils.normalize(text);
        return String(text || '')
            .normalize('NFKD')
            .replace(/[\u064B-\u065F\u0670\u06D6-\u06ED]/g, '')
            .replace(/[أإآٱ]/g, 'ا')
            .replace(/[ؤئ]/g, 'ء')
            .replace(/ى/g, 'ي')
            .replace(/ة/g, 'ه')
            .replace(/\s+/g, ' ')
            .trim()
            .toLowerCase();
    }

    function createSearchMatcher(query) {
        if (searchUtils?.createMatcher) return searchUtils.createMatcher(query);
        const normalized = normalizeArabicForSearch(query);
        return {
            score(haystack) {
                const target = normalizeArabicForSearch(haystack);
                if (!target) return 0;
                if (!normalized) return 1;
                return target.includes(normalized) ? 1 : 0;
            }
        };
    }

    function sanitizeAnswerText(text) {
        let value = String(text || '').replace(/\s+/g, ' ').trim();
        value = value.replace(/\s+[0-9٠-٩]+\s*[\.)-]\s+[^.؟!?]+$/g, '').trim();
        return value;
    }

    function normalizeInlineTextLocal(text) {
        if (typeof window.normalizeInlineText === 'function') {
            return window.normalizeInlineText(text);
        }
        return String(text || '').replace(/\s+/g, ' ').trim();
    }

    function wrapCanvasText(ctx, text, maxWidth) {
        if (typeof window.wrapCanvasTextByWords === 'function') {
            return window.wrapCanvasTextByWords(ctx, text, maxWidth);
        }

        const words = normalizeInlineTextLocal(text).split(' ').filter(Boolean);
        const lines = [];
        let current = '';

        words.forEach((word) => {
            const next = current ? `${current} ${word}` : word;
            if (ctx.measureText(next).width <= maxWidth) {
                current = next;
            } else {
                if (current) lines.push(current);
                current = word;
            }
        });

        if (current) lines.push(current);
        return lines;
    }

    function canvasToBlobLocal(canvas) {
        if (typeof window.canvasToBlob === 'function') {
            return window.canvasToBlob(canvas, 'image/png', 0.96);
        }

        return new Promise((resolve, reject) => {
            if (!canvas?.toBlob) {
                reject(new Error('Canvas toBlob is unavailable'));
                return;
            }

            canvas.toBlob((blob) => {
                if (blob) resolve(blob);
                else reject(new Error('Failed to create image blob'));
            }, 'image/png', 0.96);
        });
    }

    function triggerBlobDownloadLocal(blob, filename) {
        if (typeof window.triggerBlobDownload === 'function') {
            window.triggerBlobDownload(blob, filename);
            return;
        }

        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1500);
    }

    function showShareToastLocal(message) {
        if (typeof window.showShareToast === 'function') {
            window.showShareToast(message);
            return;
        }

        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.left = '20px';
        toast.style.zIndex = '9999';
        toast.style.background = 'rgba(15, 23, 42, 0.9)';
        toast.style.color = '#fff';
        toast.style.padding = '10px 14px';
        toast.style.borderRadius = '10px';
        toast.style.fontSize = '0.9rem';
        toast.style.fontFamily = 'Cairo, sans-serif';
        toast.style.boxShadow = '0 8px 22px rgba(0,0,0,0.22)';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 1700);
    }

    function fitCanvasLines(ctx, text, maxWidth, maxHeight, fontSizes, weight) {
        const safeText = normalizeInlineTextLocal(text);
        for (const size of fontSizes) {
            const lineHeight = Math.round(size * 1.75);
            ctx.font = `${weight} ${size}px Cairo, Tahoma, Arial`;
            const lines = wrapCanvasText(ctx, safeText, maxWidth);
            const maxLines = Math.max(1, Math.floor(maxHeight / lineHeight));
            if (lines.length <= maxLines) {
                return { size, lineHeight, lines };
            }
        }

        const fallbackSize = fontSizes[fontSizes.length - 1];
        const lineHeight = Math.round(fallbackSize * 1.75);
        ctx.font = `${weight} ${fallbackSize}px Cairo, Tahoma, Arial`;
        const lines = wrapCanvasText(ctx, safeText, maxWidth);
        const maxLines = Math.max(1, Math.floor(maxHeight / lineHeight));
        const fitted = lines.slice(0, maxLines);
        if (lines.length > maxLines && fitted.length) {
            let last = fitted[fitted.length - 1];
            while (last.length > 3 && ctx.measureText(`${last}…`).width > maxWidth) {
                last = last.slice(0, -1).trim();
            }
            fitted[fitted.length - 1] = `${last}…`;
        }

        return { size: fallbackSize, lineHeight, lines: fitted };
    }

    async function createFatwaShareImageBlob({ question, answer, number, signature }) {
        if (document.fonts?.ready) {
            await Promise.race([
                document.fonts.ready,
                new Promise((resolve) => setTimeout(resolve, 1200))
            ]);
        }

        const canvas = document.createElement('canvas');
        canvas.width = 1080;
        canvas.height = 1350;

        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('Canvas context unavailable');

        const bgGradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        bgGradient.addColorStop(0, '#1a5f4a');
        bgGradient.addColorStop(1, '#1f7a5a');
        ctx.fillStyle = bgGradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = 'rgba(212, 175, 55, 0.09)';
        for (let y = 34; y < canvas.height; y += 78) {
            for (let x = 34; x < canvas.width; x += 78) {
                ctx.beginPath();
                ctx.arc(x, y, 2.1, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        const card = { x: 70, y: 150, width: 940, height: 1080 };
        ctx.fillStyle = 'rgba(255,255,255,0.97)';
        ctx.beginPath();
        ctx.roundRect(card.x, card.y, card.width, card.height, 30);
        ctx.fill();

        ctx.fillStyle = '#d4af37';
        ctx.beginPath();
        ctx.roundRect(card.x + card.width - 10, card.y + 14, 10, card.height - 28, 7);
        ctx.fill();

        ctx.direction = 'rtl';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#d4af37';
        ctx.font = '700 35px Cairo, Tahoma, Arial';
        ctx.fillText('أحكام فقهية', canvas.width / 2, 95);

        const safeNumber = normalizeInlineTextLocal(number || '');
        if (safeNumber) {
            const numberX = card.x + 74;
            const numberY = card.y + 86;
            ctx.fillStyle = '#1a5f4a';
            ctx.beginPath();
            ctx.arc(numberX, numberY, 34, 0, Math.PI * 2);
            ctx.fill();
            ctx.textAlign = 'center';
            ctx.fillStyle = '#d4af37';
            ctx.font = '700 34px Cairo, Tahoma, Arial';
            ctx.fillText(safeNumber, numberX, numberY + 12);
        }

        ctx.textAlign = 'right';
        ctx.fillStyle = 'rgba(212, 175, 55, 0.35)';
        ctx.font = '700 132px Cairo, Tahoma, Arial';
        ctx.fillText('؟', card.x + card.width - 58, card.y + 195);

        const textWidth = card.width - 116;
        const questionBoxY = card.y + 170;
        const questionBoxHeight = 215;
        ctx.fillStyle = 'rgba(26, 95, 74, 0.07)';
        ctx.beginPath();
        ctx.roundRect(card.x + 38, questionBoxY, card.width - 76, questionBoxHeight, 24);
        ctx.fill();

        const questionLayout = fitCanvasLines(
            ctx,
            question,
            textWidth - 28,
            questionBoxHeight - 56,
            [38, 35, 32, 29],
            700
        );
        ctx.fillStyle = '#12382c';
        ctx.font = `700 ${questionLayout.size}px Cairo, Tahoma, Arial`;
        let questionY = questionBoxY + 58;
        questionLayout.lines.forEach((line) => {
            ctx.fillText(line, card.x + card.width - 68, questionY);
            questionY += questionLayout.lineHeight;
        });

        ctx.fillStyle = '#d4af37';
        ctx.font = '700 30px Cairo, Tahoma, Arial';
        ctx.fillText('الجواب', card.x + card.width - 58, card.y + 450);

        const answerLayout = fitCanvasLines(
            ctx,
            answer,
            textWidth,
            500,
            [30, 28, 26, 24, 22],
            600
        );
        ctx.fillStyle = '#0f2f24';
        ctx.font = `600 ${answerLayout.size}px Cairo, Tahoma, Arial`;
        let answerY = card.y + 510;
        answerLayout.lines.forEach((line) => {
            ctx.fillText(line, card.x + card.width - 58, answerY);
            answerY += answerLayout.lineHeight;
        });

        const safeSignature = normalizeInlineTextLocal(signature || '— الشيخ أحمد إسماعيل الفشني');
        const signatureLineY = card.y + card.height - 122;
        ctx.strokeStyle = 'rgba(212, 175, 55, 0.45)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(card.x + 55, signatureLineY);
        ctx.lineTo(card.x + card.width - 55, signatureLineY);
        ctx.stroke();

        ctx.fillStyle = '#1a5f4a';
        ctx.font = '700 34px Cairo, Tahoma, Arial';
        ctx.textAlign = 'center';
        ctx.fillText(safeSignature, canvas.width / 2, signatureLineY + 58);

        ctx.fillStyle = 'rgba(255,255,255,0.88)';
        ctx.font = '600 20px Cairo, Tahoma, Arial';
        ctx.fillText('ahmedelfashny.com', canvas.width / 2, canvas.height - 42);

        return canvasToBlobLocal(canvas);
    }

    function bindShareButton(card, button, item, answerText) {
        if (!button || !card) return;

        button.addEventListener('click', async (event) => {
            event.preventDefault();

            const question = normalizeInlineTextLocal(item.question || '');
            const answer = normalizeInlineTextLocal(answerText || '');
            const number = normalizeInlineTextLocal(item.id || '');
            if (!question || !answer) return;

            const imageFileName = `fatwa-${number || 'share'}.png`;

            button.disabled = true;
            button.style.pointerEvents = 'none';
            button.style.opacity = '0.85';

            try {
                const imageBlob = await createFatwaShareImageBlob({
                    question,
                    answer,
                    number,
                    signature: '— الشيخ أحمد إسماعيل الفشني'
                });

                const imageFile = new File([imageBlob], imageFileName, { type: 'image/png' });
                const canShareImage = typeof navigator.canShare === 'function'
                    && navigator.canShare({ files: [imageFile] });

                if (navigator.share && canShareImage) {
                    await navigator.share({ files: [imageFile] });
                    showShareToastLocal('تمت مشاركة الحكم كصورة');
                    return;
                }

                if (navigator.clipboard?.write && window.ClipboardItem) {
                    await navigator.clipboard.write([
                        new ClipboardItem({ 'image/png': imageBlob })
                    ]);
                    showShareToastLocal('تم نسخ صورة الحكم للحافظة');
                    return;
                }

                triggerBlobDownloadLocal(imageBlob, imageFileName);
                showShareToastLocal('تم تنزيل صورة الحكم');
            } catch {
                try {
                    const fallbackBlob = await createFatwaShareImageBlob({
                        question,
                        answer,
                        number,
                        signature: '— الشيخ أحمد إسماعيل الفشني'
                    });
                    triggerBlobDownloadLocal(fallbackBlob, imageFileName);
                    showShareToastLocal('تم تنزيل صورة الحكم');
                } catch {
                    showShareToastLocal('تعذر مشاركة الصورة حالياً');
                }
            } finally {
                button.disabled = false;
                button.style.pointerEvents = '';
                button.style.opacity = '';
            }
        });
    }

    function updateCardOverflowState(card) {
        const answerEl = card.querySelector('.fatwa-answer');
        const toggleBtn = card.querySelector('.fatwa-toggle');
        if (!answerEl || !toggleBtn) return;

        answerEl.classList.remove('expanded', 'no-clamp');
        toggleBtn.textContent = 'عرض المزيد';
        toggleBtn.hidden = false;

        const isOverflowing = answerEl.scrollHeight > answerEl.clientHeight + 2;
        if (!isOverflowing) {
            answerEl.classList.add('no-clamp');
            toggleBtn.hidden = true;
        }
    }

    function createFatwaCard(item) {
        const answerText = sanitizeAnswerText(item.answer || '');
        const card = document.createElement('article');
        card.className = 'fatwa-card';
        card.innerHTML = `
            <span class="fatwa-number">${item.id}</span>
            <h3 class="fatwa-question">${item.question || ''}</h3>
            <div class="fatwa-answer">${answerText}</div>
            <div class="fatwa-card-footer">
                <span class="fatwa-card-meta"><i class="fas fa-circle-question"></i> أحكام فقهية</span>
                <div class="fatwa-card-actions">
                    <button class="fatwa-toggle" type="button">عرض المزيد</button>
                    <button class="fatwa-share-btn" type="button" title="مشاركة الحكم كصورة" aria-label="مشاركة الحكم كصورة">
                        <i class="fas fa-share-alt" aria-hidden="true"></i>
                        <span>مشاركة</span>
                    </button>
                </div>
            </div>
        `;

        const toggleBtn = card.querySelector('.fatwa-toggle');
        if (toggleBtn) {
            const answerEl = card.querySelector('.fatwa-answer');
            toggleBtn.addEventListener('click', () => {
                answerEl.classList.toggle('expanded');
                toggleBtn.textContent = answerEl.classList.contains('expanded') ? 'إخفاء' : 'عرض المزيد';
            });
        }

        bindShareButton(card, card.querySelector('.fatwa-share-btn'), item, answerText);

        return card;
    }

    function renderFatawa(items, grid, empty) {
        grid.innerHTML = '';
        if (!items.length) {
            empty.hidden = false;
            return;
        }

        empty.hidden = true;
        const fragment = document.createDocumentFragment();
        items.forEach((item) => fragment.appendChild(createFatwaCard(item)));
        grid.appendChild(fragment);

        requestAnimationFrame(() => {
            grid.querySelectorAll('.fatwa-card').forEach((card) => updateCardOverflowState(card));
        });
    }

    async function initFatawaPage() {
        const grid = document.getElementById('fatawaGrid');
        const empty = document.getElementById('fatawaEmpty');
        const searchInput = document.getElementById('fatawaSearchInput');
        const countElement = document.getElementById('fatawaCount');
        if (!grid || !empty || !searchInput || !countElement) return;

        try {
            const res = await fetch('data/fatawa.json', { cache: 'no-cache' });
            if (!res.ok) throw new Error('Failed to load fatawa data');
            const payload = await res.json();
            const allItems = Array.isArray(payload.items) ? payload.items : [];

            countElement.textContent = String(allItems.length);

            const searchable = allItems.map((item) => ({
                ...item,
                _haystack: normalizeArabicForSearch(`${item.question || ''} ${item.answer || ''}`)
            }));

            const applyFilter = () => {
                const query = (searchInput.value || '').trim();
                const matcher = createSearchMatcher(query);
                const filtered = !query
                    ? searchable
                    : searchable
                        .map((item) => ({ ...item, _score: matcher.score(item._haystack) }))
                        .filter((item) => item._score > 0)
                        .sort((a, b) => b._score - a._score || Number(a.id || 0) - Number(b.id || 0));
                renderFatawa(filtered, grid, empty);
            };

            searchInput.addEventListener('input', applyFilter);
            applyFilter();
        } catch (error) {
            console.error(error);
            empty.hidden = false;
            empty.textContent = 'تعذر تحميل الأحكام الفقهية حالياً. حاول لاحقاً.';
        }
    }

    document.addEventListener('DOMContentLoaded', initFatawaPage);
})();
