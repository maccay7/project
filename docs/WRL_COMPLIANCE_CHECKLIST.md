# WRL Compliance Checklist – DuraCapital

Use this with:
- **Guidelines:** `06_New_ WRL Project System Manual Guidelines - Copy.pdf`
- **Defense rubric:** `07_WRL Project-System Prototype Defense - Level 3-2.pdf`
- **Your report:** `Makanaka Kanyai Project Documentation (2).docx`

## Document structure (required chapters)

| Chapter | Required content | Your project status |
|---------|------------------|---------------------|
| 1 Introduction | Background, problem, SMART objectives | In docx |
| 2 Planning | Feasibility, risk, Gantt | In docx |
| 3 Analysis | Current system diagrams (≥2), weaknesses, requirements | In docx – verify diagrams exist |
| 4 Design | Proposed diagrams (≥2), EER, **Figma wireframes** | Flask+Vue+MySQL in §4.1; Figma in `docs/FIGMA_WIREFRAMES.md` |
| 5 Implementation | Screenshots, **pytest**, Postman, JMeter | **Fix Django/PostgreSQL text** (see `DOCUMENTATION_FIXES_FOR_WORD.md`) |
| 6 Conclusion | Summary + recommendations | In docx |
| Appendix | User manual | Add short login → report steps |

**Limit:** Report ≤ 50 pages. Font: headings 14pt bold TNR; body 12pt, 1.5 spacing.

## Prototype defense rubric (Level 3)

| Criterion | What assessors check | Your system |
|-----------|----------------------|-------------|
| UI/UX | Intuitive, consistent, appealing | Vue 3 + `#0B2044`, sidebar workflow |
| Functionality | Upload → clean → calculate → visualize → report | All routes in `project/backend` |
| Code quality | Readable, modular | `pages/*_details.py` + `routes/*.py` |
| Testing | pytest, Postman, validation | `backend/tests/test_fred_config.py` + manual tables in Ch.5 |
| Security | Auth, validation | JWT login, input checks on upload |
| FRED / market data | External benchmark | Calculations + visuals + reports |

## Tech stack (must match report and demo)

| Layer | **Actual build** | **Wrong in docx Ch.5 (fix)** |
|-------|------------------|------------------------------|
| Frontend | Vue 3 + Vite (port 3001) | OK in Ch.4 |
| Backend | **Flask** (port 5000) | Says **Django** |
| Database | **MySQL** (`duracapital`) | Says **PostgreSQL** |
| Wireframes | **Figma** | OK |
| Market data | **FRED API** | Add one sentence in Ch.5 |

## Diagrams minimum (Ch.3 & Ch.4)

- [ ] Context diagram (current + proposed)
- [ ] At least **2** DFDs OR use case + sequence
- [ ] Activity diagram (workflow)
- [ ] EER from MySQL Workbench (Fig 4.2)
- [ ] Figma screens Fig 4.3 – 4.3.7

## Demo script (5 minutes)

1. Login → Dashboard KPIs  
2. Upload Excel → Cleaning → **Calculations** (show FRED benchmark card)  
3. **Visualizations** (filters: Country, Currency, Maturity + charts)  
4. **Reports** → Download HTML with charts  
5. Mention pytest + Postman tests in Ch.5  

## Tools to show proficiency (one per phase)

| Phase | Tool used |
|-------|-----------|
| Planning | MS Project / Excel Gantt |
| Analysis | draw.io / Lucidchart |
| Design | Figma + MySQL Workbench |
| Implementation | VS Code, Flask, Vue |
| Testing | pytest, Postman, JMeter |
