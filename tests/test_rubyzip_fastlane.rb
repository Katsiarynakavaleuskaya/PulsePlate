# frozen_string_literal: true

require 'tmpdir'
require_relative '../scripts/ci/check_rubyzip_fastlane'

# This native, stdlib-only fixture suite belongs to the Ruby-enabled CI job, not pytest.
module RubyzipFastlaneFixtures
  FORK = 'https://github.com/Katsiarynakavaleuskaya/fastlane.git'
  REVISION = '1ac01395d37bf7e6b88b3d0bcba5f84af841fcbc'

  def self.fixture(version = '3.4.0')
    manifest = <<~GEMFILE
      source "https://rubygems.org"
      gem "CFPropertyList", "= 3.0.8"
      gem "fastlane", "= 2.237.0", git: "#{FORK}", ref: "#{REVISION}"
      gem "public_suffix", "< 7"
      gem "rubyzip", "= #{version}"
    GEMFILE
    lock = <<~LOCK
      GIT
        remote: #{FORK}
        revision: #{REVISION}
        ref: #{REVISION}
        specs:
          fastlane (2.237.0)
            CFPropertyList (>= 2.3, < 5.0.0)
            bundler (>= 2.4.0, < 5.0.0)
            excon (>= 0.71.0, < 2.0.0)
            json (< 3.0.0)
            jwt (>= 2.10.3, < 4)
            rubyzip (>= 3.4.0, < 4.0.0)

      GEM
        remote: https://rubygems.org/
        specs:
          CFPropertyList (3.0.8)
          excon (1.5.0)
          json (2.19.9)
          jwt (3.2.0)
          public_suffix (6.0.2)
          rubyzip (#{version})

      PLATFORMS
        ruby

      DEPENDENCIES
        CFPropertyList (= 3.0.8)
        fastlane (= 2.237.0)!
        public_suffix (< 7)
        rubyzip (= #{version})

      BUNDLED WITH
         2.4.22
    LOCK
    [manifest, lock]
  end

  def self.check_case(name, manifest, lock, surfaces, accepted: false)
    File.write('Gemfile', manifest)
    begin
      report = RubyzipFastlaneGuard.check(manifest, lock, surfaces)
    rescue RubyzipFastlaneGuard::Hold, Bundler::LockfileError, Gem::Requirement::BadRequirementError
      raise "#{name}: valid fixture rejected" if accepted
      report = nil
    end
    raise "#{name}: invalid fixture accepted" if !accepted && report
    raise "#{name}: Gemfile was evaluated" if File.exist?('forbidden-side-effect')
    report
  end

  def self.run
    count = 0
    Dir.mktmpdir('rubyzip-fastlane-guard-fixtures') do |directory|
      Dir.chdir(directory) do
        ['3.4.0', '3.4.1', '3.9.0'].each do |version|
          report = check_case(version, *fixture(version), ['ios/Gemfile', 'ios/Gemfile.lock'], accepted: true)
          unless report[:status] == 'PASS' && report[:rubyzip] == [version] &&
                 report[:fastlane_revision] == REVISION && report[:independent_advisories] == 4 &&
                 report[:advisory_records].length == 5 && report[:tracked_surfaces] == ['ios/Gemfile', 'ios/Gemfile.lock']
            raise "#{version}: incomplete accepted evidence"
          end
          count += 1
        end
        ['1.2.0', '1.2.1', '1.2.2', '1.3.0', '2.4.1', '3.4.0.rc1', '3.4.0-pre', '4.0.0'].each do |version|
          check_case(version, *fixture(version), ['ios/Gemfile', 'ios/Gemfile.lock'])
          count += 1
        end
        %w[
          new_surface missing_surface surface_alias duplicate_surface invalid_manifest manifest_code
          interpolation escaped_name dependency_alias duplicate_manifest duplicate_option wrong_source
          short_ref wrong_revision version_spoof duplicate_spec duplicate_dependency duplicate_edge
          duplicate_section duplicate_source_option unsupported_section malformed_lock missing_rubyzip
          missing_pin_marker manifest_lock_mismatch incompatible_fork unsafe_constraint cfpropertylist_floor
          public_suffix_constraint jwt_floor json_floor excon_floor bundler_drift empty_platforms
          duplicate_platform trailing_source_alias
        ].each do |mutation|
          manifest, lock = fixture
          surfaces = ['ios/Gemfile', 'ios/Gemfile.lock']
          case mutation
          when 'new_surface' then surfaces << 'other/Gemfile'
          when 'missing_surface' then surfaces.pop
          when 'surface_alias' then surfaces << 'ios/gems.rb'
          when 'duplicate_surface' then surfaces << 'ios/Gemfile'
          when 'invalid_manifest' then manifest += 'gem "unfinished'
          when 'manifest_code' then manifest += "File.write(\"forbidden-side-effect\", \"must not execute\")\n"
          when 'interpolation' then manifest = manifest.gsub('"rubyzip"', '"ruby#{"zip"}"')
          when 'escaped_name' then manifest = manifest.gsub('"rubyzip"') { '"\x72ubyzip"' }
          when 'dependency_alias'
            manifest, lock = manifest.gsub('rubyzip', 'RubyZip'), lock.gsub('rubyzip', 'RubyZip')
          when 'duplicate_manifest' then manifest += "gem \"rubyzip\", \"= 3.4.0\"\n"
          when 'duplicate_option'
            manifest = manifest.gsub("git: \"#{FORK}\"", "git: \"#{FORK}\", git: \"#{FORK}\"")
          when 'wrong_source'
            manifest, lock = manifest.gsub(FORK, 'https://github.com/other/fastlane.git'), lock.gsub(FORK, 'https://github.com/other/fastlane.git')
          when 'short_ref'
            manifest, lock = manifest.gsub(REVISION, REVISION[0, 7]), lock.gsub(REVISION, REVISION[0, 7])
          when 'wrong_revision' then lock = lock.gsub("revision: #{REVISION}", "revision: #{'0' * 40}")
          when 'version_spoof'
            manifest, lock = manifest.gsub('2.237.0', '2.238.0'), lock.gsub('2.237.0', '2.238.0')
          when 'duplicate_spec'
            lock = lock.gsub('    rubyzip (3.4.0)', "    rubyzip (3.4.0)\n    rubyzip (3.4.0)")
          when 'duplicate_dependency'
            lock = lock.gsub('  rubyzip (= 3.4.0)', "  rubyzip (= 3.4.0)\n  rubyzip (= 3.4.0)")
          when 'duplicate_edge'
            lock = lock.gsub('      rubyzip (>= 3.4.0, < 4.0.0)', "      rubyzip (>= 3.4.0, < 4.0.0)\n      rubyzip (>= 3.4.0, < 4.0.0)")
          when 'duplicate_section' then lock += "\nBUNDLED WITH\n   2.4.22\n"
          when 'duplicate_source_option'
            lock = lock.gsub("  remote: #{FORK}", "  remote: #{FORK}\n  remote: #{FORK}")
          when 'unsupported_section' then lock += "\nUNTRUSTED\n  extension\n"
          when 'malformed_lock' then lock = lock.gsub('    rubyzip (3.4.0)', '    rubyzip (nonsense)')
          when 'missing_rubyzip' then lock = lock.gsub("    rubyzip (3.4.0)\n", '')
          when 'missing_pin_marker' then lock = lock.gsub('fastlane (= 2.237.0)!', 'fastlane (= 2.237.0)')
          when 'manifest_lock_mismatch' then manifest = manifest.gsub('"= 3.4.0"', '"= 3.4.1"')
          when 'incompatible_fork'
            lock = lock.gsub('rubyzip (>= 3.4.0, < 4.0.0)', 'rubyzip (>= 2.0.0, < 3.0.0)')
          when 'unsafe_constraint'
            manifest, lock = manifest.gsub('"= 3.4.0"', '">= 0"'), lock.gsub('rubyzip (= 3.4.0)', 'rubyzip (>= 0)')
          when 'cfpropertylist_floor' then lock = lock.gsub('    CFPropertyList (3.0.8)', '    CFPropertyList (4.0.0)')
          when 'public_suffix_constraint'
            manifest, lock = manifest.gsub('"< 7"', '"< 8"'), lock.gsub('public_suffix (< 7)', 'public_suffix (< 8)')
          when 'jwt_floor' then lock = lock.gsub('jwt (3.2.0)', 'jwt (3.1.0)')
          when 'json_floor' then lock = lock.gsub('json (2.19.9)', 'json (2.19.8)')
          when 'excon_floor' then lock = lock.gsub('excon (1.5.0)', 'excon (1.4.2)')
          when 'bundler_drift' then lock = lock.gsub('   2.4.22', '   2.5.11')
          when 'empty_platforms' then lock = lock.gsub("PLATFORMS\n  ruby", 'PLATFORMS')
          when 'duplicate_platform' then lock = lock.gsub("PLATFORMS\n  ruby", "PLATFORMS\n  ruby\n  ruby")
          when 'trailing_source_alias' then lock = lock.gsub("  remote: #{FORK}", "  remote: #{FORK}/")
          else raise "Unimplemented fixture: #{mutation}"
          end
          check_case(mutation, manifest, lock, surfaces)
          count += 1
        end
      end
    end
    puts(JSON.generate(status: 'PASS', cases: count, ruby: RUBY_VERSION, bundler: Bundler::VERSION))
  end
end

RubyzipFastlaneFixtures.run
