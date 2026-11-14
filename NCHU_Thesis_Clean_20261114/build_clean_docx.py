"""Build clean, professional NCHU thesis Word document (.docx and .doc) for NCHU_Thesis_Clean_20261114/
Preserving all 15 figures, 11 tables, mathematical formulas, and formal cover/committee pages.
"""
import os
import shutil
import subprocess
from pathlib import Path
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

CLEAN_DIR = Path("/Users/benchen1981/Downloads/Web SCADA Final 20261111/NCHU_Thesis_Clean_20261114")
MAIN_TEX = CLEAN_DIR / "main.tex"
RAW_DOCX = CLEAN_DIR / "raw_pandoc.docx"

FINAL_DOCX = CLEAN_DIR / "NCHU_Thesis_陳宥興_可編輯修改稿.docx"
FINAL_DOC = CLEAN_DIR / "NCHU_Thesis_陳宥興_可編輯修改稿.doc"
MAIN_DOCX = CLEAN_DIR / "main.docx"
MAIN_DOC = CLEAN_DIR / "main.doc"
DATE_DOCX = CLEAN_DIR / "NCHU_Thesis_陳宥興_可編輯修改稿_20261114.docx"
DATE_DOC = CLEAN_DIR / "NCHU_Thesis_陳宥興_可編輯修改稿_20261114.doc"

def run_pandoc():
    print("Running Pandoc on main.tex...")
    cmd = [
        "pandoc",
        str(MAIN_TEX),
        "-o", str(RAW_DOCX),
        f"--resource-path={CLEAN_DIR}:{CLEAN_DIR}/picture",
        "--mathjax"
    ]
    subprocess.run(cmd, check=True)
    print("Pandoc conversion completed.")

def main():
    run_pandoc()

    print("Formatting Document and Prepending Cover & Committee Pages...")
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
    add_before(p0, "", 12, space_after_pt=24)
    add_before(p0, "國立中興大學", 22, bold=True, space_after_pt=10)
    add_before(p0, "人工智慧與資料科學碩士在職學位學程", 20, bold=True, space_after_pt=10)
    add_before(p0, "碩士學位論文", 18, bold=True, space_after_pt=40)
    add_before(p0, "基於因果式時間序列預測與多層狀態機之\n半導體製程冷卻水 (PCW) 壓力漂移早期預警與 Web SCADA 系統整合", 18, bold=True, space_after_pt=18)
    add_before(p0, "Early Warning of Pressure Drift in Semiconductor Process Cooling Water (PCW) Systems\nvia Causal Time-Series Forecasting and Multi-Layer State Machine Integrated with Web SCADA", 14, bold=True, space_after_pt=48)
    add_before(p0, "研  究  生：陳宥興 (You-Xing Chen)", 16, bold=True, space_after_pt=12)
    add_before(p0, "指導教授：吳宏達 博士 (Hong-Da Wu, Ph.D.)", 16, bold=True, space_after_pt=48)
    add_before(p0, "中華民國一一五年十一月\nNovember, 2026", 14, bold=True, space_after_pt=24)

    # Page Break after Cover
    p_br = p0.insert_paragraph_before()
    r_br = p_br.add_run()
    r_br.add_break(docx.enum.text.WD_BREAK.PAGE)

    # ------------------ ORAL DEFENSE APPROVAL PAGE ------------------
    add_before(p0, "", 12, space_after_pt=20)
    add_before(p0, "國立中興大學碩士學位論文口試委員會審定書", 20, bold=True, space_after_pt=24)
    approval_text = (
        "本校 人工智慧與資料科學碩士在職學位學程 碩士班 陳宥興 君所提論文：\n\n"
        "基於因果式時間序列預測與多層狀態機之半導體製程冷卻水 (PCW) 壓力漂移早期預警與 Web SCADA 系統整合\n"
        "Early Warning of Pressure Drift in Semiconductor Process Cooling Water (PCW) Systems via Causal Time-Series Forecasting and Multi-Layer State Machine Integrated with Web SCADA\n\n"
        "經本口試委員會審查，符合碩士學位論文標準，特此證明。"
    )
    add_before(p0, approval_text, 14, bold=False, space_after_pt=36, align=WD_ALIGN_PARAGRAPH.LEFT)

    sign_box = (
        "口試委員會委員：\n\n"
        "________________________        ________________________\n\n"
        "________________________        ________________________\n\n"
        "指導教授：________________________\n\n"
        "所    長：________________________\n\n"
        "中  華  民  國  一  一  五  年  十  一  月      日"
    )
    add_before(p0, sign_box, 13, bold=False, space_after_pt=24, align=WD_ALIGN_PARAGRAPH.LEFT)

    p_br2 = p0.insert_paragraph_before()
    r_br2 = p_br2.add_run()
    r_br2.add_break(docx.enum.text.WD_BREAK.PAGE)

    print(f"Saving final docx to {FINAL_DOCX}...")
    doc.save(FINAL_DOCX)

    if RAW_DOCX.exists():
        RAW_DOCX.unlink()

    print("Generating .doc format via textutil...")
    cmd_doc = ["textutil", "-convert", "doc", "-output", str(FINAL_DOC), str(FINAL_DOCX)]
    subprocess.run(cmd_doc, check=True)

    print("Creating synchronised filenames...")
    shutil.copy2(FINAL_DOCX, MAIN_DOCX)
    shutil.copy2(FINAL_DOC, MAIN_DOC)
    shutil.copy2(FINAL_DOCX, DATE_DOCX)
    shutil.copy2(FINAL_DOC, DATE_DOC)

    print("All Word documents built successfully!")

if __name__ == "__main__":
    main()
