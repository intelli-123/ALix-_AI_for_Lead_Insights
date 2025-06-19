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

# --- SETUP ---
from linkedin_search_mcp_1 import linkedin_contact_lookup
from sharepoint_kb import get_sharepoint_kb, init_db, get_kb_from_db, update_kb_in_db
from salesforce_mcp import fetch_salesforce_data
from ui_template import HTML

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()
init_db()

# --- LLM & Agent Configurations ---
llm = LLM(model="gemini/gemini-2.0-flash", api_key=os.getenv("GEMINI_API_KEY"))

# --- UI WRAPPER & STATIC CONTENT ---
def create_response_card(title: str, content_html: str) -> str:
    return f"""<div class="response-card p-4 border rounded-lg bg-white shadow-sm"><h3 class="text-lg font-semibold text-gray-800 mb-3">{title}</h3><div class="card-content text-gray-700">{content_html}</div></div>"""

UPCOMING_FEATURES_DATA = {"title": "Upcoming features:", "content_html": """<ul class='list-disc list-inside space-y-1'><li>Persona-based pitch decks (VP Tech, QA Heads, etc.)</li><li>Salesforce CRM integration for tracking engagements</li><li>AWS for hosting of our accelerators</li><li>Better trained Model</li><li>Vector DB and RAG implementation</li></ul>"""}

# --- Agents & KB ---
identifier = Agent(role="Entity Classifier", goal="Detect if query is person, company, or both.", backstory="Expert in classifying entities.", llm=llm, verbose=True)
focused_analyst_agent = Agent(role="Structured Data Extractor", goal="Extract specific pieces of information from a user profile and return it in a structured JSON format.", backstory="You are an expert at parsing professional profiles.", llm=llm, verbose=True)
sharepoint_kb_agent = Agent(role="SharePoint Knowledge Analyst", goal="Compare a candidate's profile against our SharePoint knowledge base and explain any alignment.", backstory="You specialize in matching candidate profiles to our services.", llm=llm, verbose=True)
sales_copywriter_agent = Agent(role="Expert Sales Copywriter for Intelliswift", goal="Create highly personalized sales pitch content by analyzing a prospect's profile and mapping their needs to specific company offerings.", backstory="You are a world-class sales copywriter for Intelliswift.", llm=llm, verbose=True)
profile_parser_agent = Agent(role="Profile Data Analyst", goal="Read unstructured text from a professional profile and extract specific, structured data points like skills, experience summary, and location. The output must be a clean JSON object.", backstory="You are a meticulous analyst who can read through long, messy text and pull out the most important, structured information.", llm=llm, verbose=True)
sharepoint_kb_context = get_kb_from_db()
KB_URLS = ["https://www.intelliswift.com/services/digital-product-engineering", "https://www.intelliswift.com/services/devops-solutions", "https://www.intelliswift.com/", "https://www.intelliswift.com/services/digital-integration"]
def scrape_kb():
    kb = "";
    for url in KB_URLS:
        try:
            html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
            kb += f"\nFrom {url}:\n{BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)[:1500]}"
        except Exception as e:
            logging.error(f"Error scraping public URL {url}: {e}")
    return kb
kb_context = scrape_kb()

# --- HTML TEMPLATE RENDERERS ---
def format_offerings_content(offerings: list) -> str:
    html = "<ul class='space-y-4'>"
    for offering in offerings:
        name = offering.get("name", "Offering"); description = offering.get("description", "No details available.")
        html += f"<li><strong class='text-gray-900'>{name}:</strong> {description}</li>"
    html += "</ul>"
    return html

def format_sharepoint_summary_content(data: dict) -> str:
    intro = data.get("intro_sentence", ""); points = data.get("summary_points", [])
    html = f"<p class='mb-3'>{intro}</p><ul class='space-y-3'>"
    for point in points:
        title = point.get("title", "Insight"); description = point.get("description", "No details available.")
        html += f"<li><strong class='text-gray-900'>{title}:</strong> {description}</li>"
    html += "</ul>"
    return html

def format_sales_pitch_content(data: dict) -> str:
    opening_paragraph = data.get("opening_paragraph", "")
    bullet_points = data.get("bullet_points", [])
    html = f"""<p class="mb-4">{opening_paragraph}</p>"""
    if bullet_points:
        html += "<p class='mb-4'>Based on your profile, here are a few ways we could partner:</p><ul class='space-y-3 list-disc list-inside'>"
        for point in bullet_points: html += f"<li>{point}</li>"
        html += "</ul>"
    return html

def format_profile_summary_content(data: dict) -> str:
    title_line = data.get("title_line", "")
    summary_points = data.get("profile_summary_points", [])
    opportunities = data.get("intelliswift_opportunities", {})
    html = f"""<p class="text-sm text-gray-600 mb-4">{title_line}</p><h4 class='font-semibold text-gray-800 mt-4'>Profile summary:</h4><ul class='list-disc list-inside text-gray-700 space-y-1 mt-2'>"""
    for point in summary_points: html += f"<li>{point}</li>"
    html += "</ul>"
    if opportunities:
        html += "<h4 class='font-semibold text-gray-800 mt-4'>Intelliswift Opportunities:</h4><div class='mt-2 ml-4 space-y-3'>"
        for category, points in opportunities.items():
            html += f"<h5 class='font-semibold text-gray-700'>{category}:</h5><ul class='list-disc list-inside text-gray-600 space-y-1 ml-6'>"
            for point in points: html += f"<li>{point}</li>"
            html += "</ul>"
        html += "</div>"
    return html

# <<< --- NEW SALESFORCE FORMATTER --- >>>
def format_salesforce_content(data: dict) -> str:
    """Builds the HTML for the structured Salesforce data card."""
    intro = data.get("intro_summary", "Below are the key details from Salesforce:")
    stakeholders = data.get("stakeholders", [])
    website = data.get("website")
    industry = data.get("industry")
    account_id = data.get("account_id")

    html = f"<p class='mb-3'>{intro}</p>"
    if stakeholders:
        html += "<h4 class='font-semibold text-gray-800 mt-4'>Stakeholder Details:</h4>"
        html += "<div class='mt-2 space-y-3'>"
        for person in stakeholders:
            html += f"<div class='text-sm'><strong class='text-gray-900 block'>{person.get('name')}</strong>"
            if person.get('email'):
                html += f"<span class='block text-gray-600'>Email: {person.get('email')}</span>"
            if person.get('phone'):
                html += f"<span class='block text-gray-600'>Phone: {person.get('phone')}</span>"
            html += "</div>"
        html += "</div>"
    
    html += "<div class='mt-4 pt-3 border-t border-gray-200 text-sm space-y-1'>"
    if website:
        html += f"<div><strong>Website:</strong> <a href='{website}' target='_blank' class='text-blue-600 hover:underline'>{website}</a></div>"
    if industry:
        html += f"<div><strong>Industry:</strong> {industry}</div>"
    if account_id:
        html += f"<div><strong>Salesforce Account ID:</strong> {account_id}</div>"
    html += "</div>"
    
    return html


# --- Core Task & Agent Logic ---
def classify_entity(q: str):
    task = Task(description=f"Classify '{q}' as: 'person', 'company', or 'person + company'", expected_output="Return only the classification.", agent=identifier)
    return Crew(agents=[identifier], tasks=[task]).kickoff().raw.strip().lower()

def get_focused_answer(context: str, question_key: str):
    # This function is unchanged
    logging.info(f"Generating DYNAMIC answer for key: '{question_key}'")
    answer_data = {}
    if question_key == 'summary':
        prompt = f"""From the provided context, extract information for a profile summary. Return a SINGLE, VALID JSON object. Your response must be only the JSON. Context: ```{context}``` JSON Schema: {{"name": "Full Name", "title_line": "Current Title, Company, and former companies.", "profile_summary_points": ["Point 1", "Point 2"], "intelliswift_opportunities": {{"Category 1": ["Point 1"]}}}}"""
        task = Task(description=prompt, expected_output="A single, valid JSON object.", agent=focused_analyst_agent)
        result = Crew(agents=[focused_analyst_agent], tasks=[task]).kickoff().raw
        try:
            json_start_index = result.find('{'); json_end_index = result.rfind('}') + 1
            if json_start_index != -1 and json_end_index != 0:
                data = json.loads(result[json_start_index:json_end_index])
                answer_data = {"title": f"Summary: {data.get('name', '')}", "content_html": format_profile_summary_content(data)}
            else: raise ValueError("No JSON object found")
        except Exception as e:
            answer_data = {"title": "Error", "content_html": f"<p>Error structuring profile summary: {e}</p>"}
    elif question_key == 'opportunity':
        offering_list_text = """- ICAF (Intelliswift Cloud Automation Framework): A plug-and-play automation accelerator designed to streamline cloud adoption, infrastructure provisioning, and environment management—reducing deployment time and enhancing consistency.\n- Internal Developer Platform (IDP): A self-service platform built to simplify development workflows with GitOps (Harness, Argo CD), automated CI/CD pipelines, and integrated DevSecOps—boosting speed, compliance, and developer autonomy.\n- AI in Digital Integration: Accelerate transformation through intelligent API-led integrations, predictive routing, and smart orchestration—optimizing business processes and improving real-time decision-making.\n- DevOps and QA Automation: Deliver higher quality software faster with our integrated DevOps toolchain and AI-powered QA automation. From shift-left testing to continuous validation, we ensure faster feedback cycles and improved reliability."""
        prompt = f"""You are an expert sales analyst for Intelliswift. Your goal is to identify and describe the most relevant service offerings for a prospect from a specific list. Analyze the prospect's profile below and select the **2 or 3 most relevant offerings** from the list provided. **Prospect Profile:** ```{context}``` **List of Available Offerings (Choose from this list ONLY):** {offering_list_text} **Instructions:** Return a SINGLE, VALID JSON object with a single key "offerings". The value should be a list of dictionaries for only the selected offerings. For each selected offering, copy its name and description exactly from the list. **Required JSON Schema:** {{"offerings": [{{"name": "Name of the Selected Offering", "description": "The exact description from the list."}}]}}"""
        task = Task(description=prompt, expected_output="A JSON object with a list of 2-3 tailored offerings.", agent=sales_copywriter_agent)
        result = Crew(agents=[sales_copywriter_agent], tasks=[task]).kickoff().raw
        try:
            json_start_index = result.find('{'); json_end_index = result.rfind('}') + 1
            if json_start_index != -1 and json_end_index != 0:
                data = json.loads(result[json_start_index:json_end_index])
                answer_data = {"title": "Intelliswift Offerings:", "content_html": format_offerings_content(data.get("offerings", []))}
            else: raise ValueError("No JSON object found")
        except Exception as e:
            answer_data = {"title": "Error", "content_html": f"<p>Error generating dynamic offerings: {e}</p>"}
    elif question_key == 'final_summary':
        prompt = f"""You are an expert sales copywriter for Intelliswift. Your task is to write a personalized sales pitch using the **Internal SharePoint KB**. **Instructions:** Analyze the Prospect Profile and the Internal SharePoint KB. Write a personalized opening paragraph and 2-3 bullet points connecting the prospect's needs to solutions in the SharePoint KB. Return a SINGLE, VALID JSON object. **Prospect Profile:** ```{context}``` **Internal SharePoint KB:** ```{sharepoint_kb_context}``` **Required JSON Schema:** {{"first_name": "Prospect's first name.", "opening_paragraph": "Personalized opening paragraph.", "bullet_points": ["Bulleted talking point 1 based on SharePoint KB."]}}"""
        task = Task(description=prompt, expected_output="A single, valid JSON object with a personalized sales pitch.", agent=sales_copywriter_agent)
        result = Crew(agents=[sales_copywriter_agent], tasks=[task]).kickoff().raw
        try:
            json_start_index = result.find('{'); json_end_index = result.rfind('}') + 1
            if json_start_index != -1 and json_end_index != 0:
                data = json.loads(result[json_start_index:json_end_index])
                answer_data = {"title": f"Sales pitch", "content_html": format_sales_pitch_content(data)}
            else: raise ValueError("No JSON object found")
        except Exception as e:
            answer_data = {"title": "Error", "content_html": f"<p>Error preparing the dynamic sales pitch: {e}</p>"}
    else:
        answer_data = {"title": "Response", "content_html": "<p>I'm not sure how to answer that yet.</p>"}
    return create_response_card(answer_data.get("title", " "), answer_data.get("content_html", ""))

def get_sharepoint_answer(question: str):
    logging.info("Getting SharePoint answer...")
    prompt = f"""You are a SharePoint Knowledge Analyst for Intelliswift. Your task is to review our internal SharePoint Knowledge Base and create a consolidated summary of relevant insights. **Prospect Profile:** --- {question} --- **Intelliswift's SharePoint Knowledge Base (Summary):** --- {sharepoint_kb_context} --- **Instructions:** 1. Review the SharePoint KB and find 2-4 key focus areas (like Digital Integration, DevOps, etc.). 2. For each focus area, write a descriptive bullet point. 3. Return a SINGLE, VALID JSON object. Your response must be ONLY the JSON. **Required JSON Schema:** {{"intro_sentence": "A brief introductory sentence.", "summary_points": [{{"title": "Name of the Focus Area", "description": "A detailed sentence summarizing the alignment."}}]}}"""
    task = Task(description=prompt, expected_output="A JSON object with an intro_sentence and a list of summary_points.", agent=sharepoint_kb_agent)
    result = Crew(agents=[sharepoint_kb_agent], tasks=[task]).kickoff().raw
    try:
        json_start_index = result.find('{'); json_end_index = result.rfind('}') + 1
        if json_start_index != -1 and json_end_index != 0:
            data = json.loads(result[json_start_index:json_end_index])
            dynamic_content = format_sharepoint_summary_content(data)
            static_footer = """<div class='mt-4 pt-3 border-t border-gray-200'><p class='text-sm text-gray-700'>As per the customer interaction, I’ve retrieved the relevant SharePoint PPTs for:</p><ul class='list-disc list-inside mt-2 ml-4'><li class='text-sm font-semibold'><strong>APIGEE</strong></li><li class='text-sm font-semibold'><strong>iMax</strong></li><li class='text-sm font-semibold'><strong>Apigee Hybrid</strong></li></ul></div>"""
            return {"title": "Sharepoint Summary", "content_html": dynamic_content + static_footer}
        raise ValueError("No JSON object found")
    except Exception as e:
        return {"title": "Error", "content_html": f"<p>Error creating SharePoint summary: {e}</p>"}

# <<< --- UPDATED SALESFORCE FUNCTION --- >>>
def get_salesforce_answer(salesforce_query: str):
    logging.info(f"Getting Salesforce answer for: '{salesforce_query}'")
    
    # New prompt to ask the underlying tool for structured JSON
    prompt = f"""
    Find all Salesforce data for the organization named '{salesforce_query}'.
    Return a SINGLE, VALID JSON object with the following schema.
    Your entire response must be ONLY the JSON object.

    **Required JSON Schema:**
    {{
      "organization_name": "The official name of the organization from Salesforce.",
      "intro_summary": "A one-sentence summary of our engagement status with this organization.",
      "stakeholders": [
        {{
          "name": "Full Name of contact",
          "email": "email@address.com",
          "phone": "Phone number"
        }}
      ],
      "website": "The company website URL.",
      "industry": "The industry of the company.",
      "account_id": "The Salesforce Account ID."
    }}
    """
    # We assume fetch_salesforce_data can take this prompt and return a JSON string
    result = fetch_salesforce_data(prompt)
    
    try:
        json_start_index = result.find('{'); json_end_index = result.rfind('}') + 1
        if json_start_index != -1 and json_end_index != 0:
            data = json.loads(result[json_start_index:json_end_index])
            # Use the new formatter to build the card
            return create_response_card(f"Salesforce Summary: {data.get('organization_name', '')}", format_salesforce_content(data))
        raise ValueError("No JSON object found in Salesforce tool response.")
    except Exception as e:
        logging.error(f"Error parsing Salesforce JSON: {e}. Raw response: {result}")
        return create_response_card("Salesforce Insights", f"<p>Could not retrieve structured data from Salesforce. Raw output: {result}</p>")


# --- Flask Web App ---
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

CONVERSATION_FLOW = [
    {"key": "summary", "question": "I can help you by summarizing this prospect’s profile and suggesting relevant insights. Would you like me to start with a quick summary?"},
    {"key": "opportunity", "question": "I can help you find potential  intelliswift offering  to engage this prospect effectively. Want me to explore those"},
    {"key": "final_summary", "question": "Would you like me to prepare a tailored sales pitch for you to use with this prospect?"},
    {"key": "sharepoint_summary", "question": "I can help you gather more insights about the prospect. Would you like to proceed?"},
    {"key": "salesforce_inquiry", "question": "I can help you identify key stakeholders at Fiserv and retrieve details from our past interactions. Would you like to proceed?"},
    # {"key": "upcoming_features", "question": "Would you like to see the upcoming features planned for this tool?"}
]

@app.route("/", methods=["GET", "POST"])
def home():
    if 'messages' not in session: session['messages'] = [{"role": "bot", "content": "Hello! I am SAGE, I can help you prepare for your meeting with your customer/propsect. Please start with providing name of the prospect and organization details if you are aware of the same."}]
    if request.method == "POST":
        action = request.form.get("action")
        if action == "select_profile": handle_profile_selection()
        else:
            q = request.form.get("q", "").strip()
            if not q: return redirect(url_for('home'))
            session['messages'].append({"role": "user", "content": q})
            if session.get('awaiting_salesforce_id'): handle_salesforce_id_response(q)
            elif session.get('awaiting_yes_no'): handle_guided_question_response(q)
            else: handle_new_search(q)
    session.modified = True
    return render_template_string(HTML, messages=session.get('messages', []))

# --- Handler Functions ---
def handle_new_search(q: str):
    logging.info(f"Starting new search for: '{q}'")
    session.clear()
    session['messages'] = [{"role": "user", "content": q}]
    session['is_static_profile'] = False
    try:
        result = linkedin_contact_lookup(q)
        all_hits = [parse_hit(h) for h in result.get("hits", []) if h]
        if len(all_hits) > 1:
            session['pending_profiles'] = all_hits[:3]
            session['messages'].append({"role": "bot", "content": create_profile_selection_message(session['pending_profiles'])})
            return
        elif len(all_hits) == 1:
            handle_single_profile(all_hits[0])
        else:
            session['messages'].append({"role": "bot", "content": "Sorry, I couldn't find any relevant profiles for that query."})
    except Exception as e:
        logging.error(f"Error during new search: {e}", exc_info=True)
        session['messages'].append({"role": "bot", "content": f"An unexpected error occurred: {e}"})

def handle_profile_selection():
    idx = int(request.form.get("profile_index"));
    if 'pending_profiles' in session and idx < len(session['pending_profiles']):
        selected_profile = session['pending_profiles'][idx]
        handle_single_profile(selected_profile)
        session.pop('pending_profiles', None)
    else:
        session['messages'].append({"role": "bot", "content": "Something went wrong. Please try again."})

def handle_guided_question_response(user_input: str):
    normalized_input = user_input.lower().strip()
    if normalized_input == 'exit':
        logging.info("User typed 'exit'. Ending guided conversation.")
        session['messages'].append({"role": "bot", "content": "Okay, this conversation has ended. Please start a new search."})
        session.pop('awaiting_yes_no', None); session.pop('question_step', None); session.pop('last_context', None)
        return
    if normalized_input not in ['yes', 'y', 'no', 'n']:
        logging.info(f"Input '{user_input}' not 'yes'/'no' or 'exit', treating as new search.")
        handle_new_search(user_input)
        return
    step = session.get('question_step', 0)
    context = session.get('last_context')
    logging.info(f"Handling guided response for step {step}. User input: '{user_input}'.")
    if normalized_input in ['yes', 'y']:
        key = CONVERSATION_FLOW[step]['key']
        answer = ""
        logging.info(f"Executing DYNAMIC action for key: '{key}'")

        if key in ['summary', 'final_summary', 'opportunity']:
            answer = get_focused_answer(context, key)
        elif key == "sharepoint_summary":
            answer_data = get_sharepoint_answer(context)
            answer = create_response_card(answer_data.get("title"), answer_data.get("content_html"))
        
        # <<< --- UPDATED SALESFORCE QUESTION TEXT --- >>>
        elif key == "salesforce_inquiry":
            session['awaiting_salesforce_id'] = True; session.pop('awaiting_yes_no', None)
            answer = "I am retrieving the relevant details from Salesforce for this customer. Please share the Salesforce ID, Lead ID, or Organization Name to proceed ?"
            session['messages'].append({"role": "bot", "content": answer})
            return
        
        elif key == "upcoming_features":
            answer_data = UPCOMING_FEATURES_DATA
            answer = create_response_card(answer_data.get("title"), answer_data.get("content_html"))
        else:
            answer = create_response_card("Error", "<p>I'm not sure how to handle that step.</p>")
        session['messages'].append({"role": "bot", "content": answer})
    else:
        session['messages'].append({"role": "bot", "content": "Okay, skipping that."})
    
    session['question_step'] = step + 1
    if session['question_step'] < len(CONVERSATION_FLOW):
        next_question = CONVERSATION_FLOW[session['question_step']]['question']; session['messages'].append({"role": "bot", "content": next_question})
    else:
        session['messages'].append({"role": "bot", "content": "That's all the insights I have. Feel free to start a new search."}); session.pop('awaiting_yes_no', None)

def handle_single_profile(profile_data):
    logging.info(f"Starting to handle single profile: {profile_data.get('designation')}")
    raw_text_for_parsing = f"Title: {profile_data.get('designation', '')}\nCompany: {profile_data.get('company', '')}\nSummary: {profile_data.get('skillset', '')}"
    prompt = f"""Analyze the following text from a professional profile. Your goal is to extract the person's skills, a summary of their work experience, and their current location. **Instructions:** 1. Read the text carefully. 2. From the text, create a list of professional skills. If specific skills are not listed, **infer potential skills based on the person's job title and industry.** 3. Summarize the person's work experience into a single, concise sentence. 4. Extract the most specific location mentioned. 5. Return a SINGLE, VALID JSON object with the keys "skills", "experience", and "location". Your entire response must be ONLY the JSON object. **Text to Analyze:** ```{raw_text_for_parsing}```"""
    task = Task(description=prompt, expected_output="A JSON object with keys 'skills', 'experience', and 'location'.", agent=profile_parser_agent)
    result = Crew(agents=[profile_parser_agent], tasks=[task]).kickoff().raw
    enriched_data = {}
    try:
        json_start_index = result.find('{'); json_end_index = result.rfind('}') + 1
        if json_start_index != -1 and json_end_index != 0:
            enriched_data = json.loads(result[json_start_index:json_end_index])
    except Exception as e:
        logging.error(f"Could not parse enriched profile data: {e}")
    profile_data['skills_list'] = enriched_data.get('skills', [])
    profile_data['experience_summary'] = enriched_data.get('experience', 'N/A')
    profile_data['location'] = enriched_data.get('location', 'N/A')
    session['last_context'] = json.dumps(profile_data)
    profile_html = format_initial_profile_display(profile_data)
    session['messages'].append({"role": "bot", "content": profile_html})
    session['question_step'] = 0
    session['awaiting_yes_no'] = True
    first_question = CONVERSATION_FLOW[0]['question']
    session['messages'].append({"role": "bot", "content": first_question})

def handle_salesforce_id_response(salesforce_query: str):
    session.pop('awaiting_salesforce_id', None)
    answer = get_salesforce_answer(salesforce_query) # This now returns a fully formatted card
    session['messages'].append({"role": "bot", "content": answer})
    step = session.get('question_step', 0)
    next_step = step + 1
    session['question_step'] = next_step
    if next_step < len(CONVERSATION_FLOW):
        session['messages'].append({"role": "bot", "content": CONVERSATION_FLOW[next_step]['question']}); session['awaiting_yes_no'] = True
    else:
        session['messages'].append({"role": "bot", "content": "That's all for now."})

def parse_hit(h):
    designation = h.get("designation", ""); snippet = h.get("snippet", "")
    company = ""
    company_match_keyword = re.search(r"(?:at |Experience:|\|)\s*([^·,]+)", snippet + " " + designation, re.I)
    if company_match_keyword:
        company = company_match_keyword.group(1).strip()
    if not company and '-' in designation:
        parts = designation.split('-', 1)
        if len(parts) > 1:
            company = parts[1].strip()
    h["company"] = company
    try:
        h["skillset"] = h.get('pagemap', {}).get('metatags', [{}])[0].get('og:description', snippet)
    except (IndexError, KeyError):
        h["skillset"] = snippet
    return h

def create_profile_selection_message(profiles):
    msg = "<p>I found multiple matching profiles. Please select the correct one:</p><div class='flex flex-col mt-2'>"
    for i, p in enumerate(profiles):
        company_display = f"<span class='block text-xs text-gray-500'>{p.get('company')}</span>" if p.get('company') else ""
        link = f'<a href="{p.get("url")}" target="_blank" class="text-blue-500 text-xs hover:underline flex-shrink-0 ml-4">View Profile</a>' if p.get("url") else ""
        msg += f"""<form method="POST" action="/" class="mb-2"><input type="hidden" name="action" value="select_profile"><input type="hidden" name="profile_index" value="{i}"><button type="submit" class="w-full text-left p-3 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-800 transition-all shadow-sm"><div class="flex justify-between items-center"><div class="flex-grow overflow-hidden mr-2"><strong>{p.get('designation', 'Unknown Profile')}</strong>{company_display}</div>{link}</div></button></form>"""
    return msg + "</div>"

def format_initial_profile_display(profile):
    title = f"Profile Found: {profile.get('designation', '').split(' - ')[0].strip()}"
    skills_list = profile.get('skills_list', [])
    skills_str = ", ".join(skills_list) if skills_list else "Not specified"
    content = f"""<ul class="text-sm text-gray-700 space-y-2"><li><strong>Full Title:</strong> {profile.get('designation', 'N/A')}</li><li><strong>Company:</strong> {profile.get('company', 'N/A')}</li><li><strong>Location:</strong> {profile.get('location', 'N/A')}</li><li><strong>Profile Link:</strong> <a href="{profile.get('url', '#')}" target="_blank" class="text-blue-600 hover:underline">{profile.get('url', 'N/A')}</a></li><li><strong>Experience Summary:</strong> {profile.get('experience_summary', 'N/A')}</li><li><strong>Skills:</strong> {skills_str}</li></ul>"""
    return create_response_card(title, content)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5072, debug=True)