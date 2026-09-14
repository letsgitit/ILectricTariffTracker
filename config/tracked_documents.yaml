# Tracked regulatory tariff documents — ComEd & Ameren Illinois, C&I electric classes.
#
# Each entry is one PDF/tariff sheet that gets fetched on schedule, hashed, and
# (optionally) parsed for specific dollar-figure line items via regex patterns.
#
# `line_item_patterns` are OPTIONAL. Without them, the tracker still detects
# "this document changed" via content hash — it just won't tell you which
# specific number moved. Tariff PDFs are inconsistent enough in layout that
# these patterns need tuning per document; the ones below are a starting point
# based on the actual current documents, not guarantees they'll match every
# future revision. Treat this file as a seed you'll extend, not a finished list.
#
# label: human name for the line item
# pattern: regex with one capture group around the dollar figure

- id: comed-rate-rds
  utility: ComEd
  rate_class: "All C&I delivery classes (Small/Medium/Large/Very Large Load, etc.)"
  name: "Rate RDS - Retail Delivery Service"
  url: "https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/blt000eeaac79942ad7/658c50c27a2e06000abc41c7/06_Rate_RDS.pdf?branch=prod_alias"
  doc_type: pdf
  notes: >
    ComEd bundles all non-residential delivery classes into this one tariff.
    VERIFIED (fetched and read the live PDF while building this): Rate RDS
    itself is qualitative — it defines each charge type by name and says the
    actual dollar figure "is equal to the applicable [charge] listed in the
    Delivery Service Charges Informational Sheets." So this document is
    useful for catching structural/legal changes (new charge types, changed
    eligibility, new riders referenced) but will NOT move when a dollar
    figure changes — that lives in the "Summary of Typical Nonresidential
    Line Item Charges" doc tracked separately below. Track both.
  line_item_patterns: []

- id: comed-nonresidential-line-items
  utility: ComEd
  rate_class: "Watt-Hour, Small/Medium/Large/Very Large/Extra Large Load, High Voltage, Lighting"
  name: "Summary of Typical Nonresidential Line Item Charges"
  url: "https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/blt2a55fd60b0fa4cf2/679124a91d0aeed2124fed68/ADA_Summary_of_Typical_Nonresidential_Line_Item_Changes.pdf?branch=prod_alias"
  doc_type: pdf
  notes: >
    VERIFIED (fetched and read the live PDF): this is ComEd's actual
    dollar-figure table for nonresidential delivery classes — Customer
    Charge, Standard Metering Charge, Secondary/Primary Voltage Distribution
    Facilities Charge, Transformer Charge, IEDT — one row per delivery
    class. Republished annually with each January billing period (URL path
    is versioned by ComEd, so if this stops resolving one January, check
    comed.com/Rates for the current year's version and update the url
    field here). This is the single best document to catch actual C&I
    fixed-charge changes.

    STALE AS OF THIS WRITING: the fetched copy is the January 2025 vintage
    (Medium Load Secondary Voltage DFC $14.94/kW). A real Myd Monte LLC
    invoice (Medium Load, hourly-priced) shows a different DFC path across
    2026: $12.94/kW (service starting 2026-01-13) -> $13.03/kW (starting
    2026-03-12) -> $13.02/kW (starting 2026-05-12), with Customer Charge and
    Standard Metering Charge moving in step. Third-party reporting (Ltd
    Solar, July 2026) corroborates that ComEd's delivery rate rose in
    January 2026 following a $243M ICC-approved rate case, though the
    invoice's own change lands in March, not January, so the two aren't
    confirmed to be the same event without the real 2026 sheet in hand.
    I searched repeatedly for a live 2026 edition of this document and could
    not find a fetchable URL — ComEd's CDN paths use unguessable hashes per
    file, so this url field still points at the 2025 vintage until someone
    finds and swaps in the current one from comed.com/Rates. Track the
    invoice-derived numbers above as the best current source in the
    meantime; don't treat the $14.94/kW figure below as current.

    Also worth knowing: the invoice's "Peak Period DFC" / "Off Peak DFC"
    labels are NOT a separate tariff or rider — confirmed by fetching Rate
    BESH (tracked below), which defines the Distribution Facilities Charge
    identically to Rate RDS, with no on/off-peak split named anywhere in the
    tariff text. The split is ComEd's own billing presentation of the same
    Secondary Voltage DFC, computed off on-peak demand only (per the "Update"
    note ComEd prints on the bill itself) — not a distinct charge to track
    separately.
  line_item_patterns:
    - label: "Small Load Delivery Class - Customer Charge ($/Mo)"
      pattern: 'Small Load Delivery Class \(0 - 100 kW\)\s*\$([\d,]+\.\d{2})'
    - label: "Small Load Delivery Class - Secondary Voltage DFC ($/kW)"
      pattern: 'Small Load Delivery Class \(0 - 100 kW\)\s*\$[\d,]+\.\d{2}\s*\$[\d,]+\.\d{2}\s*\$([\d,]+\.\d{2})'
    - label: "Medium Load Delivery Class - Customer Charge ($/Mo)"
      pattern: 'Medium Load Delivery Class \(>100 - 400 kW\)\s*\$([\d,]+\.\d{2})'
    - label: "Medium Load Delivery Class - Secondary Voltage DFC ($/kW)"
      pattern: 'Medium Load Delivery Class \(>100 - 400 kW\)\s*\$[\d,]+\.\d{2}\s*\$[\d,]+\.\d{2}\s*\$([\d,]+\.\d{2})'
    - label: "Large Load Delivery Class - Customer Charge ($/Mo)"
      pattern: 'Large Load Delivery Class \(>400 - 1000 kW\)\s*\$([\d,]+\.\d{2})'
    - label: "Large Load Delivery Class - Secondary Voltage DFC ($/kW)"
      pattern: 'Large Load Delivery Class \(>400 - 1000 kW\)\s*\$[\d,]+\.\d{2}\s*\$[\d,]+\.\d{2}\s*\$([\d,]+\.\d{2})'
    - label: "Very Large Load Delivery Class - Customer Charge ($/Mo)"
      pattern: 'Very Large Load Delivery Class\s*\(>1000 - 10,000 kW\)\s*\$([\d,]+\.\d{2})'

- id: comed-rate-besh
  utility: ComEd
  rate_class: "Hourly-priced accounts (Rate BESH / Rider PPO) across all delivery classes"
  name: "Rate BESH - Basic Electric Service Hourly Pricing"
  url: "https://azure-na-assets.contentstack.com/v3/assets/blt3ebb3fed6084be2a/bltd1ac833ef55f82e3/658c529d6fa3d5000db76f9d/05_Rate_BESH.pdf?branch=prod_alias"
  doc_type: pdf
  notes: >
    VERIFIED (fetched and read the live PDF). Added because Myd Monte LLC's
    account is "Commercial Hourly" (Rate BESH supply + Rate RDS delivery) -
    Rate RDS alone doesn't cover how this account's supply-side charges
    (Capacity Charge, PJM Services Charge / labeled Transmission Services
    Charge on the bill, Misc Procurement Components Charge, Hourly Purchased
    Electricity Adjustment) get set and revised. Like Rate RDS, this tariff
    is qualitative — dollar figures aren't in the tariff text itself, they're
    filed periodically with the ICC "for informational purposes" per this
    tariff's own Informational Filings section. Confirmed schedule relevant
    to this account: Capacity Charge and PJM Services Charge both reset
    for the June billing period (per PJM Planning Year) and again for
    September, which matches the Myd Monte invoice showing a coordinated
    reset in Capacity Charge rate/basis, Transmission Services Charge rate,
    and Misc Procurement rate all starting the 2026-05-12 billing period.
    Hash-only for now — no separate numeric document located for these
    figures; the invoice itself is the most reliable current source.
  line_item_patterns: []

- id: comed-schedule-of-rates
  utility: ComEd
  rate_class: "All classes (reference index)"
  name: "ComEd Entire Schedule of Rates for Electric Service"
  url: "https://www.comed.com/Rates"
  doc_type: html_index
  notes: >
    This is the index/landing page (not the ~800pg combined PDF itself, which
    is too large to diff line-by-line). Track this page's list of linked PDFs
    to catch newly filed tariff sheets ComEd hasn't announced elsewhere.
  line_item_patterns: []

- id: ameren-ds2
  utility: "Ameren Illinois"
  rate_class: "DS-2 (Small General Delivery Service, <150 kW)"
  name: "Rate DS-2 - Small General Delivery Service"
  url: "https://www.ameren.com/-/media/rates/files/illinois/aiel12rtds2.pdf"
  doc_type: pdf
  line_item_patterns: []

- id: ameren-ds3
  utility: "Ameren Illinois"
  rate_class: "DS-3 (General Delivery Service, 150kW-1000kW)"
  name: "Rate DS-3 - General Delivery Service"
  url: "https://www.ameren.com/-/media/rates/files/illinois/aiel13rtds3.pdf"
  doc_type: pdf
  line_item_patterns: []

- id: ameren-ds4
  utility: "Ameren Illinois"
  rate_class: "DS-4 (Large General Delivery Service)"
  name: "Rate DS-4 - Large General Delivery Service"
  url: "https://www.ameren.com/-/media/rates/files/illinois/aiel14rtds4.pdf"
  doc_type: pdf
  line_item_patterns: []

- id: ameren-pbr-r
  utility: "Ameren Illinois"
  rate_class: "DS-1 through DS-6 (Base Rate Revenue mechanism)"
  name: "Rate PBR-R - Performance-Based Ratemaking Reconciliation"
  url: "https://www.ameren.com/-/media/rates/files/illinois/aiel8rtpbrr.ashx"
  doc_type: pdf
  notes: >
    Governs the annual adjustment factor layered on top of DS-2/3/4 base
    delivery charges. Changes here move effective rates without a new DS-x
    tariff filing, so it's worth tracking independently.
  line_item_patterns: []

- id: ameren-mapp-delivery-charges
  utility: "Ameren Illinois"
  rate_class: "DS-3, DS-4 (Customer/Meter charges by voltage level)"
  name: "Rate MAP-P - Delivery Charges Informational Sheet"
  url: "https://www.ameren.com/-/media/rates/illinois/non-residential/electric-rates/distribution-delivery/aiifmapp116.ashx"
  doc_type: pdf
  notes: >
    This informational sheet carries the actual current dollar tables
    (Customer Charge / Meter Charge by meter voltage tier) for DS-3 and
    DS-4 and is republished whenever those figures change — best single
    document for catching numeric changes to Ameren C&I fixed charges.
  line_item_patterns:
    - label: "DS-3 Customer Charge (Secondary Voltage)"
      pattern: 'DS-3[^$]{0,400}?Secondary Meter Voltage[^$]{0,40}\$?\s*([\d,]+\.\d{2})'
    - label: "DS-4 Customer Charge (Secondary Voltage)"
      pattern: 'DS-4[^$]{0,400}?Secondary Meter Voltage[^$]{0,40}\$?\s*([\d,]+\.\d{2})'
