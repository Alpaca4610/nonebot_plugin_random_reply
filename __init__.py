from nonebot import on_message, require
require("nonebot_plugin_saa")
from nonebot_plugin_saa import Text

import nonebot
import random
import time
import json

from openai import AsyncOpenAI
from nonebot.rule import is_type
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot_plugin_userinfo import BotUserInfo, UserInfo
from .config import Config, ConfigError


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

random_reply = on_message(
    priority=100,
    rule=is_type(GroupMessageEvent),
    block=True
)


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


@random_reply.handle()
async def handle_whats_talk(bot: Bot, event: GroupMessageEvent, user_info: UserInfo = BotUserInfo(),):
    group_id = event.group_id
    if str(group_id) not in [""]:    ## 群聊白名单
        return
    if random.random() < reply_pro:
        try:
            messages = await get_history_chat(bot, group_id)
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
        await Text(reply).finish()
    else:
        return

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
    # logger.info(messages)
    return messages

async def get_res(history, name):
    response = await client.chat.completions.create(
        model=model_id,
        messages=[
            {
                "role": "user",
                "content": f"""
                【任务规则】
1. 根据当前聊天记录的语境，回复最后1条内容进行回应，聊天记录中可能有多个话题，注意分辨最后一条信息的话题，禁止跨话题联想其他历史信息
2. 用中文互联网常见的口语化短句回复，禁止使用超过30个字的长句
3. 模仿真实网友的交流特点：适当使用缩写、流行梗、表情符号（但每条最多1个）,精准犀利地进行吐槽
4. 输出必须为纯文本，禁止任何格式标记或前缀
5. 使用00后常用网络语态（如：草/绝了/好耶）
6. 核心萌点：偶尔暴露二次元知识
7. 当出现多个话题时，优先回应最新的发言内容

【回复特征】
- 句子碎片化（如：笑死 / 确实 / 绷不住了）
- 高频使用语气词（如：捏/啊/呢/吧）
- 有概率根据回复的语境加入合适emoji帮助表达
- 有概率使用某些流行的拼音缩写
- 有概率玩谐音梗

【应答策略】
遇到ACG话题时：
有概率接经典梗（如：团长你在干什么啊团长）
禁用颜文字时改用括号吐槽（但每3条限1次）
克制使用表情包替代词（每5条发言限用1个→）

每条聊天记录的格式为:  "T": "消息发送时间", "N": "发送者的昵称", "C": "消息内容" 
请始终保持自然随意的对话风格，避免完整句式或逻辑论述。输出禁止包含任何格式标记或前缀和分析过程,禁止包含任何格式标记或前缀和分析过程，禁止包含任何格式标记或前缀和分析过程
在下面的历史聊天记录中，你在群聊中的昵称为{name},现在请处理最新消息：\n" 
                """ + "\n".join(history),
            },
        ],
    )

    return response.choices[0].message.content
