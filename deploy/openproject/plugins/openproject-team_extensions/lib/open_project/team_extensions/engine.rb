# frozen_string_literal: true

require "open_project/plugins"

module OpenProject::TeamExtensions
  class Engine < ::Rails::Engine
    engine_name :openproject_team_extensions

    include OpenProject::Plugins::ActsAsOpEngine

    register "openproject-team_extensions",
             author_url: "https://github.com/mrchinh189/ai-learning",
             requires_openproject: ">= 17.0.0"

    # Thêm tính năng ở đây, ví dụ (xem plugin mẫu openproject-proto_plugin):
    #   - menu:    menu :project_menu, :my_page, { controller: "/my_things", action: :index }, ...
    #   - quyền:   project_module :my_module do permission :view_my_things, ... end
    #   - patch:   patches %i[WorkPackage]  -> lib/open_project/team_extensions/patches/work_package_patch.rb
    #   - hook:    lib/open_project/team_extensions/hooks.rb (OpenProject::Hook::ViewListener)
    # Migration đặt trong db/migrate, controller/view trong app/, bản dịch trong config/locales.
  end
end
