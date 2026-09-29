# Alert Runbooks

Mỗi alert dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

---

## Alert 1: HighLatency

- **Tên:** HighLatency
- **Severity:** warning
- **Duration:** 5 phút
- **Kênh thông báo:** Slack
- **SLI/SLO liên quan:** `fast_successful_requests` — P95 latency phải <= 3000ms
- **Điều kiện:** P95 latency > 3000ms trong 5 phút liên tục
- **Ảnh hưởng:** Người dùng chờ lâu, UX kém, có thể bỏ qua

### Ba bước kiểm tra đầu tiên

1. **Kiểm tra dashboard latency** — Xem panel Latency để xác nhận P95 vượt ngưỡng và khoảng thời gian bắt đầu.
2. **Kiểm tra retrieval span** — Tìm trace có `correlation_id` trong thời gian đó, xem span `retrieval` có latency cao bất thường không.
3. **Kiểm tra incidents** — Chạy `GET /incidents/enabled` để xem có incident nào đang active không.

### Mitigation tạm thời

- Disable các incident đang enable nếu không cần thiết
- Restart service nếu không có incident rõ ràng
- Scale up nếu tải cao liên tục

### Owner

backend-team

---

## Alert 2: HighErrorRate

- **Tên:** HighErrorRate
- **Severity:** critical
- **Duration:** 3 phút
- **Kênh thông báo:** Slack
- **SLI/SLO liên quan:** `fast_successful_requests` — error rate phải <= 2%
- **Điều kiện:** Error rate > 2% trong 3 phút liên tục
- **Ảnh hưởng:** Người dùng nhận HTTP 500, request thất bại hoàn toàn

### Ba bước kiểm tra đầu tiên

1. **Kiểm tra errors panel** — Xem dashboard errors để xác nhận error rate và loại lỗi.
2. **Lọc logs** — Tìm `event == "request_failed"` trong `data/logs.jsonl`, lấy một `correlation_id`.
3. **Trace lỗi** — Tìm trace với `correlation_id` đó để xác định span gây lỗi.

### Mitigation tạm thời

- Disable incident `tool_fail` nếu đang enable và không cần thiết
- Check service dependencies (vector store, external APIs)
- Rollback prompt version nếu lỗi liên quan đến prompt

### Owner

backend-team

---

## Alert 3: LowRetrievalSuccess

- **Tên:** LowRetrievalSuccess
- **Severity:** warning
- **Duration:** 5 phút
- **Kênh thông báo:** Slack
- **SLI/SLO liên quan:** Retrieval success rate phải >= 90%
- **Điều kiện:** Retrieval success rate < 90% trong 5 phút liên tục
- **Ảnh hưởng:** LLM nhận ít context, câu trả lời kém chất lượng

### Ba bước kiểm tra đầu tiên

1. **Kiểm tra errors panel** — Xem `tool_success` rate trong panel Errors.
2. **Kiểm tra incidents** — Chạy `GET /incidents/enabled`, kiểm tra `tool_fail` incident.
3. **Trace retrieval span** — Tìm trace có `retrieval` span với `doc_count` thấp hoặc `tool_success=false`.

### Mitigation tạm thời

- Disable `tool_fail` incident nếu đang enable
- Check vector store connectivity
- Restart service nếu cần thiết

### Owner

backend-team
