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
from .parse_doc import parse_doc_tool

root_agent = Agent(
   # A unique name for the agent.
   name="apartment_document_agent",
   # The Large Language Model (LLM) that agent will use.
   model="gemini-2.0-flash-exp", # if this model does not work, try below
   #model="gemini-2.0-flash-live-001",
   # A short description of the agent's purpose.
   description="Agent for answering questions about product and service manuals and building info.",
   # Instructions to set the agent's behavior.
   instruction=(
       "Answer questions about apartment living using the following workflow: "
       "1. Use find_document_tool to find relevant documents from product and service "
       "manuals covering appliances, services, building rules, and facilities. "
       "2. After finding documents, inform the user how many documents were found and "
       "notify them to wait a moment while reading the first manual. Use show_document_tool "
       "to display the first page of the most relevant document, then use parse_doc_tool "
       "on that document to get detailed analysis. "
       "3. Evaluate if the result from parse_doc_tool is relevant to the user's query: "
       "   - If the result contains relevant information that answers the user's question, "
       "provide answer to the user directly. Do NOT call show_document_tool again since "
       "the document is already displayed. "
       "   - If the result seems unrelated or does not contain useful information for the "
       "query, use show_document_tool to display the next document from the search results, "
       "then try parse_doc_tool with that document (second result, then third if needed). "
       "   - Only try up to 3 documents maximum to avoid excessive processing. "
       "4. Provide the best answer based on the most relevant parse_doc_tool result found. "
       "Keep your answer concise and under 100 words. "
       "ALWAYS respond in the same language as the user's question. "
       "Do not ask for clarification when documents are found. Follow this sequence: "
       "find_document_tool → show_document_tool → parse_doc_tool → (repeat "
       "show_document_tool + parse_doc_tool for other documents if needed) → provide answer."
   ),
   # Add tools for product and service manual queries, document display, and document parsing.
   tools=[find_document_tool, show_document_tool, parse_doc_tool],
)
