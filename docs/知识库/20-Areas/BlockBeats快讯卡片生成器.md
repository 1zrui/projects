# BlockBeats 快讯卡片生成器

摘要：用Python生成BlockBeats风格的快讯卡片PNG图片，杂志排版风。

## 用法

```cmd
python flash_card_maker.py --id 364318 --title "标题" --content "正文" --time "22:14"
```

## 依赖

- Pillow：`pip install pillow`
- 字体：Windows用 `C:/Windows/Fonts/msyh.ttc`，Linux用 NotoSansCJK

## 输出

当前目录 `flash_<id>.png`

## 设计风格

- 暖灰色背景 (242, 238, 232)
- 左上角红色 FLASH 标签
- 黑色加粗标题（28号字，自动换行）
- 橙色分隔线
- 深色正文（16号字）
- 底部品牌署名

## 位置

- 云上：`/home/ubuntu/.hermes/cache/documents/flash_card_maker.py`
- GitHub：`projects/scripts/tools/flash_card_maker.py`
- 知识库本文档
