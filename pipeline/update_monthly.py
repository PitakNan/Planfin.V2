# -*- coding: utf-8 -*-
"""update_monthly.py - อัปเดตหน้า Planfin Monitor ทุกรอบ (ทำทีเดียวจบ ยกเว้น push)

ใช้:
    python pipeline/update_monthly.py                 # เดือนปฏิทินก่อนหน้า (เช่น วันที่ 10 พ.ย. -> ต.ค.)
    python pipeline/update_monthly.py --month 11      # ระบุเดือนปฏิทิน 1-12 (พ.ย. = 11)
    python pipeline/update_monthly.py --skip-pull     # ใช้ raw ที่ดึงไว้แล้ว (สร้าง data ใหม่อย่างเดียว)

ขั้นตอน
  1) ดึงรายงาน Planfin รายโรงพยาบาลจาก HFA ผ่าน hfa_pull.py (ต้องล็อกอิน ThaiD ก่อนถ้า session หมดอายุ: python hfa_login.py)
     การดึงทีเดียวได้ "ยอดสะสมตั้งแต่ ต.ค. ถึงเดือนที่ขอ" ของทุก รพ. -> แก้ย้อนหลังของ รพ.ถูกดึงมาแทนที่เองทุกรอบ
  2) build_data.py แปลงยอดสะสมเป็นยอดรายเดือน + จับคู่กับแผน -> data/*.json
  3) แสดงสรุป/ข้อควรตรวจ  -- ไม่ commit/push ให้เอง (ตรวจหน้าเว็บก่อน แล้วสั่ง push เอง)

เดือนปฏิทิน -> ปีงบ : ต.ค.-ธ.ค. ใช้ปีงบ = พ.ศ.+1 ; ม.ค.-ก.ย. ใช้ปีงบ = พ.ศ. (ต.ค.69 = --fy 2570 --month 10)
"""
import argparse, datetime, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HFA_DIR = os.environ.get('HFA_DIR', r'D:\Scripts\HFA-TrialBalance')
RAW_ROOT = os.environ.get('PLANFIN_RAW', r'D:\Scripts\Planfin-Monitor\raw')

ap = argparse.ArgumentParser()
ap.add_argument('--month', type=int, help='เดือนปฏิทิน 1-12 (ค่าเริ่มต้น = เดือนก่อนหน้า)')
ap.add_argument('--skip-pull', action='store_true')
ap.add_argument('--plan-label', default=None, help='ชื่อเวอร์ชันแผนที่จะแสดงบนหน้าเว็บ')
a = ap.parse_args()

today = datetime.date.today()
if a.month:
    m = a.month
    ce = today.year if m <= today.month else today.year - 1
else:
    first = today.replace(day=1)
    prev = first - datetime.timedelta(days=1)
    m, ce = prev.month, prev.year
be = ce + 543
fy = be + 1 if m >= 10 else be
raw = os.path.join(RAW_ROOT, '%d-%02d' % (fy, m))
print('ปีงบ %d เดือนปฏิทิน %d  ->  %s' % (fy, m, raw))

if not a.skip_pull:
    cmd = [sys.executable, os.path.join(HFA_DIR, 'hfa_pull.py'), '--fy', str(fy), '--month', str(m), '--sets', 'planfin', '--outdir', raw]
    print('ดึงจาก HFA:', ' '.join(cmd))
    r = subprocess.run(cmd, cwd=HFA_DIR)
    if r.returncode != 0:
        print('\n[หยุด] ดึงข้อมูลไม่สำเร็จ (exit %d) — ถ้า session หมดอายุให้รัน: python %s\\hfa_login.py แล้วลองใหม่' % (r.returncode, HFA_DIR))
        sys.exit(r.returncode)

cmd = [sys.executable, os.path.join(HERE, 'build_data.py'), '--fy', str(fy), '--raw', raw]
if a.plan_label:
    cmd += ['--plan-label', a.plan_label]
r = subprocess.run(cmd)
if r.returncode != 0:
    sys.exit(r.returncode)
print('\nเสร็จ — เปิดดูในเครื่อง: python -m http.server 8765 (ในโฟลเดอร์ Planfin.V2) แล้วเข้า http://localhost:8765/')
print('ยังไม่ได้ commit/push — ตรวจ "ยอดติดลบที่ควรตรวจ" และตัวเลขก่อน แล้วค่อยสั่ง push')
