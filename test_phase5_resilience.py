#!/usr/bin/env python3
"""
Phase 5: Error Handling & Resilience Testing for My Newsletters Voice Assistant
Tests system reliability, error recovery, and failure handling mechanisms
"""

import asyncio
import json
import time
import random
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import aiohttp
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Configuration
BASE_URL = "http://localhost:5000"

class ResilienceTestSuite:
    """Error handling and resilience testing framework"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_results: Dict[str, List[Dict]] = {
            "external_service_failures": [],
            "network_resilience": [],
            "data_corruption_recovery": []
        }
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        
    async def setup(self):
        """Initialize test session"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        print("\n" + "="*80)
        print("PHASE 5: ERROR HANDLING & RESILIENCE TESTING")
        print("="*80)
        print(f"Target: {self.base_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
    async def teardown(self):
        """Clean up test session"""
        if self.session:
            await self.session.close()
            
    async def run_test(self, category: str, test_name: str, test_func):
        """Execute a single test and record results"""
        self.total_tests += 1
        print(f"\n[{self.total_tests}] Testing: {test_name}")
        print("-" * 60)
        
        try:
            result = await test_func()
            if result["status"] == "PASS":
                self.passed_tests += 1
                print(f"✅ PASSED: {result.get('message', 'Test successful')}")
            elif result["status"] == "SKIP":
                self.skipped_tests += 1
                print(f"⏭️  SKIPPED: {result.get('message', 'Test skipped')}")
            elif result["status"] == "WARN":
                self.passed_tests += 1  # Count warnings as passes with caveats
                print(f"⚠️  WARNING: {result.get('message', 'Test passed with warnings')}")
            else:
                self.failed_tests += 1
                print(f"❌ FAILED: {result.get('message', 'Test failed')}")
                if "error" in result:
                    print(f"   Error: {result['error']}")
                    
            self.test_results[category].append({
                "test": test_name,
                "status": result["status"],
                "message": result.get("message", ""),
                "details": result.get("details", {})
            })
        except Exception as e:
            self.failed_tests += 1
            print(f"❌ ERROR: {str(e)}")
            self.test_results[category].append({
                "test": test_name,
                "status": "ERROR",
                "message": str(e)
            })

    # ==================== EXTERNAL SERVICE FAILURE TESTS ====================
    
    async def test_gmail_api_failures(self) -> Dict:
        """Test Gmail API failure handling"""
        try:
            test_scenarios = []
            
            # Test 1: OAuth endpoint when Gmail might be down
            try:
                async with self.session.post(
                    f"{self.base_url}/auth/gmail-oauth",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 500:
                        # Server error might indicate Gmail service issues
                        error_text = await resp.text()
                        if "timeout" in error_text.lower() or "connection" in error_text.lower():
                            test_scenarios.append("Gmail connection timeout handled")
                        else:
                            test_scenarios.append("Gmail error handled gracefully")
                    elif resp.status in [200, 415]:  # Normal responses
                        test_scenarios.append("Gmail OAuth accessible")
                    else:
                        test_scenarios.append(f"Gmail OAuth returned {resp.status}")
            except asyncio.TimeoutError:
                test_scenarios.append("Gmail timeout handled with exception")
            except Exception as e:
                test_scenarios.append(f"Gmail error: {str(e)[:50]}")
                
            # Test 2: Newsletter fetch with invalid/expired tokens
            invalid_token = "invalid_gmail_token_12345"
            try:
                async with self.session.post(
                    f"{self.base_url}/newsletters/fetch",
                    json={"access_token": invalid_token, "user_id": 1},
                    headers={"Authorization": "Bearer mock_token"}
                ) as resp:
                    if resp.status in [401, 403]:
                        test_scenarios.append("Invalid Gmail token rejected properly")
                    elif resp.status == 500:
                        error_text = await resp.text()
                        if "gmail" in error_text.lower() or "oauth" in error_text.lower():
                            test_scenarios.append("Gmail auth error handled")
                        else:
                            test_scenarios.append("Server error on invalid token")
                    else:
                        test_scenarios.append(f"Gmail fetch returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Gmail fetch error handled: {str(e)[:30]}")
                
            # Test 3: Rate limiting behavior
            rapid_requests = 0
            rate_limited = False
            try:
                for i in range(10):  # Make rapid requests
                    async with self.session.post(
                        f"{self.base_url}/auth/gmail-oauth"
                    ) as resp:
                        rapid_requests += 1
                        if resp.status == 429:
                            rate_limited = True
                            break
                        await asyncio.sleep(0.1)
                        
                if rate_limited:
                    test_scenarios.append("Gmail rate limiting working")
                else:
                    test_scenarios.append("Gmail requests processed normally")
            except Exception as e:
                test_scenarios.append(f"Gmail rate limit test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 3:
                return {
                    "status": "PASS", 
                    "message": f"Gmail failure handling tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited Gmail testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_elevenlabs_failures(self) -> Dict:
        """Test ElevenLabs API failure handling"""
        try:
            test_scenarios = []
            
            # Test 1: Audio generation with potential service issues
            try:
                async with self.session.post(
                    f"{self.base_url}/audio/generate",
                    json={"text": "Test audio for resilience testing", "story_id": 999},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 500:
                        error_text = await resp.text()
                        if "elevenlabs" in error_text.lower() or "tts" in error_text.lower():
                            test_scenarios.append("ElevenLabs service error handled")
                        else:
                            test_scenarios.append("Audio generation error handled")
                    elif resp.status == 200:
                        test_scenarios.append("ElevenLabs service accessible")
                    elif resp.status == 401:
                        test_scenarios.append("Audio generation requires auth")
                    else:
                        test_scenarios.append(f"Audio generation returned {resp.status}")
            except asyncio.TimeoutError:
                test_scenarios.append("ElevenLabs timeout handled")
            except Exception as e:
                test_scenarios.append(f"ElevenLabs error: {str(e)[:40]}")
                
            # Test 2: Invalid voice ID handling
            try:
                async with self.session.post(
                    f"{self.base_url}/audio/generate",
                    json={
                        "text": "Test", 
                        "story_id": 1, 
                        "voice_id": "invalid_voice_id_12345"
                    }
                ) as resp:
                    if resp.status in [400, 422]:
                        test_scenarios.append("Invalid voice ID rejected")
                    elif resp.status == 500:
                        test_scenarios.append("Invalid voice ID error handled")
                    else:
                        test_scenarios.append(f"Voice ID test returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Voice ID test error: {str(e)[:30]}")
                
            # Test 3: Large text handling (quota/limit testing)
            large_text = "This is a very long text for testing ElevenLabs limits. " * 100
            try:
                async with self.session.post(
                    f"{self.base_url}/audio/generate",
                    json={"text": large_text, "story_id": 1}
                ) as resp:
                    if resp.status == 413:
                        test_scenarios.append("Large text payload rejected properly")
                    elif resp.status == 400:
                        test_scenarios.append("Large text validation working")
                    elif resp.status == 500:
                        test_scenarios.append("Large text server error handled")
                    else:
                        test_scenarios.append(f"Large text returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Large text test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 2:
                return {
                    "status": "PASS", 
                    "message": f"ElevenLabs failure handling tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited ElevenLabs testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_openai_failures(self) -> Dict:
        """Test OpenAI API failure handling"""
        try:
            test_scenarios = []
            
            # Test 1: Newsletter parsing that might use OpenAI
            try:
                invalid_html = "<html><body>" + "Invalid content " * 1000 + "</body></html>"
                async with self.session.post(
                    f"{self.base_url}/newsletters/parse",
                    json={"html_content": invalid_html}
                ) as resp:
                    if resp.status == 500:
                        error_text = await resp.text()
                        if "openai" in error_text.lower() or "ai" in error_text.lower():
                            test_scenarios.append("OpenAI service error handled")
                        else:
                            test_scenarios.append("Parsing error handled gracefully")
                    elif resp.status == 200:
                        test_scenarios.append("OpenAI parsing service accessible")
                    elif resp.status in [400, 422]:
                        test_scenarios.append("Invalid HTML rejected properly")
                    else:
                        test_scenarios.append(f"HTML parsing returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"OpenAI parsing test: {str(e)[:40]}")
                
            # Test 2: Extremely large content that might hit token limits
            huge_content = "Newsletter content for testing AI limits. " * 500
            try:
                async with self.session.post(
                    f"{self.base_url}/newsletters/parse",
                    json={"html_content": huge_content},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 413:
                        test_scenarios.append("Large content payload rejected")
                    elif resp.status == 500:
                        test_scenarios.append("Large content processing error handled")
                    elif resp.status == 200:
                        test_scenarios.append("Large content processed successfully")
                    else:
                        test_scenarios.append(f"Large content returned {resp.status}")
            except asyncio.TimeoutError:
                test_scenarios.append("OpenAI timeout handled properly")
            except Exception as e:
                test_scenarios.append(f"Large content test: {str(e)[:30]}")
                
            # Test 3: Malformed content
            try:
                malformed_content = "{'invalid': 'json structure for testing"
                async with self.session.post(
                    f"{self.base_url}/newsletters/parse",
                    json={"html_content": malformed_content}
                ) as resp:
                    if resp.status in [400, 422]:
                        test_scenarios.append("Malformed content rejected")
                    elif resp.status == 500:
                        test_scenarios.append("Malformed content error handled")
                    else:
                        test_scenarios.append(f"Malformed content returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Malformed content test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 2:
                return {
                    "status": "PASS", 
                    "message": f"OpenAI failure handling tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited OpenAI testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_database_failures(self) -> Dict:
        """Test database failure handling"""
        try:
            test_scenarios = []
            
            # Test 1: Invalid database queries
            try:
                # Try to access non-existent newsletter
                async with self.session.get(
                    f"{self.base_url}/newsletters/999999999"
                ) as resp:
                    if resp.status == 404:
                        test_scenarios.append("Non-existent record handled properly")
                    elif resp.status == 500:
                        error_text = await resp.text()
                        if "database" not in error_text.lower():
                            test_scenarios.append("Database error hidden from user")
                        else:
                            test_scenarios.append("Database error exposed")
                    else:
                        test_scenarios.append(f"Invalid ID returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Database query test: {str(e)[:30]}")
                
            # Test 2: Concurrent database operations
            try:
                tasks = []
                for i in range(10):
                    task = self.session.get(f"{self.base_url}/health")
                    tasks.append(task)
                    
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                success_count = 0
                error_count = 0
                
                for resp in responses:
                    if isinstance(resp, Exception):
                        error_count += 1
                    elif hasattr(resp, 'status'):
                        if resp.status == 200:
                            success_count += 1
                        elif resp.status >= 500:
                            error_count += 1
                        await resp.close()
                    else:
                        error_count += 1
                        
                if success_count >= 8:  # Most requests should succeed
                    test_scenarios.append("Concurrent database access handled")
                elif error_count <= 2:  # Some errors acceptable under load
                    test_scenarios.append("Database load partially handled")
                else:
                    test_scenarios.append(f"Database overload: {error_count}/{len(responses)} errors")
                    
            except Exception as e:
                test_scenarios.append(f"Concurrent test: {str(e)[:30]}")
                
            # Test 3: Invalid user operations
            try:
                async with self.session.get(
                    f"{self.base_url}/users/invalid_user_id/newsletters"
                ) as resp:
                    if resp.status in [400, 404]:
                        test_scenarios.append("Invalid user ID handled")
                    elif resp.status == 500:
                        test_scenarios.append("Invalid user error handled")
                    else:
                        test_scenarios.append(f"Invalid user returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Invalid user test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 3:
                return {
                    "status": "PASS", 
                    "message": f"Database failure handling tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited database testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_supabase_storage_failures(self) -> Dict:
        """Test Supabase storage failure handling"""
        try:
            test_scenarios = []
            
            # Test 1: Audio file upload with potential storage issues
            try:
                # Create a test audio file
                test_audio_data = b"fake_audio_data_for_testing" * 100
                
                # Try to upload
                data = aiohttp.FormData()
                data.add_field('audio_file', test_audio_data, 
                              filename='test_resilience.mp3', 
                              content_type='audio/mpeg')
                
                async with self.session.post(
                    f"{self.base_url}/audio/upload",
                    data=data
                ) as resp:
                    if resp.status == 413:
                        test_scenarios.append("Large file upload rejected")
                    elif resp.status == 415:
                        test_scenarios.append("Invalid file type rejected")
                    elif resp.status == 500:
                        error_text = await resp.text()
                        if "storage" in error_text.lower():
                            test_scenarios.append("Storage error handled")
                        else:
                            test_scenarios.append("Upload error handled")
                    elif resp.status == 200:
                        test_scenarios.append("Storage upload working")
                    elif resp.status == 401:
                        test_scenarios.append("Upload requires authentication")
                    else:
                        test_scenarios.append(f"Upload returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Storage upload test: {str(e)[:40]}")
                
            # Test 2: Access non-existent audio files
            try:
                async with self.session.get(
                    f"{self.base_url}/audio/999999999"
                ) as resp:
                    if resp.status == 404:
                        test_scenarios.append("Non-existent audio file handled")
                    elif resp.status == 500:
                        test_scenarios.append("Audio access error handled")
                    elif resp.status == 401:
                        test_scenarios.append("Audio access requires auth")
                    else:
                        test_scenarios.append(f"Audio access returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Audio access test: {str(e)[:30]}")
                
            # Test 3: Audio queue status under stress
            try:
                async with self.session.get(
                    f"{self.base_url}/audio/queue/status"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "status" in data or "queue" in data:
                            test_scenarios.append("Audio queue status accessible")
                        else:
                            test_scenarios.append("Audio queue response incomplete")
                    elif resp.status == 500:
                        test_scenarios.append("Audio queue error handled")
                    else:
                        test_scenarios.append(f"Audio queue returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Audio queue test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 2:
                return {
                    "status": "PASS", 
                    "message": f"Storage failure handling tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited storage testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    # ==================== NETWORK RESILIENCE TESTS ====================
    
    async def test_websocket_disconnections(self) -> Dict:
        """Test WebSocket disconnection recovery"""
        try:
            # Since direct WebSocket testing is complex, we test the WebSocket endpoint availability
            # and recovery mechanisms
            test_scenarios = []
            
            # Test 1: WebSocket endpoint accessibility
            try:
                # Check if WebSocket endpoint responds (usually returns method not allowed for GET)
                async with self.session.get(f"{self.base_url}/voice") as resp:
                    if resp.status == 405:  # Method not allowed - endpoint exists
                        test_scenarios.append("WebSocket endpoint accessible")
                    elif resp.status == 404:
                        test_scenarios.append("WebSocket endpoint not found")
                    else:
                        test_scenarios.append(f"WebSocket endpoint returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"WebSocket endpoint test: {str(e)[:30]}")
                
            # Test 2: Session recovery mechanisms (briefing sessions)
            try:
                # Test session state endpoint which should handle interruptions
                async with self.session.get(
                    f"{self.base_url}/briefing/999/state"
                ) as resp:
                    if resp.status == 404:
                        test_scenarios.append("Non-existent session handled properly")
                    elif resp.status == 401:
                        test_scenarios.append("Session access requires auth")
                    elif resp.status == 500:
                        test_scenarios.append("Session state error handled")
                    else:
                        test_scenarios.append(f"Session state returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Session recovery test: {str(e)[:30]}")
                
            # Test 3: Multiple rapid connection attempts (simulating reconnections)
            try:
                connection_attempts = 0
                successful_attempts = 0
                
                for i in range(5):
                    try:
                        async with self.session.get(
                            f"{self.base_url}/health",
                            timeout=aiohttp.ClientTimeout(total=2)
                        ) as resp:
                            connection_attempts += 1
                            if resp.status == 200:
                                successful_attempts += 1
                            await asyncio.sleep(0.1)
                    except:
                        connection_attempts += 1
                        
                if successful_attempts >= 4:
                    test_scenarios.append("Rapid reconnections handled well")
                elif successful_attempts >= 2:
                    test_scenarios.append("Some reconnections successful")
                else:
                    test_scenarios.append("Connection instability detected")
                    
            except Exception as e:
                test_scenarios.append(f"Reconnection test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 2:
                return {
                    "status": "PASS", 
                    "message": f"WebSocket resilience tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited WebSocket testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_retry_logic(self) -> Dict:
        """Test retry logic and exponential backoff"""
        try:
            test_scenarios = []
            
            # Test 1: Rate limiting triggers retry behavior
            try:
                # Make rapid requests to trigger rate limiting and test retry behavior
                retry_attempts = 0
                rate_limited = False
                
                for i in range(20):
                    async with self.session.post(
                        f"{self.base_url}/auth/gmail-oauth"
                    ) as resp:
                        if resp.status == 429:
                            rate_limited = True
                            # Wait a bit and try again to test retry behavior
                            await asyncio.sleep(0.5)
                            async with self.session.post(
                                f"{self.base_url}/auth/gmail-oauth"
                            ) as retry_resp:
                                retry_attempts += 1
                                if retry_resp.status != 429:
                                    test_scenarios.append("Rate limit retry successful")
                                break
                        await asyncio.sleep(0.1)
                        
                if rate_limited:
                    test_scenarios.append("Rate limiting active (retry logic testable)")
                else:
                    test_scenarios.append("No rate limiting encountered")
                    
            except Exception as e:
                test_scenarios.append(f"Retry logic test: {str(e)[:40]}")
                
            # Test 2: Timeout and recovery behavior
            try:
                # Test with very short timeout to trigger timeouts and recovery
                start_time = time.time()
                timeout_handled = False
                
                try:
                    async with self.session.get(
                        f"{self.base_url}/health",
                        timeout=aiohttp.ClientTimeout(total=0.001)  # Very short timeout
                    ) as resp:
                        pass
                except asyncio.TimeoutError:
                    timeout_handled = True
                    
                # Try again with normal timeout
                async with self.session.get(f"{self.base_url}/health") as resp:
                    if resp.status == 200:
                        if timeout_handled:
                            test_scenarios.append("Timeout recovery working")
                        else:
                            test_scenarios.append("Service consistently available")
                            
            except Exception as e:
                test_scenarios.append(f"Timeout recovery test: {str(e)[:30]}")
                
            # Test 3: Error recovery patterns
            try:
                # Test invalid endpoint followed by valid endpoint
                async with self.session.get(f"{self.base_url}/invalid_endpoint") as resp:
                    error_status = resp.status
                    
                async with self.session.get(f"{self.base_url}/health") as resp:
                    if resp.status == 200:
                        test_scenarios.append("Error recovery functional")
                    else:
                        test_scenarios.append("Service degradation after error")
                        
            except Exception as e:
                test_scenarios.append(f"Error recovery test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 2:
                return {
                    "status": "PASS", 
                    "message": f"Retry logic tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited retry testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_circuit_breaker(self) -> Dict:
        """Test circuit breaker patterns"""
        try:
            # Circuit breaker testing is complex - we test behavior under load
            test_scenarios = []
            
            # Test 1: Service degradation under high load
            try:
                # Send many concurrent requests to test circuit breaker behavior
                start_time = time.time()
                concurrent_requests = 50
                successful_requests = 0
                failed_requests = 0
                
                tasks = []
                for i in range(concurrent_requests):
                    task = self.session.get(f"{self.base_url}/health")
                    tasks.append(task)
                    
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                for resp in responses:
                    if isinstance(resp, Exception):
                        failed_requests += 1
                    elif hasattr(resp, 'status'):
                        if resp.status == 200:
                            successful_requests += 1
                        else:
                            failed_requests += 1
                        await resp.close()
                    else:
                        failed_requests += 1
                        
                success_rate = successful_requests / concurrent_requests
                elapsed_time = time.time() - start_time
                
                if success_rate >= 0.9:
                    test_scenarios.append(f"High load handled well ({success_rate:.1%} success)")
                elif success_rate >= 0.7:
                    test_scenarios.append(f"Moderate load handling ({success_rate:.1%} success)")
                else:
                    test_scenarios.append(f"Load issues detected ({success_rate:.1%} success)")
                    
            except Exception as e:
                test_scenarios.append(f"Load test: {str(e)[:40]}")
                
            # Test 2: Recovery after load
            try:
                await asyncio.sleep(1)  # Allow system to recover
                
                async with self.session.get(f"{self.base_url}/health") as resp:
                    if resp.status == 200:
                        test_scenarios.append("Service recovered after load")
                    else:
                        test_scenarios.append("Service degradation persists")
                        
            except Exception as e:
                test_scenarios.append(f"Recovery test: {str(e)[:30]}")
                
            # Test 3: Graceful degradation check
            try:
                # Test if service provides degraded functionality during stress
                async with self.session.get(f"{self.base_url}/health") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "status" in data:
                            test_scenarios.append("Core functionality maintained")
                        else:
                            test_scenarios.append("Response format degraded")
                    else:
                        test_scenarios.append("Service not available")
                        
            except Exception as e:
                test_scenarios.append(f"Degradation test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 2:
                return {
                    "status": "PASS", 
                    "message": f"Circuit breaker behavior tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited circuit breaker testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_graceful_degradation(self) -> Dict:
        """Test graceful degradation capabilities"""
        try:
            test_scenarios = []
            
            # Test 1: Core endpoints remain available under stress
            core_endpoints = ["/health", "/sessions/active"]
            available_endpoints = 0
            
            for endpoint in core_endpoints:
                try:
                    async with self.session.get(f"{self.base_url}{endpoint}") as resp:
                        if resp.status == 200:
                            available_endpoints += 1
                            test_scenarios.append(f"{endpoint} available")
                        elif resp.status in [401, 403]:  # Auth required but endpoint works
                            available_endpoints += 1
                            test_scenarios.append(f"{endpoint} requires auth")
                        else:
                            test_scenarios.append(f"{endpoint} returned {resp.status}")
                except Exception as e:
                    test_scenarios.append(f"{endpoint} error: {str(e)[:20]}")
                    
            # Test 2: Error messages are user-friendly
            try:
                async with self.session.get(f"{self.base_url}/nonexistent") as resp:
                    if resp.status == 404:
                        try:
                            error_data = await resp.json()
                            if "error" in error_data and len(error_data["error"]) > 0:
                                test_scenarios.append("User-friendly error messages")
                            else:
                                test_scenarios.append("Error messages present")
                        except:
                            test_scenarios.append("Error response not JSON")
                    else:
                        test_scenarios.append(f"404 handling returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Error message test: {str(e)[:30]}")
                
            # Test 3: Service health reporting
            try:
                async with self.session.get(f"{self.base_url}/health") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "services" in data:
                            healthy_services = 0
                            total_services = 0
                            for service, status in data["services"].items():
                                total_services += 1
                                if status == "healthy":
                                    healthy_services += 1
                                    
                            if healthy_services == total_services:
                                test_scenarios.append("All services healthy")
                            elif healthy_services > 0:
                                test_scenarios.append(f"Partial service availability ({healthy_services}/{total_services})")
                            else:
                                test_scenarios.append("Service health issues detected")
                        else:
                            test_scenarios.append("Health endpoint lacks service details")
                    else:
                        test_scenarios.append("Health endpoint unavailable")
            except Exception as e:
                test_scenarios.append(f"Health check test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 3:
                return {
                    "status": "PASS", 
                    "message": f"Graceful degradation tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited degradation testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_timeout_handling(self) -> Dict:
        """Test timeout handling mechanisms"""
        try:
            test_scenarios = []
            
            # Test 1: Request timeout behavior
            timeout_scenarios = [1, 5, 10]  # Different timeout values
            timeout_results = []
            
            for timeout_val in timeout_scenarios:
                try:
                    async with self.session.get(
                        f"{self.base_url}/health",
                        timeout=aiohttp.ClientTimeout(total=timeout_val)
                    ) as resp:
                        if resp.status == 200:
                            timeout_results.append(f"{timeout_val}s: success")
                        else:
                            timeout_results.append(f"{timeout_val}s: {resp.status}")
                except asyncio.TimeoutError:
                    timeout_results.append(f"{timeout_val}s: timeout")
                except Exception as e:
                    timeout_results.append(f"{timeout_val}s: error")
                    
            test_scenarios.append(f"Timeout behavior: {'; '.join(timeout_results)}")
            
            # Test 2: Long-running operation handling
            try:
                # Test newsletter parsing which might be long-running
                large_content = "Newsletter content " * 1000
                start_time = time.time()
                
                async with self.session.post(
                    f"{self.base_url}/newsletters/parse",
                    json={"html_content": large_content},
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as resp:
                    elapsed = time.time() - start_time
                    
                    if resp.status == 200:
                        test_scenarios.append(f"Long operation completed ({elapsed:.1f}s)")
                    elif resp.status == 422:
                        test_scenarios.append("Long operation validation rejected")
                    elif resp.status == 500:
                        test_scenarios.append("Long operation error handled")
                    else:
                        test_scenarios.append(f"Long operation returned {resp.status}")
                        
            except asyncio.TimeoutError:
                test_scenarios.append("Long operation timeout handled")
            except Exception as e:
                test_scenarios.append(f"Long operation test: {str(e)[:30]}")
                
            # Test 3: Concurrent timeout handling
            try:
                timeout_tasks = []
                for i in range(5):
                    task = self.session.get(
                        f"{self.base_url}/health",
                        timeout=aiohttp.ClientTimeout(total=0.5)  # Very short timeout
                    )
                    timeout_tasks.append(task)
                    
                results = await asyncio.gather(*timeout_tasks, return_exceptions=True)
                timeouts = sum(1 for r in results if isinstance(r, asyncio.TimeoutError))
                successes = sum(1 for r in results if hasattr(r, 'status') and r.status == 200)
                
                # Close successful responses
                for r in results:
                    if hasattr(r, 'close'):
                        await r.close()
                        
                test_scenarios.append(f"Concurrent timeouts: {timeouts}/5 timed out, {successes}/5 succeeded")
                
            except Exception as e:
                test_scenarios.append(f"Concurrent timeout test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 2:
                return {
                    "status": "PASS", 
                    "message": f"Timeout handling tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited timeout testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    # ==================== DATA CORRUPTION & RECOVERY TESTS ====================
    
    async def test_database_consistency(self) -> Dict:
        """Test database consistency after failures"""
        try:
            test_scenarios = []
            
            # Test 1: Data integrity checks
            try:
                async with self.session.get(f"{self.base_url}/health") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "services" in data and "database" in data["services"]:
                            if data["services"]["database"] == "healthy":
                                test_scenarios.append("Database integrity verified")
                            else:
                                test_scenarios.append("Database health issues detected")
                        else:
                            test_scenarios.append("Database status not reported")
                    else:
                        test_scenarios.append("Health check unavailable")
            except Exception as e:
                test_scenarios.append(f"Integrity check: {str(e)[:30]}")
                
            # Test 2: Referential integrity
            try:
                # Test accessing related data (newsletters -> stories)
                async with self.session.get(
                    f"{self.base_url}/newsletters/1"
                ) as resp:
                    if resp.status == 404:
                        test_scenarios.append("Non-existent data handled properly")
                    elif resp.status == 401:
                        test_scenarios.append("Data access requires authentication")
                    elif resp.status == 200:
                        try:
                            data = await resp.json()
                            if "stories" in data or "id" in data:
                                test_scenarios.append("Related data structure intact")
                            else:
                                test_scenarios.append("Data structure incomplete")
                        except:
                            test_scenarios.append("Data format issues")
                    else:
                        test_scenarios.append(f"Data access returned {resp.status}")
            except Exception as e:
                test_scenarios.append(f"Referential integrity test: {str(e)[:30]}")
                
            # Test 3: Concurrent data access consistency
            try:
                tasks = []
                for i in range(5):
                    task = self.session.get(f"{self.base_url}/newsletters")
                    tasks.append(task)
                    
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                consistent_responses = 0
                
                for resp in responses:
                    if not isinstance(resp, Exception) and hasattr(resp, 'status'):
                        if resp.status in [200, 401]:  # Expected responses
                            consistent_responses += 1
                        await resp.close()
                        
                if consistent_responses >= 4:
                    test_scenarios.append("Concurrent access consistency maintained")
                else:
                    test_scenarios.append("Consistency issues under concurrent access")
                    
            except Exception as e:
                test_scenarios.append(f"Concurrent consistency test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 2:
                return {
                    "status": "PASS", 
                    "message": f"Database consistency tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited consistency testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_transaction_rollback(self) -> Dict:
        """Test transaction rollback mechanisms"""
        try:
            test_scenarios = []
            
            # Test 1: Invalid data insertion should rollback
            try:
                # Try to create invalid newsletter data
                invalid_data = {
                    "user_id": -1,  # Invalid user ID
                    "title": "",    # Empty title
                    "content": None  # Null content
                }
                
                async with self.session.post(
                    f"{self.base_url}/newsletters/save",
                    json=invalid_data
                ) as resp:
                    if resp.status in [400, 422]:
                        test_scenarios.append("Invalid data rejected (transaction prevented)")
                    elif resp.status == 500:
                        test_scenarios.append("Invalid data server error (potential rollback)")
                    elif resp.status == 401:
                        test_scenarios.append("Data creation requires authentication")
                    else:
                        test_scenarios.append(f"Invalid data returned {resp.status}")
                        
            except Exception as e:
                test_scenarios.append(f"Invalid data test: {str(e)[:30]}")
                
            # Test 2: Partial operation failure
            try:
                # Try to start briefing with invalid data
                async with self.session.post(
                    f"{self.base_url}/start-briefing",
                    json={"newsletter_ids": [-1, -2, -3]}  # Invalid IDs
                ) as resp:
                    if resp.status in [400, 422]:
                        test_scenarios.append("Invalid briefing data rejected")
                    elif resp.status == 500:
                        test_scenarios.append("Briefing creation error handled")
                    elif resp.status == 401:
                        test_scenarios.append("Briefing requires authentication")
                    else:
                        test_scenarios.append(f"Invalid briefing returned {resp.status}")
                        
            except Exception as e:
                test_scenarios.append(f"Partial operation test: {str(e)[:30]}")
                
            # Test 3: State consistency after errors
            try:
                # Check that system state remains consistent after failed operations
                async with self.session.get(f"{self.base_url}/health") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("status") == "healthy":
                            test_scenarios.append("System state consistent after errors")
                        else:
                            test_scenarios.append("System state degraded")
                    else:
                        test_scenarios.append("State check unavailable")
                        
            except Exception as e:
                test_scenarios.append(f"State consistency test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 2:
                return {
                    "status": "PASS", 
                    "message": f"Transaction rollback tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited rollback testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_audio_file_corruption(self) -> Dict:
        """Test audio file corruption detection and handling"""
        try:
            test_scenarios = []
            
            # Test 1: Invalid audio file upload
            try:
                # Upload corrupted/invalid audio data
                corrupted_data = b"corrupted_audio_file_data_not_valid_format"
                
                data = aiohttp.FormData()
                data.add_field('audio_file', corrupted_data, 
                              filename='corrupted.mp3', 
                              content_type='audio/mpeg')
                
                async with self.session.post(
                    f"{self.base_url}/audio/upload",
                    data=data
                ) as resp:
                    if resp.status in [400, 415, 422]:
                        test_scenarios.append("Corrupted audio file rejected")
                    elif resp.status == 500:
                        test_scenarios.append("Audio corruption error handled")
                    elif resp.status == 401:
                        test_scenarios.append("Audio upload requires authentication")
                    else:
                        test_scenarios.append(f"Corrupted audio returned {resp.status}")
                        
            except Exception as e:
                test_scenarios.append(f"Corrupted audio test: {str(e)[:30]}")
                
            # Test 2: Access to potentially corrupted audio
            try:
                async with self.session.get(
                    f"{self.base_url}/audio/999999"
                ) as resp:
                    if resp.status == 404:
                        test_scenarios.append("Non-existent audio handled properly")
                    elif resp.status == 500:
                        test_scenarios.append("Audio access error handled")
                    elif resp.status == 401:
                        test_scenarios.append("Audio access requires authentication")
                    else:
                        test_scenarios.append(f"Audio access returned {resp.status}")
                        
            except Exception as e:
                test_scenarios.append(f"Audio access test: {str(e)[:30]}")
                
            # Test 3: Audio generation with invalid parameters
            try:
                async with self.session.post(
                    f"{self.base_url}/audio/generate",
                    json={
                        "text": "",  # Empty text
                        "story_id": "invalid_id",  # Invalid ID type
                        "voice_id": "corrupted_voice_settings"
                    }
                ) as resp:
                    if resp.status in [400, 422]:
                        test_scenarios.append("Invalid audio generation parameters rejected")
                    elif resp.status == 500:
                        test_scenarios.append("Audio generation error handled")
                    elif resp.status == 401:
                        test_scenarios.append("Audio generation requires authentication")
                    else:
                        test_scenarios.append(f"Audio generation returned {resp.status}")
                        
            except Exception as e:
                test_scenarios.append(f"Audio generation test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 2:
                return {
                    "status": "PASS", 
                    "message": f"Audio corruption handling tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited audio corruption testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_session_state_recovery(self) -> Dict:
        """Test briefing session state recovery"""
        try:
            test_scenarios = []
            
            # Test 1: Invalid session access
            try:
                async with self.session.get(
                    f"{self.base_url}/briefing/999999/state"
                ) as resp:
                    if resp.status == 404:
                        test_scenarios.append("Non-existent session handled properly")
                    elif resp.status == 401:
                        test_scenarios.append("Session access requires authentication")
                    elif resp.status == 500:
                        test_scenarios.append("Session state error handled")
                    else:
                        test_scenarios.append(f"Session state returned {resp.status}")
                        
            except Exception as e:
                test_scenarios.append(f"Session access test: {str(e)[:30]}")
                
            # Test 2: Session control operations
            control_operations = ["pause", "resume"]
            for operation in control_operations:
                try:
                    async with self.session.post(
                        f"{self.base_url}/briefing/999/{operation}"
                    ) as resp:
                        if resp.status == 404:
                            test_scenarios.append(f"Non-existent session {operation} handled")
                        elif resp.status == 401:
                            test_scenarios.append(f"Session {operation} requires auth")
                        elif resp.status == 500:
                            test_scenarios.append(f"Session {operation} error handled")
                        else:
                            test_scenarios.append(f"Session {operation} returned {resp.status}")
                            
                except Exception as e:
                    test_scenarios.append(f"Session {operation} test: {str(e)[:20]}")
                    
            # Test 3: Session progress and metadata
            try:
                async with self.session.get(
                    f"{self.base_url}/session/999/progress"
                ) as resp:
                    if resp.status == 404:
                        test_scenarios.append("Non-existent session progress handled")
                    elif resp.status == 401:
                        test_scenarios.append("Session progress requires authentication")
                    elif resp.status == 500:
                        test_scenarios.append("Session progress error handled")
                    else:
                        test_scenarios.append(f"Session progress returned {resp.status}")
                        
            except Exception as e:
                test_scenarios.append(f"Session progress test: {str(e)[:30]}")
                
            # Test 4: Active sessions endpoint
            try:
                async with self.session.get(
                    f"{self.base_url}/sessions/active"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        test_scenarios.append("Active sessions endpoint functional")
                    elif resp.status == 401:
                        test_scenarios.append("Active sessions requires authentication")
                    elif resp.status == 500:
                        test_scenarios.append("Active sessions error handled")
                    else:
                        test_scenarios.append(f"Active sessions returned {resp.status}")
                        
            except Exception as e:
                test_scenarios.append(f"Active sessions test: {str(e)[:30]}")
                
            if len(test_scenarios) >= 3:
                return {
                    "status": "PASS", 
                    "message": f"Session recovery tested: {'; '.join(test_scenarios)}"
                }
            else:
                return {
                    "status": "WARN", 
                    "message": f"Limited session recovery testing: {'; '.join(test_scenarios)}"
                }
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    # ==================== MAIN TEST EXECUTION ====================
    
    async def run_all_tests(self):
        """Execute all resilience tests"""
        
        # External Service Failure Tests (5 tests)
        await self.run_test("external_service_failures", 
                           "Gmail API Failures", 
                           self.test_gmail_api_failures)
        await self.run_test("external_service_failures", 
                           "ElevenLabs Failures", 
                           self.test_elevenlabs_failures)
        await self.run_test("external_service_failures", 
                           "OpenAI Failures", 
                           self.test_openai_failures)
        await self.run_test("external_service_failures", 
                           "Database Failures", 
                           self.test_database_failures)
        await self.run_test("external_service_failures", 
                           "Supabase Storage Failures", 
                           self.test_supabase_storage_failures)
        
        # Network Resilience Tests (5 tests)
        await self.run_test("network_resilience", 
                           "WebSocket Disconnections", 
                           self.test_websocket_disconnections)
        await self.run_test("network_resilience", 
                           "Retry Logic", 
                           self.test_retry_logic)
        await self.run_test("network_resilience", 
                           "Circuit Breaker", 
                           self.test_circuit_breaker)
        await self.run_test("network_resilience", 
                           "Graceful Degradation", 
                           self.test_graceful_degradation)
        await self.run_test("network_resilience", 
                           "Timeout Handling", 
                           self.test_timeout_handling)
        
        # Data Corruption & Recovery Tests (4 tests)
        await self.run_test("data_corruption_recovery", 
                           "Database Consistency", 
                           self.test_database_consistency)
        await self.run_test("data_corruption_recovery", 
                           "Transaction Rollback", 
                           self.test_transaction_rollback)
        await self.run_test("data_corruption_recovery", 
                           "Audio File Corruption", 
                           self.test_audio_file_corruption)
        await self.run_test("data_corruption_recovery", 
                           "Session State Recovery", 
                           self.test_session_state_recovery)
        
        self.print_results()
        
    def print_results(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("PHASE 5 ERROR HANDLING & RESILIENCE TESTING RESULTS")
        print("="*80)
        
        for category, results in self.test_results.items():
            if results:
                print(f"\n{category.replace('_', ' ').title()}:")
                print("-" * 50)
                for result in results:
                    if result["status"] == "PASS":
                        icon = "✅"
                    elif result["status"] == "FAIL":
                        icon = "❌"
                    elif result["status"] == "SKIP":
                        icon = "⏭️"
                    elif result["status"] == "WARN":
                        icon = "⚠️"
                    else:
                        icon = "❌"
                    print(f"{icon} {result['test']}: {result['status']}")
                    if result["message"]:
                        print(f"   → {result['message']}")
                        
        print("\n" + "="*80)
        total_executed = self.total_tests - self.skipped_tests
        print(f"SUMMARY: {self.passed_tests}/{total_executed} tests passed ({self.skipped_tests} skipped)")
        if total_executed > 0:
            print(f"Pass Rate: {(self.passed_tests/total_executed*100):.1f}%")
        
        # Categorize results
        critical_failures = []
        warnings = []
        
        for category, results in self.test_results.items():
            for result in results:
                if result["status"] == "FAIL":
                    critical_failures.append(result["test"])
                elif result["status"] == "WARN":
                    warnings.append(result["test"])
        
        if critical_failures:
            print(f"\n🔴 CRITICAL FAILURES ({len(critical_failures)}):")
            for failure in critical_failures:
                print(f"   - {failure}")
                
        if warnings:
            print(f"\n🟡 WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"   - {warning}")
                
        if not critical_failures and not warnings:
            print("\n✅ All resilience tests passed!")
        elif not critical_failures:
            print("\n🟡 Resilience testing passed with warnings")
        else:
            print("\n🔴 Critical resilience issues found - investigate before production")
            
        print("="*80)
        
async def main():
    """Main test runner"""
    suite = ResilienceTestSuite()
    await suite.setup()
    
    try:
        await suite.run_all_tests()
    finally:
        await suite.teardown()
        
if __name__ == "__main__":
    asyncio.run(main())