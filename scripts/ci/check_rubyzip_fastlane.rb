# frozen_string_literal: true

gem 'bundler', '= 2.4.22'
require 'bundler'
require 'json'
require 'open3'
require 'ripper'

# Offline contract check only: no Gemfile evaluation, resolution, installation or network access.
module RubyzipFastlaneGuard
  class Hold < StandardError; end

  SURFACES = ['ios/Gemfile', 'ios/Gemfile.lock'].freeze
  FORK = 'https://github.com/Katsiarynakavaleuskaya/fastlane.git'
  REVISION = '1ac01395d37bf7e6b88b3d0bcba5f84af841fcbc'
  FASTLANE_VERSION = Gem::Version.new('2.237.0')
  RUBYZIP_RANGE = Gem::Requirement.new('>= 3.4.0', '< 4.0.0')
  # RubySec e7179ad21701894b75796c5ddd72e5fbfc446165; the withdrawn GHSA is a duplicate record.
  FIXED_FLOORS = {
    'CVE-2017-5946' => '1.2.1', 'CVE-2018-1000544' => '1.2.2',
    'CVE-2019-16892' => '1.3.0', 'CVE-2026-85396' => '3.4.0',
    'GHSA-3q5q-f79q-7hr2-withdrawn-duplicate-of-CVE-2017-5946' => '1.2.1'
  }.freeze
  RETAINED_REQUIREMENTS = {
    'CFPropertyList' => '= 3.0.8', 'public_suffix' => '< 7',
    'jwt' => '>= 3.2.0', 'json' => '>= 2.19.9', 'excon' => '>= 1.5.0'
  }.freeze
  MAX_BYTES = 2 * 1024 * 1024

  def self.require!(condition, code)
    raise Hold, code unless condition
  end

  def self.literal(node)
    require!(node.is_a?(Array) && node[0] == :string_literal, 'nonliteral_manifest')
    content = node[1]
    require!(content.is_a?(Array) && content.length == 2 && content[0] == :string_content,
             'nonliteral_manifest')
    token = content[1]
    require!(token.is_a?(Array) && token[0] == :@tstring_content && token[1].is_a?(String),
             'nonliteral_manifest')
    value = token[1]
    require!(!value.empty? && !value.match?(/[\\\x00-\x1f\x7f]/), 'escaped_or_unsafe_manifest')
    value
  end

  def self.manifest(text)
    tree = Ripper.sexp(text)
    require!(tree.is_a?(Array) && tree[0] == :program && tree[1].is_a?(Array), 'invalid_manifest')
    gems, sources = {}, []
    tree[1].each do |call|
      require!(call[0] == :command && call[1][0] == :@ident &&
               ['source', 'gem'].include?(call[1][1]) && call[2][0] == :args_add_block &&
               call[2][2] == false, 'unsupported_manifest_statement')
      args = call[2][1].dup
      options = {}
      if args.last && args.last[0] == :bare_assoc_hash
        args.pop[1].each do |pair|
          require!(pair[0] == :assoc_new && pair[1][0] == :@label, 'invalid_manifest_option')
          key = pair[1][1].delete_suffix(':')
          require!(['git', 'ref'].include?(key) && !options.key?(key), 'invalid_manifest_option')
          options[key] = literal(pair[2])
        end
      end
      values = args.map { |node| literal(node) }
      if call[1][1] == 'source'
        require!(values == ['https://rubygems.org'] && options.empty?, 'manifest_source_invalid')
        sources << values.first
      else
        name = values.shift
        require!(name && name.match?(/\A[A-Za-z0-9_.-]+\z/) && !gems.key?(name) && !values.empty?,
                 'missing_or_duplicate_manifest_dependency')
        require!(options.empty? || name == 'fastlane', 'unexpected_dependency_source')
        gems[name] = [Gem::Requirement.new(*values), options]
      end
    end
    require!(sources.length == 1, 'manifest_source_invalid')
    gems
  end

  def self.lock_envelope(text)
    sections, counts, options = [], Hash.new(0), []
    section = nil
    specs_started = false
    text.each_line.map(&:chomp).reject(&:empty?).each do |line|
      if !line.start_with?(' ')
        require!(['GIT', 'GEM', 'DEPENDENCIES', 'PLATFORMS', 'BUNDLED WITH'].include?(line),
                 'unsupported_lock_section')
        section = line
        sections << section
        specs_started = false
      elsif ['GIT', 'GEM'].include?(section) && !specs_started
        if line == Bundler::LockfileParser::SPECS
          specs_started = true
        else
          match = Bundler::LockfileParser::OPTIONS.match(line)
          require!(match && (section == 'GIT' ? ['remote', 'revision', 'ref'] : ['remote']).include?(match[1]),
                   'invalid_lock_source_option')
          require!(!options.include?([section, match[1]]), 'duplicate_lock_source_option')
          options << [section, match[1]]
        end
      elsif ['GIT', 'GEM', 'DEPENDENCIES'].include?(section)
        match = Bundler::LockfileParser::NAME_VERSION.match(line)
        allowed_indent = section == 'DEPENDENCIES' ? [2] : [4, 6]
        require!(match && allowed_indent.include?(match[1].size) && match[2].match?(/\A[A-Za-z0-9_.-]+\z/),
                 'invalid_lock_dependency_row')
        counts[match[1].size] += 1
      elsif section == 'PLATFORMS'
        require!(line.match?(/\A  \S+\z/), 'invalid_lock_platform')
      elsif section == 'BUNDLED WITH'
        require!(line.match?(/\A   \S+\z/) && Gem::Version.correct?(line.strip), 'invalid_bundler_version')
        counts[:bundler] += 1
      else
        raise Hold, 'invalid_lock_row'
      end
    end
    require!(sections == ['GIT', 'GEM', 'PLATFORMS', 'DEPENDENCIES', 'BUNDLED WITH'] &&
             counts[:bundler] == 1, 'missing_or_duplicate_lock_section')
    counts
  end

  def self.check(manifest_text, lock_text, tracked_paths)
    surfaces = tracked_paths.select do |path|
      File.basename(path).match?(/\A(?:\.?gemfile(?:\..*)?|gems\.rb|gems\.locked|.*\.gemspec)\z/i)
    end
    require!(surfaces.sort == SURFACES, 'unreconciled_ruby_surfaces')
    [manifest_text, lock_text].each do |text|
      require!(text.is_a?(String) && text.bytesize <= MAX_BYTES && text.valid_encoding? &&
               !text.include?("\x00"), 'invalid_dependency_bytes')
    end
    declared = manifest(manifest_text)
    counts = lock_envelope(lock_text)
    lock = Bundler::LockfileParser.new(lock_text)
    require!(counts[4] == lock.specs.length && counts[6] == lock.specs.sum { |spec| spec.dependencies.length } &&
             counts[2] == lock.dependencies.length, 'missing_or_duplicate_lock_dependency')
    require!(lock.bundler_version == Gem::Version.new('2.4.22'), 'bundler_lock_version_drift')
    require!(!lock.platforms.empty? && lock.platforms.uniq.length == lock.platforms.length &&
             lock.platforms.none? { |platform| platform.to_s == 'unknown' } &&
             lock.specs.all? { |spec| spec.platform == Gem::Platform::RUBY || lock.platforms.include?(spec.platform) },
             'unreconciled_lock_platform')
    names = declared.keys + lock.specs.map(&:name) + lock.dependencies.keys + lock.specs.flat_map { |spec| spec.dependencies.map(&:name) }
    names.each do |name|
      canonical = { 'rubyzip' => 'rubyzip', 'fastlane' => 'fastlane', 'cfpropertylist' => 'CFPropertyList',
                    'publicsuffix' => 'public_suffix', 'jwt' => 'jwt', 'json' => 'json', 'excon' => 'excon' }[name.downcase.delete('_.-')]
      require!(canonical.nil? || name == canonical, 'dependency_alias_forbidden')
    end
    require!(declared.keys.sort == lock.dependencies.keys.sort &&
             ['rubyzip', 'fastlane', 'CFPropertyList', 'public_suffix'].all? { |name| declared.key?(name) },
             'manifest_lock_dependency_mismatch')
    declared.each do |name, (requirement, _options)|
      require!(requirement == lock.dependencies.fetch(name).requirement, 'manifest_lock_requirement_mismatch')
    end
    ['CFPropertyList', 'public_suffix'].each do |name|
      require!(declared[name].first == Gem::Requirement.new(RETAINED_REQUIREMENTS.fetch(name)),
               'retained_manifest_requirement_drift')
    end
    specs = lock.specs.group_by(&:name)
    require!(specs.fetch('fastlane', []).length == 1 && specs['fastlane'].first.version == FASTLANE_VERSION,
             'fastlane_version_invalid')
    require!(declared['fastlane'] == [Gem::Requirement.new('= 2.237.0'), { 'git' => FORK, 'ref' => REVISION }],
             'fastlane_manifest_source_invalid')
    fastlane = specs['fastlane'].first
    source = fastlane.source
    require!(source.is_a?(Bundler::Source::Git) && source.uri == FORK && source.options['uri'] == FORK && source.ref == REVISION &&
             source.options['revision'] == REVISION && lock.dependencies['fastlane'].source == source,
             'fastlane_lock_source_invalid')
    require!(lock.sources.length == 2 && lock.sources.count { |item| item.is_a?(Bundler::Source::Git) } == 1,
             'unexpected_lock_source')
    registry = lock.sources.find { |item| item.is_a?(Bundler::Source::Rubygems) }
    require!(registry && registry.remotes.map(&:to_s) == ['https://rubygems.org/'] &&
             lock.specs.all? { |spec| spec.name == 'fastlane' || spec.source == registry },
             'unexpected_lock_source')
    required_zip = fastlane.dependencies.select { |dependency| dependency.name == 'rubyzip' }
    require!(required_zip.length == 1 && required_zip.first.requirement == RUBYZIP_RANGE,
             'fastlane_rubyzip_compatibility_missing')
    zip_specs = specs.fetch('rubyzip', [])
    require!(!zip_specs.empty?, 'rubyzip_missing')
    require!(zip_specs.all? { |spec| declared['rubyzip'].first.requirements == [['=', spec.version]] },
             'rubyzip_exact_target_required')
    zip_specs.each do |spec|
      require!(!spec.version.prerelease? && RUBYZIP_RANGE.satisfied_by?(spec.version), 'rubyzip_incompatible')
      FIXED_FLOORS.each_value do |floor|
        require!(Gem::Requirement.new(">= #{floor}").satisfied_by?(spec.version), 'rubyzip_advisory_postcondition_failed')
      end
    end
    RETAINED_REQUIREMENTS.each do |name, requirement|
      selected = specs.fetch(name, [])
      require!(!selected.empty? && selected.all? { |spec| !spec.version.prerelease? && Gem::Requirement.new(requirement).satisfied_by?(spec.version) },
               'retained_dependency_floor_failed')
    end
    (lock.dependencies.values + lock.specs.flat_map(&:dependencies)).each do |dependency|
      versions = dependency.name == 'bundler' ? [lock.bundler_version] : specs.fetch(dependency.name, []).map(&:version)
      require!(!versions.empty? && versions.all? { |version| dependency.requirement.satisfied_by?(version) },
               'incompatible_lock_dependency')
    end
    require!(lock.specs.all? { |spec| spec.dependencies.map(&:name).uniq.length == spec.dependencies.length },
             'duplicate_transitive_dependency')
    { status: 'PASS', rubyzip: zip_specs.map { |spec| spec.version.to_s }, fastlane_revision: REVISION,
      advisory_records: FIXED_FLOORS.keys, independent_advisories: 4, tracked_surfaces: surfaces.sort }
  end

  def self.main
    require!(ARGV.empty?, 'unexpected_arguments')
    root = File.expand_path('../..', __dir__)
    git = Bundler.which('git')
    require!(!git.nil?, 'git_unavailable')
    paths, _error, status = Open3.capture3({ 'GIT_OPTIONAL_LOCKS' => '0' }, File.realpath(git),
                                         '-C', root, 'ls-files', '-z')
    require!(status.success?, 'tracked_inventory_failed')
    files = SURFACES.map do |relative|
      path = File.join(root, relative)
      metadata = File.lstat(path)
      require!(metadata.file? && metadata.nlink == 1 && metadata.size <= MAX_BYTES, 'unsafe_dependency_file')
      File.read(path, encoding: 'UTF-8')
    end
    result = Dir.chdir(File.join(root, 'ios')) { check(*files, paths.split("\x00")) }
    puts(JSON.generate(result))
  rescue Hold => error
    warn("HOLD:#{error.message}")
    exit(1)
  rescue StandardError => error
    warn("HOLD:ruby_dependency_parse_failed:#{error.class}")
    exit(1)
  end
end

RubyzipFastlaneGuard.main if $PROGRAM_NAME == __FILE__
