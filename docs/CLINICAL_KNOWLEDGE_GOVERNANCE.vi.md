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
4. AI_REVIEWED — chỉ biểu thị AI hỗ trợ lập báo cáo/đánh dấu vấn đề; không phải phê duyệt.
5. CLINICAL_REVIEW_PENDING_SECOND — reviewer đầu tiên đã ghi nhận đồng ý; cần reviewer độc lập tiếp theo.
6. CLINICAL_APPROVED — chỉ khi đủ reviewer theo domain đã xác minh bản gốc, phiên bản hiện hành, quyền sử dụng, bằng chứng và phạm vi.
7. SUPERSEDED/REJECTED — không được dùng làm bằng chứng hiện hành.

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

Reviewer phải độc lập với người đăng ký tài liệu và khai báo xung đột lợi ích; reviewer có xung đột lợi ích không được phê duyệt.

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

## 10. Pipeline thu thập và lưu bản gốc

Các API mới (yêu cầu Supabase Bearer token):

- `POST /clinical-knowledge/sources/{source_key}/discover`: đọc trang danh mục đã đăng ký và tìm liên kết PDF cùng domain.
- `POST /clinical-knowledge/candidates/{candidate_id}/ingest`: tải PDF, kiểm tra magic bytes, tính SHA-256, lưu private Storage theo content-addressed path và tạo bản ghi trang.
- `GET /clinical-knowledge/documents/{id}/original-url`: tạo signed URL ngắn hạn 5 phút cho reviewer.
- `GET /clinical-knowledge/documents/{id}/pages` và `GET /clinical-knowledge/documents/{id}/page/{page_number}`: xem chẩn đoán trích xuất theo trang.
- `GET /clinical-knowledge/candidates?status=DISCOVERED`: candidate queue cho knowledge_admin.
- `GET /clinical-knowledge/documents/{id}/claims?status=UNREVIEWED`: claim queue cho reviewer.

Chỉ `knowledge_admin` được chạy discovery/ingestion. URL phải là HTTPS, host thuộc source registry, không dùng IP literal, localhost, port khác 443 hoặc redirect ra ngoài allowlist. Mỗi redirect được kiểm tra lại. Kích thước PDF tối đa 25 MB, HTML discovery tối đa 5 MB, tối đa 300 trang. Các giới hạn này là biện pháp giảm rủi ro, không phải sandbox hoàn chỉnh chống mọi kiểu DNS rebinding hoặc tấn công parser.

Original được lưu trong bucket private `clinical-knowledge-originals`, đường dẫn chứa source key và SHA-256, upload dùng `upsert=false`. API không cung cấp chức năng ghi đè hoặc xóa bản gốc. Đây là append-only ở tầng ứng dụng, **không phải WORM/retention lock** chống quản trị viên Supabase có quyền đặc biệt xóa dữ liệu.

Discovery hiện là API được kích hoạt thủ công hoặc bởi scheduler bên ngoài; chưa có crawler scheduler chạy nền. Parser chỉ tìm liên kết PDF trên cùng domain. Không tự suy đoán title, số hiệu, ngày ban hành, phiên bản hay hiệu lực; admin phải cung cấp metadata và reviewer phải xác minh.

## 11. PDF extraction và chất lượng từng trang

`backend/clinical_knowledge_ingestion.py`:
- Trích xuất text theo từng trang bằng pypdf.
- Trang ít text có thể chuyển sang Tesseract OCR tiếng Việt/Anh nếu cài optional packages và binary/traineddata.
- Lưu text hash, phương pháp trích xuất, số ký tự, tỷ lệ alphanumeric, replacement characters, OCR confidence và warning theo từng trang.
- Báo cáo EMPTY/PARTIAL/EXTRACTED; tài liệu PARTIAL không đủ điều kiện phê duyệt.
- Các cảnh báo OCR buộc reviewer xác nhận đã kiểm tra trang gốc trước khi duyệt.

Cài OCR trong môi trường triển khai:
```bash
pip install -r backend/requirements-ocr.txt
```
Đồng thời cài Tesseract OCR binary và dữ liệu ngôn ngữ `vie` + `eng`, cấu hình `TESSERACT_CMD` nếu binary không nằm trong PATH.

Các chỉ số chất lượng chỉ phát hiện dấu hiệu trích xuất kém; không đo độ chính xác y khoa, không bảo đảm OCR đúng và không thay thế kiểm tra PDF gốc. Ảnh, biểu đồ, bảng phức tạp, công thức và layout nhiều cột vẫn cần reviewer đối chiếu.

## 12. Claim extraction, appraisal và review

- `POST /clinical-knowledge/documents/{id}/claims/suggest`: AI tạo tối đa 10 claim draft từ tối đa 3 trang.
- Mỗi draft phải có exact quote khớp nội dung trang sau chuẩn hóa khoảng trắng; quote không khớp bị loại.
- AI draft không được lưu hoặc phê duyệt tự động. Reviewer phải chọn, sửa và tạo claim bằng `POST /clinical-knowledge/documents/{id}/claims`.
- Claim lưu population, intervention, comparator, outcomes, effect estimate (chỉ khi nguồn nêu), certainty, recommendation strength, page number, exact quote và locator.
- `POST /clinical-knowledge/claims/{id}/review`: reviewer thẩm định theo AGREE II, GRADE, AMSTAR 2, RoB 2, ROBINS-I, QUADAS-2 hoặc OTHER; các framework có bộ domain bắt buộc.
- Claim ở trạng thái UNREVIEWED trước review; sau reviewer đầu tiên sẽ là PENDING_SECOND_REVIEW nếu domain yêu cầu hai người. Chỉ ACCEPTED sau đủ reviewer độc lập. Claim chưa ACCEPTED không được retrieval.

AI chỉ hỗ trợ trích xuất. Nó không xác định effect estimate, certainty hoặc recommendation strength khi nguồn không nêu; không tự chuyển nội dung thành khuyến nghị. Việc quote khớp text chỉ chứng minh quote có trong bản trích xuất, không bảo đảm OCR không sai.

## 13. Document identity, version và conflict resolution

- `GET /clinical-knowledge/documents/{id}/version-candidates`: tìm tài liệu có cùng official identifier để reviewer đối chiếu.
- `POST /clinical-knowledge/documents/{id}/version-relations`: ghi nhận quan hệ SUPERSEDES/UPDATE_OF/CORRECTION_OF/TRANSLATION_OF.
- Hai reviewer độc lập phải xác nhận quan hệ trước khi predecessor được đánh dấu SUPERSEDED.
- `POST /clinical-knowledge/conflicts`: tạo conflict từ các claim đã ACCEPTED.
- `GET /clinical-knowledge/conflicts`: xem hàng đợi conflict.
- `POST /clinical-knowledge/conflicts/{id}/review`: hai reviewer độc lập xác nhận giải quyết; nếu có phiếu UNRESOLVED, conflict không được tự động đóng.

Hệ thống chỉ gợi ý ứng viên theo official identifier. Không tự kết luận bản nào mới hơn hoặc văn bản nào có hiệu lực pháp lý. Quyết định thay thế phải dựa trên văn bản chính thức và xác nhận con người.

## 14. Evidence retrieval và Companion

`POST /clinical-knowledge/retrieve` nhận query, jurisdiction, population, scope, specialty và ngày tham chiếu. Kết quả chỉ gồm claim ACCEPTED thuộc document CLINICAL_APPROVED, is_current, đúng thời gian hiệu lực, jurisdiction, population và approved_scope; trả exact quote, trang và URL nguồn. Không có kết quả phù hợp thì trả `abstention=true`.

Retrieval hiện tại là **structured lexical matching**, chưa phải semantic/vector/hybrid retrieval và không đủ để tự hiểu mọi câu hỏi y khoa. Đây là một evidence gateway fail-closed, không phải máy tạo câu trả lời lâm sàng.

Companion `POST /chat` nhận thêm trường tùy chọn `evidence_request`. Khi có request, backend truy xuất bằng chứng đã duyệt, ghi audit và chuyển evidence context vào agent. Prompt yêu cầu agent chỉ dùng claim/citation được cung cấp, không vượt quá scope; khi retrieval rỗng/lỗi thì phải nói rõ không có bằng chứng đã thẩm định và không đưa ra kết luận lâm sàng. Frontend đã có form tùy chọn nhập population, scope và specialty để gửi evidence_request từ Companion chat. Nếu bật mà không có population, UI chặn gửi request.

## 15. Migration order

Các migration phải chạy đúng thứ tự, dùng version duy nhất:

1. `202611240001_core_backend_persistence.sql`
2. `202611240002_healthcare_document_storage.sql`
3. `202611240003_clinical_knowledge_governance.sql`
4. `202611240004_evidence_grade_clinical_knowledge.sql`
5. `202611240005_clinical_knowledge_ingestion_evidence_workflows.sql`
6. `202611240006_clinical_knowledge_independent_resolution.sql`
7. `202611240007_clinical_knowledge_review_state_precision.sql`

Hai migration Clinical Knowledge ban đầu từng bị trùng version với migration core/document storage; đã đổi thành 003 và 004 để tránh xung đột version của Supabase CLI. Không chạy các file cũ có tên 001/002 của Clinical Knowledge nếu chúng còn tồn tại trong bản checkout cũ.

## 16. Trạng thái triển khai trung thực

**Đã có trong branch hiện tại:**
- Source registry, bảy knowledge domains và terminology registry.
- Governance/document APIs, reviewer credential gate, audit, approval scope và fail-closed status.
- Allowlisted official-source discovery, PDF fetch, private original storage theo SHA-256.
- PDF page extraction, optional OCR fallback và page-level quality report.
- AI-assisted claim draft có kiểm tra exact quote; claim appraisal/review API.
- Version candidate/relation workflow với hai reviewer.
- Conflict registry và independent resolution API.
- Structured lexical evidence retrieval và backend Companion evidence-context integration.
- Focused CI cho module governance/ingestion.

**Chưa có hoặc chưa được xác nhận:**
- Migration chưa chạy trên Supabase; backend chưa deploy.
- Chưa có scheduler crawler tự chạy, queue worker bền vững hoặc retry orchestration.
- Chưa có OCR runtime được cài và kiểm thử trên dữ liệu scan thực tế.
- Đã có reviewer/admin console cơ bản trong frontend cho discovery, ingest, document review, claim drafts/appraisal, version relation, conflict resolution và retrieval smoke test; chưa có usability/security review hoặc E2E verification trên môi trường triển khai.
- Chưa có vector/hybrid retrieval, reranker, terminology service tích hợp thực tế.
- Chưa có bộ benchmark lâm sàng đại diện, đánh giá độc lập của chuyên gia y tế hoặc xác nhận an toàn.
- Chưa có tài liệu/claim nào được phê duyệt lâm sàng thực tế.

Không bật clinical decision support cho bệnh nhân chỉ vì các API này tồn tại. Cần hoàn thành migrations, deployment, security review, dữ liệu chính thống, credential verification, reviewer workflow, evaluation và external clinical validation trước khi tuyên bố đạt chuẩn sử dụng lâm sàng.
