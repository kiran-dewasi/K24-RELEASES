import sys, os
from importlib import import_module

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cloud-backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

print("Path:", sys.path[:3])
try:
    mod = import_module('database')
    print("Found database at:", mod.__file__)
except Exception as e:
    print(e)
