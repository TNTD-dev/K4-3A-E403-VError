# Handoff — VLearn VError (Track D2)

## 1. Mục đích của tài liệu này

Tài liệu này cung cấp toàn bộ ngữ cảnh cần thiết để một Agent khác tiếp quản prototype MiniHackathon. Hãy ưu tiên đọc phần **Trạng thái đã xác minh** và **Việc cần làm tiếp theo** trước khi chỉnh sửa mã nguồn.

## 2. Đề tài và vấn đề cần giải quyết

**Track D2 — VLearn: học chủ động trước khi xem nội dung.**

Một học viên có thể xem hết slide/video nhưng không biết mình chưa hiểu phần nào. VLearn có tính năng luyện tập, nhưng người học thường chỉ làm quiz *sau* bài học; điều này chưa tạo được sự tò mò hay một mục tiêu chú ý khi đọc slide.

Giải pháp là **VError**: khi người học mở một phần kiến thức, hệ thống đưa ra một **pre-quiz / productive-failure checkpoint** trước. Người học phải nêu dự đoán và cơ sở của mình. Sau câu trả lời đầu tiên:

1. Hệ thống chẩn đoán giả định chưa đúng hoặc chưa đủ căn cứ.
2. Slide PDF được mở ở đúng trang/bằng chứng liên quan; vùng kiến thức trọng tâm ban đầu được che để tránh “đọc đáp án trước”.
3. Coach/Agent giải thích, đưa hint, yêu cầu học viên giải thích lại và làm case chuyển giao.
4. Hoàn thành phần hiện tại thì mới mở phần tiếp theo.

Mục tiêu không phải “học từ lỗi sai” theo kiểu thông báo đúng/sai chung chung. Mục tiêu là tạo một **cược nhận thức nhỏ trước bài học**, khiến học viên biết điều gì cần tìm và chú ý theo trình tự slide.

## 3. Trải nghiệm người dùng hiện tại

```text
Trang chủ VLearn (?)
  └─ Bấm một Buổi (?day=D04) → Reader slide giống VLearn
      ├─ Slide tiêu đề mỗi phần (Agent nhận diện) hiển thị bình thường
      ├─ Slide kế tiếp: nền slide mờ + pre-quiz nổi ngay trên slide
      ├─ Gửi câu trả lời → bỏ mờ, đọc tiếp + nút "Đi đến kiến thức trọng tâm"
      └─ "Ghi chú của giảng viên" được thay bằng slide trọng tâm + giải thích do Agent sinh
          └─ Củng cố: chẩn đoán → gợi ý → sửa câu trả lời → giảng lại → case chuyển giao
```

### UI/UX

- Trang chủ bám theo ảnh VLearn: nav, lời chào theo giờ, danh sách Buổi (link `?day=Dxx`), chuỗi ngày học, chỗ yếu.
- Chỉ **Buổi 4: DAY04** có deck + pre-quiz thật và được đánh dấu "Đang học". Các Buổi khác mở reader với trạng thái rỗng, không giả nội dung.
- Reader bám theo ảnh VLearn: header `← Bài 4 · Day04`, tiến độ, "Đặt câu hỏi với AI", "Gửi yêu cầu"; sidebar "Nội dung bài học" (Slides / Lab / Videos / KC & Luyện tập); slide render bằng pdf.js; toolbar (bút, tô sáng, khoanh, tẩy, hoàn tác, xóa, toàn màn hình), Từng trang / Cuộn dọc, zoom, pager, dải thumbnail, Sổ ghi chú.
- Khi trang bị khóa, slide độ phân giải cao **không được render**; chỉ hiện ảnh xem trước 48px phóng to (mờ tự nhiên, nhẹ máy).

## 4. Data và phạm vi prototype

- Deck nguồn: `codebase/frontend/public/prompt-engineering-tool-calling.pdf` (43 trang).
- Slide tiêu đề thật: trang 6, 11, 16, 20, 24, 28, 31, 35. `sections.py` còn giữ khoảng trang cũ (lệch từ phần 3) nhưng reader dùng outline của Slide Agent.
- `sources.v1.json` ghi số trang lệch 1–3 trang ở phần 2–6 (ví dụ `D04-P15` thực tế ở trang 17). Slide Agent khớp excerpt với chữ trên PDF để ra trang đúng (`page`, giữ `declaredPages` để đối chiếu). Chưa sửa file nguồn đã duyệt.
- Model chỉ được viết lại câu hỏi, định vị slide tiêu đề và viết lời giải thích. Slide trọng tâm luôn lấy từ nguồn đã duyệt của item; model chỉ chọn `focusPage` trong danh sách đó.

## 5. Kiến trúc hiện có

| Thành phần | Vai trò | File chính |
|---|---|---|
| Router | `?` = trang chủ, `?day=D04&page=N` = reader | `codebase/frontend/src/main.jsx` |
| Trang chủ | UI VLearn home | `codebase/frontend/src/home.jsx` |
| Reader | Layout, điều hướng trang, gating, luồng học, annotation | `codebase/frontend/src/reader.jsx` |
| Pre-quiz trên slide | Overlay loading/khóa/form/lỗi + toast sau khi gửi | `codebase/frontend/src/prequiz.jsx` |
| Kiến thức trọng tâm | Thay "Ghi chú của giảng viên": slide trọng tâm, giải thích, củng cố | `codebase/frontend/src/insight.jsx` |
| PDF | pdf.js, canvas không nhấp nháy, thumbnail, veil mờ | `codebase/frontend/src/pdf.jsx` |
| FastAPI | API sections, session, attempt, hint, generator, outline, key-insight, reset | `codebase/backend/app/main.py` |
| Question Agent | Chỉ rephrase câu hỏi từ dữ liệu đã duyệt | `codebase/backend/app/question_generator.py` |
| Slide Agent | Đọc PDF (pypdf), nhận diện slide tiêu đề (OpenAI + kiểm tra), khớp slide trọng tâm, sinh giải thích | `codebase/backend/app/slide_agent.py` |
| Learning flow | State machine: attempt → diagnosis → explain → transfer | `codebase/backend/app/orchestrator.py` |

API mới:
- `GET /api/v1/deck/outline` — slide tiêu đề, khoảng trang, `quizPage`, `keySlides`, `agent.provider/model/fallbackReason`. Cache trong process; `?refresh=true` để chạy lại.
- `POST /api/v1/sections/{id}/key-insight` body `{sessionId?}` — 403 `SLIDES_LOCKED` nếu chưa làm pre-quiz; trả `keySlides`, `insight`, `generation`.
- `POST /api/v1/progress/reset` — đặt lại tiến độ demo (nút trong sidebar "KC & Luyện tập").

## 6. Trạng thái đã hoàn thành và đã xác minh

- [x] UI trang chủ + reader theo ảnh VLearn, desktop và mobile.
- [x] Slide Agent live (`gpt-5.6-luna`) nhận diện đủ 8 slide tiêu đề, trùng với bộ đọc tất định.
- [x] Pre-quiz tự bật ở slide ngay sau slide tiêu đề, nền mờ; gửi xong bỏ mờ và hiện nút tới kiến thức trọng tâm.
- [x] Explanation Agent live sinh giải thích cá nhân hóa theo câu trả lời, bám slide trọng tâm.
- [x] Phần chưa mở hiện thẻ khóa + nút tới pre-quiz đang chờ.
- [x] `npm run build` thành công.
- [x] `python -m pytest -q`: **18 passed** (thêm test outline, key-insight gating, reset).
- [x] E2E headless (Chrome + puppeteer-core, chạy ngoài repo): home → Buổi 4 → trang 6 → trang 7 → pre-quiz AI → gửi → toast → kiến thức trọng tâm → gợi ý 1 → phần khóa → cuộn dọc → mobile; không lỗi console.

## 7. Cấu hình chạy local

Tạo/cập nhật `codebase/backend/.env` theo mẫu `codebase/backend/.env.example`:

```dotenv
MODEL_MODE=live
OPENAI_API_KEY=<khóa-của-người-dùng>
OPENAI_MODEL=gpt-5.6-luna
SQLITE_PATH=../verror.sqlite
```

Chạy bằng một lệnh duy nhất từ thư mục `codebase`:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-live.ps1
```

Không chạy frontend tách riêng bằng `npm run dev`: script đặt `VITE_API_BASE` trỏ đến backend đã chọn cổng trống. URL frontend thường là `http://127.0.0.1:5173`.

## 8. Việc cần làm tiếp theo

1. Sửa số trang trong `content/sources.v1.json` và khoảng trang trong `sections.py` theo outline thật (cần người duyệt nội dung đồng ý; test `test_tool_loop_section...` đang kiểm tra trang 22 cũ).
2. `coach.py` vẫn gọi `chat.completions` với `temperature`, có thể lỗi với `gpt-5.6-luna` và rơi về câu chẩn đoán tĩnh; nên chuyển sang Responses API như Question/Slide Agent.
3. Map lỗi live API (quota, network, BadRequest) sang thông báo tiếng Việt thân thiện.
4. Thêm nội dung thật cho các Buổi khác (hiện chỉ DAY04).
5. Đưa script E2E vào repo nếu muốn chạy trong CI.

## 9. Quy tắc an toàn khi tiếp tục

- Không commit hoặc in ra `backend/.env` hay API key.
- Không để model tự đổi answer key, citations, phần kiến thức hoặc mục tiêu câu hỏi.
- Nếu API thật lỗi, phải hiển thị fallback rõ ràng; không được nói “AI đã tạo” khi đang dùng câu hỏi tĩnh.
- Không sửa/xóa các thay đổi không liên quan trong worktree.

## 10. Câu lệnh kiểm tra nhanh cho Agent tiếp quản

```powershell
cd C:\VIN-LAB\LD5\MiniHackathon\K4-3A-E403-VError\codebase\backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run build
```

