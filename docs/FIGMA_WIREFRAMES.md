# Figma Wireframes – DuraCapital (beginner steps)

## 1. Set up Figma

1. Open [figma.com](https://figma.com) → **New design file**.
2. Press **F** (frame tool) → pick **Desktop** → **1440 × 1024**.
3. **Design** panel → create colour style **Primary** = `#0B2044`.
4. **Text** style: **Heading** 24px bold `#0B2044`, **Body** 14px `#333`.

## 2. Reusable components (make once, reuse)

| Component | Size | Notes |
|-----------|------|--------|
| `Sidebar` | 256 × 1024 | Fill `#0B2044`, white links, logo top |
| `KPI Card` | flex, height **120px** | Icon 56×56 left, value 24px, label 14px grey |
| `Primary Button` | auto × 40px | Fill `#0B2044`, white text, radius 8px |
| `Chart Placeholder` | 100% × 320px | Grey box + title “Yield Curve (FRED)” |

Duplicate the frame for each page below and swap only the main content.

## 3. Frames for your thesis (Fig 4.3)

| Frame name | What to draw |
|------------|----------------|
| `4.3 Login` | Logo, email, password, Remember me, Register link |
| `4.3.1 Dashboard` | Sidebar + 4 KPIs + 2 chart areas + quick actions |
| `4.3.2 Upload` | Drop zone, saved datasets list, Excel table preview |
| `4.3.3 Cleaning` | 4 KPIs, checkboxes (duplicates, nulls…), Proceed |
| `4.3.4 Calculations` | 4 KPIs, result cards from API |
| `4.3.5 Visualizations` | Instrument dropdown, **yield curve chart**, **3-line comparison chart** |
| `4.3.6 Reports` | Excel preview, export buttons, report preview area |
| `4.3.7 Settings` | Profile, preferences, notifications |

## 4. Visualizations frame (WRL Fig 4.3.5 / 4.3.6)

- **Filters row:** Country (US) | Currency (USD) | Maturity (3M–30Y) | Instrument
- **Chart 1:** “Yield Curve (FRED API)” – one or three lines
- **Chart 2:** “Instrument Comparison” – TB / Bonds / Money Market
- **Calculations frame:** FRED benchmark card + spread vs portfolio

## 5. Instrument workflow frames (Money Market / Bonds / T-Bills)

Same filter row on Visualizations tab; calculations tab shows FRED benchmark strip.

## 5. Export for Word

1. Select frame → right panel **Export** → PNG **2x**.
2. In Word, replace old wireframe images under **Figure 4.3.x**.
3. Caption example: *Fig 4.3.5 Visualizations screen wireframe (Figma).*

## 6. Prototype (optional)

Link sidebar items: Dashboard → Upload → Cleaning → … so your demo video looks like a real app.

---

**Live app colours:** sidebar and buttons `#0B2044`. Match Figma to the running Vue app for consistent thesis screenshots.
