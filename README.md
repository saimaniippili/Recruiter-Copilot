# Recruiter Copilot Bot

An AI-powered Telegram bot that helps technical recruiters instantly parse messy Job Descriptions and find matching candidates on LinkedIn using local LLMs.

## Approach & Workflow

1. **Input**: A recruiter pastes a messy Job Description (JD) into the Telegram bot chat.
2. **Extraction (LLM)**: The bot sends the JD to a local Ollama instance (`llama3.1:8b`). A strict prompt ensures it reliably extracts the core **Role**, **Location**, and **Keywords** without hallucinations.
3. **Sourcing (Search)**: Using the extracted fields, the bot crafts a targeted Google X-Ray query (`site:linkedin.com/in/`) and hits the SerpApi Google Search API to find live LinkedIn profiles bypassing LinkedIn's direct search limits.
4. **Output**: The bot instantly replies with the top 3 candidates and their profile links. It also compiles all candidates into a CSV spreadsheet for easy download.

## Technologies Used

* **Python 3**: Core language.
* **pyTelegramBotAPI**: For handling Telegram bot interactions and polling.
* **Ollama (Llama 3.1 8B)**: Local AI used for fast, privacy-preserving, and structured extraction of job requirements without relying on paid cloud APIs.
* **SerpApi**: Used for scraping Google Search results for X-Ray sourcing.
* **Pandas**: For organizing the extracted candidate data and exporting it to CSV.
* **dotenv**: For managing environment variables and secrets cleanly.

## Folder Structure

```
/
├── src/                        # Main source code
│   ├── __init__.py
│   ├── main.py                 # Main Telegram Bot logic and entry point
│   ├── llm.py                  # Local AI (Ollama) interaction logic
│   ├── search.py               # SerpApi Google X-Ray search logic
│   └── config.py               # Environment configuration loader
├── tests/                      # Unit and integration tests
│   ├── test_links.py
│   └── test_queries.py
├── legacy_birthday_bot_files/  # Leftover files from the previous "Birthday mail bot"
│   ├── bot_database.db
│   ├── credentials.json
│   └── token.json
├── .env                        # Environment variables (Tokens, API keys)
├── requirements.txt            # Python dependencies
├── run.py                      # Application runner script
└── README.md                   # This documentation
```

## Running the Bot

1. Ensure [Ollama](https://ollama.com) is installed and running with the `llama3.1:8b` model pulled.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the bot: `python run.py`
