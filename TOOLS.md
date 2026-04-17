---

## Edit Tool Checklist

Before calling `edit`, verify all 3 parameters:
- [ ] `file_path` — which file
- [ ] `old_string` — exact text to find
- [ ] `new_string` — what to replace with

**Common mistake:** Forgetting `new_string` when focused on the code. Double-check before executing.

---

## GitHub Pages Garden Access

**Site:** https://sshadowfaxx-tech.github.io/frierens-garden/
**Repository:** https://github.com/sshadowfaxx-tech/frierens-garden
**Token:** Available in git remote (GITHUB_TOKEN env)
**Use:** Push garden files to GitHub, auto-deploys to GitHub Pages

**Workflow:**
1. Edit/create files in `/root/.openclaw/workspace/garden/`
2. `git add <files>`
3. `git commit -m "message"`
4. `git push origin master`
5. Site updates automatically

---

Add whatever helps you do your job. This is your cheat sheet.
