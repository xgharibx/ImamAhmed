/* =====================================================
   LIVING SCRIPTURE - Interactive Animations
   Kinetic Typography, Geometric Stars & Particle System
   ===================================================== */

class LivingScriptureTheme {
    constructor() {
        this.particles = [];
        this.inkStrokes = [];
        this.isInitialized = false;
        this.starCanvas = null;
        this.starCtx = null;
        this.animationFrame = null;
    }

    init() {
        if (this.isInitialized) return;
        this.isInitialized = true;
        
        // Add theme class to body
        document.body.classList.add('living-scripture-theme');
        
        // Initialize components
        this.createParticlesContainer();
        // DISABLED: Star canvas replaced with CSS crescent moons
        // this.createGeometricStarCanvas();
        this.initParticles();
        // DISABLED: Star pattern replaced with CSS crescent moons
        // this.initGeometricStar();
        this.initInkStrokes();
        
        // Handle resize
        window.addEventListener('resize', () => this.handleResize());
    }

    /* =====================================================
       FLOATING LIGHT PARTICLES
       ===================================================== */
    createParticlesContainer() {
        const container = document.createElement('div');
        container.className = 'particles-container';
        container.id = 'particles-container';
        document.body.appendChild(container);
        this.particlesContainer = container;
    }

    initParticles() {
        const particleCount = window.innerWidth < 768 ? 20 : 40;
        
        for (let i = 0; i < particleCount; i++) {
            this.createParticle(i);
        }
    }

    createParticle(index) {
        const particle = document.createElement('div');
        particle.className = 'light-particle';
        
        // Random properties
        const size = Math.random() * 4 + 2;
        const left = Math.random() * 100;
        const duration = Math.random() * 15 + 10;
        const delay = Math.random() * 15;
        const opacity = Math.random() * 0.5 + 0.3;
        
        particle.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            left: ${left}%;
            animation-duration: ${duration}s;
            animation-delay: ${delay}s;
            --particle-opacity: ${opacity};
        `;
        
        this.particlesContainer.appendChild(particle);
        this.particles.push(particle);
    }

    /* =====================================================
       GEOMETRIC ISLAMIC STAR PATTERN
       ===================================================== */
    createGeometricStarCanvas() {
        const heroSection = document.querySelector('.hero-section');
        if (!heroSection) return;
        
        const canvas = document.createElement('canvas');
        canvas.className = 'geometric-star-canvas';
        canvas.id = 'geometric-star-canvas';
        heroSection.insertBefore(canvas, heroSection.firstChild);
        
        this.starCanvas = canvas;
        this.starCtx = canvas.getContext('2d');
        this.resizeCanvas();
    }

    resizeCanvas() {
        if (!this.starCanvas) return;
        this.starCanvas.width = window.innerWidth;
        this.starCanvas.height = window.innerHeight;
    }

    initGeometricStar() {
        if (!this.starCtx) return;
        
        this.starAnimation = {
            progress: 0,
            glowIntensity: 0,
            stars: [],
            lines: []
        };
        
        // Generate star patterns
        this.generateStarPattern();
        
        // Start animation
        this.animateGeometricStar();
    }

    generateStarPattern() {
        const centerX = this.starCanvas.width / 2;
        const centerY = this.starCanvas.height / 2;
        const maxRadius = Math.min(centerX, centerY) * 0.7;
        
        // Main 8-pointed star
        this.starAnimation.mainStar = {
            x: centerX,
            y: centerY,
            radius: maxRadius,
            points: 8,
            rotation: 0
        };
        
        // Connecting lines
        for (let i = 0; i < 8; i++) {
            const angle = (i * Math.PI * 2) / 8;
            this.starAnimation.lines.push({
                x1: centerX,
                y1: centerY,
                x2: centerX + Math.cos(angle) * maxRadius,
                y2: centerY + Math.sin(angle) * maxRadius,
                progress: 0,
                delay: i * 0.1
            });
        }
        
        // Smaller decorative stars
        for (let ring = 1; ring <= 2; ring++) {
            const ringRadius = maxRadius * (0.4 + ring * 0.25);
            const starCount = 8;
            
            for (let i = 0; i < starCount; i++) {
                const angle = (i * Math.PI * 2) / starCount + (ring * Math.PI / 8);
                this.starAnimation.stars.push({
                    x: centerX + Math.cos(angle) * ringRadius,
                    y: centerY + Math.sin(angle) * ringRadius,
                    radius: maxRadius * 0.08,
                    points: 8,
                    rotation: 0,
                    delay: 0.5 + ring * 0.3 + i * 0.05
                });
            }
        }
    }

    animateGeometricStar() {
        const ctx = this.starCtx;
        const canvas = this.starCanvas;
        
        if (!ctx || !canvas) return;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        this.starAnimation.progress += 0.005;
        this.starAnimation.glowIntensity = Math.sin(Date.now() * 0.001) * 0.3 + 0.7;
        
        const progress = Math.min(this.starAnimation.progress, 1);
        
        // Draw connecting lines with writing animation
        ctx.strokeStyle = `rgba(201, 162, 39, ${0.3 * progress * this.starAnimation.glowIntensity})`;
        ctx.lineWidth = 1;
        ctx.shadowBlur = 20;
        ctx.shadowColor = 'rgba(201, 162, 39, 0.5)';
        
        this.starAnimation.lines.forEach((line, index) => {
            const lineProgress = Math.max(0, Math.min(1, (progress - line.delay) * 3));
            if (lineProgress > 0) {
                ctx.beginPath();
                ctx.moveTo(line.x1, line.y1);
                ctx.lineTo(
                    line.x1 + (line.x2 - line.x1) * lineProgress,
                    line.y1 + (line.y2 - line.y1) * lineProgress
                );
                ctx.stroke();
            }
        });
        
        // Draw main star
        if (progress > 0.2) {
            const mainProgress = Math.min(1, (progress - 0.2) * 2);
            this.drawIslamicStar(
                ctx,
                this.starAnimation.mainStar.x,
                this.starAnimation.mainStar.y,
                this.starAnimation.mainStar.radius * mainProgress,
                8,
                Date.now() * 0.0001,
                true
            );
        }
        
        // Draw smaller stars
        this.starAnimation.stars.forEach(star => {
            const starProgress = Math.max(0, Math.min(1, (progress - star.delay) * 2));
            if (starProgress > 0) {
                this.drawIslamicStar(
                    ctx,
                    star.x,
                    star.y,
                    star.radius * starProgress,
                    8,
                    -Date.now() * 0.0002,
                    false
                );
            }
        });
        
        // Draw center ornament
        if (progress > 0.5) {
            this.drawCenterOrnament(ctx, canvas.width / 2, canvas.height / 2, progress);
        }
        
        this.animationFrame = requestAnimationFrame(() => this.animateGeometricStar());
    }

    drawIslamicStar(ctx, x, y, radius, points, rotation, isMain) {
        const glowIntensity = this.starAnimation.glowIntensity;
        
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(rotation);
        
        // Outer glow
        if (isMain) {
            ctx.shadowBlur = 40;
            ctx.shadowColor = `rgba(201, 162, 39, ${0.6 * glowIntensity})`;
        } else {
            ctx.shadowBlur = 15;
            ctx.shadowColor = `rgba(255, 255, 255, ${0.4 * glowIntensity})`;
        }
        
        // Draw 8-pointed star
        ctx.beginPath();
        for (let i = 0; i < points * 2; i++) {
            const angle = (i * Math.PI) / points;
            const r = i % 2 === 0 ? radius : radius * 0.4;
            const px = Math.cos(angle) * r;
            const py = Math.sin(angle) * r;
            
            if (i === 0) {
                ctx.moveTo(px, py);
            } else {
                ctx.lineTo(px, py);
            }
        }
        ctx.closePath();
        
        // Fill and stroke
        if (isMain) {
            ctx.fillStyle = `rgba(201, 162, 39, ${0.05 * glowIntensity})`;
            ctx.strokeStyle = `rgba(201, 162, 39, ${0.8 * glowIntensity})`;
            ctx.lineWidth = 2;
        } else {
            ctx.fillStyle = `rgba(255, 255, 255, ${0.03 * glowIntensity})`;
            ctx.strokeStyle = `rgba(255, 255, 255, ${0.5 * glowIntensity})`;
            ctx.lineWidth = 1;
        }
        
        ctx.fill();
        ctx.stroke();
        
        // Inner detail
        ctx.beginPath();
        for (let i = 0; i < points; i++) {
            const angle = (i * Math.PI * 2) / points;
            const px = Math.cos(angle) * radius * 0.5;
            const py = Math.sin(angle) * radius * 0.5;
            
            if (i === 0) {
                ctx.moveTo(px, py);
            } else {
                ctx.lineTo(px, py);
            }
        }
        ctx.closePath();
        ctx.strokeStyle = isMain 
            ? `rgba(201, 162, 39, ${0.4 * glowIntensity})`
            : `rgba(255, 255, 255, ${0.3 * glowIntensity})`;
        ctx.lineWidth = 1;
        ctx.stroke();
        
        ctx.restore();
    }

    drawCenterOrnament(ctx, x, y, progress) {
        const ornamentProgress = Math.min(1, (progress - 0.5) * 2);
        const glowIntensity = this.starAnimation.glowIntensity;
        
        ctx.save();
        ctx.translate(x, y);
        
        // Glowing circle
        const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, 50 * ornamentProgress);
        gradient.addColorStop(0, `rgba(201, 162, 39, ${0.8 * glowIntensity * ornamentProgress})`);
        gradient.addColorStop(0.5, `rgba(201, 162, 39, ${0.3 * glowIntensity * ornamentProgress})`);
        gradient.addColorStop(1, 'rgba(201, 162, 39, 0)');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(0, 0, 50 * ornamentProgress, 0, Math.PI * 2);
        ctx.fill();
        
        // Inner star
        ctx.shadowBlur = 30;
        ctx.shadowColor = `rgba(201, 162, 39, ${glowIntensity})`;
        
        ctx.beginPath();
        for (let i = 0; i < 16; i++) {
            const angle = (i * Math.PI) / 8;
            const r = i % 2 === 0 ? 25 * ornamentProgress : 15 * ornamentProgress;
            const px = Math.cos(angle) * r;
            const py = Math.sin(angle) * r;
            
            if (i === 0) {
                ctx.moveTo(px, py);
            } else {
                ctx.lineTo(px, py);
            }
        }
        ctx.closePath();
        ctx.fillStyle = `rgba(201, 162, 39, ${glowIntensity * ornamentProgress})`;
        ctx.fill();
        
        ctx.restore();
    }

    /* =====================================================
       INK STROKE ANIMATIONS
       ===================================================== */
    initInkStrokes() {
        const heroSection = document.querySelector('.hero-section');
        if (!heroSection) return;
        
        const container = document.createElement('div');
        container.className = 'ink-strokes-container';
        container.innerHTML = this.generateInkStrokeSVG();
        heroSection.appendChild(container);
    }

    generateInkStrokeSVG() {
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        // Generate flowing Arabic-inspired strokes
        const strokes = [];
        const strokeCount = 12;
        
        for (let i = 0; i < strokeCount; i++) {
            const startX = Math.random() * width;
            const startY = Math.random() * height;
            const controlX1 = startX + (Math.random() - 0.5) * 300;
            const controlY1 = startY + (Math.random() - 0.5) * 200;
            const controlX2 = startX + (Math.random() - 0.5) * 400;
            const controlY2 = startY + (Math.random() - 0.5) * 300;
            const endX = startX + (Math.random() - 0.5) * 500;
            const endY = startY + (Math.random() - 0.5) * 400;
            
            const isGold = Math.random() > 0.7;
            const delay = i * 0.3;
            const duration = 3 + Math.random() * 2;
            
            strokes.push(`
                <path 
                    class="ink-stroke ${isGold ? 'gold' : ''}"
                    d="M ${startX} ${startY} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${endX} ${endY}"
                    style="
                        stroke-dasharray: 1000;
                        stroke-dashoffset: 1000;
                        animation: write-ink ${duration}s ease ${delay}s forwards;
                        opacity: ${0.2 + Math.random() * 0.3};
                    "
                />
            `);
        }
        
        return `
            <svg width="100%" height="100%" style="position: absolute; top: 0; left: 0;">
                <defs>
                    <style>
                        @keyframes write-ink {
                            to {
                                stroke-dashoffset: 0;
                            }
                        }
                    </style>
                </defs>
                ${strokes.join('')}
            </svg>
        `;
    }

    /* =====================================================
       RESIZE HANDLER
       ===================================================== */
    handleResize() {
        this.resizeCanvas();
        if (this.starAnimation) {
            this.starAnimation.lines = [];
            this.starAnimation.stars = [];
            this.generateStarPattern();
        }
    }

    /* =====================================================
       CLEANUP
       ===================================================== */
    destroy() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        
        document.body.classList.remove('living-scripture-theme');
        
        const particlesContainer = document.getElementById('particles-container');
        if (particlesContainer) particlesContainer.remove();
        
        const starCanvas = document.getElementById('geometric-star-canvas');
        if (starCanvas) starCanvas.remove();
        
        const inkContainer = document.querySelector('.ink-strokes-container');
        if (inkContainer) inkContainer.remove();
        
        this.isInitialized = false;
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.livingScriptureTheme = new LivingScriptureTheme();
    window.livingScriptureTheme.init();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LivingScriptureTheme;
}
