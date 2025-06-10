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
from .chromadb_search import document_search_tool

root_agent = Agent(
   # A unique name for the agent.
   name="apartment_document_agent",
   # The Large Language Model (LLM) that agent will use.
   model="gemini-2.0-flash-exp", # if this model does not work, try below
   #model="gemini-2.0-flash-live-001",
   # A short description of the agent's purpose.
   description="Agent for answering questions about apartment manuals and building info.",
   # Instructions to set the agent's behavior.
   instruction="Answer questions about apartment living using the document search tool to find "
              "relevant information from apartment manuals covering appliances, services, "
              "building rules, and facilities.",
   # Add document_search_tool for apartment manual queries.
   tools=[document_search_tool],
)
