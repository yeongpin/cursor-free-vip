#!/usr/bin/env python3
"""
Auto-find working Cursor API endpoints
"""
import os
import sys
import json
import time
import requests
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api_discovery.log')
    ]
)
logger = logging.getLogger(__name__)

# Get token from environment or use the one from cursor_acc_info.py
TOKEN = os.environ.get('CURSOR_TOKEN')
if not TOKEN:
    try:
        from cursor_acc_info import get_token
        TOKEN = get_token()
    except ImportError:
        logger.error("Could not import get_token from cursor_acc_info.py")
        sys.exit(1)

if not TOKEN:
    logger.error("No Cursor token found. Please set CURSOR_TOKEN environment variable.")
    sys.exit(1)

# Common headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Cursor/0.10.0",
    "Accept": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

# Base URLs to test
BASE_URLS = [
    "https://api.cursor.sh",
    "https://api2.cursor.sh",
    "https://www.cursor.com/api",
    "https://platform.cursor.com/api",
    "https://cursor.so/api",
    "https://app.cursor.com/api",
]

# Endpoints to test
ENDPOINTS = [
    "",  # Root endpoint
    "/",
    "/v1",
    "/v1/",
    "/v1/me",
    "/v1/user",
    "/v1/user/me",
    "/v1/auth/me",
    "/v1/auth/user",
    "/v1/billing/usage",
    "/v1/billing/subscription",
    "/v1/subscription",
    "/v1/usage",
    "/me",
    "/user",
    "/user/me",
    "/auth/me",
    "/billing/usage",
    "/billing/subscription",
    "/subscription",
    "/usage",
]

# Additional headers to try
ADDITIONAL_HEADERS = [
    {},
    {"X-Requested-With": "XMLHttpRequest"},
    {"Origin": "https://cursor.sh"},
    {"Referer": "https://cursor.sh"},
    {"X-Client-Version": "1.0.0"},
]

def test_endpoint(base_url: str, endpoint: str, headers: Dict) -> Dict:
    """Test a single endpoint with given headers"""
    url = urljoin(base_url, endpoint)
    result = {
        "url": url,
        "method": "GET",
        "headers": headers,
        "success": False,
        "status_code": None,
        "error": None,
        "response": None,
        "response_headers": {},
        "time_ms": 0
    }
    
    start_time = time.time()
    
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=10,
            allow_redirects=True
        )
        
        result.update({
            "status_code": response.status_code,
            "response_headers": dict(response.headers),
            "success": response.status_code == 200,
            "time_ms": int((time.time() - start_time) * 1000)
        })
        
        # Try to parse JSON if content-type is application/json
        content_type = response.headers.get('content-type', '').lower()
        if 'application/json' in content_type and response.content:
            try:
                result["response"] = response.json()
            except json.JSONDecodeError:
                result["response"] = response.text[:1000]  # Truncate if too large
        else:
            # For non-JSON responses, include a preview
            result["response"] = response.text[:1000] if response.text else None
    
    except requests.exceptions.RequestException as e:
        result.update({
            "error": str(e),
            "success": False
        })
    except Exception as e:
        result.update({
            "error": f"Unexpected error: {str(e)}",
            "success": False
        })
    
    return result

def test_all_endpoints():
    """Test all combinations of base URLs and endpoints"""
    results = []
    total_tests = len(BASE_URLS) * len(ENDPOINTS) * len(ADDITIONAL_HEADERS)
    completed = 0
    
    print(f"\n🚀 Starting API endpoint discovery...")
    print(f"📊 Testing {total_tests} combinations...\n")
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        
        for base_url in BASE_URLS:
            for endpoint in ENDPOINTS:
                for extra_headers in ADDITIONAL_HEADERS:
                    # Combine base headers with extra headers
                    headers = HEADERS.copy()
                    headers.update(extra_headers)
                    
                    # Submit the test to the thread pool
                    future = executor.submit(test_endpoint, base_url, endpoint, headers)
                    futures.append(future)
        
        # Process results as they complete
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            
            # Print progress
            progress = (completed / total_tests) * 100
            elapsed = time.time() - start_time
            eta = (elapsed / completed) * (total_tests - completed) if completed > 0 else 0
            
            status = "✅" if result["success"] else "❌"
            print(f"\r🔍 Progress: {progress:.1f}% | {completed}/{total_tests} | "
                  f"ETA: {eta:.1f}s | {status} {result.get('status_code', '')} {result['url']}", 
                  end="", flush=True)
    
    # Sort results by success, then status code (treat None status as 0 for sorting)
    results.sort(key=lambda x: (not x["success"], x.get("status_code") or 0))
    
    # Save results to file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = f"api_discovery_results_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": time.time(),
            "total_tests": total_tests,
            "successful_tests": sum(1 for r in results if r["success"]),
            "results": results
        }, f, indent=2)
    
    print(f"\n\n🎉 Discovery complete! Results saved to {output_file}")
    
    # Print summary
    successful = [r for r in results if r["success"]]
    if successful:
        print("\n✨ Successful endpoints:")
        for i, result in enumerate(successful[:10], 1):  # Show top 10 successful endpoints
            print(f"{i}. {result['url']} ({result.get('status_code')})")
    else:
        print("\n❌ No successful endpoints found. Check the log file for details.")
    
    return output_file

def analyze_results(filename: str):
    """Analyze the results file and suggest configuration"""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        successful = [r for r in data["results"] if r["success"]]
        
        if not successful:
            print("\n❌ No successful API calls found.")
            return
        
        # Group by base URL
        by_base_url = {}
        for result in successful:
            base_url = "/".join(result["url"].split("/")[:3])  # Get protocol + domain
            if base_url not in by_base_url:
                by_base_url[base_url] = []
            by_base_url[base_url].append(result)
        
        print("\n📊 Analysis of successful endpoints:")
        
        # Find the most promising base URL
        best_base = max(by_base_url.items(), key=lambda x: len(x[1]))
        print(f"\n🔍 Best base URL: {best_base[0]} ({len(best_base[1])} successful endpoints)")
        
        # Find common endpoints
        endpoints = {}
        for result in successful:
            path = "/" + "/".join(result["url"].split("/")[3:])  # Get path without domain
            if path not in endpoints:
                endpoints[path] = 0
            endpoints[path] += 1
        
        print("\n🔑 Common endpoints:")
        for path, count in sorted(endpoints.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"- {path} ({count} successful calls)")
        
        # Suggest configuration
        print("\n💡 Suggested configuration:")
        print(f"API_BASE_URL = \"{best_base[0]}\"")
        
        # Find usage and subscription endpoints
        usage_endpoints = [e for e in endpoints if 'usage' in e.lower()]
        sub_endpoints = [e for e in endpoints if 'sub' in e.lower()]
        
        if usage_endpoints:
            print(f"USAGE_ENDPOINT = \"{usage_endpoints[0]}\"")
        if sub_endpoints:
            print(f"SUBSCRIPTION_ENDPOINT = \"{sub_endpoints[0]}\"")
        
    except Exception as e:
        logger.error(f"Error analyzing results: {str(e)}")

def main():
    print("""
    🚀 Cursor API Endpoint Discovery Tool
    ===================================
    This tool will automatically test various Cursor API endpoints
    to find working configurations.
    """)
    
    if not TOKEN:
        print("❌ Error: No Cursor token found.")
        return
    
    print(f"🔑 Using token: {TOKEN[:10]}...{TOKEN[-10:]}")
    
    # Run the discovery
    results_file = test_all_endpoints()
    
    # Analyze the results
    if os.path.exists(results_file):
        analyze_results(results_file)
    
    print("\n✅ Done!")

if __name__ == "__main__":
    main()
