import os
from supabase import create_client, Client
from core.logger import get_logger

logger = get_logger("SupabaseClient")

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.warning("⚠️  Supabase configuration missing. Database features will be inactive.")
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
        return None

# Global instance with safe initialization
supabase_client = get_supabase_client()
