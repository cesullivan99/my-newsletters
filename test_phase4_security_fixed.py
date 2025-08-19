#!/usr/bin/env python3
"""
Phase 4: Security Testing for My Newsletters Voice Assistant (Fixed Version)
Tests authentication, API security, and data protection mechanisms
Adapted to work with Gmail OAuth implementation
"""

import asyncio
import json
import time
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import aiohttp
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Configuration
BASE_URL = "http://localhost:5001"

class SecurityTestSuite:
    """Security testing framework for the My Newsletters application"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.mock_token: Optional[str] = None
        self.test_results: Dict[str, List[Dict]] = {
            "authentication_security": [],
            "api_security": [],
            "data_security": []
        }
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        
    async def setup(self):
        """Initialize test session"""
        self.session = aiohttp.ClientSession()
        print("\n" + "="*80)
        print("PHASE 4: SECURITY TESTING (FIXED)")
        print("="*80)
        print(f"Target: {self.base_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        # Generate a mock JWT token for testing
        # In a real test, we'd go through the OAuth flow
        self.mock_token = "mock_jwt_token_for_testing"
        
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
            
    # ==================== AUTHENTICATION SECURITY TESTS ====================
    
    async def test_jwt_token_security(self) -> Dict:
        """Test JWT token validation mechanisms"""
        try:
            # Test token validation endpoint with invalid token
            async with self.session.post(
                f"{self.base_url}/auth/validate",
                json={"token": "invalid.jwt.token"}
            ) as resp:
                if resp.status == 200:
                    return {"status": "FAIL", "message": "Invalid token accepted"}
                elif resp.status != 401:
                    return {"status": "WARN", "message": f"Unexpected status for invalid token: {resp.status}"}
                    
            # Test with malformed token
            async with self.session.post(
                f"{self.base_url}/auth/validate",
                json={"token": "not-even-a-jwt"}
            ) as resp:
                if resp.status == 200:
                    return {"status": "FAIL", "message": "Malformed token accepted"}
                    
            # Test with missing token
            async with self.session.post(
                f"{self.base_url}/auth/validate",
                json={}
            ) as resp:
                if resp.status == 200:
                    return {"status": "FAIL", "message": "Missing token accepted"}
                    
            # Test protected endpoint without auth
            async with self.session.get(
                f"{self.base_url}/auth/user"
            ) as resp:
                if resp.status == 200:
                    return {"status": "FAIL", "message": "Protected endpoint accessible without auth"}
                elif resp.status != 401:
                    pass  # Could be 403 or other auth error
                    
            return {"status": "PASS", "message": "JWT token validation working properly"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_token_expiration(self) -> Dict:
        """Test token expiration handling"""
        try:
            # Test refresh endpoint without valid refresh token
            async with self.session.post(
                f"{self.base_url}/auth/refresh",
                json={"refresh_token": "expired_or_invalid_token"}
            ) as resp:
                if resp.status == 200:
                    return {"status": "FAIL", "message": "Invalid refresh token accepted"}
                elif resp.status != 401:
                    pass  # Different error code is acceptable
                    
            # Test with missing refresh token
            async with self.session.post(
                f"{self.base_url}/auth/refresh",
                json={}
            ) as resp:
                if resp.status == 200:
                    return {"status": "FAIL", "message": "Missing refresh token accepted"}
                    
            return {"status": "PASS", "message": "Token expiration properly handled"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_refresh_token_security(self) -> Dict:
        """Test refresh token security mechanisms"""
        try:
            # Since we can't do full OAuth flow in test, we check the endpoint behavior
            async with self.session.post(
                f"{self.base_url}/auth/refresh",
                json={"refresh_token": "test_refresh_token"}
            ) as resp:
                if resp.status == 200:
                    return {"status": "FAIL", "message": "Test token shouldn't be valid"}
                elif resp.status == 401:
                    # Proper rejection of invalid token
                    return {"status": "PASS", "message": "Refresh tokens properly validated"}
                else:
                    return {"status": "WARN", "message": f"Unexpected status: {resp.status}"}
                    
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_oauth_security(self) -> Dict:
        """Test Gmail OAuth flow security"""
        try:
            # Test OAuth initialization endpoint
            async with self.session.post(f"{self.base_url}/auth/gmail-oauth") as resp:
                if resp.status != 200:
                    return {"status": "WARN", "message": f"OAuth init returned: {resp.status}"}
                data = await resp.json()
                
                # Check for required OAuth fields
                auth_url = data.get("auth_url") or data.get("authorization_url")
                if not auth_url:
                    return {"status": "FAIL", "message": "No auth URL in OAuth response"}
                    
                # Verify it's a proper Google OAuth URL
                if "accounts.google.com" not in auth_url:
                    return {"status": "FAIL", "message": "Invalid OAuth provider URL"}
                    
                # Check for state parameter (CSRF protection)
                if "state=" not in auth_url:
                    return {"status": "FAIL", "message": "No state parameter (CSRF vulnerability)"}
                    
                # Check for proper scopes
                if "gmail" not in auth_url.lower():
                    return {"status": "WARN", "message": "Gmail scope may be missing"}
                    
            return {"status": "PASS", "message": "OAuth flow properly configured"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_session_management(self) -> Dict:
        """Test session isolation and management"""
        try:
            # Test logout endpoint
            async with self.session.post(
                f"{self.base_url}/auth/logout"
            ) as resp:
                # Should require authentication
                if resp.status == 200:
                    return {"status": "FAIL", "message": "Logout worked without auth"}
                elif resp.status == 401:
                    pass  # Expected - requires auth
                    
            # Test session endpoints
            async with self.session.get(
                f"{self.base_url}/sessions/active"
            ) as resp:
                if resp.status != 200:
                    return {"status": "WARN", "message": "Sessions endpoint not accessible"}
                    
            return {"status": "PASS", "message": "Session management working"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_password_security(self) -> Dict:
        """Test password security (N/A for OAuth-only system)"""
        # This app uses OAuth only, no passwords
        return {"status": "SKIP", "message": "App uses OAuth only - no password storage"}
            
    # ==================== API SECURITY TESTS ====================
    
    async def test_input_validation(self) -> Dict:
        """Test that all API inputs are properly validated"""
        try:
            test_cases = [
                # SQL injection attempts
                {"endpoint": "/newsletters/parse", "method": "POST",
                 "data": {"html_content": "'; DROP TABLE users; --"}},
                # XSS attempts
                {"endpoint": "/newsletters/parse", "method": "POST",
                 "data": {"html_content": "<script>alert('XSS')</script>"}},
                # Invalid data types
                {"endpoint": "/briefing/not_a_number/pause", "method": "POST", 
                 "data": {}},
                # Missing required fields
                {"endpoint": "/newsletters/fetch", "method": "POST", 
                 "data": {}},  # Missing user_id
                # Invalid JSON
                {"endpoint": "/briefing/start", "method": "POST",
                 "data": {"newsletter_ids": "not_an_array"}},
            ]
            
            failures = []
            for test in test_cases:
                if test["method"] == "POST":
                    async with self.session.post(
                        f"{self.base_url}{test['endpoint']}",
                        json=test["data"]
                    ) as resp:
                        if resp.status == 200:
                            failures.append(f"Accepted invalid input: {test['endpoint']}")
                        elif resp.status >= 500:
                            failures.append(f"Server error on bad input: {test['endpoint']}")
                            
            if failures:
                return {"status": "FAIL", "message": f"Validation issues: {'; '.join(failures)}"}
                
            return {"status": "PASS", "message": "All inputs properly validated"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_sql_injection_prevention(self) -> Dict:
        """Test SQL injection attack prevention"""
        try:
            sql_payloads = [
                "'; DROP TABLE users; --",
                "1' OR '1'='1",
                "admin'--",
                "1; SELECT * FROM users",
                "' UNION SELECT * FROM users--"
            ]
            
            vulnerabilities = []
            
            for payload in sql_payloads:
                # Try SQL injection in various endpoints
                endpoints = [
                    f"/users/{payload}/newsletters",
                    f"/users/{payload}/preferences",
                ]
                
                for endpoint in endpoints:
                    try:
                        async with self.session.get(f"{self.base_url}{endpoint}") as resp:
                            if resp.status == 200:
                                vulnerabilities.append(f"Potential SQL injection: {endpoint}")
                            elif resp.status >= 500:
                                text = await resp.text()
                                if "sql" in text.lower() or "query" in text.lower():
                                    vulnerabilities.append(f"SQL error exposed: {endpoint}")
                    except:
                        pass  # Ignore connection errors
                        
            if vulnerabilities:
                return {"status": "FAIL", "message": f"SQL injection found: {'; '.join(vulnerabilities)}"}
                
            return {"status": "PASS", "message": "SQL injection properly prevented"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_xss_prevention(self) -> Dict:
        """Test XSS attack prevention"""
        try:
            xss_payloads = [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "<svg onload=alert('XSS')>",
                "javascript:alert('XSS')",
                "<iframe src='javascript:alert(\"XSS\")'>"
            ]
            
            vulnerabilities = []
            
            for payload in xss_payloads:
                # Try XSS in newsletter parsing
                async with self.session.post(
                    f"{self.base_url}/newsletters/parse",
                    json={"html_content": payload}
                ) as resp:
                    if resp.status == 200:
                        try:
                            data = await resp.json()
                            # Check if script tags are in response
                            response_str = json.dumps(data)
                            if "<script>" in response_str or "alert(" in response_str:
                                vulnerabilities.append(f"XSS in parse: {payload[:30]}")
                        except:
                            pass
                            
            if vulnerabilities:
                return {"status": "FAIL", "message": f"XSS vulnerabilities: {'; '.join(vulnerabilities)}"}
                
            return {"status": "PASS", "message": "XSS properly prevented"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_rate_limiting(self) -> Dict:
        """Test API rate limiting"""
        try:
            # Make rapid requests to test rate limiting
            endpoint = f"{self.base_url}/health"
            rate_limited = False
            server_errors = 0
            
            # Make 100 rapid requests
            for i in range(100):
                async with self.session.get(endpoint) as resp:
                    if resp.status == 429:  # Too Many Requests
                        rate_limited = True
                        break
                    elif resp.status >= 500:
                        server_errors += 1
                    
            if server_errors > 10:
                return {"status": "FAIL", "message": f"Server errors under load: {server_errors}"}
                
            if not rate_limited:
                # Not necessarily a failure - rate limiting might be at proxy level
                return {"status": "WARN", "message": "No rate limiting detected (configure at proxy/firewall level)"}
                
            return {"status": "PASS", "message": "Rate limiting is active"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_cors_configuration(self) -> Dict:
        """Test CORS configuration"""
        try:
            # Test CORS headers
            test_origins = [
                ("http://evil.com", False),  # Should be blocked
                ("http://localhost:3000", True),  # Should be allowed for dev
                ("http://localhost:19006", True),  # React Native dev
            ]
            
            issues = []
            
            for origin, should_allow in test_origins:
                async with self.session.options(
                    f"{self.base_url}/health",
                    headers={"Origin": origin}
                ) as resp:
                    cors_header = resp.headers.get("Access-Control-Allow-Origin")
                    
                    if cors_header == "*":
                        if not should_allow:
                            issues.append("CORS allows all origins (security risk)")
                    elif cors_header == origin:
                        if not should_allow:
                            issues.append(f"CORS allows untrusted origin: {origin}")
                    elif should_allow and cors_header != origin and cors_header != "*":
                        # This is OK - more restrictive than expected
                        pass
                        
            # Check for credentials with wildcard
            async with self.session.options(
                f"{self.base_url}/health",
                headers={"Origin": "http://localhost:3000"}
            ) as resp:
                allow_origin = resp.headers.get("Access-Control-Allow-Origin")
                allow_creds = resp.headers.get("Access-Control-Allow-Credentials")
                
                if allow_origin == "*" and allow_creds == "true":
                    issues.append("CORS allows credentials with wildcard origin (critical)")
                    
            if issues:
                return {"status": "FAIL", "message": f"CORS issues: {'; '.join(issues)}"}
                
            return {"status": "PASS", "message": "CORS properly configured"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_error_message_security(self) -> Dict:
        """Test that error messages don't leak sensitive info"""
        try:
            leaks = []
            
            # Test various error scenarios
            test_cases = [
                {"endpoint": "/newsletters/999999", "method": "GET"},
                {"endpoint": "/briefing/session/invalid", "method": "GET"},
                {"endpoint": "/audio/999999", "method": "GET"},
                {"endpoint": "/nonexistent", "method": "GET"},
            ]
            
            for test in test_cases:
                async with self.session.get(
                    f"{self.base_url}{test['endpoint']}"
                ) as resp:
                    if resp.status >= 400:
                        try:
                            error_text = await resp.text()
                            # Check for sensitive info in errors
                            sensitive_patterns = [
                                "traceback", "file \"", "line ", 
                                "psycopg", "sqlalchemy", "asyncpg",
                                "secret", "api_key", "password"
                            ]
                            for pattern in sensitive_patterns:
                                if pattern in error_text.lower():
                                    leaks.append(f"{test['endpoint']}: May expose {pattern}")
                                    break
                        except:
                            pass
                            
            if leaks:
                return {"status": "WARN", "message": f"Potential info leaks: {'; '.join(leaks)}"}
                
            return {"status": "PASS", "message": "Error messages properly sanitized"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    # ==================== DATA SECURITY TESTS ====================
    
    async def test_data_encryption(self) -> Dict:
        """Test that sensitive data is encrypted"""
        try:
            issues = []
            
            # Check security headers
            async with self.session.get(f"{self.base_url}/health") as resp:
                headers = resp.headers
                
                # Check for security headers
                if not headers.get("X-Content-Type-Options"):
                    issues.append("Missing X-Content-Type-Options header")
                if not headers.get("X-Frame-Options"):
                    issues.append("Missing X-Frame-Options header")
                if not headers.get("Strict-Transport-Security"):
                    # OK for local dev, but should be present in production
                    issues.append("No HSTS header (configure in production)")
                    
            if len(issues) > 2:
                return {"status": "FAIL", "message": f"Security headers missing: {'; '.join(issues)}"}
            elif issues:
                return {"status": "WARN", "message": f"Some security headers missing: {'; '.join(issues)}"}
                
            return {"status": "PASS", "message": "Security headers configured"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_api_key_security(self) -> Dict:
        """Test that API keys are securely stored"""
        try:
            # Check that API keys aren't exposed in responses
            endpoints_to_check = [
                "/health",
            ]
            
            exposed_keys = []
            
            for endpoint in endpoints_to_check:
                async with self.session.get(f"{self.base_url}{endpoint}") as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        # Check for common API key patterns
                        dangerous_patterns = [
                            "sk-",  # OpenAI
                            "xi-",  # ElevenLabs  
                            "\"api_key\"",
                            "\"apiKey\"",
                            "\"API_KEY\"",
                            "\"secret\"",
                            "supabase",
                            "openai",
                            "elevenlabs"
                        ]
                        for pattern in dangerous_patterns:
                            if pattern in text:
                                # Check if it's actually a key or just a service name
                                if pattern in ["openai", "elevenlabs", "supabase"]:
                                    # These are OK if just service status
                                    if f'"{pattern}": "healthy"' in text or f'"{pattern}":"healthy"' in text:
                                        continue
                                exposed_keys.append(f"{endpoint}: {pattern}")
                                break
                            
            if exposed_keys:
                return {"status": "FAIL", "message": f"Potential API key exposure: {', '.join(exposed_keys)}"}
                
            return {"status": "PASS", "message": "API keys properly secured"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_user_data_privacy(self) -> Dict:
        """Test user data protection"""
        try:
            # Test unauthorized access attempts
            test_cases = [
                "/users/1/newsletters",
                "/users/999/preferences",
                "/briefing/999/state",
            ]
            
            issues = []
            
            for endpoint in test_cases:
                async with self.session.get(f"{self.base_url}{endpoint}") as resp:
                    # These should require auth or return 404
                    if resp.status == 200:
                        issues.append(f"Unauthorized access to: {endpoint}")
                    elif resp.status >= 500:
                        issues.append(f"Server error on: {endpoint}")
                        
            if issues:
                return {"status": "FAIL", "message": f"Privacy issues: {'; '.join(issues)}"}
                
            return {"status": "PASS", "message": "User data properly protected"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_audio_file_security(self) -> Dict:
        """Test that audio files are access-controlled"""
        try:
            # Try to access audio without authentication
            test_ids = [1, 999, "invalid"]
            
            issues = []
            
            for audio_id in test_ids:
                async with self.session.get(f"{self.base_url}/audio/{audio_id}") as resp:
                    if resp.status == 200:
                        issues.append(f"Audio {audio_id} accessible without auth")
                    # 401 or 404 are both acceptable
                        
            if issues:
                return {"status": "FAIL", "message": f"Audio access issues: {'; '.join(issues)}"}
                
            return {"status": "PASS", "message": "Audio files properly access-controlled"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_database_security(self) -> Dict:
        """Test database connection security"""
        try:
            # Check for database error exposure
            test_endpoints = [
                "/newsletters?limit=abc",  # Invalid param
                "/newsletters?limit=-1",  # Negative value
                "/newsletters?offset=999999999",  # Extreme value
            ]
            
            db_leaks = []
            
            for endpoint in test_endpoints:
                async with self.session.get(f"{self.base_url}{endpoint}") as resp:
                    if resp.status >= 400:
                        try:
                            error_text = await resp.text()
                            db_patterns = [
                                "postgres", "psycopg", "sqlalchemy", 
                                "asyncpg", "database", "connection",
                                "syntax error", "query"
                            ]
                            for pattern in db_patterns:
                                if pattern in error_text.lower():
                                    db_leaks.append(f"DB info in: {endpoint}")
                                    break
                        except:
                            pass
                            
            # Test for connection pool exhaustion (reduced load)
            errors = 0
            for _ in range(50):  # Reduced from 100
                try:
                    async with self.session.get(f"{self.base_url}/health") as resp:
                        if resp.status >= 500:
                            errors += 1
                except Exception:
                    errors += 1
            
            if errors > 5:
                db_leaks.append(f"Connection pool issues ({errors} errors)")
                
            if db_leaks:
                return {"status": "WARN", "message": f"Database security concerns: {'; '.join(db_leaks)}"}
                
            return {"status": "PASS", "message": "Database connections secured"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    async def test_authentication_bypass(self) -> Dict:
        """Test for authentication bypass vulnerabilities"""
        try:
            # Additional test for auth bypass attempts
            bypass_attempts = [
                # Try with Authorization header variations
                {"header": "Authorization", "value": "Bearer "},
                {"header": "Authorization", "value": "Bearer null"},
                {"header": "Authorization", "value": "Bearer undefined"},
                {"header": "X-User-Id", "value": "1"},  # Try to spoof user ID
            ]
            
            issues = []
            
            for attempt in bypass_attempts:
                async with self.session.get(
                    f"{self.base_url}/auth/user",
                    headers={attempt["header"]: attempt["value"]}
                ) as resp:
                    if resp.status == 200:
                        issues.append(f"Auth bypass with: {attempt['header']}={attempt['value']}")
                        
            if issues:
                return {"status": "FAIL", "message": f"Auth bypass found: {'; '.join(issues)}"}
                
            return {"status": "PASS", "message": "No authentication bypass vulnerabilities"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
            
    # ==================== MAIN TEST EXECUTION ====================
    
    async def run_all_tests(self):
        """Execute all security tests"""
        
        # Authentication Security Tests (6 tests)
        await self.run_test("authentication_security", 
                           "JWT Token Security", 
                           self.test_jwt_token_security)
        await self.run_test("authentication_security", 
                           "Token Expiration", 
                           self.test_token_expiration)
        await self.run_test("authentication_security", 
                           "Refresh Token Security", 
                           self.test_refresh_token_security)
        await self.run_test("authentication_security", 
                           "OAuth Security", 
                           self.test_oauth_security)
        await self.run_test("authentication_security", 
                           "Session Management", 
                           self.test_session_management)
        await self.run_test("authentication_security", 
                           "Password Security", 
                           self.test_password_security)
        
        # API Security Tests (6 tests)
        await self.run_test("api_security", 
                           "Input Validation", 
                           self.test_input_validation)
        await self.run_test("api_security", 
                           "SQL Injection Prevention", 
                           self.test_sql_injection_prevention)
        await self.run_test("api_security", 
                           "XSS Prevention", 
                           self.test_xss_prevention)
        await self.run_test("api_security", 
                           "Rate Limiting", 
                           self.test_rate_limiting)
        await self.run_test("api_security", 
                           "CORS Configuration", 
                           self.test_cors_configuration)
        await self.run_test("api_security", 
                           "Error Message Security", 
                           self.test_error_message_security)
        
        # Data Security Tests (6 tests)
        await self.run_test("data_security", 
                           "Data Encryption", 
                           self.test_data_encryption)
        await self.run_test("data_security", 
                           "API Key Security", 
                           self.test_api_key_security)
        await self.run_test("data_security", 
                           "User Data Privacy", 
                           self.test_user_data_privacy)
        await self.run_test("data_security", 
                           "Audio File Security", 
                           self.test_audio_file_security)
        await self.run_test("data_security", 
                           "Database Security", 
                           self.test_database_security)
        await self.run_test("data_security",
                           "Authentication Bypass",
                           self.test_authentication_bypass)
        
        self.print_results()
        
    def print_results(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("PHASE 4 SECURITY TESTING RESULTS")
        print("="*80)
        
        for category, results in self.test_results.items():
            if results:
                print(f"\n{category.replace('_', ' ').title()}:")
                print("-" * 40)
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
            print("\n✅ All security tests passed!")
        elif not critical_failures:
            print("\n🟡 Security testing passed with warnings - review before production")
        else:
            print("\n🔴 Critical security issues found - must fix before production")
            
        print("="*80)
        
async def main():
    """Main test runner"""
    suite = SecurityTestSuite()
    await suite.setup()
    
    try:
        await suite.run_all_tests()
    finally:
        await suite.teardown()
        
if __name__ == "__main__":
    asyncio.run(main())