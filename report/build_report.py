"""Rebuild the submission report from preserved experimental records, without API calls."""
import json
import re
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("baseline", "subagents", "skills-auto")
HYPOTHESES = """- H1 (subagents so với baseline): Điểm đánh giá có thể tương đương baseline, nhưng token trung bình cao hơn ít nhất 20%. Tập học cho thấy việc giao nhiệm vụ lệch vai trò và truyền thiếu quy ước có thể làm mất lợi ích kiểm tra độc lập; guides/pseudocode/02_subagents.md giải thích chi phí và ngữ cảnh cô lập.
- H2 (skills-auto so với baseline): Skill cải thiện check quy ước về code, nhưng không bảo đảm cải thiện toàn bộ tác vụ đánh giá. Skill dữ liệu còn thiếu thứ tự log, phần đầu schema và quy tắc clean.csv; description rộng có thể khiến tác tử đọc nhưng chỉ làm một phần (guides/pseudocode/05_skill_quality.md).
- H3 (tác vụ học so với tác vụ đánh giá): Mức tăng điểm trên tập đánh giá thấp hơn tập học, vì quy ước mới chưa có trong phản hồi học. Cùng một bộ skill có thể cho điểm học khác nhau giữa hai lần chạy; GUIDE Phần 4.2 yêu cầu giữ kết quả trước đóng băng để nhận diện nhiễu."""


def records(folder):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*/run.json"))]


def mean(rows, key):
    return statistics.mean(r[key] if key != "tokens" else r["tokens"]["total"] for r in rows) if rows else 0


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "Chưa đóng băng"


def build():
    runs = {c: records(ROOT / "results" / c) for c in CONDITIONS}
    learning = {c: [r for r in runs[c] if r["role"] == "learn"] for c in CONDITIONS}
    evaluation = {c: [r for r in runs[c] if r["role"] == "eval"] for c in CONDITIONS}
    complete = all(len(runs[c]) == 6 for c in CONDITIONS)
    text = ["# Báo cáo Lab: Self evolving Agentic\n",
            "## 1. Thông tin nhóm và cấu hình\n",
            "| Họ tên | Mã sinh viên | Phần đóng góp |\n|---|---|---|\n| Hoàng Công Minh | 2A202602774 | Cài đặt harness, thí nghiệm, skill và báo cáo |\n",
            "Tên và mã sinh viên lấy từ tên thư mục bài nộp. Model: `google_genai:gemini-3.5-flash-lite`; `LAB_TEMPERATURE=0` theo mặc định của harness. Provider cảnh báo model dùng sampling cố định nên bỏ qua temperature; không coi đây là thí nghiệm hoàn toàn xác định. `recursion_limit=60`. Deep Agents 0.7.21, Python 3.14.4, Ubuntu WSL trên Windows. Shell không kế thừa môi trường chứa khóa API.\n",
            f"Tag `freeze`: `{git('rev-parse', 'freeze')}`. Kiểm thử gốc: **32 passed** (report/tests.txt).\n",
            "## 2. Giả thuyết (commit TRƯỚC tag `freeze`, Phần 4.0)\n", HYPOTHESES + "\n",
            "## 3. Làm quen Deep Agents (Phần 0.3)\n",
            "1. Công cụ quan sát được trong `report/tour.txt`: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`, `execute`, `task`. `execute` chạy shell.\n"
            "2. `general-purpose` có cùng khả năng công cụ với tác tử chính. Mỗi lần gọi mặc định không có trạng thái; nó chỉ nhận prompt giao việc và trả về một báo cáo cuối, không tự thấy toàn bộ hội thoại chính.\n"
            "3. Trích `task`: “Put full detail in the prompt and state exactly what it should return”. Trích `execute`: “Use read_file rather than cat/head/tail.” Prompt mặc định rỗng; harness thêm BASE_PROMPT và PATHS_NOTE để thống nhất đường dẫn tương đối giữa công cụ tệp và shell.\n",
            "## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)\n",
            "| Tác vụ | Check thất bại | Nhóm lỗi (A-G) | Bằng chứng từ detail |\n|---|---|---|---|"]
    rule_fails = 0
    for r in learning["baseline"]:
        for check in r["checks"]:
            if check["passed"]:
                continue
            group = "E" if check["name"].startswith("rule_") else "G (môi trường CRLF)" if check["name"] == "tests_not_modified" else "G"
            rule_fails += group == "E"
            text.append(f"| {r['task']} | `{check['name']}` | {group} | {check['detail'].replace('|', '/').replace(chr(10), ' ')} |")
    text.append(f"\nCó {rule_fails} check quy ước thất bại. Đây là nhóm chiếm đa số; skill có thể truyền các quy ước từ feedback, nhưng thiếu quy tắc hoặc mâu thuẫn đề bài vẫn làm thất bại. Các check thuật toán của baseline đều đạt; không có bằng chứng phổ biến cho nhóm A-D.\n")
    text.append("Check `tests_not_modified` của code-learn thất bại dù trace không sửa test gốc: SHA-256 bản CRLF là `efb5e7650d4f03356e8353d209fbcfe81505ce2fd648bd558d5ada6e8b92ff19`, còn bản LF là `79e05f4cc2e62a4f606d210b0b08a2cc21777245bc2f6ad244a126e9a2aee00d`, đúng hash check gốc. Giữ nguyên tệp được bảo vệ và điểm thô; loại sai lệch môi trường này khỏi diễn giải lỗi tác tử. Không coi việc test visible đạt là bằng chứng mọi quy ước đã đạt.\n")
    text += ["## 5. Điều kiện `subagents` (Phần 2.3)\n",
             "Ba vai trò: explorer chỉ đọc đặc tả/dữ liệu và tìm nguyên nhân; implementer sửa và kiểm tra; reviewer kiểm tra độc lập, không sửa. Description chỉ rõ khi nào giao việc. Mỗi subagent nhận PATHS_NOTE; custom subagent không được nạp skill trong điều kiện chính.\n",
             "| Tác vụ | Điểm | Token | Tool calls chính | Subagent calls |\n|---|---:|---:|---:|---:|"]
    for r in runs["subagents"]:
        text.append(f"| {r['task']} | {r['passed']}/{r['total']} | {r['tokens']['total']} | {r['tool_calls']} | {r['subagent_calls']} |")
    text.append("\nBằng chứng code-learn: lời gọi `task` giao cả việc sửa code cho `explorer`, dù system prompt của explorer cấm sửa; tác tử chính tiếp tục sửa và chạy pytest. Lời giao nêu đầy đủ đường dẫn và cấm sửa test, nhưng chỉ nhắc chung Acme, không có quy tắc cụ thể. Tác tử con cũng không thể tự suy ra quy ước ẩn từ chỉ dẫn chung này. Trace chỉ ghi luồng chính, không đủ để kiểm chứng mọi thao tác nội bộ của subagent.\n")
    text.append("Bằng chứng data-learn: explorer nhận yêu cầu viết script; reviewer nhận lời giao ngắn không nhắc lại ranh giới Q1 UTC và đường dẫn workspace đầy đủ. Hai check north_q1_revenue/north_q1_orders thất bại (giá trị đã xuất 3189.59 và 13), dù báo cáo cuối nói đã kiểm tra thành công. Điều này chứng minh kiểm tra độc lập chưa bảo đảm đúng. Logs-learn giao implementer có liệt kê các quy tắc kỹ thuật đầy đủ, nhưng thiếu các quy ước Acme ẩn; kết quả kỹ thuật đạt, rule_ vẫn trượt.\n")
    for r in learning["subagents"]:
        trace = (ROOT / "results/subagents" / r["task"] / "trace.md").read_text(encoding="utf-8")
        names = re.findall(r'"subagent_type": "([^"]+)"', trace)
        text.append(f"- `{r['task']}` giao cho: {', '.join(names) if names else 'không quan sát được lời gọi'}; token so baseline: {r['tokens']['total']} / {next((x['tokens']['total'] for x in learning['baseline'] if x['task'] == r['task']), 0)}.")
    text += ["\n## 6. Self-evolving: skill do curator sinh (Phần 3)\n",
             "Curator chạy hai lần: lần đầu Gemini trả content dạng list nên parser chưa tách được khối; đã sửa hàm curate_skills để ghép text block rồi chạy lại. Lần hai sinh 2 skill, không sửa tay hoặc xóa skill. Đầu vào chỉ là baseline learning; record có error bị bỏ qua.\n",
             "| Skill | Tổng quát và đúng/sai | Độ dài và description |\n|---|---|---|"]
    for path in sorted((ROOT / "skills/auto").glob("*/SKILL.md")):
        skill = path.read_text(encoding="utf-8")
        description = next(line.split(":", 1)[1].strip() for line in skill.splitlines() if line.startswith("description:"))
        comment = ("Quy trình dùng lại cho sửa code; phù hợp feedback về type hints, regression và changelog. Tên test/changelog là quy ước chung, không phải dữ liệu đánh giá. Không xử lý được sai lệch CRLF." if path.parent.name.startswith("enforce") else "Áp dụng cho JSON/CSV; hữu ích cho cents và chuẩn hóa chuỗi. Thiếu quy tắc clean.csv, sort log, schema_version/generated_by. Cụm 'unless explicitly instructed otherwise' và 'when required' có thể khiến tác tử ưu tiên đề bài hơn quy ước ẩn; canonical spelling chưa phân biệt rõ region với service.")
        text.append(f"| `{path.parent.name}` | {comment} | {len(skill.splitlines())} dòng toàn tệp; {description} |")
    dev = records(ROOT / "results/skills-auto-dev")
    text.append("\n| Tác vụ | Trước freeze | Sau freeze | Skill đọc trước/sau |\n|---|---:|---:|---:|")
    for r in dev:
        official = next((x for x in learning["skills-auto"] if x["task"] == r["task"]), None)
        text.append(f"| {r['task']} | {r['passed']}/{r['total']} | {str(official['passed']) + '/' + str(official['total']) if official else 'Chưa chạy'} | {r['skills_read']}/{official['skills_read'] if official else '-'} |")
    text.append("\nDevelopment code-learn chạm GraphRecursionError ở giới hạn 60, đạt 7/10 nhưng trace rỗng và skills_read=0 do phiên bản invoke tối thiểu chưa giữ trạng thái khi lỗi. Không diễn giải số 0 này là bằng chứng chưa đọc skill. Trước freeze, runner được đổi sang stream_mode=values (mở rộng trong pseudo-code 03) để lưu trace và số đếm kể cả khi invoke lỗi; toàn bộ test gốc vẫn đạt. Giữ nguyên lần development thất bại, không loại bỏ hay thay bằng một lần tốt hơn.\n")
    text += ["\n## 7. Kết quả so sánh (Phần 4.3, 4.4)\n"]
    table = ROOT / "report/table.md"
    text.append(table.read_text(encoding="utf-8") if table.exists() else "Chưa chạy chính thức; không có số liệu đánh giá.\n")
    breakdown = ROOT / "report/check-breakdown.txt"
    if breakdown.exists():
        text.append("\n```text\n" + breakdown.read_text(encoding="utf-8") + "```\n")
    errors = [(c, r["task"], r["error"].splitlines()[0]) for c in CONDITIONS for r in runs[c] if r["error"]]
    modified = [(c, r["task"]) for c in CONDITIONS for r in runs[c] if r["skills_modified"]]
    text.append(f"\nRun có error: {errors or 'không'}. Run sửa skill: {modified or 'không'}.\n")
    text.append("Điểm của run bị GraphRecursionError vẫn là điểm chấm workspace tại thời điểm ngắt, không phải chứng cứ tác tử đã hoàn thành; không dùng lỗi này để phân loại lỗi thuật toán. API từng trả quota 15 request/phút ở subagents/data-eval. Runner được thêm LAB_REQUESTS_PER_SECOND sau freeze (chỉ thay đổi nhịp gọi API, không đổi skill/prompt/model), cấu hình 0.18 cho các tiến trình sau. Tốc độ không áp dụng hồi tố cho tiến trình đã khởi động. Không so sánh seconds như cùng một điều kiện hạ tầng; token/điểm vẫn được ghi thật. Các lần API lỗi được lưu riêng và chạy lại, còn giới hạn graph 60 được giữ để không chọn riêng tham số có lợi cho skills-auto.\n")
    text += ["## 8. Phân tích\n"]
    if complete:
        for role, data in (("học", learning), ("đánh giá", evaluation)):
            text.append(f"1. Điểm trung bình tập {role}: " + "; ".join(f"{c}={mean(data[c], 'score'):.4f}" for c in CONDITIONS) + ".")
        base_score = mean(evaluation["baseline"], "score")
        multi_score = mean(evaluation["subagents"], "score")
        token_ratio = mean(evaluation["subagents"], "tokens") / max(mean(evaluation["baseline"], "tokens"), 1)
        gain_learn = mean(learning["skills-auto"], "score") - mean(learning["baseline"], "score")
        gain_eval = mean(evaluation["skills-auto"], "score") - base_score
        text.append(f"Đối chiếu giả thuyết: H1 có chênh điểm subagents-baseline {multi_score - base_score:+.4f}, tỷ lệ token {token_ratio:.2f} lần (dự đoán chi phí >=1.20 lần). H2 có chênh điểm đánh giá skills-auto-baseline {gain_eval:+.4f}. H3: mức tăng điểm học {gain_learn:+.4f}, đánh giá {gain_eval:+.4f}; {'phù hợp' if gain_eval < gain_learn else 'không phù hợp'} với dự đoán mức tăng ở đánh giá thấp hơn học. Đây là đối chiếu mô tả, không kiểm định thống kê.")
        text.append("2. Tách check kỹ thuật và rule_ ở mục 7. Skill code truyền quy ước public type hints, regression test và changelog; skill dữ liệu không chứa đầy đủ feedback nên không kỳ vọng sửa mọi rule_. Quy tắc đánh giá mới không nằm trong đầu vào curator, vì vậy cần đọc đặc tả và tổng quát hóa, không thể dựa vào ghi nhớ skill.")
        helped = []
        missed = []
        for r in learning["skills-auto"]:
            base = next(x for x in learning["baseline"] if x["task"] == r["task"])
            basechecks = {c["name"]: c["passed"] for c in base["checks"]}
            for c in r["checks"]:
                if not basechecks.get(c["name"], True) and c["passed"]:
                    helped.append(f"{r['task']}/{c['name']} (skills_read={r['skills_read']})")
                if not c["passed"] and c["name"].startswith("rule_"):
                    missed.append(f"{r['task']}/{c['name']} (skills_read={r['skills_read']})")
        text.append("3. Check chuyển từ trượt sang đạt trên tập học: " + (", ".join(helped) or "không") + ". Check quy ước skill chưa giúp: " + (", ".join(missed) or "không") + ". Đọc skill là chỉ báo sử dụng, không chứng minh nhân quả; đối chiếu các read_file và thao tác tạo/sửa tệp trong trace.")
        text.append("Bằng chứng cơ chế: trace skills-auto/code-learn đọc enforce-code-rules-and-scope rồi tạo tests/test_regressions.py và sửa CHANGELOG.md; hai check rule_regression_tests/rule_changelog chuyển sang đạt, nhưng rule_type_hints vẫn trượt. Ở code-eval, rule_type_hints và rule_regression_tests đạt sau khi đọc skill, còn rule_changelog và quy tắc mới rule_version_bump chưa đạt tại thời điểm graph bị ngắt. Data-eval đọc cả hai skill; trace execute vẫn phân vân 'integer cents or float?' vì phần ngoại lệ 'unless explicitly instructed otherwise', nên đọc skill chưa bảo đảm áp dụng đầy đủ.")
        text.append("4. Chi phí tập đánh giá: " + "; ".join(f"{c}: {mean(evaluation[c], 'tokens'):.0f} token/run, {mean(evaluation[c], 'score') / max(mean(evaluation[c], 'tokens'), 1) * 10000:.4f} điểm/10.000 token" for c in CONDITIONS) + ". Tỷ số là mô tả cho mẫu nhỏ, không phải chi phí tiền; token phụ thuộc provider và context. Token callback gồm subagent, tool_calls chỉ gồm luồng chính.")
        efficient = max(CONDITIONS, key=lambda c: mean(evaluation[c], "score") / max(mean(evaluation[c], "tokens"), 1))
        text.append(f"{efficient} có tỷ lệ điểm/token tốt nhất trong mẫu này. Subagents dùng nhiều token hơn mà điểm đánh giá trung bình thấp hơn baseline, nên chưa có bằng chứng lợi ích tương xứng chi phí. Skills-auto cải thiện điểm thô chủ yếu ở rule_ của code, nhưng các lượt code bị giới hạn bước làm kết luận về hiệu quả còn yếu.")
        text.append("5. Curator bỏ qua eval trước khi đọc trace và không nạp nội dung tác vụ đánh giá. Skill không chứa id/tên dữ liệu đánh giá; validator kiểm tra marker. Skill có tên đầu ra quy ước học là hợp lệ. Quy trình freeze tách thời điểm học và đánh giá; không chỉnh skill theo kết quả đánh giá.")
        differences = []
        for r in dev:
            official = next(x for x in learning["skills-auto"] if x["task"] == r["task"])
            differences.append(f"{r['task']}: {official['score'] - r['score']:+.4f}")
        text.append("6. Chênh lệch điểm sau/trước freeze của cùng hash skill: " + "; ".join(differences) + ". Đây là quan sát nhiễu ở tập học, không phải một lần tiến hóa mới. Chênh lệch code còn bị giới hạn bước tác động; không coi toàn bộ chênh lệch này là ngẫu nhiên thống kê. Hướng lặp thêm evaluation được hoãn do ngân sách quota; bonus đã thực hiện là red team 6c.")
    else:
        text.append("Phân tích số liệu chính thức sẽ được điền sau khi freeze và chạy evaluation; chưa có kết luận về hiệu quả trên tập đánh giá.")
    text += ["\n## 9. Hạn chế và tính hợp lệ\n",
             "1. Chỉ ba họ tác vụ và một model, nên không suy rộng sang mọi tác vụ hay provider.\n"
             "2. Sampling của Gemini không tuân theo temperature=0; ba lượt bonus chỉ mô tả dao động, chưa đủ kiểm định thống kê hay tách ảnh hưởng model/provider.\n"
             "3. Quy ước Acme được thiết kế sẵn và ẩn với tác tử: cải thiện có thể chủ yếu là truyền quy tắc từ feedback, không thể kết luận khả năng lập trình tổng quát đã tăng.\n"
             "4. Checkout Windows dùng CRLF gây sai lệch check hash test. Giữ điểm thô để tái lập; điều này làm thấp điểm code và gây nhiễu việc phân loại kỹ thuật/quy ước.\n"
             "5. Trace bị cắt từng message ở 1.500 ký tự và không chứa thao tác bên trong subagent; lần development dùng invoke mất trace khi lỗi, các lần chính thức dùng stream để giữ trạng thái cuối. Không suy diễn hành vi không quan sát được. Thư mục tạm chỉ cô lập bản sao dữ liệu; LocalShellBackend không phải ranh giới bảo mật của hệ điều hành.\n",
             "## 10. Kết luận\n"]
    if complete:
        best = max(CONDITIONS, key=lambda c: mean(evaluation[c], "score"))
        text.append(f"Trong các lượt chính thức, {best} có điểm đánh giá trung bình cao nhất ({mean(evaluation[best], 'score'):.4f}; có thể đồng hạng). Kết quả chỉ áp dụng cho bộ tác vụ và model đã đo. Skill tự sinh còn thiếu quy tắc, nên hợp lệ về định dạng không đồng nghĩa đầy đủ hay hiệu quả. Bước tiếp theo là sửa vấn đề line ending trong một checkout Linux riêng và tăng số mẫu trước khi kết luận về tổng quát hóa.")
    else:
        text.append("Harness đạt bộ kiểm thử offline; chưa có kết luận về tập đánh giá trước freeze.")
    text += ["\n## Phụ lục\n", "### Lệnh và khả năng tái lập\n",
             "Chạy trên Linux/WSL, cài `python -m venv .venv-wsl`, kích hoạt môi trường và `pip install -e .`; sử dụng `.env` riêng. Không đưa khóa vào repo. Xem `report/reproduce.sh` cho tập học và `report/run-frozen.sh` cho phần chính thức/bonus. Curator đã chạy 2 lần. Git commit `hypotheses` đứng trước commit/tag freeze; không tạo lại tag sau evaluation. Kết quả development giữ ở `results/skills-auto-dev`.\n",
             "Quá trình chạy gặp quota ngày 500 request/model/project; dừng tiến trình đang chạy để tránh tạo thêm lỗi. Người dùng thay API còn quota, giữ nguyên model. `LAB_REQUESTS_PER_SECOND=0.18 python report/resume_experiments.py` chạy bù, bỏ qua lượt đã hoàn thành và giữ nguyên các lượt bị giới hạn graph. Các run quota cũ nằm trong results/infrastructure-errors. Bonus được chọn chính thức là 6c; hướng 6e ban đầu hoãn để ưu tiên ngân sách cho phần chính.\n",
             "### Bonus 6c: tấn công ranh giới curator (đã thực hiện)\n"]
    red_team = ROOT / "results/bonus-6c/summary.json"
    if red_team.exists():
        summary = json.loads(red_team.read_text(encoding="utf-8"))
        text += ["Thiết kế: dùng ScriptedChatModel trả về 10 payload cố định (1 đối chứng hợp lệ, 9 ca tấn công), đưa qua curate_skills thật với learning fixture và một eval fixture. Đây là thí nghiệm ngoại tuyến về parser/validator, không phải bằng chứng đã thuyết phục được LLM thật. Không dùng đáp án hoặc dữ liệu evaluation, chỉ dùng marker được validator cung cấp. Đầu ra ở results/bonus-6c, tách khỏi thí nghiệm chính và skills/auto.\n",
                 "| Ca kiểm tra | Validator gốc nhận | Lớp phòng vệ nhận |\n|---|---|---|"]
        for row in summary["cases"]:
            text.append(f"| {row['case']} | {'Có' if row['original_accepted'] else 'Không'} | {'Có' if row['hardened_accepted'] else 'Không'} |")
        text.append(f"\nKết quả: {summary['original_bypasses']}/{summary['malicious_cases']} ca tấn công vượt validator gốc, {summary['hardened_bypasses']}/{summary['malicious_cases']} vượt lớp phòng vệ. Đối chứng hợp lệ được cả hai lớp chấp nhận; eval fixture bị loại khỏi prompt trong cả 10 lượt; hash skill chính không đổi.\n")
        text.append("Cơ chế từ trace.md: marker viết trực tiếp hoặc chữ hoa bị chặn bởi so khớp lowercase; chèn zero-width, chuyển sang chữ fullwidth hoặc tách ký tự bằng khoảng trắng đều được curator ghi thành SKILL.md. Tên ../evil, tên frontmatter lệch block, body quá dài và thiếu frontmatter bị chặn. Phòng vệ thử nghiệm chuẩn hóa NFKC + casefold, giữ ký tự chữ/số rồi so với marker đã chuẩn hóa; chặn được cả ba bypass. Lớp này nằm riêng trong report/run_red_team.py, không sửa validator được bảo vệ hoặc skill đóng băng.\n")
        text.append("Hạn chế: chỉ kiểm tra một marker và biến đổi ký tự đã biết; không phát hiện chắc chắn diễn đạt lại, dịch ngôn ngữ hoặc đáp án không kèm marker. Chuẩn hóa quá mạnh cũng có thể sinh false positive; một đối chứng chưa đo đủ specificity. Bước tiếp theo: thêm bộ ca paraphrase và văn bản lành tính, kiểm tra thực tế curator trên tài liệu không tin cậy, duyệt ngữ nghĩa trước khi chấp nhận skill. Tái lập: python report/run_red_team.py (không gọi API).\n")
    optional_start = len(text)
    text += ["### Hướng 6e (tùy chọn, chưa dùng để tính bonus)\n",
             "Thiết kế nếu có ngân sách: lượt chính thức và hai lượt bổ sung, cùng model/recursion_limit/hash skill. Hai lượt thêm lưu riêng results/bonus-6e/repeat-2 và repeat-3. Các con số dưới đây chỉ tính các lượt đã thực sự có tệp; không thay dữ liệu thiếu bằng dữ liệu giả.\n",
             "| Điều kiện | Tác vụ đánh giá | Điểm các lượt đã có | Trung bình | Min–max | Token trung bình |\n|---|---|---|---:|---|---:|"]
    bonus_count = 0
    for condition in CONDITIONS:
        for official in evaluation[condition]:
            reps = [official]
            for number in (2, 3):
                path = ROOT / "results/bonus-6e" / f"repeat-{number}" / condition / official["task"] / "run.json"
                if path.exists():
                    reps.append(json.loads(path.read_text(encoding="utf-8")))
                    bonus_count += 1
            scores = [r["score"] for r in reps]
            text.append(f"| {condition} | {official['task']} | {', '.join(f'{s:.4f}' for s in scores)} | {statistics.mean(scores):.4f} | {min(scores):.4f}–{max(scores):.4f} | {mean(reps, 'tokens'):.0f} |")
    text.append(f"\nSố lượt bổ sung đã lưu: {bonus_count}/18. Khi chưa có lượt bổ sung, trung bình/min–max chỉ là điểm một lượt chính thức, không phải ước lượng nhiễu. Muốn thực hiện thêm: python report/resume_experiments.py --bonus-6e. Không tính hướng chưa hoàn tất vào điểm bonus; bonus 6c đã có số liệu riêng.\n")
    if not bonus_count:
        text[optional_start:] = ["Hướng 6e ban đầu được hoãn do quota; không có lượt lặp evaluation bổ sung và không tuyên bố đã đo khoảng dao động. Lab chỉ yêu cầu chọn một hướng bonus: 6c đã được thực hiện. Lệnh tùy chọn nếu muốn mở rộng sau này: python report/resume_experiments.py --bonus-6e.\n"]
    all_runs = [r for rows in runs.values() for r in rows] + dev
    archived_count = len(list((ROOT / "results/infrastructure-errors").rglob("run.json")))
    text.append(f"Số bản ghi chính thức/development đã giữ: {len(all_runs)}; bản API lỗi lưu riêng: {archived_count}; bonus lặp bổ sung: {bonus_count}. Ngoài các bản ghi này có một tác vụ log đang chạy bị dừng khi hết quota ngày, chưa có run.json nên không đo được đầy đủ token của lượt đó. Curator có 2 lần gọi model, tour và 10 ca red-team dùng model giả. Không suy ra tổng token toàn phiên chỉ từ các run.json. Nội dung báo cáo được tổng hợp bằng python report/build_report.py.\n")
    text += ["### Thông tin nộp bài\n",
             "Kho bài nộp: https://github.com/congminh1705/K4-DAY20-MULTIAGENTS-HoangCongMinh-2A202602774, nhánh main. Mã nguồn và kết quả thí nghiệm đã được đẩy ở commit c14bc9c; tag freeze trỏ tới 01798de. Commit báo cáo cuối dùng tên `part 6: final report` theo yêu cầu bổ sung của đề bài.\n"]
    rendered = "\n".join(line.rstrip() for line in "\n".join(text).splitlines()) + "\n"
    (ROOT / "report/REPORT.md").write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    build()
