"""岗位库管理模块 — JSON 文件存储"""
import json
import os
from pathlib import Path

from .models import Job


DATA_DIR = Path(__file__).parent.parent / "data"
JOBS_FILE = DATA_DIR / "jobs.json"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_jobs() -> list[Job]:
    """加载所有岗位"""
    if not JOBS_FILE.exists():
        return []
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Job.from_dict(item) for item in data]


def save_jobs(jobs: list[Job]):
    """保存岗位列表"""
    _ensure_data_dir()
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump([j.to_dict() for j in jobs], f, ensure_ascii=False, indent=2)


def add_job(job: Job) -> Job:
    """添加岗位"""
    jobs = load_jobs()
    jobs.append(job)
    save_jobs(jobs)
    return job


def get_job(job_id: str) -> Job | None:
    """根据 ID 获取岗位"""
    for job in load_jobs():
        if job.id == job_id:
            return job
    return None


def delete_job(job_id: str) -> bool:
    """删除岗位"""
    jobs = load_jobs()
    original_len = len(jobs)
    jobs = [j for j in jobs if j.id != job_id]
    if len(jobs) < original_len:
        save_jobs(jobs)
        return True
    return False


def search_jobs(keyword: str = "", location: str = "") -> list[Job]:
    """搜索岗位"""
    jobs = load_jobs()
    results = []
    for job in jobs:
        if keyword:
            kw = keyword.lower()
            match = (kw in job.title.lower() or
                     kw in job.company.lower() or
                     any(kw in s.lower() for s in job.required_skills) or
                     kw in job.description.lower())
            if not match:
                continue
        if location and location not in job.location:
            continue
        results.append(job)
    return results


def import_sample_jobs():
    """导入示例岗位数据"""
    sample_jobs = [
        Job(
            title="Python 高级开发工程师",
            company="字节跳动",
            salary="30k-50k",
            location="北京",
            required_skills=["Python", "Django", "Flask", "MySQL", "Redis"],
            preferred_skills=["Kubernetes", "Docker", "微服务"],
            min_work_years=3,
            education_requirement="本科",
            description="负责后端服务开发和架构设计，参与核心业务系统建设。",
            benefits=["五险一金", "股票期权", "免费三餐", "健身房"],
        ),
        Job(
            title="前端开发工程师",
            company="阿里巴巴",
            salary="25k-45k",
            location="杭州",
            required_skills=["JavaScript", "React", "Vue", "HTML", "CSS"],
            preferred_skills=["TypeScript", "Webpack", "Node.js"],
            min_work_years=2,
            education_requirement="本科",
            description="负责 Web 前端开发，参与电商平台用户体验优化。",
            benefits=["五险一金", "年终奖", "弹性工作"],
        ),
        Job(
            title="Java 后端开发",
            company="腾讯",
            salary="28k-48k",
            location="深圳",
            required_skills=["Java", "Spring", "MySQL", "Redis", "Kafka"],
            preferred_skills=["微服务", "Docker", "Kubernetes"],
            min_work_years=3,
            education_requirement="本科",
            description="负责社交平台后端系统开发和性能优化。",
            benefits=["五险一金", "股票期权", "年终奖"],
        ),
        Job(
            title="数据分析师",
            company="美团",
            salary="20k-35k",
            location="北京",
            required_skills=["Python", "SQL", "pandas", "Excel"],
            preferred_skills=["Tableau", "Spark", "机器学习"],
            min_work_years=1,
            education_requirement="本科",
            description="负责业务数据分析、报表制作、数据驱动决策支持。",
            benefits=["五险一金", "餐补", "交通补贴"],
        ),
        Job(
            title="AI 算法工程师",
            company="百度",
            salary="35k-60k",
            location="北京",
            required_skills=["Python", "PyTorch", "TensorFlow", "深度学习", "NLP"],
            preferred_skills=["Kubernetes", "Spark", "C++"],
            min_work_years=2,
            education_requirement="硕士",
            description="负责 NLP 相关算法研发，包括大模型训练和推理优化。",
            benefits=["五险一金", "股票期权", "弹性工作", "科研经费"],
        ),
        Job(
            title="DevOps 工程师",
            company="华为",
            salary="25k-40k",
            location="深圳",
            required_skills=["Linux", "Docker", "Kubernetes", "Jenkins", "CI/CD"],
            preferred_skills=["AWS", "Python", "Go"],
            min_work_years=2,
            education_requirement="本科",
            description="负责 CI/CD 流水线建设和云基础设施管理。",
            benefits=["五险一金", "年终奖", "加班费"],
        ),
        Job(
            title="全栈开发工程师",
            company="小米",
            salary="22k-38k",
            location="北京",
            required_skills=["JavaScript", "Python", "React", "Node.js", "MySQL"],
            preferred_skills=["TypeScript", "Docker", "Redis"],
            min_work_years=2,
            education_requirement="本科",
            description="负责 IoT 平台全栈开发，包括前端界面和后端服务。",
            benefits=["五险一金", "员工折扣", "弹性工作"],
        ),
        Job(
            title="机器学习工程师",
            company="蚂蚁集团",
            salary="35k-55k",
            location="杭州",
            required_skills=["Python", "TensorFlow", "机器学习", "Spark", "SQL"],
            preferred_skills=["深度学习", "Kubernetes", "微服务"],
            min_work_years=3,
            education_requirement="硕士",
            description="负责风控模型和推荐算法的研发与优化。",
            benefits=["五险一金", "股票期权", "免费三餐"],
        ),
    ]
    save_jobs(sample_jobs)
    return sample_jobs
