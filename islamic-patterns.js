/* =====================================================
   الشيخ أحمد إسماعيل الفشني - Islamic Geometric Patterns
   Canvas-based Dynamic Islamic Art Generator
   ===================================================== */

class IslamicPatternGenerator {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.patterns = [];
        this.animationId = null;
        this.time = 0;
        
        // Islamic pattern colors
        this.colors = {
            gold: '#c9a227',
            goldLight: '#e8d48b',
            green: '#1a5f4a',
            greenLight: '#2d8b6f',
            white: 'rgba(255, 255, 255, 0.1)'
        };
        
        this.init();
    }
    
    init() {
        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.createPatterns();
        this.animate();
    }
    
    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }
    
    createPatterns() {
        const patternCount = Math.floor((this.canvas.width * this.canvas.height) / 50000);
        
        for (let i = 0; i < patternCount; i++) {
            this.patterns.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                size: Math.random() * 30 + 20,
                rotation: Math.random() * Math.PI * 2,
                rotationSpeed: (Math.random() - 0.5) * 0.005,
                type: Math.floor(Math.random() * 4),
                opacity: Math.random() * 0.3 + 0.1,
                pulseOffset: Math.random() * Math.PI * 2
            });
        }
    }
    
    drawEightPointStar(x, y, size, rotation) {
        this.ctx.save();
        this.ctx.translate(x, y);
        this.ctx.rotate(rotation);
        
        this.ctx.beginPath();
        for (let i = 0; i < 8; i++) {
            const angle = (i * Math.PI) / 4;
            const outerX = Math.cos(angle) * size;
            const outerY = Math.sin(angle) * size;
            const innerAngle = angle + Math.PI / 8;
            const innerX = Math.cos(innerAngle) * (size * 0.4);
            const innerY = Math.sin(innerAngle) * (size * 0.4);
            
            if (i === 0) {
                this.ctx.moveTo(outerX, outerY);
            } else {
                this.ctx.lineTo(outerX, outerY);
            }
            this.ctx.lineTo(innerX, innerY);
        }
        this.ctx.closePath();
        this.ctx.stroke();
        
        this.ctx.restore();
    }
    
    drawHexagon(x, y, size, rotation) {
        this.ctx.save();
        this.ctx.translate(x, y);
        this.ctx.rotate(rotation);
        
        this.ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle = (i * Math.PI) / 3;
            const px = Math.cos(angle) * size;
            const py = Math.sin(angle) * size;
            
            if (i === 0) {
                this.ctx.moveTo(px, py);
            } else {
                this.ctx.lineTo(px, py);
            }
        }
        this.ctx.closePath();
        this.ctx.stroke();
        
        // Inner hexagon
        this.ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle = (i * Math.PI) / 3 + Math.PI / 6;
            const px = Math.cos(angle) * (size * 0.5);
            const py = Math.sin(angle) * (size * 0.5);
            
            if (i === 0) {
                this.ctx.moveTo(px, py);
            } else {
                this.ctx.lineTo(px, py);
            }
        }
        this.ctx.closePath();
        this.ctx.stroke();
        
        this.ctx.restore();
    }
    
    drawArabesque(x, y, size, rotation) {
        this.ctx.save();
        this.ctx.translate(x, y);
        this.ctx.rotate(rotation);
        
        // Draw interlocking circles pattern
        const radius = size * 0.4;
        
        for (let i = 0; i < 4; i++) {
            const angle = (i * Math.PI) / 2;
            const cx = Math.cos(angle) * radius;
            const cy = Math.sin(angle) * radius;
            
            this.ctx.beginPath();
            this.ctx.arc(cx, cy, radius, 0, Math.PI * 2);
            this.ctx.stroke();
        }
        
        // Center circle
        this.ctx.beginPath();
        this.ctx.arc(0, 0, radius * 0.5, 0, Math.PI * 2);
        this.ctx.stroke();
        
        this.ctx.restore();
    }
    
    drawGeometricFlower(x, y, size, rotation) {
        this.ctx.save();
        this.ctx.translate(x, y);
        this.ctx.rotate(rotation);
        
        // Outer petals
        for (let i = 0; i < 8; i++) {
            const angle = (i * Math.PI) / 4;
            
            this.ctx.save();
            this.ctx.rotate(angle);
            
            this.ctx.beginPath();
            this.ctx.moveTo(0, 0);
            this.ctx.quadraticCurveTo(size * 0.3, -size * 0.2, size * 0.8, 0);
            this.ctx.quadraticCurveTo(size * 0.3, size * 0.2, 0, 0);
            this.ctx.stroke();
            
            this.ctx.restore();
        }
        
        // Center
        this.ctx.beginPath();
        this.ctx.arc(0, 0, size * 0.15, 0, Math.PI * 2);
        this.ctx.stroke();
        
        this.ctx.restore();
    }
    
    drawPattern(pattern) {
        const pulse = Math.sin(this.time * 0.002 + pattern.pulseOffset) * 0.2 + 0.8;
        
        this.ctx.strokeStyle = this.colors.gold;
        this.ctx.lineWidth = 1;
        this.ctx.globalAlpha = pattern.opacity * pulse;
        
        switch (pattern.type) {
            case 0:
                this.drawEightPointStar(pattern.x, pattern.y, pattern.size, pattern.rotation);
                break;
            case 1:
                this.drawHexagon(pattern.x, pattern.y, pattern.size, pattern.rotation);
                break;
            case 2:
                this.drawArabesque(pattern.x, pattern.y, pattern.size, pattern.rotation);
                break;
            case 3:
                this.drawGeometricFlower(pattern.x, pattern.y, pattern.size, pattern.rotation);
                break;
        }
    }
    
    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.patterns.forEach(pattern => {
            pattern.rotation += pattern.rotationSpeed;
            this.drawPattern(pattern);
        });
        
        this.time++;
        this.animationId = requestAnimationFrame(() => this.animate());
    }
    
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        window.removeEventListener('resize', this.resize);
    }
}

// Star field background effect
class StarField {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.stars = [];
        this.init();
    }
    
    init() {
        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.createStars();
        this.animate();
    }
    
    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.createStars();
    }
    
    createStars() {
        this.stars = [];
        const starCount = Math.floor((this.canvas.width * this.canvas.height) / 10000);
        
        for (let i = 0; i < starCount; i++) {
            this.stars.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                size: Math.random() * 2 + 0.5,
                opacity: Math.random() * 0.5 + 0.2,
                twinkleSpeed: Math.random() * 0.02 + 0.01,
                twinkleOffset: Math.random() * Math.PI * 2
            });
        }
    }
    
    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        const time = Date.now() * 0.001;
        
        this.stars.forEach(star => {
            const twinkle = Math.sin(time * star.twinkleSpeed + star.twinkleOffset) * 0.3 + 0.7;
            
            this.ctx.beginPath();
            this.ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(201, 162, 39, ${star.opacity * twinkle})`;
            this.ctx.fill();
        });
        
        requestAnimationFrame(() => this.animate());
    }
}

// DISABLED - Star pattern no longer used, replaced with CSS crescent moons
// Initialize Islamic pattern on canvas
document.addEventListener('DOMContentLoaded', () => {
    // Pattern canvas disabled - using CSS floating moons instead
    // const patternCanvas = document.getElementById('islamicPatternCanvas');
    // if (patternCanvas) {
    //     new IslamicPatternGenerator(patternCanvas);
    // }
    console.log('Islamic patterns: Using CSS crescent moons instead of canvas stars');
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { IslamicPatternGenerator, StarField };
}
