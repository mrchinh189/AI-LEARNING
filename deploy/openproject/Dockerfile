# Image OpenProject riêng của nhóm = image chính thức + các plugin trong ./plugins
#
# Cập nhật OpenProject: đổi OP_VERSION (hoặc TAG trong .env) rồi build lại.
ARG OP_VERSION=17

# ---- Giai đoạn 1: cài gem của plugin và biên dịch lại asset (dựa trên image đầy đủ)
FROM openproject/openproject:${OP_VERSION} AS plugin

COPY --chown=app:app plugins /app/vendor/plugins
COPY --chown=app:app Gemfile.plugins /app/

# Nếu plugin cần thêm gói NPM thì cài ở đây:
# RUN npm add <ten-goi>

RUN bundle config unset deployment && bundle install && bundle config set deployment 'true'
# Plugin có code frontend (Angular): bỏ # ở dòng dưới để biên dịch lại frontend (cần >= 4 GB RAM)
# RUN rm -f config/frontend_assets.manifest.json
RUN ./docker/prod/setup/precompile-assets.sh

# ---- Giai đoạn 2: image slim dùng cho web, worker, cron, seeder
FROM openproject/openproject:${OP_VERSION}-slim

COPY --from=plugin /usr/bin/git /usr/bin/git
COPY --chown=$APP_USER:$APP_USER --from=plugin /app/vendor/bundle /app/vendor/bundle
COPY --chown=$APP_USER:$APP_USER --from=plugin /usr/local/bundle /usr/local/bundle
COPY --chown=$APP_USER:$APP_USER --from=plugin /app/vendor/plugins /app/vendor/plugins
COPY --chown=$APP_USER:$APP_USER --from=plugin /app/public/assets /app/public/assets
COPY --chown=$APP_USER:$APP_USER --from=plugin /app/config/frontend_assets.manifest.json /app/config/frontend_assets.manifest.json
COPY --chown=$APP_USER:$APP_USER --from=plugin /app/Gemfile.* /app/
