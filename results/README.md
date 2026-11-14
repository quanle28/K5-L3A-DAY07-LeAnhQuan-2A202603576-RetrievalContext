# Kết quả thực chạy

Kết quả được tạo từ embedding BGE thật, Qdrant DAY06 B thật và GPT-4o-mini qua OpenRouter. Mock chỉ dùng trong unittest. Benchmark gồm 17 dev và 7 test; test chạy baseline và cấu hình được chọn sau khi khóa dev.

- `retrieval/dev/summary.json`: bốn cấu hình, truy vấn gốc, không gọi LLM.
- `retrieval/test/summary.json`: baseline và cấu hình đã chốt.
- `agent/dev/summary.json`, `agent/test/summary.json`: retrieval/context từ tool calls thật, thời gian và phí.
- `agent/selection.json`: lựa chọn, thời điểm khóa, checksum code/data/config và review dev trước test.
- `agent/<split>/<config>/traces.json`: query gốc/viết lại, tool calls/arguments/results, context cuối, answer/citations, model/token usage/cost/errors.
- `agent/<split>/<config>/reviews_ai.json`: nhãn câu trả lời 0–2, từng citation, lý do; test thêm context grade 0–2.
- `agent/<split>/<config>/agent_metrics_ai.json`: tổng hợp nhãn bằng starter metric, không suy điểm từ citation ID.
- `run_info.json`: model, nguồn dữ liệu, phí toàn benchmark, môi trường đo và phạm vi phép đo.
- `verification.json`: kiểm tra Python 3.13 và tái lập retrieval.
- `requirements-lock-benchmark.txt`, `requirements-lock-py313.txt`: thư viện lần đo gốc và môi trường 3.13.

Nhãn review được **Codex (AI) đọc đối chiếu**, không phải nhãn đã được học viên/giảng viên xác nhận. Không đổi gold sau khi thấy kết quả DAY07. Retrieval và generation là hai tầng khác nhau; pipeline có context tốt hơn vẫn có thể suy đoán hoặc gán sai citation. Báo cáo giữ cả các kết quả kém hơn baseline.

Các lần thử thiết lập ban đầu có lỗi kết nối mạng, schema tool thiếu trường, console Windows chưa UTF-8 và một lần unittest tranh chấp khóa Qdrant với benchmark đang chạy. Các lỗi được khắc phục trước benchmark đã nộp; không dùng kết quả lỗi đó để báo điểm. Khi dùng Qdrant local, chạy các lệnh lần lượt. Chi phí benchmark không gồm các smoke test ban đầu/cài thư viện/model download; không đo điện năng hay phần cứng.
