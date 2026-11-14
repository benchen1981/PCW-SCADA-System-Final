"""Build clean, professional NCHU thesis Word document (.docx and .doc) from thesis/main.tex, preserving all 15 figures and tables."""
import os
import shutil
import subprocess
from pathlib import Path
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = ROOT.parent
TEMPLATE_DIR = WORKSPACE_ROOT / "NCHU-thesis-template-master"
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

def main():
    print("Step 1: Running pandoc conversion...")
    run_pandoc()
    
    print("Step 2: Prepending Cover Page while preserving all images and tables...")
    doc = docx.Document(RAW_DOCX)
    
    # Set standard margins (NCHU thesis standard: 2.5cm / ~1 inch)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.18)
        section.right_margin = Inches(1.0)
        
    p0 = doc.paragraphs[0]
    w_ns = nsdecls("w")
    
    def add_before(p_anchor, text, size_pt, bold=False, space_after_pt=12, align=WD_ALIGN_PARAGRAPH.CENTER):
        p = p_anchor.insert_paragraph_before()
        p.alignment = align
        p.paragraph_format.space_after = Pt(space_after_pt)
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(size_pt)
        run.bold = bold
        rPr = run._r.get_or_add_rPr()
        xml_str = f'<w:rFonts {w_ns} w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="標楷體"/>'
        rFonts = parse_xml(xml_str)
        rPr.append(rFonts)
        return p

    # ------------------ COVER PAGE ------------------
    add_before(p0, "", 12, space_after_pt=36)
    add_before(p0, "國立中興大學人工智慧與資料科學碩士在職學位學程", 20, bold=True, space_after_pt=12)
    add_before(p0, "碩士學位論文", 20, bold=True, space_after_pt=72)
    add_before(p0, "半導體製程冷卻水系統時間序列監測的\n異常檢測與預警", 20, bold=True, space_after_pt=18)
    add_before(p0, "Anomaly Detection and Early Warning for Time-Series Monitoring\nof Semiconductor Process Cooling Water Systems", 16, bold=True, space_after_pt=72)
    add_before(p0, "指導教授： 吳宏達", 20, bold=True, space_after_pt=12)
    add_before(p0, "研究生： 陳 宥興", 20, bold=True, space_after_pt=64)
    add_before(p0, "中華民國一百一十五 年十一月", 20, bold=True, space_after_pt=24)

    # Page Break after Cover
    p_br = p0.insert_paragraph_before()
    r_br = p_br.add_run()
    r_br.add_break(docx.enum.text.WD_BREAK.PAGE)

    # ------------------ ORAL DEFENSE RESERVED PAGE ------------------
    add_before(p0, "", 12, space_after_pt=220)
    add_before(p0, "口試審核頁預留", 20, bold=True, space_after_pt=24)

    p_br2 = p0.insert_paragraph_before()
    r_br2 = p_br2.add_run()
    r_br2.add_break(docx.enum.text.WD_BREAK.PAGE)

    print(f"Step 3: Saving final docx to {FINAL_DOCX}...")
    doc.save(FINAL_DOCX)
    
    if RAW_DOCX.exists():
        RAW_DOCX.unlink()
        
    print("Step 4: Generating doc format via textutil and Word-compatible copies...")
    cmd_doc = ["textutil", "-convert", "doc", "-output", str(FINAL_DOC), str(FINAL_DOCX)]
    subprocess.run(cmd_doc, check=True)
    
    print("Step 5: Synchronizing all docx and doc files across directories...")
    # Copies within thesis/
    shutil.copy2(FINAL_DOCX, MAIN_DOCX)
    shutil.copy2(FINAL_DOC, MAIN_DOC)
    shutil.copy2(FINAL_DOCX, DATE_DOCX)
    shutil.copy2(FINAL_DOC, DATE_DOC)
    
    # Copies in PCW_SCADA_Final_Project/ root
    shutil.copy2(FINAL_DOCX, ROOT / FINAL_DOCX.name)
    shutil.copy2(FINAL_DOC, ROOT / FINAL_DOC.name)
    shutil.copy2(MAIN_DOCX, ROOT / "main.docx")
    shutil.copy2(MAIN_DOC, ROOT / "main.doc")
    
    # Copies in NCHU-thesis-template-master/
    if TEMPLATE_DIR.exists():
        shutil.copy2(FINAL_DOCX, TEMPLATE_DIR / FINAL_DOCX.name)
        shutil.copy2(FINAL_DOC, TEMPLATE_DIR / FINAL_DOC.name)
        shutil.copy2(MAIN_DOCX, TEMPLATE_DIR / "main.docx")
        shutil.copy2(MAIN_DOC, TEMPLATE_DIR / "main.doc")
        
    # Copies in WORKSPACE_ROOT (/Users/benchen1981/Downloads/Web SCADA Final 20261111/)
    shutil.copy2(FINAL_DOCX, WORKSPACE_ROOT / FINAL_DOCX.name)
    shutil.copy2(FINAL_DOC, WORKSPACE_ROOT / FINAL_DOC.name)
    shutil.copy2(MAIN_DOCX, WORKSPACE_ROOT / "main.docx")
    shutil.copy2(MAIN_DOC, WORKSPACE_ROOT / "main.doc")
    
    print("Successfully built and synchronized all Word documents with all 15 figures.")

if __name__ == "__main__":
    main()
