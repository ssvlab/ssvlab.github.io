#!/usr/bin/env bash
# Local stand-in for the build workflow, for while GitHub Actions is unavailable.
# Builds the site and writes it into ../$PUBLISH_PATH/ ready to commit.
#
# The published folder also holds ~634 MB of PDFs that this build does not
# produce. They are excluded so rsync neither transfers nor deletes them: with
# --exclude, and without --delete-excluded, rsync treats them as protected.
set -euo pipefail

cd "$(dirname "$0")"
PUBLISH_PATH="${1:-lucasccordeiro}"

# Five of these are also page permalinks on the new site, so the directory
# cannot simply be skipped: let the generated index.html through and protect
# everything else in there. Rules are evaluated in order, so include first.
KEEP=(papers talks supervisions awards cv courses vss files)
EXCLUDES=()
for dir in "${KEEP[@]}"; do
  EXCLUDES+=(--include "/$dir/" --include "/$dir/index.html" --exclude "/$dir/**")
done

bundle exec jekyll build --baseurl "/$PUBLISH_PATH"

links=$(grep -c 'lucasccordeiro/papers/' _site/publications/index.html)
echo "paper links rendered: $links"
[ "$links" -ge 150 ] || { echo "refusing to publish: publication list looks truncated" >&2; exit 1; }

echo
echo "--- dry run: files this sync would delete from ../$PUBLISH_PATH ---"
plan=$(rsync -a --delete --dry-run --itemize-changes "${EXCLUDES[@]}" _site/ "../$PUBLISH_PATH/")
echo "$plan" | grep -E "^\*deleting" | head -20 || echo "(none)"

for dir in "${KEEP[@]}"; do
  if echo "$plan" | grep -qE "^\*deleting $dir/"; then
    echo "refusing to publish: the sync would delete files under $dir/" >&2
    exit 1
  fi
done

rsync -a --delete "${EXCLUDES[@]}" _site/ "../$PUBLISH_PATH/"
echo "written to ../$PUBLISH_PATH -- review, then commit"
