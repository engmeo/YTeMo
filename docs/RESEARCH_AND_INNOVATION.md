# Nghiên cứu và đổi mới sáng tạo — Y TẾ MỞ

## 1. Định hướng

Y TẾ MỞ định hướng phát triển một hệ sinh thái nghiên cứu công nghệ y tế, kết nối AI, cảm biến đa phương thức, mô hình hóa sinh học, thiết bị y tế chi phí thấp và hợp tác liên ngành.

Một hướng nghiên cứu dài hạn là **Multimodal Biomedical Sensing & Organ Digital Twin** — cảm biến y sinh đa phương thức và bản sao số của hệ cơ quan.

Đây là chương trình nghiên cứu mục tiêu, không phải năng lực đã được triển khai hoặc xác nhận lâm sàng.

## 2. Kiến trúc nghiên cứu đề xuất

```text
SIGNAL GENERATION
OLED / LCD / LED / IR / RF / Ultrasound (tùy thiết bị)
          |
          v
MULTIMODAL SENSING
Camera RGB / NIR / PPG / Structured Light / RF / Ultrasound
          |
          v
SIGNAL PROCESSING
Filtering / Synchronization / Calibration / Reconstruction
Feature Extraction / Quality Assessment
          |
          v
DIGITAL TWIN ENGINE
3D Geometry / Anatomical Model / Physiological State
Temporal Dynamics / Model Uncertainty
          |
          v
ORGAN DIGITAL TWIN
Structure / Function / State / Change Over Time
          |
          v
AI HEALTH INTELLIGENCE
Multimodal Fusion / Trend Analysis / Hypothesis Generation
Evidence & Uncertainty / Clinician Review
          |
          v
PERSONAL HEALTHCARE COMPANION
Consent-aware support and longitudinal follow-up
```

## 3. Các cấp độ Digital Twin

### Cấp 1 — Surface Digital Twin

Tập trung vào hình học bề mặt, tư thế, chuyển động và tín hiệu quang học có thể đo được. Camera phổ thông có thể hỗ trợ một số tác vụ trong điều kiện được kiểm soát; kết quả phụ thuộc ánh sáng, hiệu chuẩn, chất lượng camera và chuyển động.

### Cấp 2 — Anatomical Digital Twin

Mô hình hóa cấu trúc giải phẫu bên trong. Cần dữ liệu phù hợp như CT, MRI, siêu âm hoặc phương thức hình ảnh y khoa đã được kiểm chứng. Camera RGB thông thường không thể tự quan sát trực tiếp nội tạng qua da.

### Cấp 3 — Physiological Digital Twin

Mô hình hóa trạng thái và biến đổi chức năng theo thời gian. Cần dữ liệu sinh lý, mô hình toán học, điều kiện biên, hiệu chuẩn và đối chiếu với phép đo thực tế.

## 4. Các nhóm nghiên cứu

1. **Optical Sensing:** RGB, NIR, PPG, Structured Light, điều chế và đồng bộ xung.
2. **Wave-based Biomedical Sensing:** RF, mmWave, siêu âm và xử lý tín hiệu phản xạ.
3. **Advanced Photonics:** planar photonics, quang thể tích ký/holography và quang phi tuyến như soliton — nghiên cứu theo bài toán cụ thể, không mặc định là thành phần cần thiết của mọi thiết bị.
4. **Photochemistry & Microfluidics:** phản ứng quang hóa bất đối xứng, vi lưu và nền tảng xét nghiệm. Cần phân biệt xúc tác quang, điều khiển phản ứng và kỹ thuật vi lưu; đây là các hướng có cơ chế và yêu cầu thực nghiệm khác nhau.
5. **Physical Reservoir Computing:** nghiên cứu hệ vật lý có động lực học phức tạp (ví dụ dao động chất lỏng) như một nền tảng tính toán tín hiệu. Ý tưởng “logic bằng rung động mặt hồ” cần được chuyển thành giả thuyết đo lường được: trạng thái đầu vào, động lực học, khả năng phân tách trạng thái, độ lặp lại, nhiễu và phép đo đầu ra.
6. **Organ Digital Twin Modeling:** mô hình hình học, giải phẫu, sinh lý và tương tác giữa các hệ cơ quan.
7. **AI Health Intelligence:** hợp nhất dữ liệu đa phương thức, phân tích diễn tiến, phát hiện bất thường và tạo giả thuyết có dẫn chứng, kèm bất định.

## 5. Nguyên tắc vật lý và an toàn

- Màn hình OLED/LCD có thể phát mẫu sáng để hỗ trợ thí nghiệm quang học; nó không tự trở thành nguồn RF hoặc siêu âm.
- Camera RGB không nhìn xuyên da để tái tạo trực tiếp cơ quan nội tạng.
- PPG qua camera/đèn flash chỉ đo biến thiên quang học liên quan tưới máu ngoại vi trong điều kiện nhất định; không thay thế thiết bị chẩn đoán hình ảnh.
- RF/mmWave và siêu âm đòi hỏi phần cứng phát/thu, hiệu chuẩn, giới hạn phơi nhiễm và quy trình an toàn phù hợp.
- AI không thể khôi phục thông tin mà cảm biến không thu được nếu không có giả định/mô hình bổ sung; mọi suy luận phải thể hiện bất định và nguồn dữ liệu.
- Không được suy diễn chẩn đoán bệnh từ dữ liệu webcam đơn lẻ hoặc từ người dùng chỉ đang truy cập một trang web.

## 6. Lộ trình nghiên cứu đề xuất

1. Chọn một bài toán hẹp có thể đo được, ví dụ tái tạo bề mặt hoặc đo chuyển động hô hấp.
2. Xây dựng bộ thu nhận tín hiệu và quy trình hiệu chuẩn.
3. Tạo dữ liệu tham chiếu và đánh giá sai số.
4. Xây dựng mô hình số cho đúng đại lượng đã đo.
5. Kiểm tra độ lặp lại, độ bền vững và sai lệch giữa thiết bị/người dùng.
6. Chỉ mở rộng sang mô hình giải phẫu hoặc sinh lý khi có phương thức đo phù hợp.
7. Đánh giá với chuyên gia và quy trình đạo đức/nghiên cứu cần thiết trước mọi tuyên bố y tế.

## 7. Liên kết với Personal Healthcare Companion

Digital Twin không tự động đọc dữ liệu cảm biến hoặc đưa ra chẩn đoán. Khi có nguyên mẫu được đánh giá phù hợp, lớp tích hợp có thể cung cấp cho Companion các kết quả đã được chuẩn hóa, gồm:
- Loại cảm biến và cấu hình đo.
- Thời điểm, chất lượng và điều kiện thu nhận.
- Đại lượng đo và đơn vị.
- Nguồn dữ liệu, phiên bản thuật toán và hiệu chuẩn.
- Bất định, giới hạn và trạng thái kiểm chứng.
- Phạm vi đồng ý của người dùng.

Companion chỉ sử dụng dữ liệu trong phạm vi consent; kết quả nguy cơ cao cần được chuyển cho chuyên gia y tế có thẩm quyền.

## 8. Trạng thái

`RESEARCH DIRECTION — NOT IMPLEMENTED`

Tài liệu này ghi nhận định hướng nghiên cứu. Nó không khẳng định Y TẾ MỞ hiện có khả năng quét toàn thân, dựng mô hình nội tạng từ webcam, chẩn đoán hình ảnh hoặc dự báo bệnh đã được xác nhận.
