from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SECRET_KEY must be set in environment.")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

domains_to_test = ["Pflege", "pflege", "Medical", "medical", "Health", "health", "CORE", "core", "General", "general"]
for d in domains_to_test:
    try:
        supabase.table("generated_texts").insert({
            "user_id": "11111111-1111-1111-1111-111111111111",
            "domain": d,
            "level": "A2",
            "anchor_word_id": 1287,
            "content": "Test content",
            "unknown_ratio": 0.1,
            "validation_passed": True
        }).execute()
        print(f"SUCCESS: {d}")
        break
    except Exception as e:
        print(f"FAILED {d}: {e}")
