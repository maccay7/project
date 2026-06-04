
# Word Document Fixes – Paste into Your Thesis

Open `Makanaka Kanyai Project Documentation (2).docx` and replace the sections below so the report matches the **running prototype** (Flask + Vue + MySQL + FRED).

---

## Chapter 5 – Section 5.2 (Implementation)

**DELETE / REPLACE** paragraphs that say:

> developed using the **Django** framework …  
> Installation of **Django** …  
> Configuration of the **PostgreSQL** database …

**REPLACE WITH:**

> The Automation of Financial Instruments Valuation System was implemented using **Python (Flask)** for the REST API, **Vue 3 with Vite** for the presentation layer, and **MySQL** for persistent storage. Market benchmark rates are retrieved from the **Federal Reserve Economic Data (FRED) API** to support valuation comparisons in calculations, visualizations, and exported reports.

---

## Chapter 5 – Section 5.9 (Deployment)

**REPLACE deployment steps with:**

1. Install Python 3 and Node.js.  
2. Create MySQL database `duracapital` and import schema from `database_schema.sql`.  
3. Configure `backend/.env` (DB credentials, `FRED_API_KEY`, `JWT_SECRET_KEY`).  
4. Backend: `cd backend` → `pip install -r requirements.txt` → `python app.py` (port 5000).  
5. Frontend: `cd frontend` → `npm install` → `npm run dev` (port 3001).  
6. Verify `/api/health` and login; run `pytest` in `backend/tests`.

---

## Chapter 5 – Section 5.11 (Summary)

**REPLACE** “Django” and “PostgreSQL” with **Flask**, **Vue 3**, **MySQL**, and **FRED API**.

---

## Chapter 3 – Add functional requirement (one bullet)

> The system shall fetch US Treasury benchmark rates from FRED and display spreads against portfolio-calculated yields on the Calculations and Visualizations pages.

---

## Chapter 4 – Section 4.3 (Interface)

**ADD** after wireframes paragraph:

> Visualization screens include filters for **country/region** (US, UK, Germany, Euro Area, Japan, Canada, Australia, South Africa, Brazil, India, Mexico, China), **currency** (auto-matched per country), and **benchmark maturity**. US uses full Treasury maturities (3M–30Y); other countries use long-term government bond yields available on FRED (typically 10Y).

---

## Abstract (short addition)

**ADD one sentence:**

> Live market benchmarks from FRED are integrated to compare portfolio yields against US Treasury rates.

---

## Fig 4.3.5 caption

Guidelines list “Reports” then “Visualizations”. Your doc uses Visualizations as 4.3.6 — either order is fine; keep figure numbers consistent with screenshots you insert.

---

## Screenshots to capture for Chapter 5

| Figure | Screenshot |
|--------|------------|
| 5.1 | Dashboard with KPIs |
| 5.2 | Treasury Bills – calculations + FRED benchmark |
| 5.3 | Money Market – visualizations with chart + filters |
| 5.4 | Bonds – calculations |
| 5.5–5.6 | Login success |
| 5.8 | Terminal: `pytest backend/tests` |
| 5.9–5.10 | Postman: `/api/fred/benchmark` and `/api/calculate` |

---

## What FRED does in your system (for viva)

1. **Calculations** – Fetches latest Treasury rate for selected maturity; shows **spread vs portfolio**.  
2. **Visualizations** – Time-series chart + multi-maturity yield curve.  
3. **Reports** – Embeds FRED charts in HTML downloads.  

FRED does **not** replace your Excel valuation formulas; it provides the **market reference rate**.
