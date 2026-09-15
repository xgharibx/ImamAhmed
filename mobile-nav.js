(() => {
    if (document.querySelector('.mobile-bottom-nav')) return;
    const root = new URL('.', document.currentScript?.src || new URL('/mobile-nav.js', location.href).href);
    const page = decodeURIComponent(location.pathname.split('/').pop() || 'index.html');
    const mobile = window.matchMedia('(max-width: 1200px)');
    const headerContainer = document.querySelector('#header .nav-container');
    if (headerContainer && !headerContainer.querySelector('.header-stars')) {
        for (const side of ['start', 'end']) {
            const stars = document.createElement('span');
            stars.className = 'header-stars header-stars-' + side;
            stars.setAttribute('aria-hidden', 'true');
            stars.innerHTML = '<i></i><i></i><i></i><i></i><i></i><i></i>';
            headerContainer.appendChild(stars);
        }
    }
    const tabs = [
        ['home', 'الرئيسية', 'fas fa-home', 'index.html'],
        ['videos', 'المرئيات', 'far fa-play-circle', 'videos.html'],
        ['khutab', 'الخطب', 'far fa-file-alt', 'khutab-written.html'],
        ['library', 'المكتبة', 'far fa-bookmark', 'articles.html']
    ];
    const sections = [
        ['القرآن الكريم', 'fa-quran', 'quran.html'],
        ['التلاوات', 'fa-microphone-alt', 'tilawa.html'],
        ['الحديث الشريف', 'fa-book', 'hadith.html'],
        ['الأذكار', 'fa-praying-hands', 'adhkar.html'],
        ['الخطب المرئية', 'fa-video', 'khutab-video.html'],
        ['المؤلفات', 'fa-book-open', 'books.html'],
        ['الخواطر', 'fa-feather-alt', 'khawater.html'],
        ['أحكام فقهية', 'fa-circle-question', 'fatawa.html'],
        ['عن الشيخ', 'fa-user', 'about.html'],
        ['تواصل معنا', 'fa-envelope', 'contact.html']
    ];
    let active = 'more';
    if (page === 'index.html') active = 'home';
    else if (page === 'videos.html' || page === 'tilawa.html') active = 'videos';
    else if (page.startsWith('khutab-') || page === 'khutba-view.html' || location.pathname.includes('/khutab/')) active = 'khutab';
    else if (['articles.html', 'books.html', 'khawater.html'].includes(page) || location.pathname.includes('/books/')) active = 'library';

    const nav = document.createElement('nav');
    nav.className = 'mobile-bottom-nav';
    nav.setAttribute('aria-label', 'التنقل الرئيسي');
    const track = document.createElement('div');
    track.className = 'mobile-nav-track';
    for (const [id, label, glyph, path] of tabs) {
        const link = document.createElement('a');
        link.href = new URL(path, root).href;
        link.dataset.mobileTab = id;
        link.innerHTML = '<i class="' + glyph + '" aria-hidden="true"></i><span>' + label + '</span>';
        if (id === active) link.setAttribute('aria-current', 'page');
        link.addEventListener('click', event => {
            if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            const target = new URL(link.href);
            if (target.pathname.replace(/index\.html$/, '') === location.pathname.replace(/index\.html$/, '')
                    && target.search === location.search && !location.hash) {
                event.preventDefault();
                window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
            }
        });
        track.append(link);
    }
    nav.append(track);
    const more = document.createElement('button');
    more.type = 'button';
    more.dataset.mobileTab = 'more';
    more.setAttribute('aria-expanded', 'false');
    more.setAttribute('aria-controls', 'mobile-nav-sheet');
    more.setAttribute('aria-haspopup', 'dialog');
    more.setAttribute('aria-label', 'المزيد');
    more.title = 'المزيد';
    if (active === 'more') more.classList.add('is-current');
    more.innerHTML = '<i class="fas fa-ellipsis-v" aria-hidden="true"></i>';
    nav.append(more);

    const sheet = document.createElement('dialog');
    sheet.id = 'mobile-nav-sheet';
    sheet.className = 'mobile-nav-sheet';
    sheet.setAttribute('aria-labelledby', 'mobile-nav-title');
    sheet.innerHTML = '<div class="mobile-nav-sheet-header"><h2 id="mobile-nav-title">أقسام الموقع</h2><button type="button" class="mobile-nav-close" aria-label="إغلاق القائمة" title="إغلاق القائمة"><i class="fas fa-times" aria-hidden="true"></i></button></div>';
    const links = document.createElement('div');
    links.className = 'mobile-nav-sections';
    for (const [label, glyph, path] of sections) {
        const link = document.createElement('a');
        link.href = new URL(path, root).href;
        link.innerHTML = '<i class="fas ' + glyph + '" aria-hidden="true"></i><span>' + label + '</span><i class="fas fa-angle-left" aria-hidden="true"></i>';
        if (page === path) link.setAttribute('aria-current', 'page');
        links.append(link);
    }
    sheet.append(links);
    document.body.append(nav, sheet);
    document.body.classList.add('has-mobile-nav');

    const stateKey = 'sheikhMobileNav';
    const closeSheet = () => {
        if (sheet.open) sheet.close();
        more.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('mobile-nav-open');
    };
    const dismiss = () => {
        closeSheet();
        if (history.state?.[stateKey]) history.back();
    };
    more.addEventListener('click', () => {
        if (sheet.open) { dismiss(); return; }
        sheet.showModal();
        more.setAttribute('aria-expanded', 'true');
        document.body.classList.add('mobile-nav-open');
        history.pushState({ ...history.state, [stateKey]: true }, '', location.href);
    });
    sheet.querySelector('.mobile-nav-close').addEventListener('click', dismiss);
    sheet.addEventListener('cancel', event => { event.preventDefault(); dismiss(); });
    sheet.addEventListener('click', event => {
        const link = event.target.closest('a[href]');
        if (link) {
            event.preventDefault();
            closeSheet();
            location.replace(link.href);
            return;
        }
        if (event.target === sheet) {
            const rect = sheet.getBoundingClientRect();
            if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dismiss();
        }
    });
    window.addEventListener('popstate', closeSheet);
    window.addEventListener('pagehide', closeSheet);
    mobile.addEventListener('change', event => { if (!event.matches && sheet.open) dismiss(); });
    if (window.visualViewport) {
        const viewport = window.visualViewport;
        const updateKeyboard = () => {
            const focused = document.activeElement;
            const editing = focused && (focused.matches('input,textarea,select') || focused.isContentEditable);
            nav.classList.toggle('keyboard-hidden', Boolean(editing && window.innerHeight - viewport.height > 140));
        };
        viewport.addEventListener('resize', updateKeyboard);
        document.addEventListener('focusout', () => window.setTimeout(updateKeyboard, 50));
    }
})();
