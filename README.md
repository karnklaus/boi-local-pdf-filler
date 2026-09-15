# BOI Local PDF Filler

แอป Flask สำหรับกรอกข้อมูลและ Export PDF แบบใช้เฉพาะเครื่องนี้ที่ `127.0.0.1`

## Public repository boundary

Repository นี้เผยแพร่เฉพาะ source code, ตัวอย่าง config และ automated tests:

- ไม่รวม PDF ของบริษัท
- ไม่รวม `app/config/documents.json` ตัวจริง
- ไม่รวม session database, source originals, QA, output หรือ duplicate archive
- ห้ามกรอกข้อมูลบริษัทจริงลงใน issue, pull request หรือ test fixture

ตัวอย่าง config สาธารณะอยู่ที่ `app/config/documents.example.json` ส่วน workflow จริงต้องใช้ document pack และ config ที่เก็บไว้ในเครื่องเท่านั้น

## Local setup

```powershell
cd app
python -m pip install -r requirements.txt
python app.py
```

เปิด <http://127.0.0.1:5000>

ถ้าต้องการใช้เอกสารจริง ให้เก็บ PDF ไว้ใน `app/documents/` และตั้งค่า `BOI_DOCUMENTS_CONFIG` เป็น `config/documents.json` จาก working directory `app` ห้าม commit ไฟล์เหล่านี้

## Validation

```powershell
cd app
python -B -m unittest discover -s tests -v
uvx ruff check .
uvx bandit -q -r . -x tests
uvx --from pip-audit pip-audit -r requirements.txt
```

## Security boundary

แอปนี้ออกแบบสำหรับเครื่องส่วนตัวหรือเครื่องที่เชื่อถือได้เท่านั้น ไม่มี authentication สำหรับผู้ใช้ภายนอก และไม่ควร bind ไปที่ `0.0.0.0` หรือ deploy ขึ้น Internet โดยตรง อ่าน [SECURITY.md](SECURITY.md) ก่อนใช้งานกับข้อมูลจริง

## License

Source code เผยแพร่ภายใต้ MIT License ดู [LICENSE](LICENSE)
