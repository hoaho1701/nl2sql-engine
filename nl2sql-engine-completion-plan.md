# nl2sql-engine — Kế hoạch hoàn thiện cho portfolio

> File này KHÔNG thay thế `PROGRESS.md` — `PROGRESS.md` vẫn là nguồn sự thật cho chi tiết kỹ thuật từng giai đoạn (0-10), tiếp tục cập nhật Status ở đó như đã quy ước. File này là lớp bổ sung: **những gì cần thêm ngoài 11 giai đoạn đã lên plan** để project sẵn sàng đưa vào CV fresher-junior AI Engineer.

---

## 0. Trạng thái tại thời điểm viết file này (theo `PROGRESS.md`)

- Đang **CHƯA BẮT ĐẦU** Giai đoạn 0 — chặn cứng vì máy code hiện tại (Intel MacBook Pro, macOS 12.7.5) không cài được Docker (`macOS >= 14` required) và Ollama (không còn bottle Intel). Quyết định đã ghi: đợi chuyển hẳn sang M4.
- Phần đã xong: `inspect_data.py`, phần lõi `load_data.py`/`schema_context.py`/`eval_test_set.py` (không cần Postgres thật), `sql_executor._is_select_only`/`_is_single_statement`, `build_messages()`, Pydantic models + CORS ở `api.py`. 27/27 test pass.
- Repo: `https://github.com/hoaho1701/nl2sql-engine` — **Public** (từ 2026-09-22), có `README.md` placeholder.

Đây là điểm quan trọng nhất cần xử lý trước, không phải thêm tính năng gì mới.

---

## 1. Việc cần làm ngay — không phụ thuộc máy M4

Những việc này làm được ngay trên máy Intel hiện tại, trong lúc chờ chuyển máy:

- [x] **Public repo ngay, gắn nhãn `🚧 Work in Progress` ở đầu README/repo description.** ✅ Đã public (2026-09-22).
- [x] **Tự xác nhận lại tên trong `LICENSE`.** ✅ Đã xác nhận "Hồ Quốc Nhân Hoà" từ trước (2026-09-15) — cảnh báo cũ trong `PROGRESS.md` đã dọn.
- [x] **Viết README phiên bản "đang làm dở" (placeholder có cấu trúc).** ✅ Đã viết `README.md` ở gốc repo (2026-09-22) — cập nhật dần khi từng giai đoạn xong, thay hẳn bằng bản chính thức ở Giai đoạn 10.

---

## 2. Bổ sung khi bắt đầu chạy được trên máy mới (song song với các Giai đoạn 3-10 trong `PROGRESS.md`)

Những mục này KHÔNG có trong `PROGRESS.md` hiện tại — cần thêm vào đúng lúc, không phải làm riêng cuối cùng:

- [ ] **Resume bullet draft — chuẩn bị song song lúc code, không đợi xong 100% mới nghĩ.** Nguyên liệu đã có sẵn từ chính các quyết định kỹ thuật đã ghi trong `PROGRESS.md`, ví dụ:
  > *"Built a self-hosted Text-to-SQL system with defense-in-depth SQL safety (3 independent layers: syntax validation, read-only DB role, statement-count parsing); discovered and documented a CTE-based bypass (`WITH x AS (DELETE ... RETURNING *) SELECT * FROM x`) that string-parsing alone cannot catch, mitigated via database-level role restriction."*
  > *"Implemented a self-correction loop achieving [X]% → [Y]% execution accuracy improvement, measured via a leak-free train/eval split and an automated experiment log."*
  Điền số liệu thật khi có (Giai đoạn 7 xong).

- [ ] **Talk-track cho phỏng vấn — 60-90 giây kể lại project, tập trung vào 2-3 quyết định kỹ thuật khó nhất**, không kể lại toàn bộ 11 giai đoạn. Ứng viên nên chọn sẵn (gợi ý dựa trên nội dung đã có trong `PROGRESS.md`):
  1. Vì sao chọn Postgres/RAG thay vì nhồi schema tĩnh — trade-off cụ thể.
  2. Câu chuyện phát hiện lỗ hổng CTE-ghi-dữ-liệu — đây là chi tiết hiếm, đáng kể nhất trong toàn bộ project.
  3. Cách đo execution accuracy bằng `Counter` thay vì so văn bản SQL, và vì sao train/eval phải tách biệt.

- [ ] **GitHub profile README** (`hoaho1701/hoaho1701`) — pin repo này, 1-2 câu elevator pitch trỏ về README chính thức khi xong.

---

## 3. Việc cần làm ở Giai đoạn 10 (đã có plan trong `PROGRESS.md`, chỉ nhắc để không bỏ sót khi ghép vào CV)

Không lặp lại chi tiết — `PROGRESS.md` Giai đoạn 10 đã mô tả đủ (thứ tự viết, "show don't tell", đổi giọng điệu so với PROGRESS.md, credit dataset Olist theo CC BY-NC-SA 4.0). Chỉ thêm 1 điểm chưa có trong `PROGRESS.md`:

- [ ] Sau khi có README chính thức, **cập nhật cả GitHub profile README và trang tổng hợp portfolio** (nếu đã làm ở project khác) trỏ đúng vào link README này — dễ quên bước đồng bộ ngược lại sau khi 1 project xong.

---

## 4. Rủi ro cần theo dõi

- **Rủi ro lớn nhất là thời gian, không phải kỹ thuật**: 8/11 giai đoạn phụ thuộc hoàn toàn vào việc chuyển sang máy M4. **Đã quyết định (2026-09-22): giữ nguyên ràng buộc $0 tuyệt đối, không dùng phương án tốn phí (GitHub Codespaces GPU, thuê GPU cloud theo giờ...) dù bị trễ bao lâu** — đây là ràng buộc xuyên suốt dự án đã đặt ra từ đầu (xem "Mục tiêu sản phẩm" trong `PROGRESS.md`), không đánh đổi lấy tốc độ. Nếu chuyển máy bị trễ nhiều tuần, phương án duy nhất là tiếp tục phần infra-độc-lập còn lại (mục 2 tài liệu học `NL2SQL Build Path`) và đợi, không tìm đường vòng tốn phí.
- **PII/sensitive data trong README** — `PROGRESS.md` đã tự flag câu hỏi mở này (mục "Rủi ro / câu hỏi mở"), cần quyết định trước khi viết README Giai đoạn 10, không phải sau.
