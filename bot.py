import csv
import json
import os
import re
from datetime import datetime

from telegram import Bot, InputFile, Update
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, CallbackContext

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.json")

CATEGORY_KEYWORDS = {
    "food": ["coffee", "cafe", "restaurant", "dinner", "lunch", "breakfast", "meal", "pizza", "burger"],
    "transport": ["taxi", "uber", "grab", "bus", "train", "transport", "fare", "petrol", "gas"],
    "shopping": ["mall", "shop", "store", "shopping", "clothes", "electronics"],
    "utilities": ["electricity", "water", "internet", "phone", "bill", "utility"],
    "groceries": ["supermarket", "grocery", "market", "vegetable", "fruit", "rice", "meat"],
    "health": ["pharmacy", "clinic", "hospital", "doctor", "medicine", "drugstore"],
    "other": []
}

PROVIDER_KEYWORDS = {
    "KBZ Pay": ["kbz", "kbz pay", "kbzpay"],
    "Wave Pay": ["wave", "wave pay", "wavepay"],
    "CB Bank": ["cb bank", "cbbank", "cb bank/pay"],
    "Mytel": ["mytel"],
    "CB Pay": ["cb pay", "cbpay"],
}

AMOUNT_REGEX = re.compile(r"\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})|[0-9]+(?:\.[0-9]{1,2}))\b")
DATE_REGEX = re.compile(r"\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(EXPENSES_FILE):
        with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)


def load_expenses():
    ensure_data_dir()
    with open(EXPENSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_expenses(expenses):
    ensure_data_dir()
    with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(expenses, f, indent=2)


def detect_provider(text: str) -> str:
    for provider, keywords in PROVIDER_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return provider
    return "Unknown"


def format_mmk(amount: float) -> str:
    return f"{amount:,.0f} MMK"


def parse_expense_text(text: str) -> dict:
    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    amount = None
    description = "Receipt"
    date = None

    for line in lines:
        if date is None:
            match = DATE_REGEX.search(line)
            if match:
                raw = match.group(1)
                try:
                    if "-" in raw:
                        date = datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
                    else:
                        date = datetime.strptime(raw, "%d/%m/%Y").date().isoformat()
                except ValueError:
                    pass
        found = AMOUNT_REGEX.findall(line)
        if found:
            for candidate in reversed(found):
                cleaned = candidate.replace(",", "")
                value = float(cleaned)
                if value > 0:
                    amount = value
                    break
        if any(keyword in line for keyword in ["total", "amount", "paid", "subtotal", "balance"]):
            description = line.title()

    if amount is None and lines:
        for line in reversed(lines):
            match = AMOUNT_REGEX.search(line)
            if match:
                amount = float(match.group(1).replace(",", ""))
                break

    if date is None:
        today = datetime.today().date().isoformat()
        date = today

    raw_text = " ".join(lines)
    category = categorize_expense(raw_text)
    provider = detect_provider(raw_text)
    status = "success" if amount and amount > 0 else "failed"

    return {
        "description": description,
        "amount": round(amount or 0.0, 2),
        "date": date,
        "category": category,
        "provider": provider,
        "status": status,
        "raw_text": raw_text
    }


def categorize_expense(text: str) -> str:
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return category
    return "other"


def build_csv_path():
    return os.path.join(DATA_DIR, "expenses.csv")


def export_to_csv(expenses):
    csv_path = build_csv_path()
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "provider", "description", "amount", "category", "status"])
        writer.writeheader()
        for item in expenses:
            writer.writerow({
                "date": item.get("date", ""),
                "provider": item.get("provider", ""),
                "description": item.get("description", ""),
                "amount": item.get("amount", ""),
                "category": item.get("category", ""),
                "status": item.get("status", "")
            })
    return csv_path


def summarize_expenses(expenses):
    total = len(expenses)
    total_amount = sum(item.get("amount", 0) for item in expenses)
    success_count = sum(1 for item in expenses if item.get("status") == "success")
    failed_count = total - success_count

    now = datetime.now()
    month_prefix = now.strftime("%Y-%m")
    month_expenses = [item for item in expenses if item.get("date", "").startswith(month_prefix)]
    month_amount = sum(item.get("amount", 0) for item in month_expenses)

    provider_counts = {}
    category_counts = {}
    for item in expenses:
        provider = item.get("provider", "Unknown")
        category = item.get("category", "other")
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1

    return {
        "total": total,
        "total_amount": total_amount,
        "month_total": len(month_expenses),
        "month_amount": month_amount,
        "success": success_count,
        "failed": failed_count,
        "providers": sorted(provider_counts.items(), key=lambda x: x[1], reverse=True),
        "categories": sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    }


def format_top_items(items, prefix=""):
    lines = []
    total = sum(count for _, count in items)
    for name, count in items[:3]:
        percent = round(count / total * 100) if total else 0
        lines.append(f"{prefix}{name}: {percent}% ({count})")
    return lines


def start(update: Update, context: CallbackContext):
    text = (
        "Welcome to the Expense Receipt Bot!\n\n"
        "Send me a receipt photo and I will extract the amount, date, category, and provider.\n"
        "Use /upload, /stats, /report, /search, /top, or /export."
    )
    update.message.reply_text(text)


def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Commands:\n"
        "/start - Start the bot\n"
        "/upload - Upload a receipt photo\n"
        "/stats - Show monthly and account analytics\n"
        "/report - View a summary report\n"
        "/search <query> - Search your receipts\n"
        "/top - Show top providers and categories\n"
        "/export - Export expenses as CSV"
    )


def upload_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Please send a receipt photo now.\n"
        "I will read it and save the expense for your analytics."
    )


def report_command(update: Update, context: CallbackContext):
    expenses = load_expenses()
    if not expenses:
        update.message.reply_text("No expenses found yet. Send a receipt photo first.")
        return

    summary = summarize_expenses(expenses)
    lines = [
        "💳 Account & Analytics",
        "━━━━━━━━━━━━━━━━",
        f"📈 Total receipts: {summary['total']}",
        f"💰 Total processed: {format_mmk(summary['total_amount'])}",
        "",
        f"📅 This month: {summary['month_total']} receipts, {format_mmk(summary['month_amount'])}",
        f"✅ Successful: {summary['success']}",
        f"❌ Failed: {summary['failed']}",
        "",
        "🏦 Top Providers:" 
    ]
    lines += [f"• {name}: {count} receipts" for name, count in summary['providers'][:3]]
    lines.append("")
    lines.append("📊 Top Categories:")
    lines += [f"• {name}: {count} receipts" for name, count in summary['categories'][:3]]

    update.message.reply_text("\n".join(lines))


def stats_command(update: Update, context: CallbackContext):
    expenses = load_expenses()
    if not expenses:
        update.message.reply_text("No expenses found yet. Send a receipt photo first.")
        return

    summary = summarize_expenses(expenses)
    top_providers = format_top_items(summary['providers'], prefix="• ")
    top_categories = format_top_items(summary['categories'], prefix="• ")

    lines = [
        "📈 Expense Analytics",
        f"This Month: {summary['month_total']} receipts | {format_mmk(summary['month_amount'])}",
        f"All-Time: {summary['total']} receipts | {format_mmk(summary['total_amount'])}",
        "",
        "Top Providers:",
        *(top_providers if top_providers else ["• None found"]),
        "",
        "Top Categories:",
        *(top_categories if top_categories else ["• None found"])
    ]
    update.message.reply_text("\n".join(lines))


def search_command(update: Update, context: CallbackContext):
    query = " ".join(context.args).strip().lower()
    if not query:
        update.message.reply_text("Usage: /search <query>\nSearch provider, category, merchant, or date.")
        return

    expenses = load_expenses()
    matches = []
    for item in expenses:
        haystack = " ".join([
            item.get("provider", ""),
            item.get("category", ""),
            item.get("description", ""),
            item.get("raw_text", ""),
            item.get("date", "")
        ]).lower()
        if query in haystack:
            matches.append(item)

    if not matches:
        update.message.reply_text(f"No receipts matched '{query}'.")
        return

    response = [f"Found {len(matches)} receipts matching '{query}':"]
    for item in matches[:5]:
        response.append(
            f"• {item.get('date')} | {item.get('provider')} | {item.get('category')} | {format_mmk(item.get('amount', 0))}"
        )
    if len(matches) > 5:
        response.append(f"...and {len(matches) - 5} more.")

    update.message.reply_text("\n".join(response))


def top_command(update: Update, context: CallbackContext):
    expenses = load_expenses()
    if not expenses:
        update.message.reply_text("No expenses found yet. Send a receipt photo first.")
        return

    summary = summarize_expenses(expenses)
    top_providers = [f"• {name}: {count} receipts" for name, count in summary['providers'][:5]] or ["• None"]
    top_categories = [f"• {name}: {count} receipts" for name, count in summary['categories'][:5]] or ["• None"]
    lines = [
        "🏆 Top Insights",
        "Top Providers:",
        *top_providers,
        "",
        "Top Categories:",
        *top_categories
    ]
    update.message.reply_text("\n".join(lines))


def export_command(update: Update, context: CallbackContext):
    expenses = load_expenses()
    if not expenses:
        update.message.reply_text("No expenses saved yet. Send a receipt photo first.")
        return
    path = export_to_csv(expenses)
    update.message.reply_document(document=InputFile(path), filename="expenses.csv")


def photo_handler(update: Update, context: CallbackContext):
    message = update.message
    if not message.photo:
        message.reply_text("Please send a photo of a receipt.")
        return

    photo = message.photo[-1]
    file = photo.get_file()
    ensure_data_dir()
    image_path = os.path.join(DATA_DIR, f"receipt_{photo.file_id}.jpg")
    file.download(image_path)

    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        message.reply_text("OCR dependencies are not installed. Please install pillow and pytesseract.")
        return

    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
    except Exception as exc:
        message.reply_text(f"Failed to process the image: {exc}")
        return

    expense = parse_expense_text(text)
    expenses = load_expenses()
    expenses.append(expense)
    save_expenses(expenses)

    message.reply_text(
        "Expense saved!\n"
        f"Date: {expense['date']}\n"
        f"Amount: {format_mmk(expense['amount'])}\n"
        f"Provider: {expense['provider']}\n"
        f"Category: {expense['category']}\n"
        f"Description: {expense['description']}"
    )


def unknown(update: Update, context: CallbackContext):
    update.message.reply_text("Sorry, I did not understand that command. Use /help for available commands.")


def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise SystemExit("Please set TELEGRAM_TOKEN in your environment.")

    updater = Updater(token)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("upload", upload_command))
    dispatcher.add_handler(CommandHandler("stats", stats_command))
    dispatcher.add_handler(CommandHandler("report", report_command))
    dispatcher.add_handler(CommandHandler("search", search_command))
    dispatcher.add_handler(CommandHandler("top", top_command))
    dispatcher.add_handler(CommandHandler("export", export_command))
    dispatcher.add_handler(MessageHandler(Filters.photo, photo_handler))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    print("Starting Telegram Expense Receipt Bot...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
