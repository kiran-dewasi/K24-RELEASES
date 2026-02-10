import requests
import re

def check_ledger_group():
    url = "http://localhost:9000"
    
    # The XML request provided by the user
    xml_request = """<ENVELOPE> <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER> <BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME> <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><ACCOUNTTYPE>Ledgers</ACCOUNTTYPE></STATICVARIABLES> <TDL><OBJECT NAME="Ledger"><FETCH>Name,Parent</FETCH></OBJECT></TDL> </REQUESTDESC></EXPORTDATA></BODY> </ENVELOPE>"""
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, data=xml_request)
        response.raise_for_status()
        
        content = response.text
        
        # Regex to find Ledger objects. Tally XML is usually <LEDGER ...> ... </LEDGER>
        # We look for the specific Name "Prince Enterprises"
        
        # 1. Try to find the specific block directly associated with Prince Enterprises
        # Valid patterns:
        # <LEDGER NAME="Prince Enterprises" ...> or <NAME>Prince Enterprises</NAME> inside LEDGER
        
        print("Searching response text for 'Prince Enterprises'...")
        
        # Simple string search first
        if "Prince Enterprises" not in content:
            print("Prince Enterprises not found in response text.")
            return

        # Use regex to find the LEDGER block containing Prince Enterprises
        # We try to grab the chunk around it.
        
        # Regex explanation:
        # <LEDGER.*?  -> start of ledger tag
        # (?:NAME="Prince Enterprises"|<NAME>Prince Enterprises</NAME>) -> strict name match
        # .*?         -> content
        # <PARENT>(.*?)</PARENT> -> capture parent
        # .*?         -> more content
        # </LEDGER>   -> end tag
        
        # Since the order of tags isn't guaranteed, we might just look for the block containing the name.
        
        ledger_blocks = re.findall(r'<LEDGER.*?/LEDGER>', content, re.DOTALL)
        
        found = False
        target_name = "Prince Enterprises"
        
        for block in ledger_blocks:
            if f'NAME="{target_name}"' in block or f'<NAME>{target_name}</NAME>' in block:
                parent_match = re.search(r'<PARENT>(.*?)</PARENT>', block)
                if parent_match:
                    print(f"Parent: {parent_match.group(1)}")
                else:
                    print("Parent tag not found in the Ledger block.")
                    # check for PARENT attribute just in case
                    parent_attr_match = re.search(r'PARENT="(.*?)"', block)
                    if parent_attr_match:
                        print(f"Parent (Attr): {parent_attr_match.group(1)}")
                    else:
                        print(f"Debug - Block content: {block[:200]}...") # print start of block
                found = True
                break
        
        if not found:
            # Fallback for lenient search (case insensitive or partial?)
            print("Exact match not found in parsed blocks. Checking raw context...")
            idx = content.find("Prince Enterprises")
            start = max(0, idx - 100)
            end = min(len(content), idx + 200)
            print(f"Context: ...{content[start:end]}...")

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Tally. Is Tally running on port 9000?")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_ledger_group()
