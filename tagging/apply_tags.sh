#!/usr/bin/env bash
# Applies category + status topics from repo-tags.csv to your GitHub repos.
#   status column: completed | in-progress | needs-improvement   (blank = leave status untouched)
#   category column: any cat-* topic                            (blank = leave category untouched)
# Needs the GitHub CLI:  brew install gh  &&  gh auth login
# Usage:  bash tagging/apply_tags.sh            (from the repo-tracker folder)
#         bash tagging/apply_tags.sh --dry-run  (show what would change)
set -euo pipefail
OWNER="${OWNER:-gkrishna4346}"
CSV="$(dirname "$0")/repo-tags.csv"
DRY=""; [[ "${1:-}" == "--dry-run" ]] && DRY=1

tail -n +2 "$CSV" | tr -d '\r' | while IFS=, read -r repo category status; do
  [[ -z "$repo" ]] && continue
  args=()
  current=$(gh repo view "$OWNER/$repo" --json repositoryTopics -q '.repositoryTopics[]?.name' 2>/dev/null < /dev/null || true)

  if [[ -n "$status" ]]; then
    case "$status" in completed|in-progress|needs-improvement) ;; *) echo "!! $repo: unknown status '$status' (skipped)"; continue;; esac
    for t in $current; do [[ $t == status-* && $t != "status-$status" ]] && args+=(--remove-topic "$t"); done
    args+=(--add-topic "status-$status")
  fi
  if [[ -n "$category" ]]; then
    [[ $category != cat-* ]] && category="cat-$category"
    for t in $current; do [[ $t == cat-* && $t != "$category" ]] && args+=(--remove-topic "$t"); done
    args+=(--add-topic "$category")
  fi
  [[ ${#args[@]} -eq 0 ]] && continue

  echo "-> $repo ${args[*]}"
  [[ -z "$DRY" ]] && gh repo edit "$OWNER/$repo" "${args[@]}" >/dev/null < /dev/null
done
echo "Done. Run the 'Update repo tracker' workflow (Actions tab) to refresh the dashboard."
