import os, json
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
from linkedin_search_mcp import linkedin_contact_lookup
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import chromadb

load_dotenv()
llm = LLM(model="gemini/gemini-1.5-flash", api_key=os.getenv("GEMINI_API_KEY"))

chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection("linkedin_profiles")
tool_query_result = {}

class LinkedInQueryInput(BaseModel):
    person_query: str = Field(..., description="Name of person or company to look up")

class LinkedInTool(BaseTool):
    name: str = "LinkedInContactLookup"
    description: str = "Search LinkedIn profiles and public info"
    args_schema: Type[BaseModel] = LinkedInQueryInput

    def _run(self, person_query: str) -> str:
        global tool_query_result

        existing = collection.query(
            query_texts=[person_query],
            n_results=1
        )
        if existing['documents'] and existing['documents'][0]:
            print("[INFO] Found in vector DB")
            result = json.loads(existing['documents'][0][0])
        else:
            print(f"[TOOL] Searching online for: {person_query}")
            result = linkedin_contact_lookup(person_query)
            collection.add(
                documents=[json.dumps(result)],
                ids=[person_query]
            )

        tool_query_result = result
        return json.dumps(result)

lookup_tool = LinkedInTool()

identifier = Agent(
    role="Entity Identifier",
    goal="Classify the input as person or company",
    backstory="Expert at analyzing text queries to identify entity type.",
    verbose=True,
    llm=llm
)

info_extractor = Agent(
    role="Info Extractor",
    goal="Extract person/company info and public profile details",
    backstory="Specialist in profiling from scraped data",
    tools=[lookup_tool],
    verbose=True,
    llm=llm
)

recommender = Agent(
    role="Business Recommender",
    goal="Give smart B2B suggestions",
    backstory="Knows how to align company goals with partnership opportunities",
    verbose=True,
    llm=llm
)

def build_tasks(query: str, input_company: str):
    task1 = Task(
        description=f"Is '{query}' a person or company?",
        expected_output="Return only 'person' or 'company'",
        agent=identifier
    )

    task2 = Task(
        description=f"""
Given the query '{query}', extract:
1. Background summary.
2. Role and company (if person).
3. Services/products (if company).
4. Public URLs (LinkedIn, website).
5. Public contact info (phones).

Use: {{ "person_query": "{query}" }}

If tool returns 'hits', pick the first one and convert to:
- role
- company
- location
- public_url
- contact_info
""",
        expected_output="JSON with background, role, company, location, public_url, contact_info",
        agent=info_extractor,
        context=[task1]
    )

    task3 = Task(
        description=f"""
Given the info above, suggest 3 business recommendations from '{input_company}' to collaborate or pitch services.
""",
        expected_output="3-5 specific business recommendations.",
        agent=recommender,
        context=[task2]
    )

    return [task1, task2, task3]

def run_pipeline(query: str, input_company: str):
    crew = Crew(
        agents=[identifier, info_extractor, recommender],
        tasks=build_tasks(query, input_company),
        verbose=True,
    )
    return crew.kickoff()

def get_last_hits():
    if "hits" in tool_query_result:
        return tool_query_result["hits"]
    elif "url" in tool_query_result:
        return [tool_query_result]
    else:
        return []
