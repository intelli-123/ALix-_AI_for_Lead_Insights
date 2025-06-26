import os
import json
import re
import requests
import logging
from dotenv import load_dotenv
from flask import Flask, request, render_template_string, redirect, url_for, session
from bs4 import BeautifulSoup
from flask_session import Session
from crewai import Agent, Task, Crew, LLM
# Removed unused Tool import for this file's logic
# from crewai_tools import Tool 

# --- SETUP ---
# Using your REAL modules now. Mocks have been removed.
from linkedin_search_mcp_1 import linkedin_contact_lookup
from sharepoint_kb import get_kb_from_db, init_db
from salesforce_mcp import fetch_salesforce_data
from ui_template import HTML


# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()
init_db()

# --- LLM & Agent Configurations ---
# Using the model you specified for the main app
llm = LLM(model="gemini/gemini-2.0-flash", api_key=os.getenv("GEMINI_API_KEY"))

# --- UI WRAPPER & STATIC CONTENT ---
def create_response_card(title: str, content_html: str) -> str:
    return f"""<div class="response-card p-4 border rounded-lg bg-white shadow-sm"><h3 class="text-lg font-semibold text-gray-800 mb-3">{title}</h3><div class="card-content text-gray-700">{content_html}</div></div>"""

# --- AGENTS & KB ---
# NOTE: The Salesforce agent is defined in your salesforce_mcp.py and is NOT needed here.
focused_analyst_agent = Agent(role="Structured Data Extractor", goal="Extract specific pieces of information from a user profile and return it in a structured JSON format.", backstory="You are an expert at parsing professional profiles.", llm=llm, verbose=True)
sharepoint_kb_agent = Agent(role="SharePoint Knowledge Analyst", goal="Compare a candidate's profile against our SharePoint knowledge base and explain any alignment.", backstory="You specialize in matching candidate profiles to our services.", llm=llm, verbose=True)
sales_copywriter_agent = Agent(role="Expert Sales Copywriter for Intelliswift", goal="Create highly personalized sales pitch content by analyzing a prospect's profile and mapping their needs to specific company offerings.", backstory="You are a world-class sales copywriter for Intelliswift.", llm=llm, verbose=True)

tool_router_agent = Agent(
    role="Intelligent Request Router and Parameter Extractor",
    goal="""Analyze the user's follow-up question. First, determine the most appropriate tool. Second, extract any specific parameters or fields the user is asking for.
            Your output MUST be a single, valid JSON object containing the 'tool_name' and a 'parameters' dictionary.

            Available Tools:
            - 'profile_summary', 'opportunity_finder', 'sales_pitch', 'sharepoint_knowledge', 'salesforce_crm', 'general_question'

            Example Scenarios:
            - User question: "can you find the company account for him from our salesforce?" -> Output: {"tool_name": "salesforce_crm", "parameters": {}}
            - User question: "what is the account id for them?" -> Output: {"tool_name": "salesforce_crm", "parameters": {"specific_field": "account_id"}}
            """,
    backstory="You are an expert at understanding user intent, routing requests, and extracting key details from questions to ensure the final answer is precise.",
    llm=llm,
    verbose=True
)

sharepoint_kb_context = get_kb_from_db()


# --- HTML TEMPLATE RENDERERS (Unchanged) ---
def format_salesforce_content(data: dict) -> str:
    intro = data.get("intro_summary", "Below are the key details from Salesforce:")
    stakeholders = data.get("stakeholders", [])
    website = data.get("website"); industry = data.get("industry"); account_id = data.get("account_id")
    html = f"<p class='mb-3'>{intro}</p>"
    if stakeholders:
        html += "<h4 class='font-semibold text-gray-800 mt-4'>Stakeholder Details:</h4><div class='mt-2 space-y-3'>"
        for person in stakeholders:
            html += f"<div class='text-sm'><strong class='text-gray-900 block'>{person.get('name')}</strong>"
            if person.get('email'): html += f"<span class='block text-gray-600'>Email: {person.get('email')}</span>"
            if person.get('phone'): html += f"<span class='block text-gray-600'>Phone: {person.get('phone')}</span>"
            html += "</div>"
        html += "</div>"
    html += "<div class='mt-4 pt-3 border-t border-gray-200 text-sm space-y-1'>"
    if website: html += f"<div><strong>Website:</strong> <a href='{website}' target='_blank' class='text-blue-600 hover:underline'>{website}</a></div>"
    if industry: html += f"<div><strong>Industry:</strong> {industry}</div>"
    if account_id: html += f"<div><strong>Salesforce Account ID:</strong> {account_id}</div>"
    html += "</div>"
    return html
# Other formatters can be added here if needed...

# --- Flask Web App ---
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/", methods=["GET", "POST"])
def home():
    if 'messages' not in session: 
        session['messages'] = [{"role": "bot", "content": "Hello! I am SAGE. Enter a person's name and company to begin, or press the refresh button to start a new search."}]
    
    if request.method == "POST":
        action = request.form.get("action")

        if action == "clear_session":
            session.clear()
            session['messages'] = [{"role": "bot", "content": "Session cleared. Ready for a new search."}]
            return redirect(url_for('home'))

        elif action == "select_profile": 
            handle_profile_selection()
        
        else:
            q = request.form.get("q", "").strip()
            if not q: return redirect(url_for('home'))
            session['messages'].append({"role": "user", "content": q})

            if 'profile_context' in session:
                handle_follow_up_question(q)
            else:
                handle_new_search(q)

    session.modified = True
    return render_template_string(HTML, messages=session.get('messages', []))

# --- Handler Functions ---
def handle_new_search(q: str):
    logging.info(f"Starting new search for: '{q}'")
    session.clear()
    session['messages'] = [{"role": "user", "content": q}]
    try:
        result = linkedin_contact_lookup(q)
        all_hits = [parse_hit(h) for h in result.get("hits", []) if h]
        if len(all_hits) > 1:
            session['pending_profiles'] = all_hits[:3]
            session['messages'].append({"role": "bot", "content": create_profile_selection_message(session['pending_profiles'])})
        elif len(all_hits) == 1:
            handle_single_profile(all_hits[0])
        else:
            session['messages'].append({"role": "bot", "content": "Sorry, I couldn't find any relevant profiles."})
    except Exception as e:
        session['messages'].append({"role": "bot", "content": f"An unexpected error occurred during search: {e}"})

def handle_profile_selection():
    idx = int(request.form.get("profile_index"))
    selected_profile = session['pending_profiles'][idx]
    session.pop('pending_profiles', None)
    handle_single_profile(selected_profile)

def handle_single_profile(profile_data):
    logging.info(f"Processing single profile: {profile_data.get('designation')}")
    session['profile_context'] = json.dumps(profile_data)
    profile_html = format_initial_profile_display(profile_data)
    session['messages'].append({"role": "bot", "content": profile_html})
    session['messages'].append({"role": "bot", "content": "I have summarized the profile above. How can I help you further?"})

def handle_follow_up_question(user_question: str):
    profile_context_str = session.get('profile_context')
    if not profile_context_str:
        session['messages'].append({"role": "bot", "content": "I've lost context. Please start a new search."})
        return
    
    profile_data = json.loads(profile_context_str)
    company_name = profile_data.get('company', '')

    task = Task(description=f"User question: '{user_question}'", expected_output="A single JSON object with 'tool_name' and 'parameters'.", agent=tool_router_agent)
    result = Crew(agents=[tool_router_agent], tasks=[task]).kickoff().raw

    try:
        route_data = json.loads(result[result.find('{'):result.rfind('}')+1])
        tool_name = route_data.get("tool_name")
        parameters = route_data.get("parameters", {})
        logging.info(f"Routing to tool: '{tool_name}' with parameters: {parameters}")
        
        answer_card = ""
        if tool_name == 'salesforce_crm':
            specific_field = parameters.get('specific_field')
            
            # Construct a detailed, natural language prompt for your salesforce_mcp module
            if specific_field:
                prompt = f"For the company '{company_name}', find the specific detail for '{specific_field}'. Please return the result as a clean JSON object."
            else:
                prompt = f"Find all account and contact information for the company '{company_name}'. Consolidate the findings into a comprehensive JSON object."

            logging.info(f"Sending prompt to salesforce_mcp: {prompt}")
            
            # Call your self-contained Salesforce module
            sf_result_str = fetch_salesforce_data(prompt)
            
            try:
                # Your module should return a JSON string. We try to parse it.
                sf_data = json.loads(sf_result_str)
                answer_card = create_response_card(f"Salesforce Summary: {sf_data.get('organization_name', company_name)}", format_salesforce_content(sf_data))
            except json.JSONDecodeError:
                # If the module returns a plain string, display it directly
                answer_card = create_response_card("Salesforce Response", f"<p>{sf_result_str}</p>")

        # Other tools would be handled here
        # elif tool_name == 'opportunity_finder':
        #    ...
        else:
            answer_card = create_response_card("SAGE", "<p>I can help with summarizing profiles, finding opportunities, or retrieving CRM data. How can I assist?</p>")

    except Exception as e:
        logging.error(f"Could not route question or execute tool: {e}. Raw router output: {result}")
        answer_card = create_response_card("Error", "<p>I had trouble understanding that request. Please try rephrasing.</p>")
        
    session['messages'].append({"role": "bot", "content": answer_card})
    session['messages'].append({"role": "bot", "content": "What else can I help you with?"})


# --- Utility Functions ---
def parse_hit(h):
    designation = h.get("designation", "")
    company = ""
    match = re.search(r'-\s*([^|-]+)', designation)
    if match:
        company = match.group(1).strip()
    else:
        company_match_keyword = re.search(r"(?:at |Experience:|\|)\s*([^·,]+)", h.get("snippet", "") + " " + designation, re.I)
        if company_match_keyword:
            company = company_match_keyword.group(1).strip()
            
    h["company"] = company
    h["skillset"] = h.get('pagemap', {}).get('metatags', [{}])[0].get('og:description', h.get("snippet", "")) or "Not specified"
    return h

def create_profile_selection_message(profiles):
    msg = "<p>I found multiple matching profiles. Please select the correct one:</p><div class='flex flex-col mt-2'>"
    for i, p in enumerate(profiles):
        company_display = f"<span class='block text-xs text-gray-500'>{p.get('company')}</span>" if p.get('company') else ""
        link = f'<a href="{p.get("url")}" target="_blank" class="text-blue-500 text-xs hover:underline flex-shrink-0 ml-4">View Profile</a>' if p.get("url") else ""
        msg += f"""<form method="POST" action="/" class="mb-2"><input type="hidden" name="action" value="select_profile"><input type="hidden" name="profile_index" value="{i}"><button type="submit" class="w-full text-left p-3 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-800 transition-all shadow-sm"><div class="flex justify-between items-center"><div class="flex-grow overflow-hidden mr-2"><strong>{p.get('designation', 'Unknown Profile')}</strong>{company_display}</div>{link}</div></button></form>"""
    return msg + "</div>"

def format_initial_profile_display(profile):
    title = f"Profile Context: {profile.get('designation', '').split(' - ')[0].strip()}"
    skills_list = profile.get('skillset', "Not specified")
    content = f"""<ul class="text-sm text-gray-700 space-y-2"><li><strong>Full Title:</strong> {profile.get('designation', 'N/A')}</li><li><strong>Company:</strong> {profile.get('company', 'N/A')}</li><li><strong>Location:</strong> {profile.get('location', 'N/A')}</li><li><strong>Profile Link:</strong> <a href="{profile.get('url', '#')}" target="_blank" class="text-blue-600 hover:underline">{profile.get('url', 'N/A')}</a></li><li><strong>Skills/Summary:</strong> {skills_list}</li></ul>"""
    return create_response_card(title, content)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5072, debug=True)