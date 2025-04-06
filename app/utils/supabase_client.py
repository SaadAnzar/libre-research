import os
from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()


def get_supabase_client() -> Client:
    # Initialize supabase client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)

    return supabase
