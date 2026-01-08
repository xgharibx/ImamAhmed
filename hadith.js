/*!
 * Hadith Section - Complete Integration with Sunnah.com
 * All major hadith collections with full content
 */

const API_BASE = 'https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1';

// Full Sunnah.com set in Arabic editions
const books = [
    // API-backed (hadith-api)
    { id: 'bukhari', name: 'صحيح البخاري', icon: 'fa-book-quran', edition: 'ara-bukhari', available: true },
    { id: 'muslim', name: 'صحيح مسلم', icon: 'fa-book-open', edition: 'ara-muslim', available: true },
    { id: 'abudawud', name: 'سنن أبي داود', icon: 'fa-scroll', edition: 'ara-abudawud', available: true },
    { id: 'tirmidhi', name: 'جامع الترمذي', icon: 'fa-book', edition: 'ara-tirmidhi', available: true },
    { id: 'nasai', name: 'سنن النسائي', icon: 'fa-bookmark', edition: 'ara-nasai', available: true },
    { id: 'ibnmajah', name: 'سنن ابن ماجه', icon: 'fa-file-alt', edition: 'ara-ibnmajah', available: true },
    { id: 'malik', name: 'موطأ مالك', icon: 'fa-star-and-crescent', edition: 'ara-malik', available: true },
    { id: 'nawawi', name: 'الأربعون النووية', icon: 'fa-list-ol', edition: 'ara-nawawi', available: true },
    // Local data-backed (scraped from sunnah.com)
    { id: 'ahmad', name: 'مسند الإمام أحمد', icon: 'fa-mosque', edition: 'local:ahmad', available: true },
    { id: 'darimi', name: 'سنن الدارمي', icon: 'fa-book-atlas', edition: 'local:darimi', available: true },
    { id: 'riyadussaliheen', name: 'رياض الصالحين', icon: 'fa-seedling', edition: 'local:riyadussaliheen', available: true },
    { id: 'adab', name: 'الأدب المفرد', icon: 'fa-pen-fancy', edition: 'local:adab', available: true },
    { id: 'shamail', name: 'الشمائل المحمدية', icon: 'fa-star', edition: 'local:shamail', available: true },
    { id: 'mishkat', name: 'مشكاة المصابيح', icon: 'fa-lightbulb', edition: 'local:mishkat', available: true },
    { id: 'bulugh', name: 'بلوغ المرام', icon: 'fa-check-double', edition: 'local:bulugh', available: true },
    { id: 'hisn', name: 'حصن المسلم', icon: 'fa-shield', edition: 'local:hisn', available: true }
];

// Cache for API responses (per edition)
const cache = {};

function toArabicDigits(value) {
    try {
        const map = ['٠','١','٢','٣','٤','٥','٦','٧','٨','٩'];
        return String(value).replace(/[0-9]/g, d => map[parseInt(d, 10)]);
    } catch {
        return value;
    }
}

// DOM Elements
let booksSection, chaptersSection, hadithSection;
let booksGrid, chaptersList, hadithContainer;
let loadingSpinner, currentBookTitle, currentChapterTitle;

// State
let currentBook = null;
let currentChapter = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Get DOM elements
        booksSection = document.getElementById('books-section');
        chaptersSection = document.getElementById('chapters-section');
        hadithSection = document.getElementById('hadith-display-section');
        booksGrid = document.getElementById('books-grid');
        chaptersList = document.getElementById('chapters-list');
        hadithContainer = document.getElementById('hadith-container');
        loadingSpinner = document.getElementById('loading-spinner');
        currentBookTitle = document.getElementById('current-book-title');
        currentChapterTitle = document.getElementById('current-chapter-title');

        if (!booksGrid) {
            console.error('Required DOM elements not found');
            return;
        }

        // Render books
        renderBooks();
        
        console.log('Hadith section initialized successfully');
    } catch (error) {
        console.error('Error initializing hadith section:', error);
    }
});

function renderBooks() {
    if (!booksGrid) return;
    
    try {
        booksGrid.innerHTML = books.map(book => {
            const disabled = book.available ? '' : 'book-card-disabled';
            const click = book.available ? `window.loadChapters('${book.id}', '${escapeHtml(book.name)}', '${book.edition}')` : `window.showUnavailable('${escapeHtml(book.name)}')`;
            const info = book.available ? 'اضغط للتصفح' : 'غير متوفر حالياً';
            return `
                <div class="book-card ${disabled}" onclick="${click}" data-aos="fade-up">
                    <div class="book-icon">
                        <i class="fas ${book.icon}"></i>
                    </div>
                    <h3 class="book-title">${book.name}</h3>
                    <p class="book-info">${info}</p>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error rendering books:', error);
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadBookData(edition) {
    if (cache[edition]?.sections && cache[edition]?.hadiths) {
        return cache[edition];
    }
    // Local data source handling (scraped JSON in data/<id>.json)
    if (edition && edition.startsWith('local:')) {
        const localId = edition.split(':')[1];
        const localUrl = `data/${localId}.json`;
        let json;
        try {
            const res = await fetch(localUrl);
            if (!res.ok) throw new Error('Failed local JSON');
            json = await res.json();
        } catch (e) {
            throw new Error(`تعذر تحميل بيانات ${localId} من الملفات المحلية`);
        }

        const chapters = Array.isArray(json.chapters) ? json.chapters : [];
        const sections = chapters.map(ch => ({
            id: `${ch.id ?? ''}`,
            name: toArabicDigits((ch.name || `الفصل ${ch.id}`).toString().trim())
        })).filter(s => s.id && s.name);

        // Flatten hadiths with a standard shape compatible with renderer
        const hadiths = [];
        chapters.forEach(ch => {
            const list = Array.isArray(ch.hadiths) ? ch.hadiths : [];
            list.forEach((h, idx) => {
                hadiths.push({
                    text: h.text || h.hadith || '',
                    hadith: h.text || h.hadith || '',
                    hadithnumber: idx + 1,
                    reference: { book: `${ch.id ?? ''}` },
                    grades: h.grades || []
                });
            });
        });

        cache[edition] = { sections, hadiths };
        return cache[edition];
    }
    // Try multiple sources for better reliability
    const sources = [
        `${API_BASE}/editions/${edition}.json`,
        `https://raw.githubusercontent.com/fawazahmed0/hadith-api/1/editions/${edition}.json`
    ];

    let data = null;
    for (const url of sources) {
        try {
            const response = await fetch(url);
            if (!response.ok) continue;
            data = await response.json();
            break;
        } catch {
            continue;
        }
    }

    if (!data) {
        throw new Error(`تعذر تحميل بيانات ${edition}`);
    }

    const sectionsMap = data.metadata?.sections || data.metadata?.sections_ar || {};
    let sectionEntries = Object.entries(sectionsMap);

    // If the API doesn’t provide sections, synthesize from hadith references
    if (sectionEntries.length === 0 && Array.isArray(data.hadiths)) {
        const grouped = new Map();
        data.hadiths.forEach(h => {
            const ref = h.reference?.book;
            const id = ref !== undefined ? `${ref}` : '1';
            grouped.set(id, grouped.get(id) || `كتاب رقم ${id}`);
        });
        sectionEntries = Array.from(grouped.entries());
    }

    const sections = sectionEntries
        .map(([id, name]) => ({
            id,
            name: toArabicDigits((name || `الفصل ${id}`).trim())
        }))
        .filter(section => section.id !== '0' && section.name)
        .sort((a, b) => {
            const aNum = parseInt(a.id, 10);
            const bNum = parseInt(b.id, 10);
            if (!isNaN(aNum) && !isNaN(bNum)) return aNum - bNum;
            return a.id.localeCompare(b.id);
        });

    cache[edition] = {
        sections,
        hadiths: data.hadiths || []
    };

    return cache[edition];
}

// Load chapters for a book
window.loadChapters = async function(bookId, bookName, edition) {
    const book = books.find(b => b.id === bookId);
    if (!book?.available || !edition) {
        showUnavailable(bookName);
        return;
    }
    showLoading();
    currentBook = { id: bookId, name: bookName, edition: edition };
    
    try {
        const data = await loadBookData(edition);
        displayChapters(data.sections);
    } catch (error) {
        console.error('Error loading chapters:', error);
        showError(`حدث خطأ أثناء تحميل الفصول للكتاب ${bookName}. يرجى التحقق من الاتصال أو المحاولة لاحقاً.`);
        showBooks();
    } finally {
        hideLoading();
    }
};

function displayChapters(chapters) {
    if (!chaptersSection || !chaptersList || !currentBookTitle) return;
    
    try {
        booksSection.style.display = 'none';
        hadithSection.style.display = 'none';
        chaptersSection.style.display = 'block';
        
        currentBookTitle.textContent = currentBook.name;
        
        chaptersList.innerHTML = chapters.map(chapter => {
            const escapedName = escapeHtml(chapter.name);
            return `
                <div class="chapter-item" onclick="window.loadHadiths('${chapter.id}', \`${escapedName}\`)" data-aos="fade-up">
                    <div class="chapter-number">${toArabicDigits(chapter.id)}</div>
                    <div class="chapter-name">${chapter.name}</div>
                </div>
            `;
        }).join('');
        
        if (window.AOS) {
            setTimeout(() => AOS.refresh(), 100);
        }
        
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
        console.error('Error displaying chapters:', error);
    }
}

// Load hadiths for a chapter
window.loadHadiths = async function(sectionId, sectionName) {
    showLoading();
    currentChapter = { id: sectionId, name: sectionName };
    
    try {
        const cached = cache[currentBook?.edition] || await loadBookData(currentBook?.edition);
        const hadiths = (cached.hadiths || []).filter(h => {
            const bookRef = h.reference?.book;
            return bookRef !== undefined && `${bookRef}` === `${sectionId}`;
        });

        displayHadiths(hadiths);
    } catch (error) {
        console.error('Error loading hadiths:', error);
        showError('حدث خطأ أثناء تحميل الأحاديث. يرجى المحاولة مرة أخرى أو اختيار فصل آخر.');
        showChapters();
    } finally {
        hideLoading();
    }
};

// Global search across all books
async function searchHadiths(query) {
    const normalized = query.trim();
    if (normalized.length < 2) {
        renderSearchResults([], 'اكتب كلمتين على الأقل للبحث.');
        return;
    }

    showLoading();
    try {
        // Load all books into cache if missing
        for (const book of books.filter(b => b.available)) {
            if (!cache[book.edition]) {
                try {
                    await loadBookData(book.edition);
                } catch (e) {
                    console.warn('Skip book in search due to load failure', book.edition, e);
                    continue;
                }
            }
        }

        const q = normalized.toLowerCase();
        const results = [];

        books.filter(b => b.available).forEach(book => {
            const data = cache[book.edition];
            if (!data) return;

            data.hadiths.forEach(h => {
                const text = (h.hadith || h.text || '').toLowerCase();
                if (text.includes(q)) {
                    const chapterId = `${h.reference?.book ?? ''}`;
                    const chapterName = data.sections.find(s => `${s.id}` === chapterId)?.name || `الفصل ${chapterId}`;
                    results.push({
                        bookName: book.name,
                        chapterName,
                        hadithNumber: h.hadithnumber || h.arabicnumber || '',
                        text: h.hadith || h.text || ''
                    });
                }
            });
        });

        renderSearchResults(results);
    } catch (error) {
        console.error('Error searching hadiths:', error);
        renderSearchResults([], 'حدث خطأ أثناء البحث. حاول مرة أخرى.');
    } finally {
        hideLoading();
    }
}

function renderSearchResults(results, statusMessage = '') {
    const statusEl = document.getElementById('search-status');
    const listEl = document.getElementById('search-results');
    if (!statusEl || !listEl) return;

    if (statusMessage) {
        statusEl.textContent = statusMessage;
    } else if (results.length === 0) {
        statusEl.textContent = 'لم يتم العثور على نتائج.';
    } else {
        statusEl.textContent = `تم العثور على ${toArabicDigits(results.length)} نتيجة.`;
    }

    if (!results.length) {
        listEl.innerHTML = '';
        return;
    }

    const limited = results.slice(0, 100); // cap to keep UI responsive
    listEl.innerHTML = limited.map(r => {
        const safeText = escapeHtml(r.text);
        const safeBook = escapeHtml(r.bookName);
        const safeChapter = escapeHtml(r.chapterName);
        const num = r.hadithNumber ? toArabicDigits(r.hadithNumber) : '';
        return `
            <div class="hadith-card" data-aos="fade-up">
                <div class="hadith-header">
                    <span class="hadith-number"><strong>${safeBook}</strong> — ${safeChapter} ${num ? ' | الحديث ' + num : ''}</span>
                </div>
                <div class="hadith-text">${safeText}</div>
            </div>
        `;
    }).join('');

    if (results.length > limited.length) {
        const more = document.createElement('div');
        more.className = 'no-hadiths';
        more.textContent = `تم إظهار أول ${toArabicDigits(limited.length)} من ${toArabicDigits(results.length)} نتيجة.`;
        listEl.appendChild(more);
    }
}

function displayHadiths(hadiths) {
    if (!hadithSection || !hadithContainer || !currentChapterTitle) return;
    
    try {
        chaptersSection.style.display = 'none';
        hadithSection.style.display = 'block';
        
        currentChapterTitle.textContent = `${currentBook.name} - ${currentChapter.name}`;
        
        if (!hadiths || hadiths.length === 0) {
            hadithContainer.innerHTML = '<div class="no-hadiths">لا توجد أحاديث في هذا الفصل</div>';
        } else {
            hadithContainer.innerHTML = hadiths.map((hadith, index) => {
                const hadithText = hadith.hadith || hadith.text || 'لا يوجد نص';
                const hadithNumber = hadith.hadithnumber || (index + 1);
                
                return `
                    <div class="hadith-card" data-aos="fade-up">
                        <div class="hadith-header">
                            <span class="hadith-number">
                                <strong>الحديث رقم:</strong> ${hadithNumber}
                            </span>
                        </div>
                        <div class="hadith-text">${hadithText}</div>
                        ${hadith.grades && hadith.grades.length > 0 ? `
                            <div class="hadith-footer">
                                <div class="hadith-grade">
                                    <strong>التصحيح:</strong> ${hadith.grades[0].grade || 'غير محدد'}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('');
        }
        
        if (window.AOS) {
            setTimeout(() => AOS.refresh(), 100);
        }
        
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
        console.error('Error displaying hadiths:', error);
    }
}

// Navigation functions
window.showBooks = function() {
    if (!booksSection || !chaptersSection || !hadithSection) return;
    
    chaptersSection.style.display = 'none';
    hadithSection.style.display = 'none';
    booksSection.style.display = 'block';
    currentBook = null;
    window.scrollTo({ top: 0, behavior: 'smooth' });
};

window.showChapters = function() {
    if (!chaptersSection || !hadithSection) return;
    
    hadithSection.style.display = 'none';
    chaptersSection.style.display = 'block';
    currentChapter = null;
    window.scrollTo({ top: 0, behavior: 'smooth' });
};

// UI Helpers
function showLoading() {
    if (loadingSpinner) {
        loadingSpinner.style.display = 'block';
    }
}

function hideLoading() {
    if (loadingSpinner) {
        loadingSpinner.style.display = 'none';
    }
}

function showError(message) {
    // Create a styled error notification
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
        color: white;
        padding: 25px 40px;
        border-radius: 12px;
        z-index: 9999;
        text-align: center;
        font-family: 'Cairo', sans-serif;
        font-size: 1.1rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        max-width: 90%;
        animation: slideIn 0.3s ease-out;
    `;
    errorDiv.textContent = message;
    document.body.appendChild(errorDiv);
    
    setTimeout(() => {
        errorDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => errorDiv.remove(), 300);
    }, 4000);
}

// Notify when a book is displayed but not yet available in the API
window.showUnavailable = function(bookName) {
    showError(`المجموعة ${bookName} غير متوفرة حالياً. سنضيفها عند توفر البيانات.`);
};

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translate(-50%, -60%);
            opacity: 0;
        }
        to {
            transform: translate(-50%, -50%);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translate(-50%, -50%);
            opacity: 1;
        }
        to {
            transform: translate(-50%, -40%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

console.log('Hadith.js loaded successfully');

// Hook up search form after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('hadith-search-form');
    const searchInput = document.getElementById('hadith-search-input');
    if (searchForm && searchInput) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            searchHadiths(searchInput.value);
        });
    }
});
