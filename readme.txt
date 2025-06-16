LSHA - Ltts Sales Helper Agent
Version: 1.0.0

Overview
LSHA (Ltts Sales Helper Agent) is an AI-powered, conversational web application designed to assist sales professionals at Intelliswift. It leverages AI agents to find, analyze, and provide strategic insights on LinkedIn profiles for both individuals and companies.

The agent initiates an interactive, guided conversation to help users understand a prospect's profile, identify relevant technology offerings, find potential opportunity areas, and generate a consolidated summary to prepare for sales meetings.

Core Features
Intelligent Entity Search: Automatically detects whether a search query is for a person, a company, or a person at a specific company.

Interactive Conversational Flow: Guides the user through a step-by-step analysis of a prospect's profile with a series of questions.

Deep Profile Analysis: Goes beyond initial search snippets to analyze the full context of a LinkedIn profile for richer insights.

Context-Aware Recommendations: Connects the prospect's professional background with Intelliswift's service offerings from a dynamic knowledge base.

Multi-Agent System: Uses a crew of specialized AI agents for different tasks like classification, summarization, and analysis.

Dockerized Application: Packaged into a lightweight and efficient Docker container for easy deployment and consistent operation.

Project Setup
Follow these steps to set up and run the LSHA application on your local machine.

1. Prerequisites
Docker installed and running.

A code editor like VS Code.

A terminal or command prompt.

2. Project Structure
Ensure your project directory is set up with the following file structure:

/LSHA-Project/
├── .dockerignore
├── .env
├── Dockerfile
├── app.py
├── linkedin_search_mcp.py
├── requirements.txt
├── ui_template.py
└── /static/
    └── intelliswift_logo.png

3. Create the .env file
Create a file named .env in the root of your project directory. This file will hold your secret API keys. Do not commit this file to Git.

# .env

# Your Google Gemini API Key
GEMINI_API_KEY="your_google_gemini_api_key_here"

# Your Google Custom Search Engine ID (cx)
# Required for linkedin_search_mcp.py
CX="your_google_custom_search_engine_id"

# Your Google API Key for Custom Search
# Required for linkedin_search_mcp.py
KEY="your_google
