# Backend Server - ADK Streaming Application

This is the FastAPI backend server for the Google ADK (Agent Development Kit) streaming application. It provides real-time communication between clients and Google ADK agents using Server-Sent Events (SSE) and HTTP endpoints.

## 🏗️ Architecture Overview

The backend server consists of:

- **FastAPI Server** (`app/main.py`): Main web server with SSE streaming endpoints
- **ADK Agent** (`app/search_agent/agent.py`): Gemini 2.0 Flash agent with Google Search integration
- **ChromaDB Search** (`app/search_agent/chromadb_search.py`): Document search functionality with vector embeddings
- **Static Assets** (`app/static/`): Simple ADK streaming test interface with audio support

### Key Features

- **Real-time Streaming**: Server-Sent Events (SSE) for agent-to-client communication
- **Audio Support**: PCM audio streaming with Base64 encoding
- **Document Search**: ChromaDB-powered search through 70+ product and service manual PDFs (34,504+ documents)
- **Multi-modal**: Supports both TEXT and AUDIO response modalities
- **Cross-platform**: Works on macOS, Linux, and Windows

## 🚀 Quick Start

### Prerequisites

1. **Python 3.12+** with pip
2. **Google API Key**: Set in `.env` file
3. **Dependencies**: Install from `requirements.txt`

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with your Google API key
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

### Running the Server

```bash
./run.sh
```

The server will be available at: <http://localhost:8000>

## 🧪 Testing

### Running All Tests

```bash
# Run all tests (includes comprehensive server test)
./test.sh

# Run only pytest tests
python -m pytest

# Run specific test file
python -m pytest test/test_agent_chromadb_integration.py
```

### Test Suite Overview

1. **Unit Tests** (`test/test_agent_chromadb_integration.py`):
   - Agent integration with ChromaDB search tool
   - Tool response formatting and content validation
   - Error handling and fallback mechanisms
   - Performance benchmarks

2. **Integration Tests** (`test/test_find_document_unique.py`):
   - Document search functionality
   - Deduplication and relevancy filtering

3. **Server Integration Test** (`test/test_server_full.py`):
   - Comprehensive end-to-end server testing
   - 20 Japanese queries testing product and service manual search
   - Document display functionality verification
   - Server startup and ChromaDB initialization

4. **Show Document Integration** (`test/test_show_document_integration.py`):
   - PDF display functionality
   - Client queue integration

### Test Results

The comprehensive server test typically achieves:

- **90%+ success rate** (18/20 queries successful)
- **Full ChromaDB initialization** with 34,504+ documents
- **Document display commands** triggered correctly

## 📡 API Endpoints

### Core Endpoints

- **GET /**: Serves the main interface (`static/index.html`)
- **GET /events/{user_id}**: SSE endpoint for agent-to-client streaming
- **POST /send/{user_id}**: HTTP endpoint for client-to-agent messages

### Message Format

**Client to Agent** (POST /send/{user_id}):

```json
{
  "mime_type": "text/plain",
  "data": "Your message here"
}
```

**Agent to Client** (SSE stream):

```json
{
  "mime_type": "text/plain",
  "data": "Agent response"
}
```

**Document Display Command**:

```json
{
  "mime_type": "application/json",
  "data": {
    "command": "show_document",
    "filename": "025.pdf",
    "page": 3
  }
}
```

## 🔍 Document Search System

### ChromaDB Integration

The server includes a powerful document search system:

- **34,504+ document chunks** from 70 product and service manual PDFs
- **Vector embeddings** for semantic search
- **Relevancy filtering** with configurable thresholds
- **Deduplication** to avoid showing the same document multiple times

### Document Categories

The system covers comprehensive product and service manual documentation:

- **HOME APPLIANCES**: Air conditioners, humidifiers, vacuum cleaners, washing machines, rice cookers
- **KITCHEN EQUIPMENT**: Coffee machines, dishwashers, microwave ovens, steam ovens
- **AUDIO/VIDEO EQUIPMENT**: Bluetooth transmitters, amplifiers, Blu-ray recorders
- **COMPUTER/NETWORK**: NAS systems, keyboards, mini PCs, tablets, Wi-Fi setup
- **SAFETY/SECURITY**: Fire evacuation devices, escape ladders, rescue equipment, intercoms
- **BUILDING INFRASTRUCTURE**: Gas equipment, electrical systems, network equipment
- **BUILDING SERVICES & RULES**: Move-in procedures, parking regulations, waste separation
- **TRANSPORTATION & AMENITIES**: Shuttle bus schedules, rental bicycles, convenience store

### Search Tool Usage

The agent automatically uses the document search tool when users ask product and service-related questions. Example queries:

```text
"エアコンの使い方は？" (How to use air conditioner?)
"Wi-Fiはどこで使えますか？" (Where can I use Wi-Fi?)
"駐車場の規則" (Parking lot rules)
```

## 🔒 SSL Certificate Configuration

### Automatic SSL Setup

This project automatically configures SSL certificates to resolve common certificate verification issues:

```text
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate
```

### SSL Configuration Methods

**1. Backend Application** (`app/main.py`):

```python
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
```

**2. Run Script** (`run.sh`):

```bash
export SSL_CERT_FILE=$(python -m certifi)
```

**3. Test Script** (`test.sh`):

```bash
export SSL_CERT_FILE=$(python -m certifi)
```

### Manual SSL Setup (if needed)

```bash
export SSL_CERT_FILE=$(python -m certifi)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### SSL Verification

Check if SSL certificates are properly configured:

```bash
python -c "import os, certifi; print('SSL_CERT_FILE:', os.getenv('SSL_CERT_FILE', 'Not set')); print('Certifi path:', certifi.where())"
```

### What SSL Configuration Fixes

- ✅ **ADK Agent API Calls**: Communication with Google's Gemini API
- ✅ **Integration Tests**: Real ADK agent tests run successfully  
- ✅ **ChromaDB Search**: Agent can use the document search tool
- ✅ **Cross-Platform**: Works on macOS, Linux, and Windows
- ✅ **CI/CD Friendly**: Automated SSL configuration

## 📁 Project Structure

```text
backend/
├── app/
│   ├── main.py                 # FastAPI server with SSE streaming
│   ├── search_agent/
│   │   ├── agent.py           # Gemini 2.0 Flash agent
│   │   ├── chromadb_search.py # Document search functionality
│   │   └── file_desc_emb.csv  # Document embeddings (34,504+ entries)
│   └── static/
│       ├── index.html         # Test interface
│       └── js/                # Audio streaming utilities
├── test/
│   ├── test_agent_chromadb_integration.py  # Agent integration tests
│   ├── test_server_full.py                 # Comprehensive server test
│   ├── test_find_document_unique.py        # Document search tests
│   └── test_show_document_integration.py   # PDF display tests
├── logs/                      # Server logs and PID files
├── requirements.txt           # Python dependencies
├── pytest.ini               # Pytest configuration
├── run.sh                   # Server startup script
├── test.sh                  # Test execution script
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```bash
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Optional (automatically set)
SSL_CERT_FILE=/path/to/certificates
```

### Pytest Configuration

The `pytest.ini` file includes:

- Asyncio support for async tests
- Test markers for integration tests
- SSL certificate configuration

## 🚨 Troubleshooting

### Common Issues

#### 1. SSL Certificate Errors

- Solution: SSL is automatically configured, but verify with the SSL verification command above

#### 2. Google API Key Not Found

- Solution: Ensure `.env` file exists with valid `GOOGLE_API_KEY`

#### 3. ChromaDB Initialization Slow

- Expected: Loading 34,504+ documents takes ~10-15 seconds on startup

#### 4. Test Failures

- Check logs in `backend/logs/` for detailed error information
- Ensure all dependencies are installed: `pip install -r requirements.txt`

### Server Logs

Server logs are automatically saved to:

- `logs/test_server_YYYYMMDD_HHMMSS.log` (test runs)
- PID files in `logs/server.pid` or `logs/test_server.pid`

### Performance

- **Server startup**: ~10-15 seconds (ChromaDB initialization)
- **Document search**: <2 seconds per query
- **Agent response**: 5-10 seconds for complex queries
- **Memory usage**: ~2-3GB (due to document embeddings)

## 🎯 Development

### Adding New Tests

1. Create test files in `test/` directory
2. Use `@pytest.mark.asyncio` for async tests
3. Follow existing patterns for agent testing
4. Add integration tests with `@pytest.mark.integration`

### Extending Document Search

1. Add new PDFs to `app/static/resources/`
2. Process with index-building tools
3. Update `file_desc_emb.csv` with new embeddings
4. Restart server to load new documents

### Modifying Agent Behavior

1. Edit `app/search_agent/agent.py` for agent configuration
2. Update `app/search_agent/chromadb_search.py` for search logic
3. Test changes with `./test.sh`

## 📊 System Requirements

- **Python**: 3.12+
- **Memory**: 4GB+ recommended (for document embeddings)
- **Storage**: 500MB+ (for document data)
- **Network**: Internet connection for Google API calls

## 📚 Related Documentation

- **Frontend**: See `../frontend/README.md`
- **Index Building**: See `../index-building/README.md`
- **Project Overview**: See `../CLAUDE.md`
