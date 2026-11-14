"""Build a report only from saved real traces and explicit AI semantic labels."""
from __future__ import annotations

import csv
import platform
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.common import load, now, save


def fraction(r):
    return f'{r["n"]}/{r["N"]}' + (f' ({100 * r["n"] / r["N"]:.1f}%)' if r["N"] else " (N/A)")


def main():
    config = load(ROOT / "config.json")
    retrieval_rows, model_rows, quality_rows, experiment_log = [], [], [], []
    all_traces, all_labels = [], []
    for split in ("dev", "test"):
        retrieval = load(ROOT / "results/retrieval" / split / "summary.json")
        for name, m in retrieval.items():
            retrieval_rows.append(f'| {name} | {split} | {fraction(m["hit1"])} | {fraction(m["hit3"])} | {fraction(m["context_hit"])} | {m["median_seconds"] * 1000:.2f} ms |')
            experiment_log.append({"configuration": name, "split": split, **config["experiments"][name],
                **{key: fraction(m[key]) for key in ("hit1", "hit3", "context_hit")}, "retrieval_api_cost_usd": 0})
        summary = load(ROOT / "results/agent" / split / "summary.json")
        for name, m in summary.items():
            folder = ROOT / "results/agent" / split / name
            traces = load(folder / "traces.json")
            labels = load(folder / "reviews_ai.json")
            quality = load(folder / "agent_metrics_ai.json")
            all_traces.extend(traces)
            all_labels.extend([{**r, "configuration": name, "split": split} for r in labels])
            model_rows.append(f'| {name} | {split} | {fraction(m["hit1"])} | {fraction(m["hit3"])} | {fraction(m["context_hit"])} | {m["total_seconds"]:.2f} s | ${m["cost_usd"]:.6f} |')
            grades = quality["grounded_answer"]
            distribution = ", ".join(f'{k} lượt: {v} câu' for k, v in quality["search_count_distribution"].items())
            quality_rows.append(f'| {name}/{split} | {fraction(quality["tool_use"])} | {distribution} | {grades["0"]}/{grades["1"]}/{grades["2"]}; {grades["mean"]:.2f}/2 | {fraction(quality["citation_validity"])} | {fraction(quality["answer_citation_coverage"])} | {fraction(quality["abstention"])} | {fraction(quality["false_abstention"])} |')
    with (ROOT / "results/experiment_log.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(experiment_log[0]))
        writer.writeheader()
        writer.writerows(experiment_log)
    usage = Counter()
    for t in all_traces:
        for call in t["llm_calls"]:
            usage.update({k: call["usage"].get(k, 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")})
    info = {"generated_at_utc": now(), "benchmark_python": "3.9.7 (existing Day 6 .venv-lab)",
        "verification_python": load(ROOT / "results/verification.json")["python"],
        "models_returned_by_provider": sorted({call["model"] for t in all_traces for call in t["llm_calls"]}),
        "model_configured": "openai/gpt-4o-mini", "endpoint": "https://openrouter.ai/api/v1",
        "model_limitations": "Provider model alias and upstream routing are not an immutable weight snapshot; stochastic/hosted output may vary despite temperature=0.",
        "cases_executed": len(all_traces), "llm_calls": sum(len(t["llm_calls"]) for t in all_traces),
        "usage": dict(usage), "benchmark_api_cost_usd": sum(t["cost_usd"] for t in all_traces),
        "cost_basis": "OpenRouter usage.cost reported for each call, not estimated rates; excludes initial smoke trials, hardware/electricity and package/model download",
        "total_case_seconds": sum(t["elapsed_seconds"] for t in all_traces),
        "errors": sum(t["status"] == "error" for t in all_traces),
        "review": "Codex AI semantic labels; no human confirmation claimed",
        "data": load(ROOT / "data/frozen.json"), "model_lock": load(ROOT / "data/model_lock.json")}
    save(ROOT / "results/run_info.json", info)
    report = f'''# Báo cáo DAY07 — Agentic RAG

**Le Anh Quan · 2A202603576 · L3A · 14/11/2026**

Bài làm phần cơ bản đã có code, ba phương pháp retrieval, model/tool calling thật, benchmark dev/test, thử nghiệm, trace và đánh giá. Không thực hiện bonus tài liệu 100 trang. Nhãn ngữ nghĩa dưới đây do **Codex (AI) đọc đối chiếu** câu trả lời, context và nguồn; chưa được học viên xác nhận, không gọi là đánh giá thủ công của học viên.

## Dữ liệu và nối DAY06

Tái dùng Python Tutorial v3.12.0 của CPython, giấy phép PSF (bản chép tại `data/LICENSE-PYTHON.txt`). 10 chương, 77 đơn vị text logic, 281 chunk chiến lược B (đoạn tối đa 900 ký tự, không overlap). `page` là số đơn vị nguồn DAY06, không phải số trang PDF. Chép index Qdrant thật sang `.cache/qdrant`, giữ collection `day6_B`, ID, metadata và vector. `data/frozen.json` lưu checksum; `day6_manifest.json` truy vết tới file RST gốc và GitHub snapshot.

Embedding **BAAI/bge-small-en-v1.5**, ONNX lượng tử, 384 chiều, cosine exact; khóa revision `aa8f8b060edb00e03bfdd08813a2949946c8ba55` và checksum từng file ở `data/model_lock.json`. Query dùng `query_embed` tương thích DAY06, không thêm prefix. Model agent **GPT-4o-mini** qua OpenRouter, temperature 0; tên thực trả về ghi từng call. Model hosted dùng alias nên không hứa đầu ra tái lập từng byte.

Benchmark có **24 câu**: dev 15 có đáp án + 2 thiếu bằng chứng; test 5 có đáp án + 2 thiếu bằng chứng. Dev tái dùng 15 câu DAY06 và đóng băng alternative q07/q13 đã có trong audit cũ. Test DAY06 đã được phân tích nên **không tái dùng**; test mới hỏi các sự kiện khác trong stdlib/stdlib2. Gold được chọn từ nguồn trước retrieval. Câu thiếu evidence được kiểm tra trên toàn bộ 77 đơn vị nguồn, không dựa vào top-k: TaskGroup timeout, sqlite isolation mặc định, Django rollback và pip require-hashes.

## Cấu hình và tiêu chí chọn

| Tên | Phương pháp | top-k | Context ký tự | Search tối đa | Giả thuyết |
|---|---|---:|---:|---:|---|
| dense_base | BGE/Qdrant B | 3 | 1800 | 1 | Baseline nối DAY06 |
| bm25 | BM25 k1=1.5, b=.75 | 3 | 1800 | 1 | Tên API/operator khớp từ khóa |
| hybrid | Dense + BM25 RRF | 3 | 1800 | 1 | Cải thiện 1: kết hợp ngữ nghĩa và từ khóa |
| hybrid_context | Dense + BM25 RRF | 6 | 6000 | 2 | Cải thiện 2: thêm evidence và cho phép tìm tiếp |

Hybrid lấy 20 candidate mỗi nhánh, hợp nhất `sum(1/(60+rank))`, không cộng trực tiếp raw score. Mọi phương pháp dùng cùng corpus/gold; filter chapter chỉ có ở câu người dùng nêu phạm vi. Trace ghi filter, query gốc và query model thực dùng. Không rerank bổ sung. Cải thiện 2 thay đồng thời top-k, budget và search limit, vì vậy chỉ kết luận về gói cấu hình, chưa cô lập từng yếu tố.

Quy tắc chốt trong `config.json`: ưu tiên dev Context Evidence Rate, rồi Hit@3, Hit@1; hòa thì chọn budget nhỏ, ít search, rồi tên cấu hình. Đọc thêm nhãn ngữ nghĩa và công bố đánh đổi trước test. `results/agent/selection.json` có timestamp, checksum runtime/data/config và checksum review dev. Cấu hình chọn là **hybrid_context**; không đổi sau khi mở test.

## Retrieval trên truy vấn gốc

Hit@1/3: có ít nhất một alternative quote đầy đủ trong một chunk đúng nguồn/đơn vị; Context Evidence Rate: quote tồn tại trong context cuối. Các câu thiếu evidence không vào mẫu số. Chỉ số substring là proxy bảo thủ, không tự đánh giá câu trả lời. Phí API retrieval local là 0 USD; thời gian truy vấn có cả cache hit/miss, không gồm khởi tạo model/cài đặt/index. Dense chạy trước và làm ấm cache query cho hybrid; không kết luận hybrid nhanh hơn dense từ chênh lệch này.

| Cấu hình | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Trung vị/query |
|---|---|---|---|---|---|
{chr(10).join(retrieval_rows)}

## Agent thật và context

Model dùng tools `search(query)` và `finish(answer,citations,abstain)`. Lượt đầu buộc search; còn lượt thì model có thể đổi query; hết lượt buộc finish. Các context cũ được đánh dấu superseded trong hội thoại; chỉ context cộng dồn mới nhất gửi lại. Context giữ nguyên đoạn, nguồn, đơn vị nguồn, loại trùng; budget tính cả header. Không đưa gold/expected answer/absence_reason vào runtime.

Runtime kiểm tra citation thuộc context cuối; nếu model chỉ trả danh sách ID hợp lệ, thêm marker từ danh sách đó và ghi event. Đây là định dạng citation, không phải xác minh ngữ nghĩa. Model từ chối được chuẩn hóa thành một câu từ chối không suy đoán. Lỗi provider/tool/schema giữ `status=error`, không đổi thành abstention. Nội dung nguồn là untrusted data.

Agent có thể viết lại query, kể cả lượt đầu dù prompt khuyến khích giữ nguyên. Vì vậy bảng dưới dùng ranking của **tool call đầu**, được báo riêng với bảng truy vấn gốc ở trên; Context Evidence Rate tính context cộng dồn cuối cùng.

| Cấu hình | Split | Hit@1 lượt đầu | Hit@3 lượt đầu | Context Evidence Rate | Tổng thời gian | Phí API thật |
|---|---|---|---|---|---|---|
{chr(10).join(model_rows)}

## Đánh giá ngữ nghĩa AI

Grade answer: 0 = sai/không có evidence, 1 = đúng một phần hoặc thiếu grounding/citation điều kiện, 2 = đúng đủ và có evidence. Citation được đọc đối chiếu riêng từng ID, không chỉ kiểm tra tồn tại. Điểm context test: 0 = không có evidence, 1 = thiếu điều kiện/nguồn, 2 = đủ. Chi tiết từng câu/citation và lý do ở `reviews_ai.json`; `human_confirmed=false`.

| Cấu hình/split | Tool use | Phân bố search | Answer 0/1/2; TB | Citation hỗ trợ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
{chr(10).join(quality_rows)}

Context test baseline: **2 câu mức 0, 0 mức 1, 3 mức 2**. Cấu hình chọn: **0 mức 0, 0 mức 1, 5 mức 2**. Đã đọc toàn bộ 5 câu có đáp án và 2 câu thiếu evidence cho cả baseline lẫn cấu hình chọn. Xem phụ lục `report/individual/TEST_REVIEW.md`.

## Hai lỗi dev và phép thử trước/sau

1. **d7-q04 — break trong vòng lặp lồng nhau.** Dense query gốc không có định nghĩa trong top-3. BM25 đưa định nghĩa lên top-1; hybrid đưa vào top-3. Tuy nhiên budget 1800 ký tự bỏ chunk dài, khiến agent dense/hybrid trả lời từ kiến thức chung và gán citation loop-else. Gói 6000 ký tự giữ định nghĩa trong context; ngữ nghĩa câu trả lời đúng hơn nhưng model vẫn trích example thay định nghĩa. Đây là phần lỗi generation/citation còn lại, không coi là đã sửa hoàn toàn.
2. **d7-q02 — chuỗi bất biến.** Query gốc dense/hybrid tìm được evidence trong top-3 nhưng context nhỏ chỉ giữ indexing/slicing, dẫn tới khẳng định thiếu nguồn. Gói 6000 giữ đoạn immutable/TypeError và agent trích đúng nguồn, grade từ 0 lên 2. Bảng đo cả cấu hình không cải thiện: hybrid nhỏ có Hit@3 cao nhưng context thấp hơn dense baseline.

Các lỗi khác: BM25 q13 lẫn exception chaining với with-file cleanup; context lớn q14 tự mở rộng từ text sang binary sai; q03 diễn đạt -0 không hợp lệ dù -0 thực chất bằng 0; q10 có evidence deque nhưng trích nhầm queue.Queue. Dev sqlite isolation vẫn bị suy đoán ở cấu hình chọn, trong khi BM25 từ chối đúng. Tăng context không đảm bảo abstention hoặc citation tốt hơn.

## Test và đánh đổi đã quan sát

Trên test, cấu hình chọn có context đủ **5/5** so với baseline **3/5**; điểm answer AI **1.80/2** so với **1.20/2**. Tuy nhiên citation hỗ trợ toàn bộ test chỉ **4/14**, thấp hơn baseline **3/6**, vì thêm citation thừa/sai và trả lời hai câu ngoài corpus. Abstention đúng giảm từ **2/2** xuống **0/2**. Không điều chỉnh pipeline sau kết quả này và không tuyên bố cấu hình chọn tốt hơn mọi mặt.

Ví dụ tốt: test `d7-t02` cấu hình chọn tìm stdlib/1 và trả `sys.argv` dạng list, có nguồn hỗ trợ. Ví dụ từ chối đúng: baseline `d7-u04` nói không đủ bằng chứng về pip require-hashes. Ví dụ lỗi: cấu hình chọn `d7-u03` sinh lệnh Django rollback dù corpus không có Django, rồi trích các đoạn pip/exception; đánh giá abstention sai, mọi citation đều không hỗ trợ.

## Tái lập, chi phí và giới hạn

Tổng benchmark agent **{info['cases_executed']} lượt câu hỏi**, **{info['llm_calls']} model calls**, **{usage['prompt_tokens']} input token + {usage['completion_tokens']} output token**, phí báo bởi OpenRouter **${info['benchmark_api_cost_usd']:.6f}**; tổng thời gian các câu **{info['total_case_seconds']:.2f}s**, không gồm cài đặt/khởi tạo/download/smoke thử trước benchmark. Không có lỗi provider trong lần benchmark đã nộp. Phí lấy `usage.cost`; điện năng/phần cứng không đo. Token input đã bao gồm system/tool/schema theo usage provider, không nhầm budget ký tự thành token.

Môi trường benchmark dùng Python 3.9.7 DAY06 đã có FastEmbed 0.6.1, ONNX Runtime 1.19.2, Qdrant-client 1.15.1. Môi trường riêng Python 3.13 được cài và chạy **26/26 unittest**, gồm kết nối BGE/Qdrant thật; phiên bản đầy đủ và so sánh fresh query embeddings/ranking lưu `results/verification.json`. Các test fake chỉ kiểm tra luồng điều khiển, không được báo làm chất lượng agent.

Hướng dẫn lệnh ở `SOLUTION.md`; runtime `src/`, config `config.json`, benchmark/data `data/`, traces/metrics/reviews `results/`, thiết kế `docs/ARCHITECTURE.md`. Script review chỉ mã hóa nhãn của lần đã đọc; không dùng để tự chấm lần sinh khác. Cần học viên đối chiếu và xác nhận nhãn trước khi trình bày. Test đã mở sau lần này phải xem là tập đã biết nếu phát triển tiếp; tạo holdout mới để báo đánh giá độc lập.

Giới hạn: test nhỏ, câu tiếng Anh trong một tutorial, chuẩn hóa DAY06 làm mất thụt dòng code, gold còn có thể thiếu nguồn tương đương (q05/q08 có evidence khác hỗ trợ), model có thể dùng kiến thức ngoài corpus bất chấp prompt; citation validator chỉ kiểm tra ID. Bộ này chưa có câu multi-hop bắt buộc nhiều nguồn, OCR hay nội dung trực quan. Phần nâng cao không làm và không yêu cầu điểm bonus.

Nguồn: [CPython snapshot v3.12.0](https://github.com/python/cpython/tree/v3.12.0/Doc/tutorial), [BGE](https://huggingface.co/BAAI/bge-small-en-v1.5), [OpenRouter tool calling](https://openrouter.ai/docs/guides/features/tool-calling), [model/pricing](https://openrouter.ai/openai/gpt-4o-mini). Giá tham khảo 0.15 USD/M input, 0.60 USD/M output; báo cáo sử dụng phí provider trả về, không suy từ giá tham khảo.
'''
    (ROOT / "report/individual/2A202603576_LeAnhQuan.md").write_text(report, encoding="utf-8")
    appendix = ["# Đối chiếu toàn bộ test (AI review)", "", "Codex đọc đối chiếu; chưa có xác nhận của học viên. Không đổi cấu hình theo test.", ""]
    for name in ("dense_base", "hybrid_context"):
        folder = ROOT / "results/agent/test" / name
        labels = {r["query_id"]: r for r in load(folder / "reviews_ai.json")}
        appendix.extend([f"## {name}", ""])
        for t in load(folder / "traces.json"):
            r = labels[t["query_id"]]
            appendix.extend([f'### {t["query_id"]}', "", t["question"], "", t["answer"], "",
                f'Context grade: {r.get("context_grade", "N/A")}; answer grade: {r.get("answer_grade", "N/A")}; abstention correct: {r.get("abstention_correct", "N/A")}.', "",
                r["reason"], "", "Citation support: " + str(r["citation_support"]), "",
                f'Trace: `results/agent/test/{name}/traces.json`, query_id `{t["query_id"]}`.', ""])
    (ROOT / "report/individual/TEST_REVIEW.md").write_text("\n".join(appendix), encoding="utf-8")
    print(f"Built report: {len(all_traces)} real agent traces, API cost ${info['benchmark_api_cost_usd']:.6f}")


if __name__ == "__main__": main()
