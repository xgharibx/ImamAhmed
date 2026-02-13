document.addEventListener('DOMContentLoaded', () => {
    let allTilawat = [];
    let filteredTilawat = [];
    let currentPage = 1;
    const itemsPerPage = 20;
    let currentCategory = 'all';

    const grid = document.getElementById('tilawa-grid');
    const loadMoreBtn = document.getElementById('tilawa-load-more');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const modal = document.getElementById('video-modal');
    const modalIframe = document.getElementById('modal-iframe');
    const modalTitle = document.getElementById('modal-title');
    const closeModal = document.querySelector('.close-modal');

    fetch('data/videos.json')
        .then((response) => response.json())
        .then((rawData) => {
            allTilawat = (Array.isArray(rawData) ? rawData : [])
                .filter(isDirectTilawah)
                .map((video, index) => ({
                    ...video,
                    tilawaCategory: detectTilawahSection(video),
                    _sourceIndex: index,
                    _sortTimestamp: extractVideoTimestamp(video)
                }))
                .sort(sortByNewest);

            filterVideos('all');
        })
        .catch((error) => {
            console.error('Failed to load tilawah videos:', error);
            grid.innerHTML = '<p class="error-msg">تعذر تحميل التلاوات حالياً.</p>';
        });

    function filterVideos(category) {
        currentCategory = category;
        currentPage = 1;

        filterButtons.forEach((btn) => {
            if (btn.dataset.filter === category) btn.classList.add('active');
            else btn.classList.remove('active');
        });

        if (category === 'all') {
            filteredTilawat = allTilawat;
        } else {
            filteredTilawat = allTilawat.filter((video) => video.tilawaCategory === category);
        }

        grid.innerHTML = '';
        renderNextBatch();
    }

    function renderNextBatch() {
        const start = (currentPage - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const batch = filteredTilawat.slice(start, end);

        if (batch.length === 0 && currentPage === 1) {
            grid.innerHTML = '<p class="no-videos">لا توجد تلاوات في هذا القسم حالياً.</p>';
            loadMoreBtn.style.display = 'none';
            return;
        }

        batch.forEach((video) => {
            grid.appendChild(createVideoCard(video));
        });

        if (end >= filteredTilawat.length) {
            loadMoreBtn.style.display = 'none';
        } else {
            loadMoreBtn.style.display = 'block';
        }
    }

    function createVideoCard(video) {
        const div = document.createElement('div');
        div.className = 'video-card aos-init aos-animate';
        div.setAttribute('data-aos', 'fade-up');

        const title = escapeHtml(video?.title || 'تلاوة');
        const videoId = (video?.id || '').toString().trim();
        const thumbnail = escapeHtml(video?.thumbnail || `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`);
        const duration = escapeHtml(video?.duration || '--:--');

        const categoryMap = {
            murattal: { icon: 'fa-quran', text: 'المصحف المرتل' },
            mujawwad: { icon: 'fa-star-and-crescent', text: 'المصحف المجود' },
            external: { icon: 'fa-microphone-lines', text: 'تلاوات خارجية' },
            mihrab: { icon: 'fa-mosque', text: 'تلاوات المحراب' }
        };

        const categoryMeta = categoryMap[video.tilawaCategory] || categoryMap.external;

        div.innerHTML = `
            <div class="video-thumbnail" onclick="openTilawaVideo('${videoId}', '${title}')">
                <img src="${thumbnail}" alt="${title}" loading="lazy">
                <div class="video-embed placeholder">
                    <div class="play-overlay">
                        <i class="fas fa-play-circle"></i>
                        <span>تشغيل</span>
                    </div>
                </div>
                <div class="duration-badge">${duration}</div>
                <span class="video-category"><i class="fas ${categoryMeta.icon}"></i> ${categoryMeta.text}</span>
            </div>
            <div class="video-content">
                <h3 class="video-title" title="${title}">${title}</h3>
                <div class="video-actions">
                    <button class="btn btn-outline btn-sm" onclick="openTilawaVideo('${videoId}', '${title}')">
                        <i class="fas fa-play"></i> مشاهدة
                    </button>
                    <a href="https://www.youtube.com/watch?v=${videoId}" target="_blank" class="btn-yt-icon" title="فتح في يوتيوب" rel="noopener">
                        <i class="fab fa-youtube"></i>
                    </a>
                </div>
            </div>
        `;

        return div;
    }

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

    function normalizeDigits(text) {
        return (text || '').replace(/[٠-٩]/g, (d) => '٠١٢٣٤٥٦٧٨٩'.indexOf(d));
    }

    function extractDateFromText(text) {
        const normalizedText = normalizeDigits((text || '').toString());
        if (!normalizedText) return 0;

        const slashMatch = normalizedText.match(/(\d{1,2})\s*[\/\-]\s*(\d{1,2})\s*[\/\-]\s*(\d{2,4})/);
        if (slashMatch) {
            const day = Number.parseInt(slashMatch[1], 10);
            const month = Number.parseInt(slashMatch[2], 10);
            const rawYear = Number.parseInt(slashMatch[3], 10);
            const year = rawYear < 100 ? 2000 + rawYear : rawYear;
            const ts = Date.UTC(year, month - 1, day);
            return Number.isNaN(ts) ? 0 : ts;
        }

        const monthMap = {
            'يناير': 1, 'فبراير': 2, 'مارس': 3, 'ابريل': 4, 'أبريل': 4,
            'مايو': 5, 'يونيو': 6, 'يوليو': 7, 'اغسطس': 8, 'أغسطس': 8,
            'سبتمبر': 9, 'اكتوبر': 10, 'أكتوبر': 10, 'نوفمبر': 11, 'ديسمبر': 12
        };

        const namedMatch = normalizedText.match(/(\d{1,2})\s+([\u0621-\u064A]+)\s+(\d{4})/);
        if (namedMatch) {
            const day = Number.parseInt(namedMatch[1], 10);
            const monthName = namedMatch[2];
            const year = Number.parseInt(namedMatch[3], 10);
            const month = monthMap[monthName] || monthMap[normalizeArabic(monthName)] || 0;
            if (month > 0) {
                const ts = Date.UTC(year, month - 1, day);
                return Number.isNaN(ts) ? 0 : ts;
            }
        }

        const isoTs = Date.parse(normalizedText);
        return Number.isNaN(isoTs) ? 0 : isoTs;
    }

    function extractVideoTimestamp(video) {
        const fromDateField = extractDateFromText(video?.date || '');
        if (fromDateField) return fromDateField;
        return extractDateFromText(video?.title || '');
    }

    function sortByNewest(a, b) {
        if (b._sortTimestamp !== a._sortTimestamp) {
            return b._sortTimestamp - a._sortTimestamp;
        }
        return a._sourceIndex - b._sourceIndex;
    }

    function hasAnyKeyword(text, keywords) {
        return keywords.some((keyword) => text.includes(keyword));
    }

    function isDirectTilawah(video) {
        const title = normalizeArabic(video?.title || '');

        const tvKeywords = ['برنامج', 'تلفزيون', 'التلفزيون', 'شاشه', 'شاشة', 'النيل الثقافيه', 'النيل الثقافية', 'قناه', 'قناة', 'اذيع', 'يذاع', 'لقاء', 'مناره الازهر', 'منارة الازهر', 'منارة الأزهر'];
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

    filterButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            filterVideos(btn.dataset.filter);
        });
    });

    loadMoreBtn?.addEventListener('click', () => {
        currentPage += 1;
        renderNextBatch();
    });

    window.openTilawaVideo = (id, title) => {
        const cleanId = (id || '').toString().trim();
        modalTitle.textContent = title;
        modalIframe.src = `https://www.youtube.com/embed/${cleanId}?autoplay=1&rel=0&modestbranding=1&playsinline=1`;
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    };

    closeModal?.addEventListener('click', closeVideoModal);

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeVideoModal();
        }
    });

    function closeVideoModal() {
        modal.classList.remove('active');
        modalIframe.src = '';
        document.body.style.overflow = '';
    }
});
