"""Llama Guard security module for input validation and prompt injection defense."""
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LlamaGuard:
    """Input validation and security using Llama Guard patterns."""

    def __init__(self):
        """Initialize Llama Guard security module."""
        # Common prompt injection patterns
        self.injection_patterns = [
            # Direct instruction overrides
            r'\b(ignore|override|disregard)\s+(previous|prior|all)\s+(instructions?|rules?|prompts?)\b',
            r'\bforget\s+(your|the)\s+(previous|prior|original)\s+(instructions?|rules?)\b',

            # System prompt manipulation
            r'\b(you\s+are|act\s+as|pretend\s+to\s+be|role-play\s+as)\s+a\s+(different|new|unrestricted)\s+(ai|assistant|model)\b',
            r'\b(break|violate|ignore)\s+(character|role|persona|restrictions)\b',

            # Jailbreak attempts
            r'\b(dan|developer\s+mode|uncensored|unfiltered)\b',
            r'\b(jailbreak|hacking|exploit)\b',

            # Dangerous instructions
            r'\b(delete|remove|erase)\s+(all\s+)?data\b',
            r'\b(drop\s+table|truncate\s+table|alter\s+table)\b',
            r'\b(system|shell|command|exec|eval)\s*\(',
            r'\bimport\s+(os|subprocess|sys)\b',

            # SQL injection patterns
            r'(\b(select|insert|update|delete|drop|create|alter)\s+.*\bfrom\b.*;)',
            r'(\bunion\s+select\b|\bscript\b.*\bselect\b)',

            # XSS patterns
            r'(<script|javascript:|on\w+\s*=)',
        ]

        # Safe keywords that should not trigger false positives
        self.safe_keywords = [
            'insurance', 'policy', 'claim', 'vehicle', 'driver', 'premium',
            'underwriting', 'risk', 'assessment', 'commercial', 'auto',
            'motor', 'truck', 'fleet', 'safety', 'violation'
        ]

    def validate_input(self, text: str, context: str = "general") -> Dict:
        """Validate input text for security issues."""
        if not text or not text.strip():
            return {
                "safe": True,
                "confidence": 1.0,
                "issues": [],
                "recommendation": "allow"
            }

        issues = []
        confidence = 0.0

        # Check for injection patterns
        for pattern in self.injection_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                issues.extend([f"Pattern match: {match[:50]}..." for match in matches])
                confidence = max(confidence, 0.8)  # High confidence for pattern matches

        # Check for suspicious keywords combinations
        suspicious_combinations = self._check_suspicious_combinations(text)
        if suspicious_combinations:
            issues.extend(suspicious_combinations)
            confidence = max(confidence, 0.6)

        # Check for encoding tricks
        encoding_issues = self._check_encoding_tricks(text)
        if encoding_issues:
            issues.extend(encoding_issues)
            confidence = max(confidence, 0.7)

        # Context-specific checks
        if context == "company_search":
            context_issues = self._validate_company_search(text)
            issues.extend(context_issues)

        # Determine safety and recommendation
        safe = len(issues) == 0
        recommendation = "allow" if safe else "block"

        # Log security events
        if not safe:
            logger.warning(f"Security issue detected in {context}: {issues[:3]}")

        return {
            "safe": safe,
            "confidence": confidence,
            "issues": issues,
            "recommendation": recommendation,
            "context": context
        }

    def _check_suspicious_combinations(self, text: str) -> List[str]:
        """Check for suspicious keyword combinations."""
        issues = []
        text_lower = text.lower()

        # Check for instruction override attempts
        if any(word in text_lower for word in ['ignore', 'disregard', 'override']) and \
           any(word in text_lower for word in ['previous', 'prior', 'original', 'instructions']):
            issues.append("Instruction override attempt detected")

        # Check for role manipulation
        if any(phrase in text_lower for phrase in ['act as', 'pretend to be', 'you are a']):
            issues.append("Role manipulation attempt detected")

        # Check for dangerous commands
        dangerous_commands = ['rm -rf', 'format c:', 'del *', 'shutdown', 'reboot']
        for cmd in dangerous_commands:
            if cmd in text_lower:
                issues.append(f"Dangerous command detected: {cmd}")

        return issues

    def _check_encoding_tricks(self, text: str) -> List[str]:
        """Check for encoding tricks and obfuscation."""
        issues = []

        # Check for base64-like strings (long strings with only base64 chars)
        base64_pattern = r'[A-Za-z0-9+/]{50,}'
        if re.search(base64_pattern, text):
            issues.append("Potential base64 encoded content detected")

        # Check for excessive special characters
        special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s]', text)) / len(text) if text else 0
        if special_char_ratio > 0.3:
            issues.append("High special character ratio detected")

        # Check for repeated characters (potential obfuscation)
        if re.search(r'(.)\1{10,}', text):  # 10+ repeated characters
            issues.append("Repeated character pattern detected")

        return issues

    def _validate_company_search(self, text: str) -> List[str]:
        """Context-specific validation for company search queries."""
        issues = []

        # Check for overly complex queries that might hide injection
        if len(text.split()) > 20:
            issues.append("Query too complex for company search")

        # Check for non-company related terms that might indicate misuse
        suspicious_terms = ['password', 'admin', 'root', 'sudo', 'exploit']
        text_lower = text.lower()
        for term in suspicious_terms:
            if term in text_lower:
                issues.append(f"Suspicious term in company search: {term}")

        return issues

    def sanitize_input(self, text: str) -> str:
        """Sanitize input by removing or neutralizing dangerous content."""
        # Remove or neutralize dangerous patterns
        sanitized = text

        # Remove script tags and javascript
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)

        # Remove SQL injection attempts
        sanitized = re.sub(r'(\b(select|insert|update|delete|drop|create|alter)\s+.*;)', '', sanitized, flags=re.IGNORECASE)

        # Remove system command attempts
        sanitized = re.sub(r'\b(system|shell|exec|eval)\s*\(', '', sanitized, flags=re.IGNORECASE)

        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000] + "..."

        return sanitized.strip()

    def get_security_stats(self) -> Dict:
        """Get security statistics (for monitoring)."""
        return {
            "patterns_monitored": len(self.injection_patterns),
            "safe_keywords": len(self.safe_keywords),
            "validation_enabled": True
        }


def validate_company_input(company_name: str) -> Dict:
    """Convenience function to validate company search input."""
    guard = LlamaGuard()
    return guard.validate_input(company_name, context="company_search")


def validate_document_content(content: str) -> Dict:
    """Convenience function to validate document content."""
    guard = LlamaGuard()
    return guard.validate_input(content, context="document")


def sanitize_search_query(query: str) -> str:
    """Convenience function to sanitize search queries."""
    guard = LlamaGuard()
    return guard.sanitize_input(query)