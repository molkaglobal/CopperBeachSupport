"""
================================================================================
FAIRE TO HELM ORDER SYNCHRONIZATION SCRIPT
================================================================================

Purpose:
    Automatically synchronizes orders from Faire wholesale platform to Helm
    order management system.

Author: Copper Beech Support
Created: 2025-10-26
Version: 1.0

Dependencies:
    - requests: HTTP library for API calls
    - google-cloud-firestore: For tracking sync state
    - Standard library: os, json, datetime, logging

Environment Variables Required:
    - FAIRE_API_TOKEN: Faire Brand API token
    - HELM_DOMAIN: Your Helm domain (e.g., client.myhelm.app)
    - HELM_API_TOKEN: Helm Bearer authentication token
    - HELM_MANUAL_CHANNEL_ID: Channel ID for Faire orders (default: 1)

Usage:
    python faire_helm_sync.py --test    (test mode with mock data)
    python faire_helm_sync.py           (production mode)

    Or deploy to Google Cloud Run with Cloud Scheduler for automation.
================================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging


# ============================================================================
# LOAD ENVIRONMENT VARIABLES FROM .env FILE (for local development)
# ============================================================================

try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file if it exists
    logger.info("Loaded environment variables from .env file")
except ImportError:
    logger.info("python-dotenv not installed, using system environment variables")

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("faire_helm_sync.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# MAIN SYNCHRONIZATION CLASS
# ============================================================================


class FaireHelmSync:
    """
    Main class for synchronizing orders between Faire and Helm.

    This class handles:
    1. Fetching new orders from Faire API
    2. Transforming order data to Helm format
    3. Creating orders in Helm
    4. Tracking sync state in Firestore
    """

    def __init__(self, test_mode: bool = False):
        """
        Initialize the synchronization service.

        Args:
            test_mode (bool): If True, uses mock data instead of real APIs.
                             Useful for testing without API credentials.

        Raises:
            ValueError: If required environment variables are missing
        """
        self.test_mode = test_mode

        # ====================================================================
        # LOAD CONFIGURATION FROM ENVIRONMENT
        # ====================================================================

        self.faire_api_token = os.getenv(
            "FAIRE_API_TOKEN", "TEST_TOKEN" if test_mode else None
        )
        self.helm_domain = os.getenv(
            "HELM_DOMAIN", "test.myhelm.app" if test_mode else None
        )
        self.helm_api_token = os.getenv(
            "HELM_API_TOKEN", "TEST_TOKEN" if test_mode else None
        )
        self.helm_manual_channel_id = os.getenv("HELM_MANUAL_CHANNEL_ID", "1")

        # Validate configuration (skip in test mode)
        if not test_mode:
            if not all([self.faire_api_token, self.helm_domain, self.helm_api_token]):
                raise ValueError(
                    "Missing required environment variables. Please set:\n"
                    "  - FAIRE_API_TOKEN\n"
                    "  - HELM_DOMAIN\n"
                    "  - HELM_API_TOKEN\n"
                    "  - HELM_MANUAL_CHANNEL_ID (optional, defaults to 1)"
                )

        # ====================================================================
        # API BASE URLS
        # ====================================================================

        self.faire_base_url = "https://www.faire.com/external-api/v2"
        self.helm_base_url = f"https://{self.helm_domain}/public-api"

        logger.info(f"Initialized FaireHelmSync (test_mode={test_mode})")
        logger.info(f"Faire API: {self.faire_base_url}")
        logger.info(f"Helm API: {self.helm_base_url}")

    # ========================================================================
    # SYNC STATE MANAGEMENT (FIRESTORE)
    # ========================================================================

    def get_last_sync_time(self) -> datetime:
        """
        Retrieve the last successful sync timestamp from Firestore.

        This prevents re-syncing orders that have already been processed.
        If no previous sync exists, defaults to 7 days ago.

        Returns:
            datetime: The last sync time, or 7 days ago if never synced
        """
        # In test mode, return recent time
        if self.test_mode:
            logger.info("[TEST MODE] Returning mock last sync time (1 day ago)")
            return datetime.now() - timedelta(days=1)

        try:
            from google.cloud import firestore

            logger.info("Checking Firestore for last sync time...")
            db = firestore.Client()
            doc_ref = db.collection("faire_sync").document("last_sync")
            doc = doc_ref.get()

            if doc.exists:
                last_sync = doc.to_dict().get("timestamp")
                if last_sync:
                    logger.info(f"Found last sync: {last_sync}")
                    return datetime.fromisoformat(last_sync)

            logger.warning("No previous sync found in Firestore")

        except Exception as e:
            logger.warning(f"Could not access Firestore: {e}")

        # Default fallback
        default_time = datetime.now() - timedelta(days=7)
        logger.info(f"Using default sync time: {default_time} (7 days ago)")
        return default_time

    def save_sync_time(self, sync_time: datetime):
        """
        Save the current sync timestamp to Firestore.

        This marks the sync as complete and stores the time for the next run.

        Args:
            sync_time (datetime): The time to save as last sync
        """
        # Skip in test mode
        if self.test_mode:
            logger.info(f"[TEST MODE] Would save sync time: {sync_time}")
            return

        try:
            from google.cloud import firestore

            db = firestore.Client()
            doc_ref = db.collection("faire_sync").document("last_sync")
            doc_ref.set(
                {
                    "timestamp": sync_time.isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
            )
            logger.info(f"[SUCCESS] Saved sync time to Firestore: {sync_time}")

        except Exception as e:
            logger.error(f"[ERROR] Failed to save sync time: {e}")

    # ========================================================================
    # FAIRE API INTEGRATION
    # ========================================================================

    def fetch_faire_orders(self, since: datetime) -> List[Dict]:
        """
        Fetch new or updated orders from Faire API.

        Uses the Faire Brand API to retrieve orders that have been created
        or updated since the last sync.

        API Endpoint: GET /external-api/v2/orders
        Documentation: https://faire.github.io/external-api-docs/#get-all-orders

        Args:
            since (datetime): Only fetch orders updated after this time

        Returns:
            List[Dict]: List of order objects from Faire API
        """
        logger.info("=" * 60)
        logger.info(f"Fetching Faire orders since: {since}")
        logger.info("=" * 60)

        # ====================================================================
        # TEST MODE: Return mock data
        # ====================================================================

        if self.test_mode:
            logger.info("[TEST MODE] Returning mock Faire orders")
            return self._get_mock_faire_orders()

        # ====================================================================
        # PREPARE API REQUEST
        # ====================================================================

        headers = {
            "X-FAIRE-ACCESS-TOKEN": self.faire_api_token,
            "Content-Type": "application/json",
        }

        # Format datetime for Faire API (ISO 8601 with milliseconds)
        since_str = since.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        params = {
            "updated_at_min": since_str,
            "limit": 50,  # Max 50 per request
            "excluded_states": "CANCELED",  # Don't sync cancelled orders
        }

        # ====================================================================
        # MAKE API REQUEST
        # ====================================================================

        try:
            logger.info(f"Making request to: {self.faire_base_url}/orders")
            logger.info(f"Parameters: {json.dumps(params, indent=2)}")

            response = requests.get(
                f"{self.faire_base_url}/orders",
                headers=headers,
                params=params,
                timeout=30,
            )

            # Check for errors
            response.raise_for_status()

            # Parse response
            data = response.json()
            orders = data.get("orders", [])

            logger.info(f"[SUCCESS] Fetched {len(orders)} orders from Faire")

            # Log order IDs for tracking
            for order in orders:
                logger.info(
                    f"   - Order: {order.get('display_id', 'UNKNOWN')} "
                    f"(State: {order.get('state', 'UNKNOWN')})"
                )

            return orders

        except requests.exceptions.Timeout:
            logger.error("[ERROR] Faire API request timed out")
            return []

        except requests.exceptions.HTTPError as e:
            logger.error(f"[ERROR] Faire API HTTP error: {e}")
            logger.error(
                f"   Response: {e.response.text if e.response else 'No response'}"
            )
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"[ERROR] Faire API request failed: {e}")
            return []

        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] Failed to parse Faire API response: {e}")
            return []

    # ========================================================================
    # DATA TRANSFORMATION (FAIRE -> HELM)
    # ========================================================================

    def transform_faire_to_helm(self, faire_order: Dict) -> Dict:
        """
        Transform a Faire order into Helm order format.

        This is the core transformation logic that maps Faire's data structure
        to what Helm expects.

        Faire Order Structure:
        {
            "id": "bo_xxx",
            "display_id": "BXDMJBWXID",
            "created_at": "2019-03-15T00:09:15.000Z",
            "items": [...],
            "address": {...},
            "retailer_id": "r_xxx"
        }

        Helm Order Structure:
        {
            "order": {...},
            "order_inventory": [...]
        }

        Args:
            faire_order (Dict): Order object from Faire API

        Returns:
            Dict: Order object formatted for Helm API
        """
        logger.info("-" * 60)
        logger.info(
            f"Transforming Faire order: {faire_order.get('display_id', 'UNKNOWN')}"
        )

        # ====================================================================
        # EXTRACT ORDER HEADER DATA
        # ====================================================================

        order_id = faire_order.get("id", "")
        display_id = faire_order.get("display_id", order_id)
        created_at = faire_order.get("created_at", "")
        order_state = faire_order.get("state", "UNKNOWN")

        logger.info(f"  Faire ID: {order_id}")
        logger.info(f"  Display ID: {display_id}")
        logger.info(f"  State: {order_state}")

        # ====================================================================
        # EXTRACT SHIPPING ADDRESS
        # ====================================================================

        address = faire_order.get("address", {})
        retailer_id = faire_order.get("retailer_id", "")
        purchase_order = faire_order.get("purchase_order_number", "")

        logger.info(f"  Retailer: {retailer_id}")
        logger.info(
            f"  Ship To: {address.get('name', 'N/A')}, "
            f"{address.get('city', 'N/A')}, {address.get('country', 'N/A')}"
        )

        # ====================================================================
        # CALCULATE ORDER TOTALS
        # ====================================================================

        items = faire_order.get("items", [])

        # Calculate total from item prices
        total_paid = sum(
            item.get("quantity", 0) * item.get("price_cents", 0) / 100 for item in items
        )

        # Estimate weight (default 0.07kg per item if not provided)
        total_weight = sum(item.get("quantity", 0) * 0.07 for item in items)

        logger.info(f"  Items: {len(items)}")
        logger.info(f"  Total: GBP {total_paid:.2f}")
        logger.info(f"  Weight: {total_weight:.3f}kg")

        # ====================================================================
        # MAP COUNTRY CODES
        # ====================================================================

        country_code = address.get("country_code", "GB")
        country_iso = self._map_country_code(country_code)

        # ====================================================================
        # BUILD HELM ORDER STRUCTURE
        # ====================================================================

        helm_order = {
            "order": {
                # Channel & Order IDs
                "manual_channel_id": int(self.helm_manual_channel_id),
                "channel_order_id": display_id,
                "channel_alt_id": order_id,
                "status_id": 1,  # 1 = New order
                # Dates
                "date_received": created_at or "",
                # Shipping
                "shipping_method_requested": "Standard",
                "lock_shipping_method": 0,
                "one_off_shipment": "",
                # Payment
                "payment_method": "Faire",
                "payment_ref": order_id,
                "payment_currency": "GBP",
                # Totals
                "total_paid": f"{total_paid:.2f}",
                "total_discount": "0",
                "total_tax": "0",
                "total_weight": f"{total_weight:.3f}",
                "shipping_paid": "0.00",
                # Contact
                "email": "",  # Faire doesn't provide retailer email
                "phone_one": address.get("phone_number", ""),
                "phone_two": "",
                "contact_id": "",
                # Tax IDs
                "vat_number": "",
                "eori_number": "",
                "tax_id": "",
                "ioss_number": "",
                # Shipping Address
                "shipping_name": address.get("name", ""),
                "shipping_name_company": address.get("company_name", ""),
                "shipping_address_line_one": address.get("address1", ""),
                "shipping_address_line_two": address.get("address2", ""),
                "shipping_address_city": address.get("city", ""),
                "shipping_address_county": address.get("state", ""),
                "shipping_address_country": address.get("country", ""),
                "shipping_address_postcode": address.get("postal_code", ""),
                "shipping_address_iso": country_iso,
                # Invoice Address (same as shipping for Faire)
                "invoice_name": address.get("name", ""),
                "invoice_name_company": address.get("company_name", ""),
                "invoice_address_line_one": address.get("address1", ""),
                "invoice_address_line_two": address.get("address2", ""),
                "invoice_address_city": address.get("city", ""),
                "invoice_address_county": address.get("state", ""),
                "invoice_address_country": address.get("country", ""),
                "invoice_address_postcode": address.get("postal_code", ""),
                "invoice_address_iso": country_iso,
                # Notes & Comments
                "customer_comments": purchase_order,
                "gift_note": "",
                "notes": [
                    f"Faire Order: {display_id}",
                    f"Retailer ID: {retailer_id}",
                    f"Order State: {order_state}",
                ],
                # Other
                "fulfilment_client_id": None,
                "custom_fields": {},
            },
            "order_inventory": [],
        }

        # ====================================================================
        # ADD ORDER ITEMS
        # ====================================================================

        for item in items:
            helm_item = {
                "inventory_id": "",  # Helm will match by SKU
                "name": item.get("product_name", ""),
                "sku": item.get("sku", ""),
                "quantity": item.get("quantity", 1),
                "unit_price": item.get("price_cents", 0) / 100,
                "line_total_discount": 0,
                "options": item.get("variant_name", ""),
                "notes": f"Product ID: {item.get('product_id', '')}",
                "hs_code": "",
                "country_of_origin": "",
            }
            helm_order["order_inventory"].append(helm_item)

            logger.info(
                f"    - {item.get('quantity')}x {item.get('sku', 'NO-SKU')} "
                f"@ GBP {item.get('price_cents', 0) / 100:.2f}"
            )

        logger.info(f"[SUCCESS] Successfully transformed order")
        return helm_order

    def _map_country_code(self, country_code: str) -> str:
        """
        Map Faire 3-letter country codes to ISO 2-letter codes.

        Faire uses 3-letter codes (e.g., CAN, USA) while Helm expects
        ISO 2-letter codes (e.g., CA, US).

        Args:
            country_code (str): 3-letter country code from Faire

        Returns:
            str: 2-letter ISO country code
        """
        country_map = {
            "CAN": "CA",  # Canada
            "USA": "US",  # United States
            "GBR": "GB",  # United Kingdom
            "AUS": "AU",  # Australia
            "FRA": "FR",  # France
            "DEU": "DE",  # Germany
            "ITA": "IT",  # Italy
            "ESP": "ES",  # Spain
            "NLD": "NL",  # Netherlands
            "BEL": "BE",  # Belgium
            "IRL": "IE",  # Ireland
        }

        # Return mapped code, or first 2 letters as fallback
        return country_map.get(country_code, country_code[:2])

    # ========================================================================
    # HELM API INTEGRATION
    # ========================================================================

    def create_helm_order(self, helm_order: Dict) -> bool:
        """
        Create an order in Helm via the API.

        API Endpoint: POST /public-api/orders/create

        Args:
            helm_order (Dict): Order object in Helm format

        Returns:
            bool: True if order was created successfully, False otherwise
        """
        order_id = helm_order["order"]["channel_order_id"]

        logger.info("-" * 60)
        logger.info(f"Creating order in Helm: {order_id}")

        # ====================================================================
        # TEST MODE: Simulate success
        # ====================================================================

        if self.test_mode:
            logger.info("[TEST MODE] Simulating successful order creation")
            logger.info(
                f"[TEST MODE] Would POST to: {self.helm_base_url}/orders/create"
            )
            logger.info(f"[TEST MODE] Order data: {json.dumps(helm_order, indent=2)}")
            return True

        # ====================================================================
        # PREPARE API REQUEST
        # ====================================================================

        headers = {
            "Authorization": f"Bearer {self.helm_api_token}",
            "Content-Type": "application/json",
        }

        # ====================================================================
        # MAKE API REQUEST
        # ====================================================================

        try:
            logger.info(f"POSTing to: {self.helm_base_url}/orders/create")

            response = requests.post(
                f"{self.helm_base_url}/orders/create",
                headers=headers,
                json=helm_order,
                timeout=30,
            )

            # Check if successful
            if response.status_code in [200, 201]:
                logger.info(f"[SUCCESS] Created order in Helm: {order_id}")
                return True
            else:
                logger.error(
                    f"[ERROR] Failed to create order: HTTP {response.status_code}"
                )
                logger.error(f"   Response: {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error(f"[ERROR] Helm API request timed out for order: {order_id}")
            return False

        except requests.exceptions.HTTPError as e:
            logger.error(f"[ERROR] Helm API HTTP error for order {order_id}: {e}")
            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"[ERROR] Helm API request failed for order {order_id}: {e}")
            return False

    # ========================================================================
    # MAIN SYNC PROCESS
    # ========================================================================

    def sync_orders(self):
        """
        Main synchronization process.

        This orchestrates the entire sync workflow:
        1. Get last sync time
        2. Fetch new orders from Faire
        3. Transform each order to Helm format
        4. Create orders in Helm
        5. Save new sync time
        6. Report summary
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("STARTING FAIRE -> HELM ORDER SYNCHRONIZATION")
        logger.info("=" * 70)
        logger.info(f"Mode: {'TEST MODE' if self.test_mode else 'PRODUCTION'}")
        logger.info(f"Time: {datetime.now().isoformat()}")
        logger.info("=" * 70)
        logger.info("")

        # ====================================================================
        # STEP 1: Get last sync time
        # ====================================================================

        last_sync = self.get_last_sync_time()
        current_sync = datetime.now()

        logger.info(f"Syncing orders from {last_sync} to {current_sync}")
        logger.info("")

        # ====================================================================
        # STEP 2: Fetch orders from Faire
        # ====================================================================

        faire_orders = self.fetch_faire_orders(last_sync)

        if not faire_orders:
            logger.info("")
            logger.info("=" * 70)
            logger.info("[INFO] No new orders to sync")
            logger.info("=" * 70)
            return

        logger.info("")

        # ====================================================================
        # STEP 3 & 4: Transform and create orders
        # ====================================================================

        success_count = 0
        fail_count = 0

        for i, faire_order in enumerate(faire_orders, 1):
            logger.info("")
            logger.info(f"Processing order {i}/{len(faire_orders)}")

            try:
                # Transform to Helm format
                helm_order = self.transform_faire_to_helm(faire_order)

                # Create in Helm
                if self.create_helm_order(helm_order):
                    success_count += 1
                else:
                    fail_count += 1

            except Exception as e:
                logger.error(f"[ERROR] Unexpected error processing order: {e}")
                logger.exception("Full traceback:")
                fail_count += 1

        # ====================================================================
        # STEP 5: Save sync time
        # ====================================================================

        self.save_sync_time(current_sync)

        # ====================================================================
        # STEP 6: Report summary
        # ====================================================================

        logger.info("")
        logger.info("=" * 70)
        logger.info("SYNCHRONIZATION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total Orders:    {len(faire_orders)}")
        logger.info(f"[SUCCESS] Successful:   {success_count}")
        logger.info(f"[FAILED] Failed:       {fail_count}")
        logger.info(
            f"Success Rate:    {(success_count / len(faire_orders) * 100):.1f}%"
        )
        logger.info("=" * 70)
        logger.info("")

    # ========================================================================
    # TEST DATA GENERATORS
    # ========================================================================

    def _get_mock_faire_orders(self) -> List[Dict]:
        """
        Generate mock Faire orders for testing.

        Returns realistic test data based on the Faire API documentation.
        """
        return [
            {
                "id": "bo_test123",
                "display_id": "TEST123",
                "created_at": "2025-10-26T10:00:00.000Z",
                "updated_at": "2025-10-26T10:00:00.000Z",
                "state": "NEW",
                "items": [
                    {
                        "id": "oi_test1",
                        "product_id": "p_test",
                        "variant_id": "po_test",
                        "quantity": 12,
                        "sku": "OCE0112",
                        "price_cents": 320,
                        "product_name": "Blood Orange - Organic 70% dark choc bar, 70g",
                        "variant_name": "default",
                    },
                    {
                        "id": "oi_test2",
                        "product_id": "p_test2",
                        "variant_id": "po_test2",
                        "quantity": 24,
                        "sku": "OCE0113",
                        "price_cents": 320,
                        "product_name": "Black Cherry - Organic 70% dark choc bar, 70g",
                        "variant_name": "default",
                    },
                ],
                "address": {
                    "name": "Test Customer",
                    "address1": "123 Test Street",
                    "address2": "",
                    "postal_code": "W1A 1AA",
                    "city": "London",
                    "state": "England",
                    "state_code": "EN",
                    "phone_number": "+447700900000",
                    "country": "United Kingdom",
                    "country_code": "GBR",
                    "company_name": "Test Shop Ltd",
                },
                "retailer_id": "r_test123",
                "purchase_order_number": "PO-TEST-001",
            }
        ]


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main():
    """
    Main entry point for the script.

    Can be run in two modes:
    1. Production mode: Uses real API credentials from environment
    2. Test mode: Uses mock data for testing without credentials
    """
    import sys

    # Check for test mode flag
    test_mode = "--test" in sys.argv or "-t" in sys.argv

    if test_mode:
        print("\n[TEST MODE] Running with mock data\n")

    try:
        # Initialize and run sync
        syncer = FaireHelmSync(test_mode=test_mode)
        syncer.sync_orders()

        # Exit successfully
        sys.exit(0)

    except ValueError as e:
        # Configuration error
        logger.error(f"[ERROR] Configuration error: {e}")
        sys.exit(1)

    except Exception as e:
        # Unexpected error
        logger.error(f"[ERROR] Fatal error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
# python faire_helm_sync.py --test
