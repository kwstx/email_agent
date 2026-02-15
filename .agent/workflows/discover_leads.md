---
description: Automatically discover new companies for the lead pool
---

### Discovery Workflow

This workflow triggers the automated discovery engine to find new companies building AI agents, copilots, and LLM infrastructure.

1. **Configure Search Queries** (Optional)
   Edit `src/scraping/discovery.py` to add or refine search queries or manual lead lists.

2. **Run Discovery Engine**
// turbo
```powershell
$env:PYTHONPATH="."; python src/scraping/discovery.py
```

3. **Verify Results**
Check the database to see the newly added leads.
```powershell
# Since sqlite3 might not be available, you can use a python script to count
python -c "from src.storage.db import get_session; from src.storage.models import Company; session=get_session(); print(f'Total Companies: {len(session.query(Company).all())}')"
```

The discovery engine prevents duplicates by checking the company domain before inserting.
