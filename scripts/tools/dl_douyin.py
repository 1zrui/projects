import urllib.request, os

urls = [
    "https://p9-pc-sign.douyinpic.com/tos-cn-i-0813c001/oIpgWIg0vA7AAAiEiWIEjCEIIPAaBgShuA6wA~tplv-dy-aweme-images:q75.webp",
    "https://p3-pc-sign.douyinpic.com/tos-cn-i-0813/o0uI6ivWaA7IAGWEIxEgAiPgAAA0gCWjESAiB~tplv-dy-aweme-images:q75.webp",
    "https://p3-pc-sign.douyinpic.com/tos-cn-i-0813c001/oQjAIAgiav4PABEWA7SuRAIWC0gAEgI7AEiy3~tplv-dy-aweme-images:q75.webp",
    "https://p9-pc-sign.douyinpic.com/tos-cn-i-0813/ogEAKEP5iIBgAzWAvWASiAjrgCuIAI7EgaBA0~tplv-dy-aweme-images:q75.webp",
    "https://p9-pc-sign.douyinpic.com/tos-cn-i-0813/oQAAAAIWI7PBIAuH6vgaSEAE0gC3Eii0AgW4j~tplv-dy-aweme-images:q75.webp",
    "https://p9-pc-sign.douyinpic.com/tos-cn-i-0813c001/oEggWIg0vA7AAAiEiWPEjCEIIPAaBgSJuA41A~tplv-dy-aweme-images:q75.webp",
    "https://p9-pc-sign.douyinpic.com/tos-cn-i-0813c001/oQuPEGeAgLp9AIAdqAQAIzFBAsAEChfJCtAsDA~tplv-dy-aweme-images:q75.jpeg",
    "https://p3-pc-sign.douyinpic.com/tos-cn-i-0813/okIgSg6ECIGA3z7iAPABjJAviaAWAg0uIWEEA~tplv-dy-aweme-images:q75.jpeg",
    "https://p9-pc-sign.douyinpic.com/tos-cn-i-0813c001/oMviaAAIBEiAAIACA4PEIWuAgjWtE7S4u0gg5~tplv-dy-aweme-images:q75.webp",
    "https://p9-pc-sign.douyinpic.com/tos-cn-i-0813c001/o0IJdAAyqAAfatAECpFEgLDuAAA9SwAQIGfsCh~tplv-dy-aweme-images:q75.webp",
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.douyin.com/',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
}

output_dir = 'D:\\Hermes\\image_cache'
for i, url in enumerate(urls):
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=30)
        ext = url.split('.')[-1].split('?')[0]
        fname = os.path.join(output_dir, f'douyin_{i+1:02d}.{ext}')
        with open(fname, 'wb') as f:
            f.write(resp.read())
        print(f'Slide {i+1}: OK ({os.path.getsize(fname)} bytes) - {fname}')
    except Exception as e:
        print(f'Slide {i+1}: ERROR - {str(e)[:80]}')
