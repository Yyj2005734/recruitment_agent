"""数据模型定义"""
from dataclasses import dataclass, field, asdict
from typing import Optional
import json
import uuid
from datetime import datetime


@dataclass
class Resume:
    """求职者简历"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    phone: str = ""
    email: str = ""
    skills: list[str] = field(default_factory=list)
    work_years: float = 0.0
    education: str = ""  # 高中/大专/本科/硕士/博士
    expected_salary: str = ""  # 例如 "15k-25k"
    expected_location: str = ""
    work_experience: list[str] = field(default_factory=list)
    raw_text: str = ""
    source_file: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Resume":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Job:
    """岗位信息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    company: str = ""
    salary: str = ""
    location: str = ""
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    min_work_years: float = 0.0
    education_requirement: str = ""
    description: str = ""
    benefits: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MatchResult:
    """匹配结果"""
    job: Job
    total_score: float = 0.0
    skill_score: float = 0.0
    experience_score: float = 0.0
    education_score: float = 0.0
    location_score: float = 0.0
    salary_score: float = 0.0
    details: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["job"] = self.job.to_dict()
        return d
