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

    // Fetch Data
    fetch('data/videos.json')
        .then(response => response.json())
        .then(data => {
            allVideos = data;
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
            filteredVideos = allVideos.filter(v => v.category === category);
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
        if (video.category === 'khutbah') { icon = 'fa-mosque'; catText = 'خطبة جمعة'; }
        else if (video.category === 'quran') { icon = 'fa-quran'; catText = 'تلاوة'; }
        else if (video.category === 'shorts') { icon = 'fa-mobile-alt'; catText = 'شورت'; }
        else if (video.category === 'tafseer') { icon = 'fa-book-open'; catText = 'تفسير'; }
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
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
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
