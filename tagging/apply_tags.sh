#!/usr/bin/env bash
# Applies category + status topics from repo-tags.csv to your GitHub repos.
#   status:   Completed / In progress / Need(s) improvement (any case; blank = leave unchanged)
#   category: e.g. cat-ml-project or "ML Project"           (blank = leave unchanged)
# Usage: bash tagging/apply_tags.sh [--dry-run]
set -uo pipefail
OWNER="${OWNER:-gkrishna4346}"
CSV="$(dirname "$0")/repo-tags.csv"
DRY=""; [[ "${1:-}" == "--dry-run" ]] && DRY=1
slug() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/^[[:space:]]+|[[:space:]]+$//g; s/[[:space:]_]+/-/g'; }
perl -pe 's/\r\n?/\n/g; s/^\x{EF}\x{BB}\x{BF}//' "$CSV" | tail -n +2 | while IFS=, read -r repo category status _; do
  repo=$(printf '%s' "$repo" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
  [[ -z "$repo" ]] && continue
  s=$(slug "$status")
  case "$s" in
    "") ;;
    completed|complete|done|finished) s="completed" ;;
    in-progress|inprogress|progress|wip|ongoing|work-in-progress) s="in-progress" ;;
    needs-improvement|need-improvement|needs-improvements|need-improvements|improvement|improve|todo|incomplete) s="needs-improvement" ;;
    *) echo "!! $repo: unknown status '$status' (skipped)"; continue ;;
  esac
  c=$(slug "$category"); [[ -n "$c" && $c != cat-* ]] && c="cat-$c"
  args=()
  current=$(gh repo view "$OWNER/$repo" --json repositoryTopics -q '.repositoryTopics[]?.name' 2>/dev/null < /dev/null || true)
  if [[ -n "$s" ]]; then
    for t in $current; do [[ $t == status-* && $t != "status-$s" ]] && args+=(--remove-topic "$t"); done
    [[ " $current " == *" status-$s "* ]] || args+=(--add-topic "status-$s")
  fi
  if [[ -n "$c" ]]; then
    for t in $current; do [[ $t == cat-* && $t != "$c" ]] && args+=(--remove-topic "$t"); done
    [[ " $current " == *" $c "* ]] || args+=(--add-topic "$c")
  fi
  if [[ ${#args[@]} -eq 0 ]]; then echo "   $repo: already up to date"; continue; fi
  echo "-> $repo ${args[*]}"
  [[ -z "$DRY" ]] && { gh repo edit "$OWNER/$repo" "${args[@]}" >/dev/null < /dev/null || echo "!! $repo: update failed"; }
done
echo "Done. Now run the 'Update repo tracker' workflow (Actions tab) to refresh the dashboard."
