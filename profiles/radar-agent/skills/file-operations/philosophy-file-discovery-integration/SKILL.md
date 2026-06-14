---
name: philosophy-file-discovery-integration
description: Systematic search for and integration of project philosophical documents (SOUL.md, ETHOS.md, etc.) from multiple sources
version: 1.0.0
metadata:
  hermes:
    tags: [file-search, integration, philosophy, configuration, investigation]
    related_skills: [github-repo-management, systematic-debugging]
---

# Philosophy File Discovery and Integration

**Purpose**: Systematic search for and integration of a project's philosophical/configuration documents (SOUL.md, ETHOS.md, PRINCIPLES.md, etc.) across multiple sources.

**When to Use**: When asked to "read X's soul.md and merge content" or similar requests to find and incorporate a project's foundational philosophy files.

---

## Methodology

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


### 1. Initial Assessment
- Check if file exists in current working directory or known locations
- Determine the project name and known repositories
- Identify common filename variants: SOUL.md, PHILOSOPHY.md, ETHOS.md, PRINCIPLES.md, VISION.md, MISSION.md, VALUES.md, MANIFESTO.md

### 2. Multi-Source Search Strategy

#### A. Local Filesystem Search
```python
import os
def find_philosophy_files(root_dir):
    results = []
    common_names = ['soul', 'philosophy', 'ethos', 'principles', 'vision', 'mission', 'values', 'manifesto']
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', '.venv']]
        for f in files:
            fname_lower = f.lower()
            if any(keyword in fname_lower for keyword in common_names):
                results.append(os.path.join(root, f))
    return results
```

#### B. GitHub Raw Content Access
Attempt direct fetch of common paths:
```
https://raw.githubusercontent.com/{owner}/{repo}/main/SOUL.md
https://raw.githubusercontent.com/{owner}/{repo}/main/docs/PHILOSOPHY.md
https://raw.githubusercontent.com/{owner}/{repo}/main/docs/VISION.md
```

#### C. Browser Navigation & Scraping
When direct access fails, navigate to GitHub repo and:
- Explore the file tree for docs/ directory
- Use browser_console to extract document content
- Check for files like README.md for embedded philosophy

#### D. Fallback Cloning
If necessary and time permits, shallow clone the target repo:
```bash
git clone --depth=1 https://github.com/owner/repo.git /tmp/repo_temp
find /tmp/repo_temp -type f -iname "*soul*" -o -iname "*philosophy*"
```

### 3. Handling Missing Files

When the expected philosophy file doesn't exist:

1. **Document the search**: Keep a log of all attempted locations and methods
2. **Analyze why**: Could be that:
   - The file uses a different naming convention
   - Philosophy is embedded in README or other docs
   - The project doesn't have an explicit philosophy document
   - The file exists in a branch or fork, not main
3. **Communicate clearly to user**:
   - What was searched
   - What was found (if anything)
   - Why the file might be missing
   - Request clarification or alternative approach

### 4. Content Integration

When a philosophy file IS found:

1. **Read and analyze** the content
2. **Merge with existing SOUL.md** (or create new one):
   - Preserve existing core principles
   - Integrate new philosophies that complement or expand current ones
   - Resolve conflicts by prioritizing user-provided directives
   - Maintain no-simplification mandate
3. **Update persistent memory** with key principles
4. **Document the integration** in session notes

### 5. Verification & Persistence

- After integration, verify consistency
- Save updated SOUL.md to disk
- Update memory with core principles (keep within 2200 char limit)
- If the philosophy changes operating principles significantly, notify user

---

## Common Pitfalls

- **Rate limiting**: GitHub API calls may be blocked; use raw.githubusercontent.com when possible
- **Branch assumptions**: Philosophy files may exist in non-main branches
- **Naming variations**: Projects may use unconventional filenames (e.g., .claw/config, .agents/identity.md)
- **Embedded content**: Philosophy might be in code comments, not a standalone file
- **Docker bias**: Many modern projects document philosophy in Docker-related files; avoid Docker per mandate

---

## Success Criteria

- File located and content extracted OR clear determination that it doesn't exist in expected form
- User's request fulfilled: content merged or user informed with actionable next steps
- System's core principles updated appropriately
- All operations performed without Docker
- Complete documentation of the investigative process

---

## Related Skills

- `github-repo-management`: For cloning and repo inspection
- `systematic-debugging`: For investigative approach methodology
- `file-operations`: Basic read/write/search patterns
## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
