<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-random-reply
</div>

# 介绍
- 根据当前语境在群聊内随机攻击群友
- 可以更换回复风格调教prompt让bot随机拟人回复
- bot的回复效果与选用的llm模型有关，经过半个多月的测试，中文语境下使用deepseek-r1的回复效果最佳，但是成本较高。推荐使用deepseek-v3模型，在保证回复质量的情况下减少使用成本。免费方案可以使用硅基流动的THUDM/glm-4-9b-chat模型进行下位替代，但是效果欠佳。
- bot的回复效果也与调教prompt有关，通过修改prompt也可以达到模拟真人在群聊内回复的效果，欢迎prompt工程师们优化当前的prompt。
# 效果

<img src="demo4.jpg" width="40%">
<img src="demo1.jpg" width="40%">
<img src="demo3.jpg" width="40%">
<img src="demo2.jpg" width="40%">

# 安装

* 手动安装
  ```
  git clone https://github.com/Alpaca4610/nonebot_plugin_random_reply.git
  ```

  下载完成后在bot项目的pyproject.toml文件手动添加插件：

  ```
  plugin_dirs = ["xxxxxx","xxxxxx",......,"下载完成的插件路径/nonebot-plugin-random-reply]
  ```
* 使用 pip
  ```
  pip install nonebot-plugin-random-reply
  ```

# 配置文件

在Bot根目录下的.env文件中追加如下内容：
必填内容：
```
oneapi_key = ""  # API KEY
oneapi_url = ""  # llm提供商地址，使用deepseek请填写"https://api.deepseek.com"，使用硅基流动请填写"https://api.siliconflow.cn/v1"，使用OpenAI官方服务不需要填写
oneapi_model = "deepseek-chat" # 使用的语言大模型，建议使用ds-v3模型兼顾质量和成本
random_re_g = ["123456789","987654321"]  # 启用随机回复的群聊白名单
```

可选内容（嫌麻烦可以不看）：
```
reply_lens = 30 # 参考的聊天记录长度
reply_pro = 0.08   # 随机回复概率，取值范围0~1，越大回复概率越高
reply_prompt = ""  #自定义bot的回复风格prompt
```

# 使用方法
填好配置文件和群聊白名单后，bot就会根据当前话题随机攻击群友
@机器人会根据本条信息回复

# 自定义prompt范例

```
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
```
