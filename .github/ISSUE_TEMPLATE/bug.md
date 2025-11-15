---
name: 🐛 Bug
about: Report an issue
title: '[BUG]: UPDATE BUG TITLE'
labels: "bug,needs-triage"
assignees: ''

---

Use this form to submit a reproducible bug.

**What is your issue?**

**Do you have a solution in mind?**

**Logs:**

Ensure you setup debug logging, before reporting issues! Instructions for your home assistant configuration:

```yaml
logger:
  default: warning
  logs:
    custom_components.xcomfort_bridge: debug
    xcomfort: debug 
```

Paste you logs below:

```log
<paste logs here>
```
