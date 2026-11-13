"""Build clean, professional NCHU thesis Word document (.docx and .doc) from thesis/main.tex."""
import os
import shutil
import subprocess
from pathlib import Path
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

ROOT = Path(__file__).resolve().parent.parent
THESIS_DIR = ROOT / "thesis"
MAIN_TEX = THESIS_DIR / "main.tex"
RAW_DOCX = THESIS_DIR / "raw_pandoc.docx"

# Target file paths
FINAL_DOCX = THESIS_DIR / "NCHU_Thesis_陳宥興_可編輯修改稿.docx"
FINAL_DOC = THESIS_DIR / "NCHU_Thesis_陳宥興_可編輯修改稿.doc"
MAIN_DOCX = THESIS_DIR / "main.docx"
MAIN_DOC = THESIS_DIR / "main.doc"
DATE_DOCX = THESIS_DIR / "NCHU_Thesis_陳宥興_可編輯修改稿_20261114.docx"
DATE_DOC = THESIS_DIR / "NCHU_Thesis_陳宥興_可編輯修改稿_20261114.doc"

def run_pandoc():
    cmd = [
        "pandoc",
        str(MAIN_TEX),
        "-o", str(RAW_DOCX),
        f"--resource-path={THESIS_DIR}:{THESIS_DIR}/picture:{ROOT}/figures",
        "--mathjax"
    ]
    subprocess.run(cmd, check=True)

def style_run(run, font_name="標楷體", font_name_ascii="Times New Roman", size_pt=12, bold=False, italic=False, color_rgb=(0, 0, 0)):
    run.font.name = font_name_ascii
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(*color_rgb)
    rPr = run._r.get_or_add_rPr()
    rFonts = parse_xml(f'<w:rFonts {nsdecls("w")} w:ascii="{font_name_ascii}" w:hAnsi="{font_name_ascii}" w:eastAsia="{font_name}"/>')
    rPr.append(rFonts)

def main():
    print("Step 1: Running pandoc conversion...")
    run_pandoc()
    
    print("Step 2: Post-processing docx with python-docx...")
    raw_doc = docx.Document(RAW_DOCX)
    new_doc = docx.Document()
    
    # Set standard margins (NCHU thesis standard: 2.5cm / ~1 inch)
    sections = new_doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.18)
        section.right_margin = Inches(1.0)
    
    # ------------------ COVER PAGE ------------------
    p_top = new_doc.add_paragraph()
    p_top.paragraph_format.space_before = Pt(36)
    
    p1 = new_doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p1.add_run("國立中興大學人工智慧與資料科學碩士在職學位學程")
    style_run(r1, font_name="標楷體", font_name_ascii="Times New Roman", size_pt=20, bold=True)
    p1.paragraph_format.space_after = Pt(12)
    
    p2 = new_doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("碩士學位論文")
    style_run(r2, font_name="標楷體", font_name_ascii="Times New Roman", size_pt=20, bold=True)
    p2.paragraph_format.space_after = Pt(72)
    
    p3 = new_doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = p3.add_run("半導體製程冷卻水系統時間序列監測的\n異常檢測與預警")
    style_run(r3, font_name="標楷體", font_name_ascii="Times New Roman", size_pt=20, bold=True)
    p3.paragraph_format.space_after = Pt(18)
    p3.paragraph_format.line_spacing = 1.3
    
    p4 = new_doc.add_paragraph()
    p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r4 = p4.add_run("Anomaly Detection and Early Warning for Time-Series Monitoring\nof Semiconductor Process Cooling Water Systems")
    style_run(r4, font_name="Times New Roman", font_name_ascii="Times New Roman", size_pt=16, bold=True)
    p4.paragraph_format.space_after = Pt(72)
    p4.paragraph_format.line_spacing = 1.2
    
    p5 = new_doc.add_paragraph()
    p5.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r5 = p5.add_run("指導教授： 吳宏達")
    style_run(r5, font_name="標楷體", font_name_ascii="Times New Roman", size_pt=20, bold=True)
    p5.paragraph_format.space_after = Pt(12)
    
    p6 = new_doc.add_paragraph()
    p6.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r6 = p6.add_run("研究生： 陳 宥興")
    style_run(r6, font_name="標楷體", font_name_ascii="Times New Roman", size_pt=20, bold=True)
    p6.paragraph_format.space_after = Pt(64)
    
    p7 = new_doc.add_paragraph()
    p7.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r7 = p7.add_run("中華民國一百一十五 年十一月")
    style_run(r7, font_name="標楷體", font_name_ascii="Times New Roman", size_pt=20, bold=True)
    
    # Page Break after Cover
    new_doc.add_page_break()
    
    # ------------------ ORAL DEFENSE APPROVAL RESERVED PAGE ------------------
    p_app_top = new_doc.add_paragraph()
    p_app_top.paragraph_format.space_before = Pt(220)
    
    p_app = new_doc.add_paragraph()
    p_app.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_app = p_app.add_run("口試審核頁預留")
    style_run(r_app, font_name="標楷體", font_name_ascii="Times New Roman", size_pt=20, bold=True)
    
    new_doc.add_page_break()
    
    # ------------------ COPY BODY FROM RAW DOCX ------------------
    skip_first_oral = True
    
    for element in raw_doc.element.body:
        if element.tag.endswith('p'):
            text = "".join(element.itertext()).strip()
            if skip_first_oral and "口試審核頁預留" in text:
                skip_first_oral = False
                continue
            new_doc.element.body.append(element)
        elif element.tag.endswith('tbl'):
            new_doc.element.body.append(element)
        elif element.tag.endswith('sectPr'):
            pass
    
    print(f"Step 3: Saving final docx to {FINAL_DOCX}...")
    new_doc.save(FINAL_DOCX)
    
    if RAW_DOCX.exists():
        RAW_DOCX.unlink()
        
    print("Step 4: Converting docx to authentic doc format via textutil...")
    cmd_doc = ["textutil", "-convert", "doc", "-output", str(FINAL_DOC), str(FINAL_DOCX)]
    subprocess.run(cmd_doc, check=True)
    
    print("Step 5: Creating aliases and copies (main.doc, main.docx, date-stamped copies)...")
    shutil.copy2(FINAL_DOCX, MAIN_DOCX)
    shutil.copy2(FINAL_DOC, MAIN_DOC)
    shutil.copy2(FINAL_DOCX, DATE_DOCX)
    shutil.copy2(FINAL_DOC, DATE_DOC)
    
    # Also sync to project root
    shutil.copy2(FINAL_DOCX, ROOT / FINAL_DOCX.name)
    shutil.copy2(FINAL_DOC, ROOT / FINAL_DOC.name)
    shutil.copy2(MAIN_DOCX, ROOT / "main.docx")
    shutil.copy2(MAIN_DOC, ROOT / "main.doc")
    
    print("Successfully generated all Word documents:")
    print(f"  - {FINAL_DOCX}")
    print(f"  - {FINAL_DOC}")
    print(f"  - {MAIN_DOCX}")
    print(f"  - {MAIN_DOC}")
    print(f"  - {DATE_DOCX}")
    print(f"  - {DATE_DOC}")

if __name__ == "__main__":
    main()
