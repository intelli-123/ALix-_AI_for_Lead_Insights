# salesforce_mcp.py
import os
from crewai import Agent, Task, Crew, LLM
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- Reusable Helper Function for Setup ---
def _check_env_vars_and_get_llm():
    """Checks for required environment variables and initializes the LLM."""
    required_env_vars = [
        "SALESFORCE_USERNAME", "SALESFORCE_PASSWORD", "SALESFORCE_TOKEN",
        "SALESFORCE_INSTANCE_URL", "GEMINI_API_KEY"
    ]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        error_msg = f"Error: The following environment variables are not set: {', '.join(missing_vars)}"
        print(error_msg)
        raise ValueError(error_msg)
    
    try:
        llm = LLM(model="gemini/gemini-1.5-flash", api_key=os.getenv("GEMINI_API_KEY"))
        return llm
    except Exception as e:
        print(f"An unexpected error occurred during LLM initialization: {e}")
        raise

# --- Function for the Flask App (Non-Interactive) ---
def fetch_salesforce_data(prompt: str) -> str:
    """
    Sets up and runs a NON-INTERACTIVE CrewAI crew to fetch Salesforce data.
    """
    print(f"🚀 [Web App] Kicking off Salesforce crew for prompt: {prompt}")
    try:
        llm = _check_env_vars_and_get_llm()
    except (ValueError, Exception) as e:
        return f"Failed to initialize Salesforce connection: {e}"

    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@tsmztech/mcp-server-salesforce"],
        env={
            "SALESFORCE_CONNECTION_TYPE": "User_Password",
            "SALESFORCE_USERNAME": os.getenv("SALESFORCE_USERNAME"),
            "SALESFORCE_PASSWORD": os.getenv("SALESFORCE_PASSWORD"),
            "SALESFORCE_TOKEN": os.getenv("SALESFORCE_TOKEN"),
            "SALESFORCE_INSTANCE_URL": os.getenv("SALESFORCE_INSTANCE_URL"),
        },
    )

    print("Attempting to connect to Salesforce MCP server for web request...")
    try:
        with MCPServerAdapter(server_params) as mcp_tools:
            print("Connection successful! Salesforce tools are now available.")
            
            salesforce_agent = Agent(
                role="Senior Salesforce Administrator",
                goal="Your primary goal is to accurately answer the user's request by finding the right information in Salesforce using the available tools.",
                backstory="You are a meticulous AI-powered Salesforce administrator...",
                tools=mcp_tools,
                llm=llm,
                verbose=True,
                allow_delegation=False,
            )

            salesforce_task = Task(
                description=prompt,
                expected_output="A clear, concise, and accurate summary of the findings from Salesforce.",
                agent=salesforce_agent,
                human_input=False,
            )

            salesforce_crew = Crew(
                agents=[salesforce_agent],
                tasks=[salesforce_task],
                verbose=True
            )

            crew_result = salesforce_crew.kickoff()
            print("✅ [Web App] Crew finished successfully.")
            
            # --- FIX: Make getting the result backward-compatible ---
            try:
                # In newer versions, the string is in the .raw attribute
                return crew_result.raw
            except AttributeError:
                # In older versions, it might just be the string itself
                return str(crew_result)
            # --- END FIX ---

    except Exception as e:
        error_message = f"An error occurred during Salesforce crew execution: {e}"
        print(f"❌ {error_message}")
        return error_message

# --- Local Flask App for Testing ---
load_dotenv()
app = Flask(__name__)

@app.route("/test_salesforce", methods=["GET"])
def test_salesforce_route():
    org_name = request.args.get("org")
    if not org_name:
        return jsonify({
            "error": "Please provide an organization name using the 'org' query parameter.",
            "example": "/test_salesforce?org=Fiserv"
        }), 400

    # --- FIX: Using a better, more reliable prompt ---
    prompt = (
        f"The user is asking for information on the organization '{org_name}'. "
        f"Search Salesforce for all relevant records (like Account, Contacts, and open Opportunities) "
        f"related to this organization and provide a comprehensive summary of your findings."
    )
    
    result = fetch_salesforce_data(prompt)
    
    return jsonify({
        "organization_queried": org_name,
        "llm_prompt": prompt,
        "final_result": result
    })

if __name__ == "__main__":
    print("--- Starting Salesforce MCP Test Server ---")
    print("Access at http://127.0.0.1:5001/test_salesforce?org=YOUR_ORGANIZATION_NAME")
    app.run(host="0.0.0.0", port=5001, debug=True)


# #salesforce_mcp.py
# import os
# from crewai import Agent, Task, Crew, LLM
# from crewai_tools import MCPServerAdapter
# from mcp import StdioServerParameters

# def run_salesforce_crew(prompt: str):
#     """
#     Sets up and runs a CrewAI crew to interact with Salesforce via an MCP server.

#     Args:
#         prompt (str): The user's request to be processed by the Salesforce agent.
#     """
#     # --- Environment Variable Check ---
#     # Ensure all necessary Salesforce and Google API credentials are set.
#     required_env_vars = [
#         "SALESFORCE_USERNAME",
#         "SALESFORCE_PASSWORD",
#         "SALESFORCE_TOKEN",
#         "SALESFORCE_INSTANCE_URL",
#         "GEMINI_API_KEY"
#     ]
    
#     missing_vars = [var for var in required_env_vars if not os.getenv(var)]
#     if missing_vars:
#         print("\n--- Missing Environment Variables ---")
#         print(f"Error: The following environment variables are not set: {', '.join(missing_vars)}")
#         print("Please set them before running the script.")
#         print("Example for macOS/Linux: export GEMINI_API_KEY='your_api_key'")
#         print("-------------------------------------\n")
#         return

#     # --- LLM Configuration ---
#     # Using CrewAI's built-in LLM class as requested.
#     # Note: The model string format 'gemini/gemini-2.0-flash' must be supported by the CrewAI LLM wrapper.
#     try:
#         llm = LLM(model="gemini/gemini-1.5-flash", api_key=os.getenv("GEMINI_API_KEY"))
#         print("LLM configured.")
#     except Exception as e:
#         print(f"\nAn unexpected error occurred during LLM initialization: {e}")
#         return

#     # --- MCP Server Configuration ---
#     server_params = StdioServerParameters(
#         command="npx",
#         args=["-y", "@tsmztech/mcp-server-salesforce"],
#         env={
#             "SALESFORCE_CONNECTION_TYPE": "User_Password",
#             "SALESFORCE_USERNAME": os.getenv("SALESFORCE_USERNAME"),
#             "SALESFORCE_PASSWORD": os.getenv("SALESFORCE_PASSWORD"),
#             "SALESFORCE_TOKEN": os.getenv("SALESFORCE_TOKEN"),
#             "SALESFORCE_INSTANCE_URL": os.getenv("SALESFORCE_INSTANCE_URL"),
#         },
#     )

#     print("\nAttempting to connect to Salesforce MCP server...")
#     print("This may take a moment as it downloads and starts the server via npx...")

#     try:
#         with MCPServerAdapter(server_params) as mcp_tools:
#             print("\nConnection successful! Salesforce tools are now available.")
            
#             # --- Agent Definition ---
#             salesforce_agent = Agent(
#                 role="Senior Salesforce Administrator",
#                 goal=f"""
#                     Your primary goal is to translate the user's request into a precise and correct tool call.
#                     Carefully analyze the user's request: '{prompt}'.
#                     Follow these steps:
#                     1.  Identify the user's intent (e.g., query data, create a record, describe an object).
#                     2.  Select the single most appropriate tool from your toolkit. For queries, this will almost always be 'salesforce_query_records'.
#                     3.  If querying, construct the correct SOQL query string needed to fulfill the request. For example, to find opportunity names for the 'honda' account, you should construct a query like: "SELECT Name FROM Opportunity WHERE Account.Name = 'honda'".
#                     4.  Execute the tool with the correctly formatted arguments.
#                     """,
#                 backstory=(
#                     "You are a meticulous AI-powered Salesforce administrator. Your strength is understanding natural language requests and translating them into precise, executable actions within Salesforce using a defined set of tools. You are thorough and always double-check your logic before acting."
#                 ),
#                 tools=mcp_tools,
#                 llm=llm,
#                 verbose=True,
#                 allow_delegation=False,
#             )

#             # --- Task Definition ---
#             # Added human_input=True to allow for verification of the agent's plan before execution.
#             salesforce_task = Task(
#                 description=prompt,
#                 expected_output=(
#                     "A clear, concise, and accurate answer to the user's request. "
#                     "If the task was to query data, the output should be the data itself, presented in a readable format. "
#                     "For example: 'Here are the opportunity names for the account honda: [OppName1, OppName2]'."
#                 ),
#                 agent=salesforce_agent,
#                 human_input=True, # This will pause the crew and ask for your confirmation before running the tool.
#             )

#             # --- Crew Execution ---
#             salesforce_crew = Crew(
#                 agents=[salesforce_agent],
#                 tasks=[salesforce_task],
#                 verbose=True
#             )

#             print("\n--- Kicking off the Crew ---")
#             print("--> NOTE: The agent will now pause and ask for your permission before executing any Salesforce action.")
#             result = salesforce_crew.kickoff()

#             print("\n--- Crew Finished ---")
#             print("Final Result:")
#             print(result)

#     except Exception as e:
#         print(f"\nAn error occurred during Crew or MCP execution: {e}")
#         print("Please check your Salesforce credentials and ensure npx is installed.")

# def main():
#     """
#     Main function to run the interactive console loop.
#     """
#     print("--- Interactive Salesforce AI Agent ---")
#     print("Enter your request for Salesforce. Type 'exit' to quit.")
    
#     while True:
#         prompt = input("\nYour prompt: ")
#         if prompt.lower() == 'exit':
#             print("Exiting...")
#             break
#         if not prompt:
#             continue
        
#         run_salesforce_crew(prompt)

# if __name__ == "__main__":
#     main()
