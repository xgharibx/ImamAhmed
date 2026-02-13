/* =====================================================
   الشيخ أحمد إسماعيل الفشني - Main JavaScript
   Navigation, Animations, and Interactions
   ===================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize all components
    initPreloader();
    initNavigation();
    initComingSoonLinks();
    initScrollEffects();
    initKhawaterSlider();
    initAnimations();
    initHomeWhatsappForm();
    initBackToTop();
    initBrowserBackButton();
    initCounters();
    initKhawaterSearchFilters();
    initKhawaterShareButtons();
    initPerformanceOptimizations();
    setCurrentYear();
});

/* ============== Preloader ============== */
function initPreloader() {
    const preloader = document.getElementById('preloader');
    
    window.addEventListener('load', () => {
        const isMobile = window.matchMedia('(max-width: 768px)').matches;
        const delay = isMobile ? 600 : 1500;
        setTimeout(() => {
            preloader.classList.add('hidden');
            document.body.style.overflow = 'visible';
        }, delay);
    });
}

/* ============== Navigation ============== */
function initNavigation() {
    const header = document.getElementById('header');
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    const navLinks = document.querySelectorAll('.nav-link');
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');

    const setMobileHeaderHeight = () => {
        if (!header) return;
        const headerHeight = Math.max(header.offsetHeight || 72, 64);
        document.documentElement.style.setProperty('--mobile-header-height', `${headerHeight}px`);
    };

    const closeMobileMenu = () => {
        hamburger?.classList.remove('active');
        navMenu?.classList.remove('active');
        if (hamburger) hamburger.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
    };

    setMobileHeaderHeight();
    
    // Mobile menu toggle
    hamburger?.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navMenu.classList.toggle('active');
        hamburger.setAttribute('aria-expanded', navMenu.classList.contains('active') ? 'true' : 'false');
        document.body.style.overflow = navMenu.classList.contains('active') ? 'hidden' : '';
    });
    
    // Close menu on link click
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (link.classList.contains('dropdown-toggle')) return;
            closeMobileMenu();
        });
    });

    // Dropdown toggles (works for mobile + desktop click)
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const parent = toggle.closest('.nav-item.dropdown');
            if (!parent) return;

            // Close other dropdowns
            document.querySelectorAll('.nav-item.dropdown.open').forEach(other => {
                if (other !== parent) {
                    other.classList.remove('open');
                    const otherToggle = other.querySelector('.dropdown-toggle');
                    if (otherToggle) otherToggle.setAttribute('aria-expanded', 'false');
                }
            });

            const isOpen = parent.classList.toggle('open');
            toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (e.target.closest('.nav-item.dropdown')) return;
        document.querySelectorAll('.nav-item.dropdown.open').forEach(dd => {
            dd.classList.remove('open');
            const ddToggle = dd.querySelector('.dropdown-toggle');
            if (ddToggle) ddToggle.setAttribute('aria-expanded', 'false');
        });
    });
    
    // Header scroll effect
    let scrollTicking = false;
    const updateHeaderOnScroll = () => {
        if (!header) return;
        if (window.scrollY > 100) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
        scrollTicking = false;
    };

    window.addEventListener('scroll', () => {
        if (scrollTicking) return;
        scrollTicking = true;
        window.requestAnimationFrame(updateHeaderOnScroll);
    }, { passive: true });

    updateHeaderOnScroll();

    window.addEventListener('resize', () => {
        setMobileHeaderHeight();
        if (window.innerWidth > 992) {
            closeMobileMenu();
            document.querySelectorAll('.nav-item.dropdown.open').forEach(dd => {
                dd.classList.remove('open');
                const ddToggle = dd.querySelector('.dropdown-toggle');
                if (ddToggle) ddToggle.setAttribute('aria-expanded', 'false');
            });
        }
    });

    window.addEventListener('orientationchange', setMobileHeaderHeight);
    
    // Active link highlighting
    updateActiveNavLink();
}

function updateActiveNavLink() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPage) {
            link.classList.add('active');
        }
    });
}

/* ============== Coming Soon (Global) ============== */
function initComingSoonLinks() {
    // Disable only khutab audio everywhere (video is now live)
    const comingSoonTargets = new Set(['khutab-audio.html']);

    document.querySelectorAll('a[href]').forEach((a) => {
        const rawHref = (a.getAttribute('href') || '').trim();
        if (!rawHref) return;

        // Ignore external links
        if (/^(https?:|mailto:|tel:)/i.test(rawHref)) return;

        const cleanHref = rawHref.split('#')[0].split('?')[0];
        if (!comingSoonTargets.has(cleanHref)) return;

        a.classList.add('is-disabled-link', 'has-soon-badge');
        a.setAttribute('aria-disabled', 'true');
        a.setAttribute('tabindex', '-1');
        a.setAttribute('data-soon', 'قريباً');

        // Extra safety in case CSS pointer-events is overridden somewhere
        a.addEventListener(
            'click',
            (e) => {
                e.preventDefault();
                e.stopPropagation();
            },
            true
        );
    });
}

/* ============== Scroll Effects ============== */
function initScrollEffects() {
    const isMobile = window.matchMedia('(max-width: 768px)').matches;

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = (this.getAttribute('href') || '').trim();
            if (!href || href === '#') return;

            let target = null;
            try {
                target = document.querySelector(href);
            } catch {
                return;
            }

            if (!target) return;

            e.preventDefault();
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        });
    });
    
    // Parallax effect for hero
    const hero = document.querySelector('.hero-section');
    if (hero && !isMobile) {
        let heroScrollTicking = false;
        window.addEventListener('scroll', () => {
            if (heroScrollTicking) return;
            heroScrollTicking = true;

            window.requestAnimationFrame(() => {
            const scrolled = window.pageYOffset;
            const heroContent = hero.querySelector('.hero-content');
            if (heroContent && scrolled < window.innerHeight) {
                heroContent.style.transform = `translateY(${scrolled * 0.3}px)`;
                heroContent.style.opacity = 1 - (scrolled / window.innerHeight);
            }
                heroScrollTicking = false;
            });
        }, { passive: true });
    }
}

/* ============== Khawater Slider ============== */
function initKhawaterSlider() {
    const slider = document.querySelector('.khawater-slider');
    if (!slider) return;
    
    const slides = slider.querySelectorAll('.khawater-slide');
    const dotsContainer = document.querySelector('.slider-dots');
    const prevBtn = document.querySelector('.prev-btn');
    const nextBtn = document.querySelector('.next-btn');
    
    let currentSlide = 0;
    let autoSlideInterval;
    
    // Create dots
    slides.forEach((_, index) => {
        const dot = document.createElement('button');
        dot.classList.add('slider-dot');
        if (index === 0) dot.classList.add('active');
        dot.addEventListener('click', () => goToSlide(index));
        dotsContainer?.appendChild(dot);
    });
    
    const dots = dotsContainer?.querySelectorAll('.slider-dot');
    
    function goToSlide(index) {
        slides[currentSlide].classList.remove('active');
        dots?.[currentSlide]?.classList.remove('active');
        
        currentSlide = index;
        if (currentSlide >= slides.length) currentSlide = 0;
        if (currentSlide < 0) currentSlide = slides.length - 1;
        
        slides[currentSlide].classList.add('active');
        dots?.[currentSlide]?.classList.add('active');
    }
    
    function nextSlide() {
        goToSlide(currentSlide + 1);
    }
    
    function prevSlide() {
        goToSlide(currentSlide - 1);
    }
    
    // Event listeners
    nextBtn?.addEventListener('click', () => {
        nextSlide();
        resetAutoSlide();
    });
    
    prevBtn?.addEventListener('click', () => {
        prevSlide();
        resetAutoSlide();
    });
    
    // Auto slide
    function startAutoSlide() {
        autoSlideInterval = setInterval(nextSlide, 5000);
    }
    
    function resetAutoSlide() {
        clearInterval(autoSlideInterval);
        startAutoSlide();
    }
    
    // Pause on hover
    slider.addEventListener('mouseenter', () => clearInterval(autoSlideInterval));
    slider.addEventListener('mouseleave', startAutoSlide);
    
    // Touch support
    let touchStartX = 0;
    let touchEndX = 0;
    
    slider.addEventListener('touchstart', e => {
        touchStartX = e.changedTouches[0].screenX;
    });
    
    slider.addEventListener('touchend', e => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    });
    
    function handleSwipe() {
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;
        
        if (diff > swipeThreshold) {
            prevSlide(); // Swipe left (RTL)
        } else if (diff < -swipeThreshold) {
            nextSlide(); // Swipe right (RTL)
        }
        resetAutoSlide();
    }
    
    startAutoSlide();
}

/* ============== AOS Animations ============== */
function initAnimations() {
    const isMobile = window.matchMedia('(max-width: 768px)').matches;

    // Initialize AOS library
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            easing: 'ease-out-cubic',
            once: true,
            offset: 50,
            delay: 100,
            disable: isMobile
        });
    }
    
    // Custom intersection observer for additional animations
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animated');
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });
}

/* ============== Home WhatsApp Form ============== */
function initHomeWhatsappForm() {
    const form = document.getElementById('homeWhatsappForm');
    if (!form) return;

    const whatsappNumber = '201030054301';

    form.addEventListener('submit', (e) => {
        e.preventDefault();

        const messageInput = document.getElementById('homeWhatsappMessage');
        const messageValue = messageInput?.value.trim() || '';
        const button = form.querySelector('button');
        const originalText = button.innerHTML;

        const message = messageValue || 'السلام عليكم ورحمة الله وبركاته، أود التواصل معكم.';
        const whatsappUrl = `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(message)}`;

        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري التحويل...';
        button.disabled = true;

        window.open(whatsappUrl, '_blank', 'noopener');

        setTimeout(() => {
            button.innerHTML = originalText;
            button.disabled = false;
        }, 1200);
    });
}

/* ============== Back to Top ============== */
function initBackToTop() {
    const backToTopBtn = document.getElementById('backToTop');
    if (!backToTopBtn) return;
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 500) {
            backToTopBtn.classList.add('visible');
        } else {
            backToTopBtn.classList.remove('visible');
        }
    }, { passive: true });
    
    backToTopBtn.addEventListener('click', (e) => {
        e.preventDefault();
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

/* ============== Browser Back Button ============== */
function initBrowserBackButton() {
    // Handle keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Alt + Left Arrow or Backspace (when not in input)
        if ((e.altKey && e.key === 'ArrowLeft') || 
            (e.key === 'Backspace' && !['INPUT', 'TEXTAREA'].includes(e.target.tagName))) {
            e.preventDefault();
            if (window.history.length > 1) {
                window.history.back();
            } else {
                window.location.href = 'index.html';
            }
        }
    });
}

/* ============== Counter Animation ============== */
function initCounters() {
    const counters = document.querySelectorAll('.stat-number');
    
    const observerOptions = {
        threshold: 0.5
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                const target = counter.innerText;
                
                // Skip if not a number
                if (isNaN(parseInt(target.replace(/[^\d]/g, '')))) return;
                
                animateCounter(counter, target);
                observer.unobserve(counter);
            }
        });
    }, observerOptions);
    
    counters.forEach(counter => observer.observe(counter));
}

/* ============== Khawater Search & Filters ============== */
function initKhawaterSearchFilters() {
    const section = document.querySelector('.khawater-main');
    if (!section) return;

    const searchInput = section.querySelector('.search-box input');
    const filterButtons = section.querySelectorAll('.filter-tags .filter-tag');
    const cards = Array.from(section.querySelectorAll('.khatera-card'));
    if (!cards.length) return;

    const searchUtils = window.SiteSearchUtils || null;
    const normalizeSearchText = (value) => {
        if (searchUtils?.normalize) return searchUtils.normalize(value);
        return String(value || '')
            .normalize('NFKD')
            .replace(/[\u064B-\u065F\u0670\u06D6-\u06ED]/g, '')
            .replace(/[أإآٱ]/g, 'ا')
            .replace(/[ؤئ]/g, 'ء')
            .replace(/ى/g, 'ي')
            .replace(/ة/g, 'ه')
            .replace(/\s+/g, ' ')
            .trim()
            .toLowerCase();
    };

    const createMatcher = (query) => {
        if (searchUtils?.createMatcher) return searchUtils.createMatcher(query);
        const normalized = normalizeSearchText(query);
        return {
            score(haystack) {
                const target = normalizeSearchText(haystack);
                if (!target) return 0;
                if (!normalized) return 1;
                return target.includes(normalized) ? 1 : 0;
            }
        };
    };

    const emptyState = document.createElement('div');
    emptyState.className = 'khutab-empty';
    emptyState.textContent = 'لا توجد نتائج مطابقة في الخواطر.';
    emptyState.style.display = 'none';
    emptyState.style.marginTop = '1rem';
    const grid = section.querySelector('.khawater-grid');
    grid?.parentElement?.appendChild(emptyState);

    let activeTag = 'الكل';
    let currentQuery = '';

    const applyFilter = () => {
        const normalizedActiveTag = normalizeSearchText(activeTag);
        const matcher = createMatcher(currentQuery);
        let visibleCount = 0;

        cards.forEach((card) => {
            const text = card.querySelector('.khatera-text')?.textContent || '';
            const tag = card.querySelector('.card-tag')?.textContent || '';
            const cardTagNormalized = normalizeSearchText(tag);

            const matchesTag = normalizedActiveTag === 'الكل' || cardTagNormalized.includes(normalizedActiveTag);
            const score = matcher.score(`${text} ${tag}`);
            const matchesQuery = !currentQuery.trim() || score > 0;

            const shouldShow = matchesTag && matchesQuery;
            card.style.display = shouldShow ? '' : 'none';
            if (shouldShow) visibleCount += 1;
        });

        emptyState.style.display = visibleCount ? 'none' : 'block';
    };

    filterButtons.forEach((button) => {
        button.addEventListener('click', () => {
            filterButtons.forEach((btn) => btn.classList.remove('active'));
            button.classList.add('active');
            activeTag = button.textContent.trim() || 'الكل';
            applyFilter();
        });
    });

    const debouncedApply = debounce(applyFilter, 220);
    searchInput?.addEventListener('input', () => {
        currentQuery = searchInput.value || '';
        debouncedApply();
    });

    applyFilter();
}

/* ============== Khawater Share ============== */
function normalizeInlineText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
}

function wrapCanvasTextByWords(ctx, text, maxWidth) {
    const words = normalizeInlineText(text).split(' ').filter(Boolean);
    const lines = [];
    let current = '';

    for (const word of words) {
        const next = current ? `${current} ${word}` : word;
        if (ctx.measureText(next).width <= maxWidth) {
            current = next;
        } else {
            if (current) lines.push(current);
            current = word;
        }
    }

    if (current) lines.push(current);
    return lines;
}

function canvasToBlob(canvas, type = 'image/png', quality = 0.95) {
    return new Promise((resolve, reject) => {
        if (!canvas?.toBlob) {
            reject(new Error('Canvas toBlob is unavailable'));
            return;
        }
        canvas.toBlob((blob) => {
            if (blob) resolve(blob);
            else reject(new Error('Failed to create image blob'));
        }, type, quality);
    });
}

async function createKhawateraShareImageBlob({ text, tag, number, signature }) {
    if (document.fonts?.ready) {
        await Promise.race([
            document.fonts.ready,
            new Promise((resolve) => setTimeout(resolve, 1200))
        ]);
    }

    const canvas = document.createElement('canvas');
    canvas.width = 1080;
    canvas.height = 1350;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas context unavailable');

    const bgGradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    bgGradient.addColorStop(0, '#1a5f4a');
    bgGradient.addColorStop(1, '#1f7a5a');
    ctx.fillStyle = bgGradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = 'rgba(212, 175, 55, 0.09)';
    for (let y = 34; y < canvas.height; y += 78) {
        for (let x = 34; x < canvas.width; x += 78) {
            ctx.beginPath();
            ctx.arc(x, y, 2.1, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    const card = { x: 70, y: 190, width: 940, height: 980 };
    ctx.fillStyle = 'rgba(255,255,255,0.97)';
    ctx.beginPath();
    ctx.roundRect(card.x, card.y, card.width, card.height, 30);
    ctx.fill();

    ctx.fillStyle = '#d4af37';
    ctx.beginPath();
    ctx.roundRect(card.x + card.width - 10, card.y + 14, 10, card.height - 28, 7);
    ctx.fill();

    ctx.direction = 'rtl';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#d4af37';
    ctx.font = '700 35px Cairo, Tahoma, Arial';
    ctx.fillText('خاطرة إيمانية', canvas.width / 2, 105);

    const safeTag = normalizeInlineText(tag || 'خواطر');
    const tagWidth = Math.min(430, Math.max(180, ctx.measureText(safeTag).width + 80));
    const tagX = card.x + card.width - tagWidth - 42;
    const tagY = card.y + 58;
    ctx.fillStyle = 'rgba(26, 95, 74, 0.12)';
    ctx.beginPath();
    ctx.roundRect(tagX, tagY, tagWidth, 56, 28);
    ctx.fill();
    ctx.textAlign = 'right';
    ctx.fillStyle = '#1a5f4a';
    ctx.font = '700 28px Cairo, Tahoma, Arial';
    ctx.fillText(safeTag, tagX + tagWidth - 28, tagY + 39);

    const safeNumber = normalizeInlineText(number || '');
    if (safeNumber) {
        const numberX = card.x + 74;
        const numberY = card.y + 86;
        ctx.fillStyle = '#1a5f4a';
        ctx.beginPath();
        ctx.arc(numberX, numberY, 34, 0, Math.PI * 2);
        ctx.fill();
        ctx.textAlign = 'center';
        ctx.fillStyle = '#d4af37';
        ctx.font = '700 34px Cairo, Tahoma, Arial';
        ctx.fillText(safeNumber, numberX, numberY + 12);
    }

    ctx.textAlign = 'right';
    ctx.fillStyle = 'rgba(212, 175, 55, 0.35)';
    ctx.font = '700 132px Cairo, Tahoma, Arial';
    ctx.fillText('”', card.x + card.width - 62, card.y + 205);

    const maxTextWidth = card.width - 130;
    const textStartY = card.y + 265;
    const textBottomY = card.y + card.height - 190;

    const safeText = normalizeInlineText(text);
    let selected = null;
    const fontSizes = [54, 50, 46, 42, 38, 34, 30];

    for (const size of fontSizes) {
        const lineHeight = Math.round(size * 1.78);
        ctx.font = `600 ${size}px Cairo, Tahoma, Arial`;
        const lines = wrapCanvasTextByWords(ctx, safeText, maxTextWidth);
        const maxLines = Math.floor((textBottomY - textStartY) / lineHeight);
        if (lines.length <= maxLines) {
            selected = { size, lineHeight, lines };
            break;
        }
    }

    if (!selected) {
        const size = 30;
        const lineHeight = Math.round(size * 1.78);
        ctx.font = `600 ${size}px Cairo, Tahoma, Arial`;
        const lines = wrapCanvasTextByWords(ctx, safeText, maxTextWidth);
        const maxLines = Math.max(3, Math.floor((textBottomY - textStartY) / lineHeight));
        selected = { size, lineHeight, lines: lines.slice(0, maxLines) };
        if (lines.length > maxLines && selected.lines.length) {
            let last = selected.lines[selected.lines.length - 1];
            while (last.length > 3 && ctx.measureText(`${last}…`).width > maxTextWidth) {
                last = last.slice(0, -1).trim();
            }
            selected.lines[selected.lines.length - 1] = `${last}…`;
        }
    }

    ctx.font = `600 ${selected.size}px Cairo, Tahoma, Arial`;
    ctx.fillStyle = '#0f2f24';
    let y = textStartY;
    for (const line of selected.lines) {
        ctx.fillText(line, card.x + card.width - 58, y);
        y += selected.lineHeight;
    }

    const safeSignature = normalizeInlineText(signature || '— الشيخ أحمد إسماعيل الفشني');
    const signatureLineY = card.y + card.height - 122;
    ctx.strokeStyle = 'rgba(212, 175, 55, 0.45)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(card.x + 55, signatureLineY);
    ctx.lineTo(card.x + card.width - 55, signatureLineY);
    ctx.stroke();

    ctx.fillStyle = '#1a5f4a';
    ctx.font = '700 34px Cairo, Tahoma, Arial';
    ctx.textAlign = 'center';
    ctx.fillText(safeSignature, canvas.width / 2, signatureLineY + 58);

    ctx.fillStyle = 'rgba(255,255,255,0.88)';
    ctx.font = '600 20px Cairo, Tahoma, Arial';
    ctx.fillText('ahmedelfashny.com', canvas.width / 2, canvas.height - 42);

    return canvasToBlob(canvas, 'image/png', 0.96);
}

function triggerBlobDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function initKhawaterShareButtons() {
    const shareButtons = document.querySelectorAll('.khatera-card .share-btn');
    if (!shareButtons.length) return;

    const signature = '— الشيخ أحمد إسماعيل الفشني';

    shareButtons.forEach((button) => {
        if (!button.querySelector('i')) {
            button.innerHTML = '<i class="fas fa-share-alt"></i>';
        }

        button.addEventListener('click', async (event) => {
            event.preventDefault();

            const card = button.closest('.khatera-card');
            const text = card?.querySelector('.khatera-text')?.textContent?.trim();
            const tag = normalizeInlineText(card?.querySelector('.card-tag')?.textContent || 'خواطر');
            const number = normalizeInlineText(card?.querySelector('.card-number')?.textContent || '');
            if (!text) return;

            const payloadText = `${text}\n\n${signature}`;
            const pageUrl = window.location.href;
            const title = document.title || 'خواطر الشيخ أحمد الفشني';
            const imageFileName = `khatera-${number || 'share'}.png`;

            button.disabled = true;
            button.style.pointerEvents = 'none';
            button.style.opacity = '0.85';

            try {
                const imageBlob = await createKhawateraShareImageBlob({
                    text,
                    tag,
                    number,
                    signature
                });

                const imageFile = new File([imageBlob], imageFileName, { type: 'image/png' });
                const canShareImage = typeof navigator.canShare === 'function'
                    && navigator.canShare({ files: [imageFile] });

                if (navigator.share && canShareImage) {
                    await navigator.share({
                        files: [imageFile],
                        title,
                        text: signature,
                        url: pageUrl
                    });
                    showShareToast('تمت مشاركة الخاطرة كصورة');
                    return;
                }

                if (navigator.clipboard?.write && window.ClipboardItem) {
                    await navigator.clipboard.write([
                        new ClipboardItem({ 'image/png': imageBlob })
                    ]);
                    showShareToast('تم نسخ صورة الخاطرة للحافظة');
                    return;
                }

                triggerBlobDownload(imageBlob, imageFileName);
                await navigator.clipboard.writeText(`${payloadText}\n${pageUrl}`);
                showShareToast('تم تنزيل الصورة ونسخ النص مع التوقيع');
            } catch {
                try {
                    const fallbackTextArea = document.createElement('textarea');
                    fallbackTextArea.value = `${payloadText}\n${pageUrl}`;
                    fallbackTextArea.style.position = 'fixed';
                    fallbackTextArea.style.opacity = '0';
                    document.body.appendChild(fallbackTextArea);
                    fallbackTextArea.select();
                    document.execCommand('copy');
                    fallbackTextArea.remove();
                    showShareToast('تم نسخ الخاطرة مع التوقيع');
                } catch {
                    showShareToast('تعذر النسخ حالياً');
                }
            } finally {
                button.disabled = false;
                button.style.pointerEvents = '';
                button.style.opacity = '';
            }
        });
    });
}

function showShareToast(message) {
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.left = '20px';
    toast.style.zIndex = '9999';
    toast.style.background = 'rgba(15, 23, 42, 0.9)';
    toast.style.color = '#fff';
    toast.style.padding = '10px 14px';
    toast.style.borderRadius = '10px';
    toast.style.fontSize = '0.9rem';
    toast.style.fontFamily = 'Cairo, sans-serif';
    toast.style.boxShadow = '0 8px 22px rgba(0,0,0,0.22)';
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 1700);
}

function animateCounter(element, target) {
    const prefix = target.match(/^[^\d]*/)?.[0] || '';
    const suffix = target.match(/[^\d]*$/)?.[0] || '';
    const number = parseInt(target.replace(/[^\d]/g, '')) || 0;
    
    if (number === 0) return;
    
    const duration = 2000;
    const start = 0;
    const increment = number / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= number) {
            element.innerText = prefix + number.toLocaleString('ar-EG') + suffix;
            clearInterval(timer);
        } else {
            element.innerText = prefix + Math.floor(current).toLocaleString('ar-EG') + suffix;
        }
    }, 16);
}

/* ============== Set Current Year ============== */
function setCurrentYear() {
    const yearElement = document.getElementById('currentYear');
    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }
}

/* ============== Performance Optimizations ============== */
function initPerformanceOptimizations() {
    const images = document.querySelectorAll('img');
    images.forEach((img) => {
        if (!img.hasAttribute('decoding')) {
            img.setAttribute('decoding', 'async');
        }
        if (!img.hasAttribute('loading')) {
            const rect = img.getBoundingClientRect();
            const nearViewport = rect.top < (window.innerHeight || 900) * 1.5;
            img.setAttribute('loading', nearViewport ? 'eager' : 'lazy');
        }
    });
}

/* ============== Utility Functions ============== */

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Format Arabic numbers
function toArabicNumbers(num) {
    const arabicNums = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
    return num.toString().replace(/\d/g, d => arabicNums[d]);
}

// Local storage helpers
const storage = {
    get(key) {
        try {
            return JSON.parse(localStorage.getItem(key));
        } catch {
            return null;
        }
    },
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch {
            console.error('localStorage error');
        }
    },
    remove(key) {
        localStorage.removeItem(key);
    }
};

// Export utilities
window.siteUtils = {
    debounce,
    throttle,
    toArabicNumbers,
    storage
};
