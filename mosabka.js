document.addEventListener('DOMContentLoaded', async () => {
    if (window.AOS) {
        AOS.init({ duration: 700, once: true, offset: 40 });
    }

    const elements = {
        badge: document.getElementById('announcementBadge'),
        season: document.getElementById('resultsSeason'),
        title: document.getElementById('resultsTitle'),
        heroNote: document.getElementById('resultsHeroNote'),
        announcement: document.getElementById('resultsAnnouncement'),
        heroStatStrip: document.getElementById('heroStatStrip'),
        championCard: document.getElementById('championCard'),
        topThreeCards: document.getElementById('topThreeCards'),
        perfectScoreGrid: document.getElementById('perfectScoreGrid'),
        perfectCount: document.getElementById('perfectCount'),
        filters: document.getElementById('resultsFilters'),
        search: document.getElementById('resultsSearch'),
        grid: document.getElementById('resultsGrid'),
        socialCardsGrid: document.getElementById('socialCardsGrid'),
        videoCard: document.getElementById('resultsVideoCard'),
        galleryGrid: document.getElementById('resultsGalleryGrid'),
        sourceNote: document.getElementById('resultsSourceNote'),
        shareButton: document.getElementById('shareResultsBtn')
    };

    const relatedMedia = {
        ceremonyVideo: {
            id: '3gtIKePc7Fs',
            title: 'حفل توزيع جوائز مسابقة شهر رمضان المبارك ١٤٤٧ هجري',
            date: '14/03/2026',
            duration: '10:33',
            summary: 'التغطية الرسمية للحفل الذي شهد إعلان النتائج وتكريم الفائزين، ليرتبط سجل الأسماء بالصوت والصورة واللحظة كاملة.',
            watchUrl: 'https://youtu.be/3gtIKePc7Fs'
        },
        gallery: [
            {
                src: 'assets/mosabka-gallery/moments-01.jpg',
                title: 'لقطات من حفل التكريم',
                caption: 'افتتاح التوثيق البصري للحفل في قالب موحد ومهيأ للنشر.'
            },
            {
                src: 'assets/mosabka-gallery/moments-02.jpg',
                title: 'تكريم الفائزين',
                caption: 'مشاهد احتفاء مميزة بالفائزين وأصحاب المراكز المتقدمة.'
            },
            {
                src: 'assets/mosabka-gallery/moments-03.jpg',
                title: 'بهجة الفوز',
                caption: 'توثيق للحظات إعلان النتائج وتسليم الجوائز في أجواء مبهجة.'
            },
            {
                src: 'assets/mosabka-gallery/moments-04.jpg',
                title: 'فرحة الحضور',
                caption: 'لقطات إنسانية تعبّر عن الامتنان والوفاء للمشاركين.'
            },
            {
                src: 'assets/mosabka-gallery/moments-05.jpg',
                title: 'الذكرى الطيبة',
                caption: 'نسخة مصقولة من الصور الخام لتبقى مناسبة للأرشفة والمشاركة.'
            },
            {
                src: 'assets/mosabka-gallery/moments-06.jpg',
                title: 'مشاركات مميزة',
                caption: 'زوايا مختارة من اليوم الختامي للمسابقة المباركة.'
            },
            {
                src: 'assets/mosabka-gallery/moments-07.jpg',
                title: 'روح المسابقة',
                caption: 'معالجة لونية وإخراج بصري موحد يمنح الصور هوية أوضح.'
            },
            {
                src: 'assets/mosabka-gallery/moments-08.jpg',
                title: 'ختام الموسم',
                caption: 'الصورة الختامية لسجل النتائج والتكريم في موسم رمضان ١٤٤٧ هـ.'
            }
        ]
    };

    let config;

    try {
        const response = await fetch('data/mosabka_results_1447.json');
        config = await response.json();
    } catch (error) {
        renderLoadError(elements.grid);
        return;
    }

    const participants = Array.isArray(config.participants)
        ? [...config.participants].sort((left, right) => Number(left.rank) - Number(right.rank))
        : [];

    if (!participants.length) {
        renderLoadError(elements.grid, 'لا توجد نتائج متاحة للعرض حالياً.');
        return;
    }

    const topScore = Number(config.stats?.topScore) || Math.max(...participants.map((item) => Number(item.score) || 0));
    const perfectScoreEntries = participants.filter((item) => Number(item.score) === topScore);
    const youngestAge = Number(config.stats?.youngestAge) || Math.min(...participants.filter((item) => Number.isFinite(item.age)).map((item) => item.age));
    const totalCount = Number(config.stats?.announcedCount) || participants.length;
    const perfectScoreCount = Number(config.stats?.perfectScoreCount) || perfectScoreEntries.length;
    const state = {
        activeFilter: 'all',
        searchTerm: ''
    };

    elements.badge.innerHTML = `<i class="fas fa-award"></i>${escapeHtml(config.badge || 'إعلان النتائج المعتمدة')}`;
    elements.season.textContent = config.season || '';
    elements.title.textContent = config.title || 'النتائج النهائية لمسابقـة شهر رمضان الكبرى';
    elements.heroNote.textContent = config.heroNote || '';
    elements.announcement.textContent = config.announcement || '';
    elements.sourceNote.textContent = config.sourceNote || '';

    renderHeroStats(elements.heroStatStrip, [
        { value: totalCount, label: 'اسماً معلناً' },
        { value: perfectScoreCount, label: 'درجة كاملة' },
        { value: topScore, label: 'أعلى درجة' },
        { value: youngestAge, label: 'أصغر سن معلن' }
    ]);

    renderChampion(elements.championCard, participants[0]);
    renderTopThree(elements.topThreeCards, participants.slice(1, 3));
    renderPerfectScores(elements.perfectScoreGrid, perfectScoreEntries);
    renderSocialCards(elements.socialCardsGrid, {
        season: config.season || '',
        champion: participants[0],
        runnersUp: participants.slice(1, 3),
        perfectScoreEntries,
        topScore
    });
    renderResultsVideo(elements.videoCard, relatedMedia.ceremonyVideo);
    renderResultsGallery(elements.galleryGrid, relatedMedia.gallery);
    elements.perfectCount.textContent = `${toArabicNumber(perfectScoreCount)} متسابق`;

    const scoreFilters = ['all', ...new Set(participants.map((item) => String(item.score)))];
    renderFilters(elements.filters, scoreFilters, state.activeFilter);
    renderResultsGrid(elements.grid, participants, state);

    elements.filters.addEventListener('click', (event) => {
        const button = event.target.closest('[data-filter]');
        if (!button) return;
        state.activeFilter = button.getAttribute('data-filter') || 'all';
        renderFilters(elements.filters, scoreFilters, state.activeFilter);
        renderResultsGrid(elements.grid, participants, state);
    });

    elements.search.addEventListener('input', (event) => {
        state.searchTerm = event.target.value.trim().toLowerCase();
        renderResultsGrid(elements.grid, participants, state);
    });

    elements.shareButton.addEventListener('click', async () => {
        const pageUrl = window.location.href;

        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(pageUrl);
                elements.shareButton.innerHTML = '<i class="fas fa-check"></i> تم نسخ الرابط';
                window.setTimeout(() => {
                    elements.shareButton.innerHTML = '<i class="fas fa-share-nodes"></i> نسخ رابط النتائج';
                }, 2200);
                return;
            }
        } catch (error) {
            // Fallback handled below.
        }

        window.prompt('انسخ رابط النتائج من هنا:', pageUrl);
    });

    elements.socialCardsGrid?.addEventListener('click', async (event) => {
        const button = event.target.closest('[data-download-card]');
        if (!button) return;

        const frame = button.closest('.social-card-frame');
        const card = frame?.querySelector('.social-card');
        const fileName = button.getAttribute('data-download-card') || 'winner-card';

        if (!card) return;

        const originalLabel = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جارٍ التجهيز';

        try {
            await downloadCardImage(card, fileName);
            button.innerHTML = '<i class="fas fa-check"></i> تم التحميل';
        } catch (error) {
            button.innerHTML = '<i class="fas fa-triangle-exclamation"></i> تعذر التحميل';
        }

        window.setTimeout(() => {
            button.disabled = false;
            button.innerHTML = originalLabel;
        }, 2200);
    });

    if (window.AOS?.refreshHard) {
        window.AOS.refreshHard();
    }
});

function renderHeroStats(container, stats) {
    container.innerHTML = stats.map((item) => `
        <article class="hero-stat-card">
            <strong>${toArabicNumber(item.value)}</strong>
            <span>${escapeHtml(item.label)}</span>
        </article>
    `).join('');
}

function renderChampion(container, entry) {
    container.innerHTML = `
        <div class="champion-header">
            <div>
                <span class="champion-title">صاحب المركز الأول</span>
                <h3 class="champion-name">${escapeHtml(entry.name)}</h3>
            </div>
            <span class="champion-crown"><i class="fas fa-crown"></i></span>
        </div>
        <div class="champion-meta">
            <span class="rank-badge"><i class="fas fa-trophy"></i> المركز ${toArabicNumber(entry.rank)}</span>
            <span class="score-pill"><i class="fas fa-star"></i> ${toArabicNumber(entry.score)} / ٩٠</span>
            <span class="age-pill"><i class="fas fa-user"></i> ${formatAge(entry.age)}</span>
        </div>
        <p class="champion-note">${escapeHtml(entry.note || 'تهنئة خاصة لصاحب أفضل نتيجة في المسابقة.')}</p>
    `;
}

function renderTopThree(container, entries) {
    const labels = ['المركز الثاني', 'المركز الثالث'];

    container.innerHTML = entries.map((entry, index) => `
        <article class="top-winner-card ${index === 0 ? 'is-second' : 'is-third'}">
            <div class="winner-card-head">
                <div>
                    <span class="champion-title">${labels[index] || ''}</span>
                    <h3 class="winner-name">${escapeHtml(entry.name)}</h3>
                </div>
                <span class="winner-rank">${toArabicNumber(entry.rank)}</span>
            </div>
            <div class="winner-meta">
                <span class="score-pill"><i class="fas fa-star"></i> ${toArabicNumber(entry.score)} / ٩٠</span>
                <span class="age-pill"><i class="fas fa-user"></i> ${formatAge(entry.age)}</span>
            </div>
            <p class="winner-note">${escapeHtml(entry.note || '') || 'تهنئة مستحقة على هذا الأداء المتميز.'}</p>
        </article>
    `).join('');
}

function renderPerfectScores(container, entries) {
    container.innerHTML = entries.map((entry) => `
        <article class="perfect-score-card">
            <strong>${escapeHtml(entry.name)}</strong>
            <span>الترتيب ${toArabicNumber(entry.rank)} • ${toArabicNumber(entry.score)} / ٩٠</span>
        </article>
    `).join('');
}

function renderSocialCards(container, data) {
    if (!container) return;

    const runnersUp = Array.isArray(data.runnersUp) ? data.runnersUp : [];
    const perfectScoreEntries = Array.isArray(data.perfectScoreEntries) ? data.perfectScoreEntries : [];
    const cards = [];

    if (data.champion) {
        cards.push(`
            <article class="social-card-frame">
                <div class="social-card is-gold">
                    <div class="social-card-content">
                        <span class="social-card-kicker"><i class="fas fa-crown"></i> بطاقة تكريم</span>
                        <h3 class="social-card-title">المركز الأول</h3>
                        <p class="social-card-subtitle">النتائج النهائية لمسابقـة شهر رمضان الكبرى</p>
                        <strong class="social-card-name">${escapeHtml(data.champion.name)}</strong>
                        <div class="social-card-meta">
                            <span class="social-card-pill"><i class="fas fa-star"></i> ${toArabicNumber(data.champion.score)} / ٩٠</span>
                            <span class="social-card-pill"><i class="fas fa-user"></i> ${formatAge(data.champion.age)}</span>
                        </div>
                        <p class="social-card-note">${escapeHtml(data.champion.note || 'تهنئة خاصة لصاحب أفضل نتيجة في المسابقة.')}</p>
                        <div class="social-card-brand">
                            <div>
                                <span>الشيخ أحمد الفشني</span>
                                <small>${escapeHtml(data.season)}</small>
                            </div>
                            <span>لوحة التكريم</span>
                        </div>
                    </div>
                </div>
                <div class="social-card-actions">
                    <button type="button" class="btn btn-primary icon-only-download" data-download-card="winner-card-first-place" aria-label="تحميل بطاقة المركز الأول" title="تحميل بطاقة المركز الأول">
                        <i class="fas fa-download"></i>
                    </button>
                </div>
            </article>
        `);
    }

    runnersUp.forEach((entry, index) => {
        const ordinal = index === 0 ? 'المركز الثاني' : 'المركز الثالث';
        const themeClass = index === 0 ? 'is-light' : 'is-bronze';
        const fileName = index === 0 ? 'winner-card-second-place' : 'winner-card-third-place';

        cards.push(`
            <article class="social-card-frame">
                <div class="social-card ${themeClass}">
                    <div class="social-card-content">
                        <span class="social-card-kicker"><i class="fas fa-award"></i> بطاقة تكريم</span>
                        <h3 class="social-card-title">${ordinal}</h3>
                        <p class="social-card-subtitle">إعلان النتائج المعتمدة</p>
                        <strong class="social-card-name">${escapeHtml(entry.name)}</strong>
                        <div class="social-card-meta">
                            <span class="social-card-pill"><i class="fas fa-star"></i> ${toArabicNumber(entry.score)} / ٩٠</span>
                            <span class="social-card-pill"><i class="fas fa-user"></i> ${formatAge(entry.age)}</span>
                        </div>
                        <p class="social-card-note">${escapeHtml(entry.note || 'تهنئة مستحقة على هذا الأداء المتميز.')}</p>
                        <div class="social-card-brand">
                            <div>
                                <span>الشيخ أحمد الفشني</span>
                                <small>${escapeHtml(data.season)}</small>
                            </div>
                            <span>بطاقة تكريم</span>
                        </div>
                    </div>
                </div>
                <div class="social-card-actions">
                    <button type="button" class="btn btn-primary icon-only-download" data-download-card="${fileName}" aria-label="تحميل ${ordinal}" title="تحميل ${ordinal}">
                        <i class="fas fa-download"></i>
                    </button>
                </div>
            </article>
        `);
    });

    if (perfectScoreEntries.length) {
        cards.push(`
            <article class="social-card-frame">
                <div class="social-card is-emerald">
                    <div class="social-card-content">
                        <span class="social-card-kicker"><i class="fas fa-stars"></i> بطاقة جماعية</span>
                        <span class="social-card-badge"><i class="fas fa-medal"></i> أصحاب الدرجة الكاملة</span>
                        <h3 class="social-card-title">كامل العلامة النهائية</h3>
                        <p class="social-card-subtitle">${toArabicNumber(perfectScoreEntries.length)} متسابقاً حققوا أعلى درجة في النتائج المعتمدة</p>
                        <div class="social-card-list">
                            ${perfectScoreEntries.map((entry) => `
                                <div class="social-card-list-item">
                                    <strong>${escapeHtml(entry.name)}</strong>
                                    <span>${toArabicNumber(entry.rank)} / ${toArabicNumber(data.topScore)}</span>
                                </div>
                            `).join('')}
                        </div>
                        <div class="social-card-brand">
                            <div>
                                <span>الشيخ أحمد الفشني</span>
                                <small>${escapeHtml(data.season)}</small>
                            </div>
                            <span>إعلان التكريم</span>
                        </div>
                    </div>
                </div>
                <div class="social-card-actions">
                    <button type="button" class="btn btn-primary icon-only-download" data-download-card="winner-card-perfect-scores" aria-label="تحميل بطاقة أصحاب الدرجة الكاملة" title="تحميل بطاقة أصحاب الدرجة الكاملة">
                        <i class="fas fa-download"></i>
                    </button>
                </div>
            </article>
        `);
    }

    container.innerHTML = cards.join('');
}

function renderFilters(container, filters, activeFilter) {
    container.innerHTML = filters.map((filterValue) => {
        const isAll = filterValue === 'all';
        const label = isAll ? 'الكل' : `${toArabicNumber(filterValue)} درجة`;
        const className = filterValue === activeFilter ? 'results-filter is-active' : 'results-filter';

        return `<button type="button" class="${className}" data-filter="${escapeHtml(filterValue)}">${escapeHtml(label)}</button>`;
    }).join('');
}

function renderResultsVideo(container, video) {
    if (!container || !video) return;

    const embedUrl = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(video.id)}?rel=0`;

    container.innerHTML = `
        <div class="results-video-frame">
            <iframe
                src="${embedUrl}"
                title="${escapeHtml(video.title)}"
                loading="lazy"
                referrerpolicy="strict-origin-when-cross-origin"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen>
            </iframe>
        </div>
        <div class="results-video-copy">
            <span class="results-video-kicker"><i class="fas fa-circle-play"></i> فيديو الحفل الرسمي</span>
            <h3>${escapeHtml(video.title)}</h3>
            <div class="results-video-meta">
                <span class="social-card-pill"><i class="fas fa-calendar-days"></i> ${escapeHtml(video.date)}</span>
                <span class="social-card-pill"><i class="fas fa-clock"></i> ${escapeHtml(video.duration)}</span>
            </div>
            <p>${escapeHtml(video.summary)}</p>
            <div class="results-video-actions">
                <a href="${escapeHtml(video.watchUrl)}" class="btn btn-primary" target="_blank" rel="noopener noreferrer">
                    <i class="fab fa-youtube"></i>
                    مشاهدة على يوتيوب
                </a>
                <a href="videos.html" class="btn btn-secondary">
                    <i class="fas fa-film"></i>
                    تصفح بقية الفيديوهات
                </a>
            </div>
        </div>
    `;
}

function renderResultsGallery(container, images) {
    if (!container || !Array.isArray(images)) return;

    container.innerHTML = images.map((image, index) => `
        <a class="results-gallery-card" href="${escapeHtml(image.src)}" target="_blank" rel="noopener noreferrer" aria-label="عرض ${escapeHtml(image.title)} بالحجم الكامل">
            <span class="gallery-seq">${toArabicNumber(index + 1)}</span>
            <img src="${escapeHtml(image.src)}" alt="${escapeHtml(image.title)}" loading="lazy">
            <span class="gallery-overlay">
                <strong>${escapeHtml(image.title)}</strong>
                <small>${escapeHtml(image.caption)}</small>
            </span>
        </a>
    `).join('');
}

function renderResultsGrid(container, participants, state) {
    const filtered = participants.filter((entry) => {
        const passesScore = state.activeFilter === 'all' || String(entry.score) === state.activeFilter;
        const passesSearch = !state.searchTerm || String(entry.name || '').toLowerCase().includes(state.searchTerm);
        return passesScore && passesSearch;
    });

    if (!filtered.length) {
        container.innerHTML = '<div class="result-empty">لا توجد نتيجة مطابقة لخيارات البحث الحالية.</div>';
        return;
    }

    container.innerHTML = filtered.map((entry) => {
        const topThreeClass = Number(entry.rank) <= 3 ? 'result-card is-top-three' : 'result-card';

        return `
            <article class="${topThreeClass}">
                <div class="result-card-head">
                    <div>
                        <strong class="result-name">${escapeHtml(entry.name)}</strong>
                        <div class="result-meta">
                            <span class="score-pill"><i class="fas fa-star"></i> ${toArabicNumber(entry.score)} / ٩٠</span>
                            <span class="age-pill"><i class="fas fa-user"></i> ${formatAge(entry.age)}</span>
                        </div>
                    </div>
                    <span class="result-rank">${toArabicNumber(entry.rank)}</span>
                </div>
                <p class="result-note">${escapeHtml(entry.note || 'لا توجد ملاحظة إضافية مذكورة في المستند.')}</p>
            </article>
        `;
    }).join('');
}

function renderLoadError(container, message = 'تعذر تحميل النتائج حالياً.') {
    if (!container) return;
    container.innerHTML = `<div class="result-empty">${escapeHtml(message)}</div>`;
}

async function downloadCardImage(card, fileName) {
    if (!window.html2canvas) {
        throw new Error('html2canvas is unavailable');
    }

    const canvas = await window.html2canvas(card, {
        backgroundColor: null,
        scale: Math.min(window.devicePixelRatio || 2, 3),
        useCORS: true,
        logging: false
    });

    const link = document.createElement('a');
    link.download = `${fileName}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
}

function formatAge(age) {
    const numericAge = Number(age);
    if (!Number.isFinite(numericAge) || numericAge <= 0) {
        return 'السن غير مذكور';
    }

    return `${toArabicNumber(numericAge)} سنة`;
}

function toArabicNumber(value) {
    return new Intl.NumberFormat('ar-EG').format(value);
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
