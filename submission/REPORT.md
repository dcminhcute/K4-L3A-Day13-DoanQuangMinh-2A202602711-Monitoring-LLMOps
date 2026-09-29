# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Đoàn Quang Minh
- **MSSV:** 2A202602711
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/dcminhcute/K4-L3A-Day13-DoanQuangMinh-2A202602711-Monitoring-LLMOps
- **Commit SHA cuối:** `13b6066`
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602711`

## 2. Evidence index

| Evidence | Đường dẫn | Trạng thái |
|---|---|---|
| Pytest cuối | `evidence/01-pytest.png` | ✅ Đã có |
| Log validator | `evidence/02-log-validator.png` | ✅ Đã có |
| Dashboard validator | `evidence/03-dashboard-validator.png` | ✅ Đã có |
| Structured log | `evidence/04-structured-log.png` | ✅ Đã có |
| PII redaction | `evidence/05-pii-redaction.png` | ✅ Đã có |
| Trace list | `evidence/06-trace-list.png` | ✅ Đã có |
| Trace waterfall | `evidence/07-trace-waterfall.png` | ✅ Đã có |
| Trace metadata | `evidence/08-trace-metadata.png` | ✅ Đã có |
| Prompt versions | `evidence/09-prompt-versions.png` | ✅ Đã có |
| Prompt rollback | `evidence/10-prompt-rollback.png` | ✅ Đã có |
| Dashboard runtime | `evidence/11-dashboard-overview.png` | ✅ Đã gen |
| Incident metric | `evidence/12-incident-metric.png` | ✅ Đã gen |
| Incident log | `evidence/13-incident-log.png` | ✅ Đã chụp (req-f657cf7a) |
| Incident trace | `evidence/14-incident-trace.png` | ✅ Đã chụp (Langfuse, che public_key) |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | ~30/100 | 100/100 | Đạt điểm tuyệt đối sau CP1 |
| `validate_dashboard.py` | HỢP LỆ: 6/6 | HỢP LỆ: 6/6 | Dashboard contract đúng cả 6 panel |
| `pytest` | 12 passed, 10 failed | 22 passed in 1.66s | 100% tests pass (22/22) |
| Số traces hợp lệ | 0 | 39 traces (>100 obs) | Đạt trên project Langfuse cá nhân |
| Số PII leak | ~3 leaks | 0 | Scrub processor hoạt động triệt để |
| Latency P95 / TTFT P95 | ~550ms / 50ms | 4058ms (incident) / 50ms | P95 vượt 3000ms do incident rag_slow |
| Retrieval success rate | 100% | 100% | Đạt mục tiêu ≥90% |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  - Middleware kiểm tra header `x-request-id`; nếu không có thì sinh `req-<8-hex>` bằng `secrets.token_hex(4)`.
  - Gọi `bind_contextvars(correlation_id=correlation_id)` để truyền vào structlog chain.
  - Trả về response headers: `x-request-id`, `x-response-time-ms`.

- **Các metadata được ghi vào structured log:**
  - `user_id_hash` — hash SHA256 của user_id, cắt 12 ký tự đầu
  - `session_id`, `feature`, `model`, `env` — bind từ request context
  - `correlation_id` — từ middleware, xuống cả request_received và response_sent

- **Cách bảo đảm PII được scrub trước khi ghi:**
  - Processor `scrub_event` đăng ký trước `JsonlFileProcessor` và `JSONRenderer` trong structlog chain.
  - Scrub mọi string trong `payload` dict và `event` field.
  - Pattern: email, phone_vn (+84/0 + 9 số), cccd (12 số), credit_card (16 số).

- **Cách kiểm chứng kết quả:**
  - Chạy `python scripts/validate_logs.py` — score đạt 100/100.
  - Gửi request với email/phone thực qua endpoint `/chat`, kiểm tra `data/logs.jsonl` thấy `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, không chứa PII thô.

## 5. Tracing và prompt versioning

- **Cách xác định traces do chính tôi tạo trong project cá nhân:**
  - Mỗi học viên tạo project Langfuse riêng `day13-k4-l3a-2A202602711`, cấu hình qua `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY` trong `.env`.
  - Trace metadata chứa `user_id_hash` (đã hash), không PII thô. Toàn bộ trace được gán đúng session và correlation ID.

- **Cấu trúc root/retrieval/generation observations:**
  ```
  trace (lab-agent-run)
  ├── span (retrieval, type=retriever)
  └── generation (llm-generation, type=generation)
        └── input, output, usage_details, cost_details
  ```

- **Cách nối trace với log:**
  - `correlation_id` từ middleware được bind vào contextvars và truyền vào hàm `agent.run()`.
  - Root observation và generation metadata trong Langfuse được gán `correlation_id` khớp chính xác với trường `correlation_id` trong `data/logs.jsonl`.

- **Prompt name:** `day13-chat`
- **Version/label baseline:** v1 — labels: `baseline`, `production`
- **Version/label candidate:** v2 — label: `candidate`
- **Trace ID của mỗi version:**
  - Baseline (v1): Chạy qua prompt v1 với label `baseline`.
  - Candidate (v2): Chạy qua prompt v2 với label `candidate`.
  - Production (trace đại diện): `1e09527202f5b71774312ff2c7c57e92` (chụp tại `evidence/07-trace-waterfall.png` và `evidence/08-trace-metadata.png`).
- **Cách promote và rollback `production`:**
  1. Tạo prompt v1 với labels `baseline` và `production`.
  2. Tạo prompt v2 với label `candidate`, tinh chỉnh nội dung prompt.
  3. Chạy kiểm thử cùng input với `LANGFUSE_PROMPT_LABEL=baseline` và `candidate`.
  4. So sánh traces, đổi label `production` sang v2 (promote).
  5. Rollback: chuyển lại label `production` về v1 nếu phát hiện bất thường, chụp ảnh minh chứng tại `evidence/10-prompt-rollback.png`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  1. **latency** — P50/P95/P99 latency_ms và TTFT P95 (threshold: P95 ≤ 3000ms)
  2. **traffic** — request count và rate per minute (threshold: rate ≥ 1 req/min)
  3. **errors** — error rate %, error types, retrieval success rate (threshold: error_rate ≤ 2%)
  4. **cost** — cost per minute và total (threshold: total ≤ $2.50 USD)
  5. **tokens** — sum input/output tokens (threshold: sum ≤ 50,000 tokens)
  6. **quality** — mean quality_score (threshold: mean ≥ 0.75)

- **SLO và lý do chọn:**
  - SLO: `fast_successful_requests` — 99.5% requests latency ≤ 3000ms.
  - Target 99.5% cân bằng giữa độ tin cậy trải nghiệm người dùng và chi phí tài nguyên xử lý LLM/RAG.

- **Cách tính error budget:**
  - Error budget = (100% - 99.5%) × 28 ngày = 0.5% × 40,320 phút = 201.6 phút.
  - Khi error budget cạn kiệt (exhausted) &rarr; đội ngũ kỹ thuật phải dừng release tính năng mới để tập trung cải thiện reliability và fix latency.

- **Ba alert và runbook tương ứng:**

  | Alert | Severity | Duration | Condition | Runbook |
  |---|---|---|---|---|
  | HighLatency | warning | 5m | P95 > 3000ms | docs/alerts.md#alert-1 |
  | HighErrorRate | critical | 3m | error_rate > 2% | docs/alerts.md#alert-2 |
  | LowRetrievalSuccess | warning | 5m | success_rate < 90% | docs/alerts.md#alert-3 |

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 2026-09-29 09:20:15Z – 09:20:33Z (tức 16:20:15 – 16:20:33 GMT+7)
- **Triệu chứng từ metrics:**
  1. Dashboard latency panel: Latency P95 tăng vọt từ mức bình thường (~500ms) lên 4058ms (đỉnh 4134ms tại request challenge), vượt ngưỡng SLO 3000ms và kích hoạt cảnh báo `HighLatency` (warning).
  2. Errors panel: Error rate vẫn ở mức 0%, cho thấy hệ thống không crash hay trả lỗi 500 mà bị nghẽn thời gian phản hồi (tail latency issue).
- **Log line và correlation ID liên quan:**
  - Control log: Line 50 trong `data/logs.jsonl` ghi nhận sự kiện bật incident: `{"service": "control", "payload": {"name": "rag_slow"}, "event": "incident_enabled", "correlation_id": "req-869ec391", "level": "warning", "ts": "2026-09-29T09:20:15.753177Z"}`.
  - Request log: Line 51–52 ghi nhận request đầu tiên bị ảnh hưởng: `correlation_id: "req-c6c6cd4a"`, `session_id: "k4-l3a-challenge-s04"`, `feature: "monitoring"`, `latency_ms: 4134` tại thời điểm `2026-09-29T09:20:20.283134Z`.
- **Trace ID và span gây ảnh hưởng:**
  - Trace ID trong Langfuse: `370ecf32e9098a600e7dd2286005b327` (nối với log qua `correlation_id: req-c6c6cd4a`).
  - Phân tích span tree trong trace:
    - Root observation: `lab-agent-run` (tổng thời gian 4.134s).
    - Span con 1: `retrieval` (type: retriever) kéo dài **2.501s** (bất thường so với baseline <10ms).
    - Span con 2: `llm-generation` (type: generation) chỉ mất **0.152s**.
    - &rarr; Span `retrieval` là thủ phạm trực tiếp chiếm >60% thời gian xử lý của request.
- **Root cause:**
  - Incident `rag_slow` được kích hoạt (trong file `app/mock_rag.py:retrieve()`), gây ra hàm `time.sleep(2.5)` mỗi khi tiến hành tìm kiếm context cho query `feature: "monitoring"`. Sự chậm trễ của vector retriever đã làm tổng thời gian xử lý vượt quá ngưỡng SLO 3000ms.
- **Fix action:**
  - Gửi request vô hiệu hóa incident: `POST http://127.0.0.1:8000/incidents/rag_slow/disable` (hoặc chạy lệnh `python scripts/inject_incident.py --disable`).
  - Sau khi tắt incident, độ trễ span retrieval lập tức quay về mức bình thường.
- **Preventive measure:**
  - Thiết lập timeout nghiêm ngặt cho span retrieval (ví dụ 1.5s max timeout) kèm circuit breaker pattern.
  - Sử dụng cơ chế fallback (cached context hoặc heuristic answer) khi vector database bị quá tải hoặc phản hồi chậm.
  - Thiết lập alert sớm tại tầng tracing/APM khi span retrieval P95 vượt quá 1000ms trước khi vi phạm SLO toàn hệ thống.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  - Triển khai custom processor `scrub_event` đăng ký trực tiếp vào structlog pipeline (đặt trước `JsonlFileProcessor` và `JSONRenderer`). Cách tiếp cận này đảm bảo mọi sự kiện log đều tự động được khử PII tại tầng middleware/logging tập trung, loại bỏ hoàn toàn nguy cơ rò rỉ dữ liệu do lập trình viên quên gọi hàm scrub ở từng controller.

- **Một lỗi/blocker đã gặp:**
  - Phiên bản Langfuse SDK v4 thay đổi API tạo observation từ cú pháp cũ `start_as_current_span` sang `start_as_current_observation(name=..., as_type=...)`. Khi tích hợp, cần kiểm tra tương thích ngược và truyền đúng `as_type="retriever"` và `as_type="generation"` để hiển thị đúng cây quan sát trên Langfuse UI.

- **Cách tìm nguyên nhân và xử lý:**
  - Tuân thủ nghiêm ngặt chuỗi điều tra: Metrics (phát hiện latency tăng đột biến trên dashboard) &rarr; Logs (lọc theo khung giờ và tìm `correlation_id` của request vi phạm) &rarr; Traces (mở trace tương ứng trên Langfuse để xem span tree và xác định chính xác span bị nghẽn).

- **Cách hiểu luồng Metrics → Logs → Traces:**
  1. **Metrics:** Cho biết **"KHI NÀO VÀ CÁI GÌ ĐANG CÓ VẤN ĐỀ"** (ví dụ: Latency P95 vi phạm SLO lúc 16:20).
  2. **Logs:** Cho biết **"REQUEST CỤ THỂ NÀO BỊ ẢNH HƯỞNG"** thông qua `correlation_id`, session ID và context lỗi.
  3. **Traces:** Cho biết **"TẠI SAO VÀ BỘ PHẬN NÀO GÂY RA LỖI"** bằng cách bóc tách chi tiết từng span (retrieval, LLM call, DB query) trong cây phân cấp thực thi.

- **Vai trò của prompt version, token/cost, SLO hoặc rollback:**
  - **Prompt versioning:** Cho phép A/B testing prompt mới mà vẫn đảm bảo khả năng rollback tức thời về baseline đã được kiểm chứng an toàn khi có sự cố chất lượng.
  - **Token/Cost tracking:** Giúp giám sát chi phí vận hành mô hình theo thời gian thực và phát hiện kịp thời các bất thường về token usage (như infinite generation loop).
  - **SLO & Error Budget:** Cung cấp chuẩn mực định lượng rõ ràng về mức độ tin cậy của dịch vụ, làm căn cứ ưu tiên giữa việc phát triển tính năng mới và cải thiện độ ổn định hệ thống.

- **Điều quan trọng nhất đã học:**
  - `correlation_id` là xương sống kết nối toàn bộ hệ sinh thái giám sát hiện đại. Nếu không có correlation ID được truyền xuyên suốt qua middleware, logs, traces và contextvars, việc điều tra sự cố trong kiến trúc microservice và LLM workflow phân tán sẽ vô cùng tốn thời gian.

- **Hạn chế hoặc phần chưa hoàn thành:**
  - Toàn bộ các yêu cầu của bài lab từ CP1 đến CP3 challenge đã được hoàn thành 100%. Các evidence hình ảnh đều được chụp và lưu trữ đầy đủ với dữ liệu thực nghiệm chuẩn xác.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô.
- [x] URL repo và commit SHA đã nộp trên LMS/Codelabs.
