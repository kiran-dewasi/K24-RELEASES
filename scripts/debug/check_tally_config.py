import os
from dotenv import load_dotenv
from backend.tally_connector import TallyConnector

load_dotenv()

print("=" * 60)
print("TALLY CONFIGURATION CHECK")
print("=" * 60)

# Check environment variables
print("\n📋 Environment Variables:")
print(f"TALLY_URL: {os.getenv('TALLY_URL', 'http://localhost:9000')}")
print(f"TALLY_LIVE_UPDATE_ENABLED: {os.getenv('TALLY_LIVE_UPDATE_ENABLED', 'false')}")
print(f"API_KEY: {os.getenv('API_KEY', 'k24-secret-key-123')}")
print(f"GOOGLE_API_KEY: {'SET' if os.getenv('GOOGLE_API_KEY') else 'NOT SET'}")

# Test Tally connection
print("\n🔌 Testing Tally Connection...")
try:
    connector = TallyConnector(url=os.getenv('TALLY_URL', 'http://localhost:9000'))
    df = connector.fetch_ledgers_full("SHREE JI SALES")
    print(f"✅ Connected! Found {len(df)} ledgers")
    
    # Search for Prince Enterprises
    print("\n🔍 Searching for 'Prince Enterprises'...")
    if 'NAME' in df.columns:
        matches = df[df['NAME'].str.contains('prince', case=False, na=False)]
        if not matches.empty:
            print(f"✅ Found {len(matches)} matching parties:")
            for idx, row in matches.iterrows():
                print(f"   - {row.get('NAME', 'N/A')} | GSTIN: {row.get('GSTIN', 'N/A')}")
        else:
            print("❌ No parties found matching 'Prince'")
            print("\n📝 Available parties (first 10):")
            for i, name in enumerate(df['NAME'].head(10)):
                print(f"   {i+1}. {name}")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")

print("\n" + "=" * 60)
