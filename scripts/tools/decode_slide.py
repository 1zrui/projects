import base64
import os

# Read the base64 file
path = r'D:\Hermes\image_cache\slide_03.jpg.json'
with open(path, 'r') as f:
    content = f.read().strip()

# Parse data URL
if content.startswith('data:'):
    b64_data = content.split(',', 1)[1]
else:
    b64_data = content

# Decode and save
img_data = base64.b64decode(b64_data)
out_path = r'D:\Hermes\image_cache\slide_03.jpg'
with open(out_path, 'wb') as f:
    f.write(img_data)

print(f'Decoded: {len(img_data)} bytes -> {out_path}')

# Check result
print(f'File exists: {os.path.exists(out_path)}')
