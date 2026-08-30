// 当前脚本来自于 http://script.345yun.cn 脚本库下载！
// 当前脚本来自于 http://2.345yun.cn 脚本库下载！
// 当前脚本来自于 http://2.345yun.cc 脚本库下载！
// 脚本库官方QQ群1群: 429274456
// 脚本库官方QQ群2群: 1077801222
// 脚本库官方QQ群3群: 433030897
// 脚本库中的所有脚本文件均来自热心网友上传和互联网收集。
// 脚本库仅提供文件上传和下载服务，不提供脚本文件的审核。
// 您在使用脚本库下载的脚本时自行检查判断风险。
// 所涉及到的 账号安全、数据泄露、设备故障、软件违规封禁、财产损失等问题及法律风险，与脚本库无关！均由开发者、上传者、使用者自行承担。

/*
推广宝 完整版
环境变量 TGB：手机号#密码，一行一个账号
依赖：axios
单广告模拟观看22秒，满5条自动领奖
注册地址：https://tg.suewammes.com/plugin.php?id=xigua_hh&ac=invite&idu=23253622
*/
const axios = require('axios');
const UA = 'Mozilla/5.0 (Linux; Android 16; V2426A Build/BP2A.250605.031.A3_V000L1; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/134.0.6998.135 Mobile Safari/537.36 TuiGuangBaoAndroid/1.0.2';
const BASE_PLUGIN = 'https://tg.suewammes.com/plugin.php?id=view&modac=sign';
const LOGIN_URL = 'https://tg.suewammes.com/member.php?mod=logging&action=login&loginsubmit=yes&mobile=2';
const BIND_YQ_URL = 'https://tg.suewammes.com/plugin.php?id=xigua_hh:bindcode';
// 内置固定邀请码
const INVITE_CODE = "000GHFAV";

axios.defaults.timeout = 15000;

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 随机基础延时
function randomDelay(min = 2000, max = 4500) {
    const t = Math.floor(Math.random() * (max - min)) + min;
    return delay(t);
}

// 通用请求头
function getHeaders(cookie = '') {
    return {
        'User-Agent': UA,
        'Cookie': cookie,
        'x-requested-with': 'XMLHttpRequest',
        'Accept': '*/*',
        'sec-ch-ua-platform': '"Android"',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Android WebView";v="134"',
        'sec-ch-ua-mobile': '?1',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://tg.suewammes.com/plugin.php?id=xigua_hh&ac=invite'
    }
}

// 账号登录
async function loginAccount(phone, pwd) {
    try {
        console.log(`开始提交账号${phone}登录请求`);
        const formData = new URLSearchParams();
        formData.append('referer', 'https://tg.suewammes.com/plugin.php?id=xigua_hb&id=xigua_hb&needlogin=1&mobile=2');
        formData.append('fastloginfield', 'username');
        formData.append('cookietime', '2592000');
        formData.append('username', phone);
        formData.append('password', pwd);

        const loginRes = await axios({
            method: 'POST',
            url: LOGIN_URL,
            headers: {
                ...getHeaders(),
                'Content-Type': 'application/x-www-form-urlencoded',
                'origin': 'https://tg.suewammes.com',
                'upgrade-insecure-requests': '1'
            },
            data: formData.toString()
        });

        const allCookieArr = loginRes.headers['set-cookie'] || [];
        if(allCookieArr.length === 0){
            throw new Error("登录无Cookie，账号密码错误/被拦截");
        }
        const finalCookie = allCookieArr.map(item => item.split(';')[0]).join('; ');
        console.log(`✅ ${phone} 登录成功`);
        return finalCookie;
    } catch (e) {
        console.log(`❌ ${phone} 登录失败：${e.message}`);
        return null;
    }
}

// 获取会话动态formhash【增强重试】
async function getSessionFormhash(cookie, retryTimes = 3) {
    for(let r = 0; r < retryTimes; r++){
        try {
            const res = await axios.get(BASE_PLUGIN, { 
                headers: getHeaders(cookie),
                timeout:12000
            });
            // 页面过短代表会话失效跳转登录页
            if(res.data.length < 300){
                console.log(`⚠️ formhash页面内容异常简短，疑似会话失效，重试${r+1}/${retryTimes}`);
                await delay(2500);
                continue;
            }
            const reg = /formhash["']?\s*[:=]\s*["']?([0-9a-f]{8})["']?/i;
            const match = res.data.match(reg);
            if(match){
                const hash = match[1];
                console.log(`🔑 formhash: ${hash}`);
                return hash;
            }else{
                console.log(`⚠️ 当前页面未匹配formhash，重试${r+1}/${retryTimes}`);
                await delay(2000);
                continue;
            }
        }catch(e){
            console.log(`⚠️ 获取formhash请求异常(${r+1}/${retryTimes}): ${e.message}`);
            await delay(3000);
        }
    }
    console.log(`❌ 获取formhash失败：已用尽重试次数`);
    return null;
}

// 绑定内置邀请码
async function bindYqCode(cookie) {
    const fh = await getSessionFormhash(cookie);
    if(!fh) return;
    try {
        const params = new URLSearchParams();
        params.append('formhash', fh);
        params.append('yqcode', INVITE_CODE);
        const res = await axios({
            method: 'POST',
            url: BIND_YQ_URL,
            headers: {
                ...getHeaders(cookie),
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data: params.toString()
        });
        let ret;
        if(typeof res.data === 'string'){
            ret = JSON.parse(res.data);
        }else{
            ret = res.data;
        }
        if(ret.code === 0){
            console.log(`🎊 邀请码${INVITE_CODE}绑定成功`);
        }else if(ret.msg === '不能绑定自己'){
            console.log(`⚠️ ${ret.msg}：该账号自身邀请码就是${INVITE_CODE}，无需绑定`);
        }else{
            console.log(`ℹ️ 绑定结果 msg:${ret.msg}`);
        }
    } catch (e) {
        console.log(`❌ 绑定邀请码接口异常：${e.message}`);
    }
}

// 查询广告任务状态
async function getTaskStatus(cookie) {
    try {
        const res = await axios({ method: 'GET', url: `${BASE_PLUGIN}&submodac=status`, headers: getHeaders(cookie) });
        if (res.data.code !== 0) throw new Error(`code:${res.data.code}`);
        return res.data.data;
    } catch (e) {
        console.log(`❌ 查询任务失败：${e.message}`);
        return null;
    }
}

// 获取广告Token
async function getNextAdToken(cookie, formhash) {
    try {
        const params = new URLSearchParams();
        params.append('formhash', formhash);
        const res = await axios({
            method: 'POST',
            url: `${BASE_PLUGIN}&submodac=next_ad`,
            headers: { ...getHeaders(cookie), 'Content-Type': 'application/x-www-form-urlencoded' },
            data: params.toString()
        });
        if (res.data.code !== 0) throw new Error(res.data.msg || '获取广告失败');
        return res.data.data;
    } catch (e) {
        console.log(`❌ 获取广告Token失败：${e.message}`);
        return null;
    }
}

// 上报广告观看完成
async function submitAdComplete(cookie, token, formhash) {
    try {
        const params = new URLSearchParams();
        params.append('formhash', formhash);
        params.append('token', token);
        const res = await axios({
            method: 'POST',
            url: `${BASE_PLUGIN}&submodac=complete_ad`,
            headers: { ...getHeaders(cookie), 'Content-Type': 'application/x-www-form-urlencoded' },
            data: params.toString()
        });
        if (res.data.code !== 0) throw new Error(res.data.msg || '上报失败');
        return res.data.data;
    } catch (e) {
        console.log(`❌ 广告上报失败：${e.message}`);
        return null;
    }
}

// 领取奖励
async function claimReward(cookie, formhash) {
    try {
        const params = new URLSearchParams();
        params.append('formhash', formhash);
        const res = await axios({
            method: 'POST',
            url: `${BASE_PLUGIN}&submodac=claim`,
            headers: { ...getHeaders(cookie), 'Content-Type': 'application/x-www-form-urlencoded' },
            data: params.toString()
        });
        console.log(`🎁 领奖返回：${res.data.msg}`);
        return res.data.data;
    } catch (e) {
        console.log(`❌ 领奖失败：${e.message}`);
        return null;
    }
}

// 单账号完整流程：登录→绑定邀请码→循环刷广告领奖
async function runSingleTask(phone, pwd, idx) {
    console.log(`\n========== 账号${idx} ${phone} 开始执行 ==========`);
    let cookie = await loginAccount(phone, pwd);
    if (!cookie) return;

    // 登录成功自动执行绑定邀请码
    await randomDelay();
    await bindYqCode(cookie);

    while (true) {
        const taskInfo = await getTaskStatus(cookie);
        if (!taskInfo) {
            console.log(`⚠️ ${phone} 获取任务状态失败，尝试重新登录刷新会话`);
            cookie = await loginAccount(phone, pwd);
            if (!cookie) {
                console.log(`❌ ${phone} 重登失败，终止该账号任务`);
                break;
            }
            await randomDelay();
            continue;
        }
        const { viewed_count, target_count, countdown_seconds, can_claim, claimed } = taskInfo;
        console.log(`📊 广告进度：${viewed_count}/${target_count} | ✅可领奖:${can_claim} | 📅今日已领取:${claimed}`);

        if (can_claim && !claimed) {
            console.log(`🎉 广告任务已满，准备执行领奖！`);
            await randomDelay();
            let fh = await getSessionFormhash(cookie);
            // 获取失败尝试重登一次
            if(!fh){
                cookie = await loginAccount(phone, pwd);
                if(!cookie) break;
                fh = await getSessionFormhash(cookie);
                if(!fh) break;
            }
            await claimReward(cookie, fh);
            console.log(`💰 ${phone}今日奖励领取完毕，任务结束`);
            break;
        }
        if (viewed_count >= target_count) {
            console.log(`✅ ${phone}今日广告任务全部完成`);
            break;
        }
        if (countdown_seconds > 0) {
            console.log(`⏳ 冷却等待 ${countdown_seconds} 秒`);
            await delay(countdown_seconds * 1000);
        }

        let fh = await getSessionFormhash(cookie);
        // formhash多次失败 → 重新登录刷新cookie
        if(!fh){
            console.log(`⚠️ formhash获取失败，执行重新登录`);
            cookie = await loginAccount(phone, pwd);
            if (!cookie) {
                console.log(`❌ ${phone}重新登录失败，终止账号任务`);
                break;
            }
            fh = await getSessionFormhash(cookie);
            if(!fh) break;
        }

        const adData = await getNextAdToken(cookie, fh);
        if (!adData) break;
        console.log(`▶ 获取广告Token：${adData.token}，模拟观看22秒`);
        await delay(22000);

        const newTask = await submitAdComplete(cookie, adData.token, fh);
        if (!newTask) break;
        console.log(`✅ 广告上报成功，当前完成数量：${newTask.viewed_count}`);
        await randomDelay();
    }
}

// 程序入口
(async function main() {
    const accountEnv = process.env.TGB || '';
    if (!accountEnv.trim()) {
        console.log('❌ 请配置环境变量 TGB，格式：手机号#密码，一行一个账号');
        process.exit(1);
    }
    const accList = accountEnv.split('\n').filter(i => i.trim());
    console.log(`成功加载账号总数：${accList.length}`);
    for (let i = 0; i < accList.length; i++) {
        const line = accList[i].trim();
        const [phone, pwd] = line.split('#');
        if (!phone || !pwd) {
            console.log(`❌ 账号${i+1}格式错误，正确格式：手机号#密码`);
            continue;
        }
        await runSingleTask(phone.trim(), pwd.trim(), i + 1);
        await delay(6000);
    }
    console.log('\n========== 全部账号执行结束 ==========');
})();


// 当前脚本来自于 http://script.345yun.cn 脚本库下载！
// 当前脚本来自于 http://2.345yun.cn 脚本库下载！
// 当前脚本来自于 http://2.345yun.cc 脚本库下载！
// 脚本库官方QQ群1群: 429274456
// 脚本库官方QQ群2群: 1077801222
// 脚本库官方QQ群3群: 433030897
// 脚本库中的所有脚本文件均来自热心网友上传和互联网收集。
// 脚本库仅提供文件上传和下载服务，不提供脚本文件的审核。
// 您在使用脚本库下载的脚本时自行检查判断风险。
// 所涉及到的 账号安全、数据泄露、设备故障、软件违规封禁、财产损失等问题及法律风险，与脚本库无关！均由开发者、上传者、使用者自行承担。