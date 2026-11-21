#!/usr/bin/env bash
# Script quản trị OpenProject của nhóm. Chạy trong thư mục deploy/openproject.
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE="docker compose"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

need_env() {
  [ -f .env ] || { echo "Chưa có .env. Chạy: ./op.sh init"; exit 1; }
}

case "${1:-help}" in
  init)
    # Tạo .env với các khoá bí mật ngẫu nhiên
    [ -f .env ] && { echo ".env đã tồn tại, bỏ qua."; exit 0; }
    cp .env.example .env
    for k in SECRET_KEY_BASE POSTGRES_PASSWORD COLLABORATIVE_SERVER_SECRET; do
      sed -i "s|^$k=.*|$k=$(openssl rand -hex 32)|" .env
    done
    echo "Đã tạo .env. Hãy sửa OPENPROJECT_HOST__NAME và các cổng nếu cần."
    ;;
  build)
    need_env
    $COMPOSE build --pull seeder
    ;;
  up|start)
    need_env
    $COMPOSE build seeder
    $COMPOSE up -d
    echo "Đang khởi động. Theo dõi: ./op.sh logs"
    ;;
  down|stop)
    $COMPOSE down
    ;;
  update)
    # Sao lưu -> kéo image mới -> build lại với plugin -> migrate -> chạy lại
    need_env
    "$0" backup
    $COMPOSE pull db cache hocuspocus proxy
    $COMPOSE build --pull seeder
    $COMPOSE up -d
    ;;
  backup)
    need_env
    mkdir -p "$BACKUP_DIR"
    ts=$(date +%Y%m%d-%H%M%S)
    $COMPOSE exec -T db pg_dump -U postgres -Fc openproject > "$BACKUP_DIR/db-$ts.dump"
    $COMPOSE run --rm --no-deps -T --entrypoint "" web \
      tar -C /var/openproject/assets -czf - . > "$BACKUP_DIR/assets-$ts.tar.gz"
    echo "Đã sao lưu: $BACKUP_DIR/db-$ts.dump, $BACKUP_DIR/assets-$ts.tar.gz"
    ;;
  restore)
    # ./op.sh restore backups/db-XXXX.dump [backups/assets-XXXX.tar.gz]
    need_env
    db="${2:?Cần đường dẫn file db-*.dump}"
    $COMPOSE stop web worker cron
    $COMPOSE exec -T db pg_restore -U postgres -d openproject --clean --if-exists < "$db"
    if [ -n "${3:-}" ]; then
      $COMPOSE run --rm --no-deps -T --entrypoint "" web \
        tar -C /var/openproject/assets -xzf - < "$3"
    fi
    $COMPOSE up -d
    ;;
  logs)
    $COMPOSE logs -f --tail=100 "${@:2}"
    ;;
  console)
    $COMPOSE exec web bundle exec rails console
    ;;
  status|ps)
    $COMPOSE ps
    ;;
  *)
    cat <<USAGE
Cách dùng: ./op.sh <lệnh>
  init      Tạo .env với khoá bí mật ngẫu nhiên
  up        Build image (kèm plugin) và chạy toàn bộ
  down      Dừng
  update    Sao lưu, kéo bản mới, build lại, migrate, chạy lại
  backup    Sao lưu database + file đính kèm vào ./backups
  restore   Khôi phục: ./op.sh restore backups/db-*.dump [backups/assets-*.tar.gz]
  logs      Xem log (vd: ./op.sh logs web)
  console   Mở Rails console
  status    Trạng thái các container
USAGE
    ;;
esac
