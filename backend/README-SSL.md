# SSL Certificate Configuration

This document explains how SSL certificates are automatically configured for the ADK backend.

## 🔒 SSL Certificate Issues

On macOS and some other environments, Python may have issues verifying SSL certificates when connecting to Google's APIs. This manifests as:

```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate
```

## ✅ Automatic SSL Configuration

This project automatically configures SSL certificates in multiple ways:

### 1. **Backend Application** (`app/main.py`)
The main FastAPI application automatically sets the SSL certificate file:
```python
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
```

### 2. **Integration Tests** (`test/test_agent_chromadb_integration.py`)
Tests automatically configure SSL certificates:
```python
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
```

### 3. **Server Run Script** (`run.sh`)
The server startup script sets SSL certificates:
```bash
export SSL_CERT_FILE=$(python -m certifi)
```

### 4. **Test Run Script** (`test.sh`)
The test script sets SSL certificates:
```bash
export SSL_CERT_FILE=$(python -m certifi)
```

## 🚀 Usage

### Running Tests
```bash
# Method 1: Direct pytest (SSL auto-configured)
python -m pytest test/test_agent_chromadb_integration.py

# Method 2: Using test script
./test.sh test/test_agent_chromadb_integration.py

# Method 3: Manual SSL setup
export SSL_CERT_FILE=$(python -m certifi)
python -m pytest test/test_agent_chromadb_integration.py
```

### Running Backend Server
```bash
# Method 1: Using run script (SSL auto-configured)
./run.sh

# Method 2: Direct python (SSL auto-configured in main.py)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Method 3: Manual SSL setup
export SSL_CERT_FILE=$(python -m certifi)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔍 Verification

Check if SSL certificates are properly configured:
```bash
python -c "import os, certifi; print('SSL_CERT_FILE:', os.getenv('SSL_CERT_FILE', 'Not set')); print('Certifi path:', certifi.where())"
```

## 📋 What This Fixes

- ✅ **ADK Agent API Calls**: Allows communication with Google's Gemini API
- ✅ **Integration Tests**: Real ADK agent tests can run successfully  
- ✅ **ChromaDB Search**: Agent can use the document search tool
- ✅ **Cross-Platform**: Works on macOS, Linux, and Windows
- ✅ **CI/CD Friendly**: Automated SSL configuration for all environments

## 🎯 Technical Details

The `certifi` package provides Mozilla's CA certificate bundle, which is the same set of certificates trusted by Firefox browser. Setting `SSL_CERT_FILE` tells OpenSSL where to find trusted Certificate Authorities for SSL verification.

This is a standard solution for Python SSL certificate issues, especially in virtual environments and on macOS systems.