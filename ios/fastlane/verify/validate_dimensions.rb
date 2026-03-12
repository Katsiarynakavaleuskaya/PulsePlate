#!/usr/bin/env ruby
# frozen_string_literal: true

require "pathname"

SCREENSHOT_NAMES = %w[
  01_welcome
  02_home
  03_plate
  04_pro_vip_paywall
  05_privacy_profile
  06_health_permission
].freeze

ALLOWED_DIMENSIONS = {
  iphone_6_9: [
    [1260, 2736],
    [1290, 2796],
    [1320, 2868]
  ],
  ipad_13: [
    [2048, 2732],
    [2064, 2752]
  ]
}.freeze

def png_dimensions(pathname)
  File.open(pathname, "rb") do |file|
    signature = file.read(8)
    raise "Invalid PNG signature: #{pathname}" unless signature == "\x89PNG\r\n\x1A\n".b

    _chunk_length = file.read(4)
    chunk_type = file.read(4)
    raise "Missing IHDR chunk: #{pathname}" unless chunk_type == "IHDR"

    width = file.read(4).unpack1("N")
    height = file.read(4).unpack1("N")
    [width, height]
  end
end

def scenario_name_for(filename)
  SCREENSHOT_NAMES.find do |name|
    filename.match?(%r{(?:^|[-_])#{Regexp.escape(name)}\.png$}i)
  end
end

def device_family_for(width, height)
  ALLOWED_DIMENSIONS.find do |family, sizes|
    sizes.include?([width, height])
  end&.first
end

root = Pathname(ARGV.fetch(0) do
  raise "Usage: validate_dimensions.rb <screenshots_path>"
end)

raise "Screenshots path does not exist: #{root}" unless root.exist?

locale_dirs = root.children.select(&:directory?).sort
raise "No locale directories found under #{root}" if locale_dirs.empty?

errors = []

locale_dirs.each do |locale_dir|
  files = locale_dir.children.select { |child| child.file? && child.extname.downcase == ".png" }.sort
  errors << "No PNG screenshots found in #{locale_dir}" if files.empty?

  coverage = Hash.new { |hash, key| hash[key] = [] }

  files.each do |file|
    scenario_name = scenario_name_for(file.basename.to_s)
    unless scenario_name
      errors << "Unexpected screenshot filename: #{file.basename}"
      next
    end

    width, height = png_dimensions(file)
    if width >= height
      errors << "Landscape screenshots are not allowed in v1: #{file.basename} (#{width}x#{height})"
      next
    end

    device_family = device_family_for(width, height)
    unless device_family
      allowed_sizes = ALLOWED_DIMENSIONS.values.flatten(1).map { |w, h| "#{w}x#{h}" }.join(", ")
      errors << "Unexpected screenshot size for #{file.basename}: #{width}x#{height}. Allowed: #{allowed_sizes}"
      next
    end

    coverage[scenario_name] << device_family
  end

  SCREENSHOT_NAMES.each do |scenario_name|
    families = coverage.fetch(scenario_name, []).uniq.sort
    missing = ALLOWED_DIMENSIONS.keys - families
    next if missing.empty?

    errors << "Locale #{locale_dir.basename}: screenshot '#{scenario_name}' is missing families #{missing.join(', ')}"
  end
end

if errors.empty?
  puts "validate_dimensions: OK"
  exit 0
end

warn errors.join("\n")
exit 1
