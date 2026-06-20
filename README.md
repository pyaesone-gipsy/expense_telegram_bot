# Telegram Expense Receipt Bot

This project is a Claude Code-friendly Telegram bot for expense tracking. It accepts receipt screenshots, extracts text with OCR, categorizes expenses automatically, and exports records as CSV.

## Files included
- `.mcp.json` — metadata for Claude Code project tools
- `.claude/skills/expense-bot/SKILL.md` — skill definition for the agent
- `.claude/agents/expense-bot.md` — agent metadata
- `bot.py` — Telegram bot implementation
- `slides/pitch.md` — 6-slide project pitch
- `report.md` — project report summary

## Setup
1. Install Python dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Install Tesseract OCR on your system:
   - Windows: https://github.com/tesseract-ocr/tesseract
   - Linux/Mac: `sudo apt install tesseract-ocr` or equivalent
3. Set the Telegram bot token:
   ```bash
   set TELEGRAM_TOKEN=your_bot_token
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

## Usage
- Send `/start` to the bot.
- Upload a receipt photo.
- Use `/export` to download expense history as a CSV file.

## Notes
This repository is designed as a project starter for the Vibe Code Tours chapter 3 assignment. It can be extended with Claude prompt integration and more advanced receipt parsing rules.
