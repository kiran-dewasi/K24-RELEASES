
import os

target_dir = r"c:\Users\kiran\OneDrive\Desktop\we are\frontend\src"
old_port = "8001"
new_port = "8000"

print(f"Replacing {old_port} with {new_port} in {target_dir}...")

count = 0
for root, dirs, files in os.walk(target_dir):
    for file in files:
        if file.endswith(".tsx") or file.endswith(".ts"):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if old_port in content:
                    print(f"Fixing: {filepath}")
                    new_content = content.replace(old_port, new_port)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    count += 1
            except Exception as e:
                print(f"Skipping {filepath}: {e}")

print(f"Done! Updated {count} files.")
