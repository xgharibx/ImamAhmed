document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const categoriesList = document.getElementById('azkar-categories');
    const categoriesTitle = document.getElementById('current-category-title');
    const container = document.getElementById('adhkar-container');
    const resetBtn = document.getElementById('reset-all-btn');
    const sidebar = document.querySelector('.azkar-sidebar');
    const mobileFab = document.getElementById('mobile-sidebar-toggle');
    
    // Create Overlay for Mobile
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);

    // State
    let allData = [];
    let currentCategory = 'morning';
    const STORE_KEY = 'azkar_progress_v1';
    let progress = loadProgress();

    // 1. Fetch Data
    fetch('data/adhkar.json')
        .then(response => response.json())
        .then(data => {
            allData = data.sections;
            init();
        })
        .catch(err => {
            console.error('Error loading Azkar data:', err);
            container.innerHTML = `<div class="error-msg">عذراً، حدث خطأ في تحميل الأذكار. يرجى تحديث الصفحة.</div>`;
        });

    // 2. Initialization
    function init() {
        renderSidebar();
        
        // Check URL hash for direct linking (e.g. #evening)
        const hash = window.location.hash.replace('#', '');
        if (hash && allData.find(s => s.id === hash)) {
            currentCategory = hash;
        }

        renderCategory(currentCategory);
        setupMobileEvents();
    }

    // 3. Render Sidebar
    function renderSidebar() {
        categoriesList.innerHTML = '';
        allData.forEach(section => {
            const li = document.createElement('li');
            li.className = `azkar-nav-item ${section.id === currentCategory ? 'active' : ''}`;
            li.dataset.target = section.id;
            li.innerHTML = `
                <span>${section.title}</span>
            `;
            
            li.addEventListener('click', () => {
                switchCategory(section.id);
                // Close sidebar on mobile if open
                closeSidebar();
            });
            
            categoriesList.appendChild(li);
        });
    }

    // 4. Switch Category
    function switchCategory(id) {
        if (currentCategory === id) return;
        currentCategory = id;
        
        // Update Sidebar Active State
        document.querySelectorAll('.azkar-nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.target === id);
        });

        // Add Hash to URL without scrolling
        history.pushState(null, null, `#${id}`);

        renderCategory(id);
    }

    // 5. Render Cards
    function renderCategory(id) {
        const sectionData = allData.find(s => s.id === id);
        if (!sectionData) return;

        categoriesTitle.innerText = sectionData.title;
        container.innerHTML = ''; // Clear current

        // Animation entry
        container.style.opacity = '0';
        
        sectionData.content.forEach((item, index) => {
            const card = createCard(item, index, id);
            container.appendChild(card);
        });

        // Fade in
        setTimeout(() => {
            container.style.opacity = '1';
        }, 100);
    }

    // 6. Create Card Logic
    function createCard(item, index, sectionId) {
        const targetCount = parseInt(item.count) || 1; 
        const currentCount = getProgress(sectionId, index);
        const isCompleted = currentCount >= targetCount;
        
        // Circular Progress Calculation
        const radius = 22;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (currentCount / targetCount) * circumference;

        const card = document.createElement('div');
        card.className = `azkar-card ${isCompleted ? 'completed' : ''}`;
        card.id = `card-${sectionId}-${index}`;

        // Benefit HTML
        let benefitHtml = '';
        if (item.benefit && item.benefit.length > 2) { 
            benefitHtml = `
                <div class="dhikr-meta">
                    <span class="meta-title">الفضل / المصدر:</span>
                    ${item.benefit}
                </div>
            `;
        }

        card.innerHTML = `
            <div class="card-content">
                <div class="dhikr-text">${item.text}</div>
                ${benefitHtml}
            </div>
            <div class="card-footer">
                <div class="counter-container">
                    <div class="counter-ring">
                        <svg width="50" height="50">
                            <circle class="progress-ring__circle-bg" stroke="#e2e8f0" stroke-width="4" fill="transparent" r="${radius}" cx="25" cy="25"/>
                            <circle class="progress-ring__circle" id="ring-${sectionId}-${index}" 
                                stroke="#D4AF37" stroke-width="4" fill="transparent" r="${radius}" cx="25" cy="25"
                                style="stroke-dasharray: ${circumference} ${circumference}; stroke-dashoffset: ${offset};"/>
                        </svg>
                        <span class="counter-text" id="display-${sectionId}-${index}" style="font-size: 1rem;">
                            ${targetCount - currentCount}
                        </span>
                    </div>
                    <button class="reset-single-btn" onclick="resetSingle('${sectionId}', ${index}, ${targetCount})" title="إعادة">
                        <i class="fas fa-redo"></i>
                    </button>
                </div>
                
                <button class="count-btn ${isCompleted ? 'completed' : ''}" onclick="incrementCount('${sectionId}', ${index}, ${targetCount})">
                    <i class="fas ${isCompleted ? 'fa-check' : 'fa-fingerprint'}"></i>
                    <span>${isCompleted ? 'اكتملت' : 'اضغط للتسبيح'}</span>
                </button>
            </div>
        `;

        // Add click listener
        card.addEventListener('click', (e) => {
            if (!e.target.closest('button')) {
                incrementCount(sectionId, index, targetCount);
            }
        });

        return card;
    }

    // 7. Global Functions
    window.incrementCount = function(sectionId, index, target) {
        let current = getProgress(sectionId, index);
        if (current >= target) return; 

        current++;
        saveProgress(sectionId, index, current);
        updateCardUI(sectionId, index, current, target);

        // Haptic Feedback
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
    };

    window.resetSingle = function(sectionId, index, target) {
        if(confirm('هل تريد تصفير العداد لهذا الذكر؟')) {
            saveProgress(sectionId, index, 0);
            updateCardUI(sectionId, index, 0, target);
        }
    };

    function updateCardUI(sectionId, index, current, target) {
        const card = document.getElementById(`card-${sectionId}-${index}`);
        const btn = card.querySelector('.count-btn');
        const display = document.getElementById(`display-${sectionId}-${index}`);
        const ring = document.getElementById(`ring-${sectionId}-${index}`);
        
        const remaining = target - current;
        display.innerText = remaining;

        // Update Ring
        const radius = 22;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (current / target) * circumference;
        ring.style.strokeDashoffset = offset;

        if (current >= target) {
            card.classList.add('completed');
            btn.classList.add('completed'); // Fixed class name to match CSS
            btn.innerHTML = `<i class="fas fa-check"></i> <span>اكتملت</span>`;
        } else {
            card.classList.remove('completed');
            btn.classList.remove('completed');
            btn.innerHTML = `<i class="fas fa-fingerprint"></i> <span>اضغط للتسبيح</span>`;
        }
    }

    // 8. Progress Management
    function loadProgress() {
        const stored = localStorage.getItem(STORE_KEY);
        return stored ? JSON.parse(stored) : {};
    }

    function saveProgress(sectionId, index, val) {
        if (!progress[sectionId]) progress[sectionId] = {};
        progress[sectionId][index] = val;
        localStorage.setItem(STORE_KEY, JSON.stringify(progress));
    }

    function getProgress(sectionId, index) {
        if (progress[sectionId] && progress[sectionId][index] !== undefined) {
            return progress[sectionId][index];
        }
        return 0;
    }

    // 9. Global Reset
    resetBtn.addEventListener('click', () => {
        if (confirm('هل أنت متأكد من تصفير العدادات لهذا القسم بالكامل؟')) {
            if (progress[currentCategory]) {
                delete progress[currentCategory];
                localStorage.setItem(STORE_KEY, JSON.stringify(progress));
                renderCategory(currentCategory); // Re-render to reset UI
            }
        }
    });

    // 10. Mobile Sidebar Logic
    function openSidebar() {
        sidebar.classList.add('active');
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    function setupMobileEvents() {
        mobileFab.addEventListener('click', openSidebar);
        overlay.addEventListener('click', closeSidebar);
    }
});
