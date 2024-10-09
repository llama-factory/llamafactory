在大模型百花齐放的今天，开发者往往需要花费大量时间在不同平台间切换，查找文档、对比接口。为了解决这个痛点，我们创建了一个集成了各大模型平台API信息的速查资源。这包括了从OpenAI到Gemini，从百川智能到腾讯混元等主流大模型平台的调用信息，全部集中在一处，方便开发者快速查找和使用。

> 详情见：[llamafactory.cn](https://www.llamafactory.cn/llm-integration/overview.html)

![在这里插入图片描述](https://i-blog.csdnimg.cn/direct/2c73307d6c6e4b2ebcf7f121051f2e41.png#pic_center)


## 我们整理了什么？

1. **OpenAI兼容接口清单**
   - 8家支持OpenAI格式调用的服务商信息
   - 包含base_url、文档链接和API Key申请入口
   - 标准化的调用示例代码

2. **其他独立接口平台**
   - 6家使用自有格式的平台完整对接信息
   - 统一的信息展示，方便对比和选择

3. **一键可用的示例代码**
   - 所有平台的标准调用示例
   - 即复制即可用的代码片段

## 这对开发者意味着什么？

1. **不再需要满世界找文档**
   - 14家主流大模型平台的信息集中在一处
   - 告别在各家官网间反复跳转的困扰

2. **快速启动新项目**
   - 5分钟内完成任意平台的接入
   - 不用再花时间研究不同的API文档

3. **轻松进行多模型对比**
   - 统一的信息展示方式
   - 方便横向对比不同平台的特点

## 实际应用案例

比如想使用Moonshot的模型，只需要：

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.moonshot.cn/v1",  # 从我们的清单中直接复制
    api_key="your-api-key"                  # 通过提供的链接快速申请
)

completion = client.chat.completions.create(
    model="moonshot-v1-8k",
    messages=[
        {"role": "user", "content": "你好，请问你是谁？"}
    ]
)
print(completion.choices[0].message.content)
```

想换成其他平台？只需要更改base_url和model名称，其他代码保持不变。

## 持续更新承诺

我们会持续跟进各平台的更新，确保信息始终保持最新。开发者可以放心使用，不用担心因为信息过时而导致开发障碍。

## 结语

在这个大模型蓬勃发展的时代，我们希望能为开发者提供一些实实在在的帮助。这个速查宝典就是我们的一点小小贡献。它也许不是最完美的，但我们相信它确实能为开发者节省宝贵的时间和精力。

如果在使用过程中有任何建议或者发现需要补充的信息，欢迎随时交流。让我们一起，用更聪明的方式工作，创造更多可能。