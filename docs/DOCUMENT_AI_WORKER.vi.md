# Bộ xử lý hồ sơ y tế nâng cao (Docling)

## Mục tiêu

Y TẾ MỞ giữ parser nhẹ hiện tại cho request thông thường. Khi cần đọc PDF scan, bảng biểu và tài liệu có bố cục phức tạp, có thể bật adapter **Docling**. Ở phiên bản hiện tại, adapter vẫn chạy trong tiến trình FastAPI; worker tách biệt là bước triển khai tiếp theo, chưa được xây xong.

- Dự án: [docling-project/docling](https://github.com/docling-project/docling)
- Giấy phép mã nguồn: MIT (kiểm tra lại license của từng model/artifact được tải kèm trước khi phân phối).
- Khả năng dùng: PDF, DOCX và nhiều định dạng tài liệu; xuất Markdown có cấu trúc; tái dựng bảng; OCR cho vùng ảnh trong PDF.
- Không phải hệ thống hiểu/chẩn đoán y khoa. OCR và trích xuất bố cục vẫn có thể sai.

Tài liệu API chính thức: https://docling-project.github.io/docling/

## Cài đặt tùy chọn

Không thêm Docling vào `backend/requirements.txt` của API chính. Nếu muốn thử adapter, cài `requirements-document-ai.txt` trong **chính môi trường Python chạy backend**; cài ở virtualenv khác sẽ không làm API nhìn thấy thư viện. Docling tải model và có thể tiêu tốn RAM/CPU đáng kể:

```powershell
cd backend
python -m pip install -r requirements-document-ai.txt
```

Docling OCR được cấu hình dùng Tesseract CLI với `vie` + `eng`. Máy chạy backend phải có Tesseract và hai bộ `traineddata` tương ứng. Nếu thiếu, xử lý PDF scan sẽ báo lỗi rõ ràng. Lần chạy đầu có thể cần tải model artifacts. Hãy thử bằng hồ sơ giả lập/đã khử định danh, đo RAM, thời gian xử lý và độ chính xác tiếng Việt.

## Bật chế độ Docling

Chỉ bật trên môi trường backend đã cài Docling và Tesseract CLI:

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

## Trạng thái triển khai và tiêu chí nghiệm thu trước production

**Chưa bật trên production.** Vì adapter hiện chạy đồng bộ trong tiến trình API, không được bật trên Render production trước khi tách thành worker có giới hạn concurrency, timeout, RAM và hàng đợi. Việc bật biến môi trường một mình không tạo ra worker riêng.



- Bộ test PDF điện tử, PDF scan tiếng Việt, DOCX có bảng, file lỗi, file mã hóa và file >10 MB.
- Đo tỷ lệ trích xuất đúng theo trường (tên xét nghiệm, kết quả, đơn vị, khoảng tham chiếu, ngày, tên thuốc, hàm lượng).
- Báo cáo precision/recall theo trường và tỷ lệ cần người rà soát.
- So sánh latency/RAM của parser nhẹ và Docling trên cùng máy.
- Không triển khai worker lên Render/API production trước khi có benchmark tài nguyên và kiểm thử quyền riêng tư.
