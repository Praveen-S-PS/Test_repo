import re
import hashlib
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from dateutil import parser
from urllib.parse import quote_plus, urlparse

HOURS_BACK = 24

SEARCH_QUERIES = [
    '"Global Capability Center" India',
    '"Global Capability Centre" India',
    'GCC India expansion',
    'GCC India investment',
    'GCC India policy',
    'GCC India incentives',
    'India GCC tax benefits',
    'India GCC payroll subsidy',
    'India GCC land incentives',
    'India GCC capex opex support',
    'AI led GCC India',
    'Tier 2 GCC India',
    'Tier 3 GCC India',
    'Bengaluru GCC expansion',
    'Hyderabad GCC expansion',
    'Chennai GCC expansion',
    'Pune GCC expansion',
    'Coimbatore GCC',
    'Ahmedabad GCC',
    'Noida GCC',
]

APPROVED_SOURCES = [
    "gcc.economictimes.indiatimes.com",
    "economictimes.indiatimes.com",
    "timesofindia.indiatimes.com",
    "moneycontrol.com",
    "meity.gov.in",
    "invest.up.gov.in",
    "guidancetn.in",
    "investkarnataka.co.in",
    "invest.telangana.gov.in",
    "investgujarat.in",
    "midcindia.org",
    "nasscom.in",
    "kpmg.com",
    "rsm.global",
    "india-briefing.com",
    "ibef.org",
]

BLOCKED_KEYWORDS = [
    "gcc countries",
    "gulf cooperation council",
    "middle east",
    "saudi",
    "uae",
    "qatar",
    "kuwait",
    "bahrain",
    "oman",
]

RELEVANT_KEYWORDS = [
    "global capability center",
    "global capability centre",
    "gcc",
    "capability centre",
    "capability center",
    "captive center",
    "captive centre",
    "technology hub",
    "shared services",
    "innovation hub",
]

BUSINESS_KEYWORDS = [
    "policy",
    "incentive",
    "subsidy",
    "tax benefit",
    "investment",
    "expansion",
    "launch",
    "opens",
    "sets up",
    "hiring",
    "jobs",
    "ai",
    "artificial intelligence",
    "tier-2",
    "tier 2",
    "tier-3",
    "tier 3",
    "capex",
    "opex",
    "land",
    "payroll",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def google_news_rss_url(query):
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"


def clean_google_news_url(url):
    return url


def domain(url):
    return re.sub(r"^www\.", "", urlparse(url).netloc.lower())


def is_approved_source(url):
    d = domain(url)
    return any(src in d for src in APPROVED_SOURCES)


def normalize_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def is_relevant(text):
    text = text.lower()

    if any(bad in text for bad in BLOCKED_KEYWORDS):
        return False

    has_gcc_context = any(word in text for word in RELEVANT_KEYWORDS)
    has_business_context = any(word in text for word in BUSINESS_KEYWORDS)

    india_context = any(
        place in text
        for place in [
            "india", "bengaluru", "bangalore", "hyderabad", "chennai",
            "pune", "mumbai", "noida", "gurugram", "gurgaon",
            "coimbatore", "ahmedabad", "karnataka", "telangana",
            "tamil nadu", "maharashtra", "gujarat", "uttar pradesh"
        ]
    )

    return has_gcc_context and has_business_context and india_context


def article_hash(title, url):
    raw = f"{title.lower().strip()}|{url}"
    return hashlib.sha256(raw.encode()).hexdigest()


def scrape_article(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "aside"]):
        tag.decompose()

    paragraphs = soup.find_all("p")
    text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)

    return normalize_text(text)


def summarize(text):
    text = normalize_text(text)
    sentences = re.split(r"(?<=[.!?])\s+", text)

    useful = [
        s for s in sentences
        if len(s.split()) > 8
    ]

    return " ".join(useful[:2]) if useful else text[:350]


def generate_tags(text):
    text = text.lower()
    tags = []

    if "policy" in text or "government" in text:
        tags.append("Policy")
    if "incentive" in text or "subsidy" in text or "tax" in text or "payroll" in text:
        tags.append("Incentives")
    if "investment" in text or "invest" in text:
        tags.append("Investment")
    if "expansion" in text or "expand" in text or "opens" in text or "sets up" in text:
        tags.append("Expansion")
    if "ai" in text or "artificial intelligence" in text:
        tags.append("AI")
    if "tier-2" in text or "tier 2" in text or "tier-3" in text or "tier 3" in text:
        tags.append("Tier-2/Tier-3")
    if "bengaluru" in text or "bangalore" in text:
        tags.append("Bengaluru")
    if "hyderabad" in text:
        tags.append("Hyderabad")
    if "chennai" in text:
        tags.append("Chennai")
    if "pune" in text:
        tags.append("Pune")

    return tags[:5] or ["GCC"]


def impact_score(text):
    text = text.lower()
    score = 0

    priority_terms = {
        "policy": 5,
        "incentive": 5,
        "subsidy": 5,
        "tax benefit": 5,
        "investment": 4,
        "expansion": 4,
        "sets up": 4,
        "opens": 4,
        "jobs": 3,
        "hiring": 3,
        "ai": 3,
        "tier-2": 3,
        "tier 2": 3,
        "tier-3": 3,
        "tier 3": 3,
    }

    for term, value in priority_terms.items():
        if term in text:
            score += value

    return score


def collect_gcc_news(hours_back=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    articles = []
    seen = set()

    for query in SEARCH_QUERIES:
        feed_url = google_news_rss_url(query)
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            title = normalize_text(entry.get("title", ""))
            link = clean_google_news_url(entry.get("link", ""))
            published_raw = entry.get("published") or entry.get("updated")

            if not title or not link or not published_raw:
                continue

            try:
                published = parser.parse(published_raw)
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
            except Exception:
                continue

            if published < cutoff:
                continue

            article_id = article_hash(title, link)
            if article_id in seen:
                continue

            seen.add(article_id)

            rss_summary = normalize_text(entry.get("summary", ""))
            combined_rss_text = f"{title} {rss_summary}"

            article_text = scrape_article(link)
            combined_text = f"{title} {rss_summary} {article_text}"

            if not is_relevant(combined_text):
                continue

            if not is_approved_source(link):
                source_name = domain(link)
            else:
                source_name = domain(link)

            summary_source = article_text if len(article_text) > 200 else rss_summary

            articles.append({
                "headline": title,
                "published": published,
                "published_date": published.strftime("%d-%b-%Y"),
                "summary": summarize(summary_source),
                "source_link": link,
                "source": source_name,
                "tags": generate_tags(combined_text),
                "impact_score": impact_score(combined_text),
            })

    articles.sort(key=lambda x: x["impact_score"], reverse=True)
    return articles


def format_digest(articles):
    if not articles:
        return "No new GCC policy, incentive, investment, or expansion announcements were identified for the selected period."

    output = "Here are today's top GCC headlines and summaries.\n\n"
    output += "------------------------------------------------\n\n"

    for article in articles:
        output += f"Headline:\n{article['headline']}\n\n"
        output += f"Published Date:\n{article['published_date']}\n\n"
        output += f"Summary:\n{article['summary']}\n\n"
        output += f"Source Link:\n{article['source_link']}\n\n"
        output += f"Tags:\n{', '.join(article['tags'])}\n\n"
        output += "------------------------------------------------\n\n"

    return output


if __name__ == "__main__":
    articles = collect_gcc_news(hours_back=HOURS_BACK)
    digest = format_digest(articles)
    print(digest)
