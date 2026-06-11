# Devpost submission checklist

**Deadline: 2026-06-11 2:00 PM PDT. Start submitting by 12:45 PM regardless of feature state.**

## Checklist

- [ ] README complete (what/why, architecture diagram, setup, screenshots)
- [ ] Public GitHub repo, MIT license
- [ ] Hosted URL live (Cloud Run `/healthz` or landing route)
- [ ] ~3 min demo video uploaded (YouTube unlisted OK)
- [ ] Devpost form: hosted URL, repo URL, video, **MongoDB partner bucket** selected
- [ ] Write-up hits judging criteria: Technological Implementation, Design/UX, Potential Impact, Quality of Idea

## Demo video script (~3 min)

1. **The problem** (20s) — AI video is flooding feeds; existing detectors need manual checks.
2. **Live detection** (60s) — browse YouTube: AI-generated video gets 🤖 badge, real video gets ✅, popup shows Gemini's reasons.
3. **The MongoDB moment** (30s) — revisit the same video: instant cached verdict via MongoDB MCP Server `find` against Atlas. Linger here.
4. **Architecture** (45s) — Chrome MV3 extension → Cloud Run → Google ADK agent → Gemini (frame forensics) + MongoDB MCP Server (cache) → Atlas.
5. **Impact** (15s) — passive media literacy for everyone; SynthID Content Detection API as the upgrade path.
