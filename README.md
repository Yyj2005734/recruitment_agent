# 
招聘智能推荐 Agent
  基于 Python 开发的简历解析 + Boss 直聘岗位实时匹配智能控制台工具，可自动解析多格式简历，实时抓取 Boss 直聘岗位并智能打分推荐。

📋 项目功能

  多格式简历解析支持 PDF/Word/TXT 文档解析支持 JPG/PNG 图片简历 OCR 文字识别自动提取：技能、工作年限、学历、期望薪资、求职城市等信息Boss 直聘实时岗位匹配根据解析后的简历信息，实时抓取 Boss 直聘真实岗位按「学历、经验、技能、薪资、城市」多维度加权打分匹配度从高到低排序展示控制台完整菜单交互手动录入简历信息
查看 / 添加 / 删除本地收藏岗位/智能对话咨询求职问题本地数据持久化岗位数据、简历信息 JSON 存储

🛠️ 技术栈

编程语言：Python 3.10+

文档解析：PyPDF2、python‑docx

图片 OCR 识别：PaddleOCR /pytesseract

网络请求：requests（Boss 直聘接口调用）

分词处理：jieba

数据存储：JSON 本地文件


快速运行

1. 克隆项目

git clone https://github.com/Yyj2005734/recruitment_agent.git

cd recruitment_agent
3. 安装依赖

pip install -r requirements.txt

4. 运行程序

python main.py

项目结构

recruitment_agent/
├── core/                # 核心功能模块

│   ├── agent.py         # 主菜单逻辑

│   ├── boss_connector.py# Boss直聘接口调用

│   ├── resume_parser.py # 文档简历解析

│   ├── ocr_parser.py    # 图片OCR识别

│   ├── matcher.py       # 岗位匹配打分算法

│   ├── job_manager.py   # 本地岗位管理

│   └── models.py        # 数据模型

├── data/                # 本地存储目录（简历、岗位数据）

├── samples/             # 示例文件

├── main.py              # 程序入口

└── requirements.txt     # 依赖清单

项目亮点

  纯 Python 实现，开箱即用，无复杂环境依赖支持图片简历 OCR，适配真实求职场景实时对接 Boss 直聘，岗位数据真实有效多维度智能匹配，精准推荐适配岗位结构清晰，模块化开发，易扩展维护。
