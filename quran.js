// Quran page functionality
let quranData = null;
let currentSurah = null;

async function loadQuran() {
  const container = document.getElementById('surah-grid-container');
  try {
    // Show loading state
    container.innerHTML = '<div style="text-align:center;padding:40px;"><i class="fas fa-spinner fa-spin fa-3x" style="color:#2e7d32"></i><p style="margin-top:20px;color:#2e7d32;font-size:1.2rem;">جاري تحميل المصحف الشريف...</p></div>';
    
    // Attempt local fetch
    const response = await fetch('data/quran.json');
    
    if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status}`);
    }
    
    quranData = await response.json();
    
    if (!quranData || !quranData.surahs || quranData.surahs.length === 0) {
        throw new Error('بيانات المصحف فارغة');
    }
    
    renderSurahGrid();
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
  if (!quranData || !quranData.surahs) {
    container.innerHTML = '<p>لا توجد بيانات</p>';
    return;
  }

  let html = '';
  for (const surah of quranData.surahs) {
    html += `
      <div class="surah-card" onclick="openSurah(${surah.id})">
        <div class="surah-name">${surah.name}</div>
        <div class="surah-meta">
          <div>${surah.englishName}</div>
          <div style="margin-top:6px;font-size:0.85rem;">${surah.ayahs.length} آية</div>
        </div>
      </div>
    `;
  }
  container.innerHTML = html;
  
  // Trigger AOS animations if available
  if (typeof AOS !== 'undefined') {
    AOS.refresh();
  }
}

function openSurah(id) {
  currentSurah = quranData.surahs.find(s => s.id === id);
  if (!currentSurah) return;

  // Hide grid, show surah section
  document.getElementById('surah-grid-section').style.display = 'none';
  document.getElementById('surah-section').style.display = 'block';
  document.getElementById('search-results-section').style.display = 'none';

  // Populate surah header
  document.querySelector('.surah-title').textContent = currentSurah.name;

  // Render ayat
  const container = document.getElementById('ayah-container');
  let html = '';
  
  // Add Bismillah for all surahs except Al-Fatiha (id 1)
  if (currentSurah.id !== 1) {
    html += `
      <div class="bismillah-ayah">
        <span class="bismillah-text">بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ</span>
      </div>
    `;
  }
  
  let surahText = '';
  
  // Clean Basmallah from first verse for non-Fatiha surahs
  // The data sometimes includes Basmallah at the start of Verse 1
  // Exact string from JSON seems to be: بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ 
  const basmallahExact = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ";

  for (let i = 0; i < currentSurah.ayahs.length; i++) {
    let ayah = currentSurah.ayahs[i];
    
    // Remove Basmallah from first verse if present (except Fatiha)
    if (i === 0 && currentSurah.id !== 1) {
       if (ayah.startsWith(basmallahExact)) {
           ayah = ayah.replace(basmallahExact, '').trim();
       }
    }

    const ayahNum = convertArabicNumbers((i + 1).toString());
    surahText += `
      <span class="ayah-text">${escapeHtml(ayah)}</span>
      <span class="ayah-end-marker">﴿${ayahNum}﴾</span>
    `;
  }
  html += `<div class="quran-text-block">${surahText}</div>`;
  
  container.innerHTML = html;

  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showSurahList() {
  currentSurah = null;
  document.getElementById('surah-grid-section').style.display = 'block';
  document.getElementById('surah-section').style.display = 'none';
  document.getElementById('search-results-section').style.display = 'none';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function searchAyat(query) {
  if (!query.trim()) {
    showSurahList();
    return;
  }

  const results = [];
  const q = query.toLowerCase();

  for (const surah of quranData.surahs) {
    for (let i = 0; i < surah.ayahs.length; i++) {
      const ayah = surah.ayahs[i];
      if (ayah.toLowerCase().includes(q) || surah.name.toLowerCase().includes(q)) {
        results.push({
          surah: surah,
          ayah: ayah,
          ayahIndex: i + 1,
          text: ayah
        });
      }
    }
  }

  // Show results
  document.getElementById('surah-grid-section').style.display = 'none';
  document.getElementById('surah-section').style.display = 'none';
  document.getElementById('search-results-section').style.display = 'block';

  const container = document.getElementById('search-results-container');
  const header = document.querySelector('.search-results-header h3');

  if (results.length === 0) {
    header.textContent = 'لم يتم العثور على نتائج';
    container.innerHTML = '<p style="text-align:center;color:#999;">جرب مصطلحاً آخر</p>';
  } else {
    header.textContent = `${results.length} نتيجة`;
    let html = '';
    for (const result of results) {
      const highlightedText = highlight(result.text, query);
      const ayahNum = convertArabicNumbers(result.ayahIndex.toString());
      html += `
        <div class="ayah" onclick="openSurah(${result.surah.id})" style="cursor:pointer;">
          <div style="font-size:0.9rem;color:#999;margin-bottom:8px;">${result.surah.name}</div>
          ${highlightedText}
          <span class="ayah-num">(${ayahNum})</span>
        </div>
      `;
    }
    container.innerHTML = html;
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function clearSearch() {
  document.getElementById('quran-search-input').value = '';
  showSurahList();
}

function highlight(text, query) {
  const escapedText = escapeHtml(text);
  const regex = new RegExp(`(${query})`, 'gi');
  return escapedText.replace(regex, '<span class="highlight">$1</span>');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function convertArabicNumbers(str) {
  const arabicNums = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
  let result = '';
  for (let char of str.toString()) {
    if (char >= '0' && char <= '9') {
      result += arabicNums[parseInt(char)];
    } else {
      result += char;
    }
  }
  return result;
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
  loadQuran();

  const searchInput = document.getElementById('quran-search-input');
  const searchBtn = document.getElementById('quran-search-btn');
  const backBtn = document.getElementById('quran-back-btn');

  if (searchBtn) {
    searchBtn.addEventListener('click', () => {
      const query = searchInput.value.trim();
      searchAyat(query);
    });
  }

  if (searchInput) {
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        const query = searchInput.value.trim();
        searchAyat(query);
      }
    });
  }

  if (backBtn) {
    backBtn.addEventListener('click', showSurahList);
  }

  // Initialize AOS animations
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
