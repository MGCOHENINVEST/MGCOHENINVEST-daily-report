# DATA_SCHEMA_2025-11-14.md

Canonical data schema for the daily report system as at **2025-11-14**.

All files live under `out/data/` in the freeze bundle and are designed for **stateless daily runs**:
each day’s run pulls required history from source (or cache), computes metrics, and writes a fully
self-contained JSON snapshot.

---

## 1. Global Conventions

### 1.1 Shared top-level fields

Every canonical JSON file **must** include:

```json
{
  "schema_version": "2025.11.14",
  "as_of_date": "2025-11-14",
  "as_of_time_utc": "2025-11-14T07:35:00Z",
  "data_vintage": "T-1_close",
  "generated_at_utc": "2025-11-14T07:37:12Z"
}
```

- `schema_version` (string)  
  Version of the schema this file complies with. For this document: `"2025.11.14"`.  
  Increment when fields are added/retired in a **non-backward-compatible** way.

- `as_of_date` (string, `YYYY-MM-DD`)  
  Logical “market date” of the snapshot. Typically the trading date referred to by the data.

- `as_of_time_utc` (string, ISO 8601)  
  When the market data snapshot is considered valid (e.g. when all source pulls completed).

- `data_vintage` (string enum)  
  Indicates which prices the file is based on:
  - `"T-1_close"` – prior day’s official close
  - `"T_intraday"` – intraday snapshot on `as_of_date`
  - `"T_close"` – same-day close (for retrospective runs)
  - Additional values must be documented here.

- `generated_at_utc` (string, ISO 8601)  
  Actual time the file was generated.

### 1.2 Null vs zero

- `null` → data not available / not applicable / unknown  
- `0` → real numeric zero  
- No magic sentinel values like `-999`.

### 1.3 Source attribution

Where a numeric field may come from multiple upstream providers or methods, add a paired
source field:

```json
{
  "pe_forward": 12.8,
  "pe_forward_source": "EODHD",
  "pe_forward_as_of": "2025-11-13"
}
```

Typical `*_source` values: `"EODHD"`, `"FRED"`, `"BOE"`, `"manual"`, `"computed"`.

### 1.4 Currency and identifiers

- Currencies: ISO 4217 3-letter codes (`"GBP"`, `"USD"`, `"EUR"`, `"CHF"`).  
- FX pairs: 6-letter code base+quote (`"GBPUSD"`).  
- Equities: combined:
  - `ticker` (e.g. `"BARC"`),
  - `exchange` (e.g. `"LSE"`),
  - `isin`,
  - `eodhd_code` (e.g. `"BARC.LSE"`).

---

## 2. Yields – UK & US Govies

### 2.1 File paths

- `yield_UK.json`
- `yield_US.json`

### 2.2 Structure

```json
{
  "schema_version": "2025.11.14",
  "as_of_date": "2025-11-14",
  "as_of_time_utc": "2025-11-14T07:35:00Z",
  "data_vintage": "T-1_close",
  "generated_at_utc": "2025-11-14T07:37:12Z",

  "country": "UK",
  "source": "BOE",
  "rows": [
    {
      "maturity_code": "UK_10Y",
      "maturity_label": "10Y",
      "tenor_years": 10.0,
      "is_on_the_run": true,
      "bucket": "long",              // short / belly / long
      "currency": "GBP",

      "yield_today": 0.04321,        // 5 significant figures
      "yield_d1": 0.04205,
      "yield_w1": 0.03980,
      "yield_m1": 0.03750,
      "yield_y1": 0.03100,

      "bp_change_d1": 11.6,          // vs d-1
      "bp_change_w1": 34.1,          // vs w-1
      "bp_change_m1": 57.1,
      "bp_change_y1": 122.1,

      "spread_vs_2y_bp": 15.2,
      "spread_vs_10y_bp": 0.0,
      "spread_vs_30y_bp": -7.8,

      "modified_duration": 8.65,
      "duration_calc_method": "computed",  // provider | approx_linear | computed
      "convexity": 0.32,
      "dv01_per_1mm": 865.0,
      "dv01_currency": "GBP",

      "price_index_today": 102.45,
      "price_index_basis": "2020-01-01=100",
      "price_return_m1": 0.0123,
      "is_total_return": false,

      "data_source": "BOE",
      "data_source_ref": "GILT_10Y_SERIES",
      "data_source_as_of": "2025-11-13"
    }
  ]
}
```

### 2.3 Notes

- Yields stored as decimals (4.321% → `0.04321`) with **5 significant figures**.  
- `rows` includes only maturities actually used in the UI (e.g. 2Y, 5Y, 10Y, 30Y, 3M/6M bills where relevant).  
- Curve spreads are optional for short maturities; `null` if not meaningful.

---

## 3. FX Majors

### 3.1 File path

- `fx_pairs.json`

### 3.2 Structure

```json
{
  "schema_version": "2025.11.14",
  "as_of_date": "2025-11-14",
  "as_of_time_utc": "2025-11-14T07:35:00Z",
  "data_vintage": "T_intraday",
  "generated_at_utc": "2025-11-14T07:37:12Z",

  "pairs": [
    {
      "pair_code": "GBPUSD",
      "base_ccy": "GBP",
      "quote_ccy": "USD",
      "pair_type": "major",          // major | minor | cross

      "spot_today": 1.23456,
      "spot_d1": 1.25600,
      "spot_w1": 1.27000,
      "spot_m1": 1.29000,
      "spot_y1": 1.21000,

      "ret_d1": -0.0171,
      "ret_w1": -0.0280,
      "ret_m1": -0.0430,
      "ret_y1": 0.0203,

      "spot_52w_high": 1.32000,
      "spot_52w_low": 1.18000,
      "distance_to_52w_high_pct": -0.0648,
      "distance_to_52w_low_pct": 0.0462,

      "bid": 1.23450,
      "ask": 1.23470,
      "spread_pips": 2.0,

      "realised_vol_20d": 0.085,
      "realised_vol_60d": 0.092,
      "vol_annualisation_factor": 252,
      "vol_calculation": "close_to_close",  // parkinson | garman_klass also allowed

      "carry_annualised": 0.0125,
      "carry_base_rate": 0.0525,
      "carry_quote_rate": 0.0400,
      "carry_rate_tenor": "overnight",      // overnight | 3m

      "data_source": "EODHD",
      "data_source_ref": "FX_SPOT_GBPUSD",
      "data_source_as_of": "2025-11-14"
    }
  ]
}
```

### 3.3 FX cross matrix (derived, UI only)

The **FX crosses table** (GBP, USD, EUR, CHF rows/columns) is **derived** at render time by
combining `fx_pairs.json`:

- For base → quote:
  - If `pair_code` exists directly, use its `spot_today`.
  - Otherwise, use triangular relationship (e.g. `GBPEUR = GBPUSD / EURUSD` where needed).

No separate canonical JSON is required.

---

## 4. Equity Indices

### 4.1 File path

- `equity_indices.json`

### 4.2 Structure

```json
{
  "schema_version": "2025.11.14",
  "as_of_date": "2025-11-14",
  "as_of_time_utc": "2025-11-14T07:35:00Z",
  "data_vintage": "T-1_close",
  "generated_at_utc": "2025-11-14T07:37:12Z",

  "indices": [
    {
      "index_code": "FTSE_100",
      "name": "FTSE 100",
      "currency": "GBP",
      "region": "UK",
      "type": "large_cap",               // large_cap / mid_cap / global / thematic

      "level_today": 7450.12,
      "level_d1": 7390.50,
      "level_w1": 7320.00,
      "level_m1": 7200.00,
      "level_m3": 7000.00,
      "level_m6": 6800.00,
      "level_y1": 7100.00,

      "ret_d1": 0.0081,
      "ret_w1": 0.0178,
      "ret_m1": 0.0347,
      "ret_m3": 0.0643,
      "ret_m6": 0.0956,
      "ret_y1": 0.0493,

      "hi_52w": 7600.00,
      "lo_52w": 6500.00,
      "drawdown_from_hi_pct": -0.0197,

      "realised_vol_20d": 0.135,
      "realised_vol_60d": 0.142,

      "pe_ttm": 13.5,
      "pe_forward": 12.8,
      "pe_forward_period": "NTM",        // NTM | 12m | FY+1
      "pb": 1.6,
      "div_yield": 0.040,
      "div_yield_trailing_12m": true,
      "earnings_yield": 0.078,
      "valuation_as_of": "2025-11-13",
      "valuation_source": "EODHD",

      "beta_vs_global": 0.95,
      "beta_reference_index": "MSCI_WORLD",
      "beta_lookback_days": 252,
      "beta_source": "computed",

      "data_source": "EODHD",
      "data_source_ref": "INDEX_FTSE100",
      "data_source_as_of": "2025-11-13"
    }
  ]
}
```

---

## 5. Commodities

### 5.1 File path

- `commodities.json`

### 5.2 Structure

```json
{
  "schema_version": "2025.11.14",
  "as_of_date": "2025-11-14",
  "as_of_time_utc": "2025-11-14T07:35:00Z",
  "data_vintage": "T-1_close",
  "generated_at_utc": "2025-11-14T07:37:12Z",

  "instruments": [
    {
      "code": "XAUUSD",
      "name": "Gold spot",
      "category": "precious_metals",      // precious_metals / energy / base_metals / ags / softs
      "contract_type": "spot",            // spot | front_future | continuous_future
      "currency": "USD",
      "unit": "oz",

      "price_today": 2450.25,
      "price_d1": 2435.10,
      "price_w1": 2400.00,
      "price_m1": 2350.00,
      "price_m3": 2250.00,
      "price_m6": 2200.00,
      "price_y1": 2100.00,

      "ret_d1": 0.0062,
      "ret_w1": 0.0209,
      "ret_m1": 0.0426,
      "ret_m3": 0.0889,
      "ret_m6": 0.1138,
      "ret_y1": 0.1668,

      "hi_52w": 2500.00,
      "lo_52w": 1900.00,
      "distance_to_52w_high_pct": -0.0200,
      "distance_to_52w_low_pct": 0.2896,

      "realised_vol_20d": 0.160,
      "realised_vol_60d": 0.155,

      "term_structure": {
        "contract_type": "front_future",
        "contract_month": "2025-12",
        "expiry_date": "2025-12-19",
        "next_contract_month": "2026-02",
        "next_contract_price": 2470.50,
        "term_structure_slope_pct": 0.0083,
        "term_structure_state": "contango",    // contango | backwardation
        "roll_date": "2025-12-10"
      },

      "ratios": {
        "gold_silver": 85.2,
        "gold_silver_components": {
          "gold": 2450.25,
          "silver": 28.76
        }
      },

      "data_source": "EODHD",
      "data_source_ref": "COMMOD_XAUUSD",
      "data_source_as_of": "2025-11-13"
    }
  ]
}
```

---

## 6. Macro Calendar

### 6.1 File path

- `macro_calendar.json`

### 6.2 Structure

```json
{
  "schema_version": "2025.11.14",
  "as_of_date": "2025-11-14",
  "as_of_time_utc": "2025-11-14T07:35:00Z",
  "data_vintage": "T-1_close",
  "generated_at_utc": "2025-11-14T07:37:12Z",

  "window_start": "2025-11-12",
  "window_end": "2025-11-18",

  "events": [
    {
      "event_id": "US_CPI_HEADLINE_2025-11-14",
      "country": "US",
      "region": "US",
      "indicator_code": "CPI_HEADLINE",
      "indicator_name": "CPI Headline, YoY",
      "importance": 3,                        // 1 = low, 2 = medium, 3 = high

      "scheduled_datetime_local": "2025-11-14T08:30:00",
      "scheduled_timezone": "America/New_York",
      "scheduled_datetime_utc": "2025-11-14T13:30:00Z",

      "actual": 3.0,
      "consensus": 3.2,
      "prior": 3.4,
      "prior_revised": 3.3,

      "surprise_abs": -0.2,                   // actual - consensus
      "surprise_pct": -0.0625,
      "surprise_z": -2.1,

      "is_actual": true,

      "good_if_higher": false,
      "interpretation": "better_than_expected", // better_than_expected | worse_than_expected | inline | mixed
      "interpretation_logic": "actual < consensus, good_if_higher=false",

      "reaction_10m_2y_yield_bp": -3.2,
      "reaction_10m_main_index_ret": 0.004,
      "reaction_10m_fx_pair": "DXY",
      "reaction_10m_fx_pair_ret": -0.003,
      "reaction_measured_from": "2025-11-14T13:30:00Z",
      "reaction_measured_to": "2025-11-14T13:40:00Z",
      "reaction_data_source": "5min_bar",

      "next_release_date": "2025-12-13",

      "source": "EODHD",
      "source_ref": "MACRO_US_CPI",
      "data_vintage": "T",
      "data_source_as_of": "2025-11-14"
    }
  ]
}
```

Notes:

- For upcoming events (no `actual` yet): set `is_actual = false`, `actual = null`, `surprise_* = null`, reaction fields `null`.  
- `window_start/window_end` define the inclusive calendar window for included events.

---

## 7. Equities Core

### 7.1 File path

- `equities_core.json`

### 7.2 Structure

```json
{
  "schema_version": "2025.11.14",
  "as_of_date": "2025-11-14",
  "as_of_time_utc": "2025-11-14T07:35:00Z",
  "data_vintage": "T-1_close",
  "generated_at_utc": "2025-11-14T07:37:12Z",

  "universe_meta": {
    "universe_name": "core_equities",
    "estimated_count": 1000,
    "source": "EODHD"
  },

  "equities": [
    {
      "security_id": {
        "ticker": "BARC",
        "exchange": "LSE",
        "isin": "GB0031348658",
        "eodhd_code": "BARC.LSE"
      },

      "name": "Barclays PLC",
      "country": "UK",
      "region": "UK",
      "sector": "Financials",
      "industry": "Banks",
      "currency": "GBP",

      "price_today": 1.720,
      "price_d1": 1.680,
      "price_w1": 1.640,
      "price_m1": 1.600,
      "price_m3": 1.520,
      "price_m6": 1.480,
      "price_y1": 1.400,

      "ret_d1": 0.0238,
      "ret_w1": 0.0488,
      "ret_m1": 0.0750,
      "ret_m3": 0.1316,
      "ret_m6": 0.1622,
      "ret_y1": 0.2286,

      "hi_52w": 1.800,
      "lo_52w": 1.200,
      "drawdown_from_hi_pct": -0.0444,

      "volume_today": 12500000,
      "avg_volume_20d": 11000000,
      "market_cap": 28000000000.0,

      "realised_vol_20d": 0.320,
      "realised_vol_60d": 0.295,

      "pe_ttm": 7.5,
      "pe_forward": 6.8,
      "pe_forward_period": "NTM",
      "pb": 0.6,
      "div_yield_ttm": 0.050,
      "div_yield_ttm_price": 1.720,
      "div_yield_forward": 0.055,
      "valuation_as_of": "2025-11-13",
      "valuation_source": "EODHD",

      "beta_vs_index": 1.20,
      "beta_reference_index": "FTSE_100",
      "beta_lookback_days": 252,
      "beta_source": "computed",

      "div_trailing_12m": 0.08,
      "div_trailing_12m_period_start": "2024-11-14",
      "div_trailing_12m_period_end": "2025-11-14",

      "div_forward_12m": 0.09,
      "div_forward_12m_basis": "estimated",   // declared | estimated | consensus

      "next_div_ex_date": "2025-12-05",
      "next_div_record_date": "2025-12-08",
      "next_div_pay_date": "2026-01-10",
      "next_div_amount": 0.03,
      "next_div_currency": "GBP",
      "next_div_type": "Interim",
      "next_div_status": "Confirmed",        // Confirmed | Announced | Expected

      "div_frequency": "Semi-annual",
      "div_frequency_actual_count_12m": 2,
      "div_payment_consistency": null,       // optional, 0–1 if implemented
      "div_growth_3y_cagr": null,            // optional

      "div_data_source": "EODHD",
      "div_data_as_of": "2025-11-13",

      "next_results_date": "2025-02-13",
      "next_results_time_local": "08:00",
      "next_results_timezone": "Europe/London",
      "next_results_time_utc": "2025-02-13T08:00:00Z",
      "next_results_type": "FY",
      "next_results_fiscal_year": "FY2025",
      "next_results_period_end": "2024-12-31",
      "next_results_status": "Confirmed",     // Confirmed | Estimated
      "next_results_announcement_method": "RNS",

      "last_results_date": "2024-08-08",
      "last_results_type": "HY",
      "last_results_fiscal_year": "FY2024",
      "last_results_eps_actual": 0.45,
      "last_results_eps_consensus": 0.42,
      "last_results_eps_surprise_pct": 0.071,
      "last_results_revenue_actual": 2450.0,
      "last_results_revenue_consensus": 2475.0,
      "last_results_revenue_surprise_pct": -0.010,
      "last_results_price_reaction_d0": 0.034,
      "last_results_price_reaction_d1": 0.012,

      "results_cadence": "Semi-annual",      // Semi-annual | Quarterly | Annual
      "results_avg_days_to_period_end": null,

      "results_data_source": "EODHD",
      "results_data_as_of": "2025-11-13"
    }
  ]
}
```
### 7.3 Derived CSV tables

The `equities_core.json` object is the canonical source. Two flat CSV tables are generated from it for use by the email renderer and GPT layer.

#### 7.3.1 Equity overview table

- File path: `out/data/equity_overview.csv`
- Grain: one row per equity in the core universe.

**Columns**

- `ticker` (string) – primary key, matches `security_id.ticker`.
- `isin` (string) – from `security_id.isin`.
- `name` (string) – issuer name.
- `exchange` (string) – trading venue, e.g. `XLON`, `XNAS`.
- `country` (string) – 2-letter ISO country code.
- `sector` (string) – sector / industry bucket.
- `currency` (string) – ISO-4217 trading currency.

- `price_today` (float) – latest adjusted close (`T_1_close`).
- `price_d1` (float) – previous trading day close.
- `price_w1` (float) – close one week ago.
- `price_m1` (float) – close one month ago.
- `price_m3` (float) – close three months ago.
- `price_m6` (float) – close six months ago.
- `price_y1` (float) – close one year ago.

- `ret_d1` (float) – 1-day total return vs `price_d1` (decimal, 0.05 = 5%).
- `ret_w1` (float) – 1-week total return.
- `ret_m1` (float) – 1-month total return.
- `ret_m3` (float) – 3-month total return.
- `ret_m6` (float) – 6-month total return.
- `ret_y1` (float) – 1-year total return.

- `hi_52w` (float) – 52-week high.
- `lo_52w` (float) – 52-week low.
- `drawdown_from_hi_pct` (float) – `(price_today / hi_52w) - 1` (decimal).

- `volume_today` (integer) – latest day’s volume.
- `avg_volume_20d` (integer) – 20-day average volume.
- `market_cap` (float) – market capitalisation in local currency.

- `realised_vol_20d` (float) – 20-day annualised realised vol (decimal).
- `realised_vol_60d` (float) – 60-day annualised realised vol (decimal).

- `pe_ttm` (float) – trailing P/E.
- `pe_forward` (float) – forward P/E.
- `pe_forward_period` (string) – e.g. `NTM`.
- `pbr` (float) – price / book.

- `div_yield_ttm` (float) – trailing cash dividend yield (decimal).
- `div_yield_forward` (float) – forward dividend yield (decimal).

- `beta_vs_index` (float) – beta vs reference index.
- `beta_reference_index` (string) – e.g. `FTSE_100`, `SPX`.
- `beta_lookback_days` (integer) – lookback window in trading days.

- `next_results_date` (date, `YYYY-MM-DD`) – next scheduled results date, if known.
- `next_results_type` (string) – `FY`, `HY`, `Q1`, etc.
- `next_results_status` (string) – `Confirmed` | `Estimated` | `None`.

_All numeric values are stored as raw floats; formatting (5 significant figures, % vs decimal, thousand separators) happens only at render time._

#### 7.3.2 Equity dividend aggregates

- File path: `out/data/equity_dividends_agg.csv`
- Grain: one row per equity with dividend history / forward dividends.
- Sources: `equities_core.json` + `dividend_events.json`.

**Columns**

- `ticker` (string) – primary key, matches `equity_overview.ticker`.

- `div_trailing_12m` (float) – total cash dividends over trailing 12 months, per share, in local currency.
- `div_trailing_12m_period_start` (date) – start of trailing window.
- `div_trailing_12m_period_end` (date) – end of trailing window.

- `div_forward_12m` (float) – expected cash dividends o

---

## 8. Dividend Events

### 8.1 File path

- `dividend_events.json`

### 8.2 Structure

```json
{
  "schema_version": "2025.11.14",
  "as_of_date": "2025-11-14",
  "as_of_time_utc": "2025-11-14T07:35:00Z",
  "data_vintage": "T-1_close",
  "generated_at_utc": "2025-11-14T07:37:12Z",

  "window_start": "2024-11-14",
  "window_end": "2026-11-14",

  "events": [
    {
      "event_id": "VOD_LSE_DIV_2025-12-05_0.045_INTERIM",
      "security_id": {
        "ticker": "VOD",
        "exchange": "LSE",
        "isin": "GB00BH4HKS39",
        "eodhd_code": "VOD.LSE"
      },

      "currency": "GBP",
      "gross_amount_per_share": 0.045,
      "net_amount_per_share": null,

      "ex_date": "2025-12-05",
      "record_date": "2025-12-08",
      "pay_date": "2026-01-10",
      "pay_date_actual": null,
      "announcement_date": "2025-11-10",

      "div_type": "Interim",
      "div_sequence": 2,
      "fiscal_year": "FY2025",
      "fiscal_period": "H2",

      "div_frequency_hint": "Semi-annual",
      "status": "Confirmed",                 // Confirmed | Announced | Paid | Cancelled

      "is_special": false,
      "is_scrip_eligible": false,

      "prior_year_same_div_amount": 0.042,
      "yoy_growth": 0.071,

      "withholding_tax_rate_default": 0.00,

      "source": "EODHD",
      "source_ref": "API_DIVIDENDS",
      "source_record_id": "12847563",
      "data_vintage": "T-1_close"
    }
  ]
}
```

Notes:

- `window_start/window_end` normally ±365 days around `as_of_date`.  
- `withholding_tax_rate_default` is jurisdictional default, not investor-specific.

---

## 9. Corporate Events (Results / Earnings)

### 9.1 File path

- `corporate_events.json`

### 9.2 Structure

```json
{
  "schema_version": "2025.11.14",
  "as_of_date": "2025-11-14",
  "as_of_time_utc": "2025-11-14T07:35:00Z",
  "data_vintage": "T-1_close",
  "generated_at_utc": "2025-11-14T07:37:12Z",

  "window_start": "2024-11-14",
  "window_end": "2026-11-14",

  "events": [
    {
      "event_id": "BARC_LSE_EARNINGS_FY2025_2026-02-13",

      "security_id": {
        "ticker": "BARC",
        "exchange": "LSE",
        "isin": "GB0031348658",
        "eodhd_code": "BARC.LSE"
      },

      "event_type": "Earnings",          // Earnings | TradingUpdate | CapitalMarketsDay | Other
      "results_type": "FY",              // FY | HY | Q1 | Q2 | Q3 | Q4
      "fiscal_year": "FY2025",
      "period_start": "2025-01-01",
      "period_end": "2025-12-31",

      "event_date": "2026-02-13",
      "event_date_is_estimate": false,
      "event_time_local": "08:00",
      "event_time_utc": "2026-02-13T08:00:00Z",
      "event_timezone": "Europe/London",
      "status": "Confirmed",             // Confirmed | Estimated | Completed | Cancelled

      "announcement_method": "RNS",
      "conference_call_scheduled": true,
      "conference_call_time_utc": "2026-02-13T09:00:00Z",

      "consensus_eps": 0.48,
      "consensus_revenue": 2600.0,
      "consensus_currency": "GBP",
      "consensus_data_source": "Bloomberg",
      "consensus_as_of": "2025-11-13",

      "source": "EODHD",
      "source_ref": "API_CORP_EVENTS",
      "source_record_id": "CORP_98234",
      "data_vintage": "T-1_close"
    }
  ]
}
```

---

## 10. AT1 Bonds

### 10.1 File path

- `at1_bonds.json`

### 10.2 Structure

```json
{
  "schema_version": "2025.11.14",
  "as_of_date": "2025-11-14",
  "as_of_time_utc": "2025-11-14T07:35:00Z",
  "data_vintage": "T-1_close",
  "generated_at_utc": "2025-11-14T07:37:12Z",

  "bonds": [
    {
      "instrument_id": {
        "isin": "XS1234567890",
        "ticker": "LLD_7.5_AT1",
        "issuer": "Lloyds Banking Group"
      },

      "currency": "USD",
      "issuer_country": "UK",
      "sector": "Financials",
      "subsector": "AT1",

      "coupon_type": "fixed_to_floating",  // fixed | floating | fixed_to_floating
      "coupon_rate": 0.075,
      "reset_spread_bp": 450.0,
      "reset_index": "5Y_USSWAP",

      "first_call_date": "2026-01-31",
      "next_call_date": "2026-01-31",
      "maturity_date": null,
      "perpetual": true,

      "principal_amount": 1000000.0,
      "minimum_denomination": 200000.0,

      "price_today": 89.50,
      "price_d1": 91.40,
      "price_w1": 92.20,
      "price_m1": 94.00,
      "price_y1": 96.50,

      "total_return_1d": -0.021,
      "total_return_w1": -0.029,
      "total_return_m1": -0.047,
      "total_return_y1": -0.073,

      "ytc": 0.089,
      "ytm": null,
      "ytw": 0.089,
      "ytw_measure": "YTC",      // YTC | YTM

      "distance_to_trigger_pct": 4.2, // CET1 buffer vs trigger (in percentage points)
      "cet1_ratio": 12.0,
      "cet1_trigger": 7.8,

      "issuer_rating_snp": "BBB+",
      "issuer_rating_moodys": "Baa1",
      "instrument_rating_snp": "BB+",

      "years_to_first_call": 0.12,
      "call_probability_implied": 0.30,

      "data_source": "EODHD",
      "data_source_ref": "AT1_LL_7.5",
      "data_source_as_of": "2025-11-13"
    }
  ]
}
```

Notes:

- `distance_to_trigger_pct` is the gap between current CET1 and the AT1 trigger level, in **percentage points**, not relative %.  
- `call_probability_implied` is optional; may be `null` until modelled.

---

## 11. Daily Brief – “4 Things That Matter”

### 11.1 File path

- `daily_brief_top4.json`

### 11.2 Structure

```json
{
  "schema_version": "2025.11.14",
  "as_of_date": "2025-11-14",
  "as_of_time_utc": "2025-11-14T07:35:00Z",
  "data_vintage": "T-1_close",
  "generated_at_utc": "2025-11-14T07:37:12Z",

  "brief_type": "TOP_4",   // TOP_4 | QUIET_DAY | WEEKLY_WRAP
  "top_4": [
    {
      "rank": 1,
      "category": "macro",
      "score": 108.0,
      "subscores": {
        "magnitude": 72.0,
        "relevance": 24.0,
        "timing": 12.0
      },

      "title": "US CPI miss opens Fed cut window",
      "fact": "US headline CPI printed 3.0% vs 3.2% consensus and 3.4% prior, the largest downside surprise in four months.",
      "why_it_matters": "This pulls forward market expectations for Fed cuts and is driving a bull-flattening move in US and UK curves.",

      "action": {
        "bucket": "PREPARE",      // ACT_TODAY | PREPARE | MONITOR | NOTE_ONLY
        "deadline_utc": "2025-11-18T20:00:00Z",
        "summary": "Define preferred duration tilt in gilts and Treasuries ahead of next week's Fed meeting; no rebalancing today.",
        "owner": "Michael",
        "instrument_refs": [
          {
            "type": "yield_curve",
            "id": "US_TREASURY_2Y"
          },
          {
            "type": "yield_curve",
            "id": "US_TREASURY_10Y"
          }
        ]
      },

      "source_refs": [
        {
          "file": "macro_calendar.json",
          "kind": "macro_event",
          "id": "US_CPI_HEADLINE_2025-11-14"
        },
        {
          "file": "yield_US.json",
          "kind": "yield_row",
          "id": "US_2Y"
        }
      ]
    }
  ],

  "message": null
}
```

### 11.3 Field definitions

- `brief_type` (string enum)
  - `"TOP_4"` – normal daily brief with up to 4 items.
  - `"QUIET_DAY"` – no items pass significance threshold; `top_4` **must** be `null`.
  - `"WEEKLY_WRAP"` – reserved for future weekly rollup.

- `top_4`  
  - For `TOP_4`: array of 1–4 `DailyBriefItem`, sorted by `rank`.  
  - For `QUIET_DAY`: `null`.

- `message`  
  - For quiet days: e.g. `"Quiet session: no high-significance moves or events across yields, FX, equities, or macro requiring decisions today."`  
  - Otherwise usually `null`.

#### `DailyBriefItem`

- `rank` (int) – 1..4, unique.  
- `category` (enum) – one of:
  - `"macro"`, `"yield"`, `"fx"`, `"equity_index"`, `"single_stock"`,
    `"dividend"`, `"results"`, `"at1"`, `"commodity"`, `"other"`.
- `score` (number) – deterministic significance score from scoring engine.  
- `subscores` (object, optional) – typically `{ "magnitude": ..., "relevance": ..., "timing": ... }`.

- `title` (string) – short headline.  
- `fact` (string) – factual description with numbers/dates.  
- `why_it_matters` (string) – 1–2 sentences of implications.

#### `action` object

- `bucket` (enum) – `"ACT_TODAY" | "PREPARE" | "MONITOR" | "NOTE_ONLY"`.  
- `deadline_utc` (ISO datetime or `null`) – action horizon where relevant.  
- `summary` (string) – one-sentence implication / instruction.  
- `owner` (string, optional).  
- `instrument_refs` (array of `InstrumentRef`, optional).

#### `InstrumentRef`

```json
{
  "type": "equity",
  "id": "BARC.LSE"
}
```

- `type` – `"equity" | "equity_index" | "yield_curve" | "fx_pair" | "fx_cross" | "commodity" | "at1" | "other"`.  
- `id` – identifier consistent with the referenced canonical file.

#### `source_refs`

```json
{
  "file": "macro_calendar.json",
  "kind": "macro_event",
  "id": "US_CPI_HEADLINE_2025-11-14"
}
```

- `file` – name of canonical file.  
- `kind` – record type within that file (`"macro_event"`, `"yield_row"`, `"fx_pair"`, `"equity"`, `"dividend_event"`, `"corporate_event"`, `"at1_bond"`, `"index"`, `"commodity"`, `"other"`).  
- `id` – event/row identifier (`event_id`, maturity code, pair code, etc).

### 11.4 Guardrails

- `score` and `subscores` are **deterministic** (rule-based), not LLM-generated.  
- LLM is allowed to generate `title`, `fact`, `why_it_matters`, and `action.summary`, but not numeric scoring.  
- Diversity filters (implemented in code) should prevent all 4 items being from one category, where possible.

---

End of `DATA_SCHEMA_2025-11-14.md`.
