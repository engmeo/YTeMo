# Patient Journey Cost Intelligence

## Muc tieu
Module `backend/healthcare_cost_intelligence.py` bo sung lop tong hop tai chinh cho du lieu da duoc trich xuat/kiem tra tu Cost, Medication, Lab va BHYT. Module khong tao them specialist agent va khong thay the `HealthcareAgentService`.

## Pham vi da cai dat
- Chuan hoa dong chi phi theo so luong, don gia, thanh tien va currency.
- Tong hop theo nhom dich vu, thuoc, xet nghiem, thu thuat, vat tu, di lai.
- Uoc tinh so hoc BHYT chi khi caller truyen ty le, so tien duoc xac nhan va muc tran (neu co).
- Bao toan `source_quote` va `source_ref` de truy vet.
- Chan currency tron lan, so am, category khong hop le, item id trung.
- Bao ve ranh gioi lam sang: khong tu de xuat doi thuoc, thay lieu, ngung thuoc hay chi dinh xet nghiem.

## Cach dung Python
```python
from healthcare_cost_intelligence import (
    analyze_patient_journey_cost,
    estimate_bhyt_payment,
    build_cost_intelligence_report,
)

costs = analyze_patient_journey_cost([
    {
        "item_id": "invoice-1",
        "category": "visit",
        "description": "Kham benh",
        "quantity": 1,
        "unit_price": 150000,
        "currency": "VND",
        "source_quote": "Tong tien kham: 150.000 VND",
        "source_ref": "invoice.pdf:line-12",
    }
])

bhyt = estimate_bhyt_payment(
    eligible_amount=120000,
    coverage_rate=80,
    rule_reference="Muc huong da duoc nhan vien BHYT xac nhan",
)
```

## Tich hop voi Agent hien co
- `cost`, `medication`, `lab`, `bhyt` van la cac specialist key hien co.
- Adapter/orchestrator can chuyen cac truong da duoc xac minh sang schema cua module; khong truyen phan hoi tu mo hinh nhu so lieu tai chinh da xac thuc neu chua co nguon.
- Endpoint `POST /healthcare/agents/run` va cac API hien co khong bi sua trong ban bo sung nay.
- Chua tu dong dua endpoint moi vao `main.py`, vi viec nay phai dung dung dependency/auth contract dang co cua repository; khong tao route khong duoc bao ve.

## Gioi han
- BHYT chi la uoc tinh so hoc, khong tu suy dien dung tuyen, nhom doi tuong, muc huong, tran quyen loi hay quy dinh phap luat.
- Khong co bang gia benh vien, danh muc thuoc, du lieu hop dong BHYT hoac ty gia tu dong.
- Khong phai tu van y khoa, bao gia, ket luan quyen loi hay xac nhan thanh toan.
