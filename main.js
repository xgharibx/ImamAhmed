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
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const heroContent = hero.querySelector('.hero-content');
            if (heroContent && scrolled < window.innerHeight) {
                heroContent.style.transform = `translateY(${scrolled * 0.3}px)`;
                heroContent.style.opacity = 1 - (scrolled / window.innerHeight);
            }
        });
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
    });
    
    backToTopBtn.addEventListener('click', () => {
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
