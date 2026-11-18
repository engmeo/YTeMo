# Contributing to Y TẾ MỞ

Cảm ơn bạn quan tâm đóng góp cho Y TẾ MỞ.

## Quy trình

1. Fork repository.
2. Clone fork về máy.
3. Tạo branch riêng cho thay đổi.
4. Cài môi trường và chạy unit tests.
5. Thực hiện thay đổi nhỏ, có mô tả rõ.
6. Chạy lại các test liên quan.
7. Tạo Pull Request về branch main.
8. Chờ review trước khi merge.

## Quy tắc kỹ thuật

- Không commit `.env`, API keys, tokens hoặc service-role secrets.
- Không commit dữ liệu bệnh nhân hoặc dữ liệu cá nhân.
- Không đưa thông tin y khoa không có nguồn thành sự thật đã xác minh.
- Thay đổi Agent cần có test tương ứng khi phù hợp.
- Thay đổi liên quan đến an toàn y tế cần nêu rõ rủi ro và giới hạn.
- Không tự ý thay đổi API contract mà không cập nhật tài liệu.

## Kiểm thử

```powershell
cd backend
python -m unittest -v test_agent_core test_gemini_service test_startup_recovery
```

## Pull Request

Pull Request cần mô tả:
- Vấn đề được giải quyết.
- Phạm vi thay đổi.
- Cách kiểm thử.
- Ảnh hưởng đến dữ liệu, bảo mật hoặc an toàn y tế.
