import requests
import re

def fetch_and_debug():
    url = "http://localhost:9000"
    xml = """
    <ENVELOPE>
        <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
        <BODY>
            <EXPORTDATA>
                <REQUESTDESC>
                    <REPORTNAME>Voucher Register</REPORTNAME>
                    <STATICVARIABLES>
                        <SVCURRENTCOMPANY>SHREE JI SALES</SVCURRENTCOMPANY>
                    </STATICVARIABLES>
                </REQUESTDESC>
            </EXPORTDATA>
        </BODY>
    </ENVELOPE>
    """
    
    print("Fetching data from Tally...")
    try:
        response = requests.post(url, data=xml, headers={'Content-Type': 'application/xml'})
        content = response.text
        print(f"Received {len(content)} bytes.")
        
        # Find the problematic area (around line 209)
        lines = content.split('\n')
        if len(lines) > 208:
            print("\n--- Problematic Area (Lines 205-215) ---")
            for i in range(205, min(len(lines), 215)):
                print(f"Line {i+1}: {repr(lines[i])}")
        
        # Check for common invalid XML chars
        # XML 1.0 allowed characters: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
        # We look for anything NOT in that list
        invalid_xml_chars = re.compile(u'[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u10000-\u10FFFF]')
        
        invalids = []
        for i, char in enumerate(content):
            if invalid_xml_chars.match(char):
                invalids.append((i, repr(char)))
        
        if invalids:
            print(f"\nFound {len(invalids)} invalid XML characters!")
            print(f"First 5: {invalids[:5]}")
        else:
            print("\nNo standard invalid XML characters found by regex.")
            
        # Try parsing to confirm error
        import xml.etree.ElementTree as ET
        try:
            ET.fromstring(content)
            print("\n✅ Parsing SUCCESSFUL (No error this time?)")
        except ET.ParseError as e:
            print(f"\n❌ Parsing FAILED: {e}")

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    fetch_and_debug()
