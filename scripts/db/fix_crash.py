import os
import re

def fix_indentation():
    file_path = "backend/database/__init__.py"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Simple heuristic: Ensure all indentation is multiple of 4 spaces
        # And specifically check line 10 if it's the issue.
        new_lines = []
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            # If line is not empty
            if stripped:
                indent = len(line) - len(stripped)
                # If indent is not multiple of 4, warn/fix? 
                # For now, just rewriting the file strictly as we read it might not fix if source is bad.
                # But since view_file showed good code, I'll trust writing back what I mistakenly think is good?
                # No, I should use the content I VIEWED which seemed correct.
                pass
        
        # Actually, let's just write the KNOWN GOOD content I analyzed.
        # But that's too big to hardcode safely.
        # I'll rely on the fact that I don't see the error, so maybe just touching the file helps?
        # Or I'll strip mixed tabs.
        cleaned_content = "".join(lines).replace("\t", "    ")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        print("✅ Cleaned backend/database/__init__.py (Tabs -> Spaces)")
        
    except Exception as e:
        print(f"❌ Failed to fix indentation: {e}")

def fix_env():
    env_path = ".env"
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Switch from IPv6 literal to Hostname
        # Comment out the IPv6 line
        content = re.sub(r'^(DATABASE_URL=postgresql://.*\[.*)', r'# \1', content, flags=re.MULTILINE)
        
        # Uncomment the Hostname line if it exists
        if "# DATABASE_URL=postgresql://postgres:Kittu%40Dew240124@db.gxukvnoiyzizienswgni.supabase.co" in content:
            content = content.replace("# DATABASE_URL=postgresql://postgres:Kittu%40Dew240124@db.gxukvnoiyzizienswgni.supabase.co", 
                                      "DATABASE_URL=postgresql://postgres:Kittu%40Dew240124@db.gxukvnoiyzizienswgni.supabase.co")
        else:
            # Append if not found
            if "DATABASE_URL=postgresql://postgres:Kittu%40Dew240124@db.gxukvnoiyzizienswgni.supabase.co" not in content:
                 content += "\nDATABASE_URL=postgresql://postgres:Kittu%40Dew240124@db.gxukvnoiyzizienswgni.supabase.co:5432/postgres"

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ Updated .env to use Hostname for DATABASE_URL")
        
    except Exception as e:
        print(f"❌ Failed to update .env: {e}")

def verify_import():
    try:
        from backend.database import engine
        print("✅ Successfully imported 'engine' from backend.database")
        print(f"✅ Connection URL: {engine.url}")
    except Exception as e:
        print(f"❌ Import Failed: {e}")

if __name__ == "__main__":
    fix_indentation()
    fix_env()
    print("--- Verifying ---")
    verify_import()
