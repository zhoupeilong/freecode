"""Classify parameters as business vs personalization to determine expansion scope"""
import json, openpyxl, sys, re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# Load param definitions
wb = openpyxl.load_workbook('F:/09_opencode/docs/code_param_list.xlsx', read_only=True, data_only=True)
ws = wb[wb.sheetnames[0]]
param_defs = {}
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0]:
        code = str(row[0]).strip()
        definition = str(row[3]).strip() if row[3] else ''
        default = str(row[4]).strip() if row[4] else ''
        try:
            defs = json.loads(definition)
            vals = [(str(d.get('value','')), str(d.get('label',''))) for d in defs]
            param_defs[code] = {'values': vals, 'default': default, 'name': str(row[1]).strip() if row[1] else ''}
        except:
            param_defs[code] = {'values': [], 'default': default, 'name': str(row[1]).strip() if row[1] else ''}
wb.close()

# Classify: business params vs personalization params
# Personalization: TSIS_GXHCS (66 company codes), DW_ZXDJGID (institution ID), etc.
# Business: CTRC_XMJLHXMFZRQSLJ (2 values), CTRC_YGH (5 values), etc.

personalization_keywords = ['GXHCS', 'ZXDJGID', 'JGMC']  # Company/institution-specific
personalization_params = set()
business_params = set()
unknown_params = set()

for code, info in param_defs.items():
    n_vals = len(info['values'])
    if n_vals == 0:
        unknown_params.add(code)
        continue
    
    # Personalization params: many values (>=10) or are company-specific
    is_personal = False
    for kw in personalization_keywords:
        if kw in code.upper():
            is_personal = True
            break
    if n_vals >= 10 and not is_personal:
        # Check if values look like company codes
        val_strs = ' '.join([v + ' ' + l for v, l in info['values']])
        if any(kw in val_strs.upper() for kw in ['XT', '信托', '公司']):
            is_personal = True
    
    if is_personal or n_vals >= 10:
        personalization_params.add(code)
    else:
        business_params.add(code)

# Load param codes from inspection SQL
wb2 = openpyxl.load_workbook('F:/09_opencode/docs/my_poor_solution.xlsx', read_only=True, data_only=True)
ws2 = wb2[wb2.sheetnames[0]]
inspection_param_codes = set()
for row in ws2.iter_rows(min_row=2, values_only=True):
    if row and row[22]:
        sql = str(row[22])
        codes = set(re.findall(r"param_code\s*=\s*'([^']+)'", sql, re.IGNORECASE))
        inspection_param_codes |= codes
wb2.close()

# Load param codes from ETL cleansing SQL
etl_param_codes = set()
import glob, os
for f in glob.glob('F:/09_opencode/docs/etl_code_list/*.sql'):
    try:
        with open(f, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()
        codes = set(re.findall(r"#\[([A-Z_0-9]+)\]", content, re.IGNORECASE))
        for c in codes:
            if c.startswith('CTRC_') or c.startswith('TPRT_') or c.startswith('SRDT5_') or c.startswith('DW_') or c.startswith('TUSP_'):
                etl_param_codes.add(c)
    except:
        pass

# Now classify params found in inspection SQL and ETL code
print("=" * 60)
print("PARAMETER CLASSIFICATION FOR EXPANSION")
print("=" * 60)

# All unique param codes from all sources
all_params = inspection_param_codes | etl_param_codes | set(param_defs.keys())
business_found = all_params & business_params
personal_found = all_params & personalization_params

print(f"\nTotal params in code_param_list: {len(param_defs)}")
print(f"Business params (should expand): {len(business_params)}")
print(f"Personalization params (keep URP_PARAM_CONFIG): {len(personalization_params)}")
print(f"Unknown params (no definition): {len(unknown_params)}")

print("\n" + "=" * 60)
print("PARAMS FOUND IN INSPECTION SQL (need expansion decision)")
print("=" * 60)
for code in sorted(inspection_param_codes):
    if code in param_defs:
        info = param_defs[code]
        n_vals = len(info['values'])
        category = "PERSONAL" if code in personalization_params else "BUSINESS"
        print(f"  {code}: {n_vals} values, {category}, name={info['name'][:30]}")
    else:
        print(f"  {code}: NOT IN CONFIG (personal/company-specific)")

print("\n" + "=" * 60)
print("PARAMS FOUND IN ETL CLEANSING SQL")
print("=" * 60)
for code in sorted(etl_param_codes):
    if code in param_defs:
        info = param_defs[code]
        n_vals = len(info['values'])
        category = "PERSONAL" if code in personalization_params else "BUSINESS"
        print(f"  {code}: {n_vals} values, {category}, name={info['name'][:30]}")
    else:
        print(f"  {code}: NOT IN CONFIG")

# Calculate expansion count: only business params
print("\n" + "=" * 60)
print("EXPANSION ESTIMATE (Business params only)")
print("=" * 60)

# Re-calculate: for each of the 153 param SQLs, calculate expansion using ONLY business params
wb3 = openpyxl.load_workbook('F:/09_opencode/docs/my_poor_solution.xlsx', read_only=True, data_only=True)
ws3 = wb3[wb3.sheetnames[0]]

total_expanded = 0
expansion_details = []
for row in ws3.iter_rows(min_row=2, values_only=True):
    if row and row[22]:
        sql = str(row[22])
        if 'URP_PARAM_CONFIG' not in sql and '#[' not in sql:
            continue
        
        alias = str(row[1]) if row[1] else ''
        all_codes = set(re.findall(r"param_code\s*=\s*'([^']+)'", sql, re.IGNORECASE))
        hash_codes = set(re.findall(r"#\[([A-Z_0-9]+)\]", sql, re.IGNORECASE))
        all_codes |= hash_codes
        
        # Separate business vs personal
        biz_codes = []
        personal_codes = []
        for code in all_codes:
            if code in personalization_params:
                personal_codes.append(code)
            else:
                biz_codes.append(code)
        
        # Expansion: only for business params
        expansion = 1
        for code in biz_codes:
            if code in param_defs:
                expansion *= len(param_defs[code]['values'])
            else:
                expansion *= 2  # unknown: assume 2
        
        total_expanded += expansion
        if expansion > 1 or len(biz_codes) > 0:
            expansion_details.append({
                'alias': alias,
                'all_codes': list(all_codes),
                'biz_codes': biz_codes,
                'personal_codes': personal_codes,
                'expansion': expansion
            })

wb3.close()

original_count = 1746
param_count = len(expansion_details)
non_expanded = original_count - param_count  # non-param items stay as 1 each

# Items with no business params (only personal params) → stay as 1
no_expansion = sum(1 for d in expansion_details if d['expansion'] == 1)
has_expansion = sum(1 for d in expansion_details if d['expansion'] > 1)

print(f"Original check items: {original_count}")
print(f"  Non-param items: {non_expanded}")
print(f"  Param items (total): {param_count}")
print(f"    Param items with business expansion: {has_expansion}")
print(f"    Param items with personal-only (no expansion): {no_expansion}")
print(f"  Total expanded from business params: {total_expanded}")
print(f"New total: {non_expanded} + {total_expanded} = {non_expanded + total_expanded}")

# Show top expansion items
expansion_details.sort(key=lambda x: -x['expansion'])
print(f"\nTop 15 expansion items (business params only):")
for d in expansion_details[:15]:
    biz_info = []
    for c in d['biz_codes']:
        if c in param_defs:
            biz_info.append(f"{c}({len(param_defs[c]['values'])}vals)")
        else:
            biz_info.append(f"{c}(unknown)")
    pers_info = [f"{c}(kept)" for c in d['personal_codes']]
    print(f"  {d['alias']}: {d['expansion']}x -> biz={biz_info}, personal={pers_info}")