# frozen_string_literal: true

$:.push File.expand_path("lib", __dir__)

require "open_project/team_extensions/version"

Gem::Specification.new do |s|
  s.name        = "openproject-team_extensions"
  s.version     = OpenProject::TeamExtensions::VERSION
  s.authors     = "Team"
  s.summary     = "Các tính năng bổ sung của nhóm cho OpenProject"
  s.description = "Plugin nội bộ: nơi đặt mọi tuỳ biến để không phải sửa lõi OpenProject."
  s.license     = "GPLv3"

  s.files = Dir["{app,config,db,lib}/**/*"] + %w(README.md)
end
