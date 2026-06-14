#!/usr/bin/env python3
"""
Hermes Git Workflow Integration v1.0
=====================================
Automated Git workflow helpers for code review, commit messages, and change summaries.

Core features:
  1. PR Review auto-generation — analyzes git diff to produce structured review comments
  2. Commit message generation — conventional commits from staged/unstaged diffs
  3. Code change summary — summarizes what changed, why, and impact assessment

Usage:
  from scripts.git_workflow import GitWorkflow
  gw = GitWorkflow()
  summary = gw.summarize_changes()          # Summarize working tree changes
  review = gw.generate_pr_review()          # Generate PR review from diff
  msg = gw.generate_commit_message()        # Generate conventional commit message
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================================
# Data Types
# ============================================================================


@dataclass
class DiffFile:
    """Represents a single file's diff information."""

    path: str
    change_type: str  # 'added', 'modified', 'deleted', 'renamed'
    additions: int = 0
    deletions: int = 0
    language: str = ""
    hunks: List[Dict] = field(default_factory=list)


@dataclass 
class ChangeSummary:
    """Overall summary of changes in a diff."""

    total_files: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    files: List[DiffFile] = field(default_factory=list)
    summary: str = ""
    risk_level: str = "low"  # low, medium, high
    categories: List[str] = field(default_factory=list)


# ============================================================================
# Git Workflow Engine
# ============================================================================


class GitWorkflow:
    """Git workflow automation engine.

    Uses subprocess to interact with git, parses diff output,
    and generates human-readable summaries and commit messages.
    """

    def __init__(self, repo_path: Optional[str] = None):
        self._repo_path = Path(repo_path) if repo_path else Path.cwd()
        self._cached_diff: Optional[str] = None

    # ------------------------------------------------------------------
    # Low-level git operations
    # ------------------------------------------------------------------

    def _run_git(self, args: list, capture: bool = True) -> Tuple[int, str, str]:
        """Run a git command, return (returncode, stdout, stderr)."""
        cmd = ["git", "-C", str(self._repo_path)] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            return 1, "", "git not found"
        except subprocess.TimeoutExpired:
            return 1, "", "git command timed out"

    def _is_git_repo(self) -> bool:
        """Check if the path is a git repository."""
        rc, _, _ = self._run_git(["rev-parse", "--git-dir"])
        return rc == 0

    def _get_diff(
        self,
        staged: bool = False,
        target_branch: Optional[str] = None,
        paths: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Get git diff output.

        Args:
            staged: If True, diff staged changes. Otherwise working tree.
            target_branch: Compare against this branch (e.g. 'main').
            paths: Restrict diff to these file paths.
        """
        args = ["diff"]
        if staged:
            args.append("--staged")
        if target_branch:
            args.append(target_branch + "...")
        if paths:
            args.extend(["--"] + paths)

        rc, stdout, stderr = self._run_git(args)
        if rc != 0:
            logger.warning(f"git diff failed: {stderr}")
            return None
        return stdout

    # ------------------------------------------------------------------
    # Diff parsing
    # ------------------------------------------------------------------

    def _parse_diff(self, diff_text: str) -> List[DiffFile]:
        """Parse git unified diff output into structured DiffFile objects."""
        files: List[DiffFile] = []
        current_file: Optional[DiffFile] = None
        current_hunk: Optional[Dict] = None

        lines = diff_text.split("\n")

        for line in lines:
            # File header: diff --git a/path b/path
            if line.startswith("diff --git "):
                if current_file and current_hunk:
                    current_file.hunks.append(current_hunk)
                    current_hunk = None
                parts = line.split(" ")
                if len(parts) >= 4:
                    b_path = parts[3]
                    if b_path.startswith("b/"):
                        b_path = b_path[2:]
                    current_file = DiffFile(
                        path=b_path,
                        change_type="modified",
                    )
                    # Detect language from extension
                    ext = Path(b_path).suffix.lstrip(".")
                    current_file.language = ext if ext else ""
                    files.append(current_file)
                continue

            if current_file is None:
                continue

            # Change type
            if line.startswith("new file "):
                current_file.change_type = "added"
            elif line.startswith("deleted file "):
                current_file.change_type = "deleted"
            elif line.startswith("rename from "):
                current_file.change_type = "renamed"

            # Hunk header: @@ -a,b +c,d @@
            if line.startswith("@@ ") and line.endswith(" @@"):
                if current_hunk:
                    current_file.hunks.append(current_hunk)
                current_hunk = {
                    "header": line,
                    "context": "",
                    "additions": [],
                    "deletions": [],
                }
                continue

            # Count additions/deletions within hunks
            if line.startswith("+") and not line.startswith("+++"):
                current_file.additions += 1
                if current_hunk:
                    current_hunk["additions"].append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                current_file.deletions += 1
                if current_hunk:
                    current_hunk["deletions"].append(line[1:])

        # Append last hunk
        if current_file and current_hunk:
            current_file.hunks.append(current_hunk)

        return files

    # ------------------------------------------------------------------
    # Change Summary
    # ------------------------------------------------------------------

    def summarize_changes(
        self,
        staged: bool = False,
        target_branch: Optional[str] = None,
    ) -> ChangeSummary:
        """Summarize the current working tree or staged changes.

        Returns a ChangeSummary with file-level breakdown and risk assessment.
        """
        if not self._is_git_repo():
            return ChangeSummary(summary="Not a git repository")

        diff_text = self._get_diff(staged=staged, target_branch=target_branch)
        if diff_text is None or not diff_text.strip():
            return ChangeSummary(summary="No changes detected")

        parsed = self._parse_diff(diff_text)

        total_additions = sum(f.additions for f in parsed)
        total_deletions = sum(f.deletions for f in parsed)

        # Categorize changes
        categories = set()
        for f in parsed:
            ext = f.language.lower()
            if ext in ("py", "js", "ts", "go", "rs", "java", "cpp", "c", "rb"):
                categories.add("code")
            elif ext in ("json", "yaml", "yml", "toml", "xml", "ini", "cfg"):
                categories.add("config")
            elif ext in ("md", "rst", "txt"):
                categories.add("documentation")
            elif ext in ("sql", "db", "sqlite"):
                categories.add("database")
            elif ext in ("sh", "bash", "zsh", "ps1"):
                categories.add("script")
            elif ext in ("html", "css", "jsx", "tsx", "vue", "svelte"):
                categories.add("frontend")
            else:
                categories.add("other")

        # Risk assessment
        risk = "low"
        if total_additions + total_deletions > 500:
            risk = "high"
        elif total_additions + total_deletions > 200:
            risk = "medium"
        if any(f.change_type == "deleted" for f in parsed):
            risk = max(risk, "medium")
        if any(
            f.path.endswith((".py", ".js", ".go")) and f.additions > 100
            for f in parsed
        ):
            risk = "high"

        # Generate human-readable summary
        file_list = "\n".join(
            f"  [{f.change_type.upper():7s}] {f.path} (+{f.additions}/-{f.deletions})"
            for f in parsed
        )

        summary_lines = [
            f"Change Summary:",
            f"  Files changed: {len(parsed)}",
            f"  Total additions: +{total_additions}",
            f"  Total deletions: -{total_deletions}",
            f"  Categories: {', '.join(sorted(categories))}",
            f"  Risk level: {risk.upper()}",
            f"",
            f"Files:",
            file_list,
        ]

        return ChangeSummary(
            total_files=len(parsed),
            total_additions=total_additions,
            total_deletions=total_deletions,
            files=parsed,
            summary="\n".join(summary_lines),
            risk_level=risk,
            categories=sorted(categories),
        )

    # ------------------------------------------------------------------
    # Commit Message Generation (Conventional Commits)
    # ------------------------------------------------------------------

    def generate_commit_message(
        self, staged: bool = True, style: str = "conventional"
    ) -> str:
        """Generate a conventional commit message from staged changes.

        Args:
            staged: If True, use staged changes. Otherwise working tree.
            style: 'conventional' (default) for Conventional Commits format.

        Returns:
            A formatted commit message string.
        """
        if not self._is_git_repo():
            return "chore: update (not a git repo)"

        diff_text = self._get_diff(staged=staged)
        if diff_text is None or not diff_text.strip():
            return "chore: no changes detected"

        parsed = self._parse_diff(diff_text)

        if not parsed:
            return "chore: update files"

        # Determine the commit type based on file changes
        commit_type = self._infer_commit_type(parsed)
        scope = self._infer_scope(parsed)

        # Build subject line
        subject = self._build_subject(parsed, commit_type, scope)

        # Build body
        body_lines = []
        for f in parsed:
            body_lines.append(
                f"- {f.change_type} {f.path} (+{f.additions}/-{f.deletions})"
            )

        # Format as conventional commit
        if style == "conventional":
            lines = [subject, ""] + body_lines
            return "\n".join(lines)

        return subject

    def _infer_commit_type(self, files: List[DiffFile]) -> str:
        """Infer the conventional commit type from changed files."""
        types = set()
        for f in files:
            if f.change_type == "deleted":
                types.add("chore")
            elif f.path.startswith("test") or f.path.endswith("_test.py"):
                types.add("test")
            elif f.path.endswith(".md") or f.path.endswith(".rst"):
                types.add("docs")
            elif f.path.endswith((".cfg", ".ini", ".yaml", ".yml", ".json", ".toml")):
                types.add("config")
            elif f.change_type == "added":
                types.add("feat")
            else:
                # Look at hunk content for type hints
                for hunk in f.hunks:
                    combined = " ".join(hunk["additions"] + hunk["deletions"])
                    if re.search(r"\b(fix|bug|issue|error|crash|broken)\b", combined, re.I):
                        types.add("fix")
                    elif re.search(r"\b(refactor|clean|simplify|restructure)\b", combined, re.I):
                        types.add("refactor")

        if "feat" in types:
            return "feat"
        if "fix" in types:
            return "fix"
        if "docs" in types and len(types) == 1:
            return "docs"
        if "test" in types and len(types) == 1:
            return "test"
        if "refactor" in types:
            return "refactor"
        if "config" in types and len(types) == 1:
            return "chore"
        return "chore"

    def _infer_scope(self, files: List[DiffFile]) -> str:
        """Infer the scope from changed files (common parent directory)."""
        dirs = set()
        for f in files:
            parts = Path(f.path).parts
            if len(parts) > 1:
                dirs.add(parts[0])
            else:
                dirs.add(Path(f.path).stem)
        if len(dirs) == 1:
            return dirs.pop()
        return ""

    def _build_subject(
        self,
        files: List[DiffFile],
        commit_type: str,
        scope: str,
    ) -> str:
        """Build the commit subject line."""
        scope_part = f"({scope})" if scope else ""

        if len(files) == 1:
            f = files[0]
            verb = {
                "added": "add",
                "modified": "update",
                "deleted": "remove",
                "renamed": "rename",
            }.get(f.change_type, "update")
            return f"{commit_type}{scope_part}: {verb} {Path(f.path).name}"

        # Multiple files
        verbs = set()
        for f in files:
            verbs.add(
                {
                    "added": "add",
                    "modified": "update",
                    "deleted": "remove",
                    "renamed": "rename",
                }.get(f.change_type, "update")
            )

        if verbs == {"add"}:
            action = "add"
        elif verbs == {"remove", "deleted"}:
            action = "remove"
        else:
            action = "update"

        return f"{commit_type}{scope_part}: {action} {len(files)} files"

    # ------------------------------------------------------------------
    # PR Review Generation
    # ------------------------------------------------------------------

    def generate_pr_review(
        self,
        base_branch: str = "main",
        head_branch: Optional[str] = None,
    ) -> str:
        """Generate a PR review from the diff between two branches.

        Analyzes the diff and produces structured review comments covering:
        - Summary of changes
        - Risk assessment
        - Code quality observations
        - Suggestions for improvement

        Args:
            base_branch: The target branch (e.g., 'main', 'develop')
            head_branch: The source branch. If None, uses current branch.

        Returns:
            A formatted review string.
        """
        if not self._is_git_repo():
            return "## PR Review\n\n**Error:** Not a git repository.\n"

        # Get the current branch if head not specified
        if head_branch is None:
            rc, stdout, _ = self._run_git(["branch", "--show-current"])
            if rc == 0 and stdout.strip():
                head_branch = stdout.strip()
            else:
                return "## PR Review\n\n**Error:** Cannot determine current branch.\n"

        # Get diff between branches (compare head against base)
        rc, stdout, stderr = self._run_git(
            ["diff", f"{base_branch}...{head_branch}"]
        )
        diff_text = stdout if rc == 0 else None

        if diff_text is None:
            return f"## PR Review\n\n**Error:** Cannot diff {base_branch}...{head_branch}\n"

        if not diff_text.strip():
            return (
                f"## PR Review: {head_branch} → {base_branch}\n\n"
                f"**Status:** No changes detected.\n"
                f"Base: `{base_branch}` | Head: `{head_branch}`\n"
            )

        parsed = self._parse_diff(diff_text)
        total_add = sum(f.additions for f in parsed)
        total_del = sum(f.deletions for f in parsed)

        # ---- Build the review ----
        lines = [
            f"## PR Review: {head_branch} → {base_branch}",
            "",
            "### Summary",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Files changed | {len(parsed)} |",
            f"| Additions | +{total_add} |",
            f"| Deletions | -{total_del} |",
            f"| Net change | +{total_add - total_del} |",
            "",
            "### Changed Files",
        ]

        for f in parsed:
            lines.append(
                f"- `{f.path}` — "
                f"{f.change_type.upper()} "
                f"(+{f.additions}/-{f.deletions}) "
                f"{'[' + f.language + ']' if f.language else ''}"
            )

        # Risk assessment
        lines.append("")
        lines.append("### Risk Assessment")
        risk = "low"
        risk_reasons = []
        if total_add + total_del > 500:
            risk = "high"
            risk_reasons.append("Large change set (>500 lines)")
        elif total_add + total_del > 200:
            risk = "medium"
            risk_reasons.append("Moderate change set (>200 lines)")
        if any(f.change_type == "deleted" for f in parsed):
            risk_reasons.append("File deletions detected")
        if any(
            f.path.endswith((".py", ".js", ".ts", ".go")) and f.additions > 100
            for f in parsed
        ):
            risk = "high"
            risk_reasons.append("Large single-file changes in code files")

        lines.append(f"**Risk Level:** {risk.upper()}")
        if risk_reasons:
            for reason in risk_reasons:
                lines.append(f"- {reason}")
        else:
            lines.append("- No significant risk factors detected")

        # Code quality observations
        lines.append("")
        lines.append("### Observations")

        large_files = [f for f in parsed if f.additions > 200]
        if large_files:
            lines.append(
                f"- **Large files:** {', '.join(f'`{f.path}`' for f in large_files)} "
                f"have >200 additions. Consider splitting."
            )

        no_test = not any("test" in f.path.lower() for f in parsed)
        code_files = [
            f for f in parsed if f.language in ("py", "js", "ts", "go", "rs", "java")
        ]
        if no_test and code_files:
            lines.append("- **Missing tests:** No test files detected in this PR.")

        doc_files = [
            f for f in parsed if f.language in ("md", "rst", "txt")
        ]
        if not doc_files and total_add > 100:
            lines.append("- **Documentation:** Consider updating relevant docs.")

        # Suggestions
        lines.append("")
        lines.append("### Suggestions")

        suggestions = []
        if risk == "high":
            suggestions.append("Consider breaking this PR into smaller, focused changes.")
        if no_test and code_files:
            suggestions.append("Add unit/integration tests for the changed code paths.")
        if any(f.path.endswith(".py") for f in parsed):
            suggestions.append("Run linting (`ruff`/`black`) and type checking (`mypy`).")
        if any(f.path.endswith((".yaml", ".yml", ".json")) for f in parsed):
            suggestions.append("Validate config files for syntax correctness.")

        if suggestions:
            for i, s in enumerate(suggestions, 1):
                lines.append(f"{i}. {s}")
        else:
            lines.append("No specific suggestions at this time.")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Changelog generation
    # ------------------------------------------------------------------

    def generate_changelog(
        self, from_ref: str = "HEAD~10", to_ref: str = "HEAD"
    ) -> str:
        """Generate a changelog from git log between two refs."""
        if not self._is_git_repo():
            return "Not a git repository"

        rc, stdout, _ = self._run_git(
            [
                "log",
                "--oneline",
                "--no-decorate",
                f"{from_ref}..{to_ref}",
            ]
        )
        if rc != 0 or not stdout.strip():
            return f"No commits between {from_ref} and {to_ref}"

        commits = stdout.strip().split("\n")
        lines = [f"## Changelog: {from_ref} → {to_ref}", ""]
        for commit in commits:
            lines.append(f"- {commit}")

        return "\n".join(lines)


# ============================================================================
# Standalone execution
# ============================================================================

if __name__ == "__main__":
    import sys

    gw = GitWorkflow()

    if not gw._is_git_repo():
        print("Not a git repository.")
        sys.exit(1)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
    else:
        cmd = "summary"

    if cmd == "summary":
        summary = gw.summarize_changes()
        print(summary.summary)
    elif cmd == "commit":
        msg = gw.generate_commit_message()
        print(msg)
    elif cmd == "review":
        base = sys.argv[2] if len(sys.argv) > 2 else "main"
        review = gw.generate_pr_review(base_branch=base)
        print(review)
    elif cmd == "changelog":
        from_ref = sys.argv[2] if len(sys.argv) > 2 else "HEAD~10"
        to_ref = sys.argv[3] if len(sys.argv) > 3 else "HEAD"
        print(gw.generate_changelog(from_ref, to_ref))
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: git_workflow.py [summary|commit|review|changelog]")
