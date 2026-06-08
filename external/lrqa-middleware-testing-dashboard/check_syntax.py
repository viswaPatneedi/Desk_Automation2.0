#!/usr/bin/env python3
import ast
import sys

try:
    with open('app.py', 'r') as f:
        code = f.read()
    ast.parse(code)
    print('✓ No syntax errors in app.py')
    sys.exit(0)
except SyntaxError as e:
    print(f'❌ SyntaxError at line {e.lineno}: {e.msg}')
    if e.text:
        print(f'   Text: {e.text}')
    print(f'   Offset: {" " * (e.offset - 1) if e.offset else ""}^')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error: {type(e).__name__}: {e}')
    sys.exit(1)
