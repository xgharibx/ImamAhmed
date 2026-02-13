const quranState = {
  data: null,
  pageMapMeta: null,
  currentSurah: null,
  mushafPages: [],
  totalMushafPages: 0,
  currentMushafPage: 1,
  bookmarkedPages: new Set(),
  bookmarkedAyahs: new Set()
};

const PAGE_BOOKMARKS_KEY = 'quran_page_bookmarks';
const AYAH_BOOKMARKS_KEY = 'quran_ayah_bookmarks';

function ayahBookmarkKey(surahId, ayahNumber) {
  return `${surahId}:${ayahNumber}`;
}

function saveBookmarks() {
  localStorage.setItem(PAGE_BOOKMARKS_KEY, JSON.stringify([...quranState.bookmarkedPages]));
  localStorage.setItem(AYAH_BOOKMARKS_KEY, JSON.stringify([...quranState.bookmarkedAyahs]));
}

function loadBookmarks() {
  try {
    const pageRaw = JSON.parse(localStorage.getItem(PAGE_BOOKMARKS_KEY) || '[]');
    const ayahRaw = JSON.parse(localStorage.getItem(AYAH_BOOKMARKS_KEY) || '[]');
    quranState.bookmarkedPages = new Set(Array.isArray(pageRaw) ? pageRaw : []);
    quranState.bookmarkedAyahs = new Set(Array.isArray(ayahRaw) ? ayahRaw : []);
  } catch {
    quranState.bookmarkedPages = new Set();
    quranState.bookmarkedAyahs = new Set();
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function convertArabicNumbers(str) {
  const arabicNums = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
  return String(str).replace(/[0-9]/g, (digit) => arabicNums[Number(digit)]);
}

function normalizeForSearch(text) {
  return (text || '')
    .normalize('NFKC')
    .replace(/[\u064B-\u065F\u0670]/g, '')
    .replace(/أ|إ|آ/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ة/g, 'ه')
    .toLowerCase();
}

function cleanFirstAyahBasmallah(ayah, surahId, ayahIndex) {
  const basmallah = 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ';
  if (surahId !== 1 && ayahIndex === 0 && ayah.startsWith(basmallah)) {
    return ayah.replace(basmallah, '').trim();
  }
  return ayah;
}

async function loadQuran() {
  const container = document.getElementById('surah-grid-container');
  const status = document.getElementById('quran-search-status');

  try {
    container.innerHTML = '<div style="text-align:center;padding:40px;"><i class="fas fa-spinner fa-spin fa-3x" style="color:#2e7d32"></i><p style="margin-top:20px;color:#2e7d32;font-size:1.2rem;">جاري تحميل المصحف الشريف...</p></div>';

    const [quranResponse, pageMapResponse] = await Promise.all([
      fetch('data/quran.json', { cache: 'no-cache' }),
      fetch('data/quran_page_map.json', { cache: 'no-cache' }).catch(() => null)
    ]);

    if (!quranResponse.ok) throw new Error(`HTTP Error: ${quranResponse.status}`);

    const json = await quranResponse.json();
    if (!json?.surahs?.length) throw new Error('بيانات المصحف فارغة');

    let pageMapMeta = null;
    if (pageMapResponse && pageMapResponse.ok) {
      try {
        pageMapMeta = await pageMapResponse.json();
      } catch {
        pageMapMeta = null;
      }
    }

    quranState.data = json;
    quranState.pageMapMeta = pageMapMeta;
    renderSurahGrid();
    buildMushafPages();
    renderMushafPage(1);
    if (status) {
      const pagesLabel = quranState.totalMushafPages || 0;
      status.textContent = `تم التحميل بنجاح: ${convertArabicNumbers(json.surahs.length)} سورة • ${convertArabicNumbers(pagesLabel)} صفحة`;
    }
  } catch (error) {
    console.error('Error loading Quran:', error);
    container.innerHTML = `
      <div style="text-align:center;padding:40px;color:#d32f2f;">
        <i class="fas fa-exclamation-circle fa-3x"></i>
        <h3 style="margin:20px 0 10px;">عذراً، حدث خطأ في تحميل المصحف</h3>
        <p>يرجى التأكد من اتصالك بالإنترنت وتحديث الصفحة</p>
        <p style="font-size:0.9rem;opacity:0.8;margin-top:10px;direction:ltr;">${error.message}</p>
        <button onclick="location.reload()" style="margin-top:20px;padding:10px 20px;background:#2e7d32;color:white;border:none;border-radius:5px;cursor:pointer;">تحديث الصفحة</button>
      </div>
    `;
  }
}

function renderSurahGrid() {
  const container = document.getElementById('surah-grid-container');
  const surahs = quranState.data?.surahs || [];
  if (!surahs.length) {
    container.innerHTML = '<p>لا توجد بيانات</p>';
    return;
  }

  container.innerHTML = surahs.map((surah) => `
    <button type="button" class="surah-card" data-surah-id="${surah.id}">
      <div class="surah-name">${escapeHtml(surah.name)}</div>
      <div class="surah-meta">
        <div>${escapeHtml(surah.englishName || '')}</div>
        <div style="margin-top:6px;font-size:0.85rem;">${convertArabicNumbers(surah.ayahs.length)} آية</div>
      </div>
    </button>
  `).join('');

  if (typeof AOS !== 'undefined') AOS.refresh();
}

function showSurahList() {
  quranState.currentSurah = null;
  document.getElementById('surah-grid-section').style.display = 'block';
  document.getElementById('surah-section').style.display = 'none';
  document.getElementById('search-results-section').style.display = 'none';
  document.getElementById('mushaf-section').style.display = 'none';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function openSurah(id, highlightAyahNumber = null) {
  const surah = quranState.data?.surahs?.find((item) => item.id === Number(id));
  if (!surah) return;

  quranState.currentSurah = surah;
  document.getElementById('surah-grid-section').style.display = 'none';
  document.getElementById('surah-section').style.display = 'block';
  document.getElementById('search-results-section').style.display = 'none';
  document.getElementById('mushaf-section').style.display = 'none';

  const titleEl = document.querySelector('.surah-title');
  if (titleEl) titleEl.textContent = surah.name;

  const container = document.getElementById('ayah-container');
  const lines = surah.ayahs.map((rawAyah, index) => {
    const ayahNumber = index + 1;
    const cleanedAyah = cleanFirstAyahBasmallah(rawAyah, surah.id, index);
    if (!cleanedAyah) return '';

    const key = ayahBookmarkKey(surah.id, ayahNumber);
    const isBookmarked = quranState.bookmarkedAyahs.has(key);
    const lineId = `ayah-line-${surah.id}-${ayahNumber}`;

    return `
      <div id="${lineId}" class="ayah-line ${isBookmarked ? 'is-bookmarked-ayah' : ''}">
        <button type="button" class="bookmark-ayah-btn ${isBookmarked ? 'active' : ''}" data-surah-id="${surah.id}" data-ayah-number="${ayahNumber}" aria-label="تعليم الآية">
          <i class="fas fa-bookmark"></i>
        </button>
        <span class="ayah-text">${escapeHtml(cleanedAyah)}</span>
        <span class="ayah-end-marker">﴿${convertArabicNumbers(ayahNumber)}﴾</span>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    ${surah.id !== 1 ? '<div class="bismillah-ayah"><span class="bismillah-text">بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ</span></div>' : ''}
    <div class="quran-text-block">${lines}</div>
  `;

  attachAyahBookmarkHandlers(container);
  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (highlightAyahNumber) {
    const target = document.getElementById(`ayah-line-${surah.id}-${highlightAyahNumber}`);
    if (target) {
      setTimeout(() => target.scrollIntoView({ behavior: 'smooth', block: 'center' }), 120);
    }
  }
}

function buildMushafPages() {
  const surahs = quranState.data?.surahs || [];
  const pageMap = quranState.pageMapMeta?.map || null;
  const mappedTotal = Number(quranState.pageMapMeta?.totalPages) || 604;

  if (pageMap) {
    const pages = Array.from({ length: mappedTotal }, () => ({ items: [] }));
    let fallbackPage = 1;

    surahs.forEach((surah) => {
      surah.ayahs.forEach((rawAyah, index) => {
        const ayahNumber = index + 1;
        const text = cleanFirstAyahBasmallah(rawAyah, surah.id, index);
        if (!text) return;

        const key = `${surah.id}:${ayahNumber}`;
        const mappedPage = Number(pageMap[key]);
        const page = mappedPage >= 1 && mappedPage <= mappedTotal ? mappedPage : fallbackPage;
        fallbackPage = page;

        pages[page - 1].items.push({
          surahId: surah.id,
          surahName: surah.name,
          ayahNumber,
          text,
          isFirstAyahInSurah: ayahNumber === 1
        });
      });
    });

    quranState.mushafPages = pages;
    quranState.totalMushafPages = mappedTotal;
    if (quranState.currentMushafPage > mappedTotal) quranState.currentMushafPage = 1;
    return;
  }

  const maxCharsPerPage = 1400;
  const maxAyahsPerPage = 12;
  const fallbackPages = [];
  let pageItems = [];
  let pageCharCount = 0;

  const pushPage = () => {
    if (!pageItems.length) return;
    fallbackPages.push({ items: pageItems });
    pageItems = [];
    pageCharCount = 0;
  };

  surahs.forEach((surah) => {
    surah.ayahs.forEach((rawAyah, index) => {
      const ayahNumber = index + 1;
      const text = cleanFirstAyahBasmallah(rawAyah, surah.id, index);
      if (!text) return;

      const wouldOverflow = pageItems.length >= maxAyahsPerPage || (pageCharCount + text.length) > maxCharsPerPage;
      if (wouldOverflow) pushPage();

      pageItems.push({
        surahId: surah.id,
        surahName: surah.name,
        ayahNumber,
        text,
        isFirstAyahInSurah: ayahNumber === 1
      });
      pageCharCount += text.length;
    });
  });

  pushPage();
  quranState.mushafPages = fallbackPages;
  quranState.totalMushafPages = fallbackPages.length;
  if (quranState.currentMushafPage > fallbackPages.length) quranState.currentMushafPage = 1;
}

function renderMushafPage(pageNumber) {
  const total = quranState.totalMushafPages || quranState.mushafPages.length;
  if (!total) return;

  quranState.currentMushafPage = Math.min(Math.max(1, pageNumber), total);
  const page = quranState.mushafPages[quranState.currentMushafPage - 1] || { items: [] };

  document.getElementById('surah-grid-section').style.display = 'none';
  document.getElementById('surah-section').style.display = 'none';
  document.getElementById('search-results-section').style.display = 'none';
  document.getElementById('mushaf-section').style.display = 'block';

  const pageIndicator = document.getElementById('mushaf-page-indicator');
  const prevBtn = document.getElementById('mushaf-prev-btn');
  const nextBtn = document.getElementById('mushaf-next-btn');
  const bookmarkPageBtn = document.getElementById('bookmark-page-btn');

  if (pageIndicator) {
    pageIndicator.textContent = `الصفحة ${convertArabicNumbers(quranState.currentMushafPage)} من ${convertArabicNumbers(total)}`;
  }
  if (prevBtn) prevBtn.disabled = quranState.currentMushafPage === 1;
  if (nextBtn) nextBtn.disabled = quranState.currentMushafPage === total;

  const isBookmarkedPage = quranState.bookmarkedPages.has(quranState.currentMushafPage);
  if (bookmarkPageBtn) {
    bookmarkPageBtn.classList.toggle('active', isBookmarkedPage);
    bookmarkPageBtn.innerHTML = isBookmarkedPage
      ? '<i class="fas fa-bookmark"></i> الصفحة مُعلّمة'
      : '<i class="far fa-bookmark"></i> تعليم الصفحة';
  }

  let lastSurahId = null;
  const lines = page.items.map((item) => {
    const surahChanged = item.surahId !== lastSurahId;
    lastSurahId = item.surahId;

    const key = ayahBookmarkKey(item.surahId, item.ayahNumber);
    const isBookmarked = quranState.bookmarkedAyahs.has(key);

    const surahHeader = surahChanged
      ? `<div class="mushaf-surah-divider"><span>${escapeHtml(item.surahName)}</span></div>`
      : '';

    const bismillah = item.isFirstAyahInSurah && item.surahId !== 1 && item.surahId !== 9
      ? '<div class="bismillah-ayah"><span class="bismillah-text">بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ</span></div>'
      : '';

    return `
      ${surahHeader}
      ${bismillah}
      <div class="ayah-line ${isBookmarked ? 'is-bookmarked-ayah' : ''}">
        <button type="button" class="bookmark-ayah-btn ${isBookmarked ? 'active' : ''}" data-surah-id="${item.surahId}" data-ayah-number="${item.ayahNumber}" aria-label="تعليم الآية">
          <i class="fas fa-bookmark"></i>
        </button>
        <span class="ayah-text">${escapeHtml(item.text)}</span>
        <span class="ayah-end-marker">﴿${convertArabicNumbers(item.ayahNumber)}﴾</span>
      </div>
    `;
  }).join('');

  const container = document.getElementById('mushaf-page-container');
  container.innerHTML = `
    ${page.items.length ? `<div class="quran-text-block">${lines}</div>` : '<div class="mushaf-page-empty">لا يوجد محتوى في هذه الصفحة.</div>'}
  `;

  attachAyahBookmarkHandlers(container);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function attachAyahBookmarkHandlers(scopeElement) {
  scopeElement.querySelectorAll('.bookmark-ayah-btn').forEach((button) => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      const surahId = Number(button.getAttribute('data-surah-id'));
      const ayahNumber = Number(button.getAttribute('data-ayah-number'));
      toggleAyahBookmark(surahId, ayahNumber);
    });
  });
}

function toggleAyahBookmark(surahId, ayahNumber) {
  const key = ayahBookmarkKey(surahId, ayahNumber);
  if (quranState.bookmarkedAyahs.has(key)) {
    quranState.bookmarkedAyahs.delete(key);
  } else {
    quranState.bookmarkedAyahs.add(key);
  }
  saveBookmarks();

  if (quranState.currentSurah) {
    openSurah(quranState.currentSurah.id, ayahNumber);
  } else {
    renderMushafPage(quranState.currentMushafPage);
  }
}

function togglePageBookmark() {
  const page = quranState.currentMushafPage;
  if (quranState.bookmarkedPages.has(page)) {
    quranState.bookmarkedPages.delete(page);
  } else {
    quranState.bookmarkedPages.add(page);
  }
  saveBookmarks();
  renderMushafPage(page);
}

function highlight(text, query) {
  const escapedText = escapeHtml(text);
  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escapedQuery})`, 'gi');
  return escapedText.replace(regex, '<span class="highlight">$1</span>');
}

function searchAyat(query) {
  const q = (query || '').trim();
  if (!q) {
    showSurahList();
    return;
  }

  const normalizedQ = normalizeForSearch(q);
  const results = [];

  for (const surah of quranState.data?.surahs || []) {
    for (let i = 0; i < surah.ayahs.length; i++) {
      const rawAyah = cleanFirstAyahBasmallah(surah.ayahs[i], surah.id, i);
      const ayah = rawAyah || surah.ayahs[i];
      const ayahMatch = normalizeForSearch(ayah).includes(normalizedQ);
      const surahMatch = normalizeForSearch(surah.name).includes(normalizedQ);
      if (ayahMatch || surahMatch) {
        results.push({
          surahId: surah.id,
          surahName: surah.name,
          ayahText: ayah,
          ayahNumber: i + 1
        });
      }
    }
  }

  document.getElementById('surah-grid-section').style.display = 'none';
  document.getElementById('surah-section').style.display = 'none';
  document.getElementById('mushaf-section').style.display = 'none';
  document.getElementById('search-results-section').style.display = 'block';

  const titleEl = document.getElementById('search-results-title');
  const container = document.getElementById('search-results-container');

  if (!results.length) {
    if (titleEl) titleEl.textContent = 'لم يتم العثور على نتائج';
    container.innerHTML = '<p style="text-align:center;color:#999;">جرب مصطلحاً آخر</p>';
    return;
  }

  if (titleEl) titleEl.textContent = `${convertArabicNumbers(results.length)} نتيجة`;
  container.innerHTML = results.map((result) => `
    <button type="button" class="ayah search-result-item" data-surah-id="${result.surahId}" data-ayah-number="${result.ayahNumber}" style="width:100%;text-align:right;cursor:pointer;">
      <div style="font-size:0.9rem;color:#2e7d32;margin-bottom:8px;">${escapeHtml(result.surahName)}</div>
      ${highlight(result.ayahText, q)}
      <span class="ayah-num">(${convertArabicNumbers(result.ayahNumber)})</span>
    </button>
  `).join('');

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function bindUi() {
  const searchInput = document.getElementById('quran-search-input');
  const searchBtn = document.getElementById('quran-search-btn');
  const backBtn = document.getElementById('quran-back-btn');
  const showSurahModeBtn = document.getElementById('show-surah-mode-btn');
  const showMushafModeBtn = document.getElementById('show-mushaf-mode-btn');
  const mushafPrevBtn = document.getElementById('mushaf-prev-btn');
  const mushafNextBtn = document.getElementById('mushaf-next-btn');
  const bookmarkPageBtn = document.getElementById('bookmark-page-btn');
  const surahGrid = document.getElementById('surah-grid-container');
  const searchResultsContainer = document.getElementById('search-results-container');

  searchBtn?.addEventListener('click', () => searchAyat(searchInput?.value || ''));
  searchInput?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      searchAyat(searchInput.value || '');
    }
  });

  backBtn?.addEventListener('click', showSurahList);
  showSurahModeBtn?.addEventListener('click', showSurahList);
  showMushafModeBtn?.addEventListener('click', () => renderMushafPage(quranState.currentMushafPage || 1));

  mushafPrevBtn?.addEventListener('click', () => renderMushafPage(quranState.currentMushafPage - 1));
  mushafNextBtn?.addEventListener('click', () => renderMushafPage(quranState.currentMushafPage + 1));
  bookmarkPageBtn?.addEventListener('click', togglePageBookmark);

  surahGrid?.addEventListener('click', (event) => {
    const card = event.target.closest('.surah-card[data-surah-id]');
    if (!card) return;
    openSurah(card.getAttribute('data-surah-id'));
  });

  searchResultsContainer?.addEventListener('click', (event) => {
    const button = event.target.closest('.search-result-item[data-surah-id]');
    if (!button) return;
    const surahId = Number(button.getAttribute('data-surah-id'));
    const ayahNumber = Number(button.getAttribute('data-ayah-number'));
    openSurah(surahId, ayahNumber);
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  loadBookmarks();
  bindUi();
  await loadQuran();

  if (typeof AOS !== 'undefined') {
    AOS.init({
      duration: 800,
      easing: 'ease-out-cubic',
      once: true,
      offset: 50,
      delay: 100
    });
  }
});
