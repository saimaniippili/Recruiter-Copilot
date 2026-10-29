import os
import json
import telebot
from telebot import types
from pathlib import Path
from typing import List, Dict, Any

from .core.config import settings
from .core.schemas import CandidateSchema
from .jobs.orchestrator import orchestrator
from .storage.db import repo

if not settings.TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing. Please check your .env file.")

bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN)

PAGE_SIZE = 3


def safe_send_text(chat_id: int, text: str, reply_markup=None, **kwargs):
    """Safely delivers plain text message avoiding entity parsing failures."""
    try:
        return bot.send_message(chat_id, text, reply_markup=reply_markup, **kwargs)
    except Exception as e:
        print(f"[Warning] Failed to send message to {chat_id}: {e}")
        return None


def safe_reply_text(message, text: str, reply_markup=None, **kwargs):
    """Safely replies with plain text message."""
    try:
        return bot.reply_to(message, text, reply_markup=reply_markup, **kwargs)
    except Exception:
        return bot.send_message(message.chat.id, text, reply_markup=reply_markup, **kwargs)


def format_candidate_page(job_id: str, candidates: list, page: int) -> str:
    """Formats a page of candidates in clean enterprise typography without emojis."""
    total = len(candidates)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    start_idx = page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total)
    current_batch = candidates[start_idx:end_idx]

    lines = [
        "========================================",
        "RECRUITER COPILOT | CANDIDATE SOURCING",
        "========================================",
        f"Job ID: {job_id} | Total Candidates: {total}",
        f"Displaying Page {page + 1} of {total_pages}",
        "----------------------------------------"
    ]

    for i, c in enumerate(current_batch, start=start_idx + 1):
        if isinstance(c, dict):
            name = c.get('name') or 'Candidate'
            headline = c.get('headline') or 'N/A'
            score = c.get('score', 0.0)
            eligibility = c.get('eligibility', 'requires_human_review')
            url = c.get('profile_url', '')
            notes = ""
            if c.get('evidence_json'):
                try:
                    ev_data = json.loads(c['evidence_json'])
                    notes = ev_data.get('fit_summary', '')
                except Exception:
                    notes = ""
        else:
            name = c.name or 'Candidate'
            headline = c.headline or 'N/A'
            score = c.preliminary_match_score
            eligibility = c.eligibility.value
            url = c.profile_url
            notes = c.fit_summary or ""

        status_tag = str(eligibility).replace('_', ' ').upper()

        lines.append(f"[{i}/{total}] {name}")
        lines.append(f"TITLE: {headline}")
        lines.append(f"MATCH: {score}% | STATUS: [{status_tag}]")
        if notes:
            lines.append(f"EVALUATION: {notes}")
        lines.append(f"LINK: {url}")
        lines.append("----------------------------------------")

    return "\n".join(lines)


def build_pagination_keyboard(job_id: str, page: int, total_candidates: int) -> types.InlineKeyboardMarkup:
    """Creates inline navigation keyboard for paging candidates and action buttons."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    total_pages = max(1, (total_candidates + PAGE_SIZE - 1) // PAGE_SIZE)
    nav_buttons = []

    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("< Previous", callback_data=f"page:{job_id}:{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("Next >", callback_data=f"page:{job_id}:{page + 1}"))

    if nav_buttons:
        markup.row(*nav_buttons)

    action_buttons = [
        types.InlineKeyboardButton("Download CSV", callback_data=f"csv:{job_id}"),
        types.InlineKeyboardButton("New Search", callback_data="cmd:search")
    ]
    markup.row(*action_buttons)
    return markup


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "========================================\n"
        "RECRUITER COPILOT | SOURCING PLATFORM\n"
        "========================================\n"
        "Deterministic candidate sourcing and qualification platform.\n"
        "Hybrid search provider orchestration with evidence evaluation rubric.\n\n"
        "SYNTAX INSTRUCTIONS:\n"
        "- Prefix non-negotiable criteria with '*' (e.g. *C++, *Figma, *8-10 years)\n"
        "- Clearly state target location and experience requirements.\n\n"
        "AVAILABLE COMMANDS:\n"
        "/search         - Submit a Job Description for candidate sourcing\n"
        "/status <id>    - Check progress of a background sourcing job\n"
        "/help           - View platform guide and commands"
    )
    safe_reply_text(message, welcome_text)


@bot.message_handler(commands=['status'])
def check_status(message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        safe_reply_text(message, "Usage: /status <job_id>")
        return
    job_id = parts[1]
    job_record = repo.get_job(job_id)
    if not job_record:
        safe_reply_text(message, f"[ERROR] Job '{job_id}' not found in database.")
        return
    
    status_msg = (
        "========================================\n"
        "JOB STATUS REPORT\n"
        "========================================\n"
        f"Job ID: {job_id}\n"
        f"Role: {job_record.get('role_title') or 'Parsing in progress'}\n"
        f"State: {job_record.get('state', '').upper()}\n"
        f"Last Updated: {job_record.get('updated_at')}\n"
    )
    if job_record.get("error_message"):
        status_msg += f"Error Detail: {job_record.get('error_message')}\n"
    status_msg += "----------------------------------------"
    safe_reply_text(message, status_msg)


@bot.message_handler(commands=['search'])
def start_search(message):
    msg = safe_reply_text(
        message,
        "SUBMIT JOB DESCRIPTION\n"
        "----------------------------------------\n"
        "Paste your Job Description below.\n\n"
        "Tip: Mark non-negotiable requirements with '*' (e.g. *C++, *Dutch, *8-10 years)."
    )
    bot.register_next_step_handler(msg, process_jd_step)


def process_jd_step(message):
    chat_id = message.chat.id
    jd_text = message.text

    if not jd_text or len(jd_text.strip()) < 15:
        safe_send_text(chat_id, "[ERROR] Please provide a valid Job Description text.")
        return

    # 1. Send immediate acknowledgement
    status_msg = bot.send_message(
        chat_id,
        "[JOB QUEUED]\nInitial parsing in progress..."
    )
    status_msg_id = status_msg.message_id

    def update_progress(text: str):
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=status_msg_id)
        except Exception:
            pass

    def on_complete(job_id: str, candidates: List[CandidateSchema]):
        if not candidates:
            safe_send_text(
                chat_id,
                f"[SEARCH COMPLETE: {job_id}]\n"
                f"No candidates met the verified criteria.\n\n"
                "Suggestions:\n"
                "- Broaden location constraints or verify spelling.\n"
                "- Reduce the count of starred mandatory keywords.\n"
                "- Submit /search again with alternative keywords."
            )
            return

        # Render first page with pagination controls
        page_text = format_candidate_page(job_id, candidates, page=0)
        markup = build_pagination_keyboard(job_id, page=0, total_candidates=len(candidates))
        safe_send_text(chat_id, page_text, reply_markup=markup, disable_web_page_preview=True)

        # Attach CSV
        csv_file = settings.EXPORTS_DIR / f"recruiter_copilot_{job_id}.csv"
        if csv_file.exists():
            with open(csv_file, "rb") as f:
                try:
                    bot.send_document(
                        chat_id,
                        f,
                        caption=f"[EXPORT] Candidate evaluation report for Job ID {job_id}."
                    )
                except Exception as doc_err:
                    print(f"[Warning] Failed to send document: {doc_err}")

    def on_error(job_id: str, error: Exception):
        err_msg = str(error)[:150]
        safe_send_text(
            chat_id,
            f"[JOB FAILED: {job_id}]\nError: {err_msg}"
        )

    # Launch asynchronously
    job_id = orchestrator.submit_job_async(
        chat_id=chat_id,
        raw_jd_text=jd_text,
        on_progress=update_progress,
        on_complete=on_complete,
        on_error=on_error
    )


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    data = call.data or ""
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if data.startswith("page:"):
        parts = data.split(":")
        if len(parts) >= 3:
            job_id = parts[1]
            page = int(parts[2])
            candidates = repo.get_candidates(job_id)
            if not candidates:
                bot.answer_callback_query(call.id, "Candidate records not found.")
                return

            text = format_candidate_page(job_id, candidates, page)
            markup = build_pagination_keyboard(job_id, page, len(candidates))
            try:
                bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup, disable_web_page_preview=True)
                bot.answer_callback_query(call.id)
            except Exception:
                bot.answer_callback_query(call.id)

    elif data.startswith("csv:"):
        parts = data.split(":")
        if len(parts) >= 2:
            job_id = parts[1]
            csv_file = settings.EXPORTS_DIR / f"recruiter_copilot_{job_id}.csv"
            if csv_file.exists():
                bot.answer_callback_query(call.id, "Dispatching CSV report...")
                with open(csv_file, "rb") as f:
                    bot.send_document(
                        chat_id,
                        f,
                        caption=f"[EXPORT] Sourcing report for Job ID {job_id}."
                    )
            else:
                bot.answer_callback_query(call.id, "CSV report not found.")

    elif data == "cmd:search":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(
            chat_id,
            "SUBMIT JOB DESCRIPTION\n"
            "----------------------------------------\n"
            "Paste your Job Description below.\n\n"
            "Syntax: Mark non-negotiable requirements with '*' (e.g. *C++, *Dutch, *8-10 years)."
        )
        bot.register_next_step_handler(msg, process_jd_step)


def run_bot():
    print("Recruiter Copilot Production Platform is running...")
    bot.infinity_polling(timeout=20, long_polling_timeout=20)


if __name__ == '__main__':
    run_bot()
