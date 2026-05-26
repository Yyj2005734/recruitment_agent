"""Boss直聘 实时岗位连接器 — 从 Boss直聘 搜索并抓取真实岗位数据"""
import re
import json
import time
import random
import hashlib
from typing import Optional

from .models import Job


# Boss直聘城市代码映射
CITY_CODES = {
    "全国": "100010000",
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280100",
    "深圳": "101280600",
    "杭州": "101210100",
    "成都": "101270100",
    "南京": "101190100",
    "武汉": "101200100",
    "西安": "101110100",
    "重庆": "101040100",
    "苏州": "101190400",
    "天津": "101030100",
    "长沙": "101250100",
    "郑州": "101180100",
    "青岛": "101120200",
    "大连": "101070200",
    "厦门": "101230200",
    "合肥": "101220100",
    "福州": "101230100",
}

# Boss直聘经验代码
EXPERIENCE_CODES = {
    "不限": "0",
    "在校生": "108",
    "应届生": "102",
    "1年以内": "103",
    "1-3年": "104",
    "3-5年": "105",
    "5-10年": "106",
    "10年以上": "107",
}

# Boss直聘学历代码
EDUCATION_CODES = {
    "不限": "0",
    "初中及以下": "101",
    "中专/中技": "102",
    "高中": "103",
    "大专": "104",
    "本科": "105",
    "硕士": "106",
    "博士": "107",
}

# 请求头（模拟浏览器）
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "application/json,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.zhipin.com/",
}


class BossConnector:
    """Boss直聘 连接器"""

    BASE_URL = "https://www.zhipin.com"
    API_URL = "https://www.zhipin.com/wapi/zpgeek"

    def __init__(self):
        self.session = None
        self._last_request_time = 0

    def _get_session(self):
        """获取/创建 requests session"""
        if self.session is None:
            import requests
            self.session = requests.Session()
            self.session.headers.update(HEADERS)
        return self.session

    def _rate_limit(self):
        """请求限速，避免触发反爬"""
        elapsed = time.time() - self._last_request_time
        delay = random.uniform(1.5, 3.5)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request_time = time.time()

    def search(
        self,
        query: str,
        city: str = "",
        page: int = 1,
        experience: str = "",
        education: str = "",
    ) -> list[Job]:
        """搜索 Boss直聘 岗位

        Args:
            query: 搜索关键词（如 "Python"、"前端开发"）
            city: 城市名称（如 "北京"、"上海"），空=全国
            page: 页码，从 1 开始
            experience: 经验要求
            education: 学历要求

        Returns:
            Job 对象列表
        """
        city_code = CITY_CODES.get(city, "")
        if city and not city_code:
            print(f"[提示] 未知城市 '{city}'，将搜索全国岗位。")

        # 策略1：尝试 API 接口
        jobs = self._try_api_search(query, city_code, page, experience, education)
        if jobs:
            return jobs

        # 策略2：尝试 HTML 页面抓取
        jobs = self._try_html_search(query, city_code, page)
        if jobs:
            return jobs

        # 策略3：全部失败，返回空
        return []

    def _try_api_search(
        self, query: str, city_code: str, page: int,
        experience: str, education: str,
    ) -> list[Job]:
        """尝试通过 API 接口搜索"""
        try:
            session = self._get_session()
            self._rate_limit()

            # 先访问首页获取 cookie
            session.get(self.BASE_URL, timeout=10)

            self._rate_limit()

            # 构造 API 请求
            url = f"{self.API_URL}/search/joblist.json"
            params = {
                "query": query,
                "city": city_code or "100010000",
                "page": page,
                "pageSize": 30,
            }
            if experience and experience in EXPERIENCE_CODES:
                params["experience"] = EXPERIENCE_CODES[experience]
            if education and education in EDUCATION_CODES:
                params["degree"] = EDUCATION_CODES[education]

            resp = session.get(url, params=params, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    job_list = data.get("zpData", {}).get("jobList", [])
                    return [self._parse_api_job(item) for item in job_list]
        except Exception as e:
            print(f"[调试] API 搜索失败: {e}")
        return []

    def _try_html_search(
        self, query: str, city_code: str, page: int,
    ) -> list[Job]:
        """尝试通过 HTML 页面抓取"""
        try:
            session = self._get_session()
            self._rate_limit()

            # 构造搜索 URL
            url = f"{self.BASE_URL}/web/geek/job"
            params = {"query": query, "page": page}
            if city_code:
                params["city"] = city_code

            resp = session.get(url, params=params, timeout=15)

            if resp.status_code == 200:
                return self._parse_html_page(resp.text)
        except Exception as e:
            print(f"[调试] HTML 搜索失败: {e}")
        return []

    def _parse_api_job(self, item: dict) -> Job:
        """解析 API 返回的岗位数据"""
        # 提取技能标签
        skills = []
        if item.get("skills"):
            skills = item["skills"] if isinstance(item["skills"], list) else []
        elif item.get("skillLabels"):
            skills = item["skillLabels"]

        # 提取福利
        benefits = item.get("welfareList", []) or item.get("benefits", [])
        if isinstance(benefits, str):
            benefits = [b.strip() for b in benefits.split(",") if b.strip()]

        # 经验要求解析
        exp_str = item.get("jobExperience", item.get("experienceName", ""))
        min_years = self._parse_experience_years(exp_str)

        return Job(
            title=item.get("jobName", item.get("title", "")),
            company=item.get("brandName", item.get("company", "")),
            salary=item.get("salaryDesc", item.get("salary", "")),
            location=item.get("cityName", item.get("areaDistrict", "")),
            required_skills=skills[:6],
            min_work_years=min_years,
            education_requirement=item.get("degreeName", item.get("education", "")),
            description=item.get("jobLabels", ""),
            benefits=benefits[:5] if benefits else [],
        )

    def _parse_html_page(self, html: str) -> list[Job]:
        """解析 HTML 搜索结果页面"""
        jobs = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            # 策略1：从嵌入的 JSON 数据提取
            json_jobs = self._extract_json_from_html(html)
            if json_jobs:
                return json_jobs

            # 策略2：通过 CSS 选择器解析
            cards = soup.select(".job-card-wrapper, .job-list li, .search-job-result .job-card-body")
            for card in cards:
                job = self._parse_html_card(card)
                if job and job.title:
                    jobs.append(job)

        except ImportError:
            print("[提示] 需要安装 beautifulsoup4: pip install beautifulsoup4 lxml")
        except Exception as e:
            print(f"[调试] HTML 解析异常: {e}")

        return jobs

    def _extract_json_from_html(self, html: str) -> list[Job]:
        """从 HTML 中提取嵌入的 JSON 数据（React/Vue SSR 数据）"""
        jobs = []

        # 模式1: __INITIAL_STATE__ 或 window.__INITIAL_DATA__
        patterns = [
            r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});?\s*</script>",
            r"window\.__INITIAL_DATA__\s*=\s*(\{.*?\});?\s*</script>",
            r"__NEXT_DATA__.*?\"jobList\"\s*:\s*(\[.*?\])\s*,",
            r'"jobList"\s*:\s*(\[.*?\])\s*[,}]',
        ]

        for pat in patterns:
            m = re.search(pat, html, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                jobs.append(self._parse_api_job(item))
                    elif isinstance(data, dict):
                        # 递归查找 jobList
                        job_list = self._find_job_list(data)
                        for item in job_list:
                            jobs.append(self._parse_api_job(item))
                    if jobs:
                        return jobs
                except json.JSONDecodeError:
                    continue

        return jobs

    def _find_job_list(self, data: dict) -> list:
        """递归查找字典中的 jobList"""
        if isinstance(data, dict):
            if "jobList" in data and isinstance(data["jobList"], list):
                return data["jobList"]
            for v in data.values():
                result = self._find_job_list(v)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_job_list(item)
                if result:
                    return result
        return []

    def _parse_html_card(self, card) -> Optional[Job]:
        """解析单个 HTML 岗位卡片"""
        try:
            from bs4 import BeautifulSoup

            # 标题
            title_el = card.select_one(
                ".job-name, .job-title, [class*='job-name'], [class*='title']"
            )
            title = title_el.get_text(strip=True) if title_el else ""

            # 薪资
            salary_el = card.select_one(
                ".salary, [class*='salary'], [class*='red']"
            )
            salary = salary_el.get_text(strip=True) if salary_el else ""

            # 公司
            company_el = card.select_one(
                ".company-name, [class*='company-name'], [class*='brand']"
            )
            company = company_el.get_text(strip=True) if company_el else ""

            # 地区
            area_el = card.select_one(
                ".job-area, [class*='area'], [class*='city']"
            )
            location = area_el.get_text(strip=True) if area_el else ""

            # 经验/学历要求
            tags = card.select(
                ".tag-list li, .job-info span, [class*='tag'], [class*='info'] span"
            )
            tag_texts = [t.get_text(strip=True) for t in tags]

            exp_text = ""
            edu_text = ""
            for t in tag_texts:
                if "年" in t or "经验" in t:
                    exp_text = t
                elif any(k in t for k in ("本科", "硕士", "博士", "大专", "学历")):
                    edu_text = t

            # 技能标签
            skill_els = card.select(
                ".tag-list li, [class*='skill'], [class*='tag'] li"
            )
            skills = [s.get_text(strip=True) for s in skill_els[:6] if s.get_text(strip=True)]

            if not title:
                return None

            return Job(
                title=title,
                salary=salary,
                company=company,
                location=location,
                required_skills=[s for s in skills if s not in (exp_text, edu_text)],
                min_work_years=self._parse_experience_years(exp_text),
                education_requirement=edu_text,
            )
        except Exception:
            return None

    def _parse_experience_years(self, text: str) -> float:
        """解析经验要求文本为最低年限"""
        if not text:
            return 0.0
        m = re.search(r"(\d+)", text)
        if m:
            return float(m.group(1))
        if "应届" in text or "在校" in text:
            return 0.0
        return 0.0

    def search_by_resume(
        self,
        resume,
        city: str = "",
        page: int = 1,
    ) -> list[Job]:
        """根据简历自动搜索匹配岗位

        从简历中提取最相关的关键词作为搜索词
        """
        # 构建搜索关键词：优先用简历中的技能
        query = self._build_search_query(resume)
        # 使用期望城市，未填则使用参数
        search_city = city or getattr(resume, "expected_location", "") or ""

        print(f"[Boss直聘] 搜索关键词: {query}  城市: {search_city or '全国'}")
        return self.search(query=query, city=search_city, page=page)

    def _build_search_query(self, resume) -> str:
        """从简历构建搜索关键词"""
        skills = getattr(resume, "skills", [])
        if skills:
            # 取前3个最核心技能
            return " ".join(skills[:3])
        return "开发"

    def close(self):
        """关闭连接"""
        if self.session:
            self.session.close()
            self.session = None
