# Bộ xử lý hồ sơ y tế nâng cao (Docling)

## Mục tiêu

Y TẾ MỞ giữ parser nhẹ hiện tại cho request thông thường. Khi cần đọc PDF scan, bảng biểu và tài liệu có bố cục phức tạp, có thể bật **Docling** trong một document worker riêng.

- Dự án: [docling-project/docling](https://github.com/docling-project/docling)
- Giấy phép mã nguồn: MIT (kiểm tra lại license của từng model/artifact được tải kèm trước khi phân phối).
- Khả năng dùng: PDF, DOCX và nhiều định dạng tài liệu; xuất Markdown có cấu trúc; tái dựng bảng; OCR cho vùng ảnh trong PDF.
- Không phải hệ thống hiểu/chẩn đoán y khoa. OCR và trích xuất bố cục vẫn có thể sai.

Tài liệu API chính thức: https://docling-project.github.io/docling/

## Cài đặt tách biệt

Không thêm Docling vào `backend/requirements.txt` của API chính. Docling tải model và có thể tiêu tốn RAM/CPU đáng kể. Cài trong môi trường worker:

```powershell
cd backend
python -m venv .venv-document-ai
.\.venv-document-ai\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-document-ai.txt
```

Lần chạy đầu có thể cần tải model artifacts. Hãy kiểm thử trên bản sao hồ sơ giả lập/đã khử định danh, đo RAM, thời gian xử lý và độ chính xác tiếng Việt trước khi mở cho người dùng.

## Bật chế độ Docling

Chỉ bật trên môi trường đã cài Docling:

```env
YTEMO_DOCUMENT_ENGINE=docling
```

Mặc định không đặt biến này: API tiếp tục dùng parser hiện có. Khi bật, endpoint trích xuất gọi adapter Docling; lỗi được trả thành lỗi trích xuất rõ ràng, không âm thầm quay về parser khác và tạo cảm giác đã đọc đầy đủ.

## Quy tắc dữ liệu và an toàn

1. Xử lý hồ sơ trong bộ nhớ; adapter không ghi file hoặc gửi hồ sơ tới dịch vụ bên ngoài.
2. Không dùng hồ sơ người bệnh để huấn luyện model mặc định.
3. Không đưa văn bản OCR thành clinical knowledge đã duyệt nếu chưa có reviewer.
4. Lưu provenance theo trang, đoạn/bảng và file gốc ở tầng workflow; yêu cầu con người đối chiếu ảnh gốc khi OCR không chắc chắn.
5. Dữ liệu scan, bảng xét nghiệm và thuốc cần bộ test chuyên gia riêng; không lấy việc parser chạy thành công làm bằng chứng chính xác lâm sàng.

## Tiêu chí nghiệm thu trước production

- Bộ test PDF điện tử, PDF scan tiếng Việt, DOCX có bảng, file lỗi, file mã hóa và file >10 MB.
- Đo tỷ lệ trích xuất đúng theo trường (tên xét nghiệm, kết quả, đơn vị, khoảng tham chiếu, ngày, tên thuốc, hàm lượng).
- Báo cáo precision/recall theo trường và tỷ lệ cần người rà soát.
- So sánh latency/RAM của parser nhẹ và Docling trên cùng máy.
- Không triển khai worker lên Render/API production trước khi có benchmark tài nguyên và kiểm thử quyền riêng tư.
