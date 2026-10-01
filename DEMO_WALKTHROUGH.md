# Sales Intelligence Platform — Demo Walkthrough

**IMA AI Pod 1 | Gabriel Solis & Ethan Doehler**

---

## What This Tool Does

It monitors companies weekly, filters the noise, and tells a Strategy& partner exactly what happened, why it matters, and what to do about it — connected to a specific S& capability.

We'll walk through the pipeline using **Boeing** as the example.

---

## Step 1: Collect News

Every week, the system pulls news from multiple sources — Google News, defense publications, the Federal Register, SEC filings, and government contract databases.

**For Boeing this week:** ~250 raw articles and filings came in from across these sources.

Most of it is noise — stock price articles, analyst ratings, consumer aviation content, duplicate coverage of the same story from different outlets.

---

## Step 2: Filter to What's Actionable

AI reads every article and asks one question: **does this create a need for a specific S& capability?**

To answer that, it uses the S& capability taxonomy for Aerospace & Defense — the actual list of services we offer in this sector.

**For Boeing:** 250 raw articles → **8 curated signals**. Everything else was filtered out.

Each surviving signal gets tagged with:
- The **exact S& capability** it maps to
- **Why it matters** for Boeing specifically
- A **suggested action** for the partner

Example signal that made it through:
> **[Manufacturing Footprint Optimization]** Navy Chooses Boeing to Build Next-Generation Jet Fighter
> *Why it matters:* Dual sixth-gen fighter wins require immediate facility investment and capacity planning across defense production sites.

Example signal that got filtered out:
> "RBC Capital raises Aptiv target to $90, maintains Outperform" — analyst commentary, not actionable.

---

## Step 3: Compare Against the 12-Month Baseline

When Boeing was first added, the system built an **annual baseline** — a 12-month timeline of the major events, analyzed into strategic themes.

Boeing's baseline themes include: production recovery, Spirit AeroSystems reintegration, $10B cash flow gap, China market loss, labor normalization.

This week's signals get compared against that baseline:

**Accelerated this week:**
- Defense portfolio re-rating — the F/A-XX win alongside F-47 makes Boeing the sole holder of both sixth-gen fighter programs
- Supply chain stress — three concurrent defense programs now compete for the same supplier base

**New this week (not in the baseline):**
- FAA delays 737 MAX 10 certification over a software issue — regulatory risk not previously weighted

---

## Step 4: Connect to Financials

The system has Boeing's financial analysis (from SEC filings) and knows where Boeing ranks vs. peers in the A&D sector.

This week, the financial cross-reference connects the news to the numbers:
> "The dual fighter wins add ~$40B in long-term defense backlog, but Boeing's operating margin (4.8%) already ranks near the bottom of the sector. Absorbing two concurrent development programs without margin improvement requires the kind of operational restructuring S& specializes in."

**Note on the financial benchmark:** The current model is an AI estimate based on SEC XBRL filings. We know EUR has a more robust benchmarking model that could eventually be integrated to improve this.

---

## Step 5: Add PwC Relationship Context

The system pulls from People Connector and Salesforce to identify:
- **GRP:** Chris Tierney (Partner)
- **Active PwC engagements:** 8 open engagements at Boeing (cyber, Workday HCM, data modernization, AI governance)
- **Strategy& footprint:** One active S& engagement (AI Governance & Strategy Support, closing Sep 29)

This means PwC is deeply embedded at Boeing, but almost entirely in tech/compliance — not in the strategic core of the turnaround.

---

## Step 6: Produce the Weekly Briefing

Everything combines into one document:

**The card (what the partner sees first):**
> **Boeing Company** — Act Now (9/10)
> Dual sixth-gen fighter wins create manufacturing footprint pressure
> *Opportunity:* Manufacturing footprint optimization engagement spanning F-47, F/A-XX, and F-15EX programs
> *Action:* Chris Tierney should convene an internal S& defense capability team this week

**The full report** (click to expand) includes:
- Baseline delta — what changed vs. the 12-month trajectory
- All 8 curated signals with taxonomy tags
- Industry context — sector-wide A&D signals
- Financial cross-reference — how the news connects to the numbers
- The specific opportunity — capability, why now, Phase 1 scope
- Who should act — by name, with email
- Confidence assessment — scored on 5 dimensions

---

## The Confidence Rubric

Every briefing gets a standardized score so the partner knows how much to trust the recommendation.

| Dimension | What It Measures | Boeing This Week |
|---|---|---|
| Signal Strength | One article or multiple corroborating sources? | 2/2 — WSJ, Breaking Defense, Janes all confirm |
| Financial Evidence | Does the financial data support the need? | 2/2 — 4.8% op margin, $10B cash gap |
| Timing Urgency | Is there a deadline or forcing function? | 2/2 — Q4 production planning gates closing |
| Taxonomy Fit | Does this map to a specific S& capability? | 2/2 — Manufacturing Footprint Optimization |
| Baseline Alignment | Does this fit the 12-month trajectory? | 1/2 — accelerates defense theme, new dual-program angle |

**Total: 9/10 — Act Now**

---

## The Portfolio View

Partners don't cover one company — they cover many. The portfolio report shows all companies as cards, ranked by confidence:

| Company | Score | Opportunity |
|---|---|---|
| **Boeing** | 9/10 Act Now | Manufacturing Footprint Optimization |
| **Aptiv** | 8/10 Act Now | Separation & Carve-out (VersaGen spin-off) |
| **Duke Energy** | 8/10 Act Now | Integration (SC merger + NC generation strategy) |

Cross-portfolio themes and specific weekly actions are generated across the selected companies.

---

## What Makes This Different

1. **It's selective** — not a news dump. Only signals that map to an S& capability survive.
2. **It connects news to action** — every signal comes with a "why it matters" and "what to do."
3. **It compares against a baseline** — the partner sees what *changed*, not just what happened.
4. **It's scored** — the confidence rubric is standardized across all companies, so priorities are clear.
5. **It names names** — who at PwC should act, who at the client to talk to, what the Salesforce pipeline looks like.
