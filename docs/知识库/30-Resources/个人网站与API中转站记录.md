# 个人网站搭建与 API 中转站部署记录

> 日期：2026-08-16
> 状态：✅ 网站初版完成、中转站运行中
> 摘要：基于 Mizuki 模板搭建「四点的光」个人网站；部署 new-api 中转站统一管理 API key,实现 Token 自由。

## 一、个人网站「四点的光」

### 技术选型
- 模板:**Mizuki**(LyraVoid/Mizuki,Apache-2.0,基于 Astro + Tailwind + Svelte)
- 对比过的方案:
  - 场景滚动站(ryota-kk/personal-homepage)—— 视频背景+横滑,效果炫但重
  - 磷光终端风 —— 被否(太技术宅)
  - Zine 手工杂志风 —— 被否
  - 苹果质感风 —— 用户要更高级独特
  - **最终选 Mizuki** —— 功能全、静态站、适合个人博客+工具

### 站点配置
- 站名:**四点的光**(用户自选,凌晨四点服务器最安静)
- 副标题:凌晨四点,服务器最安静的时候
- 语言:zh_CN,主题色 200(青蓝)
- 导航:首页 / 归档 / 关于 / 我的(日记·相册·项目)/ 链接(密钥库·GitHub·豆包)
- 关闭页面:番剧/友链/技能/时间线/设备/AI工具
- 页脚:Powered by Astro & 四点的光

### 功能
- **密钥库 /vault/**(自研):API Key 保险箱,AES-GCM 加密 + PBKDF2 主密码派生,存 localStorage,主密码解锁后才能查看
- 相册/日记/项目页:已开,内容留空待填
- 首页壁纸:用户提供的 Zootopia 图(banner 模式,轮播关闭)

### 关键坑位
1. **banner 配置在 `siteConfig.ts` 的 `banner` 段**,不是 backgroundWallpaper.ts(全屏壁纸是另一套,默认没启用)
2. 改壁纸后浏览器缓存旧图 → **换文件名**(zootopia.webp)强制刷新
3. 构建脚本 `check-global-style-loading.mjs` 强制要求 about 页含 `::github{repo=...}` 卡片标记(两个冒号,三个会渲染失败)
4. **pnpm 版本**:仓库声明 pnpm@11(需 Node 22+),Node 20 会报 `node:sqlite` 错误。解决:装 Node 22 + corepack 激活 pnpm 11
5. Mizuki 模板自带大量原仓库内容(公告/示例文章/项目数据/看板娘/页脚版权)——需逐处清理:announcementConfig、src/content/spec、src/data/projects.ts、friends.ts、pioConfig(看板娘)、Footer.astro

### 技术栈环境
- Node 22.17.0(`~/.local/node22/bin`),pnpm 11.5.3(corepack)
- 构建:`cd /tmp/mizuki && pnpm build`,产物在 dist/
- 本地预览:`python3 -m http.server 8899 --directory dist`

## 二、API 中转站(new-api)

### 部署
- 软件:**new-api**(QuantumNous,Go 单文件,内存仅 ~19M)
- 位置:`/home/ubuntu/app/new-api/new-api`,版本 v1.0.0-rc.24
- 端口:3000
- 开机自启:systemd 服务 `new-api.service`(Restart=on-failure)
- 面板:默认 root/123456(用户已改)

### 渠道与模型
- 上游:**8 个商汤 key**(SenseNova Token Plan 免费额度),new-api 面板内轮询
- 可用模型:
  - `deepseek-v4-flash`(1M 上下文,思考模式)—— 每5小时500次/号
  - `glm-5.2`(1M 上下文+128K 输出)—— 每5小时500次/号
  - `sensenova-6.8-flash-lite`(多模态智能体)—— 每5小时1500次/号
  - `sensenova-6.7-flash-lite`(8/31前自动路由到 6.8)
- Base URL:https://token.sensenova.cn/v1(官方)

### 额度(8 key)
| 模型 | /天 |
|---|---|
| sensenova | ~57600 次 |
| deepseek/glm | ~19200 次 |

### Hermes 辅助模型全部切换
| 辅助任务 | 原(NVIDIA) | 现(中转站) |
|---|---|---|
| vision | nemotron nano | **sensenova-6.8-flash-lite** |
| title_generation | nemotron mini | **deepseek-v4-flash** |
| compression | nemotron 120b | **deepseek-v4-flash** |
| web_extract | nemotron 30b | **sensenova-6.8-flash-lite** |
| memory_query_rewrite | llama 8b | **glm-5.2** |

配置方式:`hermes config set auxiliary.<task>.provider openai` + base_url `http://127.0.0.1:3000/v1` + api_key
主模型 deepseek-v4-flash(opencode-go)**未动**。

### 关键坑位
1. glm-5.2 / sensenova 输出在 `reasoning` / `reasoning_content` 字段,非 content(解析响应注意)
2. 免费额度有限流,多个 key 轮询分担
3. 辅助模型走中转站后,调用计费/日志在 new-api 面板可查

## 三、设计技能安装
- **taste-skill**(Leonxlnx,76.7k★):反 AI 模板设计,4 个变体已装
- **impeccable**(pbakaus,59.2k★):23 命令 + 59 条检测规则,浏览器实时迭代
- 均已装入 Hermes 技能库(creative 分类)

## 待办
- [ ] 网站内容填充(相册/日记/项目/文章)
- [ ] 网站部署到 Nginx(正式发布,配域名/HTTPS)
- [ ] 密钥库存真实 key 测试
- [ ] 可选:sensenova-u1-fast 信息图模型加入渠道
