#!/usr/bin/env python3
# K24 Socket.IO Removal Script -- Changes 2-4
# Run from: c:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare
import re
import os

BASE = os.path.dirname(os.path.abspath(__file__))

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def check_no_pattern(content, pattern, filepath):
    matches = re.findall(pattern, content)
    if matches:
        print("  FAIL: Still found '%s' in %s" % (pattern, os.path.basename(filepath)))
        return False
    print("  OK: No '%s' in %s" % (pattern, os.path.basename(filepath)))
    return True

# =======================================================
# CHANGE 2 -- tally_live_update.py
# =======================================================
print("\n=== Change 2: tally_live_update.py ===")
path = os.path.join(BASE, "backend", "tally_live_update.py")
content = read_file(path)

# Block A: in post_to_tally_async -- remove socket try block, keep HTTP fallback
block_a_pattern = re.compile(
    r'    # 1\. Try Socket\.IO Agent First\r?\n'
    r'    try:\r?\n'
    r'        from socket_manager import socket_manager\r?\n'
    r'        \r?\n'
    r'        if socket_manager\.active_tenants:.*?'
    r'    except Exception as e:\r?\n'
    r'         print\(f"[^"]*Agent Dispatch Error \(Async\)[^"]*"\)\r?\n'
    r'\r?\n'
    r'    # 2\. Fallback to Direct HTTP',
    re.DOTALL
)
if block_a_pattern.search(content):
    content = block_a_pattern.sub('    # Direct HTTP to Tally', content)
    print("  OK: Block A (async) removed")
else:
    print("  FAIL: Block A not found -- showing line range:")
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'Socket.IO Agent First' in line or 'socket_manager.active_tenants' in line:
            print("    Line %d: %r" % (i+1, line[:80]))

# Block B: in post_to_tally (sync) -- remove socket try block, keep HTTP fallback
block_b_pattern = re.compile(
    r'    # 1\. Try Socket\.IO Agent First\r?\n'
    r'    try:\r?\n'
    r'        from socket_manager import socket_manager\r?\n'
    r'        import asyncio\r?\n'
    r'        \r?\n'
    r'        if socket_manager\.active_tenants:.*?'
    r'    except ImportError:\r?\n'
    r'        pass\r?\n'
    r'    except Exception as e:\r?\n'
    r'         print\(f"[^"]*Agent Dispatch Error[^"]*"\)\r?\n'
    r'\r?\n'
    r'    # 2\. Fallback to Direct HTTP',
    re.DOTALL
)
if block_b_pattern.search(content):
    content = block_b_pattern.sub('    # Direct HTTP to Tally', content)
    print("  OK: Block B (sync) removed")
else:
    print("  FAIL: Block B not found -- showing relevant lines:")
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'socket_manager' in line or 'execute_sync' in line:
            print("    Line %d: %r" % (i+1, line[:80]))

write_file(path, content)
check_no_pattern(content, 'socket_manager', path)
for kw in ['localhost:9000', 'TALLY_URL', 'requests.post']:
    print("    '%s' present: %s" % (kw, kw in content))

# =======================================================
# CHANGE 3 -- backend/routers/sync.py
# Remove one import line
# =======================================================
print("\n=== Change 3: routers/sync.py ===")
path = os.path.join(BASE, "backend", "routers", "sync.py")
content = read_file(path)

removed = False
for variant in ["    from socket_manager import socket_manager\n",
                "    from socket_manager import socket_manager\r\n"]:
    if variant in content:
        content = content.replace(variant, "")
        print("  OK: Import removed from sync.py")
        removed = True
        break
if not removed:
    print("  FAIL: pattern not found in sync.py")

write_file(path, content)
check_no_pattern(content, 'socket_manager', path)

# =======================================================
# CHANGE 4 -- backend/api.py
# =======================================================
print("\n=== Change 4: api.py ===")
path = os.path.join(BASE, "backend", "api.py")
content = read_file(path)

# 4A: Remove startup_event socket block (lines ~366-370, no ENABLE_SOCKET_IO guard)
# "        # Capture Main Loop for Socket Manager Thread-Safety\n..."
block4a = re.compile(
    r'        # Capture Main Loop for Socket Manager Thread-Safety\r?\n'
    r'        import asyncio\r?\n'
    r'        loop = asyncio\.get_running_loop\(\)\r?\n'
    r'        from socket_manager import socket_manager\r?\n'
    r'        socket_manager\.set_main_loop\(loop\)\r?\n'
    r'        \r?\n'
)
if block4a.search(content):
    content = block4a.sub('        \n', content)
    print("  OK: Block 4A removed (startup_event)")
else:
    print("  FAIL: Block 4A not found")

# 4B: Remove lifespan ENABLE_SOCKET_IO block (lines ~118-127)
block4b = re.compile(
    r'    # Capture the running event loop for the Socket manager \(OPTIONAL\)\r?\n'
    r'    # \(Only required to bridge synchronous Celery threads to async SocketIO\)\r?\n'
    r'    if os\.getenv\("ENABLE_SOCKET_IO", "false"\)\.lower\(\) == "true":\r?\n'
    r'        try:\r?\n'
    r'            from socket_manager import socket_manager\r?\n'
    r'            loop = asyncio\.get_running_loop\(\)\r?\n'
    r'            socket_manager\.set_main_loop\(loop\)\r?\n'
    r'            logger\.info\("[^"]*"\)\r?\n'
    r'        except Exception as e:\r?\n'
    r'            logger\.warning\(f"[^"]*"\)\r?\n'
    r'    \r?\n'
)
if block4b.search(content):
    content = block4b.sub('    \n', content)
    print("  OK: Block 4B removed (lifespan ENABLE_SOCKET_IO)")
else:
    print("  FAIL: Block 4B not found")

# 4C: Remove end-of-file socket mount block
block4c = re.compile(
    r'\r?\n# Mount Socket\.IO App \(WebSocket\) only if explicitly enabled\r?\n'
    r'if os\.getenv\("ENABLE_SOCKET_IO", "false"\)\.lower\(\) == "true":\r?\n'
    r'    try:\r?\n'
    r'        from socket_manager import socket_manager\r?\n'
    r'        app\.mount\("/socket\.io", socket_manager\.app\)\r?\n'
    r'        logger\.info\("[^"]*"\)\r?\n'
    r'    except Exception as e:\r?\n'
    r'        logger\.error\(f"[^"]*"\)\r?\n'
    r'else:\r?\n'
    r'    logger\.info\("[^"]*"\)\r?\n'
)
if block4c.search(content):
    content = block4c.sub('\n', content)
    print("  OK: Block 4C removed (app.mount socket)")
else:
    print("  FAIL: Block 4C not found -- checking...")
    if 'socket_manager' in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'socket_manager' in line:
                print("    Line %d: %r" % (i+1, line[:80]))

write_file(path, content)
remaining = re.findall(r'socket_manager', content)
if remaining:
    print("  FAIL: %d socket_manager refs remain in api.py" % len(remaining))
else:
    print("  OK: Zero socket_manager references in api.py")

print("\n=== Script complete ===")
