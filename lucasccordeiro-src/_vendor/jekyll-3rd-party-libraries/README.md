# jekyll-3rd-party-libraries (local fork)

Unmodified copy of [jekyll-3rd-party-libraries](https://github.com/george-gca/jekyll-3rd-party-libraries)
0.0.1 by George Corrêa de Araújo (MIT), carrying one change: the gemspec's
`css_parser` requirement is widened from `< 2.0` to `< 4.0`.

`lib/` is byte-for-byte upstream.

## Why

`al_img_tools` depends on this gem, and upstream's `css_parser < 2.0` pin held
the site on css_parser 1.x, which is vulnerable to
[GHSA-9pmc-p236-855h](https://github.com/advisories/GHSA-9pmc-p236-855h)
(SSRF and local file disclosure via `@import`). 0.0.1 is the only release ever
published, so there was no upstream version to move to, and the pin is
transitive — dropping the direct `Gemfile` entry does not lift it.

Bundler resolves a `:path` source against this gemspec instead of the published
one, which satisfies `al_img_tools`' `~> 0.0.1` requirement while letting
css_parser reach the patched 3.0.0.

Retire this directory once upstream relaxes the pin.
