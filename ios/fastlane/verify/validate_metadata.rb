#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "pathname"
require "uri"

REQUIRED_LOCALES = %w[en-US ru-RU es-ES].freeze
# Policy: repo metadata stays launch-ready and source-controlled across locales,
# so we require a complete localized pack even for ASC fields that can be
# conditionally optional in some submission contexts.
REQUIRED_FILES = %w[
  name.txt
  subtitle.txt
  description.txt
  keywords.txt
  promotional_text.txt
  release_notes.txt
  privacy_url.txt
  support_url.txt
  marketing_url.txt
].freeze
MAX_NAME_LENGTH = 30
MAX_DESCRIPTION_LENGTH = 4000

def read_text(pathname)
  pathname.read.strip
end

def validate_https_url(pathname, errors)
  value = read_text(pathname)
  uri = URI.parse(value)
  unless uri.is_a?(URI::HTTPS) && !uri.host.to_s.empty?
    errors << "Expected HTTPS URL in #{pathname}"
  end
rescue URI::InvalidURIError
  errors << "Invalid URL in #{pathname}"
end

metadata_root = Pathname(ARGV.fetch(0) { raise "Usage: validate_metadata.rb <metadata_path> <review_notes> <privacy_json>" })
review_notes_path = Pathname(ARGV.fetch(1))
privacy_json_path = Pathname(ARGV.fetch(2))

errors = []

REQUIRED_LOCALES.each do |locale|
  locale_dir = metadata_root.join(locale)
  unless locale_dir.directory?
    errors << "Missing metadata locale directory: #{locale_dir}"
    next
  end

  REQUIRED_FILES.each do |filename|
    file_path = locale_dir.join(filename)
    unless file_path.file?
      errors << "Missing metadata file: #{file_path}"
      next
    end

    if read_text(file_path).empty?
      errors << "Metadata file is empty: #{file_path}"
    end
  end

  subtitle = locale_dir.join("subtitle.txt")
  name = locale_dir.join("name.txt")
  description = locale_dir.join("description.txt")

  errors << "Name too long in #{name}" if name.file? && read_text(name).length > MAX_NAME_LENGTH
  errors << "Subtitle too long in #{subtitle}" if subtitle.file? && read_text(subtitle).length > 30
  errors << "Description too long in #{description}" if description.file? && read_text(description).length > MAX_DESCRIPTION_LENGTH

  promotional_text = locale_dir.join("promotional_text.txt")
  if promotional_text.file? && read_text(promotional_text).length > 170
    errors << "Promotional text too long in #{promotional_text}"
  end

  keywords = locale_dir.join("keywords.txt")
  if keywords.file?
    raw_keywords = read_text(keywords)
    errors << "Keywords exceed 100 characters in #{keywords}" if raw_keywords.length > 100
    has_multiple_keywords = raw_keywords.strip.split(/\s+/).length > 1
    if raw_keywords.match?(/[;|]/)
      errors << "Keywords must be comma-separated in #{keywords}"
    elsif has_multiple_keywords && !raw_keywords.include?(",")
      errors << "Keywords must be comma-separated in #{keywords}"
    end
  end

  %w[privacy_url.txt support_url.txt marketing_url.txt].each do |url_file|
    validate_https_url(locale_dir.join(url_file), errors) if locale_dir.join(url_file).file?
  end
end

unless review_notes_path.file? && !read_text(review_notes_path).empty?
  errors << "Missing or empty reviewer notes: #{review_notes_path}"
end

unless privacy_json_path.file?
  errors << "Missing app privacy JSON: #{privacy_json_path}"
end

if privacy_json_path.file?
  begin
    parsed = JSON.parse(privacy_json_path.read)
    errors << "App privacy JSON must be a non-empty array" unless parsed.is_a?(Array) && !parsed.empty?
  rescue JSON::ParserError
    errors << "Invalid JSON in #{privacy_json_path}"
  end
end

if errors.empty?
  puts "validate_metadata: OK"
  exit 0
end

warn errors.join("\n")
exit 1
