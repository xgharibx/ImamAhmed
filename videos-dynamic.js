document.addEventListener('DOMContentLoaded', () => {
    // State
    let allVideos = [];
    let filteredVideos = [];
    let currentPage = 1;
    const itemsPerPage = 20;
    let currentCategory = 'all';

    // Elements
    const grid = document.getElementById('videos-grid');
    const loadMoreBtn = document.getElementById('load-more-btn');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const modal = document.getElementById('video-modal');
    const modalIframe = document.getElementById('modal-iframe');
    const modalTitle = document.getElementById('modal-title');
    const closeModal = document.querySelector('.close-modal');

    const knownCategories = new Set(['khutbah', 'lessons', 'tv', 'tafseer', 'quran', 'shorts']);

    // Fetch Data
    fetch('data/videos.json')
        .then(response => response.json())
        .then(data => {
            allVideos = (Array.isArray(data) ? data : [])
                .map((video, index) => ({
                    ...video,
                    normalizedCategory: classifyVideo(video),
                    supplementalCategories: getSupplementalCategories(video),
                    _sourceIndex: index,
                    _sortTimestamp: extractVideoTimestamp(video)
                }))
                .filter(video => video.normalizedCategory !== 'khutbah')
                .sort(sortByNewest);
            // Initial filter
            filterVideos('all');
        })
        .catch(err => {
            console.error('Error loading videos:', err);
            grid.innerHTML = '<p class="error-msg">عذراً، حدث خطأ أثناء تحميل الفيديوهات.</p>';
        });

    // Filter Logic
    function filterVideos(category) {
        currentCategory = category;
        currentPage = 1;
        
        // Update Buttons
        filterButtons.forEach(btn => {
            if(btn.dataset.filter === category) btn.classList.add('active');
            else btn.classList.remove('active');
        });

        // Filter Data
        if (category === 'all') {
            filteredVideos = allVideos;
        } else {
            filteredVideos = allVideos.filter(v =>
                v.normalizedCategory === category || (v.supplementalCategories || []).includes(category)
            );
        }

        // Render
        grid.innerHTML = ''; // Clear
        renderNextBatch();
    }

    // Render Batch
    function renderNextBatch() {
        const start = (currentPage - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const batch = filteredVideos.slice(start, end);

        if (batch.length === 0 && currentPage === 1) {
            grid.innerHTML = '<p class="no-videos">لا توجد فيديوهات في هذا القسم حالياً.</p>';
            loadMoreBtn.style.display = 'none';
            return;
        }

        batch.forEach(video => {
            const card = createVideoCard(video);
            grid.appendChild(card);
        });

        // Hndle Load More Button
        if (end >= filteredVideos.length) {
            loadMoreBtn.style.display = 'none';
        } else {
            loadMoreBtn.style.display = 'block';
        }
    }

    // Create Card DOM
    function createVideoCard(video) {
        const div = document.createElement('div');
        div.className = 'video-card aos-init aos-animate';
        div.setAttribute('data-aos', 'fade-up');
        
        // Icon mapping
        let icon = 'fa-play-circle';
        let catText = 'فيديو';
        if (video.normalizedCategory === 'khutbah') { icon = 'fa-mosque'; catText = 'خطبة جمعة'; }
        else if (video.normalizedCategory === 'quran') { icon = 'fa-quran'; catText = 'تلاوة'; }
        else if (video.normalizedCategory === 'shorts') { icon = 'fa-mobile-alt'; catText = 'شورت'; }
        else if (video.normalizedCategory === 'tafseer') { icon = 'fa-book-open'; catText = 'تفسير'; }
        else if (video.normalizedCategory === 'tv') { icon = 'fa-tv'; catText = 'لقاء تلفزيوني'; }
        else { icon = 'fa-chalkboard-teacher'; catText = 'درس'; }

        div.innerHTML = `
            <div class="video-thumbnail" onclick="openVideo('${video.id}', '${escapeHtml(video.title)}')">
                <img src="${video.thumbnail}" alt="${video.title}" loading="lazy">
                <div class="video-embed placeholder">
                    <div class="play-overlay">
                        <i class="fas fa-play-circle"></i>
                        <span>تشغيل</span>
                    </div>
                </div>
                <div class="duration-badge">${video.duration}</div>
                <span class="video-category"><i class="fas ${icon}"></i> ${catText}</span>
            </div>
            <div class="video-content">
                <h3 class="video-title" title="${video.title}">${video.title}</h3>
                <div class="video-actions">
                    <button class="btn btn-outline btn-sm" onclick="openVideo('${video.id}', '${escapeHtml(video.title)}')">
                        <i class="fas fa-play"></i> مشاهدة
                    </button>
                    <a href="https://www.youtube.com/watch?v=${video.id}" target="_blank" class="btn-yt-icon" title="فتح في يوتيوب">
                        <i class="fab fa-youtube"></i>
                    </a>
                </div>
            </div>
        `;
        return div;
    }

    // Escape Helper
    function escapeHtml(text) {
        return (text || '')
            .toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
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

    function parseDurationSeconds(rawDuration) {
        const durationText = (rawDuration || '').toString().trim();
        if (!durationText) return 0;
        const parts = durationText.split(':').map(p => Number.parseInt(p, 10));
        if (parts.some(Number.isNaN)) return 0;
        if (parts.length === 2) return (parts[0] * 60) + parts[1];
        if (parts.length === 3) return (parts[0] * 3600) + (parts[1] * 60) + parts[2];
        return 0;
    }

    function hasAnyKeyword(text, keywords) {
        return keywords.some(keyword => text.includes(keyword));
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

    function classifyVideo(video) {
        const title = normalizeArabic(video?.title || '');
        const originalCategory = (video?.category || '').toString().trim().toLowerCase();
        const durationSeconds = parseDurationSeconds(video?.duration);

        const khutbahKeywords = ['خطبه', 'خطب', 'الجمعه', 'الجمعه'];
        const tafseerKeywords = ['تفسير', 'في نور القران', 'في نور القرآن'];
        const tvKeywords = ['برنامج', 'تلفزيون', 'التلفزيون', 'شاشه', 'شاشة', 'النيل الثقافيه', 'النيل الثقافية', 'قناه', 'قناة', 'اذيع', 'يذاع', 'لقاء', 'مناره الازهر', 'منارة الازهر', 'منارة الأزهر'];
        const directQuranKeywords = ['تلاوه', 'تلاوة', 'ما تيسر', 'سوره', 'سورة', 'المصحف', 'القران الكريم', 'القرآن الكريم', 'المجود', 'المرتل'];
        const mihrabHintKeywords = ['صلاه', 'صلاة', 'فجر', 'عشاء', 'محراب', 'تراويح', 'تهجد'];
        const shortKeywords = ['short', 'شورت', '#shorts', 'ريل'];

        const isKhutbah = hasAnyKeyword(title, khutbahKeywords);
        const isTafseer = hasAnyKeyword(title, tafseerKeywords);
        const isTv = hasAnyKeyword(title, tvKeywords);
        const looksLikeDirectQuran = hasAnyKeyword(title, directQuranKeywords) || hasAnyKeyword(title, mihrabHintKeywords);
        const isShort = hasAnyKeyword(title, shortKeywords) || (durationSeconds > 0 && durationSeconds <= 180);

        if (isTv) return 'tv';
        if (isKhutbah) return 'khutbah';
        if (isTafseer) return 'tafseer';
        if (isShort && !looksLikeDirectQuran) return 'shorts';
        if (looksLikeDirectQuran && !isTv) return 'quran';
        if (knownCategories.has(originalCategory)) return originalCategory;
        return 'lessons';
    }

    function getSupplementalCategories(video) {
        const title = normalizeArabic(video?.title || '');
        const tafseerKeywords = ['تفسير', 'في نور القران', 'في نور القرآن'];
        const tvKeywords = ['برنامج', 'تلفزيون', 'التلفزيون', 'شاشه', 'شاشة', 'النيل الثقافيه', 'النيل الثقافية', 'قناه', 'قناة', 'اذيع', 'يذاع', 'لقاء', 'مناره الازهر', 'منارة الازهر', 'منارة الأزهر'];

        const isTafseer = hasAnyKeyword(title, tafseerKeywords);
        const isTv = hasAnyKeyword(title, tvKeywords);

        if (isTv && isTafseer) {
            return ['tafseer'];
        }

        return [];
    }

    // Event Listeners
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterVideos(btn.dataset.filter);
        });
    });

    loadMoreBtn.addEventListener('click', () => {
        currentPage++;
        renderNextBatch();
    });

    // Modal Global Functions
    window.openVideo = (id, title) => {
        // Clean ID just in case
        const cleanId = id.trim();
        modalTitle.textContent = title;
        // Switches back to standard youtube.com and removes 'origin' which causes 153 errors on local files/some browsers
        modalIframe.src = `https://www.youtube.com/embed/${cleanId}?autoplay=1&rel=0&modestbranding=1&playsinline=1`;
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    };

    closeModal.addEventListener('click', () => {
        closeVideoModal();
    });

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
