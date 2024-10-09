在开发和调试大模型训练代码时，使用print语句进行调试往往效率低下且容易遗漏重要信息。本文将介绍三种使用VSCode进行交互式debug的方法，让你的调试过程更加高效和精确。

> 具体见 [VSCode debug 配置生成器](https://www.llamafactory.cn/tools/vscode-debug-llm.html)

## 准备工作

在开始之前，请确保：
1. 已安装VSCode和Python扩展
2. 在你的项目中已设置好训练环境
3. 了解基本的断点设置方法（在代码行号左侧点击即可设置断点）

## 方法一：直接启动调试

这是最简单且功能完整的方法，支持单卡和多卡训练场景。

### 步骤一：创建调试配置

1. 点击VSCode左侧的"运行和调试"图标（或按下`Ctrl+Shift+D`）
2. 点击"创建launch.json文件"
3. 在弹出的选项中，选择"Python Debugger"
4. 再选择"Python文件"

![vscode创建launch.json文件](https://i-blog.csdnimg.cn/direct/432a7707f12d4496b9cc82c745421a3b.png)

### 步骤二：使用LLamaFactory调试配置转换器

为了简化配置过程，LLamaFactory提供了一个便捷的调试配置转换器。你只需要：

1. 将原始的训练命令粘贴到转换器中
2. 点击"转换"按钮
3. 复制生成的配置
![llamfactory.cn的大模型debug工具](https://i-blog.csdnimg.cn/direct/12264e1ee13343dabe081a56b8dfc407.png)

### 步骤三：配置launch.json

将转换器生成的配置替换到`.vscode/launch.json`文件中。一个典型的多卡训练配置如下：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "debug.llamafactory.cn",
            "type": "debugpy",
            "request": "launch",
            "module": "torch.distributed.run",
            "console": "integratedTerminal",
            "args": [
                "--nproc_per_node",
                "4",
                "--master_port",
                "25644",
                "src/llamafactory/launcher.py",
                "--model_name",
                "llama31",
                "--dataset_name",
                "data",
                "--learning_rate",
                "1e-4",
                "--size_valid_set",
                "0.05",
                "--warmup_ratio",
                "0.03",
                "--optim",
                "paged_adamw_32bit",
                "--lr_scheduler_type",
                "cosine",
                "--per_device_train_batch_size",
                "16",
                "--per_device_eval_batch_size",
                "16",
                "--lora_alpha",
                "16",
                "--lora_r",
                "8",
                "--lora_target_modules",
                "W_pack",
                "--max_input_length",
                "256",
                "--max_output_length",
                "64",
                "--num_train_epochs",
                "3",
                "--evaluation_strategy",
                "steps",
                "--logging_steps",
                "100",
                "--save_steps",
                "300",
                "--eval_steps",
                "500",
                "--save_total_limit",
                "5",
                "--num_workers",
                "64",
                "--gradient_checkpointing",
                "--ddp_find_unused_parameters",
                "False",
                "--logging_first_step",
                "True",
                "--output_dir",
                "./output",
                "--report_to",
                "tensorboard"
            ],
            "env": {
                "CUDA_VISIBLE_DEVICES": "\"0,1,2,3\""
            },
            "justMyCode": false
        }
    ]
}
```

### 步骤四：开始调试

1. 在需要调试的代码处设置断点
2. 点击左上角的绿色箭头（或按下F5）开始调试

![vscode选择配置开始debug](https://i-blog.csdnimg.cn/direct/271cd698dc0d49f392e335690c7afa5e.png)

## 方法二：监听端口调试

这种方法需要修改训练代码，适用于特定场景。

### 步骤一：添加调试代码

在训练的主函数（例如`https://github.com/hiyouga/LLaMA-Factory/blob/main/src/llamafactory/train/tuner.py#L43`）开始处，添加以下代码：

```python
import os
import debugpy

# 只在rank 0进程中启动调试器
if int(os.environ.get('LOCAL_RANK', '0')) == 0:
    debugpy.listen(("localhost", 5678))
    print("⏳ 等待调试器附加...")
    debugpy.wait_for_client()
    print("🚀 调试器已附加！继续执行...")
```

### 步骤二：配置launch.json

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python Debugger: Attach",
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "justMyCode": false
        }
    ]
}
```

### 步骤三：启动调试

1. 正常启动训练脚本，例如：
   ```bash
   CUDA_VISIBLE_DEVICES=6,7 llamafactory-cli train examples/train_lora/llama3_lora_sft.yaml
   ```
2. 当看到"⏳ 等待调试器附加..."时，在VSCode中选择"Python Debugger: Attach"
3. 点击开始调试按钮

## 方法三：命令行参数调试

这种方法不需要修改代码，但只支持单卡调试。

### 步骤一：配置launch.json

与方法二相同的配置。

### 步骤二：修改启动命令

将原来的启动命令修改为：

```bash
CUDA_VISIBLE_DEVICES=0 torchrun --nproc_per_node 1 \
    --master_port 23456 \
    -m debugpy \
    --listen 5678 \
    --wait-for-client \
    src/train.py \
    examples/train_lora/llama3_lora_sft.yaml
```

### 步骤三：启动调试

1. 运行修改后的命令
2. 在VSCode中选择"Python Debugger: Attach"并开始调试

## 调试技巧

1. **设置条件断点**：右键点击断点，可以设置只在特定条件满足时才中断
2. **查看变量**：在调试面板中可以查看当前所有变量的值
3. **监视表达式**：添加监视可以实时查看特定表达式的值
4. **使用调试控制台**：可以在这里执行Python代码，实时查看结果

## 注意事项

1. 方法一支持多卡调试，且配置最为简单，推荐优先使用
2. 方法二和方法三中，调试器会等待VSCode连接，在连接前程序不会继续执行
3. 使用调试器可能会略微影响训练速度，但这对调试过程的影响通常可以忽略

## 总结

通过本文介绍的三种方法，相信你已经可以根据不同场景选择合适的调试方式。特别推荐使用方法一，配合[LlamaFactory](https://www.llamafactory.cn/tools/vscode-debug-llm.html)的调试配置转换器，可以快速开始调试工作