"""OCR 简历解析器 — 支持 JPG/PNG 图片简历"""
import os
import re
from pathlib import Path

from .models import Resume
from . import resume_parser


_ocr_engine = None


def get_ocr_engine():
    """懒加载 PaddleOCR 引擎（首次初始化较慢）"""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            print("[OCR] 正在初始化 PaddleOCR 引擎（首次可能较慢）...")
            _ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang="ch",
                show_log=False,
            )
            print("[OCR] PaddleOCR 引擎就绪。")
        except ImportError:
            raise ImportError(
                "图片 OCR 需要安装依赖: pip install paddleocr paddlepaddle"
            )
    return _ocr_engine


def extract_text_from_image(filepath: str) -> str:
    """从图片文件提取文字（OCR）"""
    filepath = str(filepath)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    ext = Path(filepath).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"):
        raise ValueError(f"不支持的图片格式: {ext}")

    # 预处理图片提升 OCR 准确率
    processed_path = _preprocess_image(filepath)

    ocr = get_ocr_engine()
    result = ocr.ocr(processed_path, cls=True)

    # 清理预处理临时文件
    if processed_path != filepath:
        try:
            os.remove(processed_path)
        except OSError:
            pass

    if not result or not result[0]:
        return ""

    # 拼接识别结果，按 y 坐标排序（从上到下）
    lines = []
    for line in result[0]:
        text = line[1][0]  # (box, (text, confidence))
        lines.append(text)

    return "\n".join(lines)


def _preprocess_image(filepath: str) -> str:
    """图片预处理：灰度化 + 二值化 + 去噪，提升 OCR 准确率"""
    try:
        from PIL import Image, ImageFilter, ImageEnhance

        img = Image.open(filepath)

        # 转灰度
        img = img.convert("L")

        # 增强对比度
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)

        # 锐化
        img = img.filter(ImageFilter.SHARPEN)

        # 二值化（Otsu 简化版）
        threshold = 128
        img = img.point(lambda p: 255 if p > threshold else 0, "1")

        # 保存预处理后的临时文件
        temp_path = str(Path(filepath).with_suffix(".processed.png"))
        img.save(temp_path)
        return temp_path
    except Exception:
        # 预处理失败则直接用原图
        return filepath


def parse_image_resume(filepath: str) -> Resume:
    """解析图片简历，返回 Resume 对象"""
    text = extract_text_from_image(filepath)

    if not text.strip():
        raise RuntimeError("OCR 未识别到任何文字，请检查图片是否清晰。")

    # 复用文本解析器的提取逻辑
    return Resume(
        name=resume_parser.extract_name(text),
        phone=resume_parser.extract_phone(text),
        email=resume_parser.extract_email(text),
        skills=resume_parser.extract_skills(text),
        work_years=resume_parser.extract_work_years(text),
        education=resume_parser.extract_education(text),
        expected_salary=resume_parser.extract_salary(text),
        expected_location=resume_parser.extract_location(text),
        work_experience=resume_parser.extract_experience_entries(text),
        raw_text=text[:2000],
        source_file=os.path.basename(filepath),
    )
