"""
AAM test data fixtures for populating Redis streams.

Provides realistic AAM canonical event data matching production format.
"""
from typing import Dict, Any, List


def get_salesforce_aam_data() -> List[Dict[str, Any]]:
    """
    Get Salesforce AAM canonical events for testing.
    
    Returns list of canonical events matching AAM connector output format.
    Each event has a batch_id and tables with schema and samples.
    """
    return [
        {
            "batch_id": "test-salesforce-batch-001",
            "tables": {
                "Account": {
                    "schema": {
                        "Id": "string",
                        "Name": "string", 
                        "Industry": "string",
                        "AnnualRevenue": "numeric"
                    },
                    "samples": [
                        {"Id": "001xx000003DGb2AAG", "Name": "Acme Corp", "Industry": "Technology", "AnnualRevenue": 5000000},
                        {"Id": "001xx000003DGb3AAG", "Name": "Global Industries", "Industry": "Manufacturing", "AnnualRevenue": 12000000}
                    ]
                },
                "Opportunity": {
                    "schema": {
                        "Id": "string",
                        "Name": "string",
                        "Amount": "numeric",
                        "StageName": "string",
                        "AccountId": "string"
                    },
                    "samples": [
                        {"Id": "006xx000001Sv2fAAC", "Name": "Big Deal", "Amount": 250000, "StageName": "Closed Won", "AccountId": "001xx000003DGb2AAG"},
                        {"Id": "006xx000001Sv2gAAC", "Name": "Major Contract", "Amount": 500000, "StageName": "Negotiation", "AccountId": "001xx000003DGb3AAG"}
                    ]
                }
            }
        }
    ]


def get_hubspot_aam_data() -> List[Dict[str, Any]]:
    """
    Get HubSpot AAM canonical events for testing.
    
    Returns list of canonical events matching AAM connector output format.
    """
    return [
        {
            "batch_id": "test-hubspot-batch-001",
            "tables": {
                "Company": {
                    "schema": {
                        "id": "string",
                        "name": "string",
                        "domain": "string",
                        "industry": "string"
                    },
                    "samples": [
                        {"id": "123456", "name": "TechStart Inc", "domain": "techstart.com", "industry": "SaaS"},
                        {"id": "123457", "name": "Enterprise Co", "domain": "enterprise.com", "industry": "Enterprise"}
                    ]
                },
                "Deal": {
                    "schema": {
                        "id": "string",
                        "dealname": "string",
                        "amount": "numeric",
                        "dealstage": "string",
                        "company_id": "string"
                    },
                    "samples": [
                        {"id": "987654", "dealname": "Q4 Enterprise Deal", "amount": 150000, "dealstage": "closedwon", "company_id": "123456"},
                        {"id": "987655", "dealname": "Annual Contract", "amount": 300000, "dealstage": "proposal", "company_id": "123457"}
                    ]
                }
            }
        }
    ]


def get_dynamics_aam_data() -> List[Dict[str, Any]]:
    """
    Get Dynamics 365 AAM canonical events for testing.
    
    Returns list of canonical events matching AAM connector output format.
    """
    return [
        {
            "batch_id": "test-dynamics-batch-001",
            "tables": {
                "account": {
                    "schema": {
                        "accountid": "string",
                        "name": "string",
                        "revenue": "numeric",
                        "industrycode": "string"
                    },
                    "samples": [
                        {"accountid": "d365-001", "name": "Microsoft Partner", "revenue": 8000000, "industrycode": "IT"},
                        {"accountid": "d365-002", "name": "Azure Customer", "revenue": 3000000, "industrycode": "Cloud"}
                    ]
                }
            }
        }
    ]
