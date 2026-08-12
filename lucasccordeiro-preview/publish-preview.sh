#!/usr/bin/env bash
# Local stand-in for the build workflow, for while GitHub Actions is unavailable.
# Builds the site and writes it into ../lucasccordeiro-preview/ ready to commit.
set -euo pipefail

cd "$(dirname "$0")"
PUBLISH_PATH="${1:-lucasccordeiro-preview}"

bundle exec jekyll build --baseurl "/$PUBLISH_PATH"

links=$(grep -c 'lucasccordeiro/papers/' _site/publications/index.html)
echo "paper links rendered: $links"
[ "$links" -ge 150 ] || { echo "refusing to publish: publication list looks truncated" >&2; exit 1; }

rsync -a --delete _site/ "../$PUBLISH_PATH/"
echo "written to ../$PUBLISH_PATH -- review, then commit"
