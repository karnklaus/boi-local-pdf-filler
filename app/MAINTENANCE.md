# คู่มือดูแลและเพิ่มเอกสาร BOI

เอกสารนี้เป็นแนวทางสำหรับผู้พัฒนาในอนาคต กรณีต้องเพิ่ม PDF ใหม่ แก้ชื่อฟิลด์ แก้หน้ากรอกข้อมูล หรือแก้รูปแบบไฟล์ PDF ที่ Export ออกมา

## ภาพรวมการทำงาน

แอปทำงานเฉพาะเครื่องนี้ที่ `127.0.0.1` และใช้ลำดับดังนี้:

```text
เลือกเอกสาร
    ↓
กรอกข้อมูลกลางชุดเดียว โดยแยกดูทีละเอกสาร
    ↓
ตรวจสอบข้อมูล
    ↓
เติมข้อมูลลง PDF ที่เลือก และรวมเป็น PDF เดียว
```

ผลลัพธ์เป็น PDF แบบ Static สำหรับพิมพ์ต่อ โดยระบบจะลบ Widget/Form Field ออกจากไฟล์ผลลัพธ์แล้ว ส่วนช่องลายเซ็นจะเว้นไว้ตามแม่แบบ PDF

## โครงสร้างโฟลเดอร์

```text
D:\boi\app\
├─ app.py                         # Workflow หลักและการสร้าง PDF
├─ run_app.bat                    # เปิดแอปบนเครื่องนี้
├─ README.md                      # คำอธิบายแบบย่อ
├─ MAINTENANCE.md                 # คู่มือนี้
├─ requirements.txt               # Runtime dependencies ที่ทดสอบแล้ว
├─ .gitignore                     # กันข้อมูล private และไฟล์ generated
├─ config\
│  ├─ documents.example.json      # config สาธารณะที่ไม่มี PDF จริง
│  └─ documents.json              # config local/private ไม่ commit
├─ documents\                    # PDF แม่แบบที่แอปใช้จริง
│  └─ *.fill.pdf
├─ data\                          # SQLite session private (สร้างตอนรัน)
│  └─ sessions.sqlite3
├─ tests\                         # Automated workflow tests
│  └─ test_app.py
├─ templates\                    # HTML ของแต่ละหน้า
│  ├─ base.html
│  ├─ select_documents.html
│  ├─ form.html
│  ├─ review.html
│  ├─ export.html
│  ├─ _progress.html
│  └─ _settings_modal.html
└─ static\
   ├─ style.css                   # สี ระยะห่าง Layout และ Responsive
   └─ app.js                      # Sync ฟิลด์, Tabs, Settings Popup
```

## ขอบเขต public/private

`documents.example.json` ใช้เป็น schema/config ตัวอย่างสำหรับ public repository ส่วน `documents.json` เป็น config ที่ผูกกับ PDF private ในเครื่องจริง และถูกกันด้วย `.gitignore` เช่นเดียวกับ `documents\`, `data\`, `source\`, `working\`, `output\` และ `_duplicates\`

Automated tests สร้าง PDF synthetic ใน temporary directory เอง จึงไม่ควร copy PDF บริษัทเข้ามาใน test fixture หรือ commit ลง repository

## ต้องแก้ไฟล์ไหนในแต่ละกรณี

| ต้องการเปลี่ยนแปลง | จุดที่ต้องแก้ |
|---|---|
| เพิ่ม PDF ใหม่ | วางไฟล์ใน `documents\` และเพิ่มรายการใน `config\documents.json` |
| เปลี่ยนชื่อเอกสารที่แสดงบนเว็บ | ค่า `title` และ `description` ใน `config\documents.json` |
| เปลี่ยนลำดับเริ่มต้นเอกสาร | ค่า `order` ในรายการเอกสารของ config; ผู้ใช้ยังจัดเรียงซ้ำได้ในหน้า Export |
| เปิด/ปิดเอกสารชั่วคราว | ค่า `enabled` ใน config โดยไม่ต้องลบ PDF |
| เปลี่ยนชื่อ Text Field ใน Adobe | เปลี่ยนชื่อใน Adobe แล้วแก้ค่า `pdf_field` ให้ตรงกันใน config |
| ย้ายตำแหน่งข้อความใน PDF | ย้ายหรือปรับขนาด Text Field ใน Adobe ไม่ต้องแก้พิกัดใน `app.py` |
| เพิ่มข้อมูลกลางช่องใหม่ | เพิ่ม field ในส่วน `fields` และเพิ่ม binding ให้เอกสารที่ต้องใช้ |
| ทำให้ข้อมูลช่องเดียวกัน Sync ข้ามเอกสาร | ใช้ค่า `key` เดียวกันใน binding เช่น `company` |
| แก้หน้ากรอกข้อมูล/รายการเอกสาร | `templates/form.html` และ `static/style.css` |
| ลดความสูงของ Progress 2 | กลุ่ม `.document-field-*` และ `.document-workspace` ใน `static/style.css` |
| แก้หน้า Progress 3 / Review Center | `templates/review.html`, `static/app.js` และกลุ่ม `.review-*` ใน `static/style.css` |
| แก้การทำงานของ Tabs หรือการ Sync ช่อง | `static/app.js` |
| แก้จุดสถานะกรอกข้อมูลของแต่ละเอกสาร | `app.py` ฟังก์ชัน `document_is_complete`, `templates/form.html` และ `static/app.js` |
| แก้ Progress และลำดับขั้นตอน | `templates/_progress.html` และ `app.py` ฟังก์ชัน `build_progress` |
| แก้ Settings Popup | `templates/_settings_modal.html`, `static/app.js`, `static/style.css` และ `app.py` ส่วน `ACCENT_OPTIONS`/`THEME_OPTIONS` |
| เพิ่มหรือเปลี่ยน Font | `FONT_OPTIONS` ใน `app.py` และตรวจ path ใน `C:\Windows\Fonts\` |
| เพิ่มหรือเปลี่ยนสีระบบ | `ACCENT_OPTIONS` ใน `app.py` และตัวแปรสีใน `static/style.css` ทั้ง Light/Dark |
| แก้ Light/Dark/Auto mode | `THEME_OPTIONS` ใน `app.py`, `templates/base.html`, `static/app.js` และตัวแปรธีมใน `static/style.css` |
| แก้การแสดงวันที่ภาษาไทย | ฟังก์ชัน `thai_date`, `date_input_value`, `format_value` ใน `app.py` |
| แก้เหตุผลรายได้น้อย 2 บรรทัด | ฟังก์ชัน `split_reason` หรือ `transform` ใน config |
| เปลี่ยนชื่อไฟล์ Export | ฟังก์ชัน `safe_filename` ใน `app.py` |
| เปลี่ยนวิธีสร้าง/รวม PDF | ฟังก์ชัน `binding_values` และ `render_filled_pdf` ใน `app.py` |

เอกสารทั่วไปไม่ควรต้องแก้ `app.py` แค่เพื่อเพิ่ม PDF หรือ mapping ใหม่ ให้เริ่มจาก `documents\` และ `config\documents.json` ก่อน

## ขั้นตอนเพิ่มเอกสารใหม่

### 1. เตรียม PDF ด้วย Adobe

1. เปิด PDF ต้นฉบับใน Adobe Acrobat
2. สร้าง Text Field เฉพาะจุดที่ต้องการให้ระบบเติมข้อมูล
3. ตั้งชื่อฟิลด์ให้ไม่ซ้ำกันภายในเอกสาร และจำชื่อจริงไว้ให้ครบ
4. ปรับตำแหน่งและขนาดของ Field ให้ตรงกับพื้นที่ในเอกสาร
5. เว้นช่องลายเซ็นไว้ ไม่ต้องสร้าง Field สำหรับลายเซ็นถ้าต้องการเขียนเองภายหลัง
6. บันทึกเป็น PDF แบบ Fillable เช่น `new-document.fill.pdf`

แนะนำให้ใช้ชื่อไฟล์ภาษาอังกฤษ/ตัวเลขสำหรับไฟล์ใน `documents\` เพื่อลดปัญหา encoding และควรเก็บ PDF ต้นฉบับไว้ใน `..\source\originals\` โดยไม่เขียนทับไฟล์เดิม

### 2. วางไฟล์แม่แบบ

วางไฟล์ในโฟลเดอร์นี้:

```text
D:\boi\app\documents\new-document.fill.pdf
```

ชื่อไฟล์ใน config ต้องตรงกับชื่อจริงแบบตัวต่อตัว รวมถึงนามสกุลไฟล์

### 3. เพิ่มรายการใน config

เปิด `config\documents.json` แล้วเพิ่ม object ใน array `documents` ตัวอย่าง:

```json
{
  "id": "new-document",
  "title": "ชื่อเอกสารใหม่",
  "description": "คำอธิบายสั้น ๆ ที่แสดงให้ผู้ใช้เห็น",
  "filename": "new-document.fill.pdf",
  "enabled": true,
  "order": 30,
  "bindings": [
    {"pdf_field": "ชื่อบริษัทใน PDF", "key": "company"},
    {"pdf_field": "วันที่ใน PDF", "key": "letter_date"}
  ]
}
```

กฎสำคัญ:

- `id` ต้องไม่ซ้ำกับเอกสารอื่น และควรใช้ภาษาอังกฤษ/ตัวเลข/ขีดกลาง
- `title` คือชื่อที่ผู้ใช้เห็น ไม่จำเป็นต้องเหมือนชื่อไฟล์
- `filename` ต้องเป็นไฟล์ที่มีอยู่จริงใน `documents\`
- `enabled: true` ทำให้เอกสารปรากฏในหน้าเลือก
- `order` ใช้เป็นลำดับเริ่มต้นในหน้าเลือกและ PDF รวม แต่ผู้ใช้สามารถแก้ลำดับเฉพาะงานปัจจุบันในหน้า Export ได้
- `pdf_field` ต้องตรงกับชื่อ Text Field ใน Adobe ทุกตัวอักษร ช่องว่าง และวรรณยุกต์
- `key` ต้องเป็นชื่อข้อมูลกลางที่มีอยู่ในส่วน `fields`
- JSON ห้ามใส่ comment และห้ามมี comma หลังรายการสุดท้าย

### 4. กรณีเอกสารต้องใช้ข้อมูลใหม่

ถ้าเอกสารใหม่ใช้ข้อมูลที่ยังไม่มีใน config ให้เพิ่มใน object `fields` ก่อน เช่น:

```json
"branch_number": {
  "label": "เลขที่สาขา",
  "type": "number",
  "placeholder": "กรอกตัวเลข",
  "required": false,
  "order": 140
}
```

จากนั้นเพิ่ม binding:

```json
{"pdf_field": "เลขที่สาขาใน PDF", "key": "branch_number"}
```

ประเภทข้อมูลที่ระบบรองรับในปัจจุบัน:

| `type` | การทำงาน |
|---|---|
| `text` | ช่องข้อความบรรทัดเดียว |
| `textarea` | ช่องข้อความหลายบรรทัด |
| `date` | กรอก/เลือกวันที่เป็น `วว/ดด/พ.ศ.` และระบบเก็บภายในเป็น `YYYY-MM-DD` |
| `number` | รับเฉพาะตัวเลข 0–9 และเว้นว่างได้ |

ปัจจุบันทุกช่องตั้งใจให้เว้นว่างได้ ดังนั้นอย่าเพิ่ม validation บังคับใน `app.py` เว้นแต่มีความต้องการใหม่ที่ชัดเจน

### 5. ข้อมูลที่ใช้ร่วมกันระหว่างเอกสาร

ถ้าข้อมูลเดียวกันปรากฏในหลาย PDF ให้ใช้ `key` เดียวกัน เช่น:

```json
{"pdf_field": "ชื่อบริษัทเอกสาร A", "key": "company"}
{"pdf_field": "ชื่อบริษัทเอกสาร B", "key": "company"}
```

หน้าเว็บจะแสดงช่องแยกตามเอกสาร แต่เมื่อกรอกช่องใดช่องหนึ่ง ค่าจะ Sync ไปยังช่องที่มี `data-shared-key` เดียวกัน และ backend จะรวมกลับเป็นข้อมูลกลางชุดเดียว

อย่าสร้าง key ซ้ำในชื่ออื่น เช่น `company_2` ถ้าหมายถึงบริษัทเดียวกัน เพราะจะทำให้ข้อมูลไม่ Sync กัน

### 6. ฟิลด์พิเศษและการแบ่งเหตุผลเป็น 2 บรรทัด

ผู้ใช้กรอก `reason` เพียงช่องเดียว ระบบจะวัดความกว้างของ Text Field และแบ่งข้อความลงฟิลด์ PDF สองตัว:

```json
{"pdf_field": "สาเหตุบรรทัดที่หนึ่ง", "key": "reason", "transform": "reason_line_1"}
{"pdf_field": "สาเหตุบรรทัดที่สอง", "key": "reason", "transform": "reason_line_2"}
```

ถ้าเอกสารใหม่มีกรณีพิเศษแบบเดียวกัน ให้ใช้ `reason_line_1` และ `reason_line_2` ได้ หากเป็นกฎใหม่ที่ระบบยังไม่รู้จัก ต้องเพิ่ม logic ใน `binding_values`/ฟังก์ชัน transform ของ `app.py` พร้อมทดสอบผลลัพธ์จริง

## Font และขนาด Font

Font และขนาด Font เป็นการตั้งค่าของงานปัจจุบัน สามารถแก้ได้จากปุ่มรูปเฟืองบน Header หรือแก้โดยตรงใน Progress 4 ก่อนดาวน์โหลด PDF

Font ที่ลงทะเบียนไว้ในปัจจุบันอยู่ใน `FONT_OPTIONS` ของ `app.py` ได้แก่:

- TH Sarabun New: `C:\Windows\Fonts\THSarabunNew.ttf`
- Tahoma: `C:\Windows\Fonts\tahoma.ttf`
- Arial: `C:\Windows\Fonts\arial.ttf`

ถ้าจะเพิ่ม Font:

1. ตรวจว่าติดตั้ง Font บนเครื่องจริง
2. เพิ่มชื่อ, path ไฟล์ `.ttf` และชื่อที่ใช้ register กับ ReportLab ใน `FONT_OPTIONS`
3. เพิ่ม option ใน `templates/_settings_modal.html` ถ้าต้องการให้เลือกจากหน้าเว็บ
4. ทดลอง Export กับข้อความภาษาไทยและภาษาอังกฤษ

การเปลี่ยน Font อาจทำให้ข้อความกว้างขึ้นหรือแคบลง โดยเฉพาะ `reason` ที่แบ่งตามความกว้าง Field ดังนั้นต้องตรวจ PDF จริงทุกครั้งหลังเปลี่ยน Font หรือขนาด

## Progress 3: Review Center

หน้า Progress 3 แสดงเอกสารแบบ 2 ฝั่งเพื่อรองรับเอกสารจำนวนมาก:

- ฝั่งซ้ายคือรายการเอกสารที่เลือกและมีพื้นที่เลื่อนของตัวเอง
- ฝั่งขวาแสดงข้อมูลของเอกสารที่กำลังเลือกเพียงรายการเดียว
- ค้นหาได้จากชื่อเอกสาร และกรอง `ทั้งหมด`, `ยังไม่ครบ`, `ครบแล้ว`
- ปุ่ม `แก้ไขข้อมูล` ของแต่ละเอกสารจะกลับไปยัง Tab ของเอกสารนั้นใน Progress 2 ผ่าน URL hash เช่น `#document-tab-change-visa`
- เรื่องลำดับเอกสารยังอยู่ใน Progress 4 ตามเดิม

ถ้าจะปรับพฤติกรรมการเลือกเอกสาร ให้แก้ส่วน `data-review-*` ใน `templates/review.html` และ logic Review Center ใน `static/app.js` อย่าใช้เลขลำดับเป็นตัวระบุเอกสาร เพราะผู้ใช้สามารถจัดลำดับใหม่ใน Progress 4 ได้ ให้ใช้ `doc.id` เป็นหลัก

## สีระบบและ Light/Dark mode

ผู้ใช้เปลี่ยนค่าได้จากปุ่มรูปเฟืองบน Header โดยค่าจะถูกเก็บใน Session ของงานปัจจุบัน และใช้กับหน้าเว็บทั้งหมด สีที่เลือกมีผลเฉพาะ UI ไม่เปลี่ยนสีหรือรูปแบบของข้อความที่วางลงใน PDF

ตัวเลือกสีและธีมถูกกำหนดไว้ใน `app.py`:

- `ACCENT_OPTIONS` คือรายการสีหลัก เช่น `purple`, `blue`, `green`, `orange`
- `THEME_OPTIONS` คือธีม `light`, `dark` และ `auto` (ตามระบบปฏิบัติการ)
- `current_settings()` ตรวจและคืนค่าที่ปลอดภัยก่อนส่งให้ Template
- `templates/base.html` ใส่ค่าเป็น `data-theme`, `data-theme-preference` และ `data-accent` บน `<html>`
- `static/app.js` ติดตามการเปลี่ยนโหมดสีของระบบเมื่อเลือก `Auto`

โครงสร้าง Settings Popup ปัจจุบันเรียงเป็น 3 ช่วง: ฟอนต์/ขนาดฟอนต์แบบ 2 คอลัมน์, สีหลักแบบ 4 ช่องเต็มแถว และ Light/Dark/Auto แบบ 3 ปุ่มเต็มแถว ถ้าปรับหน้าตา ให้แก้ markup ใน `templates/_settings_modal.html` และ layout ใน `.modal-fields`, `.settings-preferences`, `.accent-options` และ `.theme-options` ของ `static/style.css`
- `static/style.css` เป็นจุดกำหนดสีของแต่ละ accent และค่าพื้นหลัง/ตัวอักษรของ Dark mode

ถ้าจะเพิ่มสีใหม่ ให้เพิ่ม key ใน `ACCENT_OPTIONS` และเพิ่ม selector ทั้งสองแบบใน `static/style.css`:

```css
html[data-accent="new-color"] { /* Light */ }
html[data-theme="dark"][data-accent="new-color"] { /* Dark */ }
```

ควรตรวจ Contrast ของสีปุ่ม สีข้อความ และ Focus ring ในทั้งสองธีมก่อนใช้งานจริง ไม่ควรเปลี่ยนแค่สีม่วงใน `:root` เพราะจะทำให้ค่าใน Dark mode ไม่ครบ

## Checklist หลังเพิ่มหรือแก้เอกสาร

ก่อนส่งให้ผู้ใช้ ให้ตรวจอย่างน้อยรายการต่อไปนี้:

- [ ] เปิดแอปใหม่หลังแก้ config เพราะ config ถูกอ่านตอนเริ่มโปรแกรม
- [ ] หน้าเลือกเอกสารแสดงชื่อใหม่ถูกต้อง
- [ ] เลือกเอกสารใหม่เพียงไฟล์เดียวแล้ว Export ได้ PDF 1 หน้า
- [ ] เลือกเอกสารเดิมและใหม่แล้ว Export ได้จำนวนหน้าตามลำดับที่แสดงใน Review
- [ ] ทดลองพิมพ์เลขลำดับใหม่และลากรายการในหน้า Export แล้วตรวจลำดับหน้า PDF
- [ ] ข้อมูลร่วม เช่น ชื่อบริษัท และวันที่ Sync ข้ามแท็บได้
- [ ] ช่องว่างยังสามารถส่งต่อไป Review/Export ได้ตามนโยบายปัจจุบัน
- [ ] ช่องวันที่เลือกได้ และวันที่ใน PDF แสดงเป็นภาษาไทย
- [ ] ช่องตัวเลขรับเฉพาะ 0–9
- [ ] Progress 2 แสดงจุดสีแดงเมื่อข้อมูลเอกสารยังไม่ครบ และเปลี่ยนเป็นสีเขียวเมื่อครบ
- [ ] เหตุผลยาวถูกแบ่งบรรทัดและไม่ล้นกรอบ
- [ ] ช่องลายเซ็นยังว่าง
- [ ] PDF Export ไม่มี Widget/Form Field ว่างติดอยู่
- [ ] ชื่อไฟล์แก้ไขได้ใน Progress 4, ค่าเริ่มต้นเป็น `หนังสือบริษัท ชื่อบริษัท.pdf` และสร้างใหม่ทุกครั้งเมื่อชื่อบริษัทเปลี่ยน
- [ ] ชื่อไฟล์ลงท้ายด้วย `.pdf` และไม่มีอักขระต้องห้ามของ Windows
- [ ] เปลี่ยนสีหลักเป็นทุกตัวเลือกแล้วตรวจปุ่ม, Progress, จุดสถานะ และ Focus
- [ ] สลับ Light/Dark แล้วตรวจพื้นหลัง, ช่องกรอก, Modal และตัวอักษรว่าอ่านได้ครบ

## คำสั่งตรวจสอบบน Windows

เปิด PowerShell ใน `D:\boi\app` แล้วรัน:

```powershell
python -B -c "from pathlib import Path; compile(Path('app.py').read_text(encoding='utf-8'), 'app.py', 'exec')"
node --check static/app.js
python -m json.tool config/documents.example.json > $null
python -B -m unittest discover -s tests -v
```

ตรวจ mapping และไฟล์ที่ config อ้างถึง (ใช้ได้เมื่อมี private config/PDF ในเครื่อง):

```powershell
@'
from app import CONFIG_ERRORS
for error in CONFIG_ERRORS:
    print(error)
if CONFIG_ERRORS:
    raise SystemExit(1)
print("CONFIG_ERRORS=0")
'@ | python -B -
```

จากนั้นรัน:

```powershell
python app.py
```

แล้วเปิด `http://127.0.0.1:5000` ถ้าแก้ `app.py` หรือ `config\documents.json` ให้หยุดแล้วเปิดโปรแกรมใหม่ก่อนทดสอบ

ตรวจว่า PDF ไม่มี Widget ด้วย Python หลัง Export:

```python
from pypdf import PdfReader

reader = PdfReader("ผลลัพธ์.pdf")
widget_count = sum(
    len(page.get("/Annots", []))
    for page in reader.pages
)
assert widget_count == 0, f"ยังมี Widget อยู่ {widget_count} รายการ"
```

## แก้ปัญหาที่พบบ่อย

### แจ้งว่าไม่พบ PDF Field

ตรวจตามลำดับนี้:

1. เปิด PDF แม่แบบใน Adobe และดูชื่อ Field จริง
2. ตรวจว่าชื่อใน `pdf_field` ตรงกันแบบตัวต่อตัว
3. ตรวจว่า `filename` ชี้ไปยังไฟล์ใน `documents\` ที่ถูกต้อง
4. ปิดแล้วเปิด Flask ใหม่

ชื่อ Field ที่ต่างกันแม้เพียงช่องว่างหรือตัวอักษรหนึ่งตัวจะถือว่าไม่ตรงกัน

### ข้อความอยู่ผิดตำแหน่ง

ระบบใช้สี่เหลี่ยมของ Adobe Text Field เป็นตำแหน่งและขนาดในการวางข้อความ ให้แก้ด้วยการย้าย/ปรับขนาด Field ใน Adobe แล้วบันทึก PDF ใหม่ ไม่ควร hardcode พิกัดใน `app.py`

### วันที่ไม่แสดงหรือแสดงผิดรูปแบบ

ผู้ใช้กรอกวันที่เป็น `วว/ดด/พ.ศ.` เช่น `01/09/2569` หรือเลือกจากปุ่มปฏิทิน ระบบจะแปลงภายในเป็น ISO `2026-09-01` และแสดง/Export เป็น `1 กันยายน 2569` หากแก้ backend โดยตรง ให้คงค่า ISO ไว้ใน Session

### อายุหรือช่องตัวเลขกรอกไม่ได้

ช่อง `number` รับเฉพาะเลข ASCII `0–9` ไม่รับคำว่า `ปี` หรือเลขไทย หากต้องการเปลี่ยนกฎนี้ต้องแก้ทั้ง input ใน `templates/form.html` และ validation ใน `app.py`

### Font ภาษาไทยแสดงไม่ครบ

ตรวจว่าไฟล์ `.ttf` มีอยู่จริงใน `C:\Windows\Fonts\` และชื่อ path ใน `FONT_OPTIONS` ถูกต้อง จากนั้นลอง Export ใหม่ด้วย TH Sarabun New หรือ Tahoma

## สิ่งที่ไม่ควรทำ

- อย่าลบหรือเขียนทับไฟล์ใน `..\source\originals\`
- อย่าแก้ PDF ต้นฉบับเพื่อใช้แทน PDF ใน `documents\` โดยไม่เก็บสำเนา
- อย่าแก้พิกัดข้อความใน `app.py` ถ้าปัญหาเกิดจากตำแหน่ง Field ใน Adobe
- อย่าใช้ key คนละชื่อแทนข้อมูลเดียวกัน
- อย่าใส่ข้อมูลตัวอย่างหรือข้อความตกแต่งที่ผู้ใช้ไม่จำเป็นต้องเห็นในหน้าเว็บ
- อย่าเพิ่ม CDN, analytics หรือบริการภายนอก เพราะแอปนี้ออกแบบให้ทำงานเฉพาะเครื่อง
- อย่าคง Widget/Form Field ไว้ใน PDF ผลลัพธ์ ถ้าต้องการไฟล์ Static สำหรับพิมพ์
- อย่า commit `data\sessions.sqlite3`, PDF ใน `documents\` หรือข้อมูลจากบริษัทขึ้น repository
- อย่าเปลี่ยน `app.run` เป็น `0.0.0.0` หากยังไม่มี authentication และการป้องกันเครือข่าย
- อย่าใส่ค่า `BOI_SECRET_KEY` จริงไว้ใน source code หรือไฟล์ที่ commit

## สรุปสั้นสำหรับจำในอนาคต

```text
เพิ่ม PDF       → documents\ + documents.json
เปลี่ยนชื่อ      → documents.json
เปลี่ยนตำแหน่ง  → Adobe Text Field
เพิ่มข้อมูลใหม่  → fields + bindings ใน documents.json
แก้หน้าตา       → templates\ + static\style.css
แก้การทำงานเว็บ → static\app.js
แก้ PDF logic   → app.py
```

อัปเดตคู่มือนี้เมื่อเพิ่มประเภทข้อมูลใหม่ เพิ่ม transform ใหม่ หรือเปลี่ยนขั้นตอน Export เพื่อให้คนดูแลโปรเจกต์ต่อไม่ต้องไล่อ่านโค้ดทั้งหมดใหม่
