from supabase import create_client, Client
from core.config import settings
from core.logger import get_logger
import asyncio

logger = get_logger("SupabaseAuth")

class SupabaseAuth:
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        self.supabase: Client = create_client(self.url, self.key)
        logger.info("Supabase Client Initialized with Service Role.")

    async def get_next_id(self) -> int:
        """Fetch the next available 4-digit ID starting from 1000."""
        try:
            response = self.supabase.table("aegis_users").select("id").order("id", desc=True).limit(1).execute()
            if not response.data:
                return 1000
            last_id = response.data[0]["id"]
            if last_id < 1000: return 1000
            return last_id + 1
        except Exception as e:
            logger.error(f"Error fetching next ID: {e}")
            return 1000

    async def create_user(self, user_data: dict):
        """Insert a new user into the aegis_users table."""
        try:
            # Assign the 4-digit ID
            user_data["id"] = await self.get_next_id()
            response = self.supabase.table("aegis_users").insert(user_data).execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Supabase Create User Error: {e}")
            raise e

    async def get_user_by_username(self, username: str):
        """Fetch user details by username."""
        try:
            response = self.supabase.table("aegis_users").select("*").eq("username", username).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Supabase Fetch User Error: {e}")
            return None

    async def update_password(self, username: str, hashed_password: str):
        """Update password for a user."""
        try:
            response = self.supabase.table("aegis_users").update({"hashed_password": hashed_password}).eq("username", username).execute()
            return response.data
        except Exception as e:
            logger.error(f"Supabase Update Password Error: {e}")
            raise e

    async def log_document(self, user_id: str, filename: str, metadata: dict):
        """Sync document ingestion metadata to Supabase."""
        try:
            data = {
                "user_id": user_id,
                "filename": filename,
                "metadata": metadata,
            }
            # Note: Supabase handles created_at/now() by default if configured
            self.supabase.table("aegis_documents").insert(data).execute()
            logger.info(f"Cloud Sync: Logged document {filename} for User {user_id}")
        except Exception as e:
            logger.error(f"Supabase Doc Logging Error: {e}")

supabase_auth = SupabaseAuth()
