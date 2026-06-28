"""
core/mock_broker.py
===================
Mock implementation of the BreezeConnect SDK for offline testing.
Simulates network latency and returns fake portfolio holdings.
"""

from __future__ import annotations
import time
import uuid
from typing import Any

class MockBreeze:
    """Mock ICICI Direct Breeze API Client."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session_generated = False
        
    def generate_session(self, secret_key: str, api_session: str) -> None:
        """Simulate authentication delay."""
        time.sleep(0.5)
        self.session_generated = True

    def get_portfolio_holdings(
        self,
        exchange_code: str = "",
        from_date: str = "",
        to_date: str = "",
        stock_code: str = "",
        portfolio_type: str = "",
    ) -> dict[str, Any]:
        """Simulate fetching holdings."""
        time.sleep(0.5)
        return {
            "Status": 200,
            "Success": [
                {
                    "stock_code": "RELIANCE",
                    "isin": "INE002A01018",
                    "quantity": 150,
                    "free_quantity": 150,
                    "exchange_code": "NSE",
                },
                {
                    "stock_code": "TCS",
                    "isin": "INE467B01029",
                    "quantity": 50,
                    "free_quantity": 50,
                    "exchange_code": "NSE",
                },
                {
                    "stock_code": "HDFCBANK",
                    "isin": "INE040A01034",
                    "quantity": 300,
                    "free_quantity": 300,
                    "exchange_code": "NSE",
                }
            ]
        }
        
    def gtt_single_leg_place_order(
        self,
        exchange_code: str,
        stock_code: str,
        product: str,
        action: str,
        order_type: str,
        quantity: str,
        price: str,
        trigger_price: str,
        expiry_date: str,
        right: str,
        strike_price: str,
    ) -> dict[str, Any]:
        """Simulate placing a GTT order."""
        # Note: the gtt_engine sleeps 0.2s between orders, 
        # so we don't need a huge delay here, just a tiny one to mimic network.
        time.sleep(0.05)
        
        # Simulate a 5% random failure rate just for realistic testing
        import random
        if random.random() < 0.05:
            return {
                "Status": 500,
                "Error": "Mock API random failure simulation."
            }
            
        return {
            "Status": 200,
            "Success": {
                "order_id": f"MOCK-{uuid.uuid4().hex[:8].upper()}",
                "message": "GTT Order Placed Successfully"
            }
        }
