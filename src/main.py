import os
import urllib.parse
import pandas as pd
import telebot

from .config import TELEGRAM_TOKEN
from .llm import ai_parse_jd
from .search import find_candidates

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is missing. Please check your .env file.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 *Welcome to Recruiter Copilot!*\n\n"
        "I use Local AI to instantly parse messy Job Descriptions and find matching candidates on LinkedIn.\n\n"
        "Send /search to begin!"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['search'])
def start_search(message):
    msg = bot.reply_to(message, "📝 **Paste the entire Job Description below:**\n_(It can be messy, I will use AI to extract the key details!)_", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_jd_step)

def process_jd_step(message):
    chat_id = message.chat.id
    jd_text = message.text
    
    # 1. Parse JD with Local AI
    bot.send_message(chat_id, "🧠 *AI is analyzing the Job Description...*", parse_mode="Markdown")
    role, location, keywords = ai_parse_jd(jd_text)
    
    if role == "ERROR":
        bot.send_message(chat_id, f"❌ *AI Offline Error*\nI couldn't analyze the JD because the local AI (Ollama) is not running on your computer. Your computer restarted recently, which closed it.\n\n_Please open the Ollama app on your computer and try again!_\n\nError: `{keywords}`", parse_mode="Markdown")
        return
        
    safe_title = role.replace("/", " ").replace("\\", " ").replace("(", " ").replace(")", " ")
    safe_location = location.replace("/", " ").replace("\\", " ").replace("(", " ").replace(")", " ")
    strict_keywords = " ".join([f'"{k.strip()}"' for k in keywords.replace(",", " ").split() if k.strip()])
    query_str = f'site:linkedin.com/in/ intitle:"{safe_title}" {safe_location} {strict_keywords}'
    google_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query_str)}"
    
    response_msg = (
        f"✅ *JD Parsed successfully!*\n\n"
        f"*Role:* {role}\n"
        f"*Location:* {location}\n"
        f"*Keywords:* {keywords}\n\n"
        f"🔗 **[Click here to view Candidates on Google]({google_url})**\n\n"
        f"_(I am also trying to automatically download them into a spreadsheet for you... but if the search engine blocks me, just click the link above!)_"
    )
    bot.send_message(chat_id, response_msg, parse_mode="Markdown", disable_web_page_preview=True)
    
    # 2. Search for candidates
    candidates, used_query = find_candidates(role, location, keywords, max_results=15)
    
    bot.send_message(chat_id, f"⚙️ *Searching LinkedIn...*\n_Query: {used_query}_\n\n_Please wait a few seconds..._", parse_mode="Markdown")
    
    if not candidates:
        bot.send_message(chat_id, "❌ No candidates found for those parameters on Google. Try a simpler Job Title or fewer keywords.")
        return
        
    # 3. Send Results
    bot.send_message(chat_id, f"✅ Found {len(candidates)} candidates! Here are the top 3:")
    
    for c in candidates[:3]:
        clean_snippet = c['Snippet'].replace('\n', ' ')
        text = f"👤 *{c['Name']}*\n💼 {c['Headline']}\n📌 _\"{clean_snippet}\"_\n🔗 [LinkedIn Profile]({c['Profile']})"
        bot.send_message(chat_id, text, parse_mode="Markdown", disable_web_page_preview=True)
        
    # 4. Save to CSV and send file
    filename = f"candidates_{chat_id}.csv"
    df = pd.DataFrame(candidates)
    df.to_csv(filename, index=False)
    
    with open(filename, "rb") as file:
        bot.send_document(chat_id, file, caption="📁 Here is the full spreadsheet of all candidates found! Send /search to do another one.")
        
    os.remove(filename)

def run_bot():
    print("Recruiter bot is polling with AI JD parsing...")
    bot.infinity_polling()
