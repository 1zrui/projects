# new-api 关闭注册实录

> 摘要：新版 new-api 的 options 表缺省 RegisterEnabled 即默认开放注册；直接写 DB 关掉比调 API 可靠；用注册接口实测验证。

## 背景
- 大哥发现 new-api 上有好多注册的机器人号，要求禁用注册。
- 站点：/home/ubuntu/app/new-api，SQLite（one-api.db），systemd 服务 new-api.service，端口 3000。

## 查到的
1. `users` 表只有 zrui（管理员），`tokens` 表 2 个 key（admin/韩）——机器人号已被大哥手动删完，库已干净。
2. `options` 表一共才 13 项，**没有 RegisterEnabled / PasswordRegisterEnabled**——缺省=程序按前端默认值（true）跑，等于大门敞开。
3. 前端源码确认：`系统设置→认证→basic-auth` 有 `RegisterEnabled`（默认true）+ `PasswordRegisterEnabled`（默认true），经 `PUT /api/option/` 保存。

## 做法（大哥点头后动手）
```bash
cd /home/ubuntu/app/new-api
python3 -c "
import sqlite3
db = sqlite3.connect('one-api.db')
cur = db.cursor()
cur.execute(\"INSERT OR REPLACE INTO options(key,value) VALUES('RegisterEnabled','false'),('PasswordRegisterEnabled','false')\")
db.commit()"
sudo systemctl restart new-api.service
```

## 验证
- `systemctl is-active` = active，3000 端口 200。
- 实测 `POST /api/user/register` 返回：`{"message":"New user registration has been disabled by administrator","success":false}` ✅
- 自己登录和现有 key 不受影响。

## 教训
- 直接写 DB 比调 `PUT /api/option/` 可靠（之前 Turnstile 也是 API 没持久化，见此前踩坑）。
- 改配置前必须先跟大哥确认，這次照规矩先报开关名+现状再动手。
