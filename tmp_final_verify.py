import re, os, subprocess

print('=== SOCKET.IO REMOVAL -- FINAL VERIFICATION ===')
print()

# 1. Zero socket refs in backend
print('1. socket_manager references in backend/:')
found = []
for root, dirs, files in os.walk('backend'):
    dirs[:] = [d for d in dirs if d not in ('__pycache__',)]
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                content = open(path, encoding='utf-8').read()
            except Exception:
                continue
            if 'socket_manager' in content:
                for i, line in enumerate(content.split('\n')):
                    if 'socket_manager' in line:
                        found.append('%s:%d: %s' % (path, i+1, line.strip()[:70]))
if found:
    for item in found:
        print('  FOUND: ' + item)
else:
    print('  OK: ZERO results')

# 2. socket_manager.py deleted
print()
if os.path.exists(os.path.join('backend', 'socket_manager.py')):
    print('2. FAIL: socket_manager.py still exists')
else:
    print('2. OK: socket_manager.py deleted')

# 3. Backend import check
print()
print('3. Backend import check:')
result = subprocess.run(
    ['python', '-c', 'import sys; sys.path.insert(0, "."); from api import app; print("PASS")'],
    cwd='backend', capture_output=True, text=True, timeout=30
)
if 'PASS' in result.stdout:
    print('  OK: Backend imports cleanly')
else:
    print('  FAIL:')
    print('  STDOUT:', result.stdout[:200])
    print('  STDERR:', result.stderr[:400])

# 4. invoice_tool direct Tally path
print()
print('4. invoice_tool.py direct Tally path:')
content = open(os.path.join('backend', 'tools', 'invoice_tool.py'), encoding='utf-8').read()
for kw in ['post_to_tally_async', 'tally_live_update']:
    print('  %s present: %s' % (kw, kw in content))
print('  socket_manager present (should be False):', 'socket_manager' in content)

# 5. tally_live_update direct Tally path
print()
print('5. tally_live_update.py direct Tally path:')
content = open(os.path.join('backend', 'tally_live_update.py'), encoding='utf-8').read()
for kw in ['localhost:9000', 'requests.post', 'Direct HTTP to Tally']:
    print('  %s present: %s' % (kw, kw in content))
print('  socket_manager present (should be False):', 'socket_manager' in content)

# 6. auth.py integrity
print()
print('6. auth.py integrity:')
content = open(os.path.join('backend', 'auth.py'), encoding='utf-8').read()
print('  create_access_token present:', 'def create_access_token' in content)
print('  create_socket_token gone:', 'create_socket_token' not in content)
print('  decode_socket_token gone:', 'decode_socket_token' not in content)

# 7. ConnectDevice.tsx clean
print()
print('7. ConnectDevice.tsx socket_token refs:')
content = open(os.path.join('frontend', 'src', 'components', 'auth', 'ConnectDevice.tsx'), encoding='utf-8').read()
if 'socket_token' in content:
    for i, line in enumerate(content.split('\n')):
        if 'socket_token' in line:
            print('  FOUND line %d: %s' % (i+1, line.strip()[:80]))
else:
    print('  OK: ZERO socket_token references')

print()
print('=== END ===')
