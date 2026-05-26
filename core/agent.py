"""对话 Agent — 自然语言招聘咨询"""
import re
from .models import Resume
from . import job_manager, matcher, resume_parser
from .boss_connector import BossConnector


# 意图关键词映射
INTENT_KEYWORDS = {
    "boss_search": ["boss", "直聘", "实时搜索", "线上岗位", "搜一下", "搜岗位"],
    "search_job": ["找工作", "有什么岗位", "推荐岗位", "哪些职位", "招聘", "岗位推荐", "职位推荐", "适合什么工作"],
    "match_score": ["匹配度", "匹配分数", "多少分", "能匹配", "合不合适", "行不行", "胜算"],
    "job_detail": ["岗位详情", "职位详情", "具体要求", "什么条件", "介绍一下"],
    "career_advice": ["建议", "怎么提升", "怎么准备", "面试", "简历怎么写", "求职建议", "规划"],
    "salary_info": ["薪资", "工资", "待遇", "多少钱", "薪酬"],
    "skill_advice": ["学什么", "需要学", "补什么技能", "缺什么"],
    "help": ["帮助", "怎么用", "功能", "help", "能做什么"],
    "list_jobs": ["所有岗位", "全部岗位", "岗位列表", "有哪些岗位"],
}


class RecruitmentAgent:
    """招聘智能对话 Agent"""

    def __init__(self):
        self.current_resume: Resume | None = None
        self.history: list[dict] = []

    def set_resume(self, resume: Resume):
        """设置当前求职者简历"""
        self.current_resume = resume

    def detect_intent(self, text: str) -> str:
        """识别用户意图"""
        text_lower = text.lower()
        for intent, keywords in INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return intent
        return "unknown"

    def extract_job_keyword(self, text: str) -> str:
        """从文本中提取岗位关键词"""
        # 常见岗位名称
        titles = [
            "python", "java", "前端", "后端", "全栈", "算法",
            "数据", "测试", "运维", "devops", "产品经理",
            "设计", "运营", "架构师",
        ]
        text_lower = text.lower()
        for title in titles:
            if title in text_lower:
                return title
        return ""

    def respond(self, user_input: str) -> str:
        """处理用户输入，返回回复"""
        self.history.append({"role": "user", "content": user_input})
        intent = self.detect_intent(user_input)
        reply = self._handle_intent(intent, user_input)
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def _handle_intent(self, intent: str, text: str) -> str:
        if intent == "boss_search":
            return self._reply_boss_search(text)
        elif intent == "help":
            return self._reply_help()
        elif intent == "list_jobs":
            return self._reply_list_jobs()
        elif intent == "search_job":
            return self._reply_search_job(text)
        elif intent == "match_score":
            return self._reply_match_score(text)
        elif intent == "job_detail":
            return self._reply_job_detail(text)
        elif intent == "career_advice":
            return self._reply_career_advice()
        elif intent == "salary_info":
            return self._reply_salary_info(text)
        elif intent == "skill_advice":
            return self._reply_skill_advice()
        else:
            return self._reply_unknown(text)

    def _reply_help(self) -> str:
        return (
            "我是招聘智能助手，可以帮你：\n"
            "  1. Boss直聘搜索 — 「搜岗位」「Boss搜索 Python」\n"
            "  2. 搜索岗位 — 「有什么岗位」「推荐前端岗位」\n"
            "  3. 匹配打分 — 「我和这个岗位匹配度多少」\n"
            "  4. 岗位详情 — 「Python 开发的岗位详情」\n"
            "  5. 薪资查询 — 「北京有哪些高薪岗位」\n"
            "  6. 求职建议 — 「给我一些求职建议」\n"
            "  7. 技能建议 — 「我应该补什么技能」\n"
            "\n提示：先上传或输入简历，我能给出更精准的推荐。"
        )

    def _reply_boss_search(self, text: str) -> str:
        """Boss直聘实时搜索"""
        keyword = self.extract_job_keyword(text)
        if not keyword and self.current_resume and self.current_resume.skills:
            keyword = " ".join(self.current_resume.skills[:3])
        if not keyword:
            keyword = "开发"

        city = ""
        cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "南京", "武汉"]
        for c in cities:
            if c in text:
                city = c
                break
        if not city and self.current_resume:
            city = self.current_resume.expected_location or ""

        connector = BossConnector()
        try:
            jobs = connector.search(query=keyword, city=city, page=1)
            if not jobs:
                return f"Boss直聘暂未搜索到 '{keyword}' 相关岗位，可能是网络问题或触发了反爬。请稍后重试或使用本地岗位库。"

            # 保存到本地库
            existing = job_manager.load_jobs()
            existing_ids = {j.id for j in existing}
            new_jobs = [j for j in jobs if j.id not in existing_ids]
            if new_jobs:
                existing.extend(new_jobs)
                job_manager.save_jobs(existing)

            if self.current_resume:
                results = [matcher.calculate_match(self.current_resume, j) for j in jobs]
                results.sort(key=lambda r: r.total_score, reverse=True)
                lines = [f"从 Boss直聘 搜索到 {len(jobs)} 个岗位，为你推荐："]
                for i, r in enumerate(results[:5], 1):
                    lines.append(
                        f"  {i}. {r.job.title} — {r.job.company}\n"
                        f"     匹配度: {r.total_score:.0f}分 | {r.job.salary} | {r.job.location}"
                    )
                return "\n".join(lines)
            else:
                lines = [f"从 Boss直聘 搜索到 {len(jobs)} 个岗位："]
                for i, j in enumerate(jobs[:5], 1):
                    lines.append(f"  {i}. {j.title} — {j.company} | {j.salary} | {j.location}")
                lines.append("\n提示：上传简历后可查看匹配度排名。")
                return "\n".join(lines)
        except Exception as e:
            return f"Boss直聘搜索失败: {e}"
        finally:
            connector.close()

    def _reply_list_jobs(self) -> str:
        jobs = job_manager.load_jobs()
        if not jobs:
            return "当前岗位库为空，请先导入岗位数据。"
        lines = [f"共 {len(jobs)} 个岗位："]
        for j in jobs:
            lines.append(f"  [{j.id}] {j.title} — {j.company} | {j.salary} | {j.location}")
        return "\n".join(lines)

    def _reply_search_job(self, text: str) -> str:
        keyword = self.extract_job_keyword(text)
        # 提取地点
        location = ""
        cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "南京", "武汉"]
        for city in cities:
            if city in text:
                location = city
                break

        jobs = job_manager.search_jobs(keyword=keyword, location=location)
        if not jobs:
            return f"没有找到相关岗位{'（关键词: ' + keyword + '）' if keyword else ''}{'（地点: ' + location + '）' if location else ''}。"

        if self.current_resume:
            results = matcher.recommend_jobs(self.current_resume, top_n=len(jobs))
            # 过滤搜索结果
            job_ids = {j.id for j in jobs}
            results = [r for r in results if r.job.id in job_ids]
            if not results:
                return "搜索结果中没有匹配的岗位。"
            lines = ["为你推荐以下岗位："]
            for i, r in enumerate(results[:5], 1):
                lines.append(
                    f"  {i}. {r.job.title} — {r.job.company}\n"
                    f"     匹配度: {r.total_score:.0f}分 | {r.job.salary} | {r.job.location}"
                )
            return "\n".join(lines)
        else:
            lines = [f"找到 {len(jobs)} 个相关岗位："]
            for j in jobs[:5]:
                lines.append(f"  - {j.title} — {j.company} | {j.salary} | {j.location}")
            lines.append("\n提示：上传简历后可查看匹配度排名。")
            return "\n".join(lines)

    def _reply_match_score(self, text: str) -> str:
        if not self.current_resume:
            return "请先上传或输入你的简历信息，我才能计算匹配度。"

        # 尝试找到具体岗位
        keyword = self.extract_job_keyword(text)
        jobs = job_manager.search_jobs(keyword=keyword) if keyword else job_manager.load_jobs()
        if not jobs:
            return "没有找到可匹配的岗位。"

        results = [matcher.calculate_match(self.current_resume, j) for j in jobs]
        results.sort(key=lambda r: r.total_score, reverse=True)

        lines = [f"简历（{self.current_resume.name or '未命名'}）与岗位匹配度："]
        for i, r in enumerate(results[:5], 1):
            level = "优秀" if r.total_score >= 80 else "良好" if r.total_score >= 60 else "一般"
            lines.append(
                f"  {i}. {r.job.title} — {r.job.company}: "
                f"{r.total_score:.0f}分 ({level})"
            )
        return "\n".join(lines)

    def _reply_job_detail(self, text: str) -> str:
        keyword = self.extract_job_keyword(text)
        jobs = job_manager.search_jobs(keyword=keyword) if keyword else job_manager.load_jobs()
        if not jobs:
            return "没有找到相关岗位。"
        job = jobs[0]
        lines = [
            f"【{job.title}】",
            f"公司: {job.company}",
            f"薪资: {job.salary}",
            f"地点: {job.location}",
            f"经验要求: {job.min_work_years}年以上",
            f"学历要求: {job.education_requirement}",
            f"必备技能: {', '.join(job.required_skills)}",
            f"加分技能: {', '.join(job.preferred_skills) if job.preferred_skills else '无'}",
            f"岗位描述: {job.description}",
            f"福利: {', '.join(job.benefits) if job.benefits else '无'}",
        ]
        if self.current_resume:
            result = matcher.calculate_match(self.current_resume, job)
            lines.append(f"\n你的匹配度: {result.total_score:.0f}分")
            lines.append(result.details)
        return "\n".join(lines)

    def _reply_career_advice(self) -> str:
        if not self.current_resume:
            return "请先上传简历，我才能给出针对性的建议。"

        resume = self.current_resume
        jobs = job_manager.load_jobs()
        results = [matcher.calculate_match(resume, j) for j in jobs]
        results.sort(key=lambda r: r.total_score, reverse=True)

        advices = [f"基于你的简历（{resume.name}），我的建议如下："]

        # 技能建议
        all_required = set()
        for j in jobs:
            all_required.update(s.lower() for s in j.required_skills)
        missing = all_required - {s.lower() for s in resume.skills}
        if missing:
            top_missing = list(missing)[:5]
            advices.append(f"  建议补充技能: {', '.join(top_missing)}")

        # 匹配情况
        if results:
            top = results[0]
            advices.append(f"  最匹配的岗位: {top.job.title}（{top.total_score:.0f}分）")
            if top.skill_score < 60:
                advices.append(f"  技能短板: {top.details.split('技能')[1].split(';')[0] if '技能' in top.details else '需提升核心技能'}")

        # 通用建议
        if resume.work_years < 2:
            advices.append("  经验较少，建议多参与开源项目积累经验。")
        if not resume.expected_salary:
            advices.append("  建议填写期望薪资，有助于精准匹配。")

        return "\n".join(advices)

    def _reply_salary_info(self, text: str) -> str:
        keyword = self.extract_job_keyword(text)
        location = ""
        cities = ["北京", "上海", "广州", "深圳", "杭州", "成都"]
        for city in cities:
            if city in text:
                location = city
                break

        jobs = job_manager.search_jobs(keyword=keyword, location=location)
        if not jobs:
            return "没有找到相关岗位的薪资信息。"

        lines = ["岗位薪资参考："]
        for j in jobs[:5]:
            lines.append(f"  {j.title} ({j.company}, {j.location}): {j.salary}")
        return "\n".join(lines)

    def _reply_skill_advice(self) -> str:
        if not self.current_resume:
            return "请先上传简历，我才能分析你的技能缺口。"

        resume = self.current_resume
        results = matcher.recommend_jobs(resume, top_n=3)
        if not results:
            return "岗位库为空，无法分析。"

        # 汇总最匹配岗位的必备技能
        needed_skills = set()
        for r in results:
            for s in r.job.required_skills:
                needed_skills.add(s.lower())

        my_skills = {s.lower() for s in resume.skills}
        missing = needed_skills - my_skills

        lines = [
            f"根据你的简历和 Top3 匹配岗位分析：",
            f"  你已有的技能: {', '.join(resume.skills[:10])}",
            f"  建议补充: {', '.join(sorted(missing)) if missing else '无明显缺口'}",
        ]
        for r in results:
            if r.skill_score < 70:
                lines.append(f"  {r.job.title} 技能匹配 {r.skill_score:.0f}分，可加强: "
                             f"{', '.join(set(r.job.required_skills) - my_skills)}")
        return "\n".join(lines)

    def _reply_unknown(self, text: str) -> str:
        return (
            "不太理解你的意思。你可以试试：\n"
            "  - 「有什么岗位」查看岗位列表\n"
            "  - 「推荐前端岗位」搜索特定岗位\n"
            "  - 「匹配度多少」查看匹配分数\n"
            "  - 「求职建议」获取个性化建议\n"
            "  - 输入「帮助」查看全部功能"
        )
