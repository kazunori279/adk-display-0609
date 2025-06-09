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
```

### Index Building (Python)

```bash
cd index-building
pip install -r requirements.txt
pytest              # Run all tests
pytest -m "not integration"  # Skip integration tests
python process_all_pdfs.py   # Process PDF documents
```

### Code Quality and Testing

Always run these commands when making changes:

- **pylint**: Use pylint for Python code quality checks
- **markdownlint**: Use markdownlint for Markdown formatting
- **Tests**: Run relevant tests before committing changes

## Key Technical Details

### ADK Integration

- Uses Google ADK InMemoryRunner with LiveRequestQueue for real-time agent communication
- Agent configured with `gemini-2.0-flash-exp` model and Google Search tool
- Supports both TEXT and AUDIO response modalities
- SSE endpoint at `/events/{user_id}` for agent-to-client streaming
- HTTP POST endpoint at `/send/{user_id}` for client-to-agent messages

### Frontend-Backend Communication

- Frontend connects to backend via Server-Sent Events (SSE)
- Audio data transmitted as Base64-encoded PCM
- CORS enabled for cross-origin requests

### Document Processing

- PDF chunking system in `index-building/` for processing apartment manuals and equipment documentation
- Uses pytest with integration test markers
- CSV output format for processed document chunks
