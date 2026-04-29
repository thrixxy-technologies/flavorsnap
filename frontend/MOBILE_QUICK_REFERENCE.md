# Mobile Responsiveness Quick Reference

## 🎯 Quick Start

### Import Mobile Utilities

```tsx
// React Hook
import { useMobileResponsive } from '@/hooks/useMobileResponsive';

// Utility Functions
import { isMobileDevice, optimizeImageUrl } from '@/utils/mobileOptimization';
```

### Basic Usage

```tsx
function MyComponent() {
  const { isMobile, breakpoint } = useMobileResponsive();
  
  return (
    <div className="responsive-container">
      {isMobile ? <MobileView /> : <DesktopView />}
    </div>
  );
}
```

## 📱 Breakpoints

| Name | Min Width | Max Width | Device Type |
|------|-----------|-----------|-------------|
| xs   | 320px     | 639px     | Mobile phones |
| sm   | 640px     | 767px     | Large phones |
| md   | 768px     | 1023px    | Tablets |
| lg   | 1024px    | 1279px    | Small desktops |
| xl   | 1280px    | 1535px    | Desktops |
| 2xl  | 1536px+   | -         | Large desktops |

## 🎨 Common CSS Classes

### Touch Targets

```html
<!-- Minimum 44px touch target -->
<button class="touch-target">Click</button>

<!-- Comfortable 48px touch target -->
<button class="touch-target-comfortable">Primary Action</button>

<!-- Touch manipulation enabled -->
<button class="touch-manipulation">Tap Me</button>
```

### Responsive Containers

```html
<!-- Mobile-first container -->
<div class="responsive-container">Content</div>

<!-- Responsive card -->
<div class="card-responsive">Card content</div>
```

### Visibility

```html
<!-- Show only on mobile -->
<div class="mobile-only">Mobile content</div>

<!-- Hide on mobile -->
<div class="mobile-hidden">Desktop content</div>

<!-- Show only on desktop -->
<div class="desktop-only">Desktop content</div>
```

### Responsive Grid

```html
<!-- Auto-responsive grid (1 col mobile, 2 tablet, 3 desktop, 4 large) -->
<div class="grid-responsive">
  <div>Item 1</div>
  <div>Item 2</div>
  <div>Item 3</div>
</div>
```

## 🖼️ Responsive Images

### Basic Responsive Image

```tsx
<img 
  src="/image.jpg" 
  alt="Description"
  className="img-responsive"
  loading="lazy"
/>
```

### Optimized Image

```tsx
import { optimizeImageUrl } from '@/utils/mobileOptimization';

const optimizedSrc = optimizeImageUrl('/image.jpg', {
  width: 800,
  quality: 80,
  format: 'webp'
});

<img src={optimizedSrc} alt="Description" />
```

## 🎯 Touch-Friendly Buttons

### Minimum Requirements

```tsx
// ✅ Good - Meets 44px minimum
<button className="
  min-w-[44px] min-h-[44px]
  px-4 py-3
  touch-manipulation
">
  Click
</button>

// ❌ Bad - Too small
<button className="px-2 py-1 text-xs">
  Click
</button>
```

### Primary Action Button

```tsx
<button className="
  min-w-[48px] min-h-[48px]
  px-6 py-4
  touch-manipulation
  active:scale-95
  transition-transform
">
  Primary Action
</button>
```

## 📝 Forms

### Mobile-Friendly Input

```tsx
// Prevents iOS zoom with 16px font size
<input
  type="text"
  className="
    text-base
    min-h-[44px]
    px-4 py-3
    rounded-lg
  "
  placeholder="Enter text"
/>
```

### Select Dropdown

```tsx
<select className="
  text-base
  min-h-[44px]
  px-4 py-3
  rounded-lg
  appearance-none
">
  <option>Option 1</option>
  <option>Option 2</option>
</select>
```

## 🎭 Responsive Typography

### Using Tailwind Classes

```tsx
// Responsive heading
<h1 className="
  text-2xl sm:text-3xl md:text-4xl lg:text-5xl
  font-bold
">
  Heading
</h1>

// Responsive body text
<p className="
  text-sm sm:text-base md:text-lg
  leading-relaxed
">
  Body text
</p>
```

### Using Custom Classes

```tsx
<h1 className="heading-responsive-xl">Extra Large Heading</h1>
<h2 className="heading-responsive-lg">Large Heading</h2>
<h3 className="heading-responsive-md">Medium Heading</h3>
<p className="text-responsive">Body text</p>
```

## 🎨 Responsive Layout

### Mobile-First Grid

```tsx
<div className="
  grid
  grid-cols-1
  sm:grid-cols-2
  md:grid-cols-3
  lg:grid-cols-4
  gap-4 sm:gap-6 lg:gap-8
">
  <div>Item 1</div>
  <div>Item 2</div>
  <div>Item 3</div>
  <div>Item 4</div>
</div>
```

### Responsive Padding

```tsx
<div className="
  p-4 sm:p-6 md:p-8 lg:p-10
">
  Content with responsive padding
</div>
```

### Responsive Flex

```tsx
<div className="
  flex
  flex-col sm:flex-row
  gap-4 sm:gap-6
  items-center sm:items-start
">
  <div>Item 1</div>
  <div>Item 2</div>
</div>
```

## 🎣 React Hooks

### useMobileResponsive

```tsx
const {
  isMobile,      // boolean
  isTablet,      // boolean
  isTouch,       // boolean
  isLandscape,   // boolean
  viewport,      // { width, height }
  breakpoint     // 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl'
} = useMobileResponsive();
```

### useBreakpoint

```tsx
const isMobile = useBreakpoint('xs');
const isTablet = useBreakpoint('md');
```

### useMinBreakpoint

```tsx
const isTabletOrLarger = useMinBreakpoint('md');
const isDesktop = useMinBreakpoint('lg');
```

### useTouchGestures

```tsx
const elementRef = useRef<HTMLDivElement>(null);

useTouchGestures(elementRef, {
  onSwipeLeft: () => console.log('Swiped left'),
  onSwipeRight: () => console.log('Swiped right'),
  onTap: () => console.log('Tapped'),
});

<div ref={elementRef}>Swipeable content</div>
```

### useBodyScrollLock

```tsx
const [isModalOpen, setIsModalOpen] = useState(false);
useBodyScrollLock(isModalOpen);
```

### useOrientation

```tsx
const orientation = useOrientation(); // 'portrait' | 'landscape'
```

### useNetworkStatus

```tsx
const { isOnline, connectionType, isSlowConnection } = useNetworkStatus();
```

## 🛠️ Utility Functions

### Device Detection

```tsx
import {
  isMobileDevice,
  isTabletDevice,
  isTouchDevice,
  isLandscape,
  isPortrait
} from '@/utils/mobileOptimization';

if (isMobileDevice()) {
  // Mobile-specific code
}
```

### Viewport

```tsx
import { getViewportSize } from '@/utils/mobileOptimization';

const { width, height } = getViewportSize();
```

### Image Optimization

```tsx
import { 
  getOptimalImageSize,
  optimizeImageUrl 
} from '@/utils/mobileOptimization';

const { width, height } = getOptimalImageSize(1920, 1080);
const optimizedUrl = optimizeImageUrl(url, { width: 800, quality: 80 });
```

### Performance

```tsx
import { debounce, throttle } from '@/utils/mobileOptimization';

const debouncedSearch = debounce(searchFunction, 300);
const throttledScroll = throttle(scrollHandler, 100);
```

### Body Scroll

```tsx
import { preventBodyScroll } from '@/utils/mobileOptimization';

// Lock scroll
preventBodyScroll(true);

// Unlock scroll
preventBodyScroll(false);
```

## 🎯 Common Patterns

### Responsive Modal

```tsx
<div className="modal-mobile">
  <div className="modal-content">
    <h2>Modal Title</h2>
    <p>Modal content</p>
  </div>
</div>
```

### Mobile Navigation

```tsx
const [isMenuOpen, setIsMenuOpen] = useState(false);

<>
  {/* Hamburger Button */}
  <button 
    className="hamburger"
    onClick={() => setIsMenuOpen(!isMenuOpen)}
  >
    <span></span>
    <span></span>
    <span></span>
  </button>

  {/* Mobile Menu */}
  <div className={`mobile-menu ${isMenuOpen ? 'open' : ''}`}>
    <nav>
      <a href="/">Home</a>
      <a href="/about">About</a>
    </nav>
  </div>

  {/* Overlay */}
  <div 
    className={`mobile-menu-overlay ${isMenuOpen ? 'open' : ''}`}
    onClick={() => setIsMenuOpen(false)}
  />
</>
```

### Responsive Card

```tsx
<div className="card-responsive">
  <img src="/image.jpg" alt="Card" className="img-responsive" />
  <h3 className="heading-responsive-md">Card Title</h3>
  <p className="text-responsive">Card description</p>
  <button className="touch-target">Action</button>
</div>
```

## ⚡ Performance Tips

1. **Use lazy loading for images**
   ```tsx
   <img loading="lazy" src="/image.jpg" alt="Description" />
   ```

2. **Debounce resize events**
   ```tsx
   const handleResize = debounce(() => {
     // Resize logic
   }, 150);
   ```

3. **Use CSS transforms for animations**
   ```css
   .animated {
     transform: translateX(0);
     transition: transform 0.3s ease;
   }
   ```

4. **Optimize images for mobile**
   ```tsx
   const optimizedSrc = optimizeImageUrl(src, {
     width: viewport.width,
     quality: 80,
     format: 'webp'
   });
   ```

## ✅ Checklist

- [ ] All buttons are at least 44x44px
- [ ] Form inputs use 16px font size minimum
- [ ] Images are responsive and lazy-loaded
- [ ] Layout works on all breakpoints
- [ ] Touch interactions feel natural
- [ ] Text is readable at all sizes
- [ ] Navigation works on mobile
- [ ] Modals are mobile-friendly
- [ ] Performance is optimized
- [ ] Accessibility is maintained

## 🐛 Common Issues

### Issue: iOS Zoom on Input Focus

**Solution**: Use 16px minimum font size
```css
input { font-size: 16px; }
```

### Issue: Buttons Too Small on Mobile

**Solution**: Use minimum 44px touch targets
```css
button { min-width: 44px; min-height: 44px; }
```

### Issue: Images Not Responsive

**Solution**: Use responsive image classes
```css
img { max-width: 100%; height: auto; }
```

### Issue: Layout Breaks on Small Screens

**Solution**: Use mobile-first approach
```css
/* Mobile first */
.element { padding: 1rem; }

/* Then enhance for larger screens */
@media (min-width: 640px) {
  .element { padding: 2rem; }
}
```

## 📚 Resources

- [Full Documentation](./MOBILE_RESPONSIVENESS.md)
- [Tailwind Responsive Design](https://tailwindcss.com/docs/responsive-design)
- [WCAG Touch Target Guidelines](https://www.w3.org/WAI/WCAG21/Understanding/target-size.html)

---

**Quick Reference Version**: 1.0.0  
**Last Updated**: April 27, 2026
