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
       "1. Analyze the user's question to identify the target product or service name. "
       "If the user omitted the product or service name in their query, complement it by "
       "predicting from the conversation context (previous questions, mentioned products, etc.). "
       "Then use find_document_tool with a query that has both product/service name and question "
       "about it. "
       "2. After finding documents, inform the user how many documents were found and "
       "notify them to wait a moment while reading the first manual. Use show_document_tool "
       "with just the filename (e.g., '013.pdf') to display the first page of the most relevant "
       "document, then use parse_doc_tool on that document to get detailed analysis. "
       "3. Evaluate if the result from parse_doc_tool is relevant to the user's query: "
       "   - If the result contains relevant information that answers the user's question, "
       "use show_document_tool with the pdf_file value from parse_doc_tool result. The pdf_file "
       "value is automatically formatted as 'filename:page' (e.g., '013.pdf:9') when a specific "
       "page number is identified, or just 'filename' when no specific page is found. Always use "
       "the exact pdf_file value returned by parse_doc_tool without any modification or parsing. "
       "   - If the result seems unrelated or does not contain useful information for the "
       "query, use show_document_tool with the next document filename from the search results, "
       "then try parse_doc_tool with that document (second result, then third if needed). "
       "   - Try all available documents returned by the search (typically 3 documents). "
       "4. Provide the best answer based on the most relevant parse_doc_tool result found. "
       "Keep your answer concise and under 100 words. "
       "ALWAYS respond in the same language as the user's question. "
       "Do not ask for clarification when documents are found. Follow this sequence: "
       "find_document_tool → show_document_tool (filename only) → parse_doc_tool → (repeat "
       "show_document_tool + parse_doc_tool for other documents if needed) → provide answer."
   ),
   # Add tools for product and service manual queries, document display, and document parsing.
   tools=[find_document_tool, show_document_tool, parse_doc_tool],
)
