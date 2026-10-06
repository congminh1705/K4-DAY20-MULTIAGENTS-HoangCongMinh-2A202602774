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
    errors = [(c, r["task"], r["error"]) for c in CONDITIONS for r in runs[c] if r["error"]]
    modified = [(c, r["task"]) for c in CONDITIONS for r in runs[c] if r["skills_modified"]]
    text.append(f"\nRun có error: {errors or 'không'}. Run sửa skill: {modified or 'không'}.\n")
    text += ["## 8. Phân tích\n"]
    if complete:
        for role, data in (("học", learning), ("đánh giá", evaluation)):
            text.append(f"1. Điểm trung bình tập {role}: " + "; ".join(f"{c}={mean(data[c], 'score'):.4f}" for c in CONDITIONS) + ".")
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
        text.append("4. Chi phí tập đánh giá: " + "; ".join(f"{c}: {mean(evaluation[c], 'tokens'):.0f} token/run, {mean(evaluation[c], 'score') / max(mean(evaluation[c], 'tokens'), 1) * 10000:.4f} điểm/10.000 token" for c in CONDITIONS) + ". Tỷ số là mô tả cho mẫu nhỏ, không phải chi phí tiền; token phụ thuộc provider và context. Token callback gồm subagent, tool_calls chỉ gồm luồng chính.")
        text.append("5. Curator bỏ qua eval trước khi đọc trace và không nạp nội dung tác vụ đánh giá. Skill không chứa id/tên dữ liệu đánh giá; validator kiểm tra marker. Skill có tên đầu ra quy ước học là hợp lệ. Quy trình freeze tách thời điểm học và đánh giá; không chỉnh skill theo kết quả đánh giá.")
        differences = []
        for r in dev:
            official = next(x for x in learning["skills-auto"] if x["task"] == r["task"])
            differences.append(f"{r['task']}: {official['score'] - r['score']:+.4f}")
        text.append("6. Chênh lệch điểm sau/trước freeze của cùng hash skill: " + "; ".join(differences) + ". Đây là quan sát nhiễu ở tập học, không phải một lần tiến hóa mới. Bonus đo thêm nhiễu đánh giá với ba lượt mỗi điều kiện.")
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
             "### Bonus 6e: lặp để đo nhiễu\n",
             "Thiết kế: lượt chính thức và hai lượt bổ sung, cùng model, recursion_limit, tập tác vụ và hash skill. Không sinh lại hoặc chỉnh skill. Hai lượt thêm nằm riêng trong `results/bonus-6e/repeat-2` và `repeat-3`, không tham gia bảng kết quả chính. Chạy tuần tự từng điều kiện.\n",
             "| Điều kiện | Tác vụ đánh giá | Điểm ba lượt | Trung bình | Min–max | Token trung bình |\n|---|---|---|---:|---|---:|"]
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
    text.append(f"\nSố lượt bổ sung đã lưu: {bonus_count}/18. Phân tích cơ chế dựa vào trace của từng lượt, gồm lời gọi task, read_file skills và nội dung trả về; không gán mọi thay đổi điểm cho skill. Hạn chế: ba lượt mỗi tác vụ vẫn ít, thứ tự chạy cố định và điều kiện hạ tầng có thể thay đổi. Bước tiếp theo: đảo thứ tự điều kiện và tăng lượt chạy.\n")
    all_runs = [r for rows in runs.values() for r in rows] + dev
    text.append(f"Số lần chạy chính thức/development đã giữ: {len(all_runs)}; bonus bổ sung: {bonus_count}; không tính lần gọi curator và tour vào số tác vụ. Nội dung báo cáo này được tổng hợp từ run.json bằng `python report/build_report.py`.\n")
    (ROOT / "report/REPORT.md").write_text("\n".join(text) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
