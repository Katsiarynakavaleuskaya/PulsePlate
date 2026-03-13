#!/usr/bin/env ruby
# frozen_string_literal: true

require "pathname"

PNG_SIGNATURE = "\x89PNG\r\n\x1A\n".b
ALLOWED_PROFILES = ["sRGB", "ICC:Display P3"].freeze

def png_chunks(pathname)
  File.open(pathname, "rb") do |file|
    signature = file.read(8)
    raise "Invalid PNG signature: #{pathname}" unless signature == PNG_SIGNATURE

    chunks = []
    until file.eof?
      length_data = file.read(4)
      break unless length_data

      length = length_data.unpack1("N")
      chunk_type = file.read(4)
      chunk_data = file.read(length)
      file.read(4) # CRC
      chunks << [chunk_type, chunk_data]
      break if chunk_type == "IEND"
    end

    chunks
  end
end

def profile_name_for(pathname)
  png_chunks(pathname).each do |chunk_type, chunk_data|
    return "sRGB" if chunk_type == "sRGB"
    next unless chunk_type == "iCCP"

    return "ICC:#{chunk_data.split("\x00".b, 2).first.force_encoding("UTF-8")}"
  end

  nil
end

root = Pathname(ARGV.fetch(0) do
  raise "Usage: validate_color_gamut.rb <screenshots_path>"
end)

raise "Screenshots path does not exist: #{root}" unless root.exist?

png_files = root.glob("**/*.png").sort
raise "No PNG screenshots found under #{root}" if png_files.empty?

profiles = Hash.new { |hash, key| hash[key] = [] }
errors = []

png_files.each do |pathname|
  profile_name = profile_name_for(pathname)
  if profile_name.nil?
    errors << "Missing color profile chunk (sRGB or iCCP) in #{pathname}"
    next
  end

  unless ALLOWED_PROFILES.include?(profile_name)
    errors << "Unsupported color profile in #{pathname}: #{profile_name}. Allowed: #{ALLOWED_PROFILES.join(', ')}"
    next
  end

  profiles[profile_name] << pathname
end

if profiles.keys.size > 1
  errors << "Mixed color profiles detected: #{profiles.keys.join(', ')}"
end

if errors.empty?
  puts "validate_color_gamut: OK (#{profiles.keys.first})"
  exit 0
end

warn errors.join("\n")
exit 1
