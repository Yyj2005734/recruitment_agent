"""智能匹配引擎 — 多维度加权匹配"""
from .models import Resume, Job, MatchResult
from . import job_manager


# 权重配置
WEIGHTS = {
    "skill": 0.40,       # 技能匹配权重最大
    "experience": 0.20,  # 工作经验
    "education": 0.15,   # 学历
    "location": 0.15,    # 地点
    "salary": 0.10,      # 薪资期望
}

EDUCATION_ORDER = {"": 0, "高中": 1, "大专": 2, "本科": 3, "硕士": 4, "博士": 5}


def _normalize(s: str) -> str:
    return s.lower().replace(".js", "").replace("js", "").strip()


def match_skills(resume_skills: list[str], required: list[str], preferred: list[str]) -> tuple[float, str]:
    """技能匹配打分

    必备技能命中率占 70%，加分技能占 30%。
    返回 (分数 0-100, 描述文字)
    """
    if not required and not preferred:
        return 80.0, "岗位未明确技能要求"

    resume_set = {_normalize(s) for s in resume_skills}
    required_set = {_normalize(s) for s in required}
    preferred_set = {_normalize(s) for s in preferred}

    # 必备技能匹配
    if required_set:
        matched_req = resume_set & required_set
        req_score = len(matched_req) / len(required_set) * 100
        missing_req = required_set - matched_req
    else:
        matched_req = set()
        req_score = 80.0
        missing_req = set()

    # 加分技能匹配
    if preferred_set:
        matched_pref = resume_set & preferred_set
        pref_score = len(matched_pref) / len(preferred_set) * 100
    else:
        matched_pref = set()
        pref_score = 50.0

    total = req_score * 0.7 + pref_score * 0.3

    # 构建描述
    parts = []
    if matched_req:
        parts.append(f"必备技能匹配: {', '.join(matched_req)}")
    if missing_req:
        parts.append(f"缺少必备: {', '.join(missing_req)}")
    if matched_pref:
        parts.append(f"加分技能: {', '.join(matched_pref)}")

    return min(total, 100.0), "; ".join(parts) if parts else "技能匹配度一般"


def match_experience(work_years: float, min_years: float) -> tuple[float, str]:
    """工作经验匹配"""
    if min_years <= 0:
        return 80.0, "无经验要求"
    if work_years >= min_years * 1.5:
        return 100.0, f"经验 {work_years} 年，远超要求 {min_years} 年"
    elif work_years >= min_years:
        ratio = work_years / min_years
        score = 70 + (ratio - 1) * 100  # 1.0x→70, 1.5x→100
        return min(score, 100.0), f"经验 {work_years} 年，满足要求 {min_years} 年"
    elif work_years >= min_years * 0.7:
        score = work_years / min_years * 70
        return score, f"经验 {work_years} 年，略低于要求 {min_years} 年"
    else:
        score = max(work_years / min_years * 50, 10)
        return score, f"经验 {work_years} 年，低于要求 {min_years} 年"


def match_education(resume_edu: str, job_edu: str) -> tuple[float, str]:
    """学历匹配"""
    resume_level = EDUCATION_ORDER.get(resume_edu, 0)
    job_level = EDUCATION_ORDER.get(job_edu, 0)

    if job_level == 0:
        return 80.0, "无学历要求"

    if resume_level >= job_level + 1:
        return 100.0, f"学历 {resume_edu}，超出要求 {job_edu}"
    elif resume_level >= job_level:
        return 90.0, f"学历 {resume_edu}，满足要求 {job_edu}"
    elif resume_level == job_level - 1:
        return 60.0, f"学历 {resume_edu}，略低于要求 {job_edu}"
    else:
        return 30.0, f"学历 {resume_edu}，低于要求 {job_edu}"


def match_location(resume_loc: str, job_loc: str) -> tuple[float, str]:
    """地点匹配"""
    if not resume_loc or not job_loc:
        return 70.0, "地点信息不完整"
    if resume_loc == job_loc:
        return 100.0, f"期望地点 {resume_loc} 与岗位一致"
    # 同区域加分
    nearby = {
        "北京": ["天津", "河北"],
        "上海": ["苏州", "杭州", "南京"],
        "深圳": ["广州", "东莞", "佛山", "珠海"],
        "广州": ["深圳", "佛山", "东莞"],
        "杭州": ["上海", "宁波", "南京"],
        "成都": ["重庆"],
    }
    for hub, regions in nearby.items():
        if (resume_loc == hub and job_loc in regions) or (job_loc == hub and resume_loc in regions):
            return 75.0, f"期望 {resume_loc}，岗位在 {job_loc}（同区域）"
    return 40.0, f"期望 {resume_loc}，岗位在 {job_loc}（异地）"


def parse_salary_range(salary_str: str) -> tuple[float, float]:
    """解析薪资范围字符串，统一转为 k 为单位"""
    if not salary_str:
        return 0.0, 0.0
    import re
    s = salary_str.lower().replace(" ", "")

    # 处理 "30k-50k" 格式
    m = re.search(r"(\d+)\s*k\s*[-~至到]\s*(\d+)\s*k", s)
    if m:
        return float(m.group(1)), float(m.group(2))

    # 处理 "3万-5万" 格式
    m = re.search(r"([\d.]+)\s*[万w]\s*[-~至到]\s*([\d.]+)\s*[万w]", s)
    if m:
        return float(m.group(1)) * 10, float(m.group(2)) * 10

    # 处理单个数字
    m = re.search(r"(\d+)\s*k", s)
    if m:
        v = float(m.group(1))
        return v, v

    return 0.0, 0.0


def match_salary(resume_salary: str, job_salary: str) -> tuple[float, str]:
    """薪资匹配"""
    r_min, r_max = parse_salary_range(resume_salary)
    j_min, j_max = parse_salary_range(job_salary)

    if r_min == 0 and r_max == 0:
        return 70.0, "未填写期望薪资"
    if j_min == 0 and j_max == 0:
        return 70.0, "岗位未标注薪资"

    r_mid = (r_min + r_max) / 2 if r_max > r_min else r_min
    j_mid = (j_min + j_max) / 2 if j_max > j_min else j_min

    if j_mid == 0:
        return 70.0, "岗位薪资信息不完整"

    ratio = r_mid / j_mid
    if 0.8 <= ratio <= 1.2:
        return 100.0, f"期望 {resume_salary} 与岗位 {job_salary} 匹配"
    elif 0.6 <= ratio < 0.8:
        return 80.0, f"期望 {resume_salary} 略低于岗位 {job_salary}"
    elif 1.2 < ratio <= 1.5:
        return 70.0, f"期望 {resume_salary} 略高于岗位 {job_salary}"
    elif ratio < 0.6:
        return 60.0, f"期望 {resume_salary} 远低于岗位 {job_salary}（可能低估自己）"
    else:
        return 40.0, f"期望 {resume_salary} 远高于岗位 {job_salary}"


def calculate_match(resume: Resume, job: Job) -> MatchResult:
    """计算简历与岗位的匹配度"""
    skill_score, skill_detail = match_skills(resume.skills, job.required_skills, job.preferred_skills)
    exp_score, exp_detail = match_experience(resume.work_years, job.min_work_years)
    edu_score, edu_detail = match_education(resume.education, job.education_requirement)
    loc_score, loc_detail = match_location(resume.expected_location, job.location)
    sal_score, sal_detail = match_salary(resume.expected_salary, job.salary)

    total = (
        skill_score * WEIGHTS["skill"] +
        exp_score * WEIGHTS["experience"] +
        edu_score * WEIGHTS["education"] +
        loc_score * WEIGHTS["location"] +
        sal_score * WEIGHTS["salary"]
    )

    details = (
        f"技能({skill_score:.0f}分): {skill_detail}\n"
        f"经验({exp_score:.0f}分): {exp_detail}\n"
        f"学历({edu_score:.0f}分): {edu_detail}\n"
        f"地点({loc_score:.0f}分): {loc_detail}\n"
        f"薪资({sal_score:.0f}分): {sal_detail}"
    )

    return MatchResult(
        job=job,
        total_score=round(total, 1),
        skill_score=round(skill_score, 1),
        experience_score=round(exp_score, 1),
        education_score=round(edu_score, 1),
        location_score=round(loc_score, 1),
        salary_score=round(sal_score, 1),
        details=details,
    )


def recommend_jobs(resume: Resume, top_n: int = 5) -> list[MatchResult]:
    """为求职者推荐最匹配的岗位"""
    jobs = job_manager.load_jobs()
    results = [calculate_match(resume, job) for job in jobs]
    results.sort(key=lambda r: r.total_score, reverse=True)
    return results[:top_n]


def recommend_candidates(job: Job, resumes: list[Resume], top_n: int = 5) -> list[tuple[Resume, MatchResult]]:
    """为岗位推荐最匹配的候选人"""
    results = [(resume, calculate_match(resume, job)) for resume in resumes]
    results.sort(key=lambda x: x[1].total_score, reverse=True)
    return results[:top_n]
