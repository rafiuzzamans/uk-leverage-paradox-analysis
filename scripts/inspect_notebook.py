import json

with open('Financial_Analysis_Charts.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

print('Number of cells:', len(nb['cells']))
for i, cell in enumerate(nb['cells']):
    preview = ''.join(cell['source'][:2]).strip()
    print(f"Cell {i}: type={cell['cell_type']}, lines={len(cell['source'])}, preview={preview[:60]}")
