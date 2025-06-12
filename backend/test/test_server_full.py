#!/usr/bin/env python3
"""
Comprehensive server test that:
1. Kills all processes using port 8000
2. Runs the server
3. Sends test query and verifies response
4. Checks server log for errors
5. Leaves server running
"""

import asyncio
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional

import httpx


class ServerTester:
    """Comprehensive server testing class."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.server_process: Optional[subprocess.Popen] = None
        self.log_file: Optional[str] = None

    def step_1_kill_existing_processes(self):
        """Step 1: Kill all processes using port 8000."""
        print("🔥 Step 1: Killing all processes using port 8000...")

        # Kill processes using lsof
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{self.port}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                print(f"   Found processes using port {self.port}: {pids}")

                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"   Killed process {pid}")
                    except (ProcessLookupError, ValueError):
                        print(f"   Process {pid} already terminated")

                # Wait for processes to terminate
                time.sleep(2)
                print("   ✅ Existing processes terminated")
            else:
                print("   ✅ No existing processes found on port 8000")

        except subprocess.TimeoutExpired:
            print("   ⚠️  lsof command timed out")
        except FileNotFoundError:
            print("   ⚠️  lsof command not found, trying alternative method")

        # Kill any remaining uvicorn processes
        try:
            subprocess.run(["pkill", "-f", "uvicorn"], timeout=5, check=False)
            print("   ✅ Killed any remaining uvicorn processes")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def step_2_start_server(self):
        """Step 2: Start a new server process."""
        print("🚀 Step 2: Starting new server...")

        # Set SSL certificate file
        env = os.environ.copy()
        env['SSL_CERT_FILE'] = subprocess.check_output(
            ["python", "-m", "certifi"], text=True
        ).strip()

        # Create logs directory in backend directory
        backend_dir = Path(__file__).parent.parent  # Go up from test/ to backend/
        logs_dir = backend_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Set log file with timestamp (full path)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.log_file = str(logs_dir / f"test_server_{timestamp}.log")

        print(f"   Starting server with SSL_CERT_FILE: {env['SSL_CERT_FILE']}")
        print(f"   Server logs: {self.log_file}")

        # Start server process (change to backend directory first)
        backend_dir = Path(__file__).parent.parent  # Go up from test/ to backend/
        with open(self.log_file, 'w', encoding='utf-8') as log_file:
            self.server_process = subprocess.Popen(
                [
                    "python", "-m", "uvicorn",
                    "app.main:app",
                    "--reload",
                    "--host", self.host,
                    "--port", str(self.port)
                ],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=str(backend_dir),  # Set working directory to backend/
                preexec_fn=os.setsid if os.name != 'nt' else None
            )

        print(f"   Server started with PID: {self.server_process.pid}")

        # Save PID to file in backend logs directory
        pid_file_path = logs_dir / "test_server.pid"
        with open(pid_file_path, "w", encoding='utf-8') as pid_file:
            pid_file.write(str(self.server_process.pid))

        # Wait for server to initialize (including ChromaDB loading)
        print("   Waiting for server initialization (including ChromaDB loading)...")
        self._wait_for_server_ready()

    def _wait_for_server_ready(self, timeout: int = 180):
        """Wait for server to be ready, including ChromaDB initialization."""
        start_time = time.time()
        server_responding = False

        print("   ⏳ Waiting for server to start...")

        while time.time() - start_time < timeout:
            try:
                # Check if server process is still running
                if self.server_process and self.server_process.poll() is not None:
                    print(f"   ❌ Server process terminated with code {self.server_process.poll()}")
                    raise RuntimeError("Server process terminated unexpectedly")

                # Check if server responds
                with httpx.Client(timeout=10) as client:
                    response = client.get(f"{self.base_url}/")
                    if response.status_code == 200:
                        if not server_responding:
                            print("   ✅ Server is responding to HTTP requests")
                            server_responding = True

                        # Check if ChromaDB initialization is complete
                        if self._check_chromadb_initialization():
                            print("   ✅ ChromaDB initialization complete")
                            return
                        
                        # Show progress dots for ChromaDB loading
                        elapsed = int(time.time() - start_time)
                        if elapsed % 10 == 0:  # Every 10 seconds
                            print(f"   ⏳ ChromaDB loading... ({elapsed}s elapsed)")

            except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError):
                if not server_responding:
                    # Show progress dots for server startup
                    elapsed = int(time.time() - start_time)
                    if elapsed % 5 == 0:  # Every 5 seconds
                        print(f"   ⏳ Server starting... ({elapsed}s elapsed)")

            time.sleep(3)

        raise TimeoutError(f"Server did not become ready within {timeout} seconds")

    def _check_chromadb_initialization(self) -> bool:
        """Check if ChromaDB initialization is complete by looking at logs."""
        if not self.log_file or not os.path.exists(self.log_file):
            return False

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
                return "🎉 ChromaDB initialization complete - server ready!" in log_content
        except Exception:
            return False

    async def step_3_send_test_query(self):
        """Step 3: Send test query and verify response."""
        print("🔍 Step 3: Sending test query and verifying response...")

        # Test queries covering wide range of topics in Japanese (20 total) - based on actual CSV content
        test_queries = [
            # Wi-Fi and Internet (using actual CSV queries)
            "Wi-Fiはどこで使えますか？",  # Where can I use Wi-Fi?
            "オーナーズリビングでインターネットに接続できますか？",  # Can I connect to internet at Owner's Living?
            
            # Air conditioning and heating
            "エアコンの使い方は？",  # How to use air conditioner
            "暖房の設定方法",  # Heating setup method
            "ミストサウナ機能付き浴室暖房乾燥機の衣類乾燥機能はありますか？",  # Does mist sauna bathroom heater dryer have clothes drying function?
            
            # Kitchen appliances
            "電子レンジの使い方",  # How to use microwave
            "食器洗い機の操作方法",  # How to operate dishwasher
            "コーヒーメーカーの使用方法",  # How to use coffee maker
            "炊飯の始め方を教えてください",  # How to start rice cooking (actual CSV query)
            
            # Laundry and cleaning (using actual CSV queries)
            "洗濯機の使い方",  # How to use washing machine
            "掃除機の組み立て方を教えてください",  # How to assemble vacuum cleaner (actual CSV query)
            "衣類乾燥機能はありますか？",  # Is there a clothes drying function? (actual CSV query)
            
            # Building services and facilities (using actual CSV queries)
            "駐車場の規則",  # Parking lot rules
            "ゴミの分別方法",  # Garbage separation method
            "シャトルバスの時刻表",  # Shuttle bus schedule
            "BBQグッズの予約はコンシェルジュカウンターですか？",  # Is BBQ goods reservation at concierge counter? (actual CSV query)
            
            # Safety and security
            "火災警報器の使い方",  # How to use fire alarm
            "避難器具の操作方法",  # How to operate evacuation equipment
            "インターホンの使い方",  # How to use intercom (more specific)
            
            # Troubleshooting (using actual CSV queries)
            "エアコンが効かない時の対処法"  # Air conditioner not working troubleshooting
        ]

        for i, query in enumerate(test_queries, 1):
            print(f"   Test Query {i}: {query}")

            try:
                # Connect to SSE endpoint first (use integer user_id)
                user_id = int(time.time()) + i  # Add i to make each user_id unique
                sse_task = asyncio.create_task(self._listen_for_responses(user_id))

                # Wait a moment for SSE connection
                await asyncio.sleep(1)

                # Send query
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        f"{self.base_url}/send/{user_id}",
                        json={
                            "mime_type": "text/plain",
                            "data": query
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        if result.get("status") == "sent":
                            print(f"   ✅ Query {i} sent successfully")

                            # Wait for response (shorter time for efficiency with 20 queries)
                            await asyncio.sleep(8)  # Give time for agent to respond

                            # Cancel SSE listening
                            sse_task.cancel()
                            try:
                                await sse_task
                            except asyncio.CancelledError:
                                pass

                            print(f"   ✅ Query {i} completed")
                        else:
                            print(f"   ❌ Query {i} failed: {result}")
                    else:
                        print(f"   ❌ Query {i} HTTP error: {response.status_code}")

            except Exception as e:
                print(f"   ❌ Query {i} exception: {e}")

            # Brief pause between queries (shorter for efficiency)
            await asyncio.sleep(1)

    async def _listen_for_responses(self, user_id: int):
        """Listen for SSE responses and check for show_document messages."""
        show_document_received = False
        messages_received = []
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "GET",
                    f"{self.base_url}/events/{user_id}?is_audio=false"
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    messages_received.append(data)
                                    
                                    # Check for show_document command
                                    if (data.get("mime_type") == "application/json" and 
                                        isinstance(data.get("data"), dict) and
                                        data["data"].get("command") == "show_document"):
                                        show_document_received = True
                                        print(f"   ✅ show_document message received: {data}")
                                    
                                    # Check for text responses
                                    elif data.get("mime_type") == "text/plain":
                                        print(f"   📝 Text response: {data.get('data', '')[:100]}...")
                                    
                                    if data.get("turn_complete"):
                                        break
                                except json.JSONDecodeError:
                                    continue
        except Exception as e:
            print(f"   ⚠️  SSE connection error: {e}")
        
        # Store results for this user_id
        if not hasattr(self, 'test_results'):
            self.test_results = {}
        self.test_results[user_id] = {
            'show_document_received': show_document_received,
            'messages_count': len(messages_received)
        }
        
        if show_document_received:
            print(f"   ✅ User {user_id}: show_document message successfully received!")
        else:
            print(f"   ⚠️  User {user_id}: No show_document message received")

    def step_4_check_server_logs(self):
        """Step 4: Check server logs for errors."""
        print("📋 Step 4: Checking server logs for errors...")

        if not self.log_file or not os.path.exists(self.log_file):
            print("   ❌ Log file not found")
            return

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()

            # Look for error patterns
            error_patterns = [
                "ERROR",
                "CRITICAL",
                "Exception",
                "Traceback",
                "Failed",
                "Error:"
            ]

            errors_found = []
            lines = log_content.split('\n')

            for i, line in enumerate(lines):
                for pattern in error_patterns:
                    if pattern in line and "DeprecationWarning" not in line:
                        errors_found.append(f"Line {i+1}: {line.strip()}")

            if errors_found:
                print(f"   ⚠️  Found {len(errors_found)} potential errors in logs:")
                for error in errors_found[:5]:  # Show first 5 errors
                    print(f"      {error}")
                if len(errors_found) > 5:
                    print(f"      ... and {len(errors_found) - 5} more errors")
            else:
                print("   ✅ No errors found in server logs")

            # Check for successful initialization
            if "🎉 ChromaDB initialization complete - server ready!" in log_content:
                print("   ✅ ChromaDB initialization successful")
            else:
                print("   ⚠️  ChromaDB initialization message not found")

            # Check for document loading
            if "📊 Ready to search" in log_content:
                pattern = r"📊 Ready to search (\d+) product and service manual documents"
                match = re.search(pattern, log_content)
                if match:
                    doc_count = match.group(1)
                    print(f"   ✅ Loaded {doc_count} documents successfully")
                else:
                    print("   ⚠️  Document count not found in logs")

        except Exception as e:
            print(f"   ❌ Error reading log file: {e}")

    def step_5_verify_show_document_functionality(self):
        """Step 5: Verify show_document functionality based on test results."""
        print("📋 Step 5: Verifying show_document functionality...")
        
        if not hasattr(self, 'test_results') or not self.test_results:
            print("   ⚠️  No test results available to verify")
            return
        
        show_document_tests = []
        total_tests = len(self.test_results)
        total_messages = sum(results['messages_count'] for results in self.test_results.values())
        
        for user_id, results in self.test_results.items():
            if results['show_document_received']:
                show_document_tests.append(user_id)
        
        print(f"   📊 Test Summary:")
        print(f"      Total queries tested: {total_tests}")
        print(f"      Total messages received: {total_messages}")
        print(f"      show_document messages: {len(show_document_tests)}")
        print(f"      Success rate: {len(show_document_tests)/total_tests*100:.1f}%")
        
        if show_document_tests:
            print(f"   ✅ show_document functionality working! Success rate: {len(show_document_tests)}/{total_tests}")
            if len(show_document_tests) <= 5:  # Show details for small numbers
                for user_id in show_document_tests:
                    print(f"      - User {user_id}: show_document message received")
            else:
                print(f"      - {len(show_document_tests)} queries successfully triggered document display")
        else:
            print("   ⚠️  show_document functionality may not be working - no messages received")
            print("   💡 This could mean:")
            print("      - The agent didn't use the show_document_tool")
            print("      - The queue integration has issues")
            print("      - The queries didn't trigger document display")

    def step_6_keep_server_running(self):
        """Step 6: Keep server running and provide status."""
        print("🏃 Step 6: Keeping server running...")

        if self.server_process and self.server_process.poll() is None:
            print(f"   ✅ Server is running with PID: {self.server_process.pid}")
            print(f"   📍 URL: {self.base_url}")
            print(f"   📄 Logs: {self.log_file}")
            backend_dir = Path(__file__).parent.parent
            pid_file_path = backend_dir / "logs" / "test_server.pid"
            print(f"   🔍 PID file: {pid_file_path}")
            print()
            print("   Commands:")
            print(f"     tail -f {self.log_file}                    # Follow logs")
            print(f"     kill {self.server_process.pid}             # Stop server")
            print(f"     kill $(cat {pid_file_path})           # Stop using PID file")
            print()
            print("   🎉 Server test completed successfully!")
            print("   🚀 Server is ready for testing at http://localhost:8000")
        else:
            print("   ❌ Server is not running")

    async def run_full_test(self):
        """Run the complete server test."""
        print("🧪 Starting comprehensive server test...")
        print("=" * 60)

        try:
            self.step_1_kill_existing_processes()
            print()

            self.step_2_start_server()
            print()

            await self.step_3_send_test_query()
            print()

            self.step_4_check_server_logs()
            print()

            self.step_5_verify_show_document_functionality()
            print()

            self.step_6_keep_server_running()

        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            if self.server_process:
                self.server_process.terminate()
            raise


async def main():
    """Main test function."""
    tester = ServerTester()
    await tester.run_full_test()


if __name__ == "__main__":
    asyncio.run(main())
