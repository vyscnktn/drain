# Drain Brand Guidelines

**Version:** 1.0  
**Last updated:** August 2026  
**Purpose:** This document defines the visual and verbal identity of Drain for consistent application across all touchpoints.

---

## 1. Brand Foundation

### Positioning Statement
For healthcare professionals (Pflege) and IT specialists in Germany who need to pass the Fachsprachenprüfung or advance their careers, Drain is a personalized comprehensible input engine that delivers meaningful, level-appropriate German texts daily. Unlike traditional language apps that rely on memorization or generic content, Drain builds a portable "Digital Brain" of vocabulary mastery that users own and can export anytime.

### Brand Personality
- **Precise, not pedantic** — we respect the user's time and intelligence
- **Supportive, not paternalistic** — we are a coach, not a teacher
- **Scientific, not academic** — evidence-based but jargon-free in user-facing copy
- **Quietly confident** — we let results speak, no hype or gamification overload

### Core Message
**Primary tagline:** "Meaningful input for faster learning."  
**Secondary tagline:** "Personalized comprehensible input."  
**Forbidden in user-facing copy:** Krashen, i+1, Comprehensible Input theory, acquisition vs. learning distinction.

---

## 2. Logo System

### Primary Logo
- **Wordmark:** lowercase "drain" in custom geometric sans-serif
- **Icon:** funnel/droplet shape branching into 3-4 neural nodes (represents filtering → knowledge network)

### Logo Variations
- **Primary:** Icon + wordmark (horizontal lockup)
- **Icon-only:** For app icons, favicons, social avatars (minimum 32px)
- **Monochrome:** White version for dark backgrounds, black version for light backgrounds

### Clear Space
- Minimum clear space around logo = height of the "d" in the wordmark

### Incorrect Usage
- Never stretch, rotate, or add effects (shadows, gradients)
- Never change the teal color to any other hue
- Never place the icon without sufficient contrast on busy backgrounds

---

## 3. Color Palette

### Primary Colors
| Role | Name | HEX | RGB | Usage |
|------|------|-----|-----|-------|
| Primary | Deep Teal | `#1A6E6E` | 26, 110, 110 | Logo, primary CTAs, key UI elements |
| Primary Hover | Dark Teal | `#0F4C4C` | 15, 76, 76 | Button hover states |
| Background Light | Off-White | `#F7F6F2` | 247, 246, 242 | Light mode background |
| Background Dark | Charcoal | `#171614` | 23, 22, 20 | Dark mode background |

### Semantic Colors
| Role | Name | HEX | Usage |
|------|------|-----|-------|
| Success | Gridania Green | `#437A22` | Completion, mastery achieved |
| Warning | Terra Brown | `#964219` | Streak at risk, attention needed |
| Error | Jenova Maroon | `#A12C7B` | Destructive actions, failures |
| Info | Limsa Blue | `#006494` | Notifications, tips |

### Neutral Scale
- Text Primary: `#28251D` (light) / `#CDCCCA` (dark)
- Text Muted: `#7A7974` (light) / `#797876` (dark)
- Surface: `#F9F8F5` (light) / `#1C1B19` (dark)

### Accessibility
- All text meets WCAG 2.1 AA contrast ratios (4.5:1 minimum)
- Primary teal on white: 4.6:1 (passes)
- White on primary teal: 4.6:1 (passes)

---

## 4. Typography

### Font Families
- **Display/Headings:** Satoshi (Fontshare) — geometric, modern, distinctive
- **Body/UI:** Inter (Google Fonts) — highly legible, excellent x-height
- **Fallback stack:** `system-ui, -apple-system, sans-serif`

### Type Scale
| Element | Size | Weight | Line Height | Usage |
|---------|------|--------|-------------|-------|
| Hero | 48-56px | 700 (Bold) | 1.1 | Landing page headline only |
| Page Title | 32-36px | 700 | 1.2 | Section headers |
| Section Heading | 24px | 600 (Semibold) | 1.3 | Feature headings |
| Body Large | 18px | 400 (Regular) | 1.6 | Intro paragraphs |
| Body | 16px | 400 | 1.6 | Standard text, UI labels |
| Body Small | 14px | 400 | 1.5 | Buttons, form inputs |
| Caption | 12px | 500 (Medium) | 1.4 | Timestamps, metadata |

### Rules
- Never use display font below 24px
- Body text minimum 16px for readability
- All caps only for short labels (max 3-4 words)

---

## 5. Voice & Tone

### Brand Voice
- **Direct:** Short sentences. No filler words.
- **Precise:** Use exact numbers when possible ("1 new word per text" not "a few new words")
- **Warm but professional:** Friendly without being casual, expert without being cold

### Tone by Context
| Context | Tone | Example |
|---------|------|---------|
| Landing page | Confident, benefit-focused | "Learn professional German, exactly at your level." |
| Onboarding | Encouraging, clear | "Let's find your starting point." |
| Error states | Helpful, not blaming | "That didn't work. Try again?" |
| Success states | Celebratory, brief | "Done. 1 new word mastered." |
| Export/download | Empowering | "Your Digital Brain is ready. It's yours." |

### Vocabulary Rules
- **Say:** "learn," "practice," "master," "your level"
- **Don't say:** "acquire," "comprehensible input," "i+1," "Krashen," "pedagogy"
- **Say:** "Digital Brain" or "vocabulary network"
- **Don't say:** "knowledge graph" (too technical for users)

---

## 6. Imagery & Iconography

### Photography Style
- Real people in real work settings (hospitals, offices)
- Natural lighting, not staged
- Diverse representation (age, gender, ethnicity)
- No stock photo clichés (handshakes, pointing at screens)

### Iconography
- **Style:** Monoline, consistent stroke weight (2px at 24px size)
- **Metaphors:** Funnel (filtering), nodes/network (Digital Brain), document (export)
- **Library:** Lucide Icons preferred; custom icons follow same stroke weight

### Illustration
- Minimal, geometric shapes only
- Limited color palette (primary teal + neutrals)
- No characters or mascots

---

## 7. Brand in Product

### UI Component Guidelines
- **Buttons:** Primary = Deep Teal background, white text, 14px medium weight, 8px border-radius
- **Cards:** Surface background, 1px border (10% opacity), 12px border-radius
- **Inputs:** 16px font size (prevents iOS zoom), 12px border-radius, focus ring = primary teal

### Motion
- **Duration:** 200ms for micro-interactions, 400ms for page transitions
- **Easing:** `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out-expo)
- **Reduce motion:** Respect `prefers-reduced-motion` — disable animations

### Dark Mode
- Full parity with light mode
- Surface elevation via lighter backgrounds, not shadows
- Primary teal lightens to `#4F98A3` for sufficient contrast

---

## 8. Application Examples

### Landing Page
- Hero: Display font, 48px, Deep Teal headline
- CTA: Primary button style, "7 gün ücretsiz dene" / "Start free trial"
- Feature grid: 3 columns on desktop, 1 column on mobile

### Email
- Subject lines: 50 characters max, no clickbait
- Body: Body font, 16px, single column, plenty of whitespace

### Social Media
- Avatar: Icon-only version, centered, clear space maintained
- Cover images: Minimal, brand colors only, no text overlay unless essential

---

## 9. Governance

### File Formats
- **Logo:** SVG (vector), PNG (raster, 2x and 3x for retina)
- **Fonts:** WOFF2 for web, TTF for desktop
- **Colors:** Design tokens exported as CSS variables, JSON, and Figma styles

### Contact
For brand questions or asset requests: [brand@drainmind.com]

---

*This document is a living system. Update it as the brand evolves.*
