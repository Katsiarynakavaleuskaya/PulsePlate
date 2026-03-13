#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "pathname"

INFO_PLIST_LOCALES = {
  "en-US" => "en.lproj",
  "ru-RU" => "ru.lproj",
  "es-ES" => "es.lproj"
}.freeze

BLOCKED_MEDICAL_CLAIMS = /
  \b(?:BMI|IMC|medical|diagnos(?:e|es|ed|ing|is|tic)?|treat(?:ment|ments|s|ed|ing)?|cure(?:s|d|ing)?)\b|
  \b(?:ИМТ|диагноз(?:а|ом|е|ы)?|леч(?:ит|ить|ен|ени(?:е|я)))\b|
  \b(?:m[eé]dic(?:o|a|os|as|al|amente)?|tratamient(?:o|os)?|cura(?:r|ción|ciones|s)?)\b
/ix.freeze

def parse_strings(pathname)
  entries = {}
  pathname.read.each_line do |line|
    match = line.match(/"(?<key>[^"]+)"\s*=\s*"(?<value>(?:[^"\\]|\\.)*)";/)
    next unless match

    entries[match[:key]] = match[:value].gsub(/\\(.)/) { Regexp.last_match(1) }
  end
  entries
end

if ARGV.length != 3
  abort "Usage: validate_healthkit_copy.rb <pulseplate_root> <review_notes> <privacy_json>"
end

app_root = Pathname(ARGV[0])
review_notes_path = Pathname(ARGV[1])
privacy_json_path = Pathname(ARGV[2])

errors = []

INFO_PLIST_LOCALES.each_value do |folder_name|
  strings_path = app_root.join(folder_name, "InfoPlist.strings")
  unless strings_path.file?
    errors << "Missing localized InfoPlist.strings: #{strings_path}"
    next
  end

  entries = parse_strings(strings_path)
  share_copy = entries["NSHealthShareUsageDescription"]
  update_copy = entries["NSHealthUpdateUsageDescription"]

  if share_copy.to_s.empty?
    errors << "NSHealthShareUsageDescription must exist in #{strings_path}"
    next
  end

  errors << "NSHealthUpdateUsageDescription must be absent for read-only HealthKit in #{strings_path}" unless update_copy.to_s.empty?
  errors << "Blocked medical claim wording found in #{strings_path}" if share_copy.match?(BLOCKED_MEDICAL_CLAIMS)
end

unless review_notes_path.file?
  errors << "Missing reviewer notes: #{review_notes_path}"
end

unless privacy_json_path.file?
  errors << "Missing app privacy JSON: #{privacy_json_path}"
end

if review_notes_path.file?
  notes = review_notes_path.read
  %w[HealthKit wellness consent read-only].each do |required_phrase|
    next if notes.downcase.include?(required_phrase.downcase)

    errors << "Reviewer notes must mention '#{required_phrase}'"
  end
end

if privacy_json_path.file?
  begin
    privacy_entries = JSON.parse(privacy_json_path.read)
    unless privacy_entries.is_a?(Array) && !privacy_entries.empty?
      errors << "App privacy JSON must be a non-empty array"
    end

    if privacy_entries.is_a?(Array) && !privacy_entries.any? { |entry| entry.is_a?(Hash) && Array(entry["data_protections"]).include?("DATA_NOT_COLLECTED") }
      errors << "App privacy JSON must declare on-device HealthKit data as DATA_NOT_COLLECTED"
    end
  rescue JSON::ParserError
    errors << "Invalid JSON in #{privacy_json_path}"
  end
end

if errors.empty?
  puts "validate_healthkit_copy: OK"
  exit 0
end

warn errors.join("\n")
exit 1
