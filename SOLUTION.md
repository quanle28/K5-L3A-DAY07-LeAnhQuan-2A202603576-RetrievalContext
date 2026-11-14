# Chạy bài lab DAY07

Học viên: Le Anh Quan · MSSV 2A202603576 · L3A. Bài làm phần cơ bản: dense/BM25/hybrid retrieval, agent gọi model thật, benchmark 24 câu, thử nghiệm dev và đánh giá test sau khi chốt. Phần nâng cao tài liệu 100 trang không thực hiện.

## Mở lại trên máy hiện tại

Mở PowerShell tại thư mục DAY07. `.env` đã được cấu hình cục bộ cho OpenRouter, không đưa vào Git. Chạy từng lệnh lần lượt vì Qdrant local chỉ cho một tiến trình mở index.

```powershell
.\.venv\Scripts\python.exe -m src check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m src ask --question "Why does Python reject assigning to a string index?"
```

`ask` mặc định dùng `hybrid_context`, ghi trace vào `results/demo.json`; benchmark đã đo nằm trong `results/agent/`. Nếu đổi model, trace lưu model thực tế, usage và phí từ OpenRouter. Chi phí chưa biết được ghi `null`, không tự coi là miễn phí.

## Cài lại

Đặt DAY06 và DAY07 cạnh nhau như `day6_root` trong `config.json`. DAY06 cần có `starter/src/`, `starter/model_lock.json`, dữ liệu và model BGE đã khóa. Cấu hình hiện tại giữ ID, nguồn, đơn vị nguồn và vector của collection `day6_B`.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Sửa .env bằng trình soạn thảo: không dán khóa vào mã nguồn hay commit.
.\.venv\Scripts\python.exe scripts\restore_index.py
.\.venv\Scripts\python.exe -m src check
```

Muốn khóa chính xác thư viện của môi trường đã kiểm tra, dùng `results/requirements-lock-py313.txt`. Lần benchmark gốc dùng môi trường DAY06 (Python 3.9.7); Python 3.13 được kiểm tra riêng để đáp ứng yêu cầu 3.11+ và kết quả kiểm tra được lưu trong `results/verification.json`.

`restore_index.py` sao chép index thật DAY06 nếu còn cache. Nếu không có index, script tạo lại B bằng các chunk đã chốt và embedding thật cùng model/revision. Model khóa chưa có trên máy sẽ cần mạng để tải qua adapter DAY06. Script không thay vector bằng số ngẫu nhiên. `.cache/`, `.venv/` và `.env` đều bị Git bỏ qua.

`python -m src prepare` chỉ dùng lúc tạo bộ dữ liệu lần đầu từ DAY06. Trên bản bài nộp đã có `data/frozen.json`, lệnh chỉ xác minh checksum. Khôi phục index bằng script riêng ở trên.

## Tái chạy thí nghiệm

Các kết quả lần nộp hiện tại được giữ để đối chiếu. Trước khi đo một thí nghiệm mới, chuyển thư mục `results/agent` và `results/retrieval` sang một thư mục lưu trữ riêng trong dự án; giữ nguyên bản gốc. Khi thay code/cấu hình sau khi đã mở test, tập test này trở thành tập đã biết, không còn là holdout độc lập cho lần cải tiến tiếp theo.

```powershell
.\.venv\Scripts\python.exe -m src retrieval --split dev
.\.venv\Scripts\python.exe -m src agent --split dev
# Đọc từng answer/citation/context, lập reviews.json theo BENCHMARK.md.
# Không dùng review_dev.py để tự chấm một lần sinh mới: nhãn script đó thuộc lần đã nộp.
# Chốt lựa chọn sau khi xem dev, rồi mới chạy test.
.\.venv\Scripts\python.exe -m src retrieval --split test
.\.venv\Scripts\python.exe -m src agent --split test
```

Test yêu cầu checksum dữ liệu, cấu hình và code giống dev; từ chối ghi đè test đã hoàn thành. Lỗi API/vector store giữ thành `status=error` cùng trace trước lỗi, không chuyển thành câu trả lời giả. Lệnh dừng sớm khi câu đầu lỗi để tránh tiếp tục tốn phí do cấu hình sai. Trace từng cấu hình được lưu sau mỗi câu; một dev run mới sẽ chạy lại toàn bộ, không tự resume.

## Tệp chính

| Tệp | Vai trò |
|---|---|
| `config.json` | 4 cấu hình, giả thuyết, top-k/context/search limits và tiêu chí chọn |
| `src/retrieval.py` | BGE + Qdrant thật, BM25, RRF, lọc metadata, dedup/context budget |
| `src/agent.py` | Tool calling `search`/`finish`, nhiều lượt, citation validation, lỗi/abstention |
| `src/llm.py` | HTTP client tương thích OpenAI; khóa chỉ đọc từ môi trường/.env |
| `src/experiment.py` | Tách dev/test, khóa checksum, metrics và incremental traces |
| `data/questions.json` | 15+2 dev, 5+2 test mới; gold chỉ dùng ngoài runtime agent |
| `data/frozen.json` | Nguồn, giấy phép, checksum và lịch sử chia tập |
| `results/agent/*/*/reviews_ai.json` | Nhãn AI đọc đối chiếu, lý do và từng citation; chưa xác nhận bởi học viên |
| `scripts/build_report.py` | Tổng hợp báo cáo từ artifacts đã đo và đã review |

Chi tiết luồng dữ liệu và giới hạn: [ARCHITECTURE.md](docs/ARCHITECTURE.md). Yêu cầu chấm bài gốc giữ trong README, GUIDE, RULES, BENCHMARK và RUBRIC.
