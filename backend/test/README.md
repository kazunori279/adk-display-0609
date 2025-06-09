# Backend Integration Tests

This directory contains comprehensive integration tests for the FastAPI backend server.

## Test Files

### `test_basic_integration.py`
- **Purpose**: Demonstrates integration testing patterns with mock server and client
- **Features**:
  - Mock server startup and shutdown
  - Mock client connection and message exchange
  - Multiple client testing
  - Proper cleanup and resource management
  - Comprehensive workflow testing

### `test_integration.py` 
- **Purpose**: Full integration tests with real server (requires additional setup)
- **Features**:
  - Real server process management
  - SSE (Server-Sent Events) testing
  - HTTP client-server communication
  - Advanced mocking of Google ADK components

### `test_integration_simple.py`
- **Purpose**: Simple integration tests focusing on basic server functionality
- **Features**:
  - Basic server startup/shutdown
  - Static file serving
  - Endpoint connectivity testing

## Running the Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements.txt
```

### Running Tests

Run all basic integration tests (recommended):
```bash
python -m pytest test/test_basic_integration.py -v --asyncio-mode=auto
```

Run with detailed output:
```bash
python -m pytest test/test_basic_integration.py -v -s --asyncio-mode=auto
```

Run a specific test:
```bash
python -m pytest test/test_basic_integration.py::test_comprehensive_integration_workflow -v --asyncio-mode=auto
```

Run all tests in the directory:
```bash
python -m pytest test/ -v --asyncio-mode=auto
```

### Test Configuration

The tests use `pytest.ini` configuration:
- Async mode: auto
- Test paths: test directory
- Verbose output by default

## Test Structure

### 1. Server Management
Tests demonstrate proper server lifecycle management:
- Starting server processes
- Waiting for server readiness
- Graceful shutdown
- Resource cleanup

### 2. Client Communication
Tests cover various client-server communication patterns:
- Text message exchange
- Audio message handling
- Multiple concurrent clients
- Session management
- Error handling

### 3. Integration Patterns
Tests showcase integration testing best practices:
- Mock objects and fixtures
- Async test patterns
- Resource management
- Cleanup procedures
- Comprehensive workflow testing

## Example Test Output

```
test/test_basic_integration.py::test_mock_server_startup_and_shutdown PASSED
test/test_basic_integration.py::test_mock_client_connection PASSED
test/test_basic_integration.py::test_mock_text_message_communication PASSED
test/test_basic_integration.py::test_mock_audio_message_communication PASSED
test/test_basic_integration.py::test_multiple_mock_clients PASSED
test/test_basic_integration.py::test_mock_session_not_found PASSED
test/test_basic_integration.py::test_mock_client_connection_error PASSED
test/test_basic_integration.py::test_mock_cleanup_and_resource_management PASSED
test/test_basic_integration.py::test_comprehensive_integration_workflow PASSED

9 passed in 1.00s
```

## Key Features Demonstrated

1. **Server Startup/Shutdown**: Complete server lifecycle management
2. **Mock Client Testing**: Simulated client-server communication
3. **Message Exchange**: Text and audio message handling
4. **Multiple Clients**: Concurrent client connection testing
5. **Error Handling**: Session management and error scenarios
6. **Resource Cleanup**: Proper cleanup and resource management
7. **Comprehensive Workflow**: End-to-end integration testing

These tests provide a solid foundation for ensuring the backend server works correctly and can handle various client scenarios safely and efficiently.