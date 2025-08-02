#!/usr/bin/env python3
"""
Test script to verify Cursor API connection using config.py settings
"""
import os
import sys
import requests
from config import API_BASE_URL, USAGE_ENDPOINT, SUBSCRIPTION_ENDPOINT, REQUEST_TIMEOUT, USER_AGENT, ALTERNATE_ENDPOINTS
from colorama import Fore, Style, init

# Initialize colorama
init()

def test_endpoint(url, token):
    """Test a single API endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    
    try:
        print(f"\n{Fore.CYAN}Testing endpoint: {url}{Style.RESET_ALL}")
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        print(f"Status Code: ", end="")
        if 200 <= response.status_code < 300:
            print(f"{Fore.GREEN}{response.status_code}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}{response.status_code}{Style.RESET_ALL}")
            
        print(f"Response: {response.text[:200]}" + ("..." if len(response.text) > 200 else ""))
        return response.status_code < 400
        
    except requests.RequestException as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
        return False

def main():
    # Get API token from environment variable or user input
    token = os.environ.get("CURSOR_TOKEN")
    if not token:
        token = input(f"{Fore.YELLOW}Enter your Cursor API token: {Style.RESET_ALL}")
    
    if not token:
        print(f"{Fore.RED}No API token provided. Exiting.{Style.RESET_ALL}")
        sys.exit(1)
    
    # Test primary endpoints
    endpoints = [
        f"{API_BASE_URL.rstrip('/')}{USAGE_ENDPOINT}",
        f"{API_BASE_URL.rstrip('/')}{SUBSCRIPTION_ENDPOINT}"
    ]
    
    # Test alternate endpoints
    for endpoint in ALTERNATE_ENDPOINTS:
        endpoints.append(f"{API_BASE_URL.rstrip('/')}{endpoint}")
    
    # Add some common API endpoints to test
    common_endpoints = [
        "https://api.cursor.sh/v1/me",
        "https://api2.cursor.sh/v1/me",
        "https://platform.cursor.com/api/v1/me"
    ]
    
    endpoints.extend(common_endpoints)
    
    # Test all endpoints
    print(f"\n{Fore.CYAN}=== Testing Cursor API Endpoints ==={Style.RESET_ALL}")
    print(f"Using API Base URL: {API_BASE_URL}")
    print(f"Token: {token[:10]}...{token[-5:] if len(token) > 15 else ''}")
    
    success = False
    for endpoint in endpoints:
        if test_endpoint(endpoint, token):
            success = True
            break
    
    if not success:
        print(f"\n{Fore.RED}All endpoints failed. Please check your API token and network connection.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.GREEN}Successfully connected to Cursor API!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
