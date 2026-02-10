
import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fetch_purchase_sample():
    url = "http://localhost:9000"
    
    # Request 1: Get List of Purchase Vouchers
    # TDL to fetch one voucher date/number
    tdl = """<ENVELOPE>
        <HEADER>
            <TALLYREQUEST>Export Data</TALLYREQUEST>
        </HEADER>
        <BODY>
            <EXPORTDATA>
                <REQUESTDESC>
                    <REPORTNAME>Vouchers</REPORTNAME>
                    <STATICVARIABLES>
                        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                        <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
                    </STATICVARIABLES>
                </REQUESTDESC>
            </EXPORTDATA>
        </BODY>
    </ENVELOPE>"""
    
    try:
        print("Fetching Purchase Voucher Sample...")
        resp = requests.post(url, data=tdl, headers={'Content-Type': 'text/xml'})
        with open("purchase_sample.xml", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("Saved to purchase_sample.xml")
        
        # Print first 20 lines
        lines = resp.text.split('\n')
        for l in lines[:50]:
            print(l)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_purchase_sample()
