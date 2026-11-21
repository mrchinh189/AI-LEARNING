# OpenProject cho nhóm nhỏ: cài đặt, cập nhật và tự phát triển tính năng

Bộ cấu hình này chạy [OpenProject](https://github.com/opf/openproject) bằng Docker Compose. Nó dùng **image riêng của nhóm**, tức image chính thức cộng thêm các plugin trong thư mục `plugins/`. Nhờ vậy nhóm vừa nhận được bản cập nhật chính thức, vừa thêm được tính năng riêng mà không phải sửa lõi OpenProject.

Đã kiểm thử với OpenProject **17.9.8** (tag `17`): build image, chạy toàn bộ stack, plugin hiện trong *Quản trị → Plugins*, giao diện tiếng Việt, sao lưu và khôi phục đều chạy được.

## Kiến trúc

```
Trình duyệt ──► proxy (Caddy, cổng 8080 hoặc 80/443, tự cấp HTTPS khi có tên miền)
                 ├── /hocuspocus ──► hocuspocus (soạn thảo cộng tác)
                 └── /*          ──► web (Rails, image team-openproject)
                                     worker  (job nền: email, import...)
                                     cron    (tác vụ định kỳ)
                                     seeder  (migrate + seed mỗi lần khởi động rồi thoát)
                                     db      (PostgreSQL 17)  · cache (Memcached)
```

| File | Vai trò |
|---|---|
| `Dockerfile` | Build `team-openproject:<TAG>` từ image chính thức, kèm plugin |
| `Gemfile.plugins` | Danh sách plugin (plugin nội bộ hoặc lấy từ git) |
| `plugins/openproject-team_extensions/` | Plugin của nhóm, nơi viết tính năng mới |
| `docker-compose.yml` | Toàn bộ các service |
| `Caddyfile` | Reverse proxy và HTTPS |
| `.env.example` | Mẫu cấu hình (phiên bản, tên miền, mật khẩu) |
| `op.sh` | Lệnh quản trị: init, up, update, backup, restore, logs, console |

## 1. Cài đặt

Yêu cầu: máy Linux có Docker Engine và Docker Compose v2, tối thiểu 4 GB RAM (nên có 8 GB) và 20 GB đĩa.

```bash
git clone https://github.com/mrchinh189/ai-learning.git
cd ai-learning/deploy/openproject
./op.sh init      # tạo .env với các khoá bí mật ngẫu nhiên
nano .env         # sửa OPENPROJECT_HOST__NAME, cổng, tên miền
./op.sh up        # build image kèm plugin rồi chạy toàn bộ
./op.sh logs web  # chờ đến khi web sẵn sàng (lần đầu mất 2–5 phút)
```

Sau đó mở `http://<máy-chủ>:8080` và đăng nhập `admin` / `admin`. Hệ thống sẽ yêu cầu đổi mật khẩu ngay.

### Chạy với tên miền và HTTPS

Trỏ DNS của tên miền (ví dụ `pm.congty.vn`) về máy chủ, mở cổng 80 và 443, rồi sửa `.env`:

```
SITE_ADDRESS=pm.congty.vn
HTTP_PORT=80
HTTPS_PORT=443
OPENPROJECT_HOST__NAME=pm.congty.vn
OPENPROJECT_HTTPS=true
COLLABORATIVE_SERVER_URL=wss://pm.congty.vn/hocuspocus
```

Chạy lại `./op.sh up`. Caddy sẽ tự xin chứng chỉ Let's Encrypt.

Sau khi cài, nên cấu hình gửi email (SMTP) trong *Quản trị → Email và thông báo*.

## 2. Cập nhật OpenProject

- **Bản vá trong cùng phiên bản lớn** (ví dụ 17.9.8 lên 17.9.9): chỉ cần chạy `./op.sh update`.
- **Lên phiên bản lớn mới** (ví dụ 17 lên 18): đọc [ghi chú phát hành](https://www.openproject.org/docs/release-notes/) trước. Sau đó đổi `TAG=18` và `HOCUSPOCUS_TAG` trong `.env`, rồi chạy `./op.sh update`.

`./op.sh update` làm lần lượt các bước:

1. Sao lưu database và file đính kèm vào `backups/`.
2. Kéo image chính thức mới nhất của tag đó và build lại image kèm plugin.
3. Chạy `seeder` để migrate database, rồi khởi động lại các service.

Nếu có lỗi, quay về tag cũ trong `.env` rồi khôi phục bản sao lưu:

```bash
./op.sh restore backups/db-<thời-gian>.dump backups/assets-<thời-gian>.tar.gz
```

Lưu ý:
- Kiểm tra plugin trên môi trường thử trước khi lên phiên bản lớn, vì API nội bộ có thể thay đổi.
- Nên đặt lịch sao lưu hằng ngày, ví dụ bằng crontab: `0 2 * * * cd /đường/dẫn/deploy/openproject && ./op.sh backup`. Định kỳ chép thư mục `backups/` sang máy khác.

## 3. Thêm tính năng: viết plugin (cách khuyên dùng)

OpenProject là ứng dụng Rails. Plugin là một Rails engine được nạp vào OpenProject. Plugin có thể:

- thêm model, controller, view, route và migration database;
- thêm menu, quyền truy cập, module dự án và bản dịch;
- *patch* hành vi của class lõi (ví dụ `WorkPackage`) và gắn *hook* vào giao diện;
- mở rộng API v3.

Viết tính năng trong plugin giúp cập nhật OpenProject gần như không bị xung đột code. Chỉ những chỗ plugin dùng API nội bộ mới cần kiểm tra lại.

Plugin của nhóm nằm tại `plugins/openproject-team_extensions/`. Điểm bắt đầu là `lib/open_project/team_extensions/engine.rb`.

```
plugins/openproject-team_extensions/
├── openproject-team_extensions.gemspec
├── lib/open_project/team_extensions/engine.rb   # đăng ký plugin, menu, quyền, patch
├── lib/open_project/team_extensions/version.rb  # tăng version mỗi lần phát hành
├── config/locales/{vi,en}.yml                   # bản dịch
├── app/   (tự tạo khi cần: controllers, models, views...)
└── db/migrate/ (tự tạo khi cần)
```

Tài liệu và ví dụ để tham khảo:
- [Hướng dẫn tạo plugin](https://www.openproject.org/docs/development/create-openproject-plugin/)
- Plugin mẫu [opf/openproject-proto_plugin](https://github.com/opf/openproject-proto_plugin): menu, hook vào view, menu dự án...
- Các module có sẵn trong lõi, thư mục [`modules/`](https://github.com/opf/openproject/tree/dev/modules) (ví dụ `avatars`, `github_integration`). Đây là plugin thật và là ví dụ tốt nhất.

### Môi trường phát triển (máy lập trình viên)

Không nên viết code bằng cách build image Docker rồi thử, vì mỗi lần build rất chậm. Hãy dựng môi trường dev của OpenProject để code tự nạp lại:

```bash
git clone https://github.com/opf/openproject.git --branch release/17.9 openproject-core
cd openproject-core
# Làm theo docs/development/development-environment/ (có bản Docker và bản cài trực tiếp)
```

Sau đó khai báo plugin trong `openproject-core/Gemfile.plugins`, trỏ tới thư mục plugin của repo này:

```ruby
group :opf_plugins do
  gem "openproject-team_extensions", path: "../ai-learning/deploy/openproject/plugins/openproject-team_extensions"
end
```

Chạy `bundle install` rồi khởi động OpenProject ở chế độ dev. Khi đã viết và test xong, commit plugin vào repo này, rồi chạy `./op.sh up` trên server để build lại image.

Lưu ý: hướng dẫn dựng môi trường dev ở trên chưa được kiểm thử trong phiên làm việc này, chỉ phần chạy production đã được kiểm thử.

### Thêm plugin của bên thứ ba

Thêm dòng `gem ...` vào `Gemfile.plugins` (xem ví dụ trong file), rồi chạy `./op.sh up`.

Nếu plugin có code frontend (Angular), bỏ dấu `#` ở dòng `RUN rm -f config/frontend_assets.manifest.json` trong `Dockerfile` để frontend được biên dịch lại. Bước này cần ít nhất 4 GB RAM và mất thêm vài phút. Xem [tài liệu Docker → OpenProject plugins](https://www.openproject.org/docs/installation-and-operations/installation/docker/#openproject-plugins).

## 4. Khi thật sự phải sửa lõi: fork

Chỉ fork khi plugin không làm được, ví dụ cần sửa sâu giao diện Angular hoặc thay đổi logic lõi không có điểm mở rộng:

1. Fork `opf/openproject` và tạo nhánh `team/17.9` từ `release/17.9`.
2. Giữ các thay đổi nhỏ, mỗi thay đổi một commit rõ ràng để dễ áp lại.
3. Build image từ fork: `docker build -f docker/prod/Dockerfile --target slim -t team-openproject:17 .`, rồi chạy `docker compose up -d --no-build`. Không dùng `./op.sh up` vì lệnh đó build lại từ `Dockerfile` của thư mục này và ghi đè image vừa build từ fork.
4. Khi có bản mới, chạy `git fetch upstream` rồi rebase hoặc merge `release/17.x` mới vào nhánh của nhóm và xử lý xung đột.

Cách này tốn công bảo trì hơn nhiều so với plugin, nên hãy thử plugin trước. Cũng có thể đề xuất thay đổi lên upstream để không phải duy trì fork.

## Lệnh thường dùng

```bash
./op.sh status          # trạng thái container
./op.sh logs web        # log của web (worker, cron, seeder, db...)
./op.sh console         # Rails console để kiểm tra và sửa dữ liệu
./op.sh backup          # sao lưu ngay
./op.sh down            # dừng (dữ liệu vẫn nằm trong volume)
```

Giấy phép: OpenProject dùng GPLv3. Nếu phân phối bản đã sửa ra ngoài nhóm thì phải công bố mã nguồn tương ứng. Dùng nội bộ thì không bắt buộc.
