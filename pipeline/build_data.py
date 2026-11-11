# -*- coding: utf-8 -*-
"""build_data.py - สร้าง data/*.json ให้หน้า Monitor
อินพุต : plan70.json (จาก extract_plan70.py) + โฟลเดอร์ raw ที่ดึงจาก HFA (hfa_pull.py --sets planfin)
เอาต์พุต: data/meta.json  data/plan.json  data/actual.json

กติกาสำคัญ (ตกลงกับผู้ใช้):
  * ผลจริงจาก HFA เป็น "ยอดสะสม" -> แปลงเป็นยอดรายเดือน = สะสมเดือนนี้ - สะสมเดือนก่อน
  * แผนเป็นยอดทั้งปี -> แผนรายเดือน = แผนทั้งปี / 12 (ตามวิธีของ กศภ.) ; ถ้ามีปรับแผน (เม.ย.-พ.ค.) ใช้ "แผนใหม่/12" เป็นฐานทั้งปี (เวอร์ชันล่าสุดแทนที่ทั้งหมด)
  * แผน P10 = HFA P09.1+P09.2+P09.3+P10 (พิสูจน์แล้ว 102/102 แห่ง)
"""
import argparse, json, glob, os, datetime
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--fy', type=int, default=2570)
ap.add_argument('--raw', required=True, help='โฟลเดอร์ที่มี planfin_รายเดือน_*.parquet (ใช้ไฟล์ของเดือนล่าสุด)')
ap.add_argument('--plan', default=os.path.join(HERE, 'plan70.json'))
ap.add_argument('--plan-label', default='แผนต้นปี (ส่งวันที่ 19–20 ต.ค. 69)')
ap.add_argument('--out', default=os.path.join(HERE, '..', 'data'))
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

MONTHS = ['ต.ค.', 'พ.ย.', 'ธ.ค.', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.']
REV = ['P04', 'P05', 'P06', 'P61', 'P07', 'P08', 'P09', 'P10', 'P11', 'P12', 'P121', 'P13']
EXP = ['P14', 'P15', 'P151', 'P16', 'P17', 'P18', 'P19', 'P20', 'P21', 'P22', 'P23', 'P24', 'P241', 'P25', 'P251']
SUMS = ['P_REV_TOTAL', 'P_EXP_TOTAL', 'P_NI', 'P_EBITDA']
PLAN_TO_ITEM = {'P13S': 'P_REV_TOTAL', 'P26S': 'P_EXP_TOTAL', 'P27S': 'P_NI', 'P29': 'P_EBITDA'}
LABEL = {'P_REV_TOTAL': 'รวมรายได้', 'P_EXP_TOTAL': 'รวมค่าใช้จ่าย',
         'P_NI': 'รายได้สูง(ต่ำ)กว่าค่าใช้จ่ายสุทธิ (NI)', 'P_EBITDA': 'EBITDA',
         'P10': 'รายได้ค่ารักษาและบริการอื่น ๆ (รวม P09.1–P09.3)'}
KEEP = set(REV + EXP + SUMS)

# ---------- ผลจริง ----------
files = sorted(glob.glob(os.path.join(a.raw, 'planfin_รายเดือน_*.parquet')))
if not files:
    raise SystemExit('ไม่พบ planfin_รายเดือน_*.parquet ใน ' + a.raw)
df = pd.read_parquet(files[-1])
rep = json.load(open(os.path.join(a.raw, '_report.json'), encoding='utf-8'))
for _, r in df[['รหัส', 'รายการ']].drop_duplicates('รหัส').iterrows():
    if r['รหัส'] not in LABEL:
        LABEL[r['รหัส']] = str(r['รายการ']).strip()

cum = {}   # hc -> code -> [12]
for r in df.itertuples(index=False):
    hc = str(r[0]); code = r[2]; mi = int(r[5]) - 1; v = float(r[7])
    cum.setdefault(hc, {}).setdefault(code, [None] * 12)[mi] = v

full = pd.read_parquet(files[-1].replace('planfin_รายเดือน_', 'planfin_'))
hosp = {}
for r in full[['รหัสหน่วยบริการ', 'ชื่อหน่วยบริการ', 'จังหวัด']].drop_duplicates().itertuples(index=False):
    hosp[str(r[0])] = dict(n=r[1], p=r[2])


def filled(arr):
    """เติมค่าที่หายกลางทางด้วยค่าก่อนหน้า (ยอดสะสมไม่ลด) ; ก่อนเดือนแรกที่มีข้อมูล = 0 ; หลังเดือนสุดท้าย = None"""
    last = max((i for i, v in enumerate(arr) if v is not None), default=-1)
    out, prev = [], 0.0
    for i in range(12):
        if i > last:
            out.append(None)
            continue
        v = arr[i]
        v = prev if v is None else v
        out.append(v)
        prev = v
    return out


actual, quality = {}, []
for hc, codes in cum.items():
    parts = [filled(codes[k]) for k in ('P09.1', 'P09.2', 'P09.3', 'P10') if codes.get(k)]
    c10 = []
    for i in range(12):
        vs = [f[i] for f in parts if f[i] is not None]
        c10.append(sum(vs) if vs else None)
    series = {k: v for k, v in codes.items() if k in KEEP and k != 'P10'}
    series['P10'] = c10
    ref = [i for k in ('P_REV_TOTAL', 'P_EXP_TOTAL') for i, v in enumerate(codes.get(k, [None] * 12)) if v is not None]
    L = (max(ref) + 1) if ref else 0
    m = {}
    for k, arr in series.items():
        f = filled(arr)
        mm = []
        for i in range(12):
            if i >= L or f[i] is None:
                mm.append(None)
                continue
            prevv = f[i - 1] if i > 0 and f[i - 1] is not None else 0.0
            mm.append(round(f[i] - prevv, 2))
        if any(x for x in mm if x):
            m[k] = mm
        if k not in ('P_NI', 'P_EBITDA'):
            for i, x in enumerate(mm):
                if x is not None and x < -0.5:
                    quality.append(dict(h=hc, code=k, month=i + 1, value=x))
    hosp.setdefault(hc, dict(n=hc, p=''))
    actual[hc] = dict(L=L, m=m)

if any(c.get('P04.1') and any(v for v in c['P04.1'] if v) for c in cum.values()):
    quality.append(dict(h='*', code='P04.1', month=0, value=0, note='พบยอด P04.1 ไม่เป็นศูนย์ ยังไม่รวมเข้า P04'))

latest = max(h['L'] for h in actual.values())

# ---------- แผน ----------
pj = json.load(open(a.plan, encoding='utf-8'))['plans']
annual = {}
for hc, v in pj.items():
    d = {}
    for k, x in v['items'].items():
        item = PLAN_TO_ITEM.get(k, k)
        if item in KEEP and isinstance(x, (int, float)):
            d[item] = round(x, 2)
    annual[hc] = d
    hosp.setdefault(hc, dict(n=v.get('name') or hc, p=v.get('province') or ''))
missing_plan = sorted(set(actual) - set(annual))
missing_act = sorted(set(annual) - set(actual))
for hc in missing_act:
    actual[hc] = dict(L=0, m={})

hospitals = sorted([dict(c=hc, n=h['n'], p=h['p']) for hc, h in hosp.items()], key=lambda x: (x['p'], x['n']))
items = ([dict(id=i, label=LABEL.get(i, i), g='rev') for i in REV]
         + [dict(id='P_REV_TOTAL', label=LABEL['P_REV_TOTAL'], g='sumrev')]
         + [dict(id=i, label=LABEL.get(i, i), g='exp') for i in EXP]
         + [dict(id='P_EXP_TOTAL', label=LABEL['P_EXP_TOTAL'], g='sumexp')]
         + [dict(id='P_NI', label=LABEL['P_NI'], g='sum'), dict(id='P_EBITDA', label=LABEL['P_EBITDA'], g='sum')])
now = datetime.datetime.now().isoformat(timespec='seconds')
meta = dict(fy=a.fy, months=MONTHS, latest_month=latest, pulled_at=rep.get('pulled_at'), built_at=now,
            tolerance_pct=5.0, items=items, hospitals=hospitals,
            sent=sum(1 for h in actual.values() if h['L'] == latest), total=len(hospitals), quality=quality)
plan = dict(fy=a.fy, versions=[dict(id='v1', label=a.plan_label, from_month=1, annual=annual)])


def dump(name, obj):
    with open(os.path.join(a.out, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))


dump('meta.json', meta)
dump('plan.json', plan)
dump('actual.json', dict(fy=a.fy, hospitals=actual))
print('รพ. %d · ส่งข้อมูลเดือนล่าสุด(%s) %d · แผน %d · ยังไม่มีผลจริงเลย %d' % (
    len(hospitals), MONTHS[latest - 1] if latest else '-', meta['sent'], len(annual),
    sum(1 for h in actual.values() if h['L'] == 0)))
print('ไม่มีแผน:', missing_plan, '· ไม่มีผลจริง:', missing_act)
print('รายการติดลบที่ควรตรวจ:', len(quality), quality[:5])
for n in ('meta', 'plan', 'actual'):
    print(n, round(os.path.getsize(os.path.join(a.out, n + '.json')) / 1024, 1), 'KB')
