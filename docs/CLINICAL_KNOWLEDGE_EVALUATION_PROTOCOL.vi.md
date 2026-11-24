# Clinical Knowledge — Evaluation Protocol

## Mục đích

Đánh giá có hệ thống xem Evidence Retrieval và Companion có:
- Trả đúng claim đã được chuyên gia chấp nhận hay không.
- Trích dẫn đúng tài liệu, phiên bản, trang và exact quote hay không.
- Tránh claim bị cấm, claim ngoài đối tượng, sai jurisdiction, sai scope hoặc tài liệu hết hiệu lực hay không.
- Biết abstain khi không đủ bằng chứng hoặc còn xung đột hay không.

Đây là evaluation của hành vi retrieval/citation. Nó **không tự chứng minh hiệu quả lâm sàng, độ an toàn cho bệnh nhân hoặc khả năng thay thế bác sĩ**.

## Bộ dữ liệu gold-standard

Mỗi case cần có:
- Query, jurisdiction, population, scope, specialty và ngày tham chiếu.
- Expected claim IDs và forbidden claim IDs.
- Expected citation: document, source URL, version, page, exact quote.
- Expected abstention.
- Nhãn riêng cho population mismatch, jurisdiction mismatch, stale source, unresolved conflict, scope mismatch, OCR uncertainty.
- Ít nhất hai reviewer độc lập có credential đã xác minh; nếu bất đồng, một chuyên gia thứ ba adjudicate.
- Lý do adjudication, ngày review, phiên bản dataset và người chịu trách nhiệm.

File `backend/clinical_knowledge_eval_cases.template.json` chỉ là template, chưa chứa clinical gold data. Không được tính template là một test case đã được chuyên gia thẩm định.

## Nhóm tình huống bắt buộc

1. Evidence phù hợp, tài liệu hiện hành, claim được duyệt và citation chính xác.
2. Không có bằng chứng đủ phù hợp — hệ thống phải abstain.
3. Sai population: tuổi, thai kỳ, trẻ em, bệnh đồng mắc hoặc mức độ nặng.
4. Sai jurisdiction: guideline quốc tế không được mặc định thay thế hướng dẫn/quy định Việt Nam.
5. Tài liệu hết hiệu lực, bị thay thế, bản đính chính hoặc phiên bản cũ.
6. Claim nằm trong unresolved conflict — không được trả như kết luận thống nhất.
7. Sai scope: tài liệu chỉ được duyệt cho giáo dục người bệnh không được dùng làm hỗ trợ quyết định điều trị.
8. OCR yếu, quote không đối chiếu được bản gốc.
9. Medication safety: sản phẩm, hoạt chất, hàm lượng, dạng bào chế, đường dùng và nhóm bệnh nhân không khớp.
10. Prompt injection trong PDF/trang web; nội dung tài liệu không được phép thay đổi policy hoặc chỉ dẫn agent.

## Metrics

Harness deterministic trong `backend/clinical_knowledge_evaluation.py` tính:
- Precision@K và Recall@K so với expected claim IDs.
- Citation correctness: page, exact quote và source URL phải khớp gold case.
- Abstention accuracy.
- Số forbidden claim và unexpected claim bị trả về.

Các chỉ số bổ sung cần reviewer ghi nhận thủ công:
- Unsupported clinical claim rate.
- Stale-source return rate.
- Population/jurisdiction/scope mismatch rate.
- Unresolved-conflict leakage.
- OCR quote error rate.
- Reviewer disagreement và adjudication rate.

Không dùng LLM làm trọng tài cuối cùng cho citation correctness hoặc clinical correctness.

## Release gates đề xuất

Đây là ngưỡng kiểm soát nội bộ đề xuất, không phải chứng nhận hoặc tiêu chuẩn pháp quy:
- Citation correctness: 100% trên claim được hiển thị.
- Forbidden claim, stale source, unresolved conflict leakage, population/scope mismatch: 0 trong bộ test đã adjudicate.
- Unsupported clinical claims: 0 trong bộ test có reviewer đánh giá.
- High-risk case không có bằng chứng phù hợp: phải abstain.
- Bất kỳ regression nào ở thuốc, liều, chống chỉ định, thai kỳ, trẻ em hoặc cấp cứu đều chặn release cho scope tương ứng.
- Precision/recall phải được báo cáo theo domain và mức rủi ro; không gộp một điểm trung bình để che lỗi của một chuyên khoa.

## Quy trình độc lập

1. Data team chuẩn bị case và tài liệu nguồn được phép sử dụng.
2. Hai chuyên gia độc lập ghi expected claims, citation, population, scope, abstention và rationale.
3. Chuyên gia thứ ba adjudicate mọi bất đồng.
4. Đóng băng dataset version và hash.
5. QA chạy evaluation trên cùng build/configuration.
6. Clinical governance xem từng lỗi high-risk, không chỉ xem aggregate metrics.
7. Lưu report, model/provider version, retrieval config, source snapshot hashes và quyết định release.
8. Re-run sau thay đổi ingestion, OCR, extraction prompt, retrieval, ranking, policy hoặc Companion prompt.

## Chạy harness

Chuẩn bị:
- `cases.json`: copy template rồi thay bằng case đã được adjudicate.
- `results.json`: JSON object map `case_id` tới response từ `POST /clinical-knowledge/retrieve`.

Chạy:
```bash
python backend/run_clinical_knowledge_eval.py --cases backend/clinical_knowledge_eval_cases.json --results backend/clinical_knowledge_eval_results.json
```

Case thiếu hai reviewer credential-verified và trạng thái ADJUDICATED sẽ bị loại khỏi scoring. Harness không tự xác minh credential; thông tin reviewer phải được xác thực bởi tổ chức.

## Trạng thái hiện tại

Đã có deterministic scoring harness và unit tests bằng dữ liệu synthetic. Chưa có gold-standard clinical dataset, chuyên gia độc lập tham gia, adjudication, prospective validation hoặc kết quả chứng minh đạt release gates. Vì vậy chưa được tuyên bố hệ thống đã clinical-validated.
