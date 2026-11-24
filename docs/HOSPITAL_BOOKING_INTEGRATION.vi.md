# Tích hợp đặt lịch bệnh viện — điều kiện triển khai

## Phạm vi đã chốt

Y TẾ MỞ không tự tạo slot, không tự xác nhận lịch và không tuyên bố đã đặt lịch nếu chưa nhận được xác nhận từ hệ thống bệnh viện.

Có hai nhánh:

1. **Bệnh viện có API chính thức và cho phép tích hợp:** triển khai adapter riêng cho từng bệnh viện.
2. **Bệnh viện không có API hoặc chưa cấp quyền:** chỉ hiển thị hướng dẫn và liên kết đặt lịch chính thức đã xác minh. Người dùng tự hoàn tất thao tác trên hệ thống bệnh viện.

## Hợp đồng tối thiểu của một adapter API

Mỗi adapter phải cung cấp:

- `search_slots(specialty, facility, date_range, patient_context)`: trả về slot lấy trực tiếp từ API bệnh viện, kèm thời điểm truy vấn và timezone.
- `create_booking(slot_id, patient_identity, idempotency_key, consent_reference)`: chỉ tạo lịch sau khi người dùng xác nhận lần cuối.
- `get_booking(booking_id)`: đọc trạng thái đặt lịch từ hệ thống nguồn.
- `cancel_booking(booking_id, idempotency_key)`: chỉ hủy khi API bệnh viện hỗ trợ và người dùng xác nhận.

Không dùng LLM để tự tạo slot, tự điền danh tính hoặc tự xác nhận booking.

## Điều kiện mở một adapter

Cần có đủ:

1. Tên pháp nhân/cơ sở và domain API chính thức.
2. API documentation, môi trường sandbox và tài khoản thử nghiệm.
3. Văn bản cho phép tích hợp hoặc hợp đồng với bệnh viện.
4. Cơ chế OAuth/API key, giới hạn tốc độ, chữ ký webhook nếu có.
5. Trường dữ liệu định danh bệnh nhân, quy trình đồng ý chia sẻ dữ liệu và thời hạn lưu.
6. Quy tắc hủy/đổi lịch, phí, timezone và trạng thái booking.
7. Kiểm thử idempotency, lỗi mạng, timeout, slot hết chỗ và xác nhận từ hệ thống nguồn.

API key chỉ lưu ở backend/secret manager, không gửi xuống frontend.

## Fallback khi không có API

- Chỉ dùng liên kết đặt lịch trên domain chính thức đã xác minh.
- Hiển thị địa chỉ, hotline, giấy tờ cần chuẩn bị và hướng dẫn do bệnh viện công bố.
- Gắn thời điểm kiểm tra và thông báo người dùng tự xác nhận với bệnh viện.
- Không hiển thị slot trống giả lập và không ghi trạng thái “đã đặt”.

## Trạng thái hiện tại

Chưa có tên bệnh viện, tài liệu API, sandbox hoặc quyền tích hợp trong phạm vi repo hiện tại. Vì vậy chưa đăng ký adapter bệnh viện nào và chưa bật thao tác đặt lịch tự động. Đây là blocker phụ thuộc đối tác, không phải việc có thể hoàn tất bằng cách viết một adapter chung rồi tuyên bố đã kết nối.
