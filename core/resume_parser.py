"""简历解析模块 — 支持 PDF、Word、TXT"""
import re
import os
from pathlib import Path

from .models import Resume


# --- 技能关键词库 ---
SKILL_KEYWORDS = [
    # 编程语言
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "php", "ruby", "swift", "kotlin", "scala", "r", "matlab",
    # 前端
    "react", "vue", "vue.js", "angular", "html", "css", "sass", "less",
    "webpack", "vite", "nextjs", "next.js", "nuxt",
    # 后端
    "spring", "spring boot", "django", "flask", "fastapi", "express",
    "node.js", "nodejs", "nestjs", ".net",
    # 数据库
    "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch",
    "oracle", "sql server", "sqlite", "clickhouse",
    # 大数据/云
    "hadoop", "spark", "kafka", "hive", "flink", "aws", "azure",
    "gcp", "docker", "kubernetes", "k8s", "jenkins", "ci/cd",
    # AI/ML
    "机器学习", "深度学习", "tensorflow", "pytorch", "keras",
    "nlp", "自然语言处理", "计算机视觉", "opencv",
    "scikit-learn", "sklearn", "pandas", "numpy",
    # 其他
    "git", "linux", "nginx", "微服务", "restful", "api",
    "agile", "scrum", "设计模式", "数据结构", "算法",
]

EDUCATION_LEVELS = {
    "博士": 5, "phd": 5, "doctor": 5,
    "硕士": 4, "研究生": 4, "master": 4,
    "本科": 3, "学士": 3, "bachelor": 3,
    "大专": 2, "专科": 2, "college": 2,
    "高中": 1, "high school": 1,
}


def extract_text_from_pdf(filepath: str) -> str:
    """从 PDF 提取文本"""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n".join(text_parts)
    except ImportError:
        raise ImportError("解析 PDF 需要安装 pdfplumber: pip install pdfplumber")
    except Exception as e:
        raise RuntimeError(f"PDF 解析失败: {e}")


def extract_text_from_docx(filepath: str) -> str:
    """从 Word 文档提取文本"""
    try:
        from docx import Document
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        raise ImportError("解析 Word 需要安装 python-docx: pip install python-docx")
    except Exception as e:
        raise RuntimeError(f"Word 解析失败: {e}")


def extract_text_from_txt(filepath: str) -> str:
    """从 TXT 文件提取文本"""
    for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"无法解码文件: {filepath}")


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}


def extract_text(filepath: str) -> str:
    """根据文件类型提取文本"""
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(filepath)
    elif ext == ".txt":
        return extract_text_from_txt(filepath)
    elif ext in IMAGE_EXTENSIONS:
        # 图片文件走 OCR
        from .ocr_parser import extract_text_from_image
        return extract_text_from_image(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {ext}（支持: PDF/Word/TXT/JPG/PNG）")


def extract_name(text: str) -> str:
    """提取姓名"""
    patterns = [
        r"姓\s*名[：:\s]*([^\n]{2,4})",
        r"^([^\n]{2,4})\s*$",  # 第一行单独的短文本
    ]
    for pat in patterns:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            name = m.group(1).strip()
            if re.match(r"^[一-龥]{2,4}$", name):
                return name
    return ""


def extract_phone(text: str) -> str:
    """提取手机号"""
    m = re.search(r"1[3-9]\d{9}", text)
    return m.group() if m else ""


def extract_email(text: str) -> str:
    """提取邮箱"""
    m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return m.group() if m else ""


def extract_skills(text: str) -> list[str]:
    """提取技能列表"""
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill.lower() in text_lower:
            # 去重：避免 vue 和 vue.js 同时出现
            normalized = skill.lower().replace(".js", "").replace("js", "")
            if not any(normalized in s.lower().replace(".js", "").replace("js", "") for s in found):
                found.append(skill)
    return found


def extract_work_years(text: str) -> float:
    """提取工作年限"""
    # 先尝试直接匹配文字描述
    patterns = [
        r"(\d+)\s*[年+]\s*(?:以上)?\s*(?:工作|开发|从业)?\s*经[验历]",
        r"工作\s*[经年限]*[：:\s]*(\d+)\s*年",
        r"(?:work|experience)[^\d]*(\d+)\s*(?:year|yr)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1))

    # 从工作经历日期范围计算：匹配 "2019.06 - 2021.02" 或 "2019/06-至今" 格式
    # 排除教育经历的日期范围（包含学校关键词的行）
    from datetime import datetime
    edu_keywords = ("大学", "学院", "学校", "本科", "硕士", "博士", "大专", "专科",
                     "bachelor", "master", "phd", "university", "college", "school")

    total_months = 0
    now = datetime.now()
    for line in text.split("\n"):
        line_stripped = line.strip()
        # 跳过包含教育关键词的行
        if any(kw in line_stripped.lower() for kw in edu_keywords):
            continue
        # 提取日期范围
        m = re.search(
            r"(20\d{2})[./-](\d{1,2})\s*[-~至到]\s*(?:(20\d{2})[./-](\d{1,2})|(至今|现在))",
            line_stripped,
        )
        if m:
            start_year, start_month = int(m.group(1)), int(m.group(2))
            if m.group(5):  # 至今/现在
                end_year, end_month = now.year, now.month
            else:
                end_year, end_month = int(m.group(3)), int(m.group(4))
            months = (end_year - start_year) * 12 + (end_month - start_month)
            total_months += max(months, 0)
    if total_months > 0:
        return round(total_months / 12, 1)
    return 0.0


def extract_education(text: str) -> str:
    """提取最高学历"""
    text_lower = text.lower()
    best_level = 0
    best_edu = ""
    for keyword, level in EDUCATION_LEVELS.items():
        if keyword in text_lower and level > best_level:
            best_level = level
            best_edu = keyword
    # 统一中文返回
    edu_map = {
        "博士": "博士", "phd": "博士", "doctor": "博士",
        "硕士": "硕士", "研究生": "硕士", "master": "硕士",
        "本科": "本科", "学士": "本科", "bachelor": "本科",
        "大专": "大专", "专科": "大专", "college": "大专",
        "高中": "高中", "high school": "高中",
    }
    return edu_map.get(best_edu, best_edu)


def extract_salary(text: str) -> str:
    """提取期望薪资"""
    patterns = [
        r"期望薪资[：:\s]*([\d]+\s*[kK万wW]?\s*[-~至到]\s*[\d]+\s*[kK万wW]?)",
        r"薪资[期望要求]*[：:\s]*([\d]+\s*[kK万wW]?\s*[-~至到]\s*[\d]+\s*[kK万wW]?)",
        r"([\d]+\s*[kK]\s*[-~至到]\s*[\d]+\s*[kK])",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def extract_location(text: str) -> str:
    """提取期望工作地点"""
    cities = [
        "北京", "上海", "广州", "深圳", "杭州", "成都", "南京", "武汉",
        "西安", "重庆", "苏州", "天津", "长沙", "郑州", "青岛", "大连",
        "厦门", "合肥", "福州", "济南", "珠海", "东莞", "佛山",
    ]
    # 先看是否有"期望城市/地点"标注
    m = re.search(r"(?:期望)?(?:工作)?(?:城市|地点)[：:\s]*([^\n]+)", text)
    if m:
        location_text = m.group(1)
        for city in cities:
            if city in location_text:
                return city
    # 否则扫描全文取第一个出现的城市
    for city in cities:
        if city in text:
            return city
    return ""


def extract_experience_entries(text: str) -> list[str]:
    """提取工作经历条目"""
    entries = []
    # 匹配 "2020.01 - 2023.05 公司名" 或 "2020/01-2023/05" 格式
    pattern = r"((?:20\d{2})[./-]\d{1,2}\s*[-~至到]\s*(?:(?:20\d{2})[./-]\d{1,2}|至今|现在).*)"
    for m in re.finditer(pattern, text):
        line = m.group(1).strip()
        if len(line) < 100:
            entries.append(line)
    return entries


def parse_resume(filepath: str) -> Resume:
    """解析简历文件，返回 Resume 对象"""
    filepath = str(filepath)
    text = extract_text(filepath)

    return Resume(
        name=extract_name(text),
        phone=extract_phone(text),
        email=extract_email(text),
        skills=extract_skills(text),
        work_years=extract_work_years(text),
        education=extract_education(text),
        expected_salary=extract_salary(text),
        expected_location=extract_location(text),
        work_experience=extract_experience_entries(text),
        raw_text=text[:2000],  # 保留前2000字符
        source_file=os.path.basename(filepath),
    )


def parse_resume_from_text(text: str, source: str = "manual_input") -> Resume:
    """从纯文本解析简历（用于手动输入）"""
    return Resume(
        name=extract_name(text),
        phone=extract_phone(text),
        email=extract_email(text),
        skills=extract_skills(text),
        work_years=extract_work_years(text),
        education=extract_education(text),
        expected_salary=extract_salary(text),
        expected_location=extract_location(text),
        work_experience=extract_experience_entries(text),
        raw_text=text[:2000],
        source_file=source,
    )
