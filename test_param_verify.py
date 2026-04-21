"""验证参数展开逻辑的端到端测试脚本"""
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parsers.param_config_loader import load_param_config, classify_param, _get_equivalent_param

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_stg_file")
XLSX_PATH = os.path.join(BASE_DIR, "code_param_list.xlsx")

def main():
    param_config = load_param_config(XLSX_PATH)
    
    personal_only_count = 0
    business_remaining_count = 0
    combo_count = 0
    sample_personal = []
    sample_business = []
    
    for dir_name in os.listdir(OUTPUT_DIR):
        dir_path = os.path.join(OUTPUT_DIR, dir_name)
        if not os.path.isdir(dir_path) or not dir_name.startswith('SUC'):
            continue
        for fname in os.listdir(dir_path):
            if not fname.endswith('.sql'):
                continue
            fpath = os.path.join(dir_path, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if '-- 参数组合:' in content:
                combo_count += 1
                continue
            
            if 'URP_PARAM_CONFIG' not in content:
                continue
            
            # Has URP_PARAM_CONFIG but no param combo
            pattern = r"param_code='([A-Z0-9_]+)'"
            codes = re.findall(pattern, content)
            has_business = False
            for code in codes:
                actual = code
                if code not in param_config:
                    equiv = _get_equivalent_param(code)
                    if equiv and equiv in param_config:
                        actual = equiv
                if actual in param_config and param_config[actual].category == 'business':
                    has_business = True
                    break
            
            if has_business:
                business_remaining_count += 1
                if len(sample_business) < 3:
                    sample_business.append((fname, codes))
            else:
                personal_only_count += 1
                if len(sample_personal) < 3:
                    sample_personal.append((fname, codes))
    
    print("=== Parameter Expansion Verification ===")
    print(f"Files with '-- param combo' header: {combo_count}")
    print(f"Files with URP_PARAM_CONFIG but no combo: {personal_only_count + business_remaining_count}")
    print(f"  Personal-only (correct): {personal_only_count}")
    print(f"  Still has business params (BUG): {business_remaining_count}")
    print()
    
    if sample_personal:
        print("Personal-only sample files:")
        for fname, codes in sample_personal:
            print(f"  {fname}: {codes}")
    
    if sample_business:
        print("Business-remaining sample files (need fix):")
        for fname, codes in sample_business:
            print(f"  {fname}: {codes}")

    # Additional: check DM_SUPPLEMENT files
    dm_supplement_remaining = 0
    for dir_name in os.listdir(OUTPUT_DIR):
        dir_path = os.path.join(OUTPUT_DIR, dir_name)
        if not os.path.isdir(dir_path) or not dir_name.startswith('SUC'):
            continue
        for fname in os.listdir(dir_path):
            if not fname.endswith('.sql'):
                continue
            fpath = os.path.join(dir_path, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'DM' in content and 'URP_PARAM_CONFIG' in content and '-- param combo' not in content.lower():
                dm_supplement_remaining += 1
    
    print(f"\nDM_SUPPLEMENT files with URP_PARAM_CONFIG but no param combo: {dm_supplement_remaining}")
    
    if business_remaining_count == 0:
        print("\nALL PASSED: All business param conditions correctly removed!")
    else:
        print(f"\nISSUE: {business_remaining_count} files still have business param conditions")

if __name__ == '__main__':
    main()