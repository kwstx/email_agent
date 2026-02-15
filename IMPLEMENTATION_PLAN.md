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
- [ ] **Step 5: Decision Maker Identification**
    - Identify technical roles (CTO, VP Eng, Head of AI).
    - Verify roles via LinkedIn/Apollo/etc.
- [ ] **Step 6: Contact Info Retrieval**
    - Email finding and verification.

## Phase 4: Outreach & Automation
- [ ] **Step 7: Personalized Outreach Generation**
    - LLM-based template generation using detected signals.
- [ ] **Step 8: Automated Sending & Tracking**
    - Integration with email provider.
    - Classification of replies (Interest vs. Objection).

## Phase 5: Optimization & Scaling
- [ ] **Step 9: Pipeline Integration**
    - Automatic CRM/Sheet updates.
- [ ] **Step 10: Continuous Learning**
    - Feedback loop based on reply rates.
