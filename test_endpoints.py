#!/usr/bin/env python
"""
Quick endpoint verification script for Phase 1 API implementation.
Tests that all 24 missing endpoints are now properly implemented and responding.
"""

import asyncio
import json
import sys
from typing import Dict, List

import httpx


class EndpointTester:
    """Test suite for verifying API endpoint implementation."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.results: List[Dict] = []
        
    async def test_endpoint(self, method: str, endpoint: str, expected_status: int, 
                          headers: Dict = None, json_data: Dict = None, 
                          description: str = ""):
        """Test a single endpoint and record results."""
        url = f"{self.base_url}{endpoint}"
        headers = headers or {}
        
        async with httpx.AsyncClient() as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=json_data)
                elif method.upper() == "PATCH":
                    response = await client.patch(url, headers=headers, json=json_data)
                else:
                    response = await client.request(method, url, headers=headers, json=json_data)
                
                success = response.status_code == expected_status
                
                self.results.append({
                    "method": method.upper(),
                    "endpoint": endpoint,
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "success": success,
                    "description": description,
                    "response": response.text[:200] if response.text else ""
                })
                
                status_icon = "✅" if success else "❌"
                print(f"{status_icon} {method.upper()} {endpoint} -> {response.status_code} (expected {expected_status})")
                
                return success
                
            except Exception as e:
                self.results.append({
                    "method": method.upper(),
                    "endpoint": endpoint,
                    "expected_status": expected_status,
                    "actual_status": "ERROR",
                    "success": False,
                    "description": description,
                    "response": str(e)
                })
                print(f"❌ {method.upper()} {endpoint} -> ERROR: {e}")
                return False
    
    async def run_tests(self):
        """Run all endpoint tests."""
        print("=" * 80)
        print("🧪 TESTING PHASE 1 API ENDPOINT IMPLEMENTATIONS")
        print("=" * 80)
        
        # Test infrastructure and basic endpoints
        print("\n📍 Infrastructure Tests:")
        await self.test_endpoint("GET", "/health", 200, description="Health check")
        await self.test_endpoint("GET", "/invalid-endpoint", 404, description="404 handling")
        
        # Test authentication endpoints
        print("\n🔐 Authentication Endpoints:")
        await self.test_endpoint(
            "POST", "/auth/gmail-oauth", 200, 
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Gmail OAuth init"
        )
        await self.test_endpoint(
            "GET", "/auth/google/callback", 400,
            description="OAuth callback without code"
        )
        await self.test_endpoint(
            "GET", "/auth/user", 401,
            description="User info without auth"
        )
        await self.test_endpoint(
            "POST", "/auth/validate", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Token validation without auth"
        )
        await self.test_endpoint(
            "POST", "/auth/refresh", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Token refresh without token"
        )
        await self.test_endpoint(
            "POST", "/auth/logout", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Logout without auth"
        )
        await self.test_endpoint(
            "PUT", "/auth/profile", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Profile update without auth"
        )
        
        # Test newsletter endpoints  
        print("\n📰 Newsletter Management Endpoints:")
        await self.test_endpoint(
            "POST", "/newsletters/fetch", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Newsletter fetch without auth"
        )
        await self.test_endpoint(
            "POST", "/newsletters/parse", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Newsletter parse without auth"
        )
        await self.test_endpoint(
            "POST", "/newsletters/save", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Newsletter save without auth"
        )
        await self.test_endpoint(
            "GET", "/newsletters", 401,
            description="Newsletter list without auth"
        )
        await self.test_endpoint(
            "GET", "/newsletters/test-id", 401,
            description="Newsletter details without auth"
        )
        await self.test_endpoint(
            "PATCH", "/newsletters/test-id/status", 401,
            headers={"Content-Type": "application/json"},
            json_data={"status": "completed"},
            description="Newsletter status update without auth"
        )
        
        # Test briefing session endpoints
        print("\n🎤 Briefing Session Endpoints:")
        await self.test_endpoint(
            "POST", "/briefing/start", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Briefing start without auth"
        )
        await self.test_endpoint(
            "GET", "/briefing/session/test-session-id", 401,
            description="Session state without auth"
        )
        await self.test_endpoint(
            "POST", "/briefing/session/test-session-id/pause", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Session pause without auth"
        )
        await self.test_endpoint(
            "POST", "/briefing/session/test-session-id/resume", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Session resume without auth"
        )
        await self.test_endpoint(
            "POST", "/briefing/session/test-session-id/stop", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Session stop without auth"
        )
        await self.test_endpoint(
            "POST", "/briefing/session/test-session-id/next", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Next story without auth"
        )
        await self.test_endpoint(
            "POST", "/briefing/session/test-session-id/previous", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Previous story without auth"
        )
        await self.test_endpoint(
            "GET", "/briefing/session/test-session-id/metadata", 401,
            description="Session metadata without auth"
        )
        await self.test_endpoint(
            "POST", "/briefing/cleanup", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Session cleanup without auth"
        )
        
        # Test audio processing endpoints
        print("\n🔊 Audio Processing Endpoints:")
        await self.test_endpoint(
            "POST", "/audio/generate", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Audio generation without auth"
        )
        await self.test_endpoint(
            "POST", "/audio/upload", 401,
            description="Audio upload without auth"
        )
        await self.test_endpoint(
            "GET", "/audio/test-story-id", 401,
            description="Audio retrieval without auth"
        )
        await self.test_endpoint(
            "GET", "/audio/queue/status", 401,
            description="Audio queue status without auth"
        )
        await self.test_endpoint(
            "POST", "/audio/batch", 401,
            headers={"Content-Type": "application/json"},
            json_data={},
            description="Audio batch processing without auth"
        )
        
        # Generate summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🔍 Failed Tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"  ❌ {result['method']} {result['endpoint']} -> {result['actual_status']} (expected {result['expected_status']})")
                    if result.get('response'):
                        print(f"     Response: {result['response'][:100]}...")
        
        print("\n" + "=" * 80)
        if failed_tests == 0:
            print("🎉 ALL TESTS PASSED! API endpoints are properly implemented.")
            print("✅ Phase 1 API implementation is COMPLETE.")
        elif passed_tests >= total_tests * 0.8:  # 80% pass rate
            print("⚠️  Most tests passed, but some endpoints need attention.")
            print("🔧 Phase 1 API implementation is mostly complete.")
        else:
            print("❌ Many tests failed. Significant work needed.")
            print("🚧 Phase 1 API implementation needs more work.")
        print("=" * 80)


async def main():
    """Main test runner."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:5000"
    
    tester = EndpointTester(base_url)
    await tester.run_tests()
    
    # Return exit code based on results
    failed_tests = sum(1 for r in tester.results if not r["success"])
    return 0 if failed_tests == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)