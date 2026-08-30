import base64
import json
import os

def decode_batches(base_dir):
    """Decode all batch files in the directory."""
    batch_files = [f for f in os.listdir(base_dir) 
                   if f.startswith('slides_batch_') and f.endswith('.json')]
    
    total_decoded = 0
    for bf in sorted(batch_files):
        path = os.path.join(base_dir, bf)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # The file contains a JSON-encoded string, which itself is a JSON array
        # So we need to parse it twice
        try:
            # First parse - get the inner string
            inner_str = json.loads(content)
            # Second parse - get the array
            data = json.loads(inner_str)
        except (json.JSONDecodeError, TypeError):
            # Maybe it's already an array
            try:
                data = json.loads(content)
            except:
                print(f'  {bf}: Cannot parse JSON')
                continue
        
        if not isinstance(data, list):
            print(f'  {bf}: Not a list (type={type(data).__name__})')
            continue
        
        # Extract start index from filename
        parts = bf.replace('.json', '').split('_')
        last_part = parts[-1]
        start_str, end_str = last_part.split('-')
        start_idx = int(start_str)
        
        base_slide_num = start_idx  # slide number = base + item index
        
        for i, item in enumerate(data):
            slide_num = base_slide_num + i
            if item is None:
                print(f'  Slide {slide_num:02d}: SKIP (null)')
                continue
            if not isinstance(item, str):
                print(f'  Slide {slide_num:02d}: SKIP (type={type(item).__name__})')
                continue
            if item.startswith('ERROR'):
                print(f'  Slide {slide_num:02d}: {item}')
                continue
            
            # Parse data URL
            if item.startswith('data:'):
                comma = item.find(',')
                if comma < 0:
                    print(f'  Slide {slide_num:02d}: Bad data URL format')
                    continue
                b64 = item[comma + 1:]
            else:
                b64 = item
            
            try:
                img_data = base64.b64decode(b64)
                out_path = os.path.join(base_dir, f'slide_{slide_num:02d}.jpg')
                with open(out_path, 'wb') as f:
                    f.write(img_data)
                print(f'  Slide {slide_num:02d}: {len(img_data)} bytes -> OK')
                total_decoded += 1
            except Exception as e:
                print(f'  Slide {slide_num:02d}: decode error - {str(e)[:60]}')
    
    return total_decoded

result = decode_batches(r'D:\Hermes\image_cache')
print(f'\nTotal decoded: {result}')

# List final files
base = r'D:\Hermes\image_cache'
slides = [f for f in os.listdir(base) if f.startswith('slide_') and f.endswith('.jpg')]
print(f'Total JPEG slides: {len(slides)}')
for s in sorted(slides):
    sz = os.path.getsize(os.path.join(base, s))
    print(f'  {s}: {sz} bytes')
