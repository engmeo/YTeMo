# Evidence-grade Clinical Knowledge Foundation — Y TẾ MỞ

## 1. Mục tiêu chất lượng

Layer này không phải một thư mục PDF hay một vector database. Mục tiêu là tạo ra một nền tảng bằng chứng có thể truy nguyên để Companion/Medical Knowledge Agent chỉ tổng hợp trong phạm vi nguồn, đối tượng, thời gian và mục đích đã được phê duyệt.

Một tài liệu chỉ là **nguồn đầu vào**. Một tài liệu không tự động trở thành bằng chứng đủ để đưa ra khuyến nghị. Cần phân biệt:

1. **Publisher/source** — tổ chức phát hành.
2. **Document/version** — tài liệu cụ thể, số hiệu, phiên bản, ngày ban hành, hiệu lực.
3. **Evidence claim** — một mệnh đề hoặc khuyến nghị cụ thể có vị trí trích dẫn trong tài liệu.
4. **Evidence appraisal** — đánh giá thiết kế nghiên cứu, nguy cơ sai lệch, tính nhất quán, độ trực tiếp, độ chính xác và độ chắc chắn.
5. **Clinical synthesis** — tổng hợp nhiều claim trong đúng bối cảnh, quần thể, jurisdiction và thời điểm.
6. **Human authorization** — phê duyệt bởi người có chuyên môn, đúng phạm vi hành nghề và được xác minh danh tính/chứng chỉ.

Không được suy luận rằng nguồn uy tín đồng nghĩa mọi tài liệu trên nguồn đó đều đúng, mới nhất hoặc áp dụng cho mọi bệnh nhân.

## 2. Bảy kho tri thức

Các domain được đăng ký trong bảng `clinical_knowledge_domains`:

| Domain key | Nội dung | Nguyên tắc áp dụng |
|---|---|---|
| `national_guidelines` | Hướng dẫn Bộ Y tế, quyết định, quy trình kỹ thuật và văn bản chuyên môn Việt Nam | Ưu tiên bối cảnh pháp lý/chuyên môn Việt Nam; kiểm tra số hiệu, cơ quan ban hành, hiệu lực và văn bản thay thế |
| `who_guidelines` | Hướng dẫn WHO và khuyến nghị y tế công cộng | Nguồn quốc tế; không tự động thay thế hướng dẫn/quy định Việt Nam |
| `specialty_guidelines` | Hướng dẫn hội chuyên ngành quốc tế | Ghi rõ hội ban hành, nhóm chuyên gia, phương pháp, xung đột lợi ích và khả năng áp dụng tại Việt Nam |
| `medication` | Nhãn/tờ hướng dẫn thuốc được phê duyệt tại Việt Nam, thông tin thuốc, cảnh báo và cảnh giác dược | Không dùng nguồn quốc tế để ghi đè nhãn được phê duyệt tại Việt Nam; mọi thông tin liều phải gắn sản phẩm, hàm lượng, dạng bào chế, đường dùng và đối tượng |
| `health_education` | Tài liệu giáo dục sức khỏe đã được biên tập/thẩm định | Phải xác định đối tượng đọc, mục tiêu, tác giả/tổ chức chịu trách nhiệm và ngày rà soát |
| `diagnostics` | Tiêu chí chẩn đoán, xét nghiệm, hình ảnh học, quy trình theo dõi | Gắn quần thể, phương pháp, đơn vị, thiết bị/phòng xét nghiệm và khoảng tham chiếu cụ thể |
| `prevention_public_health` | Tiêm chủng, sàng lọc, dự phòng, dinh dưỡng, sức khỏe bà mẹ-trẻ em và y tế công cộng | Gắn độ tuổi, nguy cơ, địa bàn, thời điểm và chương trình áp dụng |

### Nguồn khởi tạo trong Source Registry

Migration hiện đăng ký domain của Bộ Y tế Việt Nam, WHO, ESC, KDIGO, GINA, GOLD, ADA và Cục Quản lý Dược Việt Nam. Đây là danh sách khởi tạo để tìm và quản trị tài liệu, **không phải danh sách đã xác minh từng guideline hay license**.

- Bộ Y tế: https://moh.gov.vn/
- WHO Guidelines: https://www.who.int/publications/who-guidelines
- WHO Guidelines Review Committee: https://www.who.int/groups/guidelines-review-committee
- ESC: https://www.escardio.org/Guidelines
- KDIGO: https://kdigo.org/guidelines/
- GINA: https://ginasthma.org/
- GOLD: https://goldcopd.org/
- ADA: https://diabetes.org/
- Cục Quản lý Dược: https://dav.gov.vn/

Không thêm domain của blog, bệnh viện, nhà thuốc, hãng dược hoặc trang tổng hợp vào trust tier cao chỉ vì nội dung có vẻ chuyên nghiệp. Nguồn bổ sung phải qua quy trình đánh giá publisher, governance, editorial policy, conflict-of-interest, update cadence, jurisdiction và license.

## 3. Chuẩn metadata và provenance

Mỗi document phải có tối thiểu:

- `title`, `publisher`, `document_type`, `source_url`, `published_at`.
- `knowledge_domain`, `jurisdiction`, `target_population`.
- `effective_from`, `effective_until`, `version`, `official_identifier`.
- `specialty`, `language`, `license_status`.
- `source_locator`: số trang, mục, bảng, phụ lục hoặc đoạn có thể kiểm tra.
- `content_hash`: phát hiện thay đổi nội dung và trùng lặp.
- `limitations`: giới hạn bằng chứng và điều kiện không áp dụng.

Khi ingest thực tế cần lưu thêm bản gốc bất biến, thời điểm tải, URL tải, HTTP metadata, checksum, extraction/OCR engine và version, trang lỗi OCR, người thực hiện, lịch sử sửa đổi và liên kết văn bản thay thế. Hash chỉ chứng minh nội dung không đổi so với bản đã hash; nó không chứng minh tài liệu chính thống.

## 4. Đánh giá chất lượng bằng chứng

Không dùng một điểm AI tổng hợp để quyết định độ tin cậy. Quy trình appraisal cần chọn công cụ phù hợp với loại tài liệu:

- Clinical practice guideline: xem phương pháp phát triển, systematic search, panel composition, conflict of interest, external review, applicability và update plan; có thể dùng AGREE II như khung appraisal.
- Systematic review/meta-analysis: xem protocol, search completeness, study selection, risk of bias và certainty; cân nhắc AMSTAR 2/ROBIS.
- Randomized trial: đánh giá risk of bias theo RoB 2.
- Non-randomized intervention: cân nhắc ROBINS-I.
- Diagnostic accuracy: cân nhắc QUADAS-2.
- Recommendation/evidence certainty: ghi rõ hệ thống phân hạng của publisher; nếu tổng hợp theo GRADE thì phải ghi lý do nâng/hạ certainty và không tự chuyển đổi máy móc giữa các hệ thống.

Mỗi claim cần gắn với population, intervention/exposure, comparator (nếu có), outcome, effect estimate/precision (nếu báo cáo), certainty, recommendation strength, source locator và limitations. Không tự tạo effect estimate hoặc certainty khi tài liệu không cung cấp.

AI có thể hỗ trợ trích xuất, phân loại, đối chiếu và phát hiện thiếu sót. AI không được tự chấm điểm cuối cùng, tự xác nhận guideline còn hiệu lực hoặc tự biến claim thành khuyến nghị đã được duyệt.

## 5. Xử lý xung đột bằng chứng

Không chọn tài liệu chỉ vì mới hơn, có trust tier cao hơn hoặc vector similarity lớn hơn.

Khi phát hiện khuyến nghị khác nhau, tạo conflict record và đối chiếu:
1. Jurisdiction và hiệu lực pháp lý.
2. Quần thể, tuổi, thai kỳ, bệnh đồng mắc và mức độ nặng.
3. Mục đích: sàng lọc, chẩn đoán, điều trị, theo dõi hay dự phòng.
4. Phương pháp guideline và chất lượng bằng chứng nền.
5. Ngày tìm kiếm bằng chứng, ngày công bố, cập nhật/withdrawal.
6. Recommendation strength, certainty và lợi ích-nguy cơ.
7. Điều kiện nguồn lực và khả năng áp dụng tại Việt Nam.

Nếu không thể giải quyết chắc chắn, giữ trạng thái UNRESOLVED, hiển thị bất đồng và giới hạn kết luận. Không để LLM tự hòa giải thành một câu trả lời duy nhất.

## 6. Terminology normalization — lớp xuyên suốt

Các hệ thống mã hóa/thuật ngữ không phải kho bằng chứng và không chứng minh hiệu quả điều trị:

- ICD-10/ICD-11: phân loại bệnh tật.
- ATC/DDD: phân loại và thống kê sử dụng thuốc.
- LOINC: xét nghiệm và quan sát lâm sàng.
- SNOMED CT: thuật ngữ lâm sàng có ngữ nghĩa.
- UCUM: đơn vị đo lường.

Phải quản lý version, mapping, provenance và license riêng. Đặc biệt, không triển khai SNOMED CT hoặc tái phân phối dữ liệu có điều kiện trước khi kiểm tra quyền sử dụng theo lãnh thổ và tổ chức.

## 7. Quy trình vòng đời và phê duyệt

1. DISCOVERED — tài liệu vừa được đăng ký.
2. Automated metadata/extraction checks — kiểm tra trường bắt buộc, HTTPS, độ dài và tính toàn vẹn; không xác minh tính đúng.
3. Domain match — lưu ở thuộc tính `source_domain_matched`; không phải trạng thái và không phải xác thực tài liệu.
4. AI_REVIEWED — AI hỗ trợ lập báo cáo/đánh dấu vấn đề; không phải phê duyệt.
5. CLINICAL_APPROVED — chỉ khi reviewer đã xác minh bản gốc, phiên bản hiện hành, quyền sử dụng, bằng chứng và phạm vi.
6. SUPERSEDED/REJECTED — không được dùng làm bằng chứng hiện hành.

Trong code hiện tại, trạng thái mới đăng ký luôn là DISCOVERED. Cột legacy `source_verified` được giữ tương thích nhưng phải false; cột `source_domain_matched` chỉ biểu thị hostname thuộc registry.

Các domain có `required_reviewers = 2` (guideline, specialty, medication, diagnostics) cần hai reviewer độc lập. Reviewer phải có hồ sơ chuyên môn được xác minh ngoài hệ thống; chỉ bật `credential_verified` sau khi tổ chức xác thực giấy phép/chứng chỉ, phạm vi hành nghề và chuyên khoa. Tài khoản `knowledge_admin` không có quyền phê duyệt lâm sàng.

Sau khi tổ chức xác minh độc lập giấy phép/chứng chỉ, quản trị viên có thể cấp quyền bằng SQL (thay các placeholder bằng hồ sơ đã xác minh; không tự đặt `credential_verified=true`):

```sql
insert into public.clinical_knowledge_reviewers
  (user_id, role, specialties, credential_type, credential_identifier,
   credential_verified, credential_verified_at, credential_verified_by, is_active)
values
  ('<REVIEWER_AUTH_UUID>', 'physician', array['cardiology'],
   '<LICENSE_TYPE>', '<VERIFIED_LICENSE_NUMBER>',
   true, now(), '<VERIFYING_ADMIN_AUTH_UUID>', true);
```

Đây là thao tác quản trị có trách nhiệm pháp lý/tổ chức; phần mềm hiện không kết nối cơ quan cấp phép để tự xác minh credential.

Reviewer phải ghi:
- Xác minh bản tài liệu gốc.
- Xác minh phiên bản/hiệu lực hiện hành.
- Xác minh quyền sử dụng/license.
- Evidence assessment, rationale và limitations.
- Approved scope: nhóm người dùng, mục đích, chuyên khoa, jurisdiction và giới hạn.

Phê duyệt document không có nghĩa toàn bộ nội dung document được phép dùng cho mọi tình huống. Claim-level review và clinical synthesis governance vẫn cần hoàn thiện trước khi bật retrieval phục vụ ý kiến lâm sàng.

## 8. API hiện có và thay đổi contract

Tất cả endpoint yêu cầu Supabase Bearer token:

- GET `/clinical-knowledge/sources`
- POST `/clinical-knowledge/documents`
- GET `/clinical-knowledge/documents?status=...`
- GET `/clinical-knowledge/review-queue` (reviewer đã xác minh credential)
- GET `/clinical-knowledge/documents/{id}` (reviewer đã xác minh credential)
- POST `/clinical-knowledge/documents/{id}/review` (reviewer đã xác minh credential)

POST document cần thêm `knowledge_domain`, `jurisdiction`, `target_population`. Review APPROVED cần `source_document_verified`, `version_current`, `license_cleared`, `evidence_assessment` và `scope`. Reviewer đầu tiên của domain cần hai người sẽ để tài liệu ở AI_REVIEWED; reviewer độc lập thứ hai mới có thể chuyển sang CLINICAL_APPROVED.

Cần chạy migration theo thứ tự:
1. `202611240001_clinical_knowledge_governance.sql`
2. `202611240002_evidence_grade_clinical_knowledge.sql`

## 9. Điều kiện trước khi đưa ý kiến dựa trên tri thức

Không bật clinical retrieval hoặc để Companion dùng nội dung như căn cứ cho ý kiến cho đến khi có đủ:

- Ingestion có kiểm soát, bản gốc bất biến, OCR/extraction quality và page-level provenance.
- Document identity, legal status, version/supersession và license verification.
- Claim extraction có source locator; reviewer có thể mở lại đúng trang/bảng/đoạn.
- Evidence appraisal theo đúng loại nghiên cứu/hướng dẫn.
- Conflict detection/resolution và jurisdiction-aware applicability.
- Reviewer credential verification, specialty matching, audit và quy trình tái thẩm định.
- Retrieval chỉ lấy claim/document CLINICAL_APPROVED, đúng scope, đúng thời gian hiệu lực, đúng quần thể và chuyên khoa; mọi câu trả lời phải dẫn nguồn.
- Bộ test retrieval: citation correctness, unsupported-claim rate, stale-source rate, contradiction handling, population mismatch, abstention và adversarial tests.
- Đánh giá độc lập bởi chuyên gia y tế trên bộ tình huống đại diện; đánh giá lại sau mỗi thay đổi lớn.

Khi không đủ bằng chứng, dữ liệu bệnh nhân hoặc chuyên môn để kết luận, hệ thống phải nói rõ giới hạn, hỏi thêm dữ kiện phù hợp hoặc chuyển người có chuyên môn. Không tạo cảm giác chắc chắn giả.

## 10. Trạng thái triển khai trung thực

Đã có nền tảng schema/API, registry khởi tạo, metadata/integrity checks, reviewer workflow, evidence-domain taxonomy, terminology registry, claim/conflict schema và focused unit tests.

Chưa có: crawler/downloader an toàn, OCR pipeline, document/version resolver, claim extraction pipeline, appraisal workflow hoàn chỉnh, xác minh giấy phép reviewer, claim-level approval UI, conflict-resolution UI, vector/hybrid retrieval, citation-grounded Companion integration, evaluation dataset, external clinical validation hoặc production deployment.

Migration chưa tự chạy trên Supabase. Reviewer chưa được xác minh chỉ bằng cách thêm UUID vào bảng. Không có tài liệu nào được tự động xem là clinical-approved từ migration này.
