"""
================================================================================
TEST SCRIPT FOR FAIRE TO HELM INTEGRATION
================================================================================

Purpose:
    Test connections to both Faire and Helm APIs before deploying.
    Can run with or without real API credentials.

Author: Copper Beech Support
Created: 2025-10-26
Version: 1.0

Usage:
    python test_faire_helm.py           (with real credentials)
    python test_faire_helm.py --mock    (without credentials, mock mode)

================================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

# ============================================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================================

try:
    from dotenv import load_dotenv

    load_dotenv()
    print("[INFO] Loaded environment variables from .env file")
except ImportError:
    print("[INFO] python-dotenv not installed, using system environment")

# ============================================================================
# CONFIGURATION
# ============================================================================

FAIRE_API_TOKEN = os.getenv("FAIRE_API_TOKEN")
HELM_DOMAIN = os.getenv("HELM_DOMAIN")
HELM_API_TOKEN = os.getenv("HELM_API_TOKEN")
HELM_CHANNEL_ID = os.getenv("HELM_MANUAL_CHANNEL_ID", "1")

# API Base URLs
FAIRE_BASE_URL = "https://www.faire.com/external-api/v2"
HELM_BASE_URL = f"https://{HELM_DOMAIN}/public-api" if HELM_DOMAIN else None


# ============================================================================
# TEST FUNCTIONS
# ============================================================================


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(success: bool, message: str):
    """Print a formatted result"""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {message}")


def test_faire_connection(mock_mode: bool = False) -> bool:
    """
    Test connection to Faire API.

    Args:
        mock_mode: If True, skip actual API call

    Returns:
        bool: True if connection successful
    """
    print_header("Testing Faire API Connection")

    # Check for credentials
    if not FAIRE_API_TOKEN:
        print_result(False, "FAIRE_API_TOKEN not set in environment")
        return False

    print(f"[INFO] Faire API Token: {FAIRE_API_TOKEN[:20]}...")
    print(f"[INFO] Faire API URL: {FAIRE_BASE_URL}")

    # Mock mode
    if mock_mode:
        print_result(True, "MOCK MODE - Skipping actual API call")
        return True

    # Make test request
    headers = {
        "X-FAIRE-ACCESS-TOKEN": FAIRE_API_TOKEN,
        "Content-Type": "application/json",
    }

    params = {"limit": 1}  # Just get 1 order to test

    try:
        print("[INFO] Making test request to Faire API...")

        response = requests.get(
            f"{FAIRE_BASE_URL}/orders", headers=headers, params=params, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            total_orders = data.get("page", 0)

            print_result(True, "Successfully connected to Faire API")
            print(f"[INFO] Your account has access to orders")

            # Show sample order if available
            if data.get("orders"):
                sample = data["orders"][0]
                print(f"[INFO] Sample Order: {sample.get('display_id', 'N/A')}")
                print(f"[INFO] Retailer ID: {sample.get('retailer_id', 'N/A')}")

            return True

        elif response.status_code == 401:
            print_result(False, "Authentication failed - Invalid API token")
            return False

        elif response.status_code == 403:
            print_result(False, "Access forbidden - Check API permissions")
            return False

        else:
            print_result(False, f"Unexpected response: HTTP {response.status_code}")
            print(f"[ERROR] Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print_result(False, "Request timed out")
        return False

    except requests.exceptions.RequestException as e:
        print_result(False, f"Connection error: {e}")
        return False


def test_helm_connection(mock_mode: bool = False) -> bool:
    """
    Test connection to Helm API.

    Args:
        mock_mode: If True, skip actual API call

    Returns:
        bool: True if connection successful
    """
    print_header("Testing Helm API Connection")

    # Check for credentials
    if not HELM_DOMAIN or not HELM_API_TOKEN:
        print_result(False, "HELM_DOMAIN or HELM_API_TOKEN not set")
        return False

    print(f"[INFO] Helm Domain: {HELM_DOMAIN}")
    print(f"[INFO] Helm API Token: {HELM_API_TOKEN[:20]}...")
    print(f"[INFO] Helm API URL: {HELM_BASE_URL}")

    # Mock mode
    if mock_mode:
        print_result(True, "MOCK MODE - Skipping actual API call")
        return True

    # Make test request
    headers = {
        "Authorization": f"Bearer {HELM_API_TOKEN}",
        "Content-Type": "application/json",
    }

    params = {"page": 1}

    try:
        print("[INFO] Making test request to Helm API...")

        response = requests.get(
            f"{HELM_BASE_URL}/orders", headers=headers, params=params, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            total_orders = data.get("total", 0)

            print_result(True, "Successfully connected to Helm API")
            print(f"[INFO] Total orders in system: {total_orders}")
            print(f"[INFO] API access is working correctly")

            return True

        elif response.status_code == 401:
            print_result(False, "Authentication failed - Invalid Bearer token")
            return False

        elif response.status_code == 403:
            print_result(False, "Access forbidden - Check API permissions")
            return False

        elif response.status_code == 404:
            print_result(False, "API endpoint not found - Check HELM_DOMAIN")
            return False

        else:
            print_result(False, f"Unexpected response: HTTP {response.status_code}")
            print(f"[ERROR] Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print_result(False, "Request timed out")
        return False

    except requests.exceptions.RequestException as e:
        print_result(False, f"Connection error: {e}")
        return False


def test_data_transformation() -> bool:
    """
    Test the data transformation logic with sample data.

    Returns:
        bool: True if transformation works correctly
    """
    print_header("Testing Data Transformation")

    # Sample Faire order
    sample_faire_order = {
        "id": "bo_test123",
        "display_id": "TEST123",
        "created_at": "2025-10-26T10:00:00.000Z",
        "state": "NEW",
        "items": [
            {
                "product_id": "p_test",
                "quantity": 12,
                "sku": "OCE0112",
                "price_cents": 320,
                "product_name": "Blood Orange Chocolate",
                "variant_name": "default",
            }
        ],
        "address": {
            "name": "Test Customer",
            "address1": "123 Test St",
            "city": "London",
            "postal_code": "W1A 1AA",
            "country": "United Kingdom",
            "country_code": "GBR",
            "phone_number": "+447700900000",
        },
        "retailer_id": "r_test",
    }

    try:
        # Import the sync class
        from faire_helm_sync import FaireHelmSync

        # Create instance in test mode
        syncer = FaireHelmSync(test_mode=True)

        # Transform the order
        helm_order = syncer.transform_faire_to_helm(sample_faire_order)

        # Validate structure
        assert "order" in helm_order, "Missing 'order' key"
        assert "order_inventory" in helm_order, "Missing 'order_inventory' key"
        assert helm_order["order"]["channel_order_id"] == "TEST123", "Order ID mismatch"
        assert len(helm_order["order_inventory"]) == 1, "Item count mismatch"

        print_result(True, "Data transformation working correctly")
        print(f"[INFO] Transformed Faire order -> Helm format")
        print(f"[INFO] Order ID: {helm_order['order']['channel_order_id']}")
        print(f"[INFO] Items: {len(helm_order['order_inventory'])}")
        print(f"[INFO] Total: GBP {helm_order['order']['total_paid']}")

        return True

    except Exception as e:
        print_result(False, f"Transformation failed: {e}")
        return False


def create_test_order(mock_mode: bool = False) -> bool:
    """
    Create a test order in Helm to verify end-to-end functionality.

    Args:
        mock_mode: If True, skip actual order creation

    Returns:
        bool: True if order created successfully
    """
    print_header("Testing Order Creation in Helm")

    # Check for credentials
    if not HELM_DOMAIN or not HELM_API_TOKEN:
        print_result(False, "HELM_DOMAIN or HELM_API_TOKEN not set")
        return False

    # Mock mode
    if mock_mode:
        print_result(True, "MOCK MODE - Skipping actual order creation")
        return True

    # Ask for confirmation
    print("[WARNING] This will create a REAL test order in Helm!")
    print("[WARNING] You should delete this test order afterwards.")
    response = input("\nContinue? (yes/no): ")

    if response.lower() != "yes":
        print("[INFO] Test cancelled by user")
        return False

    # Create test order
    test_order = {
        "order": {
            "manual_channel_id": int(HELM_CHANNEL_ID),
            "channel_order_id": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "status_id": 1,
            "date_received": datetime.now().isoformat(),
            "shipping_method_requested": "Test",
            "lock_shipping_method": 0,
            "one_off_shipment": "",
            "channel_alt_id": "",
            "payment_method": "Faire-Test",
            "payment_ref": "TEST",
            "payment_currency": "GBP",
            "total_paid": "10.00",
            "total_discount": "0",
            "total_tax": "0",
            "total_weight": "0.070",
            "shipping_paid": "0.00",
            "email": "test@example.com",
            "phone_one": "+447700900000",
            "phone_two": "",
            "contact_id": "",
            "vat_number": "",
            "eori_number": "",
            "tax_id": "",
            "ioss_number": "",
            "shipping_name": "Test Customer",
            "shipping_name_company": "Test Company",
            "shipping_address_line_one": "123 Test Street",
            "shipping_address_line_two": "",
            "shipping_address_city": "London",
            "shipping_address_county": "Greater London",
            "shipping_address_country": "United Kingdom",
            "shipping_address_postcode": "W1A 1AA",
            "shipping_address_iso": "GB",
            "invoice_name": "Test Customer",
            "invoice_name_company": "Test Company",
            "invoice_address_line_one": "123 Test Street",
            "invoice_address_line_two": "",
            "invoice_address_city": "London",
            "invoice_address_county": "Greater London",
            "invoice_address_country": "United Kingdom",
            "invoice_address_postcode": "W1A 1AA",
            "invoice_address_iso": "GB",
            "customer_comments": "Test order from integration test",
            "gift_note": "",
            "fulfilment_client_id": None,
            "notes": ["This is a TEST order", "Please DELETE after verification"],
            "custom_fields": {},
        },
        "order_inventory": [
            {
                "inventory_id": "",
                "name": "Test Product",
                "sku": "TEST-SKU",
                "quantity": 1,
                "unit_price": 10.00,
                "line_total_discount": 0,
                "options": "",
                "notes": "Test item",
                "hs_code": "",
                "country_of_origin": "",
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {HELM_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        print(f"[INFO] Creating test order: {test_order['order']['channel_order_id']}")

        response = requests.post(
            f"{HELM_BASE_URL}/orders/create",
            headers=headers,
            json=test_order,
            timeout=30,
        )

        if response.status_code in [200, 201]:
            print_result(True, "Test order created successfully!")
            print(f"[INFO] Order ID: {test_order['order']['channel_order_id']}")
            print("[WARNING] Remember to DELETE this test order from Helm!")
            return True
        else:
            print_result(False, f"Failed to create order: HTTP {response.status_code}")
            print(f"[ERROR] Response: {response.text}")
            return False

    except Exception as e:
        print_result(False, f"Error creating order: {e}")
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================


def main():
    """
    Run all tests and provide summary.
    """
    # Check for mock mode
    mock_mode = "--mock" in sys.argv or "-m" in sys.argv

    # Print header
    print("\n" + "=" * 70)
    print("  FAIRE TO HELM INTEGRATION TEST SUITE")
    print("=" * 70)
    print(f"  Mode: {'MOCK (no API calls)' if mock_mode else 'LIVE (real API calls)'}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Check configuration
    print_header("Configuration Check")
    print(f"[INFO] FAIRE_API_TOKEN: {'Set' if FAIRE_API_TOKEN else 'NOT SET'}")
    print(f"[INFO] HELM_DOMAIN: {HELM_DOMAIN if HELM_DOMAIN else 'NOT SET'}")
    print(f"[INFO] HELM_API_TOKEN: {'Set' if HELM_API_TOKEN else 'NOT SET'}")
    print(f"[INFO] HELM_CHANNEL_ID: {HELM_CHANNEL_ID}")

    # Run tests
    results = {
        "faire_connection": test_faire_connection(mock_mode),
        "helm_connection": test_helm_connection(mock_mode),
        "transformation": test_data_transformation(),
    }

    # Optional: Test order creation
    if not mock_mode and results["helm_connection"]:
        print("\n")
        results["order_creation"] = create_test_order(mock_mode)

    # Print summary
    print_header("Test Summary")

    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed

    print(f"Total Tests: {total}")
    print(f"[PASS] Passed: {passed}")
    print(f"[FAIL] Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")

    print("\n" + "=" * 70)

    if failed == 0:
        print("[SUCCESS] All tests passed! Ready to deploy.")
    else:
        print("[WARNING] Some tests failed. Please fix before deploying.")

    print("=" * 70 + "\n")

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
