(function () {
    function normalizeArabicForSearch(text) {
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

    function sanitizeAnswerText(text) {
        let value = String(text || '').replace(/\s+/g, ' ').trim();
        value = value.replace(/\s+[0-9٠-٩]+\s*[\.)-]\s+[^.؟!?]+$/g, '').trim();
        return value;
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
            <button class="fatwa-toggle" type="button">عرض المزيد</button>
        `;

        const toggleBtn = card.querySelector('.fatwa-toggle');
        if (toggleBtn) {
            const answerEl = card.querySelector('.fatwa-answer');
            toggleBtn.addEventListener('click', () => {
                answerEl.classList.toggle('expanded');
                toggleBtn.textContent = answerEl.classList.contains('expanded') ? 'إخفاء' : 'عرض المزيد';
            });
        }

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
                const query = normalizeArabicForSearch(searchInput.value || '');
                const filtered = !query
                    ? searchable
                    : searchable.filter((item) => item._haystack.includes(query));
                renderFatawa(filtered, grid, empty);
            };

            searchInput.addEventListener('input', applyFilter);
            applyFilter();
        } catch (error) {
            console.error(error);
            empty.hidden = false;
            empty.textContent = 'تعذر تحميل الفتاوى حالياً. حاول لاحقاً.';
        }
    }

    document.addEventListener('DOMContentLoaded', initFatawaPage);
})();
