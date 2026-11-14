# Thiết kế bài làm

## Liên kết DAY06

DAY06 thực hiện ingestion → chuẩn hóa → chunk → embedding BGE → Qdrant. DAY07 tái sử dụng **281 chunk B**, ID SHA-256, 384 chiều, cosine exact, revision ONNX và checksum trong `data/model_lock.json`. Snapshot Python Tutorial v3.12.0 có 10 chương, 77 đơn vị text logic. Trường `page` là số đơn vị text của DAY06, **không phải số trang PDF**. Giấy phép PSF lưu cùng dữ liệu.

Hai repo đều có package `src`; adapter nạp mã DAY06 bằng alias `day6_lab_src` để tránh nhầm package. Index được sao chép sang cache DAY07; cache query mới cũng ghi DAY07. Adapter kiểm tra dimension, cosine và toàn bộ tập ID trong index khớp export đã khóa. Không ingest/gán ID mới vào dữ liệu DAY06.

## Ba cách retrieval

1. **Dense:** query embedding bằng chính `MyEmbedder.query_embed` DAY06, không thêm prefix mới; Qdrant exact cosine trên `day6_B`.
2. **BM25:** k1=1.5, b=0.75, token Unicode casefold; giữ identifier Python và `/`, `//`, `%`, `**`. Không dùng embedding.
3. **Hybrid:** lấy 20 candidate từ mỗi retriever (hoặc top-k nếu lớn hơn), hợp nhất Reciprocal Rank Fusion `sum(1/(60+rank))`; không cộng trực tiếp cosine và BM25. Trace lưu rank và score từng thành phần.

Filter equality allowlist: chapter/language/version/document_id/page. Các câu benchmark có phạm vi chương do người dùng nêu ngay trong câu hỏi; chỉ truyền `filter` tương ứng, không suy ra từ gold. Cùng filter áp dụng cho cả BM25 và dense.

Context giữ chunk nguyên vẹn, nguồn và số đơn vị nguồn; loại ID trùng và text trùng trong cùng đơn vị nguồn. Đo ngân sách bằng số ký tự Unicode kể cả header và dấu phân cách, không gọi là token budget. Chunk không vừa bị bỏ qua; không cắt dở evidence. Context đa lượt cộng dồn theo thứ tự truy xuất; các đoạn cũ có thể chiếm ngân sách của kết quả mới — giới hạn này được công bố.

## Agent thật

Model gọi function `search(query)` và nhận context, sau đó chọn tìm tiếp hoặc `finish(answer,citations,abstain)`. Lượt đầu bị buộc tìm kiếm; đạt giới hạn thì buộc finish. Cấu hình `hybrid_context` cho tối đa 2 search, 6 hit/lượt, 6.000 ký tự; cấu hình khác 1 search, 3 hit, 1.800 ký tự. Có tối đa `max_searches + 2` lượt model. Không có gold, expected answer hay absence_reason trong model prompt hoặc retriever.

Document/tool results được đánh dấu untrusted. Giữ context mới nhất trong tool message; context cũ được đánh dấu superseded để không nhân ngân sách. Đây là chỉ dẫn phòng prompt injection, không phải chứng minh tuyệt đối chống mọi tấn công.

Citation phải thuộc context cuối, duy nhất và khớp marker trong answer. Nếu model gửi citation list hợp lệ nhưng quên marker, runtime thêm marker từ đúng danh sách đó, ghi event `render_citation_markers`. Không tự chọn nguồn thay model. Raw tool call và answer trước định dạng vẫn nằm trong trace. ID hợp lệ không đồng nghĩa nguồn hỗ trợ câu trả lời; bước review ngữ nghĩa đánh giá riêng điều này.

Nếu model tự từ chối, runtime xuất câu từ chối cố định để không lẫn suy đoán. Citation sai/thiếu hay giới hạn tìm kiếm dẫn đến abstention có lý do; lỗi kết nối/schema/tool được ghi `error`, giữ trace và usage đã dùng. Không mock/fallback trong benchmark.

## Thí nghiệm và giới hạn

Gold đóng băng trước retrieval. Dev cũ DAY06 được tái dùng với hai alternative đã công bố trong audit cũ. Năm câu test DAY06 đã phân tích được bỏ; test DAY07 là 5 sự kiện mới và 2 câu thiếu evidence. Câu hỏi test được soạn từ corpus trước retrieval, không khẳng định đây là benchmark do bên thứ ba giữ kín.

Retrieval Hit@1/3 dùng cùng cutoff và một chunk chứa trọn một alternative quote, đúng nguồn/đơn vị. Context Evidence Rate kiểm tra gold trong context cuối. Với agent, Hit@1/3 dùng lượt search đầu; context cộng dồn có thể nhiều lượt. Câu không có đáp án bị loại khỏi mẫu số retrieval và được chấm abstention riêng. Nhãn answer/citation/context do Codex đọc đối chiếu, ghi rõ AI và chưa được học viên xác nhận; không dùng substring để tự suy điểm câu trả lời.

Chọn cấu hình theo `config.json` và khóa trước test trong `results/*/selection.json`, có checksum dữ liệu lẫn runtime code. Chất lượng câu trả lời và chi phí được đọc cùng kết quả dev để công bố đánh đổi. Không sửa pipeline theo test đã mở. Test còn 7 câu nên không suy rộng sang toàn bộ Python, tiếng Việt hay tài liệu scan. Phần nâng cao 100 trang có bảng/ảnh/biểu đồ nằm ngoài phạm vi bài làm này.
