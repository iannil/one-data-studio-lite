# Memory System for Smart Data Platform

This directory contains transparent memory storage for AI agents working on this project.

## Structure

### Daily Memory (`memory/daily/`)
- **Format**: `{YYYY-MM-DD}.md`
- **Purpose**: Stream of daily activities, decisions, and progress
- **Usage**: Appended to throughout the day, never modified retroactively

### Long-term Memory (`MEMORY.md`)
- **Format**: Structured Markdown with categorized sections
- **Purpose**: Consolidated knowledge that persists across sessions
- **Usage**: Updated when meaningful patterns emerge

## Reading Memory

When starting a session:
1. Read `MEMORY.md` to get long-term context
2. Read today's daily log (if exists) to get recent context

## Writing Memory

During a session:
1. Always create today's daily log if it doesn't exist
2. Append every significant action/decision to the daily log
3. Update `MEMORY.md` when:
   - User preferences are discovered
   - Important architectural decisions are made
   - Error fixes are identified
   - New patterns emerge

## Template for Daily Log

```markdown
# {YYYY-MM-DD}

## Session Start
- Time: {HH:MM}
- Context: {What we're working on}

## Progress
- [ ] Task 1
- [ ] Task 2

## Issues Encountered
- Issue description → Solution

## Next Steps
- What to work on next
```

## Template for MEMORY.md

```markdown
# Smart Data Platform - Long-Term Memory

## User Preferences
- [Preferences learned from interactions]

## Project Context
- [Key architectural decisions]
- [Important patterns]

## Common Issues & Solutions
- Issue → Solution pattern

## Development Standards
- [Coding standards]
- [Testing requirements]
```
