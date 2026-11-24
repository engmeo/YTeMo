# Thu thập dữ liệu y khoa có giấy phép — Y TẾ MỞ

## Mục tiêu

Thu thập tài liệu y khoa có thể truy nguyên tới nguồn, phiên bản và quyền tái sử dụng. Pipeline không coi dữ liệu miễn phí để đọc là dữ liệu được phép dùng để training.

## Europe PMC Open Access

Collector đầu tiên được triển khai tại `backend/clinical_training/collect_europe_pmc.py`.

Ví dụ:
```bash
cd backend
python -m clinical_training.collect_europe_pmc --query 'TITLE:"hypertension" AND FIRST_PDATE:[2020-01-01 TO 2026-12-31]' --output-dir artifacts/europe_pmc --max-records 50
```

Collector:
- Gọi Europe PMC REST API miễn phí.
- Chỉ tải full-text XML cho bài có PMCID và license nhận diện rõ thuộc CC-BY-4.0, CC-BY-3.0 hoặc CC0.
- Từ chối mặc định CC-BY-NC, CC-BY-ND, all-rights-reserved và license không nhận diện.
- Lưu original XML, SHA-256, PMCID, URL, title, journal, publication date, license và đường dẫn file vào manifest JSONL.
- Loại nội dung trùng theo SHA-256.
- Gắn trạng thái SOURCE_ONLY; không tự biến thành dữ liệu training hoặc claim lâm sàng đã duyệt.

Lưu ý: license metadata của nguồn cần được kiểm tra lại trên trang bài gốc trước khi phát hành dataset. Collector là bộ lọc tự động ban đầu, không phải kết luận pháp lý.

## Chuyển nguồn thành dữ liệu huấn luyện

1. Chuyên viên dữ liệu xác minh source/version/license và kiểm tra nội dung gốc.
2. Tách claim, population, intervention/exposure, comparator, outcome và evidence locator.
3. Người có chuyên môn thẩm định nội dung và gán evidence state STRONG/WEAK/CONFLICTING/INSUFFICIENT.
4. Tạo instruction–response có trích nguồn, version, license và reviewer ID.
5. Đánh dấu privacy review; không sử dụng dữ liệu bệnh nhân thật trong pipeline mặc định.
6. Chạy `python -m clinical_training.prepare_dataset` để chuẩn hóa, deduplicate và từ chối record thiếu provenance/approval.

## Các nguồn khác

- PubMed: metadata và abstract có thể tìm miễn phí; không tự động có quyền tái sử dụng abstract.
- WHO: kiểm tra điều khoản từng ấn phẩm.
- ClinicalTrials.gov: dùng API cho metadata nghiên cứu; xem điều khoản và thành phần third-party.
- CDC: kiểm tra quyền của nội dung bên thứ ba trong tài liệu.

Không scrape website/forum hoặc tải hàng loạt tài liệu chỉ vì truy cập được. Mỗi nguồn mới phải được thêm vào `backend/clinical_training/dataset_sources.json` với access method, license rule và trạng thái được phép dùng.
