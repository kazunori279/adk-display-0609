# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a multi-component Google ADK (Agent Development Kit) streaming application with:

- **Backend** (`backend/app/`): FastAPI server using Google ADK with real-time agent communication via SSE
- **Frontend** (`frontend/`): Vue.js 3 + Vite application with Tailwind CSS
- **Index Building** (`index-building/`): PDF processing and chunking system for document ingestion

The system enables real-time streaming communication between clients and Google ADK agents, supporting both text and audio modalities.

## Development Commands

### Frontend (Vue.js)

```bash
cd frontend
npm install
npm run dev          # Start development server on port 3000
npm run build        # Build for production
npm run preview      # Preview production build
npm run lint         # Run ESLint with auto-fix
```

### Backend (FastAPI + Google ADK)

```bash
cd backend/app
# Requires GEMINI_API_KEY environment variable
python main.py       # Start FastAPI server
./run.sh            # Alternative: Use run script for server management
```

### Index Building (Python)

```bash
cd index-building
pip install -r requirements.txt
pytest              # Run all tests
pytest -m "not integration"  # Skip integration tests
python process_all_pdfs.py   # Process all 70 PDF documents (multi-threaded)
python demo_pdf_to_csv.py    # Process single PDF for testing
```

### Code Quality and Testing

Always run these commands when making changes:

- **pylint**: Use pylint for Python code quality checks
- **markdownlint**: Use markdownlint for Markdown formatting
- **Tests**: Run relevant tests before committing changes

#### Backend Testing

```bash
cd backend
pytest test/                    # Run all backend tests
pytest test/test_show_document_integration.py  # Run specific test file
python test/test_server_full.py # Run comprehensive server test (20 queries)
```

#### Comprehensive Server Test

The `test_server_full.py` script provides end-to-end testing of the entire system:

- **Duration**: ~5-10 minutes (processes 20 test queries)
- **Coverage**: Tests Wi-Fi setup, appliances, building services, safety equipment
- **Languages**: Japanese queries covering real-world use cases
- **Verification**: Checks ChromaDB initialization, agent responses, show_document functionality
- **Output**: Leaves test server running on localhost:8000 for manual testing

**Test Queries Include**:

- Wi-Fi and internet connectivity
- Air conditioning and heating systems  
- Kitchen appliances (microwave, dishwasher, coffee maker, rice cooker)
- Laundry and cleaning equipment
- Building services and parking rules
- Safety equipment and evacuation procedures
- Troubleshooting scenarios

## Current Assets and Structure

### Backend Assets (`backend/`)

- **Core Server**: `app/main.py` - FastAPI server with SSE streaming
- **Agent**: `app/google_search_agent/agent.py` - Gemini 2.0 Flash agent with Google Search
- **Static Assets**: `app/static/` - Simple ADK streaming test interface with audio support
- **Test Suite**: `test/` - Comprehensive integration tests (4 test files)
- **Scripts**: `run.sh` - Server management script

### Frontend Assets (`frontend/`)

- **Vue Components**:
  - `src/App.vue` - Main application layout
  - `src/components/AppHeader.vue` - Application header
  - `src/components/ChatSidebar.vue` - Chat interface with connection status
  - `src/components/MainContent.vue` - Content grid with hover effects
- **Utilities**:
  - `src/composables/useADKStreaming.js` - Vue composable for ADK streaming
  - `src/utils/audioPlayer.js` - Audio playback utilities
  - `src/utils/audioRecorder.js` - Audio recording utilities
  - `src/utils/base64Utils.js` - Base64 encoding/decoding
- **Configuration**: Vite + Tailwind CSS with forms and container query plugins

### Document Resources (`index-building/resources/`)

**70 PDF Files** (numbered 001.pdf - 070.pdf) covering:

- **Home Appliances**: Air conditioners, humidifiers, vacuum cleaners, washing machines, rice cookers
- **Kitchen Equipment**: Coffee machines, dishwashers, microwave ovens, steam ovens
- **Audio/Video Equipment**: Bluetooth transmitters, amplifiers, Blu-ray recorders
- **Computer Equipment**: NAS systems, keyboards, mini PCs, tablets
- **Safety Equipment**: Evacuation devices, escape ladders, rescue equipment
- **Building Infrastructure**: Gas equipment, electrical systems, network equipment
- **Building Documentation**: Move-in rules, parking, waste separation guides
- **Services**: Shuttle bus, rental bicycles, unmanned convenience store

### Index Building Tools (`index-building/`)

- **Core Processing**: `process_all_pdfs.py` - Multi-threaded PDF processor (10 threads)
- **Utilities**: `generate_chunks.py`, `csv_utils.py`, `gemini_utils.py`
- **Data Models**: `models.py` - Pydantic models for document queries
- **Test Suite**: 8 test files including integration tests for embeddings
- **Data**: `data/file_description.csv` - Large dataset with 34,505+ entries

## Key Technical Details

### ADK Integration

- Uses Google ADK InMemoryRunner with LiveRequestQueue for real-time agent communication
- Agent configured with `gemini-2.0-flash-exp` model and Google Search tool
- Supports both TEXT and AUDIO response modalities
- SSE endpoint at `/events/{user_id}` for agent-to-client streaming
- HTTP POST endpoint at `/send/{user_id}` for client-to-agent messages
- Audio streaming support with PCM format and Base64 encoding

### Frontend-Backend Communication

- Vue 3 with Composition API and real-time chat interface
- Server-Sent Events (SSE) for streaming communication
- Audio recording/playback with worklet processors
- Connection status indicators and responsive grid layout
- CORS enabled for cross-origin requests

### Document Processing

- Multi-threaded PDF processing system (10 concurrent threads)
- Gemini API integration with fallback models
- Structured data extraction using Pydantic models
- CSV export functionality with comprehensive test coverage
- Embedding generation pipeline for 70+ apartment manual PDFs
- Integration with Google Cloud AI Platform for embeddings
