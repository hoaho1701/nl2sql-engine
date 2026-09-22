# LOG DỰ ÁN TEXT-TO-SQL — sản phẩm Text-to-SQL kiểu Vanna (tự build, có cải tiến riêng)

> **Cách đọc file này (áp dụng cho cả AI lẫn người, kể cả khi đổi sang box chat/máy khác):**
> 1. File này là **nhật ký trạng thái**, không phải spec cố định — phần "Lộ trình" mô tả kế hoạch, phần "Trạng thái file hiện tại" và cột **Status** trong mỗi giai đoạn mới là sự thật tại thời điểm đọc.
> 2. **Luôn kiểm tra lại thực tế trước khi tin mô tả bên dưới**: đọc trực tiếp code trong `app/`, chạy `docker compose ps`, `ollama list`, `curl` các endpoint liệt kê ở Giai đoạn 0 — máy có thể đã tắt/restart từ lần làm việc trước.
> 3. Khi 1 giai đoạn hoàn tất, **cập nhật Status + ghi lại quyết định/bug đã gặp** ngay trong file này (theo đúng cấu trúc mỗi giai đoạn: Mục tiêu / Khái niệm cần nắm / Tech stack / Việc cần làm / Tại sao) trước khi kết thúc phiên làm việc — đây là cách duy nhất để 1 box chat mới "nối tiếp" được đúng ngữ cảnh.
> 4. Người dùng muốn **tự code**, AI chỉ hướng dẫn/giải thích bản chất, không code hộ toàn bộ trừ khi được yêu cầu rõ ràng ("code hộ", "viết luôn").
> 5. Nếu bạn là 1 box chat mới nhận file này, **hỏi lại người dùng** xem đã hoàn thành đến Giai đoạn mấy trong bảng Lộ trình bên dưới, đừng giả định.
> 6. **Quy ước code trong `app/`/`tests/`**: comment/docstring viết bằng **tiếng Anh**, ngắn gọn, chỉ mô tả hành vi — **không** nhắc số "Giai đoạn N" bên trong code (thông tin đó chỉ nằm ở file này, tránh code bị sai lệch nếu roadmap đánh số lại sau này). File `.md` (PROGRESS.md này) vẫn viết tiếng Việt bình thường — 2 loại tài liệu khác mục đích, không cần đồng nhất ngôn ngữ.
> 7. **Nếu clone repo này lần đầu trên máy mới**: `data/` và `.env` bị `.gitignore` loại, **không có sẵn sau khi clone** — xem mục "Sau khi clone sang máy mới" ngay dưới "Trạng thái file hiện tại" để biết việc cần làm trước khi chạy được gì.

---

## Mục tiêu dự án

Xây **1 sản phẩm Text-to-SQL hoàn chỉnh**, khởi động từ **2026-09-14**, kiến trúc RAG tương tự [vanna-ai/vanna](https://github.com/vanna-ai/vanna) (schema/doc/example SQL nạp vào vector store → retrieve theo câu hỏi → sinh SQL → thực thi → tự sửa lỗi), nhưng **không copy y hệt** — có ít nhất 2-3 điểm khác biệt/cải tiến riêng (xem Giai đoạn 9).

---

## Mục tiêu sản phẩm

**Tầm nhìn**: Một hệ thống Text-to-SQL self-hosted, cho phép người dùng truy vấn dữ liệu bằng ngôn ngữ tự nhiên mà không cần biết SQL — chính xác, an toàn, và tự cải thiện theo thời gian sử dụng.

**Luồng xử lý cốt lõi**:
1. Người dùng đặt câu hỏi bằng ngôn ngữ tự nhiên.
2. Hệ thống retrieve schema và ví dụ SQL liên quan từ vector store (RAG).
3. LLM sinh câu SQL dựa trên context đã retrieve.
4. SQL được thực thi an toàn trên Postgres (nhiều lớp phòng thủ độc lập).
5. Nếu thực thi lỗi, hệ thống tự động gửi lỗi cho LLM sửa và thử lại (bounded retry) trước khi báo lỗi cho người dùng.
6. Trả về kết quả kèm giải thích bằng ngôn ngữ tự nhiên.

**Yêu cầu bắt buộc**:
- Toàn bộ tech stack và dịch vụ phải **miễn phí ($0), self-hosted, không giới hạn số lần gọi** — không dùng cloud API trả phí hoặc free-tier giới hạn (xem "Quyết định tech stack" ở Giai đoạn 0).
- Có tối thiểu 2-3 tính năng khác biệt so với vanna mặc định (xem Giai đoạn 9) — sản phẩm này không phải bản copy.
- Train set (dữ liệu nạp vào vector store) và eval set (đo độ chính xác) phải tách biệt hoàn toàn, không rò rỉ dữ liệu giữa hai bên.
- **Thể hiện rõ năng lực MLOps + backend + frontend**, không chỉ thuần AI/RAG — lý do: mục tiêu nghề nghiệp là portfolio phục vụ xin việc, phạm vi rộng hơn 1 vai trò AI/LLM engineer thuần tuý. Cụ thể: CI pipeline tự động (Giai đoạn 8), experiment log có số liệu theo thời gian (Giai đoạn 7), dashboard observability (Giai đoạn 9), API backend chuẩn REST (Giai đoạn 8), UI React tối giản nhưng thật (Giai đoạn 8) — đây là lý do Docker/Postgres/React KHÔNG bị cắt bớt dù tốn thời gian hơn SQLite/Streamlit.

## Lộ trình tổng thể (11 giai đoạn, đánh số 0-10)

Status dùng 1 trong 3 giá trị: **CHƯA BẮT ĐẦU** / **ĐANG LÀM** / **XONG**. Cột "Cập nhật lần cuối" ghi ngày (YYYY-MM-DD) mỗi khi Status đổi — giúp phát hiện nhanh nếu hạ tầng/quyết định đã lâu không đụng tới (vd Docker/Ollama có thể đã tắt từ lâu). Cột "Ước tính effort" là số giờ làm việc tập trung (không tính thời gian chờ đợi/nghiên cứu ngoài lề) — chỉ để có 1 mốc tham khảo thô, không phải cam kết cứng; cập nhật lại nếu thực tế lệch nhiều.

| # | Giai đoạn | Status | Cập nhật lần cuối | Ước tính effort |
|---|---|---|---|---|
| 0 | Môi trường & hạ tầng (Docker, Postgres, Ollama, Chroma) | **CHƯA BẮT ĐẦU** | — | 2-4h |
| 1 | Nền dữ liệu (tải + load Olist → Postgres, FK thật) | **ĐANG LÀM** | 2026-09-14 | 4-6h |
| 2 | Schema metadata layer (DDL + mô tả + quan hệ + cảnh báo bẫy) | **ĐANG LÀM** | 2026-09-14 | 3-5h |
| 3 | Vector store & training data cho RAG (Chroma + embedding) | CHƯA BẮT ĐẦU | — | 4-6h |
| 4 | Tích hợp LLM với RAG prompt động (Ollama) | CHƯA BẮT ĐẦU | — | 4-6h |
| 5 | Thực thi SQL an toàn trên Postgres | CHƯA BẮT ĐẦU | — | 4-6h |
| 6 | Vòng tự sửa lỗi (self-correction loop) | CHƯA BẮT ĐẦU | — | 2-3h |
| 7 | Đánh giá độ chính xác (train/eval set tách biệt, experiment log) | CHƯA BẮT ĐẦU | — | 4-6h |
| 8 | Đóng gói: FastAPI + React + docker-compose + CI/CD | CHƯA BẮT ĐẦU | — | 8-12h |
| 9 | Khác biệt hoá AI + MLOps observability (so với vanna gốc) | CHƯA BẮT ĐẦU | — | 6-10h |
| 10 | README & case-study cho recruiter | CHƯA BẮT ĐẦU | — | 2-4h |

**Tổng ước tính**: ~43-68 giờ làm việc tập trung — tương đương khoảng 1-2 tuần nếu làm full-time, hoặc 4-8 tuần nếu làm buổi tối/cuối tuần. Không tính thời gian chờ máy M4 sẵn sàng (Giai đoạn 0 đang hoãn) hay thời gian debug phát sinh ngoài dự kiến.

**⏸️ Quyết định (2026-09-15): tạm dừng làm việc trên máy Intel này, đợi chuyển hẳn sang M4.** Đây là điểm dừng có chủ đích, không phải bị chặn hoàn toàn — vẫn còn vài việc infra-độc-lập có thể làm nếu muốn tiếp tục trước khi có M4 (xem danh sách "Còn làm được nhưng chưa làm" ngay dưới), nhưng người dùng chọn dừng ở đây.

**Bước tiếp theo cần làm ngay khi có M4**: Giai đoạn 0 (cài Docker + Ollama + Chroma — verify lại từ đầu bằng `sw_vers`/`sysctl -n machdep.cpu.brand_string`/`hostname`, đừng giả định đã đổi máy chỉ vì file này nói vậy). Sau đó: Giai đoạn 1 load data thật vào Postgres, rồi chạy thử ngay 18 `gold_sql` trong `app/eval_test_set.py` qua `psycopg2` thật để xác nhận không có lỗi cú pháp Postgres nào (pandas lúc trước chỉ verify được logic/con số, không bắt được lỗi cú pháp SQL).

**Còn làm được nhưng chưa làm (không bắt buộc, tự quyết định khi quay lại)**:
- `app/evaluate.py` và `app/self_correct.py`: viết luồng xử lý + test bằng cách giả lập (mock) `generate_sql`/`run_sql_safe` — không cần hạ tầng, nhưng đã chủ động hoãn (không phải bị chặn).
- `app/vector_store.py`: chưa xác minh được liệu phần cơ chế Chroma (tạo client/collection/add/retrieve) có chạy local hoàn toàn không cần Ollama hay không — chưa cài `chromadb` để test thử.
- `.github/workflows/ci.yml`: có thể viết bản nháp, nhưng không verify chạy thật được vì repo chưa có remote GitHub.

**Trạng thái cuối phiên (2026-09-15)**: 27/27 test pass (`pytest tests/ -v`), git sạch (`git status` clean sau mỗi commit), toàn bộ tiến độ đã ghi chi tiết trong bảng "Trạng thái file hiện tại" bên dưới.

**Repo đã lên GitHub**: `https://github.com/hoaho1701/nl2sql-engine` — đã chuyển sang **Public** từ 2026-09-22 (sớm hơn kế hoạch ban đầu "đợi hoàn chỉnh mới public" — quyết định đổi: public sớm kèm nhãn "Work in Progress" trong README, coi việc build công khai như 1 tín hiệu tích cực thay vì rủi ro, xem `nl2sql-engine-completion-plan.md`). Tên repo cố ý khác tên thư mục local (`text2sql`) — xem lý do ở phần lịch sử trò chuyện, không phải nhầm lẫn. **Trên máy M4, `git clone https://github.com/hoaho1701/nl2sql-engine.git` sẽ tự ra thư mục tên `nl2sql-engine/`** (không phải `text2sql`), khớp đúng tên repo — bình thường, không phải lỗi.

---

## Rủi ro / câu hỏi mở

Các điểm chưa chốt, cần quyết định trong lúc làm chứ không đoán trước — cập nhật/xoá khi đã có câu trả lời:

- **⚠️ Giai đoạn 0 KHÔNG cài được trên máy đang code hiện tại — đã tự kiểm chứng, không phải chưa thử đúng cách.** Máy đang dùng (kiểm tra 2026-09-14): Intel MacBook Pro cũ, macOS 12.7.5 (Monterey), i7-4770HQ, 16GB RAM, hostname `Hoas-MacBook-Pro-2.local` — KHÔNG phải Mac Mini M4. Đã tự verify 2 điểm chặn cứng:
  - `brew info --cask docker` và `brew info --cask orbstack` đều báo `Required: macOS >= 14` — máy đang macOS 12.7.5, **bị chặn cứng**, không phải vấn đề tốc độ.
  - `brew info ollama` (xem trực tiếp bottle list trong formula) chỉ có bottle cho `arm64` (Apple Silicon) + Linux, không còn bottle Intel macOS nào — cài được về kỹ thuật nhưng phải build from source (`cmake`+`go`), rủi ro lặp lại treo nhiều giờ như lần trước.
  - **Quyết định (2026-09-14)**: đợi chuyển hẳn sang M4, không cố cài trên máy Intel này, không dùng fallback SQLite/llama.cpp tạm thời. Trong lúc chờ, chỉ làm phần việc không cần hạ tầng (xem "Bước tiếp theo cần làm ngay").
  - **Trước khi thử lại Giai đoạn 0 ở phiên sau**: verify lại máy đang dùng bằng `sw_vers` + `sysctl -n machdep.cpu.brand_string` + `hostname` — đừng giả định đã chuyển sang M4 chỉ vì PROGRESS.md nói vậy, và đừng giả định 2 điểm chặn cứng trên đã hết hiệu lực mà không tự kiểm tra lại (`brew info --cask docker`, `brew info ollama`).
- **Size model Ollama phù hợp RAM máy** (`qwen2.5-coder:7b` vs `14b`/`32b`) — chưa xác định, cần đo ở Giai đoạn 0 bước 3 (`sysctl hw.memsize`) rồi thử tốc độ thật trước khi chốt.
- **Version cụ thể của Postgres/Ollama/ChromaDB/psycopg2/sqlparse** — chưa chốt, xem bảng "Version cụ thể đã cài" ở Giai đoạn 0, điền khi cài xong.
- **`statement_timeout` mặc định cho Postgres** — con số hợp lý (vd 5s) là kinh nghiệm chung, chưa benchmark trên chính dữ liệu Olist + query 3-4 bảng JOIN thật; nên đo ở Giai đoạn 5/7 rồi mới chốt.
- **Số lượng ví dụ (question, SQL) cần cho RAG training set** — 15-20 case chỉ là điểm khởi đầu ở Giai đoạn 3, có thể cần nhiều hơn tuỳ vào accuracy đo được ở Giai đoạn 7.
- **Dữ liệu nhạy cảm/PII trong kết quả SQL** — guardrail hiện tại (Giai đoạn 9 Nhóm A #1) chỉ xử lý bẫy fan-out/NULL, KHÔNG chặn 1 câu SELECT hợp lệ về cú pháp nhưng trả về dữ liệu nhạy cảm (vd `SELECT customer_unique_id, customer_city FROM customers` lộ thông tin định danh). Với dataset Olist là dữ liệu công khai/ẩn danh hoá sẵn nên rủi ro thực tế thấp, nhưng nếu muốn câu chuyện "an toàn" trong README (Giai đoạn 10) thuyết phục hơn khi bị hỏi xoáy lúc phỏng vấn, cần quyết định: (a) bỏ qua vì dataset không có PII thật, ghi rõ giả định này trong README, hoặc (b) thêm 1 danh sách cột nhạy cảm bị chặn/ẩn ở tầng `sql_executor.py`. Chưa quyết — quyết định trước khi viết README ở Giai đoạn 10.

---

## Sau khi clone sang máy mới (vd chuyển sang M4)

`git clone`/`git pull` **không** mang theo mọi thứ — 2 phần bị `.gitignore` loại có chủ đích, phải tự làm lại thủ công trước khi chạy được gì:

1. **`data/`** (gồm `data/raw/*.csv` — 9 file CSV Olist) — **không có sau khi clone**. Tải lại từ Kaggle: `olistbr/brazilian-ecommerce` (xem license CC BY-NC-SA 4.0 đã ghi ở Giai đoạn 10), giải nén đúng vào `data/raw/`.
2. **`.env`** — không có sau khi clone (đúng chủ đích, không commit secret). Copy từ `.env.example` (`cp .env.example .env`), tự điền giá trị thật (password Postgres, v.v — xem nội dung `.env.example` để biết cần điền gì).

Sau 2 bước trên mới bắt đầu Giai đoạn 0 như bình thường. `__pycache__/`, `.pytest_cache/` cũng bị loại nhưng không cần làm gì — chúng tự sinh lại khi chạy code/test, không ảnh hưởng gì.

---

## Trạng thái file hiện tại (thư mục `/Users/hoaho/Study/Code/text2sql`)

Git đã init (`git init`, nhiều commit) — mọi thay đổi từ đây có thể hoàn tác qua git. Toàn bộ file `.py` bên dưới là **skeleton hoặc một phần** (xem chi tiết Status từng file) — theo đúng tinh thần "tự code, AI chỉ hướng dẫn". **Danh sách dưới đây mô tả đúng máy đang code hiện tại (Intel, 2026-09-15) — nếu đọc từ máy khác sau khi clone, xem mục "Sau khi clone sang máy mới" ở trên trước.**

```
data/raw/*.csv                  [ĐÃ CÓ trên máy này] 9 file CSV Olist — GITIGNORED, KHÔNG có sau khi clone máy khác, xem "Sau khi clone sang máy mới"
.env / .env.example             [ĐÃ TẠO trên máy này] .env GITIGNORED (KHÔNG có sau khi clone), .env.example làm template (CÓ theo git)
.gitignore                      [ĐÃ TẠO]
requirements.txt                [ĐÃ TẠO]   liệt kê dep theo từng giai đoạn
docker-compose.yml       [ĐÃ CÓ]    Postgres 17 + named volume, đã sửa dùng env_file thay vì hard-code
app/__init__.py          [ĐÃ TẠO]   trống, chỉ để app/ là 1 package Python thật
app/inspect_data.py      [XONG]     Giai đoạn 1 — verify: order_status 8 enum, payment_type 5, review_score 5, geolocation_zip_code_prefix 19,015 unique/1,000,163 dòng (bẫy fan-out xác nhận)
app/load_data.py         [MỘT PHẦN] Giai đoạn 1 — TABLE_NAME_MAP + DATE_COLUMN_BY_TABLE đã điền và verify; get_engine/create_schema/load_csv_to_table/verify_row_counts/main còn NotImplementedError, TẠM HOÃN vì cần Postgres thật để viết+test có ý nghĩa
app/schema_context.py    [MỘT PHẦN] Giai đoạn 2 — TABLE_DESCRIPTIONS (9 bảng)/NON_UNIQUE_PARENT_KEYS/NULLABLE_CHILD_KEYS/build_documentation_chunks() đã viết+verify (11 chunks); generate_ddl(engine) còn NotImplementedError, TẠM HOÃN vì cần Postgres
app/vector_store.py      [SKELETON] Giai đoạn 3
app/build_prompt.py      [MỘT PHẦN] Giai đoạn 4 — build_messages() đã viết + tự test bằng context giả (2 messages: system chứa context, user chứa câu hỏi); ⚠️ đơn giản hoá tạm thời — hiện nhồi cả DDL/doc/few-shot examples chung 1 khối vào system message vì vector_store.retrieve() (Giai đoạn 3) chưa xây nên chưa tách riêng được few-shot ra user message như ghi chú "đặt gần câu hỏi thật" ở Giai đoạn 4 — cần xem lại khi Giai đoạn 3 xong
app/llm_sql.py           [SKELETON] Giai đoạn 4
app/sql_executor.py      [MỘT PHẦN] Giai đoạn 5 — _is_select_only() (chấp nhận cả CTE `with`) + _is_single_statement() (lớp 1 & 3) đã viết; lớp 2 (role read-only) + run_sql_safe() còn NotImplementedError, TẠM HOÃN vì cần Postgres thật — xem cảnh báo CTE-ghi-dữ-liệu ở Giai đoạn 5
app/self_correct.py      [SKELETON] Giai đoạn 6
app/eval_test_set.py     [MỘT PHẦN] Giai đoạn 7 — 18 case (question, gold_sql) đã viết, phủ đủ 12 dạng câu hỏi trong checklist; đã tự verify bằng pandas cho các case phức tạp (top category, top seller, HAVING, date comparison, fan-out dedup, 3+ table join) trước khi ghi làm đáp án — CHƯA chạy thử qua Postgres thật (cần hạ tầng)
app/evaluate.py          [MỘT PHẦN] Giai đoạn 7 — normalize_result() đã viết + tự test (4/4 case, gồm cả case biên rows=[] và Counter giữ đúng số lần lặp thay vì gộp như set); evaluate() còn NotImplementedError, TẠM HOÃN vì cần Ollama/Postgres thật
app/api.py               [MỘT PHẦN] Giai đoạn 8 — CORSMiddleware + QueryRequest/QueryResponse (Pydantic) đã viết + test (3/3 pass qua fastapi.testclient.TestClient, không cần server thật); endpoint POST /query còn thiếu vì cần self_correct.answer_question (TẠM HOÃN, cần Postgres/Ollama)
frontend/                [CHƯA TẠO] Giai đoạn 8 — tạo bằng công cụ React khi tới lúc, không scaffold tay
tests/__init__.py           [ĐÃ TẠO] trống — giúp `pytest` dò ngược lên gốc repo để tìm package `app/`, đồng nhất cách làm với `app/__init__.py` (thay cho `pytest.ini` đã thử trước đó, đã xoá vì dư thừa)
tests/test_sql_executor.py [XONG] Giai đoạn 8 — 13 test cho _is_select_only/_is_single_statement, 13/13 pass, gồm test khoá lại giới hạn CTE-ghi-dữ-liệu và 2 test chống nới lỏng nhầm (EXPLAIN ANALYZE, CALL). Chạy bằng `pytest tests/ -v` từ thư mục gốc — KHÔNG chạy trực tiếp bằng `python tests/test_x.py`
tests/test_evaluate.py     [XONG] Giai đoạn 8 — 6 test cho normalize_result(), 6/6 pass
tests/test_build_prompt.py [XONG] Giai đoạn 8 — 5 test cho build_messages(), 5/5 pass
tests/test_api.py          [XONG] Giai đoạn 8 — 3 test cho QueryRequest/QueryResponse/CORS qua TestClient, 3/3 pass
--- Tổng: 27/27 test pass (`pytest tests/ -v`) — cả 3 mục trong danh sách "còn làm được gì" (tests/, LICENSE, api.py Pydantic+CORS) đã hoàn tất ---
.github/workflows/ci.yml [CHƯA TẠO] Giai đoạn 8 — lint + pytest + docker compose build, tự động mỗi lần push
results/eval_log.csv     [CHƯA TẠO] Giai đoạn 7 — experiment log, mỗi lần chạy evaluate.py append 1 dòng; nguồn dữ liệu cho dashboard Giai đoạn 9
README.md                [CHƯA TẠO] Giai đoạn 10 — viết SAU CÙNG, cần số liệu + demo thật, không dịch PROGRESS.md
LICENSE                  [XONG] Giai đoạn 10 — MIT, tên "Hồ Quốc Nhân Hoà" — đã tự sửa và xác nhận trực tiếp (2026-09-15), không còn là cảnh báo mở
README.md                [MỘT PHẦN] Giai đoạn 10 — bản placeholder (2026-09-22), viết SỚM hơn kế hoạch vì repo đã public khi chưa hoàn chỉnh; sẽ thay hẳn bằng bản chính thức (elevator pitch → demo → số liệu → kiến trúc → khác biệt vanna) khi có đủ dữ liệu thật
nl2sql-engine-completion-plan.md [XONG] Lớp bổ sung ngoài 11 giai đoạn — resume bullet draft, talk-track phỏng vấn, theo dõi rủi ro thời gian (không đánh đổi ràng buộc $0)
```

---

## Giai đoạn 0 — Môi trường & hạ tầng

**Mục tiêu**: có Postgres (Docker), Ollama (native, GPU), ChromaDB (thư viện Python) chạy và verify được trên M4, trước khi viết bất kỳ dòng code nghiệp vụ nào.

**Máy: Mac Mini M4** (Apple Silicon) — có GPU Metal dùng được cho suy luận LLM, chạy Docker Desktop ổn định — tech stack cho toàn dự án được chọn theo đúng khả năng thật của máy này.

### Quyết định tech stack & lý do chọn

| Thành phần | Lựa chọn | Lý do chọn |
|---|---|---|
| Database | **PostgreSQL qua Docker** | Có FK thật, role/permission thật, `statement_timeout` native, exception hierarchy rõ ràng (phân biệt lỗi timeout với lỗi cú pháp/tham chiếu sai) — sát với DB thật ngoài production hơn SQLite, và vanna vốn nhắm tới các DB thật (Postgres/BigQuery/Snowflake...). M4 chạy Docker Desktop ổn định nên không có lý do né Docker |
| LLM server | **Ollama** (GPU Metal tự động) | M4 có GPU Apple Silicon dùng được cho suy luận LLM; Ollama cài đặt bằng 1 lệnh (`brew install ollama`), expose API tương thích chuẩn OpenAI; tốc độ đủ nhanh để hỗ trợ vòng tự sửa lỗi (Giai đoạn 6) — vốn cần gọi LLM nhiều lần cho 1 câu hỏi |
| Cách đưa schema vào prompt | **RAG qua vector store** (Chroma) — chỉ retrieve phần liên quan | Khác biệt kiến trúc cốt lõi so với cách "nhồi cứng toàn bộ schema vào mỗi prompt": prompt ngắn hơn, scale tốt khi schema lớn, few-shot ví dụ thật thường hiệu quả hơn mô tả suông cho các case khó (bẫy fan-out, nhầm SUM/COUNT...) |
| Vector store / embedding | **ChromaDB** (local, embedded) + **Ollama embedding model** (`nomic-embed-text`) | Cả hai miễn phí, chạy local, không cần server riêng ngoài Ollama |
| Đóng gói | **FastAPI + React + docker-compose** | Kiến trúc chuẩn tách backend/frontend, chạy được thật vì máy hỗ trợ Docker |

Mọi lựa chọn trên đều tuân thủ ràng buộc xuyên suốt dự án: **miễn phí ($0), self-hosted, không giới hạn số lần gọi** (xem "Mục tiêu sản phẩm" ở đầu file).

**Khái niệm cần nắm trước khi làm**
- Docker Desktop trên Apple Silicon chạy container bên trong 1 VM Linux nhẹ (qua Apple Virtualization Framework) — đây là lý do quan trọng: **container trong Docker Desktop trên Mac KHÔNG pass-through được GPU (Metal)** cho compute. Nghĩa là nếu chạy Ollama bên trong Docker, nó sẽ chạy CPU-only, mất hết lợi ích của máy có GPU → **Ollama phải chạy native trên macOS** (qua brew/app), CHỈ Postgres (workload không cần GPU) mới nên nằm trong Docker.
- Ollama là 1 server quản lý model local, expose 2 kiểu API trên cổng mặc định `11434`: API gốc (`/api/generate`, `/api/embeddings`) và **API tương thích OpenAI** (`/v1/chat/completions`, `/v1/embeddings`) — dùng được thẳng SDK `openai` của Python, chỉ cần trỏ `base_url` thành `http://localhost:11434/v1`.
- `ollama pull <model>` tải model về local 1 lần, chạy được offline mãi mãi, không giới hạn số lần gọi — giữ đúng tinh thần $0 xuyên suốt dự án.
- Cần 2 loại model khác nhau: 1 model **sinh text/code** (cho SQL) và 1 model **embedding** riêng (cho vector store ở Giai đoạn 3) — 2 việc khác bản chất, không dùng chung 1 model.
- Docker volume: nếu không đặt tên volume rõ ràng trong `docker-compose.yml`, data Postgres có thể mất khi container bị xoá (`docker compose down -v` hoặc rebuild) — cần volume dạng named (`postgres_data:`), không phải anonymous.
- ChromaDB là vector database **embedded** (giống triết lý SQLite nhưng cho vector) — chạy thẳng trong process Python qua `PersistentClient(path=...)`, ghi dữ liệu xuống 1 thư mục local, KHÔNG cần chạy server riêng, KHÔNG cần Docker.

**Tech stack giai đoạn này**: Docker Desktop (hoặc OrbStack — cũng free, nhẹ hơn, tương thích docker-compose), Ollama, PostgreSQL 16 (Docker image chính chủ `postgres:16`), ChromaDB (`pip install chromadb`).

**Việc cần làm**
1. Cài Docker Desktop hoặc OrbStack.
2. Cài Ollama: `brew install ollama` (trên M4 sẽ có sẵn bottle arm64, cài nhanh, không cần build từ source) hoặc tải `.app` trực tiếp.
3. Kiểm tra RAM thật của máy (`sysctl hw.memsize`) trước khi chọn kích cỡ model — model càng lớn càng chính xác nhưng cần nhiều RAM để chạy mượt trên GPU tích hợp (unified memory M4 dùng chung cho cả hệ thống lẫn model).
4. `ollama pull qwen2.5-coder:7b` (hoặc bản lớn hơn `14b`/`32b` nếu RAM cho phép — tự cân nhắc, đừng vội chọn bản lớn nhất) — model sinh SQL.
5. `ollama pull nomic-embed-text` — model embedding cho Giai đoạn 3.
6. `docker-compose.yml`, `.env`/`.env.example`, `.gitignore`, `requirements.txt` **đã scaffold sẵn** (Postgres 17, named volume, biến môi trường qua `env_file`) — chỉ cần rà lại giá trị trong `.env` trước khi chạy thật (đổi password mặc định nếu cần).
7. `pip install -r requirements.txt`.
8. **Verify cả 3** trước khi qua giai đoạn sau:
   - `docker compose up -d` rồi `docker compose ps` → container Postgres `healthy`.
   - `curl http://localhost:11434/api/tags` → liệt kê đúng 2 model đã pull.
   - Test nhanh 1 đoạn Python `chromadb.PersistentClient(path="./chroma_data")` không lỗi, tạo thử 1 collection rỗng.
9. **Điền bảng "Version cụ thể đã cài" bên dưới** — chốt version ngay khi cài xong, đừng để chung chung, tránh môi trường "trôi" giữa các lần chạy lại trên cùng máy.

**Version cụ thể đã cài** (điền khi hoàn tất bước 1-7, để trống là chưa chốt):

| Thành phần | Version đã cài |
|---|---|
| Docker Desktop / OrbStack | *(điền)* |
| PostgreSQL (image tag, vd `postgres:16.x`) | *(điền)* |
| Ollama | *(điền)* |
| Model sinh SQL (tag chính xác đã `pull`) | *(điền)* |
| Model embedding (tag chính xác đã `pull`) | *(điền)* |
| `chromadb` (`pip show chromadb`) | *(điền)* |
| `psycopg2-binary` | *(điền)* |

**Tại sao làm theo thứ tự này**: nếu bỏ qua bước verify mà đi thẳng vào code nghiệp vụ, khi gặp lỗi sẽ không biết là lỗi code hay lỗi hạ tầng chưa chạy — luôn verify hạ tầng trước, tránh mất thời gian debug nhầm chỗ.

---

## Giai đoạn 1 — Nền dữ liệu (Postgres)

**Mục tiêu**: tải dữ liệu Olist và load vào Postgres, có FK thật ngay từ đầu (SQLite không tiện thêm FK sau khi đã tạo bảng, nên nếu dùng SQLite sẽ phải mô phỏng quan hệ bằng text tay — đây cũng là 1 lý do chọn Postgres từ đầu).

**Khái niệm cần nắm trước khi code**
- `engine` không phải "1 kết nối đang mở" — là 1 nhà máy quản lý kết nối, gồm 3 phần: **dialect** (dịch khác biệt cú pháp/quy tắc giữa các loại DB), **DBAPI driver** (thư viện Python cấp thấp thực sự nói chuyện với DB — với Postgres là `psycopg2`, cần cài riêng qua `psycopg2-binary`), và **connection pool** (tái sử dụng kết nối, tránh mở mới tốn kém mỗi lần query). `create_engine("postgresql+psycopg2://user:password@localhost:5432/dbname")` chỉ parse URL và cấu hình sẵn `Engine`, KHÔNG mở kết nối ngay (lazy) — kết nối thật chỉ xảy ra ở lần đầu dùng nó.
- **Khác biệt kiểu dữ liệu quan trọng**: Postgres **kiểm tra kiểu nghiêm ngặt thật sự** — nếu cột ngày tháng chưa convert đúng sang `datetime` Python trước khi `to_sql`, Postgres sẽ **raise lỗi rõ ràng** (an toàn hơn SQLite, vốn khá lỏng lẻo về kiểu cột và có thể âm thầm chấp nhận sai kiểu).
- Đoán cột ngày tháng qua từ khoá tên cột (`"date"`, `"timestamp"`) là cách làm rủi ro: false negative (cột đúng là ngày nhưng tên không chứa từ khoá, vd `order_approved_at`) và false positive (tên chứa từ khoá nhưng không phải ngày) đều có thể xảy ra — khai báo tường minh (hard-code mapping từng cột) an toàn hơn dù tốn công hơn.
- FK thật trong Postgres: khai báo qua `REFERENCES other_table(column)` khi `CREATE TABLE` — đòi hỏi **thứ tự tạo bảng đúng** (bảng cha trước bảng con).
- Chiến lược nạp dữ liệu: KHÔNG nên để `df.to_sql(..., if_exists="replace")` tự suy kiểu VÀ tự tạo bảng — pandas suy kiểu từ dtype của DataFrame thường ra kiểu quá rộng (vd mọi số nguyên thành `BIGINT`) và không tạo FK. Nên tách 2 bước: (a) tự viết DDL thật có FK trước, (b) dùng `to_sql(..., if_exists="append")` chỉ để nạp dữ liệu vào bảng đã có cấu trúc sẵn.
- Cẩn thận "silent failure": 1 lỗi gõ nhầm key trong dict map (vd map tên file CSV → tên bảng) không raise exception, chỉ âm thầm khiến 1 bảng bị bỏ qua — nguy hiểm hơn lỗi crash rõ ràng vì không ai biết để sửa; luôn tự đếm lại số bảng/số dòng sau khi load để phát hiện sớm.
- Cẩn thận khi đếm dòng CSV bằng `wc -l`: lệnh này đếm dựa trên ký tự `\n`, không hiểu quy tắc quote của CSV — 1 field chứa xuống dòng hợp lệ nằm trong dấu ngoặc kép (dataset Olist có trường hợp này ở cột `review_comment_message`) sẽ làm số dòng đếm được sai lệch so với số bản ghi thật; dùng `len(df)` của pandas để đếm chính xác thay vì `wc -l`.

**Tech stack**: PostgreSQL 16, SQLAlchemy, `psycopg2-binary`, pandas (đọc CSV).

**Việc cần làm**
- Tải bộ dữ liệu Olist (Kaggle: `olistbr/brazilian-ecommerce`, 9 file CSV: `customers`, `geolocation`, `order_items`, `order_payments`, `order_reviews`, `orders`, `products`, `sellers`, `product_category_name_translation`) về `data/raw/`.
- Viết 1 script khám phá dữ liệu trước khi load (dtype mỗi cột, cardinality, tỉ lệ NULL, vài dòng mẫu) — mục đích: tự phát hiện cột nào là ngày tháng, cột nào là enum, thay vì đoán.
- Viết `load_data.py`: `TABLE_NAME_MAP` (map tên file CSV → tên bảng), `DATE_COLUMN_BY_TABLE` (khai tường minh cột ngày tháng theo từng bảng, dựa trên bước khám phá ở trên).
- Viết DDL thật cho 9 bảng, khai FK theo đúng 9 quan hệ thật giữa các bảng Olist: `orders.customer_id → customers.customer_id`; `order_items.order_id → orders.order_id`; `order_items.product_id → products.product_id`; `order_items.seller_id → sellers.seller_id`; `order_payments.order_id → orders.order_id`; `order_reviews.order_id → orders.order_id`; `products.product_category_name → product_category_name_translation.product_category_name`; `customers.customer_zip_code_prefix → geolocation.geolocation_zip_code_prefix`; `sellers.seller_zip_code_prefix → geolocation.geolocation_zip_code_prefix` (2 quan hệ cuối qua zip code — lưu ý ngay từ đây: bảng `geolocation` **không unique** theo zip code, sẽ cần cảnh báo fan-out ở Giai đoạn 2).
- Xác định đúng thứ tự tạo bảng theo phụ thuộc FK (bảng không có FK trỏ ra ngoài tạo trước).
- Load toàn bộ 9 CSV vào Postgres, verify số dòng khớp CSV gốc bằng `len(df)`.

**Tại sao nên làm vậy**: FK thật giúp Giai đoạn 2 (schema metadata) tự động phát hiện quan hệ qua `inspector.get_foreign_keys()` thay vì phải tự gõ tay từng quan hệ — giảm hẳn rủi ro typo.

---

## Giai đoạn 2 — Schema metadata layer

**Mục tiêu**: sinh ra "tri thức về schema" ở dạng có thể nạp vào vector store — không phải để nhồi thẳng vào 1 prompt tĩnh, mà là **nguyên liệu thô** cho Giai đoạn 3.

**Khái niệm cần nắm trước khi code**
- `inspect(engine)` trả về 1 object `Inspector` — chuyên đọc **metadata** (tên bảng, tên cột, kiểu dữ liệu), không đọc dữ liệu thật; hoạt động **cross-dialect** (code gọi ra giữ nguyên dù backend là Postgres hay DB khác sau này). `.get_foreign_keys(table_name)` trả về FK **thật** đọc từ Postgres — không cần tự khai tay quan hệ cho các FK đã tạo ở Giai đoạn 1.
- Vẫn cần phần **không thể tự động hoá**: ý nghĩa nghiệp vụ của enum, cảnh báo bẫy dữ liệu — đây là tri thức "đọc data thật mới biết", không nằm trong metadata DB, phải tự khám phá bằng cách query trực tiếp dữ liệu thật (vd qua script khám phá ở Giai đoạn 1) rồi viết lại thành mô tả.
- **"Fan-out" khi JOIN qua cột không unique**: 1 dòng ở bảng cha khớp với nhiều dòng ở bảng con — nếu không dedupe trước, các phép `COUNT`/`SUM` phía trên JOIN sẽ bị nhân lên sai so với thực tế. Trên dataset Olist, cần tự kiểm tra và xác nhận: `geolocation.geolocation_zip_code_prefix` không unique (rất nhiều dòng geolocation ứng với cùng 1 zip code) — JOIN qua cột này mà không dedupe sẽ cho kết quả sai.
- **INNER JOIN với cột có thể NULL** sẽ âm thầm loại bỏ các dòng có giá trị NULL ở cột đó — đúng ngữ nghĩa SQL, không phải lỗi, nhưng dễ gây hiểu nhầm kết quả nếu không biết trước; LEFT JOIN giữ lại các dòng đó. Trên dataset Olist, cần kiểm tra cột `products.product_category_name` (có NULL) trước khi quyết định kiểu JOIN.
- Output của giai đoạn này có 3 loại tài liệu riêng biệt (khớp đúng 3 collection sẽ tạo ở Giai đoạn 3):
  1. **DDL** — cấu trúc bảng dạng `CREATE TABLE ...` (sinh tự động từ inspector).
  2. **Documentation** — mô tả nghiệp vụ, cảnh báo bẫy, viết dạng đoạn văn ngắn (không phải dict Python), vì sẽ bị embed thành vector.
  3. **Question-SQL pairs** — ví dụ mẫu (sẽ viết ở Giai đoạn 3, KHÔNG dùng chung với eval set của Giai đoạn 7).

**Tech stack**: SQLAlchemy `inspect()`, không cần thư viện mới.

**Việc cần làm**
- Viết hàm sinh DDL tự động từ `inspector.get_columns()` + `get_foreign_keys()` + `get_pk_constraint()`.
- Tự khám phá và viết mô tả nghiệp vụ cho từng bảng bằng cách query trực tiếp dữ liệu thật — đặc biệt: liệt kê đủ giá trị enum thật (vd `orders.order_status`, `order_payments.payment_type`, `order_reviews.review_score` — thang điểm bao nhiêu?), ghi chú ý nghĩa của NULL có giá trị nghiệp vụ (vd cột ngày giao hàng NULL nghĩa là đơn chưa giao xong, không phải lỗi data), tự đếm cardinality để xác nhận cột nào không unique (fan-out risk) và cột FK nào có thể NULL (INNER JOIN risk).
- Viết mỗi mô tả/cảnh báo thành 1 đoạn văn bản độc lập — chuẩn bị cho việc embed từng đoạn riêng lẻ ở Giai đoạn 3.

**Tại sao làm vậy**: nếu gộp chung thành 1 khối văn bản khổng lồ, không thể embed từng phần riêng để retrieve theo độ liên quan — RAG cần đơn vị tài liệu nhỏ, độc lập.

---

## Giai đoạn 3 — Vector store & training data cho RAG (core khác biệt kiến trúc so với cách nhồi schema tĩnh)

**Mục tiêu**: có 1 ChromaDB chứa DDL + documentation + ví dụ (question, SQL), retrieve được top-k liên quan theo câu hỏi mới.

**Khái niệm cần nắm trước khi code**
- **Embedding**: 1 hàm biến văn bản thành vector số thực (vd 768 chiều) sao cho văn bản ý nghĩa gần nhau → vector gần nhau (đo bằng cosine similarity). Đây là nền tảng để "tìm đoạn liên quan" mà không cần khớp từ khoá chính xác.
- **Collection** trong Chroma giống khái niệm "bảng" — mỗi collection lưu nhiều "document" kèm vector + metadata. Dự án này cần 3 collection riêng: `ddl`, `documentation`, `sql_examples` — tách riêng vì khi build prompt sẽ muốn kiểm soát lấy bao nhiêu từ mỗi loại (vd luôn lấy toàn bộ DDL vì schema nhỏ, nhưng chỉ lấy top-3 ví dụ SQL liên quan nhất).
- **"Train" trong ngữ cảnh RAG = ghi (write) vào vector store**, không phải train lại trọng số model — dễ gây hiểu nhầm vì trùng từ với fine-tuning. Ở đây "training data" chỉ là các document được add vào Chroma.
- Ollama expose endpoint embedding riêng (`/api/embeddings` hoặc `/v1/embeddings` chuẩn OpenAI) — gọi model `nomic-embed-text` đã pull ở Giai đoạn 0, KHÔNG dùng chung model sinh SQL.
- **⚠️ Cảnh báo data leakage — điểm dễ sai nhất giai đoạn này**: 15 case trong `eval_test_set.py` (sẽ viết ở Giai đoạn 7) là để **ĐO độ chính xác**, không được add vào `sql_examples`. Nếu đưa chính câu hỏi eval vào vector store rồi dùng làm few-shot, model coi như "nhìn thấy đáp án trước khi thi" — accuracy đo được sẽ không còn phản ánh khả năng thật. Cần viết 1 bộ **question-SQL pairs MỚI, khác hẳn** bộ eval, để làm dữ liệu train cho RAG.

**Tech stack**: `chromadb` (local, miễn phí), Ollama embedding model `nomic-embed-text` (local, miễn phí).

**Tại sao chọn Chroma thay vì FAISS**: FAISS chỉ là 1 thư viện index tìm kiếm gần đúng (ANN) thuần tuý — không tự lưu metadata, không tự persist, phải tự viết thêm lớp quản lý document/id/lưu đĩa. Ở quy mô dữ liệu dự án này (vài trăm đến vài nghìn document, không phải hàng triệu), lợi thế tốc độ của FAISS không có ý nghĩa, trong khi Chroma cho API cao cấp (add/query, tự quản lý embedding function, tự persist) — phù hợp hơn cho 1 người làm, ít thời gian.

**Việc cần làm**
- Viết `app/vector_store.py`: hàm khởi tạo Chroma client + 3 collection; hàm `add_ddl(text)`, `add_documentation(text)`, `add_sql_example(question, sql)`; hàm `retrieve(question, k_ddl, k_doc, k_examples)` trả về context đã ghép sẵn.
- Chạy 1 script "seed" nạp toàn bộ output Giai đoạn 2 (DDL + documentation) vào Chroma.
- Tự viết tối thiểu 15-20 cặp (question, SQL) làm training example (khác hẳn bộ eval sẽ viết ở Giai đoạn 7), add vào collection `sql_examples`.
- Tự test retrieval: với 1 câu hỏi mẫu, in ra top-k kết quả, tự đọc bằng mắt xem có hợp lý không TRƯỚC KHI nối vào Giai đoạn 4.

---

## Giai đoạn 4 — Tích hợp LLM với RAG prompt động

**Mục tiêu**: `generate_sql(question)` không nhận `schema_context` tĩnh, mà tự gọi `vector_store.retrieve()` rồi build prompt động.

**Khái niệm cần nắm trước khi code**
- Cấu trúc prompt kiểu RAG (giống cách vanna làm): `system` = luật chung + DDL liên quan + documentation liên quan; `user` = few-shot examples (định dạng rõ ràng Question/SQL lặp lại k lần) + câu hỏi thật cần trả lời. Few-shot examples đặt gần câu hỏi thật (cuối prompt) thường hiệu quả hơn đặt ở đầu — model chú ý nhiều hơn tới phần gần cuối.
- "OpenAI-compatible API": Ollama implement lại đúng format REST API của OpenAI (đã nói ở Giai đoạn 0) — dùng chung SDK `openai` của Python, chỉ cần trỏ `base_url="http://localhost:11434/v1"`, không cần logic gọi khác.
- Cấu trúc chat completion: gửi lên 1 list `messages` có `role` (`system` = luật/ngữ cảnh chung, `user` = câu hỏi cụ thể); nhận về `response.choices[0].message.content` để lấy text thật (API trả về 1 list `choices` vì hỗ trợ sinh nhiều bản trả lời cùng lúc).
- `temperature=0` **bắt buộc** — nếu không cố định, accuracy đo được ở Giai đoạn 7 sẽ dao động do nhiễu ngẫu nhiên giữa các lần gọi, không phản ánh đúng tác động của 1 thay đổi cụ thể (prompt, model, RAG...).
- Ranh giới trách nhiệm giữa các module: `generate_sql` trả raw SQL text, chưa "làm sạch" (chưa strip markdown/code fence nếu model lỡ trả kèm) — quyết định thiết kế: xử lý việc đó ở tầng thực thi (Giai đoạn 5), không phải ở đây.
- Vì có GPU nhanh, có thể cân nhắc model lớn hơn `7b` nếu RAM đủ — nhưng nên **giữ nguyên model khi so sánh accuracy trước/sau 1 thay đổi khác** (cùng lý do với `temperature=0`: đổi nhiều biến 1 lúc thì không biết thay đổi nào gây ra kết quả).

**Tech stack**: `openai` Python SDK (`pip install openai`), Ollama.

**Việc cần làm**
- Viết `app/build_prompt.py`: hàm nhận context đã retrieve, format thành `messages` list chuẩn OpenAI chat format.
- Viết `app/llm_sql.py`: `generate_sql(question)` = `retrieve(question)` → `build_prompt(...)` → gọi Ollama → trả raw SQL text.
- Tự test bằng vài câu hỏi mẫu, so sánh SQL sinh ra với kỳ vọng.

---

## Giai đoạn 5 — Thực thi SQL an toàn trên Postgres

**Mục tiêu**: xây "defense in depth" — nhiều lớp phòng thủ độc lập, không cái nào phụ thuộc cái kia — để thực thi an toàn SQL do LLM sinh ra.

**Khái niệm cần nắm trước khi code**
- SQL do LLM sinh ra phải được coi là input không đáng tin, tương tự input người dùng — không phải vì ai đó cố tình gõ hại, mà vì model có thể hallucinate ra lệnh phá hoại.
- "Defense in depth": nhiều lớp phòng thủ độc lập xếp chồng lên nhau — 1 lớp bị bypass/có lỗi thì lớp khác vẫn chặn được, thay vì dồn hết vào 1 điểm kiểm tra duy nhất.
- **⚠️ Cần tự verify, đừng giả định**: thư viện `sqlite3` của Python tự raise lỗi nếu 1 chuỗi chứa nhiều hơn 1 statement (stacked query) — nhưng `psycopg2` (driver Postgres) **KHÔNG có hành vi này theo mặc định** (simple query protocol) — `cursor.execute()` của psycopg2 **CHO PHÉP chạy nhiều statement nối bằng `;` trong 1 lần gọi**, kể cả khi statement đầu là `SELECT` hợp lệ và statement sau là `DROP TABLE`. Đây là điểm phải tự test kỹ, không được giả định driver nào cũng tự chặn.
- Vì lớp phòng thủ "chặn multi-statement" không tự động đúng ở Postgres, cần bù lại theo hướng khác: (a) tự parse/đếm số statement thật trong chuỗi SQL bằng thư viện `sqlparse` (an toàn hơn đếm ký tự `;` thô, vì `;` có thể nằm trong 1 chuỗi literal) — từ chối nếu >1 statement; VÀ (b) **role Postgres dùng để kết nối chỉ có quyền `SELECT`** (không có `INSERT`/`UPDATE`/`DELETE`/`DROP`) — lớp phòng thủ độc lập ở tầng DB: kể cả nếu lớp (a) bị bypass và câu `DROP TABLE` lọt qua, DB vẫn từ chối thực thi vì role không có quyền.
- **⚠️ Giới hạn thật đã phát hiện ở lớp 1 (`_is_select_only`)**: để chấp nhận CTE hợp lệ (`WITH x AS (...) SELECT ...`), lớp 1 phải chấp nhận cả prefix `with`, không chỉ `select`. Nhưng Postgres cho phép CTE **kèm ghi dữ liệu** (`WITH x AS (DELETE FROM orders RETURNING *) SELECT * FROM x`) — trông như chỉ đọc nhưng thực chất xoá dữ liệu. Đã tự verify: `sqlparse`'s `get_type()` báo `SELECT` cho cả 2 trường hợp (chỉ nhìn statement ngoài cùng, không nhìn vào bên trong CTE) — **không có cách nào ở tầng string-parsing bắt được case này**. Lớp 1 cố tình cho qua case này (đã viết rõ trong docstring + có test tường minh ghi lại giới hạn này, không giấu đi) — **lớp 2 (role read-only) là lớp thực sự chặn được**, nên khi build lớp 2 ở phần "Việc cần làm" bên dưới, phải test lại đúng case CTE-ghi-dữ-liệu này để xác nhận lớp 2 chặn đúng.
- **Đã biết, chưa sửa (an toàn, chỉ bất tiện)**: `_is_select_only()` từ chối oan vài dạng SELECT hợp lệ — có comment phía trước (`-- comment\nSELECT 1`, `/* comment */ SELECT 1`), bọc trong ngoặc (`(SELECT 1)`), hoặc cú pháp rút gọn riêng của Postgres `TABLE orders`. Đây là false negative (chặn nhầm cái đúng) — không nguy hiểm vì thà chặn nhầm còn hơn bỏ sót, và xác suất LLM trả về dạng này thấp vì system prompt đã yêu cầu "chỉ trả raw SQL, không giải thích/markdown". Không sửa ngay; nếu Giai đoạn 6 (self-correction) thấy nhiều `UnsafeQueryError` lặp lại vì lý do này, đó là tín hiệu quay lại xử lý. Ngược lại, đã thêm test khoá chặt 2 case **phải luôn bị từ chối** dù ai đó sau này lỡ nới lỏng hàm: `EXPLAIN ANALYZE ...` (thực thi thật câu lệnh bên trong, không chỉ "phân tích") và `CALL ...` (gọi stored procedure, có thể gây side effect tuỳ ý).
- Postgres có `statement_timeout` là tham số cấu hình **native** của session (`SET statement_timeout = '5000ms'`) — đơn giản hơn nhiều so với việc phải tự đếm bytecode nội bộ như 1 số DB nhẹ (vd SQLite) buộc phải làm qua cơ chế callback thủ công.
- Postgres (qua psycopg2) map lỗi theo mã SQLSTATE thành các exception class riêng biệt trong `psycopg2.errors` — timeout raise `QueryCanceled`, lỗi cú pháp raise `SyntaxError`, tham chiếu cột sai raise `UndefinedColumn`... Nghĩa là phân biệt "timeout thật" với "lỗi SQL thật" chỉ cần bắt đúng exception class, không cần tự so sánh thời gian thủ công.
- Giới hạn số dòng trả về nên xử lý ở tầng fetch (`cursor.fetchmany(n)`), không nối chuỗi `LIMIT` vào SQL — nối chuỗi dễ vỡ khi SQL gốc đã có `LIMIT`/`UNION` sẵn. Lưu ý: cách này không giảm được chi phí tính toán bên trong Postgres cho query dạng aggregate/`ORDER BY` (vẫn phải quét hết mới ra 1 dòng kết quả) — chỉ giới hạn số dòng kéo về phía Python.

**Tech stack**: `psycopg2`, `sqlparse` (thư viện nhỏ để đếm statement chính xác, miễn phí), 1 Postgres role riêng chỉ có quyền đọc.

**Việc cần làm**
- Tạo role Postgres read-only: `CREATE ROLE readonly_app LOGIN PASSWORD '...'`, `GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_app` (nhớ thêm `ALTER DEFAULT PRIVILEGES` để áp dụng cho bảng tạo sau này).
- Viết `sql_executor.py` với 3 lớp phòng thủ độc lập: (1) `_is_select_only(sql)` — chặn sớm nếu chuỗi (sau `strip().lower()`) không bắt đầu bằng `select`; (2) kết nối bằng role `readonly_app`; (3) đếm statement bằng `sqlparse`, từ chối nếu >1.
- Xây exception hierarchy riêng cho tầng này (vd `SqlExecutionError` base rỗng → `UnsafeQueryError`, `QueryTimeoutError`) để tầng gọi (Giai đoạn 6, 8) chỉ cần bắt 1 loại hoặc xử lý riêng khi cần.
- Tự viết bộ test: SELECT bình thường, LIMIT ép qua `fetchmany` trên bảng lớn, chữ thường/khoảng trắng thừa, DELETE bị chặn, stacked query (`SELECT 1; DROP TABLE orders;`) bị chặn (verify bảng gốc còn nguyên sau đó), timeout dừng đúng thời gian cấu hình — **đặc biệt phải tự test kỹ case stacked query trên Postgres thật, đừng giả định nó tự động an toàn**.

---

## Giai đoạn 6 — Vòng tự sửa lỗi (self-correction loop)

**Mục tiêu**: khi SQL sinh ra chạy lỗi (sai cú pháp, sai tên cột), tự động gửi lại lỗi cho LLM để sửa, thay vì trả lỗi thẳng cho người dùng. Đây là 1 trong các điểm khác biệt/nâng cấp so với luồng cơ bản (xem thêm Giai đoạn 9).

**Khái niệm cần nắm trước khi code**
- Vòng lặp: sinh SQL → thực thi → nếu lỗi, đưa `(câu hỏi gốc, SQL vừa sai, thông báo lỗi từ Postgres)` vào 1 lượt gọi LLM mới, yêu cầu sửa → thực thi lại → lặp tối đa N lần (đề xuất N=2-3, không nên vô hạn — vừa tốn thời gian vừa có nguy cơ model lặp lại đúng lỗi cũ).
- Vì sao đáng làm: đây là điểm phần lớn demo Text-to-SQL cơ bản (và cả vanna ở luồng mặc định) không nhấn mạnh — 1 lỗi cú pháp nhỏ khiến toàn bộ câu hỏi thất bại dù model "gần đúng". Cải thiện trải nghiệm thật rõ rệt so với việc thêm 1 layer.
- Cần log lại từng lượt thử (câu hỏi, SQL, lỗi nếu có, số lần retry) — chuẩn bị dữ liệu cho dashboard ở Giai đoạn 9.
- Lưu ý chi phí: mỗi lần retry là 1 lần gọi LLM đầy đủ — với model chạy local trên GPU M4 điều này rẻ hơn nhiều so với gọi cloud API, nhưng vẫn nên giới hạn N để tránh trải nghiệm chờ lâu.

**Tech stack**: không cần thư viện mới, chỉ là logic Python nối `generate_sql` (Giai đoạn 4) + `run_sql_safe` (Giai đoạn 5).

**Việc cần làm**
- Viết `app/self_correct.py`: hàm `answer_question(question, max_retries=2)` bọc vòng lặp trên.
- Tự test bằng cách cố tình cho 1 câu hỏi khó (vd 1 câu dễ khiến model nhầm `SUM` với `COUNT`, như đếm số lượng item trong 1 đơn hàng) — xem retry có tự sửa được không, ghi lại kết quả (thành công hay vẫn sai sau N lần).

---

## Giai đoạn 7 — Đánh giá độ chính xác

**Mục tiêu**: đo execution accuracy, đảm bảo **train set (Giai đoạn 3) và eval set tách biệt hoàn toàn**.

**Khái niệm cần nắm trước khi code**
- "Execution accuracy": chấm đúng/sai bằng cách **chạy cả 2 câu SQL** (SQL LLM sinh ra và 1 câu *gold SQL* tự viết tay là đáp án đúng) rồi **so kết quả trả về**, KHÔNG so văn bản 2 câu SQL — vì có vô số cách viết SQL khác nhau cho cùng 1 kết quả đúng (khác alias, khác thứ tự JOIN, `COUNT(*)` vs `COUNT(order_id)`...).
- So sánh kết quả cần bỏ qua thứ tự dòng nhưng **vẫn phải phân biệt số lần lặp lại** — dùng `Counter` chứ không phải `set`: `set` xoá hết bản sao trùng, nên 1 predicted thiếu mất 1 dòng (do logic sai) vẫn có thể bị chấm "khớp" nếu tập giá trị duy nhất giống nhau.
- SQL do LLM sinh ra có thể lỗi khi thực thi (sai cú pháp, tham chiếu cột không tồn tại) — đây là **kết quả hợp lệ của việc đánh giá** (tính là sai), không phải bug; vòng lặp đánh giá phải `try/except` bắt lại từng case, không được crash giữa chừng vì 1 case lỗi.
- Số thực (`AVG`, `ROUND`) có thể lệch li ti do làm tròn khác nhau giữa 2 cách viết SQL khác nhau — cân nhắc so sánh với sai số nhỏ (epsilon) thay vì so bằng tuyệt đối nếu gặp trường hợp này.
- **Cẩn thận: ngay cả `gold_sql` tự viết tay cũng có thể dính bẫy fan-out** (vd JOIN trực tiếp 2 bảng con của cùng 1 order mà không dedupe) — luôn tự verify `gold_sql` bằng cách đếm số dòng trước/sau JOIN so với số lượng thực thể gốc, không mặc định `gold_sql` đúng chỉ vì tự viết.
- Lỗi thường gặp khi viết `evaluate.py`, nên tự cảnh giác: biến cờ đúng/sai chỉ gán trong nhánh `try` (gây `UnboundLocalError` nếu case đầu tiên đã lỗi), khởi tạo/reset biến cờ sai vị trí (đặt ngoài vòng `for` thay vì mỗi vòng lặp, khiến giá trị "rỉ" từ case trước sang case sau), gõ nhầm tên biến khi cộng dồn bộ đếm tổng — nên tự viết test bằng cách monkeypatch/giả lập `generate_sql`/`run_sql_safe` để bắt các lỗi này sớm, không cần chờ LLM thật chạy xong mỗi lần test.
- Cần đo accuracy ở **2 chế độ**: (a) không dùng self-correction (chỉ 1 lần gọi LLM) và (b) có self-correction (Giai đoạn 6) — để định lượng đúng self-correction cải thiện bao nhiêu %, không chỉ cảm tính.
- **Experiment log**: mỗi lần chạy `evaluate.py` nên tự động ghi lại 1 dòng vào file log riêng (không phải chỉ in ra màn hình rồi mất) — đây là thực hành MLOps cơ bản: mọi thay đổi (model, prompt, RAG config, có/không self-correction) đều phải có số liệu đo được, tra cứu lại được sau này, không chỉ nhớ miệng. Dữ liệu này cũng chính là nguồn cho dashboard ở Giai đoạn 9.

**Tech stack**: thuần Python (`collections.Counter`, `csv` built-in), không cần thư viện mới.

**Việc cần làm**
- Viết `eval_test_set.py`: tối thiểu 15 cặp `(question, gold_sql)`, phủ đủ dạng câu hỏi: đếm đơn giản, JOIN + AVG, GROUP BY + top-1, bẫy NULL (cột FK có thể NULL), bẫy fan-out (JOIN qua cột không unique), HAVING qua subquery, tổng nhiều cột, filter theo ngày, GROUP BY tìm max, so sánh 2 cột ngày, JOIN từ 3 bảng trở lên, và ít nhất vài câu trả về **nhiều dòng thật** (không chỉ 1 số/1 dòng) để test cơ chế so sánh `Counter` trên dữ liệu thật.
- Viết `evaluate.py`: chạy `generate_sql()` + `run_sql_safe()` trên từng câu hỏi, so kết quả với gold bằng `Counter`, in báo cáo — tự test bằng monkeypatch trước khi chạy với LLM thật.
- Thêm vào `evaluate.py`: sau mỗi lần chạy, append 1 dòng vào `results/eval_log.csv` (tạo thư mục `results/` nếu chưa có) — cột gợi ý: `timestamp, config_description, model, use_self_correction, n_cases, n_correct, accuracy`. `config_description` là 1 câu ngắn tự ghi tay mô tả thay đổi lần này (vd "baseline, no RAG examples" hay "+ 20 RAG examples").
- Chạy đo accuracy ở cả 2 chế độ (có/không self-correction), mỗi lần chạy = 1 dòng mới trong `eval_log.csv` — **mỗi lần chỉ đổi 1 biến** để biết chính xác thay đổi nào gây ra kết quả (giữ `temperature=0` khi so sánh).
- **⚠️ Nhắc lại cảnh báo data leakage**: không thêm case nào của eval set vào vector store ở Giai đoạn 3.

---

## Giai đoạn 8 — Đóng gói: FastAPI + React + docker-compose + CI/CD

**Mục tiêu**: đóng gói backend + frontend, dùng docker-compose thật (máy hỗ trợ Docker nên không cần hoãn phần này), cộng thêm CI pipeline — mục tiêu dự án giờ không chỉ là "chạy được" mà còn phải **thể hiện được thực hành MLOps/backend/frontend rõ ràng cho mục đích portfolio** (xem "Yêu cầu bắt buộc" ở đầu file).

**Khái niệm cần nắm trước khi code**
- FastAPI tự sinh **validation + tài liệu API (Swagger UI)** dựa trên type hint Python — định nghĩa "hình dạng" dữ liệu vào/ra bằng class kế thừa `pydantic.BaseModel`, FastAPI tự kiểm tra request có đúng định dạng không (thiếu field, sai kiểu) và tự trả lỗi `422` nếu sai, không cần validate tay.
- FastAPI (framework) và Uvicorn (server) là 2 thứ khác nhau: `FastAPI()` chỉ tạo ra 1 "app object" mô tả route, **không tự chạy, không tự lắng nghe port** — cần Uvicorn (ASGI server) để thực sự chạy nó (`uvicorn app.api:app --reload`).
- Thiết kế endpoint (`POST /query`) cần map cây exception đã xây ở Giai đoạn 5 (`UnsafeQueryError`, `QueryTimeoutError`) sang đúng HTTP status code (`400` cho SQL không hợp lệ, `408` cho timeout, `500` cho lỗi hệ thống thật).
- **CORS**: React (dev server, thường `localhost:3000`) và FastAPI (thường `localhost:8000`) là 2 "origin" khác nhau theo trình duyệt — trình duyệt **mặc định chặn** JS gọi API từ origin khác (chính sách bảo mật, không phải bug) trừ khi FastAPI thêm `CORSMiddleware` mở quyền cho origin đó.
- `docker-compose.yml` có thể gồm **Postgres + FastAPI backend** (2 service), nhưng **Ollama KHÔNG nên đưa vào docker-compose** — nhắc lại lý do ở Giai đoạn 0 (mất GPU passthrough nếu container hoá trên Mac) — Ollama tiếp tục chạy native, backend trong Docker gọi ra `http://host.docker.internal:11434` (cách Docker Desktop cho container gọi ra service chạy trên máy host).
- **CI (GitHub Actions)**: 1 file YAML trong `.github/workflows/` mô tả job chạy tự động mỗi khi push/mở PR — chạy trên máy ảo tạm thời của GitHub (runner), không phải máy của bạn. **Giới hạn thật cần biết**: runner miễn phí của GitHub KHÔNG có GPU, giới hạn số phút chạy/tháng, và không có sẵn Ollama/model đã pull — nên CI **không nên** chạy lại toàn bộ `evaluate.py` (cần gọi LLM thật, tốn phút chạy + phải tải model GB mỗi lần). CI chỉ nên chạy được: (a) lint/kiểm tra cú pháp, (b) unit test cho phần logic thuần Python không cần LLM/DB thật (vd `sql_executor._is_select_only`, `_is_single_statement`, `evaluate.normalize_result`), (c) build thử Docker image để chắc chắn `docker-compose.yml` không bị hỏng. Việc đo accuracy thật (Giai đoạn 7) vẫn chạy **thủ công, local**, ghi vào `results/eval_log.csv` — không tự động hoá trong CI vì không thực tế với tài nguyên miễn phí.
- GitHub Actions **hỗ trợ chạy 1 Postgres service container ngay trong job** (`services: postgres: image: postgres:17`) miễn phí — có thể dùng để test thật `sql_executor.py`/`load_data.py` với Postgres, không cần Ollama.
- **Đã tự phát hiện lúc viết `tests/` (Giai đoạn 8)**: bare `pytest` (khác `python -m pytest`) không tự thêm thư mục gốc repo vào đường dẫn tìm module nếu `tests/` không có `__init__.py` — sẽ báo `ModuleNotFoundError: No module named 'app'`. Có 2 cách sửa tương đương: file cấu hình `pytest.ini` (`pythonpath = .`), hoặc thêm `tests/__init__.py` (trống) để `pytest` tự dò ngược lên gốc repo. Đã chọn `tests/__init__.py` để đồng nhất với cách `app/` cũng dùng `__init__.py` — không giữ cả 2 cùng lúc vì dư thừa. **Lưu ý cho `ci.yml`**: đảm bảo `tests/__init__.py` được commit (không bị `.gitignore` loại), nếu không CI sẽ lỗi y hệt.

**Tech stack**: FastAPI, `uvicorn[standard]`, React + Node.js/npm, docker-compose (Postgres + backend, không gồm Ollama), GitHub Actions, `pytest` (cho unit test phần logic thuần Python).

**Việc cần làm**
- Viết `app/api.py`: endpoint `POST /query` nối `self_correct.answer_question`, map exception (`UnsafeQueryError` → 400, `QueryTimeoutError` → 408, lỗi hệ thống → 500).
- Viết `docker-compose.yml` gồm 2 service (Postgres, backend) — backend đọc `OLLAMA_BASE_URL` qua biến môi trường trỏ `host.docker.internal`. Mục tiêu: **1 lệnh `docker compose up` chạy được toàn bộ backend + DB** (Ollama vẫn chạy native riêng).
- Tạo project React riêng trong `frontend/`, gọi API qua `fetch`. Giữ tối giản: 1 trang chính (ô hỏi + bảng kết quả), có thể thêm 1 tab nhỏ đọc `results/eval_log.csv` (qua 1 endpoint mới) để hiển thị biểu đồ accuracy/latency theo thời gian — xem Giai đoạn 9.
- Viết `.github/workflows/ci.yml`: job chạy lint (vd `ruff`/`flake8`) + `pytest` cho các hàm thuần Python + `docker compose build` — trigger mỗi khi push.
- Viết vài test nhỏ trong `tests/` cho các hàm không cần LLM/Postgres thật: `sql_executor._is_select_only`, `_is_single_statement` (dùng chuỗi SQL giả), `evaluate.normalize_result` (dùng list số giả) — đây là phần CI thực sự chạy được.

---

## Giai đoạn 9 — Khác biệt hoá / nâng cao (KHÔNG copy nguyên vanna)

**Mục tiêu**: chọn tối thiểu 2-3 tính năng làm cho sản phẩm này **tốt hơn hoặc khác vanna ở 1 điểm cụ thể**, không chỉ là "vanna phiên bản tự build".

Chia làm 2 nhóm mục đích khác nhau: **(A) khác biệt AI/sản phẩm** — làm cho hệ thống thông minh/an toàn hơn vanna; **(B) MLOps/vận hành** — làm cho dự án thể hiện rõ năng lực MLOps/backend/frontend cho mục đích portfolio (xem "Yêu cầu bắt buộc" ở đầu file). Cả 2 nhóm đều là "nên làm", không phải 1 nhóm chính 1 nhóm phụ.

### Nhóm A — Khác biệt AI/sản phẩm (so với vanna)

1. **Guardrail dựa trên schema trap đã biết** — vanna KHÔNG có sẵn tính năng này. Dự án này (ở Giai đoạn 2) sẽ tự phát hiện và ghi chú các cột JOIN không unique / cột FK có thể NULL (vd `geolocation.geolocation_zip_code_prefix` không unique). Xây 1 lớp kiểm tra: nếu SQL sinh ra JOIN qua 1 cột đã biết là không unique mà không có `DISTINCT`/subquery dedupe, tự động cảnh báo hoặc tự thêm bước dedupe trước khi trả kết quả — biến đúng loại bug fan-out (vd tính trung bình review_score theo phương thức thanh toán, dễ bị nhân đôi nếu JOIN `order_payments` không dedupe khi 1 đơn có nhiều dòng thanh toán trả góp) thành 1 tính năng chủ động của hệ thống, không phải hy vọng model tự nhớ.
2. **Active learning flywheel** — vanna yêu cầu gọi tay `vn.train()` để thêm ví dụ mới. Ở đây: khi người dùng xác nhận qua UI (nút "✅ đúng" / "❌ sai, đây mới là SQL đúng"), tự động gọi `vector_store.add_sql_example(...)` ngay lập tức — hệ thống tự cải thiện theo thời gian sử dụng thật, không cần thao tác thủ công riêng.
3. **Giải thích SQL bằng ngôn ngữ tự nhiên** — 1 lệnh gọi LLM phụ (dùng lại model đã có, không cần model mới) diễn giải lại SQL vừa sinh ra thành câu văn thường, giúp người không biết SQL tự kiểm tra được máy có hiểu đúng ý mình không trước khi tin kết quả — tăng độ tin cậy, chi phí thêm gần như 0 vì local.

### Nhóm B — MLOps / observability (mới, phục vụ mục tiêu portfolio)

4. **Dashboard theo dõi accuracy/latency/retry theo thời gian** — đọc trực tiếp `results/eval_log.csv` (Giai đoạn 7) + log của `self_correct.py` (Giai đoạn 6), hiển thị trên chính trang React (Giai đoạn 8) dạng biểu đồ đơn giản (accuracy theo từng lần chạy eval, số lần retry trung bình...). Đây là bằng chứng trực quan nhất cho năng lực MLOps khi demo — nhà tuyển dụng nhìn thấy ngay "có đo lường, có theo dõi theo thời gian", không chỉ nghe kể.
5. **CI pipeline** — đã triển khai cụ thể ở Giai đoạn 8 (`.github/workflows/ci.yml`): lint + unit test + build Docker image tự động mỗi lần push. Nhắc lại ở đây vì đây cũng là 1 "tính năng" đáng liệt kê khi viết CV, không chỉ là việc nội bộ.
6. **1 lệnh `docker compose up` chạy được toàn bộ backend + DB** — đã làm ở Giai đoạn 8, liệt kê lại ở đây vì đây là câu chuyện "deployment" cụ thể để kể khi phỏng vấn.

### Đề xuất cân nhắc thêm (giá trị thấp hơn hoặc tốn công hơn, làm sau nếu còn thời gian)

- Query cache (bảng Postgres `question → sql đã confirm đúng`, tra trước khi gọi LLM lại).
- Multi-turn: câu hỏi follow-up tham chiếu ngữ cảnh câu trước đó.

**Việc cần làm**: làm cả nhóm A (chọn tối thiểu 2/3 mục) và nhóm B (cả 3 mục, vì đã triển khai sẵn ở Giai đoạn 7/8, chỉ cần nối vào dashboard) — KHÔNG làm tất cả nhóm A cùng lúc, mỗi tính năng nhóm A nên đo tác động riêng bằng cách so accuracy trước/sau khi chỉ bật 1 tính năng đó (xem cách đo ở Giai đoạn 7, ghi vào `results/eval_log.csv`), tránh gộp nhiều thay đổi rồi không biết cái nào thực sự có ích.

---

## Giai đoạn 10 — README & case-study cho recruiter

**Mục tiêu**: có 1 `README.md` đóng vai trò "trang bán hàng" của dự án — thứ đầu tiên (và có thể duy nhất) 1 nhà tuyển dụng/reviewer thực sự đọc trong vài phút, khác hẳn vai trò của `PROGRESS.md`.

**Khái niệm cần nắm trước khi viết**
- **Đối tượng đọc khác hẳn PROGRESS.md**: `PROGRESS.md` viết cho chính bạn (và AI) để duy trì ngữ cảnh qua nhiều phiên làm việc — dài, chi tiết, tiếng Việt, ghi lại cả sai lầm/quá trình cân nhắc. `README.md` viết cho người lạ chỉ có vài phút, không quan tâm quá trình bạn đã đi qua, chỉ quan tâm: dự án làm gì, có chạy được không, có gì đáng chú ý. **Không dịch PROGRESS.md sang tiếng Anh rồi rút gọn** — viết lại từ đầu theo đúng mục đích khác.
- **Thứ tự đọc quyết định thứ tự viết**: người đọc lướt từ trên xuống rồi bỏ đi bất cứ lúc nào — nên phần quan trọng nhất phải nằm ngay đầu: 1-2 câu mô tả dự án (elevator pitch) → demo trực quan (ảnh/GIF hoặc link chạy được) → kết quả bằng số liệu cụ thể → mới đến chi tiết kiến trúc/cách chạy. Đừng bắt người đọc cuộn hết trang mới thấy điều thú vị nhất.
- **"Show, don't tell"**: thay vì viết "tôi biết Docker/FastAPI/React/MLOps", để chính GIF demo + bảng accuracy + sơ đồ kiến trúc tự chứng minh — nhà tuyển dụng tự suy ra kỹ năng từ bằng chứng, đáng tin hơn nhiều so với tự liệt kê.
- **Viết SAU CÙNG, không viết trước**: README cần số liệu thật (từ `results/eval_log.csv`) và demo thật (từ Giai đoạn 6-9 đã chạy được) — viết sớm sẽ phải sửa lại nhiều lần và có nguy cơ ghi sai kỳ vọng so với thực tế.
- **⚠️ Đổi giọng điệu, không copy nguyên văn từ PROGRESS.md**: PROGRESS.md là tài liệu nội bộ, trung thực về động cơ (vd "làm để có portfolio xin việc", "so vanna để tìm differentiator") — sự trung thực đó ĐÚNG ở chỗ nội bộ vì nó giải thích lý do quyết định kỹ thuật. Nhưng đưa nguyên giọng điệu đó vào README công khai sẽ phản tác dụng — đọc như dự án làm màu (resume-padding) thay vì tò mò kỹ thuật thật. Khi viết README: **không bao giờ nhắc đến CV/xin việc**, để chất lượng công việc tự nói; mục so sánh vanna viết trung lập, mang tính kỹ thuật (vd "Built following Vanna's RAG pattern, extended with...") — không viết theo kiểu "hơn/thua" hay phòng thủ ("không phải bản copy").

**Tech stack**: không cần công cụ mới — Markdown thuần; có thể dùng công cụ ghi màn hình có sẵn trên macOS (Screenshot.app/QuickTime) để quay demo ngắn thành GIF/video.

**Việc cần làm**
- Viết `README.md` (tiếng Anh) gồm theo đúng thứ tự: elevator pitch 1-2 câu → demo (GIF hoặc link) → bảng kết quả accuracy (lấy trực tiếp từ `results/eval_log.csv`, có thể trích bảng before/after) → sơ đồ kiến trúc đơn giản (không cần chi tiết như PROGRESS.md, có thể vẽ bằng Mermaid) → mục "What's different from Vanna" (tóm tắt 3 điểm ở Giai đoạn 9 Nhóm A) → hướng dẫn chạy (`docker compose up`, `.env.example`...) → tech stack liệt kê ngắn gọn.
- Quay/chụp demo ngắn (30 giây - 1 phút): 1 câu hỏi bình thường (xem SQL sinh ra + kết quả), 1 câu hỏi khó cố tình để xem self-correction hoạt động.
- Đặt `README.md` ở gốc repo. `PROGRESS.md` giữ nguyên vai trò nhật ký nội bộ — không gộp 2 file, không để README dài dòng như PROGRESS.md.
- Thêm file `LICENSE` ở gốc repo (khuyến nghị MIT — đơn giản, phổ biến nhất cho portfolio project, cho phép người khác xem/dùng lại tự do) — cần có trước khi đưa link repo vào CV/đăng công khai, thiếu file này khiến repo mặc định "all rights reserved", gây khó hiểu cho người xem. Lưu ý: MIT áp dụng cho **code** của bạn — không áp dụng cho bộ dữ liệu Olist (xem mục credit dataset ngay dưới đây).
- **Ghi credit nguồn dữ liệu trong README** (mục Data/Acknowledgements): dataset Olist dùng license **CC BY-NC-SA 4.0** (đã verify trực tiếp trên Kaggle, không phải đoán) — yêu cầu ghi rõ nguồn (Olist, link Kaggle dataset) khi dùng. Dự án dùng cho mục đích phi thương mại (học tập/portfolio) nên hợp lệ, chỉ cần đảm bảo có credit, không tự nhận là dữ liệu tự thu thập.

**Tại sao làm ở cuối cùng**: cần có số liệu + demo thật mới viết đúng được; đây cũng là lý do Giai đoạn 10 đứng sau Giai đoạn 9 trong thứ tự đánh số dù về mặt thời gian có thể viết song song lúc gần hoàn thiện, không nhất thiết đợi 100% các giai đoạn trước xong.

---

## Tài liệu học — 1 trang tổng hợp

**[NL2SQL Build Path](https://claude.ai/artifact/KYJCGZx9kxABBkfQKpRos2)** — kiến thức cốt lõi + link tài liệu chính thức (không phải blog bên thứ ba) cho từng giai đoạn 0-10, kèm 2 bài báo gốc (RAG — Lewis et al. 2020; Spider benchmark — nguồn khái niệm "execution accuracy" ở Giai đoạn 7). Dùng làm tài liệu tra cứu khi làm tới từng giai đoạn, không cần đọc hết 1 lượt.
