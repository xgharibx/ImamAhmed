document.addEventListener('DOMContentLoaded', () => {
    const sectionMap = {
        murattal: document.querySelector('#murattal .tilawa-videos-grid'),
        mujawwad: document.querySelector('#mujawwad .tilawa-videos-grid'),
        external: document.querySelector('#external .tilawa-videos-grid'),
        mihrab: document.querySelector('#mihrab .tilawa-videos-grid')
    };

    const emptyMessages = {
        murattal: document.querySelector('#murattal .empty-category-msg'),
        mujawwad: document.querySelector('#mujawwad .empty-category-msg'),
        external: document.querySelector('#external .empty-category-msg'),
        mihrab: document.querySelector('#mihrab .empty-category-msg')
    };

    fetch('data/videos.json')
        .then((response) => response.json())
        .then((rawData) => {
            const videos = (Array.isArray(rawData) ? rawData : []).filter(isDirectTilawah);
            const grouped = {
                murattal: [],
                mujawwad: [],
                external: [],
                mihrab: []
            };

            videos.forEach((video) => {
                const bucket = detectTilawahSection(video);
                grouped[bucket].push(video);
            });

            Object.entries(grouped).forEach(([section, list]) => {
                const target = sectionMap[section];
                if (!target) return;

                if (list.length === 0) {
                    target.innerHTML = '<p class="tilawa-empty-note">لا توجد تلاوات مصنفة في هذا القسم حالياً.</p>';
                    return;
                }

                if (emptyMessages[section]) {
                    emptyMessages[section].style.display = 'none';
                }

                list.forEach((video) => target.appendChild(createCard(video)));
            });
        })
        .catch((error) => {
            console.error('Failed to load tilawah videos:', error);
            Object.values(sectionMap).forEach((target) => {
                if (target) {
                    target.innerHTML = '<p class="tilawa-empty-note">تعذر تحميل التلاوات حالياً.</p>';
                }
            });
        });

    function normalizeArabic(text) {
        return (text || '')
            .toString()
            .normalize('NFKC')
            .replace(/[\u064B-\u0652\u0670]/g, '')
            .replace(/أ|إ|آ/g, 'ا')
            .replace(/ى/g, 'ي')
            .replace(/ة/g, 'ه')
            .replace(/\s+/g, ' ')
            .trim()
            .toLowerCase();
    }

    function hasAnyKeyword(text, keywords) {
        return keywords.some((keyword) => text.includes(keyword));
    }

    function isDirectTilawah(video) {
        const title = normalizeArabic(video?.title || '');

        const tvKeywords = ['تلفزيون', 'التلفزيون', 'شاشه', 'شاشة', 'النيل الثقافيه', 'النيل الثقافية', 'قناه', 'قناة', 'اذيع', 'يذاع', 'لقاء', 'مناره الازهر', 'منارة الازهر', 'منارة الأزهر'];
        const tafseerKeywords = ['تفسير', 'في نور القران', 'في نور القرآن'];
        const recitationKeywords = ['تلاوه', 'تلاوة', 'ما تيسر', 'سوره', 'سورة', 'المصحف', 'القران الكريم', 'القرآن الكريم', 'المجود', 'المرتل', 'آيات'];
        const mihrabHintKeywords = ['صلاه', 'صلاة', 'فجر', 'عشاء', 'محراب', 'تراويح', 'تهجد'];

        const hasRecitationSignal = hasAnyKeyword(title, recitationKeywords) || hasAnyKeyword(title, mihrabHintKeywords);
        const isTv = hasAnyKeyword(title, tvKeywords);
        const isTafseer = hasAnyKeyword(title, tafseerKeywords);

        return hasRecitationSignal && !isTv && !isTafseer;
    }

    function detectTilawahSection(video) {
        const title = normalizeArabic(video?.title || '');

        if (hasAnyKeyword(title, ['المجود', 'مجود', 'تجويد'])) return 'mujawwad';
        if (hasAnyKeyword(title, ['المرتل', 'مرتل'])) return 'murattal';
        if (hasAnyKeyword(title, ['صلاه', 'صلاة', 'فجر', 'عشاء', 'محراب', 'تراويح', 'تهجد', 'مسجد'])) return 'mihrab';
        return 'external';
    }

    function escapeHtml(text) {
        return (text || '')
            .toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function createCard(video) {
        const card = document.createElement('article');
        card.className = 'tilawa-video-card';

        const title = escapeHtml(video?.title || 'تلاوة');
        const videoId = (video?.id || '').toString().trim();
        const thumbnail = escapeHtml(video?.thumbnail || `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`);
        const duration = escapeHtml(video?.duration || '--:--');

        card.innerHTML = `
            <div class="tilawa-video-thumb" onclick="window.open('https://www.youtube.com/watch?v=${videoId}', '_blank', 'noopener')">
                <img src="${thumbnail}" alt="${title}" loading="lazy">
                <div class="tilawa-play-overlay"><i class="fas fa-play-circle"></i></div>
                <span class="tilawa-duration">${duration}</span>
            </div>
            <div class="tilawa-video-body">
                <h3 class="tilawa-video-title">${title}</h3>
                <div class="tilawa-video-actions">
                    <a class="btn btn-outline btn-sm" href="https://www.youtube.com/watch?v=${videoId}" target="_blank" rel="noopener">
                        <i class="fas fa-play"></i> مشاهدة
                    </a>
                </div>
            </div>
        `;

        return card;
    }
});
