import requests
import xml.etree.ElementTree as ET

url = "http://localhost:9000"

def check_tally():
    # Attempt to get list of companies
    xml = """<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Export Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Companies</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
    </ENVELOPE>"""
    
    try:
        print(f"Connecting to {url}...")
        resp = requests.post(url, data=xml, headers={"Content-Type": "application/xml"}, timeout=5)
        print(f"Status: {resp.status_code}")
        print("Response Snippet:")
        print(resp.text[:1000])
        
        # Check for Period info if available or just Company Names
        if "Krishasales" in resp.text:
            print("\n✅ Found 'Krishasales' in open companies.")
        else:
            print("\n⚠️ 'Krishasales' NOT found in List of Companies report.")
            
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    check_tally()
