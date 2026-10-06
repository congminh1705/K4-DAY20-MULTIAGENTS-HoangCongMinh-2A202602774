# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Hoàng Công Minh | 2A202602774 | Cài đặt harness, thí nghiệm, skill và báo cáo |

Tên và mã sinh viên lấy từ tên thư mục bài nộp. Model: `google_genai:gemini-3.5-flash-lite`; `LAB_TEMPERATURE=0` theo mặc định của harness. Provider cảnh báo model dùng sampling cố định nên bỏ qua temperature; không coi đây là thí nghiệm hoàn toàn xác định. `recursion_limit=60`. Deep Agents 0.7.21, Python 3.14.4, Ubuntu WSL trên Windows. Shell không kế thừa môi trường chứa khóa API.

Tag `freeze`: `01798deb5bd204abbfffd5189dab056b0d6f5b64`. Kiểm thử gốc: **32 passed** (report/tests.txt).

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
| code-eval | 6/11 | 437271 | 25 | 3 |
| code-learn | 6/10 | 226861 | 15 | 1 |
| data-eval | 4/9 | 157436 | 8 | 1 |
| data-learn | 3/8 | 321083 | 6 | 2 |
| logs-eval | 6/10 | 113243 | 12 | 0 |
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
| code-learn | 7/10 | 8/10 | 0/2 |
| data-learn | 5/8 | 5/8 | 2/2 |
| logs-learn | 6/9 | 6/9 | 2/2 |

Development code-learn chạm GraphRecursionError ở giới hạn 60, đạt 7/10 nhưng trace rỗng và skills_read=0 do phiên bản invoke tối thiểu chưa giữ trạng thái khi lỗi. Không diễn giải số 0 này là bằng chứng chưa đọc skill. Trước freeze, runner được đổi sang stream_mode=values (mở rộng trong pseudo-code 03) để lưu trace và số đếm kể cả khi invoke lỗi; toàn bộ test gốc vẫn đạt. Giữ nguyên lần development thất bại, không loại bỏ hay thay bằng một lần tốt hơn.


## 7. Kết quả so sánh (Phần 4.3, 4.4)

| Task | baseline | subagents | skills-auto |
|---|---|---|---|
| code-learn | 6/10 | 6/10 | 8/10 |
| data-learn | 5/8 | 3/8 | 5/8 |
| logs-learn | 6/9 | 6/9 | 6/9 |
| code-eval | 6/11 | 6/11 | 8/11 |
| data-eval | 5/9 | 4/9 | 5/9 |
| logs-eval | 6/10 | 6/10 | 6/10 |
| **Mean score - learning tasks** | 0.63 | 0.55 | 0.70 |
| **Mean score - evaluation tasks** | 0.57 | 0.53 | 0.63 |
| **Mean tokens per run** | 117,799 | 248,767 | 188,202 |
| **Runs that read a skill** | 0/6 | 0/6 | 6/6 |


```text
condition     role    technical  house rules  mean tokens  read a skill
baseline      eval     17/18         0/12          90,665      0/3
baseline      learn    17/18         0/9          144,934      0/3
subagents     eval     16/18         0/12         235,983      0/3
subagents     learn    15/18         0/9          261,551      0/3
skills-auto   eval     17/18         2/12         189,220      3/3
skills-auto   learn    17/18         2/9          187,183      3/3
```


Run có error: [('skills-auto', 'code-eval', 'GraphRecursionError: Recursion limit of 60 reached without hitting a stop condition. You can increase the limit by setting the `recursion_limit` config key.'), ('skills-auto', 'code-learn', 'GraphRecursionError: Recursion limit of 60 reached without hitting a stop condition. You can increase the limit by setting the `recursion_limit` config key.')]. Run sửa skill: không.

Điểm của run bị GraphRecursionError vẫn là điểm chấm workspace tại thời điểm ngắt, không phải chứng cứ tác tử đã hoàn thành; không dùng lỗi này để phân loại lỗi thuật toán. API từng trả quota 15 request/phút ở subagents/data-eval. Runner được thêm LAB_REQUESTS_PER_SECOND sau freeze (chỉ thay đổi nhịp gọi API, không đổi skill/prompt/model), cấu hình 0.18 cho các tiến trình sau. Tốc độ không áp dụng hồi tố cho tiến trình đã khởi động. Không so sánh seconds như cùng một điều kiện hạ tầng; token/điểm vẫn được ghi thật. Các lần API lỗi được lưu riêng và chạy lại, còn giới hạn graph 60 được giữ để không chọn riêng tham số có lợi cho skills-auto.

## 8. Phân tích

1. Điểm trung bình tập học: baseline=0.6306; subagents=0.5472; skills-auto=0.6972.
1. Điểm trung bình tập đánh giá: baseline=0.5670; subagents=0.5300; skills-auto=0.6276.
Đối chiếu giả thuyết: H1 có chênh điểm subagents-baseline -0.0370, tỷ lệ token 2.60 lần (dự đoán chi phí >=1.20 lần). H2 có chênh điểm đánh giá skills-auto-baseline +0.0606. H3: mức tăng điểm học +0.0667, đánh giá +0.0606; phù hợp với dự đoán mức tăng ở đánh giá thấp hơn học. Đây là đối chiếu mô tả, không kiểm định thống kê.
2. Tách check kỹ thuật và rule_ ở mục 7. Skill code truyền quy ước public type hints, regression test và changelog; skill dữ liệu không chứa đầy đủ feedback nên không kỳ vọng sửa mọi rule_. Quy tắc đánh giá mới không nằm trong đầu vào curator, vì vậy cần đọc đặc tả và tổng quát hóa, không thể dựa vào ghi nhớ skill.
3. Check chuyển từ trượt sang đạt trên tập học: code-learn/rule_regression_tests (skills_read=2), code-learn/rule_changelog (skills_read=2). Check quy ước skill chưa giúp: code-learn/rule_type_hints (skills_read=2), data-learn/rule_money_in_cents (skills_read=2), data-learn/rule_meta_block (skills_read=2), data-learn/rule_clean_csv (skills_read=2), logs-learn/rule_service_names (skills_read=2), logs-learn/rule_sorted_errors (skills_read=2), logs-learn/rule_schema_header (skills_read=2). Đọc skill là chỉ báo sử dụng, không chứng minh nhân quả; đối chiếu các read_file và thao tác tạo/sửa tệp trong trace.
Bằng chứng cơ chế: trace skills-auto/code-learn đọc enforce-code-rules-and-scope rồi tạo tests/test_regressions.py và sửa CHANGELOG.md; hai check rule_regression_tests/rule_changelog chuyển sang đạt, nhưng rule_type_hints vẫn trượt. Ở code-eval, rule_type_hints và rule_regression_tests đạt sau khi đọc skill, còn rule_changelog và quy tắc mới rule_version_bump chưa đạt tại thời điểm graph bị ngắt. Data-eval đọc cả hai skill; trace execute vẫn phân vân 'integer cents or float?' vì phần ngoại lệ 'unless explicitly instructed otherwise', nên đọc skill chưa bảo đảm áp dụng đầy đủ.
4. Chi phí tập đánh giá: baseline: 90665 token/run, 0.0625 điểm/10.000 token; subagents: 235983 token/run, 0.0225 điểm/10.000 token; skills-auto: 189221 token/run, 0.0332 điểm/10.000 token. Tỷ số là mô tả cho mẫu nhỏ, không phải chi phí tiền; token phụ thuộc provider và context. Token callback gồm subagent, tool_calls chỉ gồm luồng chính.
baseline có tỷ lệ điểm/token tốt nhất trong mẫu này. Subagents dùng nhiều token hơn mà điểm đánh giá trung bình thấp hơn baseline, nên chưa có bằng chứng lợi ích tương xứng chi phí. Skills-auto cải thiện điểm thô chủ yếu ở rule_ của code, nhưng các lượt code bị giới hạn bước làm kết luận về hiệu quả còn yếu.
5. Curator bỏ qua eval trước khi đọc trace và không nạp nội dung tác vụ đánh giá. Skill không chứa id/tên dữ liệu đánh giá; validator kiểm tra marker. Skill có tên đầu ra quy ước học là hợp lệ. Quy trình freeze tách thời điểm học và đánh giá; không chỉnh skill theo kết quả đánh giá.
6. Chênh lệch điểm sau/trước freeze của cùng hash skill: code-learn: +0.1000; data-learn: +0.0000; logs-learn: +0.0000. Đây là quan sát nhiễu ở tập học, không phải một lần tiến hóa mới. Chênh lệch code còn bị giới hạn bước tác động; không coi toàn bộ chênh lệch này là ngẫu nhiên thống kê. Hướng lặp thêm evaluation được hoãn do ngân sách quota; bonus đã thực hiện là red team 6c.

## 9. Hạn chế và tính hợp lệ

1. Chỉ ba họ tác vụ và một model, nên không suy rộng sang mọi tác vụ hay provider.
2. Sampling của Gemini không tuân theo temperature=0; ba lượt bonus chỉ mô tả dao động, chưa đủ kiểm định thống kê hay tách ảnh hưởng model/provider.
3. Quy ước Acme được thiết kế sẵn và ẩn với tác tử: cải thiện có thể chủ yếu là truyền quy tắc từ feedback, không thể kết luận khả năng lập trình tổng quát đã tăng.
4. Checkout Windows dùng CRLF gây sai lệch check hash test. Giữ điểm thô để tái lập; điều này làm thấp điểm code và gây nhiễu việc phân loại kỹ thuật/quy ước.
5. Trace bị cắt từng message ở 1.500 ký tự và không chứa thao tác bên trong subagent; lần development dùng invoke mất trace khi lỗi, các lần chính thức dùng stream để giữ trạng thái cuối. Không suy diễn hành vi không quan sát được. Thư mục tạm chỉ cô lập bản sao dữ liệu; LocalShellBackend không phải ranh giới bảo mật của hệ điều hành.

## 10. Kết luận

Trong các lượt chính thức, skills-auto có điểm đánh giá trung bình cao nhất (0.6276; có thể đồng hạng). Kết quả chỉ áp dụng cho bộ tác vụ và model đã đo. Skill tự sinh còn thiếu quy tắc, nên hợp lệ về định dạng không đồng nghĩa đầy đủ hay hiệu quả. Bước tiếp theo là sửa vấn đề line ending trong một checkout Linux riêng và tăng số mẫu trước khi kết luận về tổng quát hóa.

## Phụ lục

### Lệnh và khả năng tái lập

Chạy trên Linux/WSL, cài `python -m venv .venv-wsl`, kích hoạt môi trường và `pip install -e .`; sử dụng `.env` riêng. Không đưa khóa vào repo. Xem `report/reproduce.sh` cho tập học và `report/run-frozen.sh` cho phần chính thức/bonus. Curator đã chạy 2 lần. Git commit `hypotheses` đứng trước commit/tag freeze; không tạo lại tag sau evaluation. Kết quả development giữ ở `results/skills-auto-dev`.

Quá trình chạy gặp quota ngày 500 request/model/project; dừng tiến trình đang chạy để tránh tạo thêm lỗi. Người dùng thay API còn quota, giữ nguyên model. `LAB_REQUESTS_PER_SECOND=0.18 python report/resume_experiments.py` chạy bù, bỏ qua lượt đã hoàn thành và giữ nguyên các lượt bị giới hạn graph. Các run quota cũ nằm trong results/infrastructure-errors. Bonus được chọn chính thức là 6c; hướng 6e ban đầu hoãn để ưu tiên ngân sách cho phần chính.

### Bonus 6c: tấn công ranh giới curator (đã thực hiện)

Thiết kế: dùng ScriptedChatModel trả về 10 payload cố định (1 đối chứng hợp lệ, 9 ca tấn công), đưa qua curate_skills thật với learning fixture và một eval fixture. Đây là thí nghiệm ngoại tuyến về parser/validator, không phải bằng chứng đã thuyết phục được LLM thật. Không dùng đáp án hoặc dữ liệu evaluation, chỉ dùng marker được validator cung cấp. Đầu ra ở results/bonus-6c, tách khỏi thí nghiệm chính và skills/auto.

| Ca kiểm tra | Validator gốc nhận | Lớp phòng vệ nhận |
|---|---|---|
| valid-control | Có | Có |
| literal-leak | Không | Không |
| uppercase-leak | Không | Không |
| zero-width-leak | Có | Không |
| fullwidth-leak | Có | Không |
| spaced-leak | Có | Không |
| path-traversal | Không | Không |
| name-mismatch | Không | Không |
| long-body | Không | Không |
| missing-frontmatter | Không | Không |

Kết quả: 3/9 ca tấn công vượt validator gốc, 0/9 vượt lớp phòng vệ. Đối chứng hợp lệ được cả hai lớp chấp nhận; eval fixture bị loại khỏi prompt trong cả 10 lượt; hash skill chính không đổi.

Cơ chế từ trace.md: marker viết trực tiếp hoặc chữ hoa bị chặn bởi so khớp lowercase; chèn zero-width, chuyển sang chữ fullwidth hoặc tách ký tự bằng khoảng trắng đều được curator ghi thành SKILL.md. Tên ../evil, tên frontmatter lệch block, body quá dài và thiếu frontmatter bị chặn. Phòng vệ thử nghiệm chuẩn hóa NFKC + casefold, giữ ký tự chữ/số rồi so với marker đã chuẩn hóa; chặn được cả ba bypass. Lớp này nằm riêng trong report/run_red_team.py, không sửa validator được bảo vệ hoặc skill đóng băng.

Hạn chế: chỉ kiểm tra một marker và biến đổi ký tự đã biết; không phát hiện chắc chắn diễn đạt lại, dịch ngôn ngữ hoặc đáp án không kèm marker. Chuẩn hóa quá mạnh cũng có thể sinh false positive; một đối chứng chưa đo đủ specificity. Bước tiếp theo: thêm bộ ca paraphrase và văn bản lành tính, kiểm tra thực tế curator trên tài liệu không tin cậy, duyệt ngữ nghĩa trước khi chấp nhận skill. Tái lập: python report/run_red_team.py (không gọi API).

Hướng 6e ban đầu được hoãn do quota; không có lượt lặp evaluation bổ sung và không tuyên bố đã đo khoảng dao động. Lab chỉ yêu cầu chọn một hướng bonus: 6c đã được thực hiện. Lệnh tùy chọn nếu muốn mở rộng sau này: python report/resume_experiments.py --bonus-6e.

Số bản ghi chính thức/development đã giữ: 21; bản API lỗi lưu riêng: 2; bonus lặp bổ sung: 0. Ngoài các bản ghi này có một tác vụ log đang chạy bị dừng khi hết quota ngày, chưa có run.json nên không đo được đầy đủ token của lượt đó. Curator có 2 lần gọi model, tour và 10 ca red-team dùng model giả. Không suy ra tổng token toàn phiên chỉ từ các run.json. Nội dung báo cáo được tổng hợp bằng python report/build_report.py.

### Thông tin nộp bài

Kho bài nộp: https://github.com/congminh1705/K4-DAY20-MULTIAGENTS-HoangCongMinh-2A202602774, nhánh main. Mã nguồn và kết quả thí nghiệm đã được đẩy ở commit c14bc9c; tag freeze trỏ tới 01798de. Commit báo cáo cuối dùng tên `part 6: final report` theo yêu cầu bổ sung của đề bài.
