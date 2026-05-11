import sys
import os
sys.path.append(os.getcwd())

import pytest
from utils.privacy_vault import PrivacyVault

def test_privacy_vault_masking():
    vault = PrivacyVault()
    text = "My name is John Doe and I work for Google."
    masked = vault.mask(text)
    
    assert "John Doe" not in masked
    assert "Google" not in masked
    assert "<PERSON_" in masked
    assert "<ORG_" in masked

def test_privacy_vault_unmasking():
    vault = PrivacyVault()
    text = "Contact Alice at 123-456-7890."
    masked = vault.mask(text)
    unmasked = vault.unmask(masked)
    
def test_router_logic():
    # 100% REAL TEST - No Mocks or Ghosts
    from core.router import router
    
    greeting = router.route("Hello there!")
    assert greeting.category == "GREETING"
    
    query = router.route("What are the laws on theft?")
    assert query.category == "LEGAL_QUERY"
