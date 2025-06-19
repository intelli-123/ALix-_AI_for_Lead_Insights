import os, re, requests, phonenumbers
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient
from duckduckgo_search import DDGS

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX_ID = os.getenv("GOOGLE_CX_ID")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

mcp = FastMCP("linkedin-search-v1")

# --- Search Providers ---
def _search_google_cse(query: str, k: int = 3):
    if not GOOGLE_API_KEY or not GOOGLE_CX_ID:
        return
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        response = service.cse().list(q=f'site:linkedin.com/in "{query}"', cx=GOOGLE_CX_ID, num=k).execute()
        for item in response.get("items", []):
            yield {"link": item.get("link"), "title": item.get("title"), "snippet": item.get("snippet")}
    except Exception as e:
        print(f"[Google CSE ERROR]: {e}")

def _search_tavily(query: str, k: int = 3):
    if not TAVILY_API_KEY:
        return
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        results = client.search(query=f'site:linkedin.com/in "{query}"', max_results=k)
        for item in results.get("results", []):
            yield {"link": item.get("url"), "title": item.get("title"), "snippet": item.get("content")}
    except Exception as e:
        print(f"[Tavily ERROR]: {e}")

def _search_duckduckgo(query: str, k: int = 3):
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(f'site:linkedin.com/in "{query}"', max_results=k * 2):
                if "linkedin.com/in/" in r.get("href", ""):
                    yield {"link": r.get("href"), "title": r.get("title"), "snippet": r.get("body")}
    except Exception as e:
        print(f"[DuckDuckGo ERROR]: {e}")

# --- Helpers ---
def _extract_phones(text: str):
    for match in phonenumbers.PhoneNumberMatcher(text, None):
        yield phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)

def _process_profile_url(url: str, title: str, snippet: str, source: str):
    if not url or "linkedin.com/in/" not in url:
        return None
    try:
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        content = soup.find("main").get_text(" ", strip=True) if soup.find("main") else soup.get_text(" ", strip=True)

        name = url.split("/")[-1].replace("-", " ").title()
        raw_text = snippet + " " + title

        company_match = re.search(r"\b(?:at|@)\s+([A-Z][A-Za-z0-9&\-,\. ]+)", raw_text)
        company = company_match.group(1).strip() if company_match else "N/A"

        skill_keywords = ["API", "DevOps", "Cloud", "Microservices", "AI", "ML", "Security", "Automation", "Integration"]
        found_skills = [kw for kw in skill_keywords if kw.lower() in raw_text.lower()]
        skillset = ", ".join(found_skills) if found_skills else "N/A"

        experience_match = re.search(r"\b[0-9]{1,2}\s+\+?\s*(years|yrs)\s+of\s+experience\b", raw_text, re.I)
        experience = experience_match.group(0).strip() if experience_match else "N/A"

        edu_match = re.search(r"(University|College|Institute)[^.,\n]+", raw_text)
        education = edu_match.group(0).strip() if edu_match else "N/A"

        location_match = re.search(r"(San Francisco Bay Area|California|India|USA|United States|Atlanta|Texas|New York)", raw_text)
        location = location_match.group(0).strip() if location_match else "N/A"

        phones = list(_extract_phones(content))

        limited_skillset = skillset[:75]
        print(f"\n🔍 Name: {name}")
        print(f"🔗 LinkedIn Profile: {url}")
        print(f"🏢 Company: {company}")
        print(f"🛠 Skills: { limited_skillset}")
        print(f"💼 Experience: {experience}")
        print(f"🎓 Education: {education}")
        print(f"📍 Location: {location}")
        print(f"📞 Phones: {phones}")

        return {
            "name": name,
            "url": url,
            "designation": title,
            "company": company,
            "skillset":  limited_skillset,
            "experience": experience,
            "education": education,
            "location": location,
            "phones": phones,
            "source": source,
            "snippet": snippet
        }

    except Exception as e:
        print(f"[Profile Parse ERROR]: {e}")
        return None

# --- Public Info ---
def _public_info_snippets(query: str, max_results=5):
    info = []
    try:
        if GOOGLE_API_KEY and GOOGLE_CX_ID:
            service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
            res = service.cse().list(q=query, cx=GOOGLE_CX_ID, num=max_results).execute()
            for item in res.get("items", []):
                info.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet")
                })
    except Exception as e:
        print(f"[Public Info ERROR]: {e}")
    return info

# --- Main MCP Tool ---
@mcp.tool()
def linkedin_contact_lookup(person_query: str) -> dict:
    processed_urls = set()
    max_hits = 3

    providers = [
        {"name": "Google CSE", "function": _search_google_cse},
        {"name": "Tavily", "function": _search_tavily},
        {"name": "DuckDuckGo", "function": _search_duckduckgo}
    ]

    def run_query_variants(query):
        variants = [query]
        parts = query.split()
        if len(parts) == 2:
            variants.append(" ".join(reversed(parts)))
        variants.append(query.replace(" ", " AND "))
        return variants

    def search_profiles(query_variants):
        hits = []
        for variant in query_variants:
            for provider in providers:
                if len(hits) >= max_hits:
                    break
                for item in provider["function"](variant, k=3):
                    url = item.get("link")
                    if url and url not in processed_urls:
                        processed_urls.add(url)
                        profile = _process_profile_url(url, item.get("title", ""), item.get("snippet", ""), provider["name"])
                        if profile:
                            hits.append(profile)
                            if len(hits) >= max_hits:
                                break
        return hits

    profile_hits = search_profiles(run_query_variants(person_query))
    public_info = _public_info_snippets(person_query)

    return {
        "query": person_query,
        "hits": profile_hits,
        "public_info": public_info
    }

# --- CLI Debug ---
if __name__ == "__main__":
    name = input("Enter name or name + company: ").strip()
    result = linkedin_contact_lookup(name)
    import json
    print(json.dumps(result, indent=2))
