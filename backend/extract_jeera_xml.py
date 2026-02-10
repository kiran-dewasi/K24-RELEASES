import os

try:
    with open(r"c:\Users\kiran\OneDrive\Desktop\we are\backend\full_dump.xml", "r", encoding="utf-8") as f:
        data = f.read()
        target = "Super Jeera"
        idx = data.find(target)
        if idx != -1:
            # Find start of INVENTORY entry
            start = data.rfind("<ALLINVENTORYENTRIES.LIST>", 0, idx)
            # Find end of INVENTORY entry
            end = data.find("</ALLINVENTORYENTRIES.LIST>", idx)
            if start != -1 and end != -1:
                print("✅ CLONE TARGET (Inventory Block):")
                print(data[start:end+27]) # + length of closing tag
            else:
                print("Could not isolate inventory block")
        else:
            print("Target not found")
except Exception as e:
    print(f"Error: {e}")
