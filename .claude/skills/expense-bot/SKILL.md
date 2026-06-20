# Expense Bot Skill

## Purpose
This Claude Code skill helps build and operate a Telegram expense receipt bot. It is designed to:

- Accept receipt screenshots via Telegram.
- Extract text from receipt images using OCR.
- Normalize expense lines into vendor, date, amount, and category.
- Automatically categorize expenses.
- Export transaction history as CSV.

## Usage
Use this skill to:

1. Generate prompts for receipt text parsing.
2. Define category mapping and expense rules.
3. Review or improve bot responses for different receipt formats.
4. Explain how to export data and summarize spend by category.

## Prompts
Sample prompt for the skill:

> You are an expense-tracking assistant. Given text extracted from a receipt image, return a JSON array of expense items. Each item should include `description`, `amount`, `date` (if present), and `category`.

Example output format:

```json
[
  {
    "description": "Coffee and sandwich",
    "amount": 6.75,
    "date": "2026-06-18",
    "category": "food"
  }
]
```

## Notes
- This skill is intentionally simple so it can be adapted to local OCR, Claude prompts, or another LLM pipeline.
- For better classification, extend the category list and add vendor-specific rules.
