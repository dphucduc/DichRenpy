# Dịch Ren’Py

Ứng dụng web tiếng Việt để chuẩn bị và soát bản dịch game Ren’Py bằng **Gemini web**, không cần khóa API.

## Chạy ứng dụng

Cần Python 3.10 trở lên và Git. Trong thư mục dự án:

```bash
bash scripts/setup.sh
.venv/bin/python app.py
```

Trên Windows, cài Python (có Python Launcher `py`) và Git, rồi nhấp đúp **start.bat**. Script tạo môi trường và cài công cụ trước khi mở máy chủ; xem địa chỉ trên cửa sổ lệnh và mở bằng trình duyệt. Script Windows chưa được chạy kiểm tra trên Windows trong môi trường Linux này.

Máy chủ phục vụ cổng 5000 trên máy đang chạy app. Đây là ứng dụng cho một người dùng; chưa có đăng nhập hoặc cấu hình triển khai công khai.

## Dùng lần đầu

1. Nhấn **Thử với hội thoại mẫu**, hoặc nhập tên dự án và chọn `.rpy`, `.rpyc`, `.rpa`.
2. Điền bối cảnh, tính cách, quan hệ, cách xưng hô và thuật ngữ. Xác nhận người nghe cho từng câu khi có đủ thông tin. Tên người nói lấy từ mã Ren’Py; sổ tay hiển thị các khai báo `Character` đơn giản.
3. Chọn cảnh. App chia cảnh dài thành các lượt tối đa 60 câu, kèm 8 câu trước đó làm ngữ cảnh.
4. Nhấn **Tạo yêu cầu dịch**, **Sao chép**, mở Gemini web rồi dán nội dung. Dùng cùng một cuộc trò chuyện khi dịch các cảnh liên tiếp.
5. Dán toàn bộ JSON từ Gemini vào ô kết quả rồi nhấn **Nhập & kiểm tra bản dịch**. App yêu cầu đủ ID của lượt hiện tại và giữ nguyên biến, thẻ. Nếu Gemini thiếu câu, yêu cầu Gemini trả lại toàn bộ lượt đó.
6. Soát câu gốc cạnh bản dịch, sửa và lưu. **Xuất bản dịch** tạo ZIP chứa `.rpy` cùng bản ghi dự án. **Tệp đã giải nén** tải toàn bộ tệp được lấy từ kho, gồm tài nguyên.

Mọi dự án lưu ở `data/`, tải lại trang có thể mở tiếp. Chỉnh sửa chưa lưu sẽ có cảnh báo khi rời trang. Không gửi dữ liệu tự động tới Google; Gemini web được thao tác bằng sao chép/dán và vẫn có thể có giới hạn riêng của tài khoản.

## Phạm vi bản đầu

- RPA-2.0, RPA-3.0 tiêu chuẩn; giới hạn tải lên 256 MB mỗi lượt, dữ liệu giải nén 512 MB mỗi kho. Kho bị mã hóa, tùy biến hoặc bảo vệ không được đảm bảo hỗ trợ.
- Giải biên dịch dùng [unrpyc](https://github.com/CensoredUsername/unrpyc), phiên bản cố định `3ae8334ed71a05535927dcc559663d3aca51215b` (MIT). CLI của công cụ hỗ trợ Ren’Py 6.18+ đến 8.x theo tài liệu upstream; đã kiểm tra thực tế với mẫu Ren’Py 8.2. Thất bại được ghi trong cảnh báo dự án.
- Đọc lời thoại chuỗi dấu nháy kép một dòng, lời dẫn, thuộc tính người nói và lựa chọn menu đơn giản. Không tự dịch mã Python, screen, khai báo nhân vật hoặc cặp `old/new` trong tệp dịch sẵn. Chuỗi nhiều dòng, người nói là biểu thức, lựa chọn có điều kiện và cú pháp tùy biến cần xử lý thủ công. Đây là bộ đọc thận trọng, không thay thế trình phân tích đầy đủ của Ren’Py.
- Người nghe do bạn xác nhận; app chưa suy luận tự động quan hệ giữa nhân vật. Hồ sơ và ngữ cảnh hướng dẫn Gemini nhưng chất lượng dịch vẫn cần người dùng soát.
- Xuất `.rpy` thay lời thoại trực tiếp, chưa tạo gói `game/tl/vietnamese` dùng trình sinh bản dịch của Ren’Py. Sao lưu game, thử trên bản sao và kiểm tra bằng Ren’Py. Khi thay script, bỏ `.rpyc` tương ứng cũ để game biên dịch lại; tệp trong RPA có thể cần được lấy ra/thay thế tùy cấu trúc game. Không ghi đè game gốc ngay.

## Kiểm thử

```bash
.venv/bin/python -m unittest discover -s tests -v
node --check static/app.js
```

Kiểm thử bao gồm nhập `.rpy`, giải nén RPA 2/3, giải biên dịch mẫu `.rpyc` thực, ngữ cảnh Gemini, nhập JSON, bảo vệ biến/thẻ, xuất ZIP và giữ nguyên phần mã không dịch.

Kiểm thử trình duyệt tùy chọn: `scripts/browser-smoke.cjs` dùng Playwright và Chromium có sẵn. Cài Playwright bên ngoài dự án rồi đặt `DICHRENPY_PLAYWRIGHT` thành đường dẫn package; có thể đặt `CHROMIUM_PATH` và `DICHRENPY_URL`. Chạy app trước, rồi chạy `node scripts/browser-smoke.cjs`. Script tạo và xóa riêng dự án mẫu kiểm thử, xác nhận nhập sai/đúng, xuất ZIP, mở lại dự án và bố cục di động. Không gọi Gemini thật.

Không cần tạo Git worktree: dùng checkout hiện tại trong môi trường đám mây. Cài đặt và dữ liệu được giữ trên đĩa; tiến trình app phải khởi động lại ở phiên làm việc mới.
