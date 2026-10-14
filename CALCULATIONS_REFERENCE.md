# Financial Instrument Calculations Reference

This document provides a comprehensive reference for all calculations performed by the system, including formulas, required fields, field synonyms, and validation rules for each instrument type.

---

## Table of Contents
1. [Money Market Instruments](#money-market-instruments)
2. [Treasury Bills (T-Bills)](#treasury-bills-t-bills)
3. [Bonds](#bonds)
4. [Field Name Aliases (Synonyms)](#field-name-aliases-synonyms)
5. [Day Count Conventions](#day-count-conventions)
6. [Validation Rules](#validation-rules)

---

## Money Market Instruments

### Required Fields
- **principal** (or face_value, amount)
- **interest_rate** (or rate)
- **term_days** (or days_to_maturity)
  - Alternatively: valuation_date + maturity_date
  - Alternatively: issue_date + maturity_date

### Optional Fields
- **market_value** - Current market value if available
- **day_count_convention** - Day count basis (default: ACT/360)
- **currency** - Instrument currency
- **valuation_date** - Date for valuation
- **maturity_date** - Maturity date
- **issue_date** - Issue date

### Calculations

#### 1. Interest Earned
**Formula**: `principal × interest_rate × (term_days / day_count_divisor)`

**Description**: Simple interest calculated using the day count convention.

**Precision**: 2 decimal places (monetary)

**Example**:
- Principal: 100,000
- Interest Rate: 5% (0.05)
- Term Days: 90
- Day Count: ACT/360 (divisor = 360)
- Interest = 100,000 × 0.05 × (90/360) = 1,250.00

---

#### 2. Total Value (Maturity Value)
**Formula**: `principal + interest_earned`

**Description**: Principal plus accrued interest at maturity.

**Precision**: 2 decimal places (monetary)

**Example**:
- Principal: 100,000
- Interest Earned: 1,250
- Total Value = 101,250.00

---

#### 3. Discount Yield
**Formula**: `(interest_earned / total_value) × (day_count_divisor / term_days) × 100`

**Description**: Money market yield using the same day count convention as interest calculation.

**Precision**: 4 decimal places (percentage)

**Example**:
- Interest Earned: 1,250
- Total Value: 101,250
- Term Days: 90
- Day Count: ACT/360 (divisor = 360)
- Discount Yield = (1,250 / 101,250) × (360/90) × 100 = 4.9383%

---

#### 4. Effective Yield
**Formula**: `(interest_earned / principal) × (365 / term_days) × 100`

**Description**: Annualized yield using actual/actual (365-day) basis.

**Precision**: 4 decimal places (percentage)

**Example**:
- Interest Earned: 1,250
- Principal: 100,000
- Term Days: 90
- Effective Yield = (1,250 / 100,000) × (365/90) × 100 = 5.0694%

---

#### 5. Bond Equivalent Yield
**Formula**: `(interest_earned / principal) × (365 / term_days) × 100`

**Description**: Bond equivalent yield using 365-day basis (same as effective yield for money market).

**Precision**: 4 decimal places (percentage)

**Example**:
- Same as Effective Yield: 5.0694%

---

#### 6. Yield Curve Rate (Benchmark)
**Formula**: FRED benchmark rate (if available)

**Description**: External benchmark rate from FRED for comparison.

**Precision**: 4 decimal places (percentage)

---

### Aggregations (Multi-Instrument)
- **total_principal**: Sum of all principal values
- **total_interest**: Sum of all interest_earned values
- **total_value**: Sum of all total_value values
- **weighted_avg_rate**: Weighted average of interest rates (by principal)
- **avg_days_to_maturity**: Average of term_days
- **instrument_count**: Count of unique instruments

---

## Treasury Bills (T-Bills)

### Required Fields
- **face_value** (or principal)
- **term_days** (or days_to_maturity)
  - Alternatively: valuation_date + maturity_date
  - Alternatively: issue_date + maturity_date
- **purchase_price** OR **discount_rate** (at least one required)

### Optional Fields
- **carrying_value** - Book/accounting value
- **day_count_convention** - Day count basis (default: ACT/360)
- **currency** - Instrument currency
- **valuation_date** - Date for valuation
- **maturity_date** - Maturity date
- **issue_date** - Issue date

### Calculations

#### 1. Purchase Price (from Discount Rate)
**Formula**: `face_value × (1 - discount_rate × term_days / discount_basis)`

**Description**: Calculate purchase price from discount rate using standard T-Bill formula.

**Precision**: 2 decimal places (monetary)

**Example**:
- Face Value: 100,000
- Discount Rate: 5% (0.05)
- Term Days: 90
- Discount Basis: ACT/360 (divisor = 360)
- Purchase Price = 100,000 × (1 - 0.05 × 90/360) = 98,750.00

---

#### 2. Discount Amount
**Formula**: `face_value - purchase_price`

**Description**: Difference between face value and purchase price.

**Precision**: 2 decimal places (monetary)

**Example**:
- Face Value: 100,000
- Purchase Price: 98,750
- Discount Amount = 1,250.00

---

#### 3. Discount Yield (Bank Discount Rate)
**Formula**: `(discount_amount / face_value) × (discount_basis / term_days) × 100`

**Description**: Bank discount rate using the discount basis (typically 360).

**Precision**: 4 decimal places (percentage)

**Example**:
- Discount Amount: 1,250
- Face Value: 100,000
- Term Days: 90
- Discount Basis: ACT/360 (divisor = 360)
- Discount Yield = (1,250 / 100,000) × (360/90) × 100 = 5.0000%

---

#### 4. Money Market Yield (CD Equivalent Yield)
**Formula**: `(discount_amount / purchase_price) × (discount_basis / term_days) × 100`

**Description**: Money market yield using discount basis.

**Precision**: 4 decimal places (percentage)

**Example**:
- Discount Amount: 1,250
- Purchase Price: 98,750
- Term Days: 90
- Discount Basis: ACT/360 (divisor = 360)
- Money Market Yield = (1,250 / 98,750) × (360/90) × 100 = 5.0633%

---

#### 5. Bond Equivalent Yield (Investment Yield)
**Formula**: `(discount_amount / purchase_price) × (365 / term_days) × 100`

**Description**: Bond equivalent yield using 365-day basis.

**Precision**: 4 decimal places (percentage)

**Example**:
- Discount Amount: 1,250
- Purchase Price: 98,750
- Term Days: 90
- Bond Equivalent Yield = (1,250 / 98,750) × (365/90) × 100 = 5.1266%

---

#### 6. Holding Period Yield
**Formula**: `(discount_amount / purchase_price) × 100`

**Description**: Simple holding period return.

**Precision**: 4 decimal places (percentage)

**Example**:
- Discount Amount: 1,250
- Purchase Price: 98,750
- Holding Period Yield = (1,250 / 98,750) × 100 = 1.2658%

---

#### 7. Effective Annual Yield
**Formula**: `((face_value / purchase_price) ^ (365 / term_days) - 1) × 100`

**Description**: Compounded annual yield.

**Precision**: 4 decimal places (percentage)

**Example**:
- Face Value: 100,000
- Purchase Price: 98,750
- Term Days: 90
- Effective Annual Yield = ((100,000 / 98,750) ^ (365/90) - 1) × 100 = 5.2938%

---

#### 8. Total Value (Maturity Value)
**Formula**: `face_value`

**Description**: Value at maturity (face value).

**Precision**: 2 decimal places (monetary)

**Example**:
- Total Value = 100,000.00

---

#### 9. Yield Curve Rate (Benchmark)
**Formula**: FRED benchmark rate (if available)

**Description**: External benchmark rate from FRED for comparison.

**Precision**: 4 decimal places (percentage)

---

### Aggregations (Multi-Instrument)
- **total_face_value**: Sum of all face_value values
- **total_purchase_price**: Sum of all purchase_price values
- **total_discount**: Sum of all discount_amount values
- **total_value**: Sum of all face_value values
- **avg_discount_rate**: Average of discount_yield values
- **avg_days_to_maturity**: Average of term_days values
- **instrument_count**: Count of unique instruments

---

## Bonds

### Required Fields
- **face_value** (or principal)
- **coupon_rate** (or interest_rate)
- **years_to_maturity** (or valuation_date + maturity_date, or days_to_maturity)
- **coupon_frequency** (1=annual, 2=semi-annual, 4=quarterly, 12=monthly)
- **price** OR **yield_to_maturity** (at least one required)

### Optional Fields
- **carrying_value** - Book/accounting value
- **day_count_convention** - Day count basis (default: ACT/365)
- **currency** - Instrument currency
- **valuation_date** - Date for valuation
- **maturity_date** - Maturity date
- **issue_date** - Issue date
- **last_coupon_date** - Last coupon payment date
- **risk_free_rate** - Risk-free rate for discount rate calculation
- **country_risk_premium** - Country risk premium
- **credit_spread** - Credit spread over risk-free rate

### Calculations

#### 1. Annual Coupon
**Formula**: `face_value × coupon_rate`

**Description**: Annual coupon payment amount.

**Precision**: 2 decimal places (monetary)

**Example**:
- Face Value: 100,000
- Coupon Rate: 6% (0.06)
- Annual Coupon = 100,000 × 0.06 = 6,000.00

---

#### 2. Coupon Per Period
**Formula**: `annual_coupon / coupon_frequency`

**Description**: Coupon payment per period.

**Precision**: 2 decimal places (monetary)

**Example**:
- Annual Coupon: 6,000
- Coupon Frequency: 2 (semi-annual)
- Coupon Per Period = 6,000 / 2 = 3,000.00

---

#### 3. Price from Yield to Maturity
**Formula**: Discounted cash flow:
```
price = Σ (coupon_per_period / (1 + ytm/frequency)^t) + (face_value / (1 + ytm/frequency)^n)
where t = 1 to n, n = years_to_maturity × frequency
```

**Description**: Calculate bond price from YTM using standard DCF formula.

**Precision**: 2 decimal places (monetary)

**Example**:
- Face Value: 100,000
- Coupon Rate: 6% (0.06)
- YTM: 5% (0.05)
- Years to Maturity: 5
- Frequency: 2 (semi-annual)
- Coupon Per Period: 3,000
- Periods: 10
- Price = Σ(3,000/(1.025)^t) + 100,000/(1.025)^10 ≈ 104,376.00

---

#### 4. Yield to Maturity (from Price)
**Formula**: Newton-Raphson iteration to solve for YTM:
```
price = Σ (coupon_per_period / (1 + ytm/frequency)^t) + (face_value / (1 + ytm/frequency)^n)
```

**Description**: Solve for YTM given price using iterative method.

**Precision**: 4 decimal places (percentage)

**Algorithm**: Newton-Raphson with up to 200 iterations

---

#### 5. Current Yield
**Formula**: `(annual_coupon / price) × 100`

**Description**: Annual coupon as percentage of current price.

**Precision**: 4 decimal places (percentage)

**Example**:
- Annual Coupon: 6,000
- Price: 104,376
- Current Yield = (6,000 / 104,376) × 100 = 5.7479%

---

#### 6. Accrued Interest
**Formula**: `coupon_per_period × (days_accrued / days_in_period)`

**Description**: Interest accrued since last coupon payment.

**Precision**: 2 decimal places (monetary)

**Days in Period**:
- ACT/365: 365 / frequency
- ACT/360: 360 / frequency
- 30/360: 360 / frequency

**Example**:
- Coupon Per Period: 3,000
- Days Accrued: 45
- Day Count: ACT/365, Frequency: 2
- Days in Period: 365/2 = 182.5
- Accrued Interest = 3,000 × (45/182.5) = 739.73

---

#### 7. Macaulay Duration
**Formula**: Weighted average time to cash flows:
```
macaulay = (Σ (t × PV_t) / Σ PV_t) / frequency
where PV_t = present value of cash flow at time t
```

**Description**: Weighted average time to receive cash flows.

**Precision**: 4 decimal places (years)

**Example**:
- Price: 104,376
- YTM: 5%
- Frequency: 2
- Macaulay Duration ≈ 4.3 years

---

#### 8. Modified Duration
**Formula**: `macaulay_duration / (1 + ytm/frequency)`

**Description**: Price sensitivity to yield changes.

**Precision**: 4 decimal places (years)

**Example**:
- Macaulay Duration: 4.3
- YTM: 5% (0.05)
- Frequency: 2
- Modified Duration = 4.3 / (1 + 0.05/2) = 4.1962

---

#### 9. Present Value (using Discount Rate)
**Formula**: Discounted cash flow using discount rate:
```
pv = Σ (coupon_per_period / (1 + discount_rate/frequency)^t) + (face_value / (1 + discount_rate/frequency)^n)
```

**Description**: Present value using risk-adjusted discount rate.

**Precision**: 2 decimal places (monetary)

**Discount Rate Components**:
- Risk-free rate (from FRED or input)
- + Country risk premium (if provided)
- + Credit spread (if provided)

---

#### 10. Fair Value
**Formula**: `present_value - price`

**Description**: Difference between discounted PV and market price.

**Precision**: 2 decimal places (monetary)

**Example**:
- Present Value: 106,000
- Price: 104,376
- Fair Value = 1,624.00

---

#### 11. Total Value
**Formula**: `price` (current market value)

**Description**: Current market value of the bond.

**Precision**: 2 decimal places (monetary)

---

#### 12. Bond Equivalent Yield
**Formula**: `yield_to_maturity`

**Description**: Same as YTM for bonds.

**Precision**: 4 decimal places (percentage)

---

#### 13. Yield Curve Rate (Benchmark)
**Formula**: FRED benchmark rate (if available)

**Description**: External benchmark rate from FRED for comparison.

**Precision**: 4 decimal places (percentage)

---

### Aggregations (Multi-Instrument)
- **total_face_value**: Sum of all face_value values
- **total_market_value**: Sum of all current_price values
- **total_coupon_income**: Sum of all annual_coupon values
- **total_value**: Sum of all price values (or face_value if price is 0)
- **avg_ytm**: Average of yield_to_maturity values
- **avg_duration**: Average of duration (macaulay) values
- **weighted_avg_coupon**: Weighted average of coupon rates (by face value)
- **instrument_count**: Count of unique instruments

---

## Field Name Aliases (Synonyms)

### Principal / Face Value
**Canonical**: `principal`, `face_value`

**Synonyms**:
- principal, principle, principal amount, principle amount
- face value, facevalue, face_value, face amount
- par value, parvalue, par amount
- nominal, nominal amount, nominal value
- notional, notional amount
- investment amount, initial investment, initial amount
- starting balance, opening balance, deposit amount
- capital, total cost, purchase cost, cost, amount, value
- outstanding principal, current principal

---

### Interest Rate / Coupon Rate
**Canonical**: `interest_rate`, `coupon_rate`

**Synonyms**:
- interest rate, interestrate, interest_rate
- annual rate, annual interest rate
- nominal rate, stated rate, effective rate
- apr, coupon, coupon rate
- rate %, rate%, rate
- coupon, annual coupon, annualcoupon
- fixed rate, fixedrate
- nominal rate, nominalrate
- stated rate, statedrate

---

### Days to Maturity / Term Days
**Canonical**: `days_to_maturity`, `term_days`

**Synonyms**:
- days to maturity, daystomaturity, days_to_maturity
- maturity days, duration days, contract days
- term days, term_days, termdays, term in days
- tenor, term, days, period

---

### Issue Date / Start Date
**Canonical**: `issue_date`

**Synonyms**:
- issue date, issuedate, issue_date
- start date, startdate, start_date
- effective date, effectivedate, effective_date
- settlement date, settlementdate, settlement_date
- origination date, value date, valuedate, value_date
- trade date, tradedate, trade_date

---

### Maturity Date / End Date
**Canonical**: `maturity_date`

**Synonyms**:
- maturity date, maturitydate, maturity_date
- end date, enddate, end_date
- due date, duedate, due_date
- redemption date, redemptiondate, redemption_date
- expiry date, expirydate, expiry_date
- termination date

---

### Valuation Date
**Canonical**: `valuation_date`

**Synonyms**:
- valuation, valuation date, valuationdate, valuation_date
- portfolio date, portfoliodate, portfolio_date
- report date, reportdate, report_date
- as of date, asofdate, as_of_date
- date pfolio, datepfolio

---

### Purchase Price / Price
**Canonical**: `purchase_price`, `price`

**Synonyms**:
- purchase price, purchaseprice, purchase_price
- buy price, buyprice, buy_price
- acquisition price, entry price
- price paid, pricepaid, price_paid
- issue price, issueprice, issue_price
- price
- current price, currentprice, current_price

---

### Discount Rate
**Canonical**: `discount_rate`

**Synonyms**:
- discount rate, discountrate, discount_rate
- bank discount, bankdiscount
- discount yield, discountyield
- t-bill rate, tbillrate
- auction rate, auctionrate
- discount

---

### Yield to Maturity
**Canonical**: `yield`, `yield_to_maturity`

**Synonyms**:
- yield to maturity, yieldtomaturity, yield_to_maturity
- ytm, market yield, marketyield
- required return, requiredreturn
- redemption yield, redemptionyield
- yield

---

### Coupon Frequency
**Canonical**: `coupon_frequency`, `frequency`

**Synonyms**:
- coupon frequency, couponfrequency, coupon_frequency
- Coupon Frequency, CouponFrequency, Coupon_Frequency
- payment frequency, paymentfrequency
- frequency, coupon period, payments per year

**Valid Values**:
- 1 = Annual
- 2 = Semi-annual
- 4 = Quarterly
- 12 = Monthly
- Text: annual, semi-annual, quarterly, monthly

---

### Years to Maturity
**Canonical**: `years_to_maturity`

**Synonyms**:
- years to maturity, yearstomaturity, years_to_maturity
- maturity years, maturityyears
- term years, termyears
- duration years, durationyears
- time to maturity, timetomaturity
- years, year

---

### Currency
**Canonical**: `currency`

**Synonyms**:
- currency, ccy, iso code, currency code

---

### Day Count Convention
**Canonical**: `day_count_convention`, `day_count`

**Synonyms**:
- day count convention, day count, day_count

**Valid Values**:
- ACT/360
- ACT/365
- 30/360
- 360
- 365

---

### Instrument Name
**Canonical**: `instrument_name`

**Synonyms**:
- parent company name, parent company
- issuer, company, entity
- short name, shortname
- instrument name, instrumentname, instrument_name
- instrument, description, counterparty
- bond name, bondname, bond_name, bond
- t-bill name, tbill name, tbillname, tbill_name
- tbill, t-bill, treasury bill name
- security name, securityname
- name, ticker, symbol

---

### Market Value
**Canonical**: `market_value`

**Synonyms**:
- market value, marketvalue, market_value
- current value, currentvalue
- fair value, fairvalue
- present value, presentvalue
- total value, totalvalue

---

### Carrying Value / Book Value
**Canonical**: `carrying_value`, `book_value`

**Synonyms**:
- carrying value, book value, accounting value

---

### Risk-Free Rate / Benchmark Rate
**Canonical**: `risk_free_rate`, `benchmark_rate`

**Synonyms**:
- benchmark rate, benchmarkrate
- risk-free rate, riskfreerate
- government yield, governmentyield
- treasury yield, treasuryyield, sofr

---

### Credit Spread
**Canonical**: `credit_spread`, `spread`

**Synonyms**:
- credit spread, creditspread
- g-spread, gspread, z-spread, zspread
- asset swap spread, oas

---

### Country Risk Premium
**Canonical**: `country_risk_premium`

**Synonyms**:
- country risk premium, country spread

---

## Day Count Conventions

### ACT/360 (Actual/360)
- **Description**: Actual number of days divided by 360
- **Used For**: Money market instruments, Eurodollar deposits, commercial paper
- **Default For**: Money Market, Treasury Bills
- **Days in Period**: 360 / frequency

### ACT/365 (Actual/365)
- **Description**: Actual number of days divided by 365
- **Used For**: Bonds, government securities
- **Default For**: Bonds
- **Days in Period**: 365 / frequency

### 30/360
- **Description**: 30 days per month, 360 days per year
- **Used For**: Corporate bonds, municipal bonds
- **Days in Period**: 360 / frequency

### Selection Priority
1. Explicit `day_count_convention` field
2. Instrument default (Money Market/T-Bills: ACT/360, Bonds: ACT/365)
3. Fallback to ACT/360

---

## Validation Rules

### Common Validations

#### Value Ranges
- **Principal/Face Value**: Must be > 0
- **Interest Rate/Coupon Rate**: Must be >= 0
- **Discount Rate**: Must be >= 0
- **Term Days**: Must be > 0
- **Years to Maturity**: Must be > 0
- **Coupon Frequency**: Must be > 0 and <= 365
- **Purchase Price**: Must be > 0 (for T-Bills, must be <= face_value)

#### Date Consistency
- **Valuation Date**: Must be on or before Maturity Date
- **Issue Date**: Must be on or before Maturity Date
- **Valuation Date**: Must be on or after Issue Date (logical)

#### Input Types
- **Percentages**: Can be entered as "5", "5%", or "0.05" - all normalized to decimal
- **Currency Symbols**: Stripped from numeric values
- **Commas**: Removed from numeric values
- **Negative Values**: Allowed in parentheses "(100)" or with minus sign "-100"

### Money Market Specific
- **Required**: principal, interest_rate, term_days
- **Date Calculation**: term_days OR (valuation_date + maturity_date) OR (issue_date + maturity_date)
- **Error on**: principal <= 0, rate < 0, days <= 0, date inconsistency

### Treasury Bill Specific
- **Required**: face_value, term_days, (purchase_price OR discount_rate)
- **Date Calculation**: term_days OR (valuation_date + maturity_date) OR (issue_date + maturity_date)
- **Error on**: face <= 0, days <= 0, price > face, discount_rate < 0, date inconsistency

### Bond Specific
- **Required**: face_value, coupon_rate, years_to_maturity, coupon_frequency, (price OR yield_to_maturity)
- **Date Calculation**: years_to_maturity OR (valuation_date + maturity_date) OR days_to_maturity
- **Error on**: face <= 0, years <= 0, frequency <= 0 or > 365, date inconsistency
- **Yield Validation**: Reject yield > 100% (likely monetary value, not percentage)

---

## Error Messages

### Missing Fields
Format: "Missing required field: {field_name} (aliases: {alias1}, {alias2}, ...)"

Examples:
- "Missing required field: principal (aliases: Principal, Face Value, Amount, Notional)"
- "Missing required field: coupon_frequency (Annual=1, Semi-annual=2, Quarterly=4, Monthly=12)"

### Invalid Fields
Format: "{field_name}: {reason}"

Examples:
- "face_value: must be > 0"
- "interest_rate: must be >= 0"
- "valuation_date: must be on or before maturity_date"
- "purchase_price: cannot exceed face value for discount instruments"

### Partial Calculations
When some fields are missing but calculation can proceed partially:
- Status: "partial"
- Includes calculated fields that are available
- Includes error message explaining what's missing

### Calculation Failures
When required fields are missing or validation fails:
- Status: "error" or "cannot_calculate"
- Includes list of missing fields
- Includes list of invalid fields with reasons
- No calculation results returned

---

## Output Field Names (CamelCase Aliases)

All calculation results include both snake_case and camelCase field names for frontend compatibility.

### Money Market
- principal / Principal
- interestRate / interest_rate
- termDays / term_days
- interestEarned / interest_earned
- totalValue / total_value
- discountYield / discount_yield
- effectiveYield / effective_yield
- bondEquivalentYield / bond_equivalent_yield
- yieldCurveRate / yield_curve_rate
- marketValue / market_value

### Treasury Bills
- faceValue / face_value
- purchasePrice / purchase_price
- termDays / term_days
- discountAmount / discount_amount
- discountYield / discount_yield
- moneyMarketYield / money_market_yield
- bondEquivalentYield / bond_equivalent_yield
- holdingPeriodYield / holding_period_yield
- effectiveAnnualYield / effective_annual_yield
- yieldCurveRate / yield_curve_rate
- totalValue / total_value
- carryingValue / carrying_value

### Bonds
- faceValue / face_value
- currentPrice / current_price
- couponRate / coupon_rate
- yearsToMaturity / years_to_maturity
- yieldToMaturity / yield_to_maturity
- duration / duration (macaulay)
- modifiedDuration / modified_duration
- currentYield / current_yield
- accruedInterest / accrued_interest
- annualCoupon / annual_coupon
- bondEquivalentYield / bond_equivalent_yield
- yieldCurveRate / yield_curve_rate
- presentValue / present_value
- fairValue / fair_value
- carryingValue / carrying_value
- discountRate / discount_rate

---

## Common Calculation Pitfalls

### 1. Day Count Convention Mismatch
**Problem**: Using wrong day count for the instrument type.
**Solution**: Always check the day_count_convention field or use the instrument default.

### 2. Yield vs Price Confusion
**Problem**: Providing yield as monetary value or price as percentage.
**Solution**: System validates and rejects yield > 100%. Use proper formats.

### 3. Date Inconsistency
**Problem**: Valuation date after maturity date.
**Solution**: System validates date consistency and returns clear error.

### 4. Discount Rate vs Investment Yield
**Problem**: Using discount rate formula for investment yield (T-Bills).
**Solution**: Distinguish between discount_yield (bank discount) and bond_equivalent_yield (investment yield).

### 5. Accrued Interest Calculation
**Problem**: Wrong days in period for coupon frequency.
**Solution**: Use day count convention to determine days_in_period = divisor / frequency.

### 6. Negative Values
**Problem**: Negative principal or face value.
**Solution**: System validates and rejects with clear error message.

### 7. Missing Frequency for Bonds
**Problem**: Coupon frequency not provided for bond calculations.
**Solution**: Required field - system will return error if missing.

### 8. Price > Face for T-Bills
**Problem**: Purchase price exceeding face value for discount instruments.
**Solution**: System validates and rejects with clear error.

---

## Currency Handling

### Currency Preservation
- Currency from input is preserved in all calculation results
- No automatic currency conversion
- Currency field aliases: currency, ccy, iso code, currency code

### Supported Currencies
The system supports any currency code (USD, EUR, GBP, JPY, CAD, ZAR, BWP, ZWG, etc.)
as specified in the input data. No currency conversion is performed.

### Exchange Rates
- Exchange rate conversion is NOT performed automatically
- Requires explicit exchange rate configuration if multi-currency aggregation is needed
- All values are calculated and displayed in the instrument's original currency

---

## Precision and Rounding

### Monetary Values
- **Precision**: 2 decimal places
- **Rounding**: Standard rounding (round half up)
- **Applied to**: All monetary calculations (principal, interest, price, etc.)

### Percentage Values
- **Precision**: 4 decimal places
- **Rounding**: Standard rounding (round half up)
- **Applied to**: All percentage calculations (yields, rates, spreads)

### Time Values
- **Precision**: Integer for days, 4 decimal places for years
- **Rounding**: Standard rounding
- **Applied to**: term_days, years_to_maturity, duration

---

## Backend API Endpoints

### Calculate by Instrument Type
**Endpoint**: `POST /api/calculate/{instrument_type}`

**Supported Types**:
- `money-market`
- `tbills`
- `bonds`

**Request Body**:
```json
{
  "data": [...],  // Array of row data
  "valuationDate": "YYYY-MM-DD",  // Optional
  "currency": "USD",  // Optional
  "maturity": "1M",  // Optional for FRED
  "country": "US",  // Optional for FRED
  "dataset_id": "...",  // Optional
  "session_id": "..."  // Optional
}
```

**Response**:
```json
{
  "success": true,
  "is_multi_instrument": false,
  "instrument_type": "tbills",
  "data": {
    "calculations": [...],
    "aggregates": {...}
  }
}
```

---

## FRED Benchmark Rate Integration

### Source of Truth
All FRED benchmark rates come from the **actual FRED API** (Federal Reserve Economic Data). No fallback values, mock data, or fabricated benchmarks are used.

### API Configuration
- **Base URL**: `https://api.stlouisfed.org/fred`
- **API Key**: Set via `FRED_API_KEY` environment variable
- **Timeout**: 10 seconds per request
- **Error Handling**: Returns `benchmark_rate: None` when FRED has no data

### Supported Countries and Series

| Country | Code | 1M | 3M | 6M | 1Y | 2Y | 3Y | 5Y | 7Y | 10Y | 20Y | 30Y |
|---------|------|----|----|----|----|----|----|----|----| ----| ----| ----|
| United States | US | DGS1MO | DGS3MO | DGS6MO | DGS1 | DGS2 | DGS3 | DGS5 | DGS7 | DGS10 | DGS20 | DGS30 |
| United Kingdom | GB | - | IR3TTS01GBM156N | - | IR3TTS01GBM156N | - | - | IR5TTS01GBM156N | - | IRLTLT01GBM156N | - | - |
| Japan | JP | - | IR3TTS01JPM156N | - | IR3TTS01JPM156N | - | - | IR5TTS01JPM156N | - | IRLTLT01JPM156N | - | - |
| Eurozone | EUR | - | IR3TTS01EZM156N | - | IR3TTS01EZM156N | - | - | IR5TTS01EZM156N | - | IRLTLT01EZM156N | - | - |
| Canada | CA | - | IR3TTS01CAM156N | - | IR3TTS01CAM156N | - | - | IR5TTS01CAM156N | - | IRLTLT01CAM156N | - | - |
| Australia | AU | - | IR3TTS01AUM156N | - | IR3TTS01AUM156N | - | - | IR5TTS01AUM156N | - | IRLTLT01AUM156N | - | - |
| South Africa | ZA | - | IR3TTS01ZAM156N | - | IR3TTS01ZAM156N | - | - | IR5TTS01ZAM156N | - | IRLTLT01ZAM156N | - | - |

### T-Bill Specific Series (4W, 13W, 26W, 52W)
| Country | 4W | 13W | 26W | 52W |
|---------|----| ----| ----| ---- |
| United States | DTB4WK | DTB3 | DTB6 | DTB1Y |

### FRED Data Flow

1. **Calculation Request** → Backend receives calculation request with instrument_type, maturity, country, currency
2. **Benchmark Fetch** → `get_market_benchmark()` is called with these parameters
3. **Series Lookup** → Maps country+maturity to FRED series ID (e.g., US + 1Y → DGS1)
4. **API Call** → Fetches latest observation from FRED API
5. **Value Return** → Returns `benchmark_rate` as decimal (e.g., 0.045 for 4.5%)
6. **Calculation** → benchmark_yield passed to calculation functions
7. **Result** → `yield_curve_rate` set to `benchmark_yield * 100` (converted to percentage)

### FRED Values in Calculation Results

The following fields in calculation results come from FRED API:

#### Money Market
- **yield_curve_rate** / **yieldCurveRate**: FRED benchmark rate (as percentage)

#### Treasury Bills
- **yield_curve_rate** / **yieldCurveRate**: FRED benchmark rate (as percentage)

#### Bonds
- **yield_curve_rate** / **yieldCurveRate**: FRED benchmark rate (as percentage)
- **discount_rate** / **discountRate**: (If using FRED + spreads) FRED benchmark + country_risk_premium + credit_spread

### FRED API Error Handling

When FRED API fails or returns no data:
- `benchmark_rate` is set to `None`
- `yield_curve_rate` is set to `None`
- Calculation proceeds without benchmark (not blocked)
- Error logged: "FRED benchmark fetch failed" or "FRED API returned no data"
- Note included in result: `fred.note` explains the failure

### No Fallback Data
The system **never** uses fallback or fabricated benchmark rates. If FRED has no data:
- The benchmark is `None`
- The calculation continues without it
- The result clearly indicates benchmark is unavailable

### FRED Data Structure in Results

```json
{
  "fred": {
    "benchmark_rate": 4.5,           // Decimal from FRED API
    "series_label": "1Y US Treasury",
    "series_id": "DGS1",
    "country": "US",
    "currency": "USD",
    "maturity": "1Y",
    "date": "2024-01-15",           // Observation date from FRED
    "note": ""
  }
}
```

Or when FRED has no data:

```json
{
  "fred": {
    "benchmark_rate": null,
    "error": "No benchmark data available for tbills 1Y US",
    "note": "FRED API returned no data"
  }
}
```

### Verification Steps

To verify FRED values are real:

1. **Check FRED API Key**: Ensure `FRED_API_KEY` is set in `.env` file
2. **Check API Response**: Backend logs show "Fetched X FRED data points - NO FALLBACKS"
3. **Check Result Structure**: Verify `fred.benchmark_rate` matches FRED API response
4. **Check Series ID**: Verify `fred.series_id` is a valid FRED series
5. **Check Date**: Verify `fred.date` is the observation date from FRED

### Logging

Backend logs show FRED API activity:
- `Date range mode: Fetching time series from {from_date} to {to_date}`
- `Standard yield curve mode: Fetching current rates across maturities`
- `Fetched X time series points for {key_maturity} from {from_date} to {to_date}`
- `Returning X FRED data points - NO FALLBACKS`
- `FRED benchmark fetch failed: {error}` (when API fails)

### Currency Mapping

FRED data includes currency information based on country:
- US → USD
- GB → GBP
- EUR → EUR
- JP → JPY
- CA → CAD
- AU → AUD
- ZA → ZAR
- CH → CHF
- NZ → NZD
- NO → NOK
- SE → SEK
- DK → DKK
- BR → BRL
- MX → MXN
- IN → INR
- CN → CNY
- KR → KRW
- SG → SGD
- HK → HKD
- RU → RUB
- TR → TRY
- SA → SAR
- AE → AED
- IL → ILS

---

## Notes

1. **Backend is Source of Truth**: All calculations are performed in the backend. Frontend only displays results.

2. **No Mock Data**: The system never uses mock or fabricated values. If calculation cannot be performed, it returns an error.

3. **Partial Calculations**: Some calculations may succeed partially if only some fields are missing. Status will be "partial" with available results.

4. **Session Persistence**: Calculation results are saved to sessions and can be restored.

5. **Real Workbook Data**: All calculations use the actual data from the uploaded workbook after cleaning/mapping.

6. **Benchmark Rates**: FRED benchmark rates are fetched when available but are optional - calculations proceed without them.

7. **Error Reporting**: All errors include specific field names and reasons to help users correct their data.

---

## Version History

- **v1.0** - Initial implementation with basic formulas
- **v1.1** - Added day count convention support
- **v1.2** - Fixed T-Bill pricing formulas
- **v1.3** - Enhanced validation with date consistency checks
- **v1.4** - Added currency preservation
- **v1.5** - Improved error messages with field details
- **v1.6** - Fixed Money Market day count consistency
- **v1.7** - Enhanced Bond accrued interest calculation
- **v1.8** - Added comprehensive field synonym support

---

## Contact

For questions or issues with calculations, refer to the backend implementation in:
`backend/pages/calculations_details.py`

For frontend integration, refer to:
`frontend/src/views/InstrumentView.vue`
`frontend/src/services/api.js`
