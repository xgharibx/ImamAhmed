document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('khutab-video-grid');
    const loadMoreBtn = document.getElementById('khutab-video-load-more');
    const modal = document.getElementById('video-modal');
    const modalIframe = document.getElementById('modal-iframe');
    const modalTitle = document.getElementById('modal-title');
    const closeModal = document.querySelector('.close-modal');

    let khutbahVideos = [];
    let currentPage = 1;
    const itemsPerPage = 20;

    fetch('data/videos.json')
        .then((response) => response.json())
        .then((data) => {
            const allVideos = Array.isArray(data) ? data : [];
            khutbahVideos = allVideos
                .map((video, index) => ({
                    ...video,
                    normalizedCategory: classifyVideo(video),
                    _sourceIndex: index,
                    _sortTimestamp: extractVideoTimestamp(video)
                }))
                .filter((video) => video.normalizedCategory === 'khutbah')
                .sort(sortByNewest);

            grid.innerHTML = '';
            renderNextBatch();
        })
        .catch((error) => {
            console.error('Error loading khutbah videos:', error);
            grid.innerHTML = '<p class="error-msg">عذراً، حدث خطأ أثناء تحميل الخطب المرئية.</p>';
        });

    loadMoreBtn?.addEventListener('click', () => {
        currentPage += 1;
        renderNextBatch();
    });

    function renderNextBatch() {
        const start = (currentPage - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const batch = khutbahVideos.slice(start, end);

        if (batch.length === 0 && currentPage === 1) {
            grid.innerHTML = '<p class="no-videos">لا توجد خطب مرئية متاحة حالياً.</p>';
            loadMoreBtn.style.display = 'none';
            return;
        }

        batch.forEach((video) => {
            grid.appendChild(createVideoCard(video));
        });

        if (end >= khutbahVideos.length) {
            loadMoreBtn.style.display = 'none';
        } else {
            loadMoreBtn.style.display = 'block';
        }
    }

    function createVideoCard(video) {
        const div = document.createElement('div');
        div.className = 'video-card aos-init aos-animate';
        div.setAttribute('data-aos', 'fade-up');

        const title = escapeHtml(video?.title || 'خطبة جمعة');
        const videoId = (video?.id || '').toString().trim();
        const thumbnail = escapeHtml(video?.thumbnail || `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`);
        const duration = escapeHtml(video?.duration || '--:--');

        div.innerHTML = `
            <div class="video-thumbnail" onclick="openKhutabVideo('${videoId}', '${title}')">
                <img src="${thumbnail}" alt="${title}" loading="lazy">
                <div class="video-embed placeholder">
                    <div class="play-overlay">
                        <i class="fas fa-play-circle"></i>
                        <span>تشغيل</span>
                    </div>
                </div>
                <div class="duration-badge">${duration}</div>
                <span class="video-category"><i class="fas fa-mosque"></i> خطبة جمعة</span>
            </div>
            <div class="video-content">
                <h3 class="video-title" title="${title}">${title}</h3>
                <div class="video-actions">
                    <button class="btn btn-outline btn-sm" onclick="openKhutabVideo('${videoId}', '${title}')">
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

    function escapeHtml(text) {
        return (text || '')
            .toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
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

    function classifyVideo(video) {
        const title = normalizeArabic(video?.title || '');
        const khutbahKeywords = ['خطبه', 'خطب', 'الجمعه'];
        return hasAnyKeyword(title, khutbahKeywords) ? 'khutbah' : 'other';
    }

    window.openKhutabVideo = (id, title) => {
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
