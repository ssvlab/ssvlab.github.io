require_relative 'lib/jekyll-3rd-party-libraries/version'

Gem::Specification.new do |spec|
  spec.name          = 'jekyll-3rd-party-libraries'
  spec.version       = Jekyll::ThirdPartyLibraries::VERSION
  spec.authors       = ['George Corrêa de Araújo']
  spec.summary       = 'Force updating cached files and resources in a Jekyll site.'
  spec.description   = 'Force updating cached files and resources in a Jekyll site by adding a hash.'
  spec.homepage      = 'https://github.com/george-gca/jekyll-3rd-party-libraries'
  spec.license       = 'MIT'
  spec.required_ruby_version = '>= 2.3.0'

  spec.files         = Dir['lib/**/*.rb'] + ['LICENSE', 'README.md']
  spec.require_paths = ['lib']

  spec.add_runtime_dependency 'jekyll', '>= 3.6', '< 5.0'
  # Upstream pins '< 2.0', which strands css_parser on a release vulnerable to
  # GHSA-9pmc-p236-855h. The four APIs lib/ uses -- Parser.new, load_string!,
  # each_rule_set and RuleSet#[]/#[]= -- are unchanged in 3.x.
  spec.add_runtime_dependency 'css_parser', '>= 1.6', '< 4.0'
  spec.add_runtime_dependency 'nokogiri', '>= 1.8', '< 2.0'
end
