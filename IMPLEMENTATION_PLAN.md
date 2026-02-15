# Outbound Prospecting System Implementation Plan

This plan outlines the steps for building a fully automated outbound prospecting engine for Engram.

## Phase 1: Strategy & Definition
- [x] **Step 1: Define Ideal Customer Profile (ICP)**
    - Translate target customers into concrete signals.
    - Assign points to signals for automated scoring.
    - Create `ICP_DEFINITION.md` and `scoring_config.json`.

## Phase 2: Discovery & Data Acquisition
- [x] **Step 2: Set up project environment and core infrastructure**
    - Python environment initialized.
    - Modular project structure created.
    - Database schema implemented with SQLModel.
    - APScheduler integrated for recurring tasks.
- [x] **Step 3: Company Discovery Engine**
    - Source discovery (Search engines, Partner directories, AI lists).
    - Automated extraction and normalization of domains.
    - Duplicate prevention and database storage.
- [x] **Step 4: Web Scraper & Signal Detector**
    - Scrape homepage, docs, and blogs.
    - Match keywords and patterns from `scoring_config.json`.
    - Calculate fit score.

## Phase 3: Lead Research & Qualification
- [x] **Step 5: Decision Maker Identification**
    - Identify technical roles (CTO, VP Eng, Head of AI).
    - Verify roles via LinkedIn/Apollo/etc.
- [x] **Step 6: Contact Info Retrieval**
    - Email finding and verification.

## Phase 4: Outreach & Automation
- [x] **Step 7: Personalized Outreach Generation**
    - LLM-based template generation using detected signals.
- [x] **Step 8: Automated Sending & Tracking**
    - Integration with email provider.
    - Classification of replies (Interest vs. Objection).

## Phase 5: Optimization & Scaling
- [x] **Step 9-14: Pipeline Integration, Compliance & Monitoring**
    - Automatic sequencing with timed follow-ups.
    - Reply classification (interest, deferral, referral, opt-out).
    - Suppression lists and data protection compliance.
- [x] **Step 15: Continuous Expansion & Refinement (Self-Sustaining Engine)**
    - **Outcome Tracker**: Correlates outreach results with ICP signals to identify what predicts engagement.
    - **Scoring Refiner**: Automatically adjusts signal weights based on reply/interest/opt-out rates per signal. Includes min sample thresholds, max change caps, and backup trails.
    - **Re-scoring Engine**: Detects when the scoring model changes and re-evaluates all companies. Also re-scores stale entries periodically.
    - **Discovery Expander**: Extracts patterns from successful leads (positive replies) and generates new search queries targeting similar companies. Creates a discovery flywheel.
    - **Pipeline Health Monitor**: Tracks leads through every stage, calculates conversion rates, detects bottlenecks, and generates alerts.
    - **Full Pipeline Orchestrator**: End-to-end cycle (Discovery → Scrape → Score → Enrich → Outreach → Inbox → Compliance → Track) on a recurring schedule.
    - **12 Recurring Scheduled Tasks**: Core pipeline (6 tasks at 15–120 min intervals) + Refinement (6 tasks at 2h–24h intervals).

