// Animation utilities for 60fps performance and smooth transitions

export interface AnimationConfig {
  duration: number;
  easing: string;
  delay?: number;
}

// Pre-defined animation configs optimized for 60fps
export const ANIMATION_CONFIGS = {
  // Fast transitions for UI feedback
  fast: {
    duration: 150,
    easing: 'ease-out'
  },
  // Standard transitions
  standard: {
    duration: 300,
    easing: 'ease-out'
  },
  // Smooth progress animations
  progress: {
    duration: 1500,
    easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)' // ease-out-quart
  },
  // Particle effects
  particle: {
    duration: 1000,
    easing: 'ease-out'
  },
  // Entrance animations
  entrance: {
    duration: 500,
    easing: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)' // ease-out-back
  }
} as const;

// Easing functions for JavaScript animations
export const EASING_FUNCTIONS = {
  linear: (t: number) => t,
  easeOut: (t: number) => 1 - Math.pow(1 - t, 2),
  easeOutQuart: (t: number) => 1 - Math.pow(1 - t, 4),
  easeOutBack: (t: number) => {
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
  }
} as const;

// RAF-based animation utility for smooth 60fps animations
export class AnimationFrame {
  private startTime: number | null = null;
  private animationId: number | null = null;
  private onComplete: (() => void) | null = null;

  constructor(
    private duration: number,
    private easing: (t: number) => number,
    private onUpdate: (progress: number) => void
  ) {}

  start(): void {
    this.startTime = performance.now();
    this.animate();
  }

  private animate = (): void => {
    if (this.startTime === null) return;

    const currentTime = performance.now();
    const elapsed = currentTime - this.startTime;
    const progress = Math.min(elapsed / this.duration, 1);
    
    const easedProgress = this.easing(progress);
    this.onUpdate(easedProgress);

    if (progress < 1) {
      this.animationId = requestAnimationFrame(this.animate);
    } else {
      this.onComplete?.();
      this.cleanup();
    }
  };

  setOnComplete(callback: () => void): void {
    this.onComplete = callback;
  }

  cancel(): void {
    this.cleanup();
  }

  private cleanup(): void {
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
    this.startTime = null;
    this.onComplete = null;
  }
}

// Particle system for celebration effects
export class ParticleSystem {
  private particles: Particle[] = [];
  private animationId: number | null = null;
  private container: HTMLElement | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  createParticle(x: number, y: number, color: string = '#fbbf24'): void {
    if (!this.container) return;

    const particle = document.createElement('div');
    particle.className = 'particle';
    particle.style.cssText = `
      position: absolute;
      width: 8px;
      height: 8px;
      background: ${color};
      border-radius: 50%;
      pointer-events: none;
      left: ${x}px;
      top: ${y}px;
      z-index: 1000;
    `;

    this.container.appendChild(particle);
    this.particles.push(new Particle(particle, x, y));
  }

  burst(count: number = 12, colors: string[] = ['#fbbf24', '#f59e0b', '#d97706']): void {
    if (!this.container) return;

    const rect = this.container.getBoundingClientRect();
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const color = colors[Math.floor(Math.random() * colors.length)];
      this.createParticle(centerX, centerY, color);
    }

    this.animate();
  }

  private animate = (): void => {
    const animate = () => {
      let activeParticles = 0;

      this.particles.forEach(particle => {
        if (particle.update()) {
          activeParticles++;
        }
      });

      // Remove dead particles
      this.particles = this.particles.filter(p => !p.isDead());

      if (activeParticles > 0 || this.particles.length > 0) {
        this.animationId = requestAnimationFrame(animate);
      } else {
        this.cleanup();
      }
    };

    animate();
  };

  cleanup(): void {
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }

    this.particles.forEach(particle => particle.destroy());
    this.particles = [];
  }
}

class Particle {
  private velocity = { x: 0, y: 0 };
  private gravity = 0.5;
  private friction = 0.98;
  private opacity = 1;
  private life = 1;

  constructor(
    private element: HTMLElement,
    private x: number,
    private y: number
  ) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 5 + Math.random() * 10;
    this.velocity.x = Math.cos(angle) * speed;
    this.velocity.y = Math.sin(angle) * speed - 5;
  }

  update(): boolean {
    this.velocity.y += this.gravity;
    this.velocity.x *= this.friction;
    this.velocity.y *= this.friction;

    this.x += this.velocity.x;
    this.y += this.velocity.y;

    this.life -= 0.02;
    this.opacity = Math.max(0, this.life);

    this.element.style.transform = `translate(${this.x}px, ${this.y}px)`;
    this.element.style.opacity = this.opacity.toString();

    return this.life > 0;
  }

  isDead(): boolean {
    return this.life <= 0;
  }

  destroy(): void {
    if (this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
  }
}

// Performance monitoring utilities
export class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private frameCount = 0;
  private lastTime = performance.now();
  private fps = 60;

  static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }

  update(): void {
    this.frameCount++;
    const currentTime = performance.now();
    
    if (currentTime - this.lastTime >= 1000) {
      this.fps = this.frameCount;
      this.frameCount = 0;
      this.lastTime = currentTime;
    }
  }

  getFPS(): number {
    return this.fps;
  }

  // Check if animations should be reduced for performance
  shouldReduceAnimations(): boolean {
    return this.fps < 45 || !this.isHighPerformanceDevice();
  }

  private isHighPerformanceDevice(): boolean {
    // Simple heuristic for device performance
    const navigator = window.navigator as any;
    const hardwareConcurrency = navigator.hardwareConcurrency || 4;
    const deviceMemory = navigator.deviceMemory || 4;
    
    return hardwareConcurrency >= 4 && deviceMemory >= 4;
  }
}

// Utility to check if reduced motion is preferred
export function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// Utility to create optimized CSS transitions
export function createOptimizedTransition(
  properties: string[],
  config: AnimationConfig = ANIMATION_CONFIGS.standard
): string {
  return properties
    .map(prop => `${prop} ${config.duration}ms ${config.easing}`)
    .join(', ');
}

// Utility to debounce rapid animations
export function debounceAnimation<T extends (...args: any[]) => any>(
  func: T,
  delay: number = 16 // ~60fps
): (...args: Parameters<T>) => void {
  let timeoutId: number;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay) as any;
  };
}
