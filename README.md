# Repo Tracker

Automatically tracks every public repository on this GitHub account and shows whether each one is **completed**, **in progress**, or **needs improvement**.

- 📊 **Dashboard:** `https://<your-username>.github.io/<this-repo-name>/`
- 🔄 **Refresh:** daily via GitHub Actions (or manually from the Actions tab)
- 🗄️ Archived repos are excluded

## How to set a repo's status

On each repo's GitHub page, click ⚙️ next to **About**, then add **one** of these topics:

| Topic | Meaning |
|---|---|
| `status-completed` | ✅ Finished |
| `status-in-progress` | 🚧 Still being built |
| `status-needs-improvement` | 🛠️ Works but needs fixes or improvements |

Repos without a status topic appear as ❔ **Not tagged**.

The tracker also adds automatic **health warnings**: no README, no description, no license, or no commits in 180+ days.

## Current status

<!-- TRACKER:START -->
_The table appears here after the first workflow run._
<!-- TRACKER:END -->
