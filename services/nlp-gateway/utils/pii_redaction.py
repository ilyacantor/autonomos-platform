from typing import Dict, List, Optional

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    AnalyzerEngine = None
    AnonymizerEngine = None
    OperatorConfig = None

from .logger import get_logger

logger = get_logger(__name__)

if not PRESIDIO_AVAILABLE:
    logger.warning(
        "⚠️ presidio-analyzer and presidio-anonymizer not installed. "
        "PII redaction disabled. "
        "Install with: pip install presidio-analyzer presidio-anonymizer"
    )


class PIIRedactor:
    """
    PII redaction wrapper using Microsoft Presidio.
    
    Detects and redacts PII entities like emails, phone numbers, 
    SSNs, credit cards, etc.
    
    Optional Dependencies:
    - presidio-analyzer: For PII detection
    - presidio-anonymizer: For PII redaction
      Without them, no redaction is performed (text returned as-is)
    """
    
    def __init__(self):
        if not PRESIDIO_AVAILABLE:
            self._initialized = False
            logger.info("PII Redactor: presidio not available, redaction disabled")
            return
            
        try:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            self._initialized = True
            logger.info("PII Redactor initialized successfully")
        except Exception as e:
            logger.warning(f"PII Redactor initialization failed: {e}. Redaction disabled.")
            self._initialized = False
    
    def redact(
        self,
        text: str,
        entities: Optional[List[str]] = None,
        language: str = "en"
    ) -> Dict[str, any]:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact
            entities: List of entity types to redact (e.g., ["EMAIL_ADDRESS", "PHONE_NUMBER"])
                     If None, redacts all supported entities
            language: Language code (default: "en")
            
        Returns:
            Dictionary with:
                - redacted_text: Text with PII redacted
                - original_text: Original text (for reference)
                - entities_found: List of detected entities
                - redacted: Boolean indicating if any PII was found
        """
        if not self._initialized:
            return {
                "redacted_text": text,
                "original_text": text,
                "entities_found": [],
                "redacted": False
            }
        
        try:
            results = self.analyzer.analyze(
                text=text,
                entities=entities,
                language=language
            )
            
            if not results:
                return {
                    "redacted_text": text,
                    "original_text": text,
                    "entities_found": [],
                    "redacted": False
                }
            
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"})
                }
            )
            
            entities_found = [
                {
                    "type": result.entity_type,
                    "start": result.start,
                    "end": result.end,
                    "score": result.score
                }
                for result in results
            ]
            
            return {
                "redacted_text": anonymized_result.text,
                "original_text": text,
                "entities_found": entities_found,
                "redacted": True
            }
            
        except Exception as e:
            logger.error(f"PII redaction failed: {e}")
            return {
                "redacted_text": text,
                "original_text": text,
                "entities_found": [],
                "redacted": False,
                "error": str(e)
            }


_redactor_instance: Optional[PIIRedactor] = None


def get_pii_redactor() -> PIIRedactor:
    """
    Get singleton PII redactor instance.
    
    Returns:
        PIIRedactor instance
    """
    global _redactor_instance
    if _redactor_instance is None:
        _redactor_instance = PIIRedactor()
    return _redactor_instance


def redact_pii(
    text: str,
    entities: Optional[List[str]] = None
) -> Dict[str, any]:
    """
    Convenience function to redact PII from text.
    
    Args:
        text: Text to redact
        entities: List of entity types to redact
        
    Returns:
        Redaction result dictionary
    """
    redactor = get_pii_redactor()
    return redactor.redact(text, entities=entities)
