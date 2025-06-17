
import os
import requests
import phonenumbers
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError as GoogleHttpError
from dotenv import load_dotenv
import json
from mcp.server.fastmcp import FastMCP

# Fallback imports
from tavily import TavilyClient
from duckduckgo_search import DDGS

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX_ID = os.getenv("GOOGLE_CX")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

mcp = FastMCP("linkedin-search-v2")

def _search_google_cse(query: str, k: int = 3):
    if not GOOGLE_API_KEY or not GOOGLE_CX_ID:
        print("[WARN] Missing Google CSE credentials.")
        return
    try:
        svc = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        res = svc.cse().list(q=f'site:linkedin.com/in "{query}"', cx=GOOGLE_CX_ID, num=k).execute()
        print("[DEBUG] Google CSE:", json.dumps(res, indent=2))
        for item in res.get("items", []):
            yield {"link": item.get("link"), "title": item.get("title"), "snippet": item.get("snippet")}
    except GoogleHttpError as e:
        print(f"[ERROR] Google CSE error: {e}")
    except Exception as e:
        print(f"[ERROR] Google CSE failed: {e}")

def _search_tavily(query: str, k: int = 3):
    if not TAVILY_API_KEY:
        print("[WARN] Missing TAVILY_API_KEY.")
        return
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(query=f'site:linkedin.com/in "{query}"', max_results=k)
        for item in response.get("results", []):
            yield {"link": item.get("url"), "title": item.get("title"), "snippet": item.get("content")}
    except Exception as e:
        print(f"[ERROR] Tavily failed: {e}")

def _search_duckduckgo(query: str, k: int = 3):
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(f'site:linkedin.com/in "{query}"', max_results=k * 2):
                if "linkedin.com/in/" in r.get("href", ""):
                    yield {"link": r.get("href"), "title": r.get("title"), "snippet": r.get("body")}
    except Exception as e:
        print(f"[ERROR] DuckDuckGo failed: {e}")

def _extract_phones(text: str):
    for match in phonenumbers.PhoneNumberMatcher(text, None):
        yield phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)

def _process_profile_url(url: str, title: str, snippet: str, source_name: str) -> dict | None:
    if not url or "linkedin.com/in/" not in url:
        print(f"[WARN] Skipping invalid LinkedIn URL: {url}")
        return None
    try:
        print(f"[INFO] {source_name}: Fetching {url}")
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        main = soup.find("main") or soup.find("body")
        content = main.get_text(" ", strip=True) if main else soup.get_text(" ", strip=True)
        phones = list(_extract_phones(content))
        return {
            "url": url,
            "phones": phones,
            "designation": title,
            "company": snippet,
            "location": snippet,
            "source": source_name
        }
    except Exception as e:
        print(f"[WARN] Failed to process {url}: {e}")
        return None

def _run_google_public_info_search(query: str, max_results=5) -> list:
    """Run a separate general Google search and return extra info (titles + snippets)."""
    results = []
    try:
        if not GOOGLE_API_KEY or not GOOGLE_CX_ID:
            print("[WARN] Google CSE creds missing. Skipping public info search.")
            return results
        svc = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        res = svc.cse().list(q=query, cx=GOOGLE_CX_ID, num=max_results).execute()
        for item in res.get("items", []):
            results.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet")
            })
    except Exception as e:
        print(f"[ERROR] Google public info search failed: {e}")
    return results

@mcp.tool()
def linkedin_contact_lookup(person_query: str) -> dict:
    """
    Looks up a person's LinkedIn profile using multiple search providers and fallbacks.
    It first tries the exact query, then a reversed name, and finally a broader search.
    """
    final_hits = []
    processed_urls = set()
    max_successful_hits_to_return = 3

    providers = [
        {"name": "Google CSE", "function": _search_google_cse},
        {"name": "Tavily", "function": _search_tavily},
        {"name": "DuckDuckGo", "function": _search_duckduckgo}
    ]

    def search_all_providers(query: str):
        hits = []
        for provider in providers:
            if len(final_hits) >= max_successful_hits_to_return:
                break
            try:
                results = provider["function"](query, k=3)
                for item in results:
                    url = item.get("link")
                    if url and url not in processed_urls:
                        processed_urls.add(url)
                        processed = _process_profile_url(url, item.get("title", ""), item.get("snippet", ""), provider["name"])
                        if processed:
                            hits.append(processed)
                            if len(hits) >= max_successful_hits_to_return:
                                return hits
            except Exception as e:
                print(f"[ERROR] {provider['name']} with query '{query}' failed: {e}")
        return hits

    # --- STEP 1: Search with the exact query ---
    print(f"[INFO] Step 1: Searching for exact query: '{person_query}'")
    final_hits = search_all_providers(person_query)

    # --- STEP 2: If no results, try reversing the name if it's a two-part name ---
    if not final_hits:
        query_parts = person_query.split()
        if len(query_parts) == 2:
            reversed_query = " ".join(reversed(query_parts))
            print(f"[INFO] Step 2: No results found. Retrying with reversed name: '{reversed_query}'")
            final_hits = search_all_providers(reversed_query)

    # --- STEP 3: If still no results, fallback to a broader "AND" search ---
    if not final_hits:
        fallback_query = person_query.replace(" ", " AND ")
        print(f"[INFO] Step 3: Still no results. Retrying with broader fallback: '{fallback_query}'")
        final_hits = search_all_providers(fallback_query)

    # --- STEP 4: Always perform a general public info search with the original query ---
    public_info = _run_google_public_info_search(person_query, max_results=5)

    # --- STEP 5: Enrich LinkedIn hits with public info ---
    snippet_text = " ".join([item["snippet"] for item in public_info if item.get("snippet")])

    for hit in final_hits:
        if not hit.get("company") or hit["company"] == hit["location"]:
            if "Google" in snippet_text:
                hit["company"] = "Google"

        if not hit.get("location") or hit["location"] == hit["company"]:
            if "California" in snippet_text:
                hit["location"] = "California"

        if not hit.get("designation") or hit["designation"].lower() in ["-", "n/a", ""]:
            if "CEO" in snippet_text:
                hit["designation"] = "CEO"

        hit["enriched"] = True

        score = 0
        if hit.get("company") and hit["company"] in snippet_text:
            score += 0.5
        if hit.get("designation") and hit["designation"] in snippet_text:
            score += 0.3
        if hit.get("location") and hit["location"] in snippet_text:
            score += 0.2
        hit["confidence"] = round(score, 2)

    return {
        "query": person_query,
        "hits": final_hits[:max_successful_hits_to_return],
        "public_info": public_info
    }

if __name__ == "__main__":
    import sys
    if "--mcp" in sys.argv:
        mcp.run()
    else:
        name = input("Enter name: ")
        result = linkedin_contact_lookup(name)
        print(json.dumps(result, indent=2))




# import os
# import requests
# import phonenumbers
# from bs4 import BeautifulSoup
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError as GoogleHttpError
# from dotenv import load_dotenv
# import json
# from mcp.server.fastmcp import FastMCP

# # Fallback imports
# from tavily import TavilyClient
# from duckduckgo_search import DDGS

# load_dotenv()
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# GOOGLE_CX_ID = os.getenv("GOOGLE_CX")
# TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# mcp = FastMCP("linkedin-search-v2")

# def _search_google_cse(query: str, k: int = 3):
#     if not GOOGLE_API_KEY or not GOOGLE_CX_ID:
#         print("[WARN] Missing Google CSE credentials.")
#         return
#     try:
#         svc = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
#         res = svc.cse().list(q=f'site:linkedin.com/in "{query}"', cx=GOOGLE_CX_ID, num=k).execute()
#         print("[DEBUG] Google CSE:", json.dumps(res, indent=2))
#         for item in res.get("items", []):
#             yield {"link": item.get("link"), "title": item.get("title"), "snippet": item.get("snippet")}
#     except GoogleHttpError as e:
#         print(f"[ERROR] Google CSE error: {e}")
#     except Exception as e:
#         print(f"[ERROR] Google CSE failed: {e}")

# def _search_tavily(query: str, k: int = 3):
#     if not TAVILY_API_KEY:
#         print("[WARN] Missing TAVILY_API_KEY.")
#         return
#     try:
#         client = TavilyClient(api_key=TAVILY_API_KEY)
#         response = client.search(query=f'site:linkedin.com/in "{query}"', max_results=k)
#         for item in response.get("results", []):
#             yield {"link": item.get("url"), "title": item.get("title"), "snippet": item.get("content")}
#     except Exception as e:
#         print(f"[ERROR] Tavily failed: {e}")

# def _search_duckduckgo(query: str, k: int = 3):
#     try:
#         with DDGS() as ddgs:
#             for r in ddgs.text(f'site:linkedin.com/in "{query}"', max_results=k * 2):
#                 if "linkedin.com/in/" in r.get("href", ""):
#                     yield {"link": r.get("href"), "title": r.get("title"), "snippet": r.get("body")}
#     except Exception as e:
#         print(f"[ERROR] DuckDuckGo failed: {e}")

# def _extract_phones(text: str):
#     for match in phonenumbers.PhoneNumberMatcher(text, None):
#         yield phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)

# def _process_profile_url(url: str, title: str, snippet: str, source_name: str) -> dict | None:
#     if not url or "linkedin.com/in/" not in url:
#         print(f"[WARN] Skipping invalid LinkedIn URL: {url}")
#         return None
#     try:
#         print(f"[INFO] {source_name}: Fetching {url}")
#         html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text
#         soup = BeautifulSoup(html, "html.parser")
#         main = soup.find("main") or soup.find("body")
#         content = main.get_text(" ", strip=True) if main else soup.get_text(" ", strip=True)
#         phones = list(_extract_phones(content))
#         return {
#             "url": url,
#             "phones": phones,
#             "designation": title,
#             "company": snippet,
#             "location": snippet,
#             "source": source_name
#         }
#     except Exception as e:
#         print(f"[WARN] Failed to process {url}: {e}")
#         return None

# def _run_google_public_info_search(query: str, max_results=5) -> list:
#     """Run a separate general Google search and return extra info (titles + snippets)."""
#     results = []
#     try:
#         if not GOOGLE_API_KEY or not GOOGLE_CX_ID:
#             print("[WARN] Google CSE creds missing. Skipping public info search.")
#             return results
#         svc = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
#         res = svc.cse().list(q=query, cx=GOOGLE_CX_ID, num=max_results).execute()
#         for item in res.get("items", []):
#             results.append({
#                 "title": item.get("title"),
#                 "link": item.get("link"),
#                 "snippet": item.get("snippet")
#             })
#     except Exception as e:
#         print(f"[ERROR] Google public info search failed: {e}")
#     return results

# @mcp.tool()
# def linkedin_contact_lookup(person_query: str) -> dict:
#     """
#     Looks up a person's LinkedIn profile using multiple search providers and fallbacks.
#     It first tries the exact query, then a reversed name, and finally a broader search.
#     """
#     final_hits = []
#     processed_urls = set()
#     max_successful_hits_to_return = 3

#     providers = [
#         {"name": "Google CSE", "function": _search_google_cse},
#         {"name": "Tavily", "function": _search_tavily},
#         {"name": "DuckDuckGo", "function": _search_duckduckgo}
#     ]

#     def search_all_providers(query: str):
#         hits = []
#         # Reset processed_urls for the new query type to allow finding same URL with different query
#         # processed_urls.clear() 
#         for provider in providers:
#             # Stop if we already have enough results from a previous provider
#             if len(final_hits) >= max_successful_hits_to_return:
#                 break
#             try:
#                 results = provider["function"](query, k=3)
#                 for item in results:
#                     url = item.get("link")
#                     if url and url not in processed_urls:
#                         processed_urls.add(url)
#                         processed = _process_profile_url(url, item.get("title", ""), item.get("snippet", ""), provider["name"])
#                         if processed:
#                             hits.append(processed)
#                             # Stop this inner loop if we hit the max results
#                             if len(hits) >= max_successful_hits_to_return:
#                                 return hits
#             except Exception as e:
#                 print(f"[ERROR] {provider['name']} with query '{query}' failed: {e}")
#         return hits

#     # --- STEP 1: Search with the exact query ---
#     print(f"[INFO] Step 1: Searching for exact query: '{person_query}'")
#     final_hits = search_all_providers(person_query)

#     # --- STEP 2: If no results, try reversing the name if it's a two-part name ---
#     if not final_hits:
#         query_parts = person_query.split()
#         if len(query_parts) == 2:
#             reversed_query = " ".join(reversed(query_parts))
#             print(f"[INFO] Step 2: No results found. Retrying with reversed name: '{reversed_query}'")
#             final_hits = search_all_providers(reversed_query)

#     # --- STEP 3: If still no results, fallback to a broader "AND" search ---
#     if not final_hits:
#         fallback_query = person_query.replace(" ", " AND ")
#         print(f"[INFO] Step 3: Still no results. Retrying with broader fallback: '{fallback_query}'")
#         final_hits = search_all_providers(fallback_query)

#     # --- STEP 4: Always perform a general public info search with the original query ---
#     public_info = _run_google_public_info_search(person_query, max_results=5)

#     return {
#         "query": person_query,
#         "hits": final_hits[:max_successful_hits_to_return],
#         "public_info": public_info
#     }


# if __name__ == "__main__":
#     import sys
#     if "--mcp" in sys.argv:
#         mcp.run()
#     else:
#         name = input("Enter name: ")
#         result = linkedin_contact_lookup(name)
#         print(json.dumps(result, indent=2))

# import os
# import requests
# import phonenumbers
# from bs4 import BeautifulSoup
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError as GoogleHttpError
# from dotenv import load_dotenv
# import json
# from mcp.server.fastmcp import FastMCP

# # Fallback imports
# from tavily import TavilyClient
# from duckduckgo_search import DDGS

# load_dotenv()
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# GOOGLE_CX_ID = os.getenv("GOOGLE_CX")
# TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# mcp = FastMCP("linkedin-search-v2")

# def _search_google_cse(query: str, k: int = 3):
#     if not GOOGLE_API_KEY or not GOOGLE_CX_ID:
#         print("[WARN] Missing Google CSE credentials.")
#         return
#     try:
#         svc = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
#         res = svc.cse().list(q=f'site:linkedin.com/in "{query}"', cx=GOOGLE_CX_ID, num=k).execute()
#         print("[DEBUG] Google CSE:", json.dumps(res, indent=2))
#         for item in res.get("items", []):
#             yield {"link": item.get("link"), "title": item.get("title"), "snippet": item.get("snippet")}
#     except GoogleHttpError as e:
#         print(f"[ERROR] Google CSE error: {e}")
#     except Exception as e:
#         print(f"[ERROR] Google CSE failed: {e}")

# def _search_tavily(query: str, k: int = 3):
#     if not TAVILY_API_KEY:
#         print("[WARN] Missing TAVILY_API_KEY.")
#         return
#     try:
#         client = TavilyClient(api_key=TAVILY_API_KEY)
#         response = client.search(query=f'site:linkedin.com/in "{query}"', max_results=k)
#         for item in response.get("results", []):
#             yield {"link": item.get("url"), "title": item.get("title"), "snippet": item.get("content")}
#     except Exception as e:
#         print(f"[ERROR] Tavily failed: {e}")

# def _search_duckduckgo(query: str, k: int = 3):
#     try:
#         with DDGS() as ddgs:
#             for r in ddgs.text(f'site:linkedin.com/in "{query}"', max_results=k * 2):
#                 if "linkedin.com/in/" in r.get("href", ""):
#                     yield {"link": r.get("href"), "title": r.get("title"), "snippet": r.get("body")}
#     except Exception as e:
#         print(f"[ERROR] DuckDuckGo failed: {e}")

# def _extract_phones(text: str):
#     for match in phonenumbers.PhoneNumberMatcher(text, None):
#         yield phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)

# def _process_profile_url(url: str, title: str, snippet: str, source_name: str) -> dict | None:
#     if not url or "linkedin.com/in/" not in url:
#         print(f"[WARN] Skipping invalid LinkedIn URL: {url}")
#         return None
#     try:
#         print(f"[INFO] {source_name}: Fetching {url}")
#         html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text
#         soup = BeautifulSoup(html, "html.parser")
#         main = soup.find("main") or soup.find("body")
#         content = main.get_text(" ", strip=True) if main else soup.get_text(" ", strip=True)
#         phones = list(_extract_phones(content))
#         return {
#             "url": url,
#             "phones": phones,
#             "designation": title,
#             "company": snippet,
#             "location": snippet,
#             "source": source_name
#         }
#     except Exception as e:
#         print(f"[WARN] Failed to process {url}: {e}")
#         return None

# def _run_google_public_info_search(query: str, max_results=5) -> list:
#     """Run a separate general Google search and return extra info (titles + snippets)."""
#     results = []
#     try:
#         if not GOOGLE_API_KEY or not GOOGLE_CX_ID:
#             print("[WARN] Google CSE creds missing. Skipping public info search.")
#             return results
#         svc = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
#         res = svc.cse().list(q=query, cx=GOOGLE_CX_ID, num=max_results).execute()
#         for item in res.get("items", []):
#             results.append({
#                 "title": item.get("title"),
#                 "link": item.get("link"),
#                 "snippet": item.get("snippet")
#             })
#     except Exception as e:
#         print(f"[ERROR] Google public info search failed: {e}")
#     return results

# # @mcp.tool()
# # def linkedin_contact_lookup(person_query: str) -> dict:
# #     final_hits = []
# #     processed_urls = set()
# #     max_successful_hits_to_return = 3

# #     providers = [
# #         {"name": "Google CSE", "function": _search_google_cse},
# #         {"name": "Tavily", "function": _search_tavily},
# #         {"name": "DuckDuckGo", "function": _search_duckduckgo}
# #     ]

# #     for provider in providers:
# #         if len(final_hits) >= max_successful_hits_to_return:
# #             break
# #         search_fn = provider["function"]
# #         try:
# #             results = search_fn(person_query, k=3)
# #             for item in results:
# #                 url = item.get("link")
# #                 if url and url not in processed_urls:
# #                     processed_urls.add(url)
# #                     processed = _process_profile_url(url, item.get("title", ""), item.get("snippet", ""), provider["name"])
# #                     if processed:
# #                         final_hits.append(processed)
# #                         if len(final_hits) >= max_successful_hits_to_return:
# #                             break
# #         except Exception as e:
# #             print(f"[ERROR] {provider['name']} failed: {e}")
# @mcp.tool()
# def linkedin_contact_lookup(person_query: str) -> dict:
#     final_hits = []
#     processed_urls = set()
#     max_successful_hits_to_return = 3

#     providers = [
#         {"name": "Google CSE", "function": _search_google_cse},
#         {"name": "Tavily", "function": _search_tavily},
#         {"name": "DuckDuckGo", "function": _search_duckduckgo}
#     ]

#     def search_all_providers(query: str):
#         hits = []
#         for provider in providers:
#             if len(hits) >= max_successful_hits_to_return:
#                 break
#             try:
#                 results = provider["function"](query, k=3)
#                 for item in results:
#                     url = item.get("link")
#                     if url and url not in processed_urls:
#                         processed_urls.add(url)
#                         processed = _process_profile_url(url, item.get("title", ""), item.get("snippet", ""), provider["name"])
#                         if processed:
#                             hits.append(processed)
#                             if len(hits) >= max_successful_hits_to_return:
#                                 break
#             except Exception as e:
#                 print(f"[ERROR] {provider['name']} failed: {e}")
#         return hits

#     # --- STEP 1: Exact query first ---
#     final_hits = search_all_providers(person_query)

#     # --- STEP 2: If no results, fallback to broader version ---
#     if not final_hits:
#         fallback_query = person_query.replace(" ", " AND ")
#         print(f"[INFO] No exact results, retrying with fallback query: {fallback_query}")
#         final_hits = search_all_providers(fallback_query)

#     # --- STEP 3: Always do public info search ---
#     public_info = _run_google_public_info_search(person_query, max_results=5)

#     return {
#         "query": person_query,
#         "hits": final_hits[:max_successful_hits_to_return],
#         "public_info": public_info
#     }


#     # Step 2: Direct Google search for public info (always included)
#     public_info = _run_google_public_info_search(person_query, max_results=5)

#     return {
#         "query": person_query,
#         "hits": final_hits[:max_successful_hits_to_return],
#         "public_info": public_info
#     }

# if __name__ == "__main__":
#     import sys
#     if "--mcp" in sys.argv:
#         mcp.run()
#     else:
#         name = input("Enter name: ")
#         result = linkedin_contact_lookup(name)
#         print(json.dumps(result, indent=2))




# # import os
# import requests
# import phonenumbers
# from bs4 import BeautifulSoup
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError as GoogleHttpError # Import specific error
# from dotenv import load_dotenv
# import json

# from mcp.server.fastmcp import FastMCP

# # --- New Imports for Fallbacks ---
# from tavily import TavilyClient
# from duckduckgo_search import DDGS

# # Load secrets from .env file
# load_dotenv()
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# GOOGLE_CX_ID = os.getenv("GOOGLE_CX")
# TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") # Load Tavily API Key

# # Initialize MCP tool
# mcp = FastMCP("linkedin-search-v2") # Consider versioning your tool name

# # --- Search Functions for each provider ---

# def _search_google_cse(query: str, k: int = 3):
#     """Search LinkedIn profiles using Google CSE."""
#     if not GOOGLE_API_KEY or not GOOGLE_CX_ID:
#         print("[WARN] Google API Key or CX ID not configured. Skipping Google CSE.")
#         return
#     try:
#         svc = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
#         res = svc.cse().list(q=f'site:linkedin.com/in "{query}"', cx=GOOGLE_CX_ID, num=k).execute()
#         print("[DEBUG] Google CSE raw response:", json.dumps(res, indent=2))
#         for item in res.get("items", []):
#             yield {
#                 "link": item.get("link"),
#                 "title": item.get("title"),
#                 "snippet": item.get("snippet")
#             }
#     except GoogleHttpError as e:
#         if e.resp.status == 429: # Specifically handle quota exceeded
#             print(f"[ERROR] Google CSE Quota Exceeded: {e}")
#         else:
#             print(f"[ERROR] Google CSE HTTP error: {e}")
#     except Exception as e:
#         print(f"[ERROR] Google CSE failed (non-HTTP): {e}")

# def _search_tavily(query: str, k: int = 3):
#     """Search LinkedIn profiles using Tavily."""
#     if not TAVILY_API_KEY:
#         print("[WARN] TAVILY_API_KEY not found. Skipping Tavily search.")
#         return
#     try:
#         tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
#         search_query = f'site:linkedin.com/in "{query}"'
#         # Using "basic" search_depth to conserve credits, "advanced" might yield more.
#         response = tavily_client.search(query=search_query, search_depth="basic", max_results=k, include_raw_content=False, include_answer=False)
#         print("[DEBUG] Tavily raw response:", json.dumps(response, indent=2))
#         for item in response.get("results", []):
#             yield {
#                 "link": item.get("url"),
#                 "title": item.get("title"),
#                 "snippet": item.get("content") # 'content' is Tavily's snippet equivalent
#             }
#     except Exception as e:
#         print(f"[ERROR] Tavily search failed: {e}")

# def _search_duckduckgo(query: str, k: int = 3):
#     """Search LinkedIn profiles using DuckDuckGo."""
#     try:
#         search_query = f'site:linkedin.com/in "{query}"'
#         # DDGS().text returns a generator, convert to list to control count easily
#         # Note: DuckDuckGo might not always strictly honor 'site:' or 'num' like Google/Tavily
#         with DDGS() as ddgs:
#             results = []
#             for r in ddgs.text(keywords=search_query, max_results=k*2): # fetch a bit more due to variability
#                 if "linkedin.com/in/" in r.get('href',''): # Ensure it's a profile URL
#                     results.append(r)
#                     if len(results) >= k:
#                         break
#         print("[DEBUG] DuckDuckGo raw response:", json.dumps(results, indent=2))
#         for item in results:
#             yield {
#                 "link": item.get("href"),
#                 "title": item.get("title"),
#                 "snippet": item.get("body")
#             }
#     except Exception as e:
#         print(f"[ERROR] DuckDuckGo search failed: {e}")


# # --- Helper Functions (largely unchanged) ---
# def _extract_phones(text: str):
#     """Extract phone numbers from raw HTML text."""
#     for match in phonenumbers.PhoneNumberMatcher(text, None):
#         yield phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)

# def _process_profile_url(url: str, title: str, snippet: str, source_name: str) -> dict | None:
#     """
#     Fetches content from a LinkedIn URL, extracts phones, and formats hit data.
#     Returns a dictionary if successful, None otherwise.
#     """
#     if not url or "linkedin.com/in/" not in url.lower(): # Basic check for profile URL
#         print(f"[WARN] {source_name}: Skipping non-LinkedIn profile URL or invalid URL: {url}")
#         return None
#     try:
#         print(f"[INFO] {source_name}: Checking URL: {url}")
#         # IMPORTANT: Direct scraping of LinkedIn is fragile and may get blocked.
#         # This example continues the existing method but be aware of its limitations.
#         response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"})
#         response.raise_for_status() # Raise an exception for bad status codes
#         html = response.text
#         soup = BeautifulSoup(html, "html.parser")
        
#         # Attempt to get a cleaner text representation for phone extraction
#         # This is still very broad; targeted selectors would be better but harder to maintain.
#         main_content = soup.find("main") or soup.find("body") # Try to narrow down
#         text_content = main_content.get_text(" ", strip=True) if main_content else soup.get_text(" ", strip=True)
        
#         phones = list(_extract_phones(text_content))
#         print(f"[DEBUG] {source_name}: Extracted phones for {url}: {phones if phones else 'None'}")

#         # Use original title and snippet, app.py can refine them further
#         return {
#             "url": url,
#             "phones": phones,
#             "designation": title, # Will be processed by app.py
#             "company": snippet,   # Will be processed by app.py
#             "location": snippet,  # Will be processed by app.py
#             "source": source_name
#         }
#     except requests.exceptions.RequestException as re:
#         print(f"[WARN] {source_name}: Request failed for {url}: {re}")
#     except Exception as e:
#         print(f"[WARN] {source_name}: Failed to process {url}: {e}")
#     return None

# # --- MCP Tool with Fallback Logic ---
# @mcp.tool()
# def linkedin_contact_lookup(person_query: str) -> dict:
#     """
#     Return LinkedIn profile URLs and public phone numbers (if any).
#     Tries Google CSE, then Tavily, then DuckDuckGo as fallbacks.
#     """
#     final_hits = []
#     processed_urls = set()
#     # Max desired unique, successfully processed profiles to return
#     max_successful_hits_to_return = 2
#     # How many raw search results to fetch and attempt to process from each provider
#     # This is per provider, not cumulative.
#     results_to_fetch_per_provider = 3 

#     # Define the order of search providers
#     search_providers = [
#         {"name": "Google CSE", "function": _search_google_cse},
#         {"name": "Tavily", "function": _search_tavily},
#         {"name": "DuckDuckGo", "function": _search_duckduckgo},
#     ]

#     for provider in search_providers:
#         if len(final_hits) >= max_successful_hits_to_return:
#             print(f"[INFO] Reached target of {max_successful_hits_to_return} successful hits. Stopping further searches.")
#             break

#         provider_name = provider["name"]
#         search_function = provider["function"]
#         print(f"[INFO] Attempting search with {provider_name} for '{person_query}'...")

#         try:
#             search_results_generator = search_function(person_query, k=results_to_fetch_per_provider)
#             if search_results_generator is None: # Happens if API key is missing, etc.
#                 print(f"[INFO] {provider_name} search was skipped or returned no generator.")
#                 continue

#             items_processed_from_this_provider = 0
#             for item_summary in search_results_generator:
#                 if items_processed_from_this_provider >= results_to_fetch_per_provider:
#                     break # Stop processing more items from this source than requested
#                 if len(final_hits) >= max_successful_hits_to_return:
#                     break # Stop if we've already collected enough overall

#                 url = item_summary.get("link")
#                 if url and url not in processed_urls:
#                     processed_urls.add(url) # Add to processed_urls even if processing fails, to avoid retrying same URL
                    
#                     hit_detail = _process_profile_url(
#                         url=url,
#                         title=item_summary.get("title", ""),
#                         snippet=item_summary.get("snippet", ""),
#                         source_name=provider_name
#                     )
#                     if hit_detail:
#                         final_hits.append(hit_detail)
#                         print(f"[SUCCESS] Added hit from {provider_name}: {url}")
#                 items_processed_from_this_provider +=1
            
#             if items_processed_from_this_provider > 0:
#                 print(f"[INFO] Finished processing items from {provider_name}. Current total successful hits: {len(final_hits)}")
#             else:
#                 print(f"[INFO] No new items processed or found from {provider_name}.")

#         except Exception as e: # Catch-all for unexpected errors in the search_function or its iteration
#             print(f"[ERROR] Global error during {provider_name} search/processing stage: {e}")
#             # Optionally, you could re-raise or handle more gracefully
#             # For now, just log and continue to the next provider

#     return {"query": person_query, "hits": final_hits[:max_successful_hits_to_return]}


# if __name__ == "__main__":
#     import sys
#     if "--mcp" in sys.argv:
#         mcp.run()
#     else:
#         name = input("Enter name to search: ")
#         if not name:
#             print("No name entered. Exiting.")
#         else:
#             result = linkedin_contact_lookup(name)
#             print("\n--- Final Result ---")
#             print(json.dumps(result, indent=2))


