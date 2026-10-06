# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Hoàng Công Minh | 2A202602774 | Cài đặt harness, thí nghiệm, skill và báo cáo |

Tên và mã sinh viên lấy từ tên thư mục bài nộp. Model: `google_genai:gemini-3.5-flash-lite`; `LAB_TEMPERATURE=0` theo mặc định của harness. Provider cảnh báo model dùng sampling cố định nên bỏ qua temperature; không coi đây là thí nghiệm hoàn toàn xác định. `recursion_limit=60`. Deep Agents 0.7.21, Python 3.14.4, Ubuntu WSL trên Windows. Shell không kế thừa môi trường chứa khóa API.

Tag `freeze`: `Chưa đóng băng`. Kiểm thử gốc: **32 passed** (report/tests.txt).

## 2. Giả thuyết (commit TRƯỚC tag `freeze`, Phần 4.0)

- H1 (subagents so với baseline): Điểm đánh giá có thể tương đương baseline, nhưng token trung bình cao hơn ít nhất 20%. Tập học cho thấy việc giao nhiệm vụ lệch vai trò và truyền thiếu quy ước có thể làm mất lợi ích kiểm tra độc lập; guides/pseudocode/02_subagents.md giải thích chi phí và ngữ cảnh cô lập.
- H2 (skills-auto so với baseline): Skill cải thiện check quy ước về code, nhưng không bảo đảm cải thiện toàn bộ tác vụ đánh giá. Skill dữ liệu còn thiếu thứ tự log, phần đầu schema và quy tắc clean.csv; description rộng có thể khiến tác tử đọc nhưng chỉ làm một phần (guides/pseudocode/05_skill_quality.md).
- H3 (tác vụ học so với tác vụ đánh giá): Mức tăng điểm trên tập đánh giá thấp hơn tập học, vì quy ước mới chưa có trong phản hồi học. Cùng một bộ skill có thể cho điểm học khác nhau giữa hai lần chạy; GUIDE Phần 4.2 yêu cầu giữ kết quả trước đóng băng để nhận diện nhiễu.

## 3. Làm quen Deep Agents (Phần 0.3)

1. Công cụ quan sát được trong `report/tour.txt`: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`, `execute`, `task`. `execute` chạy shell.
2. `general-purpose` có cùng khả năng công cụ với tác tử chính. Mỗi lần gọi mặc định không có trạng thái; nó chỉ nhận prompt giao việc và trả về một báo cáo cuối, không tự thấy toàn bộ hội thoại chính.
3. Trích `task`: “Put full detail in the prompt and state exactly what it should return”. Trích `execute`: “Use read_file rather than cat/head/tail.” Prompt mặc định rỗng; harness thêm BASE_PROMPT và PATHS_NOTE để thống nhất đường dẫn tương đối giữa công cụ tệp và shell.

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

| Tác vụ | Check thất bại | Nhóm lỗi (A-G) | Bằng chứng từ detail |
|---|---|---|---|
| code-learn | `tests_not_modified` | G (môi trường CRLF) | the original files in tests/ must not be modified (new test files are allowed) |
| code-learn | `rule_type_hints` | E | RULE: every public function (name not starting with '_') in the package has type annotations on all parameters and on the return value. |
| code-learn | `rule_regression_tests` | E | RULE: add tests/test_regressions.py with one test function per bug you fixed (at least 3); the file must pass. |
| code-learn | `rule_changelog` | E | RULE: record each fix in CHANGELOG.md under the heading '## Unreleased' as a bullet '- fix(<function name>): <short description>' (at least 3 bullets). |
| data-learn | `rule_money_in_cents` | E | RULE: money values in answer.json are integer cents (1606.67 USD is written 160667). |
| data-learn | `rule_meta_block` | E | RULE: answer.json has an object `meta` = {"source": <input file name>, "rows_in": <number of data rows in the input file, duplicates included>, "rows_used": <number of distinct orders with a known amount>}. |
| data-learn | `rule_clean_csv` | E | RULE: write workspace/clean.csv with the header order_id,timestamp_utc,region,amount_cents; one row per distinct order with a known amount; timestamp_utc as YYYY-MM-DDTHH:MM:SSZ (UTC); region in canonical spelling (North, South, East, West); amount in integer cents. |
| logs-learn | `rule_service_names` | E | RULE: service names in the output are lower-case with '-' replaced by '_' (payment-service -> payment_service). |
| logs-learn | `rule_sorted_errors` | E | RULE: `errors` is sorted by service, then by timestamp_utc, ascending. |
| logs-learn | `rule_schema_header` | E | RULE: the top-level object has "schema_version": 2 and "generated_by": "log-triage". |

Có 9 check quy ước thất bại. Đây là nhóm chiếm đa số; skill có thể truyền các quy ước từ feedback, nhưng thiếu quy tắc hoặc mâu thuẫn đề bài vẫn làm thất bại. Các check thuật toán của baseline đều đạt; không có bằng chứng phổ biến cho nhóm A-D.

Check `tests_not_modified` của code-learn thất bại dù trace không sửa test gốc: SHA-256 bản CRLF là `efb5e7650d4f03356e8353d209fbcfe81505ce2fd648bd558d5ada6e8b92ff19`, còn bản LF là `79e05f4cc2e62a4f606d210b0b08a2cc21777245bc2f6ad244a126e9a2aee00d`, đúng hash check gốc. Giữ nguyên tệp được bảo vệ và điểm thô; loại sai lệch môi trường này khỏi diễn giải lỗi tác tử. Không coi việc test visible đạt là bằng chứng mọi quy ước đã đạt.

## 5. Điều kiện `subagents` (Phần 2.3)

Ba vai trò: explorer chỉ đọc đặc tả/dữ liệu và tìm nguyên nhân; implementer sửa và kiểm tra; reviewer kiểm tra độc lập, không sửa. Description chỉ rõ khi nào giao việc. Mỗi subagent nhận PATHS_NOTE; custom subagent không được nạp skill trong điều kiện chính.

| Tác vụ | Điểm | Token | Tool calls chính | Subagent calls |
|---|---:|---:|---:|---:|
| code-learn | 6/10 | 226861 | 15 | 1 |
| data-learn | 3/8 | 321083 | 6 | 2 |
| logs-learn | 6/9 | 236710 | 10 | 1 |

Bằng chứng code-learn: lời gọi `task` giao cả việc sửa code cho `explorer`, dù system prompt của explorer cấm sửa; tác tử chính tiếp tục sửa và chạy pytest. Lời giao nêu đầy đủ đường dẫn và cấm sửa test, nhưng chỉ nhắc chung Acme, không có quy tắc cụ thể. Tác tử con cũng không thể tự suy ra quy ước ẩn từ chỉ dẫn chung này. Trace chỉ ghi luồng chính, không đủ để kiểm chứng mọi thao tác nội bộ của subagent.

Bằng chứng data-learn: explorer nhận yêu cầu viết script; reviewer nhận lời giao ngắn không nhắc lại ranh giới Q1 UTC và đường dẫn workspace đầy đủ. Hai check north_q1_revenue/north_q1_orders thất bại (giá trị đã xuất 3189.59 và 13), dù báo cáo cuối nói đã kiểm tra thành công. Điều này chứng minh kiểm tra độc lập chưa bảo đảm đúng. Logs-learn giao implementer có liệt kê các quy tắc kỹ thuật đầy đủ, nhưng thiếu các quy ước Acme ẩn; kết quả kỹ thuật đạt, rule_ vẫn trượt.

- `code-learn` giao cho: explorer; token so baseline: 226861 / 147969.
- `data-learn` giao cho: explorer, reviewer; token so baseline: 321083 / 215551.
- `logs-learn` giao cho: implementer; token so baseline: 236710 / 71283.

## 6. Self-evolving: skill do curator sinh (Phần 3)

Curator chạy hai lần: lần đầu Gemini trả content dạng list nên parser chưa tách được khối; đã sửa hàm curate_skills để ghép text block rồi chạy lại. Lần hai sinh 2 skill, không sửa tay hoặc xóa skill. Đầu vào chỉ là baseline learning; record có error bị bỏ qua.

| Skill | Tổng quát và đúng/sai | Độ dài và description |
|---|---|---|
| `enforce-code-rules-and-scope` | Quy trình dùng lại cho sửa code; phù hợp feedback về type hints, regression và changelog. Tên test/changelog là quy ước chung, không phải dữ liệu đánh giá. Không xử lý được sai lệch CRLF. | 8 dòng toàn tệp; Use when modifying codebase files, fixing bugs, or implementing tests to ensure scope boundaries and all requirements are respected. |
| `format-canonical-output-data` | Áp dụng cho JSON/CSV; hữu ích cho cents và chuẩn hóa chuỗi. Thiếu quy tắc clean.csv, sort log, schema_version/generated_by. Cụm 'unless explicitly instructed otherwise' và 'when required' có thể khiến tác tử ưu tiên đề bài hơn quy ước ẩn; canonical spelling chưa phân biệt rõ region với service. | 8 dòng toàn tệp; Use when exporting structured data or generating JSON/CSV files to ensure precise schema compliance, canonical names, and unit formatting. |

| Tác vụ | Trước freeze | Sau freeze | Skill đọc trước/sau |
|---|---:|---:|---:|
| code-learn | 7/10 | Chưa chạy | 0/- |
| data-learn | 5/8 | Chưa chạy | 2/- |
| logs-learn | 6/9 | Chưa chạy | 2/- |

Development code-learn chạm GraphRecursionError ở giới hạn 60, đạt 7/10 nhưng trace rỗng và skills_read=0 do phiên bản invoke tối thiểu chưa giữ trạng thái khi lỗi. Không diễn giải số 0 này là bằng chứng chưa đọc skill. Trước freeze, runner được đổi sang stream_mode=values (mở rộng trong pseudo-code 03) để lưu trace và số đếm kể cả khi invoke lỗi; toàn bộ test gốc vẫn đạt. Giữ nguyên lần development thất bại, không loại bỏ hay thay bằng một lần tốt hơn.


## 7. Kết quả so sánh (Phần 4.3, 4.4)

Chưa chạy chính thức; không có số liệu đánh giá.


Run có error: không. Run sửa skill: không.

## 8. Phân tích

Phân tích số liệu chính thức sẽ được điền sau khi freeze và chạy evaluation; chưa có kết luận về hiệu quả trên tập đánh giá.

## 9. Hạn chế và tính hợp lệ

1. Chỉ ba họ tác vụ và một model, nên không suy rộng sang mọi tác vụ hay provider.
2. Sampling của Gemini không tuân theo temperature=0; ba lượt bonus chỉ mô tả dao động, chưa đủ kiểm định thống kê hay tách ảnh hưởng model/provider.
3. Quy ước Acme được thiết kế sẵn và ẩn với tác tử: cải thiện có thể chủ yếu là truyền quy tắc từ feedback, không thể kết luận khả năng lập trình tổng quát đã tăng.
4. Checkout Windows dùng CRLF gây sai lệch check hash test. Giữ điểm thô để tái lập; điều này làm thấp điểm code và gây nhiễu việc phân loại kỹ thuật/quy ước.
5. Trace bị cắt từng message ở 1.500 ký tự và không chứa thao tác bên trong subagent; lần development dùng invoke mất trace khi lỗi, các lần chính thức dùng stream để giữ trạng thái cuối. Không suy diễn hành vi không quan sát được. Thư mục tạm chỉ cô lập bản sao dữ liệu; LocalShellBackend không phải ranh giới bảo mật của hệ điều hành.

## 10. Kết luận

Harness đạt bộ kiểm thử offline; chưa có kết luận về tập đánh giá trước freeze.

## Phụ lục

### Lệnh và khả năng tái lập

Chạy trên Linux/WSL, cài `python -m venv .venv-wsl`, kích hoạt môi trường và `pip install -e .`; sử dụng `.env` riêng. Không đưa khóa vào repo. Xem `report/reproduce.sh` cho tập học và `report/run-frozen.sh` cho phần chính thức/bonus. Curator đã chạy 2 lần. Git commit `hypotheses` đứng trước commit/tag freeze; không tạo lại tag sau evaluation. Kết quả development giữ ở `results/skills-auto-dev`.

### Bonus 6e: lặp để đo nhiễu

Thiết kế: lượt chính thức và hai lượt bổ sung, cùng model, recursion_limit, tập tác vụ và hash skill. Không sinh lại hoặc chỉnh skill. Hai lượt thêm nằm riêng trong `results/bonus-6e/repeat-2` và `repeat-3`, không tham gia bảng kết quả chính. Chạy tuần tự từng điều kiện.

| Điều kiện | Tác vụ đánh giá | Điểm ba lượt | Trung bình | Min–max | Token trung bình |
|---|---|---|---:|---|---:|

Số lượt bổ sung đã lưu: 0/18. Phân tích cơ chế dựa vào trace của từng lượt, gồm lời gọi task, read_file skills và nội dung trả về; không gán mọi thay đổi điểm cho skill. Hạn chế: ba lượt mỗi tác vụ vẫn ít, thứ tự chạy cố định và điều kiện hạ tầng có thể thay đổi. Bước tiếp theo: đảo thứ tự điều kiện và tăng lượt chạy.

Số lần chạy chính thức/development đã giữ: 9; bonus bổ sung: 0; không tính lần gọi curator và tour vào số tác vụ. Nội dung báo cáo này được tổng hợp từ run.json bằng `python report/build_report.py`.

