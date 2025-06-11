# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Search Agent configuration for ADK application.

This module defines the root agent that uses Google Search tools to answer questions.
"""

from google.adk.agents import Agent
from .chromadb_search import find_document_tool, show_document_tool

root_agent = Agent(
   # A unique name for the agent.
   name="apartment_document_agent",
   # The Large Language Model (LLM) that agent will use.
   model="gemini-2.0-flash-exp", # if this model does not work, try below
   #model="gemini-2.0-flash-live-001",
   # A short description of the agent's purpose.
   description="Agent for answering questions about apartment manuals and building info.",
   # Instructions to set the agent's behavior.
   instruction="Answer questions about apartment living using the find_document_tool to find "
              "relevant information from apartment manuals covering appliances, services, "
              "building rules, and facilities. ALWAYS respond in the same language as the user's question. "
              "When you receive results from find_document_tool, ALWAYS immediately use the show_document_tool "
              "to display the documents to the user. Extract the filename and page number from each result "
              "(format: 'filename (page X)') and use the show_document_tool with 'filename:page_number' format "
              "(e.g., ['001.pdf:5', '023.pdf:12']). Do not ask for clarification when documents are found.",
   # Add tools for apartment manual queries and document display.
   tools=[find_document_tool, show_document_tool],
)
