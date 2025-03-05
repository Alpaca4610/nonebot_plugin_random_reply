from .config import Config, ConfigError
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent,GROUP
from nonebot.log import logger
from nonebot.rule import Rule, to_me
from nonebot.plugin import PluginMetadata
from nonebot import on_message, require
from nonebot.exception import FinishedException
from openai import AsyncOpenAI
import json
import time
import random
import nonebot
import httpx

require("nonebot_plugin_saa")
from nonebot_plugin_saa import Text,Image
require("nonebot_plugin_userinfo")
from nonebot_plugin_userinfo import BotUserInfo, UserInfo

__plugin_meta__ = PluginMetadata(
    name="拟人回复bot",
    description="根据群聊语境随机攻击群友，基于llm选择表情包回复",
    usage="""
    配置好后bot随机攻击群友，@机器人也可触发
    """,
    config=Config,
    extra={},
    type="application",
    homepage="https://github.com/Alpaca4610/nonebot_plugin_random_reply",
    supported_adapters={"~onebot.v11"},
)


default_prompt = """【任务规则】
1. 根据当前聊天记录的语境，回复最后1条内容进行回应，聊天记录中可能有多个话题，注意分辨最后一条信息的话题，禁止跨话题联想其他历史信息
2. 用贴吧老哥的风格的口语化短句回复，禁止使用超过30个字的长句，句子碎片化，犀利地、一阵见血地锐评
3. 模仿真实网友的交流特点：适当使用缩写、流行梗、表情符号（但每条最多1个）
4. 输出必须为纯文本，禁止任何格式标记或前缀
5. 当出现多个话题时，优先回应最新的发言内容"""

plugin_config = Config.parse_obj(nonebot.get_driver().config.dict())

if not plugin_config.oneapi_key:
    raise ConfigError("请配置大模型使用的KEY")
if plugin_config.oneapi_url:
    client = AsyncOpenAI(
        api_key=plugin_config.oneapi_key, base_url=plugin_config.oneapi_url
    )
else:
    client = AsyncOpenAI(api_key=plugin_config.oneapi_key)

model_id = plugin_config.oneapi_model
history_lens = plugin_config.reply_lens
reply_pro = plugin_config.reply_pro
whitelsit = plugin_config.random_re_g

meme_url = plugin_config.random_meme_url
meme_token = plugin_config.random_meme_token

if plugin_config.reply_prompt == "":
    prompt = default_prompt
else:
    prompt = plugin_config.reply_prompt

async def random_rule(event: GroupMessageEvent) -> bool:
    if str(event.group_id) in whitelsit and random.random() < reply_pro:
        return True
    return False

async def to_me_rule(event: GroupMessageEvent) -> bool:
    if str(event.group_id) in whitelsit:
        return True
    return False


random_reply = on_message(
    priority=999,
    rule=Rule(random_rule),
    block=True,
    permission=GROUP
)

to_me_reply = on_message(
    rule= Rule(to_me_rule) & to_me(),
    priority=998,
    block=True,
    permission=GROUP
)

async def generate_image(prompt):
    url = meme_url
    headers = {
        "Authorization": f"Bearer {meme_token}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "6615735eaa7af4f70cf3a872",
        "prompt": prompt
    }

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

def convert_chat_history(history):
    converted = []
    for message in history["messages"]:
        sender = message["sender"].get("card") or message["sender"]["nickname"]
        if isinstance(message["message"], list):
            text_parts = [msg["data"]["text"]
                          for msg in message["message"]
                          if msg["type"] == "text"]
        elif isinstance(message["message"], str) and "CQ:" not in message["message"]:
            text_parts = [message["message"]]
        else:
            text_parts = []
        content = "".join(text_parts).strip()
        if not content:
            continue
        time_str = time.strftime(
            "%H:%M:%S", time.localtime(message["time"]))
        converted.append({
            "T": time_str,
            "N": sender.strip(),
            "C": content
        })
    result = []
    for json_obj in converted:
        json_str = json.dumps(json_obj, ensure_ascii=False)
        result.append(json_str[1:-1])
    return "\n".join(result)

@to_me_reply.handle()
@random_reply.handle()
async def handle_whats_talk(bot: Bot, event: GroupMessageEvent, user_info: UserInfo = BotUserInfo()):
    try:
        messages = await get_history_chat(bot, event.group_id)
        if not messages:
            logger.error("随机回复插件未获取到聊天记录")
            return
        reply = await get_res(messages, user_info.user_displayname)
        if not reply:
            logger.error("随机回复插件生成回复失败")
            return
    except Exception as e:
        logger.error("随机回复插件出错"+str(e))
        return
    if meme_url == "":
        await Text(reply).finish()
    else:
        try:
            await Text(reply).send()
            if meme_url := await generate_image(reply):
                await Image(meme_url).finish()
        except FinishedException:
            raise
        except Exception as e:
            logger.error(f"消息处理异常: {e}")
            return

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


async def get_res(history, name):
    response = await client.chat.completions.create(
        model=model_id,
        messages=[
            {
                "role": "user",
                "content": prompt + f"""
每条聊天记录的格式为:  "T": "消息发送时间", "N": "发送者的昵称", "C": "消息内容" 
请始终保持自然随意的对话风格，避免完整句式或逻辑论述。输出禁止包含任何格式标记或前缀和分析过程,禁止包含任何格式标记或前缀和分析过程，禁止包含任何格式标记或前缀和分析过程
在下面的历史聊天记录中，你在群聊中的昵称为{name},现在请处理最新消息：\n" 
                """ + "\n".join(history),
            },
        ],
    )

    return response.choices[0].message.content
