import base64
import json
import os

path = r'D:\Hermes\image_cache\slides_all.json'
out_dir = r'D:\Hermes\image_cache'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Parse: the file contains one JSON string which itself contains a JSON array
try:
    inner = json.loads(content)
    data = json.loads(inner)
except (json.JSONDecodeError, TypeError):
    data = json.loads(content)

if not isinstance(data, list):
    print(f'ERROR: Not a list, got {type(data).__name__}')
    exit(1)

success = 0
for i, item in enumerate(data):
    slide_num = i + 1
    if item is None or not isinstance(item, str):
        print(f'  Slide {slide_num:02d}: SKIP')
        continue
    
    if item.startswith('data:'):
        b64 = item.split(',', 1)[1]
    else:
        b64 = item
    
    try:
        img_data = base64.b64decode(b64)
        out_path = os.path.join(out_dir, f'slide_{slide_num:02d}.jpg')
        with open(out_path, 'wb') as f:
            f.write(img_data)
        print(f'  Slide {slide_num:02d}: {len(img_data)} bytes -> OK')
        success += 1
    except Exception as e:
        print(f'  Slide {slide_num:02d}: decode error - {str(e)[:60]}')

print(f'\nTotal: {success}/{len(data)} slides decoded')
