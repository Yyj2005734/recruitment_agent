"""
招聘智能推荐 Agent v2.0 — 控制台交互主入口

用法:
    python main.py              # 启动交互模式
    python main.py --init       # 初始化示例数据后启动
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.models import Resume
from core import resume_parser, job_manager, matcher
from core.agent import RecruitmentAgent
from core.boss_connector import BossConnector


BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║          招聘智能推荐 Agent v2.0                          ║
║  ────────────────────────────────────────────────────── ║
║  简历解析(PDF/Word/TXT/JPG/PNG) · Boss直聘实时岗位       ║
║  智能匹配引擎 · 多维打分 · 对话式招聘咨询                 ║
╚══════════════════════════════════════════════════════════╝
"""

MENU = """
┌──────────────── 功能菜单 ────────────────┐
│  1. 解析简历 (PDF/Word/TXT/JPG/PNG)     │
│  2. 手动输入简历信息                     │
│  3. Boss直聘 实时搜索岗位                │
│  4. 查看本地岗位库                       │
│  5. 添加岗位到本地库                     │
│  6. 删除本地岗位                         │
│  7. 查看匹配推荐（简历 vs 岗位）         │
│  8. 智能对话咨询                         │
│  9. 导入示例岗位数据                     │
│  0. 退出                                 │
└─────────────────────────────────────────┘
"""


def print_divider(char="─", width=55):
    print(char * width)


def print_resume_info(resume: Resume):
    """打印简历解析结果"""
    print_divider()
    print(f"  姓名: {resume.name or '未识别'}")
    print(f"  手机: {resume.phone or '未识别'}")
    print(f"  邮箱: {resume.email or '未识别'}")
    print(f"  技能: {', '.join(resume.skills[:10]) if resume.skills else '未识别'}")
    print(f"  工作年限: {resume.work_years} 年")
    print(f"  学历: {resume.education or '未识别'}")
    print(f"  期望薪资: {resume.expected_salary or '未填写'}")
    print(f"  期望地点: {resume.expected_location or '未填写'}")
    print_divider()


def input_resume_file(agent: RecruitmentAgent):
    """解析简历文件（支持 PDF/Word/TXT/JPG/PNG）"""
    filepath = input("请输入简历文件路径 (支持 PDF/Word/TXT/JPG/PNG): ").strip().strip('"').strip("'")
    if not filepath:
        print("[提示] 未输入路径，已取消。")
        return
    if not os.path.exists(filepath):
        print(f"[错误] 文件不存在: {filepath}")
        return
    try:
        print("[解析中] 正在识别简历内容...")
        resume = resume_parser.parse_resume(filepath)
        agent.set_resume(resume)
        print(f"\n简历解析成功！(来源: {resume.source_file})")
        print_resume_info(resume)
    except Exception as e:
        print(f"[错误] 简历解析失败: {e}")


def input_resume_manual(agent: RecruitmentAgent):
    """手动输入简历信息"""
    print("请输入简历信息（按提示逐项填写，留空跳过）：")
    name = input("  姓名: ").strip()
    skills_input = input("  技能（逗号分隔，如: Python, Java, React）: ").strip()
    work_years = input("  工作年限: ").strip()
    education = input("  学历（高中/大专/本科/硕士/博士）: ").strip()
    expected_salary = input("  期望薪资（如: 25k-40k）: ").strip()
    expected_location = input("  期望工作地点: ").strip()

    skills = [s.strip() for s in skills_input.split(",") if s.strip()] if skills_input else []

    resume = Resume(
        name=name,
        skills=skills,
        work_years=float(work_years) if work_years else 0,
        education=education,
        expected_salary=expected_salary,
        expected_location=expected_location,
        source_file="manual_input",
    )
    agent.set_resume(resume)
    print(f"\n简历已保存: {resume.name or '未命名'}，技能: {', '.join(skills) if skills else '无'}")


def boss_search(agent: RecruitmentAgent):
    """Boss直聘 实时搜索岗位"""
    if not agent.current_resume:
        print("[提示] 请先上传简历（菜单1）或手动输入简历（菜单2）。")
        print("       没有简历也可以手动指定搜索关键词。")
        manual = input("是否手动输入搜索关键词？(y/n): ").strip().lower()
        if manual != "y":
            return
        query = input("  搜索关键词（如: Python开发）: ").strip()
        if not query:
            print("[提示] 关键词不能为空。")
            return
    else:
        # 根据简历自动推荐搜索关键词
        suggested = " ".join(agent.current_resume.skills[:3]) if agent.current_resume.skills else "开发"
        query = input(f"搜索关键词（回车使用推荐: {suggested}）: ").strip()
        if not query:
            query = suggested

    # 选择城市
    default_city = ""
    if agent.current_resume and agent.current_resume.expected_location:
        default_city = agent.current_resume.expected_location
    city = input(f"城市（回车{'使用: ' + default_city if default_city else '搜索全国'}）: ").strip()
    if not city:
        city = default_city

    page_input = input("页码 (默认1): ").strip()
    page = int(page_input) if page_input.isdigit() else 1

    print(f"\n[搜索中] 正在从 Boss直聘 获取岗位数据...")
    print(f"  关键词: {query}  城市: {city or '全国'}  页码: {page}")
    print()

    connector = BossConnector()
    try:
        jobs = connector.search(query=query, city=city, page=page)

        if not jobs:
            print("[提示] 未获取到岗位数据。可能原因：")
            print("  - Boss直聘 反爬机制触发（稍后重试）")
            print("  - 网络连接问题")
            print("  - 搜索关键词过于冷门")
            print("\n提示: 可以使用本地岗位库（菜单4）或导入示例数据（菜单9）。")
            return

        print(f"获取到 {len(jobs)} 个岗位：")
        print_divider("═")

        if agent.current_resume:
            # 有简历时：按匹配度排序展示
            results = [matcher.calculate_match(agent.current_resume, j) for j in jobs]
            results.sort(key=lambda r: r.total_score, reverse=True)

            for i, r in enumerate(results, 1):
                level = (
                    "优秀 ★★★" if r.total_score >= 80 else
                    "良好 ★★" if r.total_score >= 60 else
                    "一般 ★"
                )
                print(f"\n  #{i} {r.job.title} — {r.job.company}")
                print(f"      匹配度: {r.total_score:.0f}分 [{level}]")
                print(f"      薪资: {r.job.salary} | 地点: {r.job.location}")
                if r.job.required_skills:
                    print(f"      技能要求: {', '.join(r.job.required_skills[:5])}")
                if r.job.benefits:
                    print(f"      福利: {', '.join(r.job.benefits[:3])}")
        else:
            # 无简历时：直接展示
            for i, j in enumerate(jobs, 1):
                print(f"\n  #{i} {j.title} — {j.company}")
                print(f"      薪资: {j.salary} | 地点: {j.location}")
                if j.required_skills:
                    print(f"      技能要求: {', '.join(j.required_skills[:5])}")

        print_divider("═")
        print(f"共 {len(jobs)} 个岗位（来源: Boss直聘 实时数据）")

        # 保存到本地库的选项
        save = input("是否将这些岗位保存到本地库？(y/n): ").strip().lower()
        if save == "y":
            existing = job_manager.load_jobs()
            existing.extend(jobs)
            job_manager.save_jobs(existing)
            print(f"已保存 {len(jobs)} 个岗位到本地库。")

    except Exception as e:
        print(f"[错误] Boss直聘搜索失败: {e}")
    finally:
        connector.close()


def list_jobs():
    """查看本地岗位库"""
    jobs = job_manager.load_jobs()
    if not jobs:
        print("[提示] 本地岗位库为空。")
        print("  可通过 Boss直聘搜索（菜单3）或导入示例数据（菜单9）添加岗位。")
        return
    print(f"\n本地岗位库共 {len(jobs)} 个岗位：")
    print_divider()
    for j in jobs:
        print(f"  [{j.id}] {j.title}")
        print(f"      公司: {j.company} | 薪资: {j.salary} | 地点: {j.location}")
        print(f"      要求: {', '.join(j.required_skills[:5])} | {j.min_work_years}年+ | {j.education_requirement}")
        print()


def add_job():
    """手动添加岗位到本地库"""
    print("请输入岗位信息：")
    title = input("  岗位名称: ").strip()
    if not title:
        print("[提示] 岗位名称不能为空。")
        return
    company = input("  公司名称: ").strip()
    salary = input("  薪资范围（如: 25k-40k）: ").strip()
    location = input("  工作地点: ").strip()
    skills_input = input("  必备技能（逗号分隔）: ").strip()
    pref_input = input("  加分技能（逗号分隔，可跳过）: ").strip()
    min_years = input("  最低工作年限: ").strip()
    edu = input("  学历要求（高中/大专/本科/硕士/博士）: ").strip()
    desc = input("  岗位描述: ").strip()

    from core.models import Job
    job = Job(
        title=title,
        company=company,
        salary=salary,
        location=location,
        required_skills=[s.strip() for s in skills_input.split(",") if s.strip()],
        preferred_skills=[s.strip() for s in pref_input.split(",") if s.strip()],
        min_work_years=float(min_years) if min_years else 0,
        education_requirement=edu,
        description=desc,
    )
    job_manager.add_job(job)
    print(f"\n岗位已添加: {title} [{job.id}]")


def delete_job():
    """删除本地岗位"""
    job_id = input("请输入要删除的岗位 ID: ").strip()
    if job_manager.delete_job(job_id):
        print(f"岗位 [{job_id}] 已删除。")
    else:
        print(f"[提示] 未找到 ID 为 {job_id} 的岗位。")


def show_matches(agent: RecruitmentAgent):
    """查看匹配推荐"""
    if not agent.current_resume:
        print("[提示] 请先上传简历（菜单1）或手动输入简历（菜单2）。")
        return

    jobs = job_manager.load_jobs()
    if not jobs:
        print("[提示] 本地岗位库为空。请先通过菜单3（Boss直聘搜索）或菜单9（导入示例）添加岗位。")
        return

    results = [matcher.calculate_match(agent.current_resume, j) for j in jobs]
    results.sort(key=lambda r: r.total_score, reverse=True)
    results = results[:10]

    print(f"\n为 {agent.current_resume.name or '你'} 推荐的岗位（按匹配度排序）：")
    print_divider("═")
    for i, r in enumerate(results, 1):
        level = (
            "优秀 ★★★" if r.total_score >= 80 else
            "良好 ★★" if r.total_score >= 60 else
            "一般 ★"
        )
        print(f"\n  #{i} {r.job.title} — {r.job.company}")
        print(f"      综合匹配度: {r.total_score:.0f}分 [{level}]")
        print(f"      薪资: {r.job.salary} | 地点: {r.job.location}")
        print(f"      技能:{r.skill_score:.0f} 经验:{r.experience_score:.0f} "
              f"学历:{r.education_score:.0f} 地点:{r.location_score:.0f} 薪资:{r.salary_score:.0f}")

        # 展示详情的交互
        if i <= 3:
            detail = input(f"      查看详情？(y/n): ").strip().lower() if sys.stdin.isatty() else "n"
            if detail == "y":
                print(f"\n      匹配详情:")
                for line in r.details.split("\n"):
                    print(f"        {line}")

    print_divider("═")


def chat_mode(agent: RecruitmentAgent):
    """智能对话模式"""
    print("\n进入智能对话模式（输入 q 或 退出 返回菜单）")
    print("提示: 可以问「有什么岗位」「匹配度多少」「求职建议」「Boss搜索 Python」等")
    print_divider()
    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ("q", "quit", "exit", "退出", "返回", "菜单"):
            print("返回主菜单。")
            break
        reply = agent.respond(user_input)
        print(f"\n助手: {reply}")


def main():
    print(BANNER)
    agent = RecruitmentAgent()

    # 检查是否需要初始化示例数据
    if "--init" in sys.argv:
        if not job_manager.load_jobs():
            jobs = job_manager.import_sample_jobs()
            print(f"[初始化] 已导入 {len(jobs)} 条示例岗位数据。\n")

    while True:
        try:
            print(MENU)
            choice = input("请选择功能 (0-9): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if choice == "1":
            input_resume_file(agent)
        elif choice == "2":
            input_resume_manual(agent)
        elif choice == "3":
            boss_search(agent)
        elif choice == "4":
            list_jobs()
        elif choice == "5":
            add_job()
        elif choice == "6":
            delete_job()
        elif choice == "7":
            show_matches(agent)
        elif choice == "8":
            chat_mode(agent)
        elif choice == "9":
            jobs = job_manager.import_sample_jobs()
            print(f"已导入 {len(jobs)} 条示例岗位数据。")
            list_jobs()
        elif choice == "0":
            print("感谢使用，再见！")
            break
        else:
            print("[提示] 无效选项，请输入 0-9。")


if __name__ == "__main__":
    main()
