# -*- coding: utf-8 -*-
import urllib.request, json

def send(text):
    data = json.dumps({'group_id': 1064105365, 'message': text}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:18801/send_group_msg', data=data, headers={'Content-Type': 'application/json'})
    print(urllib.request.urlopen(req).read().decode('utf-8'))

part2 = """[CQ:at,qq=2242413547] 收到就好！第2部分来了：

【豆子踩坑文档·第2部分：头条号「泰妹超爱吃」运营】

■ 人设铁律（最重要）
- 泰妹=泰国本地人！评论按泰国本地人口吻，严禁游客话术（想飞去泰国/没见过泰国菜）会自曝穿帮
- 遇 XX 是什么 类评论必须先看视频画面确认再回复，绝不凭空猜
- 东南亚本地食材识别不了就 web_search 核实，他人先回复的答案可能错

■ 评论区自动化踩坑
- 头条评论框基于 React，innerText/document.execCommand 塞文字按钮不亮（合成事件没触发）
- 消息中心监听 input 事件；视频页监听 onKeyUp，方案不同
- 2026-08 改版后回复框=textarea.byte-textarea，必须真实键盘输入（nuphus browser_type），JS 赋值打不亮发布按钮
- 发布按钮带 byte-btn-disabled=没激活
- 删重复评论必刷新验证（DOM 残影误判）

■ 运营节奏
- 只处理 6 小时内新评论（高频粉放宽 24h）
- 回复 10-30 字嘴馋型+😋，不引流，互动 1 天≤10 条

【通用：QQ/NapCat 侧】
- 本机 NapCat HTTP API 127.0.0.1:18801，机器人 779139587（豆子）
- curl 发中文会乱码（GBK/UTF-8），必须 Python urllib + ensure_ascii=False + UTF-8
- 群消息 message_id 不按时间递增，判新旧用 time 时间戳
- 发文件：存 C:\\Users\\Administrator\\Downloads\\ 用 file:///（D 盘路径被黑名单拦）
- 以上，收工～"""

send(part2)
