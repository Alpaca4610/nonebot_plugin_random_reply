from pydantic import BaseModel
from typing import Optional, Dict, List

class Config(BaseModel):
    oneapi_key: Optional[str] = ""  # OneAPI KEY
    oneapi_url: Optional[str] = ""  # API地址
    oneapi_model: Optional[str] = "deepseek-chat" # 使用的语言大模型，建议使用ds-v3模型兼顾质量和成本

    gemini_model: Optional[str] = "gemini-2.0-flash" # Gemini模型
    gemini_key: Optional[str] = ""  # Gemini KEY
    gemini_proxy: Optional[str] = ""  # Gemini 代理

    random_re_g: List[str] = [""]  # 启用随机回复的白名单
    
    reply_lens: int = 30 # 参考的聊天记录长度
    reply_pro: float = 0.05   # 默认随机回复概率
    group_reply_pro: Dict[str, float] = {}  # 分群回复概率配置
    reply_prompt_url: str = ""
    
    group_reply_prefix: str = "" # 群聊回复前缀，填写此处后@机器人将不会触发回复
    
    # LLM表情包，填写下面的内容开启LLM选择表情包，否则使用第三方API
    random_meme_url: str = "" # 用于llm选择表情包的glm-free-api地址
    random_meme_token : str = "" # glm-free-api的token

    # 表情包开关
    meme_enable: bool = True # 是否使用第三方斗图API回复表情包

    #硅基流动余额查询
    balance_on: bool = False
    balance_thresholds : Optional[List[float]] = [10.0, 5.0, 2.0]
class ConfigError(Exception):
    pass