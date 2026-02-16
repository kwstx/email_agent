# SMB Filtering & Company Size Qualification Guide

This guide provides step-by-step instructions on how to implement filters to ensure your outreach targeting focuses on **Small to Medium-sized Businesses (SMBs)** rather than large enterprises.

---

## Step 1: Update Scoring Configuration
The most direct way to filter by size is to add size-related signals to your `scoring_config.json`. 

### How to implement:
1. Open `scoring_config.json`.
2. Add a new category under `"signals"` called `"COMPANY_SIZE"`.
3. Add positive points for SMB indicators and negative/disqualification points for Enterprise indicators.

**Example Addition:**
```json
"COMPANY_SIZE": {
  "SMB_INDICATOR": {
    "description": "High-growth SMB/Startup signals",
    "points": 5,
    "keywords": [
      "early-stage", "Series A", "Series B", "venture-backed", 
      "fast-growing team", "boutique", "founded in 2024", "scrappy"
    ]
  },
  "ENTERPRISE_DISQUALIFIER": {
    "description": "Large Enterprise indicators (Negative points)",
    "points": -20,
    "keywords": [
      "Fortune 500", "Fortune 100", "10,000+ employees", 
      "global presence", "multi-national", "NASDAQ", "NYSE",
      "legacy infrastructure", "corporate social responsibility"
    ]
  }
}
```

---

## Step 2: Refine Discovery Search Queries
Filter the companies *before* they even enter your database by modifying the search queries in the discovery engine.

### How to implement:
1. Open `src/scraping/discovery.py`.
2. Locate the `queries` list in the `if __name__ == "__main__":` block (or wherever you define your search logic).
3. Append size-specific descriptors to your industry keywords.

**Recommended Changes:**
- **From:** `"AI agent orchestration platform startups"`
- **To:** `"AI agent startups under 100 employees"` or `"seed stage AI agent companies"`
- **Add specific domain filters:** `"site:ycombinator.com 'AI agents'"` or `"site:crunchbase.com 'series A' 'AI'"`

---

## Step 3: Implement Crawler Heuristics
You can detect company size by looking for specific "structural" signals on the website that are common in SMBs vs. Enterprises.

### How to implement:
1. Open `src/scraping/crawler.py`.
2. In the `_find_signal_links` method, look for links that only SMBs or Only Enterprises typically have.

**Logic to add:**
- **SMB Signal:** Link text contains "Book a Demo" (directly) or "Meet the Founders."
- **Enterprise Signal:** Link text contains "Investor Relations," "ESG Report," "Global Locations," or "Procurement."

---

## Step 4: Careers Page Intensity
The intensity of hiring for specific roles often correlates with company size and stage. SMBs are usually hiring "Founding" or "Lead" roles.

### How to implement:
1. Modify `src/scoring/detector.py` to give extra weight if the careers page contains "Founding" or "First".
2. Add these keywords to your `HIRING_ACTIVITY` category in `scoring_config.json`.

---

## Step 5: External API Integration (Advanced)
For 100% accuracy, integrate with a real-time data provider like Apollo, Clearbit, or Hunter.io.

### How to implement:
1. Create a new enrichment module `src/enrichment/size_verification.py`.
2. Use an API call to fetch the `employee_count`.
3. Update the `Company` model in `src/storage/models.py` to include an `employee_count` field.
4. Add a hard stop in `main.py` to skip companies with > 500 employees.

**Python Blueprint:**
```python
def verify_size(domain: str):
    # Example using a mock API call
    response = requests.get(f"https://api.provider.com/v1/companies/{domain}")
    size = response.json().get("employee_count")
    return size < 500
```

---

## Summary of Changes
| Method | Speed | Accuracy | Complexity |
| :--- | :--- | :--- | :--- |
| **Scoring Config** | Fast | Medium | Low |
| **Search Queries** | Fast | Low | Low |
| **Crawler Heuristics**| Medium | Medium | Medium |
| **External APIs** | Slow | High | High |
