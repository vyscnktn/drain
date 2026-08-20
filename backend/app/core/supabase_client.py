from supabase import create_client, Client
from app.core.config import settings

# Initialize the Supabase client with the Service Role Key.
# IMPORTANT: This client bypasses RLS. It should only be used in secure backend routes
# and never exposed directly to the client frontend.
supabase_admin: Client = create_client(settings.supabase_url, settings.supabase_secret_key)
