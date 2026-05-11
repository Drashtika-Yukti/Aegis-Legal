import spacy
import uuid
import re
from typing import Dict

from core.logger import get_logger

logger = get_logger("PrivacyVault")

class PrivacyVault:
    """
    Production-grade PII masking via local spaCy NER.
    """
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_md")
        except Exception as e:
            logger.warning("⚠️  spaCy model 'en_core_web_md' not found. PII masking will be inactive.")
            logger.warning("To fix this, run: python -m spacy download en_core_web_md")
            self.nlp = None
            
        self.mapping: Dict[str, str] = {}
        self.pii_labels = {"PERSON", "FAC", "LOC"} # Focusing on Person and Location/Address
        
        # Patterns for high-sensitivity identifiers
        self.patterns = {
            "EMAIL": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            "PHONE": re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
            "CARD": re.compile(r'\b(?:\d[ -]*?){13,16}\b'), # Simple card pattern
            "SSN": re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        }

    def mask(self, text: str) -> str:
        if not text or not self.nlp:
            return text
            
        masked_text = text
        
        # 1. Pattern-based Masking (Higher priority)
        for label, pattern in self.patterns.items():
            matches = pattern.findall(masked_text)
            for match in set(matches):
                placeholder = self._get_placeholder(match, label)
                masked_text = masked_text.replace(match, placeholder)

        # 2. NER Masking (Person & Locations)
        doc = self.nlp(masked_text)
        # Use reversed to avoid index shifting if we were using string slicing, 
        # but here we'll use replace for simplicity as patterns already ran.
        for ent in doc.ents:
            if ent.label_ in self.pii_labels:
                placeholder = self._get_placeholder(ent.text, ent.label_)
                masked_text = masked_text.replace(ent.text, placeholder)

        return masked_text

    def _get_placeholder(self, original: str, label: str) -> str:
        # Check if already mapped
        for p, v in self.mapping.items():
            if v == original: return p
        
        placeholder = f"<{label}_{uuid.uuid4().hex[:4].upper()}>"
        self.mapping[placeholder] = original
        return placeholder

    def unmask(self, text: str) -> str:
        unmasked_text = text
        for p, v in self.mapping.items():
            bare_id = p.strip("<>")
            pattern = re.compile(f"<{bare_id}>|{bare_id}")
            unmasked_text = pattern.sub(v, unmasked_text)
        return unmasked_text

    def reset(self):
        self.mapping = {}

vault = PrivacyVault()
