# #!/usr/bin/env python
# import os, json, re
# from dotenv import load_dotenv
# from flask import Flask, request, render_template_string, redirect, url_for
# from crewai import Agent, Task, Crew, LLM
# from crewai.tools import BaseTool
# from pydantic import BaseModel, Field
# from typing import Type
# from linkedin_search_mcp import linkedin_contact_lookup
# from ui_template import HTML

# load_dotenv()

# llm = LLM(
#     model="gemini/gemini-1.5-flash",
#     api_key=os.getenv("GEMINI_API_KEY")
# )

# # Define tool input schema properly
# class LinkedInQueryInput(BaseModel):
#     person_query: str = Field(..., description="Name of person or company to search")

# class LinkedInTool(BaseTool):
#     name: str = "LinkedInContactLookup"
#     description: str = "Fetches LinkedIn profile & contact info using multiple search engines"
#     args_schema: Type[BaseModel] = LinkedInQueryInput

#     def _run(self, person_query: str) -> str:
#         print(f"[TOOL] Looking up: {person_query}")
#         result = linkedin_contact_lookup(person_query)
#         hits = result.get("hits", [])[:2]

#         # for h in hits:
#         #     snippet = h.get("company", "")
#         #     loc_match = re.search(r"(Location|অবস্থান): ([^\|,\n]+)", snippet, re.I)
#         #     if loc_match:
#         #         h["location"] = loc_match.group(2).strip()
#         #     company_match = re.search(r"(Company|at|Experience|অভিজ্ঞতা):\s*(.*?)([.|,]|$)", snippet, re.I)
#         #     if company_match:
#         #         h["company"] = company_match.group(2).strip()
#         # return json.dumps(hits)

#         for h in hits:
#             snippet = h.get("company", "") or ""

#             # Extract location if available in the snippet
#             loc_match = re.search(r"(Location|অবস্থান):\s*([^\|,\n]+)", snippet, re.I)
#             if loc_match:
#                 h["location"] = loc_match.group(2).strip()

#             # Try to extract company name
#             company_match = re.search(r"(Company|at|Experience|অভিজ্ঞতা):\s*([^\|,.]+)", snippet, re.I)
#             if company_match:
#                 h["company"] = company_match.group(2).strip()
#             else:
#                 h["company"] = "N/A"

#             # Everything remaining in the snippet → treat as skillset
#             # Remove company name if found and clean up
#             skill_text = snippet.replace(h["company"], "") if h.get("company") and h["company"] != "N/A" else snippet
#             h["skills"] = skill_text.strip(" \n\t:-,.")

#         return json.dumps(hits)



# tools = [LinkedInTool()]

# def run_lookup(query: str):
#     agent = Agent(
#         role="LookupBot",
#         goal="Return structured contact info.",
#         backstory="Skilled researcher using LinkedIn and fallback search.",
#         tools=tools,
#         llm=llm,
#         verbose=True
#     )

#     task = Task(
#         description=f"Find contact info for {query}.",
#         expected_output="List of dicts with url, designation, company, location, phones.",
#         agent=agent
#     )

#     out = Crew(agents=[agent], tasks=[task]).kickoff()
#     raw = out.raw.strip().strip("`")
#     print("[DEBUG] Raw Output:", raw)

#     if raw.startswith("{") or raw.startswith("["):
#         try:
#             return json.loads(raw)
#         except Exception as e:
#             print("[ERROR] JSON parse error:", e)
#     else:
#         print("[WARN] Output was not JSON. Skipping.")
#     return []

# def generate_recommendations(entity: str, viewer_company: str):
#     agent = Agent(
#         role="Business Recommender",
#         goal="Suggest B2B services based on company profile",
#         backstory="Experienced strategy analyst",
#         llm=llm
#     )

#     task = Task(
#         description=f"""Given the entity '{entity}', and your company is '{viewer_company}',
# write 3-5 brief and useful B2B recommendations to help offer services/products.""",
#         agent=agent,
#         expected_output="Bullet list of business suggestions"
#     )

#     out = Crew(agents=[agent], tasks=[task]).kickoff()
#     return out.raw.strip().strip("`")

# app = Flask(__name__)

# @app.route("/", methods=["GET", "POST"])
# def home():
#     q = request.form.get("q", "").strip() if request.method == "POST" else request.args.get("q", "")
#     hits = run_lookup(q) if q and request.method == "POST" else None
#     reco = generate_recommendations(q, "Intelliswift") if hits else None

#     return render_template_string(
#         HTML,
#         hits=hits,
#         q=q,
#         page=1,
#         total_pages=1,
#         show_embed=False,
#         reco=reco
#     )

# @app.route("/clear")
# def clear():
#     return redirect(url_for("home"))

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5079, debug=True)

################################################

# #!/usr/bin/env python
# import os, json, re
# from dotenv import load_dotenv
# from flask import Flask, request, render_template_string, redirect, url_for
# from crewai import Agent, Task, Crew, LLM
# from crewai.tools import BaseTool
# from pydantic import BaseModel, Field
# from typing import Type
# import chromadb

# # ✅ Fallback-aware MCP tool
# from linkedin_search_mcp import linkedin_contact_lookup
# from ui_template import HTML

# # Load environment variables
# load_dotenv()

# # Setup ChromaDB
# client = chromadb.Client()
# try:
#     collection = client.get_or_create_collection("linkedin")
# except Exception as e:
#     print("[ERROR] Failed to access ChromaDB collection:", e)
#     collection = None

# # Setup LLM (Gemini 1.5 Flash)
# llm = LLM(
#     model="gemini/gemini-1.5-flash",
#     api_key=os.getenv("GEMINI_API_KEY")
# )

# # CrewAI tool that wraps MCP lookup
# class LinkedInQueryInput(BaseModel):
#     person_query: str = Field(..., description="Name of person or company to search")

# class LinkedInTool(BaseTool):
#     name: str = "LinkedInContactLookup"
#     description: str = "Fetches LinkedIn profile & contact info using multiple search engines"
#     args_schema: Type[BaseModel] = LinkedInQueryInput

#     def _run(self, person_query: str) -> str:
#         print(f"[TOOL] Searching via MCP: {person_query}")
#         result = linkedin_contact_lookup(person_query)  # ✅ Uses fallback MCP
#         hits = result.get("hits", [])[:2]

#         # Try to extract company/location from snippet if not set
#         for h in hits:
#             snippet = h.get("company", "") or h.get("location", "")
#             loc_match = re.search(r"(Location|অবস্থান): ([^\|,\n]+)", snippet, re.I)
#             if loc_match:
#                 h["location"] = loc_match.group(2).strip()
#             company_match = re.search(r"(Company|at|Experience|অভিজ্ঞতা):\s*(.*?)([.|,]|$)", snippet, re.I)
#             if company_match:
#                 h["company"] = company_match.group(2).strip()

#         # Store each hit in ChromaDB
#         if collection:
#             for i, h in enumerate(hits):
#                 try:
#                     collection.add(
#                         documents=[json.dumps(h)],
#                         metadatas=[{"source": person_query}],
#                         ids=[f"{person_query}_{i}"]
#                     )
#                 except Exception as e:
#                     print(f"[WARN] Skipped ChromaDB entry: {e}")

#         return json.dumps(hits)

# tools = [LinkedInTool()]

# # Crew execution for search
# def run_lookup(query: str):
#     agent = Agent(
#         role="LookupBot",
#         goal="Return structured contact info.",
#         backstory="Searches profiles using LinkedIn tool.",
#         tools=tools,
#         llm=llm,
#         verbose=True
#     )

#     task = Task(
#         description=f"Find contact info for {query}.",
#         expected_output="List of dicts with url, designation, company, location, phones.",
#         agent=agent
#     )

#     out = Crew(agents=[agent], tasks=[task]).kickoff()
#     raw = out.raw.strip().strip("`")
#     print("[DEBUG] Raw Output:", raw)

#     if raw.startswith("{") or raw.startswith("["):
#         try:
#             parsed = json.loads(raw)
#             if isinstance(parsed, list):
#                 # Sort by relevance — if query name is in the designation/title
#                 parsed.sort(key=lambda h: query.lower() in (h.get("designation", "") + h.get("company", "")).lower(), reverse=True)
#             return parsed
#         except Exception as e:
#             print("[ERROR] JSON parse error:", e)
#     else:
#         print("[WARN] Output was not JSON. Skipping.")
#     return []


# # Business recommendation generation
# def generate_recommendations(entity: str, viewer_company: str):
#     agent = Agent(
#         role="Business Recommender",
#         goal="Propose B2B opportunities based on target entity.",
#         backstory="Provides strategic ideas for business engagement.",
#         llm=llm
#     )

#     task = Task(
#         description=f"""You are from {viewer_company}. Based on the entity '{entity}', 
# propose 3 to 5 concise business recommendations for B2B collaboration.""",
#         expected_output="List of B2B suggestions.",
#         agent=agent
#     )

#     out = Crew(agents=[agent], tasks=[task]).kickoff()
#     return out.raw.strip().strip("`")

# # Flask app
# app = Flask(__name__)

# @app.route("/", methods=["GET", "POST"])
# def home():
#     q = request.form.get("q", "").strip() if request.method == "POST" else request.args.get("q", "")
#     page = int(request.args.get("page", 1))
#     show_embed = request.args.get("embed", "false") == "true"

#     hits = run_lookup(q) if q and request.method == "POST" else None

#     try:
#         results = collection.query(query_texts=[q], n_results=10) if q and collection else None
#         all_docs = results["documents"][0] if results and results["documents"] else []
#     except Exception as e:
#         print("[WARN] Failed ChromaDB query:", e)
#         all_docs = []

#     total_pages = (len(all_docs) + 1) // 2
#     docs = all_docs[(page - 1) * 2: page * 2]
#     parsed = [json.loads(d) for d in docs] if docs else hits

#     # Generate recommendations if we have results
#     reco = generate_recommendations(q, "Intelliswift") if parsed else None

#     return render_template_string(
#         HTML,
#         hits=parsed,
#         q=q,
#         page=page,
#         total_pages=total_pages,
#         show_embed=show_embed,
#         reco=reco
#     )

# @app.route("/clear")
# def clear():
#     try:
#         client.delete_collection("linkedin")
#         print("[INFO] ChromaDB cleared.")
#     except Exception as e:
#         print("[WARN] Failed to clear ChromaDB:", e)
#     return redirect(url_for("home"))

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5079, debug=True)


# #/ALix_AI_for_Lead_Insights/app.py
# #!/usr/bin/env python
# import os, json, re
# from dotenv import load_dotenv
# from flask import Flask, request, render_template_string, redirect, url_for
# from crewai import Agent, Task, Crew, LLM
# from crewai.tools import BaseTool
# from pydantic import BaseModel, Field
# from typing import Type
# import chromadb
# from linkedin_search_mcp import linkedin_contact_lookup
# from ui_template import HTML

# # Load environment
# load_dotenv()

# # Initialize ChromaDB client
# client = chromadb.Client()
# try:
#     collection = client.get_or_create_collection("linkedin")
# except Exception as e:
#     print("[ERROR] Failed to create or access collection:", e)
#     collection = None

# # Initialize Gemini 1.5 Flash
# llm = LLM(
#     model="gemini/gemini-1.5-flash",
#     api_key=os.getenv("GEMINI_API_KEY")
# )

# # CrewAI Tool
# class LinkedInQueryInput(BaseModel):
#     person_query: str = Field(..., description="Name of person or company to search")

# class LinkedInTool(BaseTool):
#     name: str = "LinkedInContactLookup"
#     description: str = "Fetches LinkedIn profile & contact info using Google CSE"
#     args_schema: Type[BaseModel] = LinkedInQueryInput

#     def _run(self, person_query: str) -> str:
#         print(f"[TOOL] Searching for: {person_query}")
#         result = linkedin_contact_lookup(person_query)
#         hits = result.get("hits", [])[:2]

#         # Extract company & location from snippet if possible
#         for h in hits:
#             snippet = h.get("company", "")
#             loc_match = re.search(r"(Location|অবস্থান): ([^\|,\n]+)", snippet, re.I)
#             if loc_match:
#                 h["location"] = loc_match.group(2).strip()
#             company_match = re.search(r"(Company|at|Experience|অভিজ্ঞতা):\s*(.*?)([.|,]|$)", snippet, re.I)
#             if company_match:
#                 h["company"] = company_match.group(2).strip()

#         # Store in ChromaDB
#         if collection:
#             for i, h in enumerate(hits):
#                 try:
#                     collection.add(
#                         documents=[json.dumps(h)],
#                         metadatas=[{"source": person_query}],
#                         ids=[f"{person_query}_{i}"]
#                     )
#                 except Exception as e:
#                     print(f"[WARN] Could not add to ChromaDB: {e}")

#         return json.dumps(hits)

# # CrewAI lookup execution
# tools = [LinkedInTool()]

# def run_lookup(query: str):
#     agent = Agent(
#         role="LookupBot",
#         goal="Return structured contact info.",
#         backstory="Searches profiles using LinkedIn tool.",
#         tools=tools,
#         llm=llm,
#         verbose=True
#     )

#     task = Task(
#         description=f"Find contact info for {query}.",
#         expected_output="List of dicts with url, designation, company, location, phones.",
#         agent=agent
#     )

#     out = Crew(agents=[agent], tasks=[task]).kickoff()
#     raw = out.raw.strip().strip("`")
#     print("[DEBUG] Raw Output:", raw)

#     # Attempt to parse only if it looks like JSON
#     if raw.startswith("{") or raw.startswith("["):
#         try:
#             return json.loads(raw)
#         except Exception as e:
#             print("[ERROR] JSON parse error:", e)
#     else:
#         print("[WARN] Output was not JSON. Skipping.")
#     return []

# # Recommendation Crew
# def generate_recommendations(entity: str, viewer_company: str):
#     agent = Agent(
#         role="Business Recommender",
#         goal="Recommend B2B services based on company profile",
#         backstory="Market intelligence strategist",
#         llm=llm
#     )

#     task = Task(
#         description=f"""Given the entity '{entity}', and that you represent '{viewer_company}',
# write 3 to 5 brief, useful business recommendations tailored to help you offer services/products to the entity.""",
#         agent=agent,
#         expected_output="Bullet list of B2B recommendations."
#     )

#     out = Crew(agents=[agent], tasks=[task]).kickoff()
#     return out.raw.strip().strip("`")

# # Flask app setup
# app = Flask(__name__)

# @app.route("/", methods=["GET", "POST"])
# def home():
#     q = request.form.get("q", "").strip() if request.method == "POST" else request.args.get("q", "")
#     page = int(request.args.get("page", 1))
#     show_embed = request.args.get("embed", "false") == "true"

#     hits = run_lookup(q) if q and request.method == "POST" else None

#     try:
#         results = collection.query(query_texts=[q], n_results=10) if q and collection else None
#         all_docs = results["documents"][0] if results and results["documents"] else []
#     except Exception as e:
#         print("[WARN] Failed to query ChromaDB:", e)
#         all_docs = []

#     total_pages = (len(all_docs) + 1) // 2
#     docs = all_docs[(page - 1) * 2: page * 2]
#     parsed = [json.loads(d) for d in docs] if docs else hits

#     # Reco only if we have at least one contact result
#     reco = generate_recommendations(q, "Intelliswift") if parsed else None

#     return render_template_string(
#         HTML,
#         hits=parsed,
#         q=q,
#         page=page,
#         total_pages=total_pages,
#         show_embed=show_embed,
#         reco=reco
#     )

# @app.route("/clear")
# def clear():
#     try:
#         client.delete_collection("linkedin")
#         print("[INFO] ChromaDB collection cleared.")
#     except Exception as e:
#         print("[WARN] Failed to delete collection:", e)
#     return redirect(url_for("home"))

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5079, debug=True)


######################################################

# from flask import Flask, request, render_template_string
# from crew_recommendation import run_pipeline, get_last_hits
# from ui_template import HTML

# app = Flask(__name__)

# @app.route("/", methods=["GET", "POST"])
# def home():
#     recommendations = None
#     hits = None
#     q = ""
#     if request.method == "POST":
#         q = request.form.get("q", "").strip()
#         company = request.form.get("company", "").strip()
#         if q and company:
#             recommendations = run_pipeline(q, company)
#             hits = get_last_hits()
#     return render_template_string(HTML, hits=hits, recs=recommendations, q=q)

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5079, debug=True)
