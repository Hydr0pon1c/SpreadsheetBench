# SpreadsheetBench 运行说明

本文档记录本机当前这套环境如何跑实验。假设仓库路径是：

```bash
cd ~/SpreadsheetBench
```

Conda 环境名：

```bash
spreadsheetbench
```

本机已经构建过的 Docker 镜像：

```bash
xingyaoww/codeact-execute-api:latest
xingyaoww/codeact-executor:latest
python:3.9
```

## 1. Docker 和代码执行 API

评测中的 `*_exec` 方法需要本地代码执行服务。它由两层组成：

- Docker daemon：负责启动 executor 容器。
- `code_exec_docker/api.py`：监听 `8081`，推理脚本通过 HTTP 调它。

### 1.1 检查 Docker 是否已经可用

```bash
docker info
```

如果能看到 Server 信息，说明 Docker daemon 已经启动，并且当前 shell 有权限访问 Docker。

再检查镜像：

```bash
docker images | grep -E 'xingyaoww/codeact|python'
```

### 1.2 如果 Docker daemon 没开

本机是 snap 安装的 Docker，启动命令是：

```bash
sudo systemctl start snap.docker.dockerd.service
```

如果要设置为开机启动：

```bash
sudo systemctl enable snap.docker.dockerd.service
```

如果当前用户不能直接执行 `docker info`，需要确认用户在 `docker` 组里：

```bash
groups
```

如果不在，需要执行：

```bash
sudo usermod -aG docker $USER
```

执行后要重新登录，或者临时进入新组：

```bash
newgrp docker
```

### 1.3 如果镜像不存在，重新构建

```bash
cd ~/SpreadsheetBench/code_exec_docker && docker build -t xingyaoww/codeact-execute-api -f Dockerfile.api . && docker build -t xingyaoww/codeact-executor -f Dockerfile.executor .
```

如果拉取基础镜像失败，先确认 Docker mirror 是否还在：

```bash
docker info | grep -A5 "Registry Mirrors"
```

### 1.4 启动 8081 代码执行 API

必须在 `code_exec_docker` 目录启动，因为 `api.py/jupyter.py` 会读取当前目录下的 `config.json`。

```bash
cd ~/SpreadsheetBench/code_exec_docker && setsid nohup conda run --no-capture-output -n spreadsheetbench python api.py --port 8081 > jupyter_server_8081.log 2>&1 < /dev/null & echo $! > jupyter_server_8081.pid
```

验证 API：

```bash
NO_PROXY=127.0.0.1,localhost curl -sS --max-time 90 -X POST http://127.0.0.1:8081/execute -H 'Content-Type: application/json' -d '{"convid":"smoke-test","code":"print(1+1)"}'
```

预期返回里有：

```json
{"result": "2\n", "new_kernel_created": true}
```

如果端口已被占用，先查进程：

```bash
ps -ef | grep 'api.py --port 8081' | grep -v grep
```

确认后再杀掉旧进程：

```bash
kill <PID>
```

## 2. 切换数据集

代码执行容器里固定通过 `/mnt/data` 访问数据。这个路径由：

```bash
~/SpreadsheetBench/code_exec_docker/config.json
```

里的 `volumes_path` 控制。

当前如果跑 `spreadsheetbench_verified_400`，应设置为：

```json
{
    "volumes_path": "/home/jingxingwang/SpreadsheetBench/data/spreadsheetbench_verified_400"
}
```

切换到 `sample_data_200`：

```json
{
    "volumes_path": "/home/jingxingwang/SpreadsheetBench/data/sample_data_200"
}
```

切换到 `all_data_912_v0.1`：

```json
{
    "volumes_path": "/home/jingxingwang/SpreadsheetBench/data/all_data_912_v0.1"
}
```

修改 `config.json` 后，要重启 `8081` API，否则新 executor 容器不会使用新的挂载路径。

```bash
ps -ef | grep 'api.py --port 8081' | grep -v grep
```

```bash
kill <PID>
```

```bash
cd ~/SpreadsheetBench/code_exec_docker && setsid nohup conda run --no-capture-output -n spreadsheetbench python api.py --port 8081 > jupyter_server_8081.log 2>&1 < /dev/null & echo $! > jupyter_server_8081.pid
```

## 3. 跑推理

推理脚本在：

```bash
~/SpreadsheetBench/inference
```

本仓库有两类推理：

- `inference_single.py`：单轮生成代码。
- `inference_multiple.py`：多轮生成，支持代码执行反馈。

多轮 `--setting` 可选：

- `row_exec`：prompt 里给前几行表格内容，并允许执行代码。
- `react_exec`：不给表格行内容，但使用 ReAct/执行反馈。
- `row_react_exec`：给前几行表格内容，并使用 ReAct/执行反馈。

`--row` 控制 prompt 里放多少行表格内容，默认常用 `5`。

### 3.1 在 verified_400 上跑 row_react_exec

```bash
cd ~/SpreadsheetBench/inference && NO_PROXY=127.0.0.1,localhost conda run --no-capture-output -n spreadsheetbench python inference_multiple.py --dataset spreadsheetbench_verified_400 --setting row_react_exec --code_exec_url http://127.0.0.1:8081/execute --max_turn_num 5 --row 5 --model <MODEL> --api_key <API_KEY> --base_url <BASE_URL>
```

如果已经在脚本默认参数里写好了 `--model/--api_key/--base_url`，可以省略这三个参数：

```bash
cd ~/SpreadsheetBench/inference && NO_PROXY=127.0.0.1,localhost conda run --no-capture-output -n spreadsheetbench python inference_multiple.py --dataset spreadsheetbench_verified_400 --setting row_react_exec --code_exec_url http://127.0.0.1:8081/execute --max_turn_num 5 --row 5
```

输出位置：

```text
data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_<MODEL>/
inference/outputs/conv_multi_row_react_exec_<MODEL>.jsonl
```

注意：脚本会 append 到 `inference/outputs/conv_*.jsonl`，重复运行同一个配置会追加记录，不会自动清空旧结果。`spreadsheetbench_verified_400` 里有少数任务的输入文件名是 `initial.xlsx`，本地代码已改成输出到唯一文件名 `1_<id>_output.xlsx`，避免多个任务写同一个 `output.xlsx`。

如果推理中断或部分任务没有写出 xlsx，可以加 `--skip_existing` 只补缺失输出：

```bash
cd ~/SpreadsheetBench/inference && NO_PROXY=127.0.0.1,localhost conda run --no-capture-output -n spreadsheetbench python inference_multiple.py --dataset spreadsheetbench_verified_400 --setting row_react_exec --code_exec_url http://127.0.0.1:8081/execute --max_turn_num 5 --row 5 --skip_existing
```

### 3.2 跑 single baseline

```bash
cd ~/SpreadsheetBench/inference && NO_PROXY=127.0.0.1,localhost conda run --no-capture-output -n spreadsheetbench python inference_single.py --dataset spreadsheetbench_verified_400 --code_exec_url http://127.0.0.1:8081/execute --row 5 --model <MODEL> --api_key <API_KEY> --base_url <BASE_URL>
```

评测时对应的 setting 是：

```text
single
```

### 3.3 setting 名称对应关系

推理命令里的 `--setting` 和评测命令里的 `--setting` 不完全一样：

```text
inference_multiple.py --setting row_exec        -> evaluation.py --setting multi_row_exec
inference_multiple.py --setting react_exec      -> evaluation.py --setting multi_react_exec
inference_multiple.py --setting row_react_exec  -> evaluation.py --setting multi_row_react_exec
inference_single.py                             -> evaluation.py --setting single
```

## 4. 做评测

评测分两步：

1. 用 LibreOffice 打开/保存输出文件，触发公式重算。
2. 跑 `evaluation.py` 比较输出文件和 golden/answer 文件。

### 4.1 评测 verified_400 的 row_react_exec

```bash
cd ~/SpreadsheetBench/evaluation && conda run --no-capture-output -n spreadsheetbench python open_spreadsheet.py --dir_path ../data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_<MODEL> --backend libreoffice && conda run --no-capture-output -n spreadsheetbench python evaluation.py --dataset spreadsheetbench_verified_400 --setting multi_row_react_exec --model <MODEL>
```

评测结果写到：

```text
outputs/eval_multi_row_react_exec_<MODEL>.json
```

### 4.2 评测 single

```bash
cd ~/SpreadsheetBench/evaluation && conda run --no-capture-output -n spreadsheetbench python open_spreadsheet.py --dir_path ../data/spreadsheetbench_verified_400/outputs/single_<MODEL> --backend libreoffice && conda run --no-capture-output -n spreadsheetbench python evaluation.py --dataset spreadsheetbench_verified_400 --setting single --model <MODEL>
```

### 4.3 其他数据集

只需要同时替换：

- `code_exec_docker/config.json` 里的 `volumes_path`
- 推理命令里的 `--dataset`
- 评测命令里的 `--dataset`
- `open_spreadsheet.py --dir_path` 里的输出目录

例如 `sample_data_200` 的输出目录会是：

```text
data/sample_data_200/outputs/<setting>_<MODEL>/
```

## 5. 并发怎么开

当前仓库的推理脚本没有内置 `--num_workers` 或 `--shard_id` 参数。`code_exec_docker/start_jupyter_server.sh` 里也明确写了暂未启用多个 API worker。

可以安全并发的情况：

- 同时跑不同模型，因为输出目录不同。
- 同时跑不同 setting，因为输出目录不同。
- 同时跑不同数据集，但要为每个数据集启动对应 `volumes_path` 的独立 API 端口，或者不要同时切换同一个 `8081` API 的 `config.json`。

不建议直接并发的情况：

- 同一个 dataset、同一个 model、同一个 setting 开多个完全相同的命令。它们会写同一个输出目录和同一个 `conv_*.jsonl`，容易重复、覆盖或交错写入。

如果要并发跑同一个配置，推荐先给脚本加任务切片参数，例如 `--shard_id` 和 `--num_shards`，让每个进程处理不同样本，并让每个进程写不同的 conversation 文件。不要只靠同时启动多条相同命令。

代码执行 API 支持不同 `--conv_id` 创建不同 kernel/container。所以多进程并发时，每条推理命令应该使用不同的 `--conv_id`：

```bash
--conv_id run0
--conv_id run1
--conv_id run2
```

如果是不同 setting 或不同 model，可以用 `tmux` 分窗口启动多条命令。例如：

```bash
cd ~/SpreadsheetBench/inference && NO_PROXY=127.0.0.1,localhost conda run --no-capture-output -n spreadsheetbench python inference_multiple.py --dataset spreadsheetbench_verified_400 --setting row_react_exec --code_exec_url http://127.0.0.1:8081/execute --conv_id row-react-run --max_turn_num 5 --row 5 --model <MODEL> --api_key <API_KEY> --base_url <BASE_URL>
```

## 6. SSH 断开后要重新做什么

如果只是 SSH 断开，机器没有重启：

- Docker daemon 通常还在。
- 用 `setsid nohup` 启动的 `8081` API 通常还在。
- Conda 环境、Docker 镜像、已解压数据都不需要重做。

回来后检查：

```bash
docker info
```

```bash
NO_PROXY=127.0.0.1,localhost curl -sS --max-time 90 -X POST http://127.0.0.1:8081/execute -H 'Content-Type: application/json' -d '{"convid":"reconnect-check","code":"print(1)"}'
```

如果 `8081` 不通，重新启动：

```bash
cd ~/SpreadsheetBench/code_exec_docker && setsid nohup conda run --no-capture-output -n spreadsheetbench python api.py --port 8081 > jupyter_server_8081.log 2>&1 < /dev/null & echo $! > jupyter_server_8081.pid
```

如果机器重启了：

- Docker daemon 可能会自动起来；如果没起来，执行 `sudo systemctl start snap.docker.dockerd.service`。
- `8081` API 需要重新启动。
- 镜像、conda 环境、数据解压结果不需要重做。

## 7. 常见问题

### 7.1 本地 8081 走了代理

本地 API 调用建议显式加：

```bash
NO_PROXY=127.0.0.1,localhost
```

否则某些代理环境会把 `127.0.0.1:8081` 请求转发出去。

### 7.2 找不到 verified_400 的 xlsx

原始代码假设文件名是 `*_input.xlsx` 和 `*_answer.xlsx`。`spreadsheetbench_verified_400` 使用的是 `*_init.xlsx` 和 `*_golden.xlsx`，本地代码已经改过以兼容这套命名。

### 7.3 OpenAI/httpx 报 `proxies`

如果出现：

```text
TypeError: Client.__init__() got an unexpected keyword argument 'proxies'
```

说明 `openai` 和 `httpx` 版本不匹配。本机当前可用组合是：

```text
openai==1.30.4
httpx==0.27.2
```

### 7.4 Docker pull 失败

本机 Docker daemon 已配置 registry mirrors。检查命令：

```bash
docker info | grep -A5 "Registry Mirrors"
```

如果 mirror 配置丢了，需要重新写 `/var/snap/docker/current/config/daemon.json` 并重启：

```bash
sudo systemctl restart snap.docker.dockerd.service
```

### 7.5 输出文件是 nobody，LibreOffice 报 Permission denied

如果 `open_spreadsheet.py` 报：

```text
Permission denied: '.../outputs/...xlsx'
```

通常是旧 executor 容器以 `nobody:nogroup` 写出了 `644` 文件，当前用户不能覆盖保存。先修复已有输出文件权限：

```bash
sudo chown -R $USER:$USER ~/SpreadsheetBench/data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_qwen3.5-35b-a3b && chmod -R u+rw ~/SpreadsheetBench/data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_qwen3.5-35b-a3b
```

本地 `code_exec_docker/jupyter.py` 已改成让新 executor 容器按当前用户 UID/GID 运行。改完后需要重启 `8081` API 才生效：

```bash
ps -ef | grep 'api.py --port 8081' | grep -v grep
```

```bash
kill <PID>
```

```bash
cd ~/SpreadsheetBench/code_exec_docker && setsid nohup conda run --no-capture-output -n spreadsheetbench python api.py --port 8081 > jupyter_server_8081.log 2>&1 < /dev/null & echo $! > jupyter_server_8081.pid
```
