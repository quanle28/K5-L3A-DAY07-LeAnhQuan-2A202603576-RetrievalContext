# Định dạng dữ liệu

**Dữ liệu bài làm:** `chunks.json` có 281 chunk B của DAY06; `questions.json` có 24 câu (17 dev/7 test), `answerable` boolean và `gold` là các nguồn thay thế. Câu thiếu bằng chứng có `gold: []` cùng absence audit. `frozen.json` giữ checksum. `pages.jsonl`/`day6_manifest.json`/`LICENSE-PYTHON.txt` giữ nội dung và provenance. `page` là đơn vị text DAY06, không phải trang PDF. Dùng `python -m src ...` với dữ liệu thật; baseline mẫu bên dưới chỉ hỗ trợ câu có gold. Xem [bài làm](../SOLUTION.md).

Các file `example_*.json` chỉ minh họa định dạng, không đủ để nộp bài. Dữ liệu thật là JSON array UTF-8; nếu dùng định dạng khác, ghi cách chuyển trong README.

- **Chunk:** `id`, `text`, `source_id`, `source`, `page`, `metadata`. ID phải duy nhất; giữ phiên bản hoặc ngày nếu có.
- **Câu có đáp án:** `id`, `split` (`dev` hoặc `test`), `question`, `expected_answer`, `gold`: danh sách `{source_id, page, evidence}`. Với schema mẫu, mỗi evidence phải nằm trọn trong một chunk đúng nguồn và trang; các phần tử `gold` là evidence thay thế. Với câu multi-hop cần nhiều đoạn, bạn có thể mở rộng schema, ghi rõ nhóm evidence bắt buộc và cách chấm. Có thể thêm `filter` do người dùng cung cấp trước.
- **Câu thiếu evidence:** `id`, `split`, `question`, `answerable: false`, `expected_behavior: "search_and_abstain"`, `absence_reason`. Xem `agent_cases_example.json`.

Không đưa `gold` hoặc nhãn đáp án vào model và retrieval tool. Ghi nguồn dữ liệu và quyền sử dụng. Cách chuyển một số định dạng Day 6: [starter/README.md](../starter/README.md).
