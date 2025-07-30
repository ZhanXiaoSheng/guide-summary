# 指引总结生成器 API

基于 FastAPI 的大模型接口服务，用于生成应急事件的智能总结。

---

## 📁 项目结构

guide_summary/
├── config/
│ ├── init.py
│ ├── settings.py # 配置管理（.env）
│ └── logging_conf.py # 日志配置
├── core/
│ ├── init.py
│ ├── generator.py # 大模型调用逻辑
│ └── models.py # 数据模型
├── routers/
│ ├── init.py
│ └── summary.py # /summary 接口
├── main.py # FastAPI 主程序（含启动）
├── requirements.txt # 依赖列表
└── .env # 环境变量（本地配置）


---

## ⚙️ 配置说明

### `.env` 文件示例
```env
APP_NAME=Guide Summary API
API_PREFIX=/api/v1
PORT=8000
MODEL_API_KEY=sk-
MODEL_ENDPOINT=https://dashscope.aliyuncs.com/api/v1/...
DEBUG=false
```

## 🚀 部署方式（Windows）
###  前提条件
1. Python 3.8+ 已安装并加入 PATH
2. 项目文件已复制到目标服务器
### 启动服务
1. 双击 start.bat 即可启动
2. 第一次运行会自动创建虚拟环境并安装依赖
3. 后续运行将跳过安装，直接启动服务
### 支持参数：
1. `start.bat`：正常启动
2. `start.bat -r`：强制重装依赖（清理旧环境）
### 停止服务
1. 双击 `stop.bat` 可终止服务
2. 或直接关闭命令行窗口（不推荐）
### 访问 API
1. Swagger UI: http://<服务器IP>:8000/api/v1/docs
2. 健康检查: http://<服务器IP>:8000/health