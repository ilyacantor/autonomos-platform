"""Chaos injection utilities for simulating API failures."""
import random
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from models import ErrorProfile, NetworkProfile


class ChaosEngine:
    """Injects controlled chaos into API responses."""
    
    def __init__(self):
        self.chaos_level = "mild"  # mild | storm | hell
        self.error_rates = {
            "mild": 0.05,
            "storm": 0.20,
            "hell": 0.50
        }
        self.rate_limit_multipliers = {
            "mild": 1.0,
            "storm": 0.5,
            "hell": 0.2
        }
    
    def set_chaos_level(self, level: str):
        """Update the global chaos level."""
        if level in self.error_rates:
            self.chaos_level = level
    
    def should_inject_error(self, profile: ErrorProfile) -> bool:
        """Determine if an error should be injected based on profile and chaos level."""
        base_rate = self.error_rates[self.chaos_level]
        
        # Adjust based on error profile
        profile_multipliers = {
            ErrorProfile.AGGRESSIVE_RATE_LIMIT: 2.0,
            ErrorProfile.FLAKY_5XX: 1.5,
            ErrorProfile.MOSTLY_OK: 0.3,
            ErrorProfile.SPIKY_RATE_LIMIT: 1.8
        }
        
        adjusted_rate = base_rate * profile_multipliers.get(profile, 1.0)
        return random.random() < adjusted_rate
    
    def get_error_response(self, profile: ErrorProfile) -> Dict[str, Any]:
        """Generate an error response based on the profile."""
        if profile == ErrorProfile.AGGRESSIVE_RATE_LIMIT:
            return {
                "status_code": 429,
                "error": "rate_limit_exceeded",
                "message": "Too many requests",
                "retry_after": random.randint(1, 10)
            }
        elif profile == ErrorProfile.FLAKY_5XX:
            error_codes = [500, 502, 503, 504]
            return {
                "status_code": random.choice(error_codes),
                "error": "server_error",
                "message": "Internal server error"
            }
        elif profile == ErrorProfile.SPIKY_RATE_LIMIT:
            # Spike every few seconds
            if datetime.now().second % 10 < 3:
                return {
                    "status_code": 429,
                    "error": "rate_limit_exceeded",
                    "message": "Temporary rate limit spike",
                    "retry_after": random.randint(1, 5)
                }
        
        # Default to 503 Service Unavailable
        return {
            "status_code": 503,
            "error": "service_unavailable",
            "message": "Service temporarily unavailable"
        }
    
    async def inject_network_delay(self, profile: NetworkProfile):
        """Inject network delays based on profile."""
        if profile == NetworkProfile.DNS_FLAKINESS:
            if random.random() < 0.1:  # 10% chance of DNS delay
                await asyncio.sleep(random.uniform(1, 5))
        elif profile == NetworkProfile.TLS_FLAKINESS:
            if random.random() < 0.05:  # 5% chance of TLS handshake delay
                await asyncio.sleep(random.uniform(0.5, 3))
        elif profile == NetworkProfile.TIMEOUT_PROBABILITY:
            if random.random() < 0.02:  # 2% chance of timeout
                await asyncio.sleep(30)  # Simulate timeout
    
    def get_rate_limit_adjustment(self) -> float:
        """Get the rate limit multiplier based on chaos level."""
        return self.rate_limit_multipliers[self.chaos_level]


class DriftSimulator:
    """Simulates schema drift over time."""
    
    def __init__(self):
        self.call_counts = {}  # Track calls per service
        self.drift_states = {}  # Track current drift state per service
    
    def record_call(self, service_id: str):
        """Record an API call for drift tracking."""
        if service_id not in self.call_counts:
            self.call_counts[service_id] = 0
        self.call_counts[service_id] += 1
    
    def should_drift(self, service_id: str, drift_action: Dict[str, Any]) -> bool:
        """Check if drift should occur based on triggers."""
        if drift_action["trigger"] == "calls_count":
            calls = self.call_counts.get(service_id, 0)
            return calls >= drift_action["threshold"]
        return False
    
    def apply_drift(self, data: Dict[str, Any], drift_action: Dict[str, Any]) -> Dict[str, Any]:
        """Apply drift transformation to response data."""
        if drift_action["action"] == "rename_field":
            if drift_action["from_field"] in data:
                data[drift_action["to_field"]] = data.pop(drift_action["from_field"])
        elif drift_action["action"] == "add_field":
            if drift_action["new_field"]:
                data[drift_action["new_field"]["name"]] = self._get_default_value(
                    drift_action["new_field"]["type"]
                )
        elif drift_action["action"] == "remove_field":
            data.pop(drift_action["from_field"], None)
        
        return data
    
    def _get_default_value(self, field_type: str) -> Any:
        """Get a default value based on field type."""
        defaults = {
            "string": "",
            "integer": 0,
            "number": 0.0,
            "boolean": False,
            "array": [],
            "object": {}
        }
        return defaults.get(field_type, None)