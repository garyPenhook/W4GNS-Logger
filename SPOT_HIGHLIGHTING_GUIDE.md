# RBN Spot Award-Based Highlighting Guide

## Overview

The W4GNS Logger now features intelligent RBN spot highlighting that helps you focus on contacts that matter for your specific awards. Rather than treating all spotted stations equally, the logger analyzes each spot against:

- Your current award progress (e.g., "need 2 more for Centurion")
- Your contact history (already worked?)
- Your award prerequisites (Tribune requires Centurion first)
- Time since last contact (worked today? vs worked 1 year ago?)

## Feature Highlights

### 1. **Award-Based Spot Classification**

Each RBN spot is automatically classified as:

| Classification | Meaning | Example |
|---|---|---|
| **CRITICAL** | Nearly qualified for award (5 or fewer contacts needed) | Red highlight: "Need 2 more contacts for Centurion" |
| **HIGH** | Important for near-term award (20 or fewer contacts needed) | Orange highlight: "Need 15 Tribune members" |
| **MEDIUM** | Helpful but long-term (100+ contacts needed) | Yellow highlight: "Helps with Triple Key (Bug type)" |
| **LOW** | Already worked recently (within 30 days) | Green highlight: "Already worked 5 days ago" |
| **SKIP** | Already worked long ago or not an SKCC member | Gray/no highlight |

### 2. **Visual Color Coding**

The spot table uses intuitive colors to immediately show relevance:

- 🔴 **Red** (CRITICAL): Stop what you're doing and work this station!
- 🟠 **Orange** (HIGH): Strongly recommended for your award progress
- 🟡 **Yellow** (MEDIUM): Helpful for longer-term goals
- 🟢 **Green** (LOW): Already worked recently (reference only)
- ⚫ **Gray** (SKIP): Not relevant to your current awards

### 3. **Award Progress Information**

When you hover over or click on a highlighted spot, you'll see:

```
📍 K5ABC
✓ Worked 1 time (3 days ago)

🎯 AWARD OPPORTUNITIES:
  • Centurion: 98/100 contacts (need 2 more)
  • Tribune: 45/100 Tribune+ members (need 55 more)
```

This instantly tells you:
- Why this spot is important
- How close you are to your goal
- Which specific awards would benefit

## Configuration

### Enabling Award-Based Highlighting

The feature is configured in your application settings:

```yaml
# In your config or UI settings
spots:
  enable_award_eligibility: true          # Master switch
  highlight_by_award: true                # Use award-based colors
  highlight_worked: true                  # Show worked contacts
  highlight_recent_days: 30               # Threshold for "recent"
```

### UI Controls (in RBN Spots Tab)

The RBN Spots Widget includes new controls:

**Options Section:**
- ☑️ **Highlight Award-Relevant** - Enable/disable award highlighting
- ☑️ **Show Worked Contacts** - Gray out stations you've already worked
- 📅 **Days** - How recent is "recent" (e.g., 30 days)?

**Filtering Section:**
- ☑️ **Show CRITICAL** - Only show spots that are critical for awards
- ☑️ **Show HIGH** - Include important award-related spots
- ☑️ **Show MEDIUM** - Include longer-term award spots
- ☑️ **Show Worked** - Include already-worked stations for reference

## Award-Specific Highlighting

### Centurion Award

Once you start logging SKCC members, the system automatically:
- Counts how many unique SKCC members you've worked
- Highlights spots for new SKCC members you haven't worked
- Shows urgency: "RED" when within 5 contacts of 100

Example progression:
```
95 contacts → RED: Need 5 more!
85 contacts → ORANGE: Need 15 more
50 contacts → YELLOW: Need 50 more
```

### Tribune/Senator Awards

After achieving Centurion:
- Spots with Tribune (T) or Senator (S) suffix are highlighted
- Tribune members show ORANGE (prerequisite award)
- Senators show RED when you're close to Tribune qualifying

### Triple Key Award

Tracks three key types separately:
- Straight Key (SK) contacts highlighted
- Bug (BUG) contacts highlighted  
- Sideswiper (SS) contacts highlighted

Example:
```
SK: 78/100 → YELLOW (need 22 more)
BUG: 45/100 → ORANGE (need 55 more)
SS: 12/100 → YELLOW (need 88 more)
```

## Workflow Examples

### Example 1: Active Centurion Hunter

You have 98 Centurion contacts and need 2 more to qualify.

**What you see:**
- RBN spot for K5XYZ (new SKCC member): **RED highlight**
- RBN spot for W4ABC (already worked): **Gray highlight**
- Info for K5XYZ shows: "CRITICAL: Need 2 more contacts for Centurion"

**Action:** Prioritize working K5XYZ!

### Example 2: Tribune Progression

You've completed Centurion (100+ contacts) and now need Tribune members.

**What you see:**
- RBN spot for K7T (Tribune member, not yet worked): **ORANGE highlight**
- RBN spot for K6 (SKCC member, not Tribune): **YELLOW highlight**
- Info for K7T shows: "Need 30 Tribune members for Tribune award (70/100 current)"

**Action:** Work K7T to progress toward Tribune!

### Example 3: Triple Key Strategy

You're working on Triple Key (need 100 of each key type).

**What you see:**
- RBN spot for N0BUG (Bug key user): **ORANGE highlight** (only 45/100 bugs)
- RBN spot for W4SK (Straight Key user): **YELLOW highlight** (already 78/100 SK)
- Info shows key type and progress for each

**Action:** Prioritize Bug users to balance your Triple Key progress!

## Advanced Features

### Automatic Cache Invalidation

When you log a new contact:
1. The award eligibility cache automatically clears
2. All spot classifications recalculate on next view
3. New contacts immediately appear with updated highlighting

### Contact Duplicate Detection

Already worked K5ABC this evening?
- Within 3 minutes: Spot is filtered (duplicate suppression)
- After 3 minutes: Spot reappears for potential re-contact

### Recently Worked Highlighting

Configurable "recent" threshold:
- Default: 30 days
- Show these as green (already in book)
- Useful for reference or multi-operator events

## Tips & Tricks

### 1. Focus on RED Spots
During a contest or focused operating session:
- Filter to show only RED spots
- These are your path to the next award
- Each one gets you closer to qualification

### 2. Use GREEN for Reference
- Show worked contacts for the last 30 days
- Useful for understanding what you've been working
- Good for spotting patterns in band/mode preferences

### 3. Monitor Award Progress
- Spot tooltip shows real-time progress
- See your progress increase as you work stations
- Motivation boost: watch the numbers move!

### 4. Combine with Other Filters
- Show only SKCC members on 40m: Focus on your preferred band
- Show only CW stations: Match your mode preference
- Show only CRITICAL award spots: Maximum focus mode

## Troubleshooting

### Spots Not Highlighting

**Issue:** Spots appear but no highlighting

**Solutions:**
1. Check: Is "Highlight Award-Relevant" enabled?
2. Check: Is award eligibility data loaded? (See Settings)
3. Check: Are you logged in with valid SKCC number?

### Highlight Color Wrong

**Issue:** Spot shows YELLOW but should be RED

**Cause:** Award progress not updated

**Solution:**
1. Log a new contact
2. Refresh spots (click "Refresh Spots" button)
3. Cache auto-updates every 5 minutes

### Missing Award Progress Info

**Issue:** Tooltip doesn't show award details

**Cause:** SKCC roster not loaded or membership lookup failed

**Solution:**
1. Verify SKCC roster file is present
2. Check application log for errors
3. Restart application to reload roster

## Performance Notes

### Highlighting Impact

- Minimal performance impact (caching used extensively)
- First analysis: ~50ms per spot (one-time)
- Subsequent analyses: <1ms per spot (cached)
- Cache refreshes every 5 minutes or after new contact

### Optimization Tips

1. **Disable if not needed:** Toggle off if not pursuing awards
2. **Adjust cache timeout:** 5 minutes default (adjustable in config)
3. **Filter spots:** Show only relevant classifications to reduce table size

## Future Enhancements

Potential features for future releases:

1. **DXCC-based highlighting** - Highlight needed countries/continents
2. **WAS-based highlighting** - Highlight needed US states
3. **Custom award rules** - Define your own award/goal combinations
4. **Predictive highlighting** - Suggest which award to pursue next based on current progress
5. **Statistics dashboard** - Show award progress trends over time

## Getting Help

For questions or issues:

1. Check the application log: `logs/` directory
2. Review this guide (especially Troubleshooting section)
3. Check application Settings for award eligibility status
4. Contact support with log file attached

---

**Happy spotting and award hunting!** 🎯📻

