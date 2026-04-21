"""Extract exact URP_PARAM_CONFIG SQL patterns from inspection templates"""
import re, openpyxl, sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook('F:/09_opencode/docs/my_poor_solution.xlsx', read_only=True, data_only=True)
ws = wb[wb.sheetnames[0]]

# Find param SQLs and extract the exact WHERE clause patterns
param_items = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if row and row[22]:
        sql = str(row[22])
        if 'URP_PARAM_CONFIG' in sql or '#[' in sql:
            alias = str(row[1]) if row[1] else ''
            param_items.append((alias, sql))

wb.close()

print(f"Found {len(param_items)} param SQLs")

# Show first 3 complete SQLs to understand the pattern
for i, (alias, sql) in enumerate(param_items[:5]):
    print(f"\n{'='*60}")
    print(f"=== {alias} ===")
    print(f"{'='*60}")
    # Find URP_PARAM_CONFIG references
    # Look around param_code / param_value
    for pattern in [r'param_code', r'param_value', r'PARAM_CONFIG']:
        idx = sql.upper().find(pattern.upper())
        while idx >= 0:
            start = max(0, idx - 80)
            end = min(len(sql), idx + 120)
            print(f"  CONTEXT: ...{sql[start:end]}...")
            idx = sql.upper().find(pattern.upper(), idx + 1)
            if idx >= 0 and idx < len(sql):
                # Show next occurrence only if different
                pass

# Now extract using a more flexible regex
print(f"\n\n=== FLEXIBLE PATTERN EXTRACTION ===")
all_patterns = set()
for alias, sql in param_items:
    # Match various URP_PARAM_CONFIG patterns
    # Pattern: ... from ... URP_PARAM_CONFIG ... where ...
    # Try to find "pc" alias patterns  
    p1 = re.findall(r"pc\.param_code\s*=\s*'([^']+)'", sql, re.IGNORECASE)
    p2 = re.findall(r"pc\.param_value\s*=\s*'([^']*)'", sql, re.IGNORECASE)
    p3 = re.findall(r"pc\.status\s*=\s*'([^']+)'", sql, re.IGNORECASE)
    
    # Also try without "pc." alias
    p4 = re.findall(r"param_code\s*=\s*'([^']+)'", sql, re.IGNORECASE)
    p5 = re.findall(r"param_value\s*=\s*'([^']*)'", sql, re.IGNORECASE)
    
    # Try #[PARAM] patterns
    p6 = re.findall(r"#\[([A-Z_0-9]+)\]", sql, re.IGNORECASE)
    
    if p1 or p4 or p6:
        all_patterns.add((
            tuple(p1) if p1 else tuple(p4) if p4 else (),
            tuple(p2) if p2 else tuple(p5) if p5 else (),
            tuple(p6) if p6 else (),
            alias
        ))

print(f"Unique pattern types: {len(all_patterns)}")
for p_codes, p_vals, p_hashes, alias in sorted(all_patterns):
    print(f"  {alias}: param_codes={p_codes}, param_values={p_vals}, hash_params={p_hashes}")

# Show 3 complete SQLs with URP_PARAM_CONFIG
print(f"\n\n=== COMPLETE SQL EXAMPLES ===")
for alias, sql in param_items[:3]:
    print(f"\n{'='*80}")
    print(f"ALIAS: {alias}")
    print(f"SQL LENGTH: {len(sql)}")
    # Print first 800 chars
    print(sql[:800])
    if len(sql) > 800:
        print(f"... [truncated, total {len(sql)} chars]")