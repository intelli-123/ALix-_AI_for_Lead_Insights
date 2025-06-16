import os, json, re, requests
from dotenv import load_dotenv
from flask import Flask, request, render_template_string, redirect, url_for, session
from bs4 import BeautifulSoup
from crewai import Agent, Task, Crew, LLM
from linkedin_search_mcp import linkedin_contact_lookup
# --- MODIFICATION START ---
# Import everything needed from the updated sharepoint_kb.py file
from sharepoint_kb import get_sharepoint_kb, init_db, get_kb_from_db, update_kb_in_db
# --- MODIFICATION END ---
from ui_template import HTML

load_dotenv()

# Initialize the database cache on startup
init_db()

# --- LLM & Agent Configurations ---
llm = LLM(model="gemini/gemini-2.0-flash", api_key=os.getenv("GEMINI_API_KEY"))

# Load SharePoint KB from cache, or fetch and cache if it's empty
sharepoint_kb_context = get_kb_from_db()
if not sharepoint_kb_context:
    print("KB cache is empty. Fetching from SharePoint source to build cache...")
    try:
        # Fetch from the slow source
        sharepoint_kb_context = get_sharepoint_kb()
        # Save to the fast cache for next time
        update_kb_in_db(sharepoint_kb_context)
        print("✅ SharePoint KB loaded from source and cached successfully.")
    except Exception as e:
        print(f"❌ ERROR: Failed to load SharePoint KB on startup: {e}")
        sharepoint_kb_context = "Error: Knowledge Base could not be loaded."
else:
    print("✅ SharePoint KB loaded successfully from local cache.")


# Agents
identifier = Agent(
    role="Entity Classifier",
    goal="Detect if query is person, company, or both.",
    backstory="Expert in classifying entities.",
    llm=llm,
    verbose=True
    )

focused_analyst_agent = Agent(
    role="Focused Analyst",
    goal="Provide a concise, summary answer to a specific question using the provided profile and company knowledge base.",
    backstory="You are an expert analyst who answers questions clearly and concisely as a brief summary.",
    llm=llm,
    verbose=True
    )

summarizer_agent = Agent(
    role="Profile Summarizer",
    goal="Create a brief, engaging summary of a professional profile from its description.",
    backstory="You are an expert in creating concise professional summaries from detailed text.",
    llm=llm,
    verbose=True
)

sharepoint_kb_agent = Agent(
    role="SharePoint Knowledge Analyst",
    goal=(
        "Assess whether a candidate's profile aligns with the DevOps tools and practices documented in the SharePoint knowledge base. "
        "If aligned, respond briefly. If not, politely explain that their skills do not match our documented stack."
    ),
    backstory="You are skilled at mapping candidate profiles to internal DevOps standards based on SharePoint documentation.",
    llm=llm,
    verbose=True
)

# --- Knowledge Base ---
KB_URLS = [ "https://www.intelliswift.com/services/icaf-test-automation-framework",
            "https://www.intelliswift.com/services/digital-product-engineering",
            "https://www.intelliswift.com/services/devops-solutions",
            "https://www.intelliswift.com/",
            "https://www.intelliswift.com/services/digital-integration"]

def scrape_kb():
    kb = ""
    for url in KB_URLS:
        try:
            html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
            kb += f"\nFrom {url}:\n{BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)[:1500]}"
        except Exception as e:
            print(f"[ERROR scraping public URL {url}]:", e)
    return kb
kb_context = scrape_kb()

# --- Core Task Logic ---
def classify_entity(q: str):
    task = Task(
        description=f"Classify '{q}' as: 'person', 'company', or 'person + company'",
        expected_output="Return only the classification.",
        agent=identifier)
    return Crew(agents=[identifier], tasks=[task], process="sequential").kickoff().raw.strip().lower()

def get_focused_answer(context: str, question_key: str):
    prompts = {
        "summary": "Summarize this prospect’s profile in 3-6 engaging sentences.",
        "opportunity": "Based on the prospect's profile, what specific opportunities can Intelliswift explore for engagement? Consider their role, company context, and skillset to suggest the most relevant service areas from our offerings.",
        "final_summary": "Provide an elaborate and detailed summary (15-20 lines) of everything we know about this prospect. Synthesize all available information from their profile (role, company, detailed skills) and explicitly connect it to specific Intelliswift services from the knowledge base. Explain the strategic value and why they are a strong prospect for our company."
    }
    question = prompts.get(question_key, "Provide a general overview.")
    final_prompt = f"""CONTEXT: {context}\n\nKNOWLEDGE BASE: {kb_context}\n\nQUESTION: {question}\n\nTASK: Answer the question as a concise summary in 3-7 lines. Focus only on the information available. Do not mention what is missing. Do not use lists or bullet points."""
    task = Task(
        description=final_prompt, expected_output="A concise summary of 3-7 lines.",
        agent=focused_analyst_agent)
    return Crew(agents=[focused_analyst_agent], tasks=[task], process="sequential").kickoff().raw.strip()

def get_sharepoint_answer(question: str):
    prompt = f"""
        You are a SharePoint knowledge analyst evaluating how a candidate’s skills align with our DevOps practices as described in internal SharePoint documentation.

        Candidate description or profile:
        ---
        {question}
        ---

        SharePoint DevOps documentation summary:
        ---
        {sharepoint_kb_context}
        ---

        Please respond with a concise, polite insight:

        - If the candidate’s skills clearly match tools or practices in the KB, briefly explain how they are a strong fit.
        - If there are partial overlaps (e.g., cloud, containers, CI/CD concepts), explain where their experience may still be relevant.
        - If no explicit tools are listed, but their role or company implies engineering leadership or digital systems familiarity, politely infer potential alignment with our practices.
        - If there is no significant alignment or inference possible, politely say that their expertise lies in areas not covered by our current DevOps knowledge base.
        - Avoid repeating the candidate profile. Keep the tone constructive, insightful, and brief.
        """.strip()

    task = Task(
        description=prompt,
        expected_output="A 2–4 sentence SharePoint-based alignment summary.",
        agent=sharepoint_kb_agent
    )

    return Crew(
        agents=[sharepoint_kb_agent],
        tasks=[task],
        process="sequential").kickoff().raw.strip()


# --- Flask Web App ---
app = Flask(__name__)
app.secret_key = os.urandom(24)

CONVERSATION_FLOW = [
    {"key": "summary", "question": "I can help you by summarizing this prospect’s profile and suggesting relevant insights. Would you like me to start with a quick summary?"},
    #{"key": "relevance", "question": "I can help you identify relevant technology offerings that align with this prospect’s background. Would you like me to explore those for you?"},
    {"key": "opportunity", "question": "I can help you find potential opportunity areas to engage this prospect effectively. Want me to explore those?"},
    {"key": "final_summary", "question": "Would you like me to give you a summary of everything we’ve discussed so far?"},
    {"key": "sharepoint_summary", "question": "Do you want a quick summary of past interactions and assets stored in SharePoint for this customer pertaining to above search?"}
]

@app.route("/", methods=["GET", "POST"])
def home():
    if 'messages' not in session:
        session['messages'] = [{"role": "bot", "content": "Hello! I am LSHA, I can help you prepare for your meeting with your customer/propsect. Please start with providing name of the prospect and organization details if you are aware of the same."}]
    if request.method == "POST":
        action = request.form.get("action")
        if action == "select_profile":
            handle_profile_selection()
        else:
            q = request.form.get("q", "").strip()
            if not q: return redirect(url_for('home'))
            session['messages'].append({"role": "user", "content": q})
            if session.get('awaiting_yes_no'):
                handle_guided_question_response(q)
            else:
                handle_new_search(q)
    session.modified = True
    return render_template_string(HTML, messages=session.get('messages', []))

@app.route('/update_kb', methods=['POST'])
def update_kb():
    global sharepoint_kb_context
    try:
        print("🔄 Attempting to refresh KB from SharePoint source...")
        # Step 1: Fetch the latest data from the slow source
        latest_kb_content = get_sharepoint_kb()

        # Step 2: Update the fast database cache
        update_kb_in_db(latest_kb_content)

        # Step 3: Update the in-memory context for the current session
        sharepoint_kb_context = latest_kb_content

        print("✅ KB reloaded from source and cache updated successfully.")
        session['messages'].append({
            "role": "bot",
            "content": "✅ The SharePoint KB has been refreshed from the source and is ready to use."
        })
    except Exception as e:
        print("❌ Error refreshing KB:", e)
        session['messages'].append({
            "role": "bot",
            "content": f"⚠️ Failed to refresh SharePoint KB: {e}"
        })
    return redirect(url_for('home'))


# IMPLEMENTED LOGIC: This function handles different search types.
def handle_new_search(q: str):
    session.clear(); session['messages'] = [{"role": "user", "content": q}]
    try:
        entity_type = classify_entity(q)
        result = linkedin_contact_lookup(q)
        all_hits = [parse_hit(h) for h in result.get("hits", [])]

        if entity_type == 'person':
            query_name_parts = [part.lower() for part in q.split() if part]
            primary_hits = [h for h in all_hits if all(part in h.get('designation', '').lower() for part in query_name_parts)]
            if len(primary_hits) > 1:
                session['pending_profiles'] = primary_hits[:3]
                session['messages'].append({"role": "bot", "content": create_profile_selection_message(session['pending_profiles'])})
                return
            elif primary_hits:
                all_hits = primary_hits # Use the single best match

        # This handles company, person+company, and single-result person searches
        if all_hits:
            handle_single_profile(all_hits[0])
        else:
            session['messages'].append({"role": "bot", "content": "Sorry, I couldn't find any relevant profiles for that query."})

    except Exception as e: # Broadened exception to catch HttpError and others
        # Specific check for 429 error if possible, requires inspecting the exception object
        if "429" in str(e):
             session['messages'].append({"role": "bot", "content": "Search quota exceeded. Please try again later."})
        else:
             session['messages'].append({"role": "bot", "content": f"An unexpected error occurred: {e}"})


def handle_profile_selection():
    idx = int(request.form.get("profile_index"))
    if 'pending_profiles' in session and idx < len(session['pending_profiles']):
        selected_profile = session['pending_profiles'][idx]
        session['messages'].append({"role": "user", "content": f"Selected: {selected_profile.get('designation')}"})
        handle_single_profile(selected_profile)
        session.pop('pending_profiles', None)
    else:
        session['messages'].append({"role": "bot", "content": "Something went wrong. Please try your search again."})

def handle_guided_question_response(user_input: str):
    if user_input.lower() not in ['yes', 'y', 'no', 'n']:
        handle_new_search(user_input)
        return

    step, context = session.get('question_step', 0), session.get('last_context')

    if not context:
        session['messages'].append({
            "role": "bot",
            "content": "I've lost the context. Please start a fresh search again."
        })
        session.pop('awaiting_yes_no', None)
        return

    if user_input.lower() in ['yes', 'y']:
        key = CONVERSATION_FLOW[step]['key']
        if key == "sharepoint_summary":
            try:
                print("🔁 [SP] Entering SharePoint summary block.")
                profile = json.loads(context) if isinstance(context, str) else context
                print("📦 [SP] Context loaded:", profile)

                company = profile.get("company", "") or profile.get("designation", "")
                print("🏷️ [SP] Extracted company/designation:", company)

                if not company:
                    session['messages'].append({
                        "role": "bot",
                        "content": "I couldn't find a company or designation to look up in SharePoint."
                    })
                    return

                sp_question = f"What are the past interactions and internal assets related to '{company}' in our SharePoint documentation?"
                print("❓ [SP] SP Question:", sp_question)

                sp_response = get_sharepoint_answer(sp_question)
                print("✅ [SP] SP Response:", sp_response)

                session['messages'].append({
                    "role": "bot",
                    "content": sp_response
                })
            except Exception as e:
                print("❌ [SP] Error during SharePoint lookup:", str(e))
                session['messages'].append({
                    "role": "bot",
                    "content": "Something went wrong while fetching SharePoint insights."
                })
        else:
            answer = get_focused_answer(context, key)
            session['messages'].append({"role": "bot", "content": answer})
    else:
        session['messages'].append({"role": "bot", "content": "Okay, skipping that."})

    session['question_step'] = step + 1

    if session['question_step'] < len(CONVERSATION_FLOW):
        next_question = CONVERSATION_FLOW[session['question_step']]['question']
        session['messages'].append({
            "role": "bot",
            "content": f"<p class='mt-4'>{next_question}</p>"
        })
    else:
        # ✅ FINAL MESSAGE WITH COLOR (previously missing)
        session['messages'].append({
            "role": "bot",
            "content": "<span class='text-blue-600'>That's all the insights I have for now. Please start a fresh search again.</span>"
        })
        session.pop('last_context', None)
        session.pop('awaiting_yes_no', None)

def handle_single_profile(profile_data):
    """Initial handling of a found profile."""
    session['last_context'] = json.dumps(profile_data)
    profile_html = format_initial_profile_display(profile_data)
    session['messages'].append({"role": "bot", "content": profile_html})
    session['question_step'] = 0
    session['awaiting_yes_no'] = True
    first_question = CONVERSATION_FLOW[0]['question']
    session['messages'].append({"role": "bot", "content": f"<p class='mt-4'>{first_question} </p>"}) # (Please type 'yes' or 'no')

def parse_hit(h):
    """Enriches the search hit with parsed data."""
    designation = h.get("designation", "")
    snippet = h.get("snippet", "")
    company_match = re.search(r"(?:at |Experience:|\|)\s*([^·,]+)", snippet + " " + designation, re.I)
    h["company"] = company_match.group(1).strip() if company_match else ""
    try:
        meta_desc = h.get('pagemap', {}).get('metatags', [{}])[0].get('og:description', snippet)
        h["skillset"] = meta_desc
    except (IndexError, KeyError):
        h["skillset"] = snippet
    return h

# --- HTML Formatting Function ---
def create_profile_selection_message(profiles):
    """Creates HTML buttons for the user to select from multiple profiles."""
    msg = "<p>There are multiple matching profiles. Could you please select the correct one from the list:</p><div class='flex flex-col gap-2 mt-2'>"
    for i, p in enumerate(profiles):
        company_display = f"<span class='block text-xs text-gray-500'>{p.get('company')}</span>" if p.get('company') else ""
        linkedin_link = f'<a href="{p.get("url")}" target="_blank" class="text-blue-500 text-xs hover:underline flex-shrink-0 ml-4">View Profile</a>' if p.get("url") else ""
        msg += f"""<form method="POST" class="w-full">
            <input type="hidden" name="action" value="select_profile"><input type="hidden" name="profile_index" value="{i}">
            <button type="submit" class="w-full text-left p-3 bg-purple-100 hover:bg-purple-200 rounded-lg text-purple-800 transition-all">
                <div class="flex justify-between items-center"><div class="flex-grow overflow-hidden mr-2">
                    <strong>{p.get('designation', 'Unknown Profile')}</strong>{company_display}
                </div>{linkedin_link}</div></button></form>"""
    return msg + "</div>"

def format_initial_profile_display(profile):
    """Formats the initial profile display to match the desired structured format."""
    profile_title = f'<h4 class="font-bold text-lg text-purple-700">Profile: {profile.get("designation", "")}</h4>'

    link_line = f'<li><strong>Link:</strong> <a href="{profile.get("url")}" target="_blank" class="text-blue-600 hover:underline">{profile.get("url")}</a></li>' if profile.get("url") else ""
    company_line = f'<li><strong>Current Company:</strong> {profile.get("company")}</li>' if profile.get("company") else ""
    skillset_line = f'<li><strong>Skillset:</strong> {profile.get("skillset")}</li>' if profile.get("skillset") else ""

    all_items = [link_line, company_line, skillset_line]
    valid_items = "".join([item for item in all_items if item and "</strong>" in item and not item.endswith("</strong> ")])

    return f"""<div class="p-4 border rounded-lg bg-slate-50 shadow-sm">
        {profile_title}
        <ul class="mt-2 text-sm text-gray-800 space-y-1 list-none">
            {valid_items}
        </ul>
    </div>"""

@app.route("/clear")
def clear():
    session.clear()
    return redirect(url_for("home"))

@app.route('/')
def index():
    return render_template_string(HTML)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5078, debug=True)

