# -*- coding: utf-8 -*-
"""ดึง "แผนต้นปี 2570" จากชีท 1.Planfin ของไฟล์ worksheet รายโรงพยาบาล -> plan70.json
หาคอลัมน์จากข้อความหัวตาราง (ไม่ hardcode G) · ตรวจตัวเอง 4 ข้อ · ไม่เดา: ที่ไม่ผ่านใส่ flags"""
import os, re, sys, json, shutil, tempfile, glob
import openpyxl, xlrd
from openpyxl.utils import get_column_letter

ROOT = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else 'plan70.json'
SKIP = re.compile(r'เหตุผลประกอบ|คำชี้แจง|ชี้แจง|วิเคราะห์|สรุป|รวม Planfin|ผล Planfin|รายงาน|ปรับแผนการลงทุน')
CODE_RE = re.compile(r'^P(\d+(\.\d+)?|\d+S|29-R|29-E|_.*)$')

def num(v):
    if v is None or v == '': return None
    if isinstance(v, (int, float)): return float(v)
    s = str(v).replace(',', '').strip()
    try: return float(s)
    except ValueError: return None

def load_rows(path):
    """คืน rows (list of list) ของชีท 1.Plan* และชื่อชีท"""
    if path.lower().endswith('.xls'):
        wb = xlrd.open_workbook(path)
        sn = [n for n in wb.sheet_names() if n.startswith('1.Plan')]
        if not sn: return None, None
        sh = wb.sheet_by_name(sn[0])
        return [sh.row_values(i) for i in range(min(sh.nrows, 70))], sn[0]
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sn = [n for n in wb.sheetnames if n.startswith('1.Plan')]
    if not sn: return None, None
    ws = wb[sn[0]]
    return [list(r) for r in ws.iter_rows(min_row=1, max_row=70, values_only=True)], sn[0]

def norm(s): return re.sub(r'\s+', '', str(s or ''))

files = []
STAGED = os.path.join(ROOT, 'index.tsv')   # โหมด staged: ไฟล์ถูกคัดลอกมาไว้ก่อน (001.xlsx ...) + index.tsv บอกที่มาเดิม
ORIG = {}
if os.path.exists(STAGED):
    for ln in open(STAGED, encoding='utf-8-sig'):
        ln = ln.rstrip('\n')
        if not ln: continue
        a, b = ln.split('\t', 1)
        ORIG[os.path.splitext(a)[0]] = b.lstrip(chr(92))
for dp, _, fn in ([] if ORIG else os.walk(ROOT)):
    for f in fn:
        if f.lower().endswith(('.xlsx', '.xls')) and not f.startswith('~$'):
            full = os.path.join(dp, f)
            if SKIP.search(f) or SKIP.search(os.path.basename(dp)): continue
            if os.path.getsize(full) < 1_000_000: continue
            files.append(full)
if ORIG:
    for f in sorted(glob.glob(os.path.join(ROOT, 'plans', '[0-9][0-9][0-9].xls*'))): files.append(f)
files.sort()
tmp = tempfile.mkdtemp()
res, problems = {}, []
for i, src in enumerate(files):
    ext = os.path.splitext(src)[1]
    if ORIG:
        orig = ORIG[os.path.splitext(os.path.basename(src))[0]]
        local = src
    else:
        orig = os.path.relpath(src, ROOT); local = os.path.join(tmp, f'{i}{ext}'); shutil.copyfile(src, local)
    prov = re.sub(r'^\d{4}-\d{2}-\d{2}\s*จังหวัด', '', orig.split(chr(92))[0]).strip('_ ')
    flags = []
    try:
        rows, sheet = load_rows(local)
    except Exception as e:
        problems.append((orig if ORIG else src, 'อ่านไม่ได้: ' + str(e)[:80])); continue
    if rows is None:
        problems.append((orig if ORIG else src, 'ไม่มีชีท 1.Plan*')); continue
    # แถวหัวตาราง = แถวที่ col B = 'รหัสรายการ'
    hdr_i = next((k for k, r in enumerate(rows) if len(r) > 1 and norm(r[1]) == 'รหัสรายการ'), None)
    if hdr_i is None:
        problems.append((orig if ORIG else src, 'หาแถวหัวตารางไม่เจอ')); continue
    hdr = rows[hdr_i]
    cands = [j for j, c in enumerate(hdr) if 'แผนต้นปี' in norm(c) and '2570' in norm(c)]
    if len(cands) != 1:
        problems.append((orig if ORIG else src, f'คอลัมน์แผนต้นปี 2570 พบ {len(cands)} คอลัมน์: {[get_column_letter(j+1) for j in cands]}')); continue
    col = cands[0]
    # รหัส รพ.: แถว 1-3 หา 5 หลัก (ชื่อ รพ. ต้องอยู่ข้างเลข) · เทียบกับชื่อไฟล์
    code_cell = None
    for r in rows[:3]:
        for c in r:
            if re.fullmatch(r'\d{5}', str(c).strip().split('.')[0] if c is not None else ''):
                code_cell = str(c).strip().split('.')[0]
    fn_code = re.search(r'(?<!\d)(\d{5})(?!\d)', os.path.basename(src))
    fn_code = fn_code.group(1) if fn_code else None
    name = next((str(c) for r in rows[:3] for c in r if isinstance(c, str) and ('โรงพยาบาล' in c or c.startswith('รพ'))), None)
    code = code_cell or fn_code
    if code_cell and fn_code and code_cell != fn_code: flags.append(f'รหัสในไฟล์ {code_cell} ≠ ชื่อไฟล์ {fn_code}')
    if not code: problems.append((orig if ORIG else src, 'ไม่พบรหัส รพ.')); continue
    items = {}
    for r in rows[hdr_i + 1:]:
        if len(r) <= max(col, 1): continue
        k = str(r[1]).strip() if r[1] is not None else ''
        if re.match(r'^P', k) and CODE_RE.match(k):
            if k == 'P28': items[k] = r[col]
            else: items[k] = num(r[col])
        if r[2] is not None and 'ข้อมูลคาดการณ์เพิ่มเติม' in str(r[2]): break
    res_key = code
    if res_key in res: flags.append('รหัสซ้ำกับไฟล์อื่น: ' + res[res_key]['file'])
    res[res_key] = dict(code=code, name=name, province=prov, file=orig, sheet=sheet,
                        col=get_column_letter(col + 1), col_header=norm(hdr[col]), items=items, flags=flags)
shutil.rmtree(tmp, ignore_errors=True)
json.dump(dict(plans=res, problems=problems), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ไฟล์ที่สแกน', len(files), '· ดึงได้', len(res), '· ปัญหา', len(problems))
for p in problems: print('  !!', p)
