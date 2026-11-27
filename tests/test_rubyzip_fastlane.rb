# frozen_string_literal: true

require 'tmpdir'
require_relative '../scripts/ci/check_rubyzip_fastlane'

# This native, stdlib-only fixture suite belongs to the Ruby-enabled CI job, not pytest.
module RubyzipFastlaneFixtures
  FORK = 'https://github.com/Katsiarynakavaleuskaya/fastlane.git'
  REVISION = '1ac01395d37bf7e6b88b3d0bcba5f84af841fcbc'

  def self.fixture(version = '3.4.0', suffix_version = '7.0.5')
    manifest = <<~GEMFILE
      source "https://rubygems.org"
      gem "CFPropertyList", "= 3.0.8"
      gem "fastlane", "= 2.237.0", git: "#{FORK}", ref: "#{REVISION}"
      gem "public_suffix", "< 8"
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
          public_suffix (#{suffix_version})
          rubyzip (#{version})

      PLATFORMS
        ruby

      DEPENDENCIES
        CFPropertyList (= 3.0.8)
        fastlane (= 2.237.0)!
        public_suffix (< 8)
        rubyzip (= #{version})

      BUNDLED WITH
         2.4.22
    LOCK
    [manifest, lock]
  end

  def self.check_case(name, manifest, lock, surfaces, accepted: false, expected_hold: nil)
    File.write('Gemfile', manifest)
    begin
      report = RubyzipFastlaneGuard.check(manifest, lock, surfaces)
    rescue RubyzipFastlaneGuard::Hold, Bundler::LockfileError, Gem::Requirement::BadRequirementError => error
      raise "#{name}: valid fixture rejected (#{error.message})" if accepted
      observed = error.is_a?(Bundler::LockfileError) ? (error.cause&.message || error.message) : error.message
      if expected_hold && observed != expected_hold
        raise "#{name}: expected #{expected_hold}, observed #{observed}"
      end
      report = nil
    end
    raise "#{name}: invalid fixture accepted" if !accepted && report
    raise "#{name}: Gemfile was evaluated" if File.exist?('forbidden-side-effect')
    report
  end

  def self.addressable_fixture(rows = ['2.9.1'], direct: false)
    manifest, lock = fixture
    lock = lock.sub("      bundler (>= 2.4.0, < 5.0.0)\n",
                    "      addressable (>= 2.0.0, < 3.0.0)\n      bundler (>= 2.4.0, < 5.0.0)\n")
    rendered = rows.map { |row| "    addressable (#{row})\n      public_suffix (>= 2.0.2, < 8.0)\n" }.join
    lock = lock.sub("    CFPropertyList (3.0.8)\n", rendered + "    CFPropertyList (3.0.8)\n")
    lock = lock.sub("PLATFORMS\n  ruby\n", "PLATFORMS\n  ruby\n  x86_64-linux\n") if rows.any? { |row| row.end_with?('-x86_64-linux') }
    if direct
      manifest += "gem \"addressable\", \"= 2.9.1\"\n"
      lock = lock.sub("DEPENDENCIES\n", "DEPENDENCIES\n  addressable (= 2.9.1)\n")
    end
    [manifest, lock]
  end

  # These observations are independent of graph rejection order for overlapping ranges.
  ADDRESSABLE_BOUNDARIES = {
    'GHSA-9crm-g4mf-wc5j' => [%w[2.0.0 2.9.0], %w[1.9.9 2.9.1]],
    'GHSA-539f-xcgw-2gjg' => [%w[2.0.0 2.9.0], %w[1.9.9 2.9.1]],
    'GHSA-qq38-m9mg-xjj5' => [%w[0.0.1 2.9.0], %w[2.9.1]],
    'GHSA-j82w-28jv-3pmj' => [%w[2.3.0 2.9.0], %w[2.2.9 2.9.1]],
    'GHSA-9f42-57jx-vpp3' => [%w[2.3.0 2.9.0], %w[2.2.9 2.9.1]],
    'GHSA-8gmh-2hhj-2hv9' => [%w[2.2.5 2.9.0], %w[2.2.4 2.9.1]],
    'GHSA-h27x-rffw-24p4' => [%w[2.3.0 2.8.9], %w[2.2.9 2.9.0]],
    'GHSA-jxhc-q857-3j6g' => [%w[2.3.0 2.7.0], %w[2.2.9 2.7.1]]
  }.freeze

  def self.addressable_controls
    ranges = RubyzipFastlaneGuard::ADDRESSABLE_AFFECTED
    raise 'Addressable advisory inventory differs' unless ranges.keys == ADDRESSABLE_BOUNDARIES.keys

    ADDRESSABLE_BOUNDARIES.each do |advisory, (inside, outside)|
      require_range = ranges.fetch(advisory)
      unless inside.all? { |v| require_range.satisfied_by?(Gem::Version.new(v)) } &&
             outside.none? { |v| require_range.satisfied_by?(Gem::Version.new(v)) }
        raise "#{advisory}: Addressable boundary differs"
      end
    end

    surfaces = ['ios/Gemfile', 'ios/Gemfile.lock']
    positive = {
      'canonical-addressable' => [addressable_fixture, [['2.9.1', 'ruby']]],
      'future-safe-release' => [addressable_fixture(['2.10.0']), [['2.10.0', 'ruby']]],
      'all-safe-platforms' => [addressable_fixture(['2.9.1', '2.10.0-x86_64-linux']),
                               [['2.9.1', 'ruby'], ['2.10.0', 'x86_64-linux']]],
      'closed-graph-absence' => [fixture, []]
    }
    positive.each do |name, (inputs, expected)|
      report = check_case(name, *inputs, surfaces, accepted: true)
      actual = report.fetch(:addressable).map { |row| [row.fetch(:version), row.fetch(:platform)] }
      unless actual.sort == expected.sort && report[:addressable_advisory_records] == ADDRESSABLE_BOUNDARIES.keys
        raise "#{name}: incomplete Addressable postcondition #{actual.inspect}"
      end
    end

    manifest, lock = addressable_fixture
    direct_manifest, direct_lock = addressable_fixture(direct: true)
    affected = 'addressable_affected:GHSA-9crm-g4mf-wc5j'
    negatives = {
      'affected-base' => [addressable_fixture(['2.9.0']), affected],
      'affected-older-release' => [addressable_fixture(['2.7.0']), affected],
      'high-prerelease' => [addressable_fixture(['2.10.0.pre']), 'invalid_addressable_version'],
      'invalid-version-record' => [addressable_fixture(['nonsense']), 'Malformed version number string nonsense'],
      'missing-with-live-edge' => [addressable_fixture([]), 'incompatible_lock_dependency'],
      'safe-first-affected-later' => [addressable_fixture(['2.9.1', '2.9.0-x86_64-linux']), affected],
      'same-platform-ambiguity' => [addressable_fixture(['2.9.1', '2.10.0']), 'ambiguous_addressable_platform'],
      'non-registry-spec' => [[manifest, lock.sub("    addressable (2.9.1)\n      public_suffix (>= 2.0.2, < 8.0)\n", '')
        .sub("    fastlane (2.237.0)\n", "    addressable (2.9.1)\n    fastlane (2.237.0)\n")], 'unexpected_lock_source'],
      'manifest-alias' => [[direct_manifest.sub('"addressable"', '"Addressable"'), direct_lock], 'dependency_alias_forbidden'],
      'root-lock-alias' => [[direct_manifest, direct_lock.sub('  addressable (= 2.9.1)', '  Address-able (= 2.9.1)')],
                            'dependency_alias_forbidden'],
      'spec-alias' => [[manifest, lock.sub('    addressable (2.9.1)', '    address_able (2.9.1)')],
                       'dependency_alias_forbidden'],
      'edge-alias' => [[manifest, lock.sub('      addressable (>= 2.0.0, < 3.0.0)', '      address.able (>= 2.0.0, < 3.0.0)')],
                       'dependency_alias_forbidden']
    }
    negatives.each do |name, (inputs, diagnostic)|
      check_case(name, *inputs, surfaces, expected_hold: diagnostic)
    end
    ADDRESSABLE_BOUNDARIES.length + positive.length + negatives.length
  end

  def self.run
    count = 0
    Dir.mktmpdir('rubyzip-fastlane-guard-fixtures') do |directory|
      Dir.chdir(directory) do
        count += addressable_controls
        ['3.4.0', '3.4.1', '3.9.0'].each do |version|
          report = check_case(version, *fixture(version), ['ios/Gemfile', 'ios/Gemfile.lock'], accepted: true)
          unless report[:status] == 'PASS' && report[:rubyzip] == [version] &&
                 report[:fastlane_revision] == REVISION && report[:independent_advisories] == 4 &&
                 report[:advisory_records].length == 5 && report[:tracked_surfaces] == ['ios/Gemfile', 'ios/Gemfile.lock']
            raise "#{version}: incomplete accepted evidence"
          end
          count += 1
        end
        ['6.0.2', '7.0.5', '7.9.0'].each do |version|
          report = check_case("public_suffix_#{version}", *fixture('3.4.0', version),
                              ['ios/Gemfile', 'ios/Gemfile.lock'], accepted: true)
          raise "#{version}: incomplete selected suffix evidence" unless report[:status] == 'PASS'

          count += 1
        end
        ['7.0.5.pre', '8.0.0', 'nonsense'].each do |version|
          check_case("public_suffix_#{version}", *fixture('3.4.0', version),
                     ['ios/Gemfile', 'ios/Gemfile.lock'])
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
          public_suffix_constraint public_suffix_requirement_mismatch
          public_suffix_duplicate_manifest public_suffix_duplicate_spec
          public_suffix_duplicate_dependency public_suffix_source_mismatch
          jwt_floor json_floor excon_floor bundler_drift empty_platforms
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
            manifest, lock = manifest.gsub('"< 8"', '"< 9"'), lock.gsub('public_suffix (< 8)', 'public_suffix (< 9)')
          when 'public_suffix_requirement_mismatch'
            lock = lock.gsub('public_suffix (< 8)', 'public_suffix (< 9)')
          when 'public_suffix_duplicate_manifest'
            manifest += "gem \"public_suffix\", \"< 8\"\n"
          when 'public_suffix_duplicate_spec'
            lock = lock.gsub('    public_suffix (7.0.5)', "    public_suffix (7.0.5)\n    public_suffix (7.0.5)")
          when 'public_suffix_duplicate_dependency'
            lock = lock.gsub('  public_suffix (< 8)', "  public_suffix (< 8)\n  public_suffix (< 8)")
          when 'public_suffix_source_mismatch'
            lock = lock.gsub('  remote: https://rubygems.org/', '  remote: https://mirror.invalid/')
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
