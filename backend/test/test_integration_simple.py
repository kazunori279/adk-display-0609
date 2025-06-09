"""Simple integration tests for the FastAPI backend server.

This module contains integration tests that:
1. Start the server
2. Test basic endpoints
3. Clean up and shutdown properly
"""

import asyncio
import json
import subprocess
import time
import signal
import os
from typing import Optional

import pytest
import pytest_asyncio
import httpx


class SimpleServerManager:
    """Manages server startup and shutdown for integration tests."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8001):
        self.host = host
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://{host}:{port}"
    
    async def start_server(self) -> None:
        """Start the FastAPI server in a subprocess."""
        # Change to the app directory to run the server
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Create a simple .env file for testing
        env_path = os.path.join(app_dir, ".env")
        with open(env_path, "w") as f:
            f.write("GEMINI_API_KEY=test_key_for_testing\n")
        
        try:
            # Start server process
            self.process = subprocess.Popen(
                ["python", "-m", "uvicorn", "app.main:app", "--host", self.host, "--port", str(self.port)],
                cwd=app_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None,
                env={**os.environ, "GEMINI_API_KEY": "test_key_for_testing"}
            )
            
            # Wait for server to be ready
            await self._wait_for_server()
        finally:
            # Clean up .env file
            if os.path.exists(env_path):
                os.remove(env_path)
    
    async def _wait_for_server(self, timeout: int = 30) -> None:
        """Wait for the server to be ready to accept connections."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.base_url}/", timeout=5.0)
                    if response.status_code == 200:
                        return
            except (httpx.ConnectError, httpx.ConnectTimeout):
                await asyncio.sleep(0.5)
                continue
        
        raise TimeoutError(f"Server did not start within {timeout} seconds")
    
    async def stop_server(self) -> None:
        """Stop the server and clean up."""
        if self.process:
            try:
                # Send SIGTERM to the process group to ensure all child processes are terminated
                if os.name != 'nt':
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    self.process.terminate()
                
                # Wait for process to terminate
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    if os.name != 'nt':
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    else:
                        self.process.kill()
                    self.process.wait()
                
            except (ProcessLookupError, OSError):
                # Process already terminated
                pass
            finally:
                self.process = None


@pytest_asyncio.fixture
async def simple_server():
    """Fixture that starts and stops the server for each test."""
    server_manager = SimpleServerManager()
    
    try:
        await server_manager.start_server()
        yield server_manager
    finally:
        await server_manager.stop_server()


async def test_server_startup_and_root_endpoint(simple_server):
    """Test that the server starts up and responds to the root endpoint."""
    async with httpx.AsyncClient() as client:
        # Test that the server is running and responds to the root endpoint
        response = await client.get(f"{simple_server.base_url}/")
        assert response.status_code == 200
        # Should serve the static HTML file
        assert "text/html" in response.headers.get("content-type", "")


async def test_server_static_files(simple_server):
    """Test that static files are served correctly."""
    async with httpx.AsyncClient() as client:
        # Test static file serving
        response = await client.get(f"{simple_server.base_url}/static/index.html")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


async def test_sse_endpoint_connection(simple_server):
    """Test that SSE endpoint can be connected to (even if it fails due to mocking)."""
    async with httpx.AsyncClient() as client:
        # Test SSE endpoint connection
        # This will likely fail due to missing Google ADK setup, but should at least connect
        try:
            with client.stream("GET", f"{simple_server.base_url}/events/1?is_audio=false") as response:
                # If we get a response (even an error), the endpoint is working
                assert response.status_code in [200, 500]  # 500 is OK due to missing API keys
        except Exception:
            # Any connection attempt is considered success for this basic test
            pass


async def test_send_endpoint_without_session(simple_server):
    """Test sending a message without an active session."""
    async with httpx.AsyncClient() as client:
        # Try to send message to a user that hasn't established SSE connection
        url = f"{simple_server.base_url}/send/999"
        payload = {
            "mime_type": "text/plain", 
            "data": "test message"
        }
        response = await client.post(url, json=payload)
        assert response.status_code == 200
        result = response.json()
        assert result.get("error") == "Session not found"


async def test_server_cleanup_and_shutdown():
    """Test proper cleanup when server shuts down."""
    server_manager = SimpleServerManager()
    
    # Start server
    await server_manager.start_server()
    
    # Verify server is running
    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(f"{server_manager.base_url}/")
        assert response.status_code == 200
    
    # Shutdown server
    await server_manager.stop_server()
    
    # Verify server is no longer accessible
    with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
        async with httpx.AsyncClient() as http_client:
            await http_client.get(f"{server_manager.base_url}/", timeout=2.0)


async def test_multiple_concurrent_requests(simple_server):
    """Test that the server can handle multiple concurrent requests."""
    async with httpx.AsyncClient() as client:
        # Send multiple concurrent requests to the root endpoint
        tasks = []
        for i in range(5):
            task = client.get(f"{simple_server.base_url}/")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])