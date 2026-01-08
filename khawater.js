/* =====================================================
   الشيخ أحمد إسماعيل الفشني - Khawater Page Scripts
   ===================================================== */

document.addEventListener('DOMContentLoaded', () => {
    initKhawaterFilter();
    initKhawaterSearch();
    initShareButtons();
    initLoadMore();
});

/* ============== Filter Functionality ============== */
function initKhawaterFilter() {
    const filterTags = document.querySelectorAll('.filter-tag');
    const cards = document.querySelectorAll('.khatera-card');
    
    filterTags.forEach(tag => {
        tag.addEventListener('click', () => {
            // Update active state
            filterTags.forEach(t => t.classList.remove('active'));
            tag.classList.add('active');
            
            const filter = tag.dataset.filter;
            
            cards.forEach(card => {
                const categories = card.dataset.category || '';
                
                if (filter === 'all' || categories.includes(filter)) {
                    card.style.display = 'block';
                    card.style.animation = 'fadeIn 0.5s ease forwards';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });
}

/* ============== Search Functionality ============== */
function initKhawaterSearch() {
    const searchInput = document.getElementById('khawaterSearch');
    const cards = document.querySelectorAll('.khatera-card');
    
    if (!searchInput) return;
    
    let debounceTimer;
    
    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        
        debounceTimer = setTimeout(() => {
            const searchTerm = e.target.value.trim().toLowerCase();
            
            cards.forEach(card => {
                const text = card.querySelector('.khatera-text').textContent.toLowerCase();
                
                if (searchTerm === '' || text.includes(searchTerm)) {
                    card.style.display = 'block';
                    card.style.animation = 'fadeIn 0.5s ease forwards';
                    
                    // Highlight search term
                    if (searchTerm !== '') {
                        highlightText(card.querySelector('.khatera-text'), searchTerm);
                    } else {
                        removeHighlight(card.querySelector('.khatera-text'));
                    }
                } else {
                    card.style.display = 'none';
                }
            });
            
            // Reset filter buttons
            document.querySelectorAll('.filter-tag').forEach(tag => {
                tag.classList.remove('active');
            });
            document.querySelector('.filter-tag[data-filter="all"]')?.classList.add('active');
        }, 300);
    });
}

function highlightText(element, searchTerm) {
    const originalText = element.getAttribute('data-original-text') || element.textContent;
    element.setAttribute('data-original-text', originalText);
    
    const regex = new RegExp(`(${escapeRegex(searchTerm)})`, 'gi');
    element.innerHTML = originalText.replace(regex, '<mark class="highlight">$1</mark>');
}

function removeHighlight(element) {
    const originalText = element.getAttribute('data-original-text');
    if (originalText) {
        element.textContent = originalText;
    }
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/* ============== Share Buttons ============== */
function initShareButtons() {
    const shareButtons = document.querySelectorAll('.share-btn');
    
    shareButtons.forEach(btn => {
        btn.addEventListener('click', async () => {
            const card = btn.closest('.khatera-card');
            const text = card.querySelector('.khatera-text').textContent;
            const shareData = {
                title: 'خاطرة - الشيخ أحمد الفشني',
                text: text.substring(0, 200) + '...',
                url: window.location.href
            };
            
            if (navigator.share) {
                try {
                    await navigator.share(shareData);
                } catch (err) {
                    if (err.name !== 'AbortError') {
                        copyToClipboard(text);
                    }
                }
            } else {
                copyToClipboard(text);
            }
        });
    });
}

function copyToClipboard(text) {
    const fullText = `${text}\n\n— الشيخ أحمد إسماعيل الفشني\n${window.location.href}`;
    
    navigator.clipboard.writeText(fullText).then(() => {
        showNotification('تم نسخ الخاطرة!');
    }).catch(() => {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = fullText;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showNotification('تم نسخ الخاطرة!');
    });
}

function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'copy-notification';
    notification.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
    notification.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: var(--primary-green);
        color: white;
        padding: 1rem 2rem;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-lg);
        z-index: 9999;
        animation: slideInUp 0.3s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-family: var(--font-primary);
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'fadeOut 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    }, 2000);
}

/* ============== Load More ============== */
function initLoadMore() {
    const loadMoreBtn = document.getElementById('loadMoreBtn');
    if (!loadMoreBtn) return;
    
    // Additional khawater data that can be loaded
    const additionalKhawater = [
        {
            number: '٢١',
            text: 'الصدق منجاة، والكذب مهلكة. فكن صادقاً في كل أحوالك، فإن الصدق يهدي إلى البر، والبر يهدي إلى الجنة.',
            category: 'wisdom tazkiya'
        },
        {
            number: '٢٢',
            text: 'بر الوالدين من أعظم القربات إلى الله، فمن أراد السعادة في الدارين فليبر والديه وليحسن إليهما.',
            category: 'faith wisdom'
        },
        {
            number: '٢٣',
            text: 'صلة الرحم تزيد في العمر وتبارك في الرزق، فصل أرحامك ولو قطعوك، وأحسن إليهم ولو أساؤوا إليك.',
            category: 'tazkiya'
        },
        {
            number: '٢٤',
            text: 'العفو من شيم الكرام، فكن عفواً صفوحاً، واعلم أن من عفا وأصلح فأجره على الله.',
            category: 'wisdom'
        },
        {
            number: '٢٥',
            text: 'الدعاء سلاح المؤمن، فأكثر منه في السراء والضراء، ولا تستعجل الإجابة، فإن الله يستجيب لعبده ما لم يدع بإثم أو قطيعة رحم.',
            category: 'faith'
        }
    ];
    
    let loaded = false;
    
    loadMoreBtn.addEventListener('click', () => {
        if (loaded) {
            showNotification('لا توجد خواطر إضافية حالياً');
            return;
        }
        
        const grid = document.getElementById('khawaterGrid');
        const originalText = loadMoreBtn.innerHTML;
        
        // Show loading
        loadMoreBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري التحميل...';
        loadMoreBtn.disabled = true;
        
        setTimeout(() => {
            additionalKhawater.forEach((khatera, index) => {
                const card = createKhateraCard(khatera, index);
                grid.appendChild(card);
                
                // Trigger AOS animation
                setTimeout(() => {
                    card.classList.add('aos-animate');
                }, index * 100);
            });
            
            loadMoreBtn.innerHTML = '<i class="fas fa-check"></i> تم تحميل الكل';
            loaded = true;
            
            // Re-initialize share buttons for new cards
            initShareButtons();
            
        }, 1000);
    });
}

function createKhateraCard(khatera, delay) {
    const card = document.createElement('article');
    card.className = 'khatera-card';
    card.setAttribute('data-aos', 'fade-up');
    card.setAttribute('data-aos-delay', delay * 100);
    card.setAttribute('data-category', khatera.category);
    
    const categoryLabel = getCategoryLabel(khatera.category.split(' ')[0]);
    
    card.innerHTML = `
        <div class="card-number">${khatera.number}</div>
        <div class="card-decoration">
            <span class="quote-mark">❝</span>
        </div>
        <div class="card-content">
            <p class="khatera-text">${khatera.text}</p>
        </div>
        <div class="card-footer">
            <span class="card-tag"><i class="fas fa-tag"></i> ${categoryLabel}</span>
            <button class="share-btn" title="مشاركة"><i class="fas fa-share-alt"></i></button>
        </div>
    `;
    
    return card;
}

function getCategoryLabel(category) {
    const labels = {
        'success': 'النجاح',
        'tazkiya': 'التزكية',
        'faith': 'الإيمان',
        'wisdom': 'حكمة'
    };
    return labels[category] || 'خاطرة';
}

// Add fadeOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(20px); }
    }
    
    .highlight {
        background: rgba(201, 162, 39, 0.3);
        padding: 0 0.2rem;
        border-radius: 3px;
    }
`;
document.head.appendChild(style);
