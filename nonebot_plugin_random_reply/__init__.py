import re
from .config import Config, ConfigError
from .balance import BalanceAlert, get_current_balance
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, GROUP
from nonebot.log import logger
from nonebot.rule import Rule, to_me
from nonebot.plugin import PluginMetadata
from nonebot import on_message, require, get_plugin_config, on_startswith, get_bot, on_command
from nonebot.exception import FinishedException
from openai import AsyncOpenAI
from typing import Optional, Union
from pathlib import Path
import json
import time
import random
import httpx
import nonebot

from nonebot.plugin import PluginMetadata


require("nonebot_plugin_saa")
from nonebot_plugin_saa import Text, Image, TargetQQPrivate

require("nonebot_plugin_userinfo")
from nonebot_plugin_userinfo import BotUserInfo, UserInfo

__plugin_meta__ = PluginMetadata(
    name="拟人回复bot",
    description="根据群聊语境随机攻击群友，基于llm选择表情包回复",
    usage="""
    配置好后bot随机攻击群友，@机器人也可触发
    余额查询————开启硅基流动余额预警后，使用该命令可以查询API余额
    """,
    config=Config,
    extra={},
    type="application",
    homepage="https://github.com/Alpaca4610/nonebot_plugin_random_reply",
    supported_adapters={"~onebot.v11"},
)


def clean_model_output(raw_output):
    # 移除思考过程标记及内容（</think>...</think>）
    cleaned = re.sub(r'</think>.*?</think>', '', raw_output, flags=re.DOTALL)
    # 移除多余空行和空格
    cleaned = re.sub(r'\n+', '\n', cleaned).strip()
    return cleaned

class AIGenerator:
    def __init__(self, plugin_config):
        if not (plugin_config.oneapi_key or plugin_config.gemini_key):
            raise ConfigError("请配置大模型使用的KEY")

        self.strategy = "oneapi" if plugin_config.oneapi_key else "gemini"

        if self.strategy == "oneapi":
            self.client = AsyncOpenAI(
                api_key=plugin_config.oneapi_key,
                base_url=plugin_config.oneapi_url or "https://api.openai.com/v1",
            )
            self.model_id = plugin_config.oneapi_model
        else:
            self.gemini_key = plugin_config.gemini_key
            self.model_id = plugin_config.gemini_model

    async def generate(
        self,
        history: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Union[str, Text]:
        if self.strategy == "oneapi":
            return await self._generate_oneapi(history, name)
        return await self._generate_gemini(history, name)

    async def _generate_oneapi(self, history: str, name: str) -> str:
        full_prompt = f"""{prompt}
每条聊天记录的格式为:  "T": "消息发送时间", "N": "发送者的昵称", "C": "消息内容" 
请始终保持自然随意的对话风格，避免完整句式或逻辑论述。输出禁止包含任何格式标记或前缀和分析过程
在下面的历史聊天记录中，你在群聊中的昵称为{name}，现在请处理最新消息：\n{history}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model_id, messages=[{"role": "user", "content": full_prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OneAPI调用失败: {str(e)}")
            return f"调用出错: {str(e)}"

    async def _generate_gemini(self, history: str, name: str) -> str:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.gemini_key}"
        full_prompt = f"""{prompt}
每条聊天记录的格式为:  "T": "消息发送时间", "N": "发送者的昵称", "C": "消息内容" 
请始终保持自然随意的对话风格，避免完整句式或逻辑论述。输出禁止包含任何格式标记或前缀和分析过程
在下面的历史聊天记录中，你在群聊中的昵称为{name}，现在请处理最新消息：\n{history}"""

        try:
            async with httpx.AsyncClient(
                proxy=plugin_config.gemini_proxy if plugin_config.gemini_proxy else None, timeout=300
            ) as client:
                response = await client.post(
                    api_url,
                    json={
                        "contents": [{"parts": [{"text": full_prompt}]}],
                        "generationConfig": {"responseModalities": ["Text"]},
                    },
                    headers={"Content-Type": "application/json"},
                )
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Gemini调用失败: {str(e)}")
            return f"调用出错: {str(e)}"


default_prompt = """【任务规则】
1. 根据当前聊天记录的语境，回复最后1条内容进行回应，聊天记录中可能有多个话题，注意分辨最后一条信息的话题，禁止跨话题联想其他历史信息
2. 用贴吧老哥的风格的口语化短句回复，禁止使用超过30个字的长句，句子碎片化，犀利地、一阵见血地锐评
3. 模仿真人发言，不要被发现你是AI，用贴吧乐子人的风格的口语化短句回复，偶尔进行反串发言，适当使用缩写、流行梗、表情符号（但每条最多1个）
4. 输出必须为纯文本，禁止任何格式标记或前缀
5. 当出现多个话题时，优先回应最新的发言内容
6. 一次仅回复一句点评话语"""


async def get_res(messages: str, name: str) -> str:
    content = await ai_generator.generate(history=messages, name=name)

    if not content or "出错" in content:
        logger.error("生成内容为空或包含错误")
        return ""
    return content.strip('"').strip()


def load_plugin_config(file_path: str):
    if not file_path.strip():
        return default_prompt
    try:
        path = Path(file_path)
        if not path.is_file():
            logger.error("随机回复插件prompt文件路径有误")
            return default_prompt

        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                logger.error("随机回复插件prompt文件为空")
                return default_prompt
            return content

    except (FileNotFoundError, OSError):
        logger.error("随机回复插件prompt文件未找到")
        return default_prompt
    except Exception as e:
        logger.error(f"随机回复插件prompt导入错误：{str(e)}")
        return default_prompt


plugin_config = get_plugin_config(Config)
ai_generator = AIGenerator(plugin_config)

history_lens = plugin_config.reply_lens
reply_pro = plugin_config.reply_pro
whitelsit = plugin_config.random_re_g

meme_url = plugin_config.random_meme_url
meme_token = plugin_config.random_meme_token

meme_enable = plugin_config.meme_enable

balance_on = plugin_config.balance_on
if balance_on:
    alert_monitor = BalanceAlert(plugin_config.balance_thresholds)
    config_ = nonebot.get_driver().config
    superusers = config_.superusers

prompt = load_plugin_config(plugin_config.reply_prompt_url)
logger.info("随机回复插件使用prompt："+ prompt)


async def random_rule(event: GroupMessageEvent) -> bool:
    group_id = str(event.group_id)
    if group_id in whitelsit:
        # 优先使用分群配置的回复概率
        group_pro = plugin_config.group_reply_pro.get(group_id, reply_pro)
        return random.random() < group_pro
    return False


async def to_me_rule(event: GroupMessageEvent) -> bool:
    if str(event.group_id) in whitelsit:
        return True
    return False


random_reply = on_message(
    priority=999, rule=Rule(random_rule), block=True, permission=GROUP
)

# LLM表情包
async def generate_image_LLM(prompt):
    url = meme_url
    headers = {
        "Authorization": f"Bearer {meme_token}",
        "Content-Type": "application/json",
    }
    data = {"model": "6615735eaa7af4f70cf3a872", "prompt": "为下面的聊天回复生成一个表情包：" + prompt,"stream": False}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            if "data" in result and len(result["data"]) > 0:
                return result["data"][0]["url"]
            else:
                logger.error("生成失败，响应数据:", result)
    except httpx.RequestError as e:
        logger.error(f"请求错误: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP 错误响应: {e.response.status_code}")
    except Exception as e:
        logger.error(f"生成图片未知错误: {e}")
        return None
    return None

async def generate_image(content):
    url = f"https://doutu.lccyy.com/doutu/items?keyword={content}&pageNum=1&pageSize=30"
    
    try:
        # 使用异步上下文管理器管理连接
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON structure")

            items = data.get("items", [])
            if not items: 
                return ""

            remaining_items = items[1:] if len(items) > 1 else []
            if not remaining_items:
                return ""

            pool = remaining_items[:5] if len(remaining_items) >=5 else remaining_items
            selected = random.choice(pool)
            return selected.get("url")

    except httpx.HTTPStatusError as e:
        logger.error(f"表情包HTTP错误: {e.response.status_code} {e.request.url}")
    except httpx.RequestError as e:
        logger.error(f"请求表情包失败: {e.__class__.__name__} {e.request.url}")
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"表情包数据解析失败: {e}")
    except Exception as e:
        logger.error(f"表情包未知错误: {e}")
    return ""


def convert_chat_history(history):
    converted = []
    for message in history["messages"]:
        sender = message["sender"].get("card") or message["sender"]["nickname"]
        if isinstance(message["message"], list):
            text_parts = [
                msg["data"]["text"]
                for msg in message["message"]
                if msg["type"] == "text"
            ]
        elif isinstance(message["message"], str) and "CQ:" not in message["message"]:
            text_parts = [message["message"]]
        else:
            text_parts = []
        content = "".join(text_parts).strip()
        if not content:
            continue
        time_str = time.strftime("%H:%M:%S", time.localtime(message["time"]))
        converted.append({"T": time_str, "N": sender.strip(), "C": content})
    result = []
    for json_obj in converted:
        json_str = json.dumps(json_obj, ensure_ascii=False)
        result.append(json_str[1:-1])
    return "\n".join(result)

@random_reply.handle()
async def handle(
    bot: Bot, event: GroupMessageEvent, user_info: UserInfo = BotUserInfo()
):
    #给管理员发送预警
    if balance_on:
        try:
            alerts = await alert_monitor.check_and_alert(token=plugin_config.oneapi_key)
            if alerts:
                for id in superusers:
                    await Text(alerts[-1]).send_to(target=TargetQQPrivate(user_id=int(id)),bot=get_bot())
    
        except Exception as e:
            logger.error(f"余额检查失败：{str(e)}")
    
    try:
        messages = await get_history_chat(bot, event.group_id)
        if not messages:
            logger.error("随机回复插件未获取到聊天记录")
            return
        reply = await get_res(messages, user_info.user_displayname)
        reply = clean_model_output(reply)
        
        if not reply:
            logger.error("随机回复插件生成回复失败")
            return
    except Exception as e:
        logger.error("随机回复插件出错" + str(e))
        return

    if not meme_enable:
        await Text(reply).finish()
    
    else:
        try:
            await Text(reply).send()
            if meme_url == "":
                if image_url := await generate_image(reply):
                    await Image(image_url).finish()
            else:
                if image_url := await generate_image_LLM(reply):
                    await Image(image_url).finish()
        except FinishedException:
            raise
        except Exception as e:
            logger.error(f"消息处理异常: {e}")
            return

if plugin_config.group_reply_prefix != "":
    prefix_reply = on_startswith(plugin_config.group_reply_prefix, block=True, priority=1)
    prefix_reply.append_handler(handle)

else:
    to_me_reply = on_message(rule=Rule(to_me_rule) & to_me(), priority=998, block=True, permission=GROUP
)
    to_me_reply.append_handler(handle)

    
## 参考了聊天记录总结插件内获取聊天记录的代码
async def get_history_chat(bot: Bot, group_id: int):
    messages = []
    try:
        history = await bot.get_group_msg_history(
            group_id=group_id,
            count=history_lens,
        )
        messages = convert_chat_history(history)
    except Exception as e:
        logger.error(f"获取聊天记录失败: {e!s}")
        raise Exception(f"获取聊天记录失败,错误信息: {e!s}")
    return messages


if balance_on:
    get_balance = on_command("查询余额", block=False, priority=1)
    @get_balance.handle()
    async def _(
        bot: Bot, event: GroupMessageEvent, user_info: UserInfo = BotUserInfo()
    ):
        try:
            balance = await get_current_balance(plugin_config.oneapi_key)
        except Exception as e:
            logger.error("获取余额出错" + str(e))
            Text("获取余额出错").finish()

        await Text("当前余额为：" + str(balance)).finish()