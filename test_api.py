#!/usr/bin/env python3
"""
Test script for Cursor API endpoints
"""
import os
import sys
import json
import logging
from colorama import Fore, Style, init
from cursor_acc_info import UsageManager, EMOJI
from config import API_BASE_URL, USAGE_ENDPOINT, SUBSCRIPTION_ENDPOINT, ALTERNATE_ENDPOINTS

# Initialize colorama
init()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_api.log')
    ]
)
logger = logging.getLogger(__name__)

def print_header(text: str) -> None:
    """Print a formatted header"""
    print(f"\n{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")

def test_usage(manager: UsageManager, token: str) -> None:
    """Test the get_usage method"""
    print_header(f"{EMOJI['USAGE']} Testing Usage Endpoint")
    usage = manager.get_usage(token)
    if usage:
        print(f"{Fore.GREEN}✓ Successfully retrieved usage info{Style.RESET_ALL}")
        print(f"Endpoint used: {usage.get('endpoint_used', 'Unknown')}")
        print(f"Premium usage: {usage.get('premium_usage', 'N/A')} / {usage.get('max_premium_usage', 'N/A')}")
        print(f"Basic usage: {usage.get('basic_usage', 'N/A')} / {usage.get('max_basic_usage', 'N/A')}")
    else:
        print(f"{Fore.RED}✗ Failed to retrieve usage info{Style.RESET_ALL}")

def test_subscription(manager: UsageManager, token: str) -> None:
    """Test the get_stripe_profile method"""
    print_header(f"{EMOJI['SUBSCRIPTION']} Testing Subscription Endpoint")
    subscription = manager.get_stripe_profile(token)
    if subscription and 'subscription' in subscription:
        print(f"{Fore.GREEN}✓ Successfully retrieved subscription info{Style.RESET_ALL}")
        print(f"Endpoint used: {subscription.get('endpoint_used', 'Unknown')}")
        print(f"Subscription status: {subscription.get('subscription', {}).get('status', 'Unknown')}")
        print(f"Plan: {subscription.get('subscription', {}).get('plan', 'Unknown')}")
    else:
        print(f"{Fore.RED}✗ Failed to retrieve subscription info{Style.RESET_ALL}")

def test_endpoint_discovery(manager: UsageManager, token: str) -> None:
    """Test the test_api_endpoints method"""
    print_header(f"{EMOJI['INFO']} Testing API Endpoint Discovery")
    results = manager.test_api_endpoints(token)
    if results:
        print(f"{Fore.GREEN}✓ Found {len(results.get('working_endpoints', []))} working endpoints{Style.RESET_ALL}")
        for endpoint in results.get('working_endpoints', []):
            print(f"- {endpoint['method']} {endpoint['url']} ({endpoint['status_code']})")
    else:
        print(f"{Fore.RED}✗ No working endpoints found{Style.RESET_ALL}")

def main() -> None:
    """Main function"""
    # Get token from environment variable or ask user
    token = os.environ.get("CURSOR_TOKEN")
    if not token:
        token = input(f"{Fore.YELLOW}Enter your Cursor API token: {Style.RESET_ALL}")
    
    if not token:
        print(f"{Fore.RED}No API token provided. Exiting.{Style.RESET_ALL}")
        sys.exit(1)
    
    manager = UsageManager()
    
    # Test the API endpoints
    test_usage(manager, token)
    test_subscription(manager, token)
    test_endpoint_discovery(manager, token)
    
    print(f"\n{Fore.GREEN}✓ Test completed. Check test_api.log for detailed logs.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
