import requests
import feedparser
from datetime import datetime, date
from urllib.parse import quote
from email.utils import parsedate_to_datetime

QUERIES = [
    '"GCC incentives" India',
    '"Global Capability Centre" incentives India',
    '"Global Capability Centers" incentives India',
    '"GCC policy" incentives India',
    '"GCC" "incentives" "state government" India',
    '"Global Capability Centre" "subsidy" India',
    '"GCC" "subsidy" India',
]

TODAY = date.today()

def google_news_rss(query):
    encoded = quote(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"

def clean_title(title):
    return title.split(" - ")[0].strip()

def extract_source(entry):
    return entry.get("source", {}).get("title", "Unknown Source")

def parse_publish_date(entry):
    published = entry.get("published", "")
    if not published:
        return None
    try:
        return parsedate_to_datetime(published).date()
    except Exception:
        return None

def detect_state(text):
    states = [
        "Karnataka", "Telangana", "Tamil Nadu", "Maharashtra", "Gujarat",
        "Uttar Pradesh", "Andhra Pradesh", "Kerala", "Rajasthan",
        "Madhya Pradesh", "West Bengal", "Odisha", "Punjab", "Haryana",
        "Delhi", "Assam", "Bihar", "Goa", "Jharkhand", "Chhattisgarh",
        "Uttarakhand", "Himachal Pradesh"
    ]

    text_lower = text.lower()
    for state in states:
        if state.lower() in text_lower:
            return state

    return "All India"

def is_gcc_incentive_news(title, summary):
    text = f"{title} {summary}".lower()

    gcc_terms = [
        "gcc",
        "global capability centre",
        "global capability center",
        "global capability centres",
        "global capability centers"
    ]

    incentive_terms = [
        "incentive",
        "subsidy",
        "policy",
        "grant",
        "tax benefit",
        "reimbursement",
        "state support",
        "government support",
        "scheme"
    ]

    return any(term in text for term in gcc_terms) and any(term in text for term in incentive_terms)

def fetch_news():
    results = []
    seen = set()

    for query in QUERIES:
        url = google_news_rss(query)
        feed = feedparser.parse(url)

        for entry in feed.entries:
            title = clean_title(entry.get("title", ""))
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            source = extract_source(entry)
            published_date = parse_publish_date(entry)

            if published_date != TODAY:
                continue

            if not is_gcc_incentive_news(title, summary):
                continue

            duplicate_key = title.lower().strip()

            if duplicate_key in seen:
                continue

            seen.add(duplicate_key)

            state = detect_state(f"{title} {summary}")

            results.append({
                "state": state,
                "summary": title,
                "publish_date": published_date.strftime("%B %d, %Y"),
                "source": source,
                "link": link
            })

    return results

def print_results(news_items):
    if not news_items:
        print(f"GCC Incentives - All India")
        print("No qualifying GCC incentive news found for today.")
        print(f"Publish date: {TODAY.strftime('%B %d, %Y')}")
        print("Source link: No qualifying source found.")
        return

    for item in news_items:
        print(f"GCC Incentives - {item['state']}")
        print(item["summary"])
        print(f"Publish date: {item['publish_date']}")
        print(f"Source: {item['source']}")
        print(f"Source link: {item['link']}")
        print("-" * 80)

if __name__ == "__main__":
    news = fetch_news()
    print_results(news)
