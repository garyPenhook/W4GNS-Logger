# RBN Spot Highlighting - Quick Reference

## What Does Each Color Mean?

| Color | Meaning | Action |
|-------|---------|--------|
| 🔴 **RED** | CRITICAL - You're almost there! (≤5 contacts needed) | **PRIORITY: Work this station NOW** |
| 🟠 **ORANGE** | HIGH - Important for your awards (≤20 contacts needed) | Work ASAP when possible |
| 🟡 **YELLOW** | MEDIUM - Helps longer-term goals (>20 contacts needed) | Nice to work, but not urgent |
| 🟢 **GREEN** | Already worked recently (within 30 days) | Reference/backup |
| ⚫ **GRAY** | Already worked long ago | Not relevant |
| ⚪ **NO COLOR** | Not relevant to your awards | Pass (unless interested) |

## Example Scenarios

### Scenario 1: You're at 98 Centurion Contacts

**Red Spot Alert:** K5XYZ is an SKCC member you haven't worked yet
- **Means:** Working K5XYZ gets you to 99/100 - you're almost there!
- **Tooltip:** "CRITICAL: Need 2 more contacts for Centurion"
- **Action:** Make it a priority!

### Scenario 2: You Just Earned Centurion

**Orange Spots Start Appearing:** K7ABC (Tribune), N6DEF (Tribune)
- **Means:** Now the system is highlighting Tribune members for your next award
- **Tooltip:** "Need 45 Tribune+ members for Tribune award (55/100 current)"
- **Action:** Work these to progress toward Tribune!

### Scenario 3: You're Chasing Triple Key

**Yellow Spots for Bug Users:** N0BUG, K0BUGME, W5KEYER
- **Means:** These help your Triple Key (Bug) goal which is still far off
- **Tooltip:** "Triple Key (Bug): 45/100 Bug users (need 55 more)"
- **Action:** Work them when you have time

## How to Use the Highlighting

### Step 1: Enable Highlighting

In the RBN Spots tab:
- ☑️ Check "Highlight Award-Relevant"
- ☑️ Check "Show Worked" (optional, shows green/gray for reference)

### Step 2: Understand Your Colors

Look at the spot table and use the color coding to prioritize:
- See a **RED** spot? Stop and work it!
- See **ORANGE** spots? Work them between other activities
- See **YELLOW** spots? Good for background goals

### Step 3: Hover for Details

Move your mouse over any highlighted spot to see:
- Full callsign and worked history
- Specific awards that benefit
- Progress toward each award
- How many more contacts you need

Example:
```
📍 K5ABC
✓ Worked 2 times (1 week ago)

🎯 AWARD OPPORTUNITIES:
  • Tribune: 85/100 Tribune+ (need 15 more)
```

### Step 4: Click to Work

Click on a highlighted spot to select it for logging, or just note the info for later.

## Common Questions

### Q: Why isn't a spot highlighted?

**Reasons:**
1. They're not an SKCC member (only SKCC members help with SKCC awards)
2. You've already worked them many times
3. No active awards would benefit from them
4. You've already achieved all awards

**Solutions:**
- Check application log to see if SKCC roster loaded correctly
- Verify your SKCC number is set correctly
- Check award progress in the Awards tab

### Q: The color changed - why?

**Possible reasons:**
1. You logged a new contact (eligibility cache updated)
2. 5 minutes passed and cache refreshed
3. Award progress changed (different eligibility)

**Typical scenario:**
- Spot was YELLOW (need 50 more)
- You work 10 more Centurion members
- Same spot (from new RBN cluster) is now ORANGE (need 40 more)

### Q: Can I focus on only RED spots?

**Yes!** Use filters:
- Check "Show CRITICAL" only
- Uncheck "Show HIGH" and "Show MEDIUM"
- This shows only your most urgent opportunities

### Q: What about non-SKCC members?

**Gray/no color** - they won't help with SKCC awards (Centurion, Tribune, Senator, Triple Key).

However:
- They might help with other awards (DXCC, WAS, WAC)
- Future versions may support these awards
- For now, ignore if pursuing SKCC awards

## Quick Setup

1. **Enter your callsign and SKCC number:**
   - Settings → Operator → Callsign & SKCC Number
   - Example: W4GNS, 14947T

2. **Confirm SKCC roster loaded:**
   - Should see message: "SKCC roster loaded (X members)"

3. **Turn on highlighting:**
   - RBN Spots tab → Highlighting Options
   - ☑️ Enable Award-Relevant highlighting

4. **Start seeing colors!**
   - Next RBN spots will have highlighting based on your awards

## Award Milestones

### Centurion (100 unique SKCC members)
- **Spots:** Any SKCC member
- **Highlighting:** RED when ≤5 away, ORANGE when ≤20 away
- **Duration:** Weeks to months

### Tribune (100 Tribune members + Centurion prerequisite)
- **Spots:** SKCC members with "T" or "S" suffix
- **Highlighting:** ORANGE when available after Centurion
- **Duration:** Months

### Senator (100 Senator members + Tribune prerequisite)
- **Spots:** SKCC members with "S" suffix only
- **Highlighting:** RED when close, after Tribune achieved
- **Duration:** Months to years

### Triple Key (100 of each key type)
- **Spots:** Users with SK/BUG/SS key preference
- **Highlighting:** Separate tracking for each type
- **Duration:** Years (slowest award)

## Pro Tips

### Tip 1: Color Intensity Matters
- Brighter = more important
- RED (bright) > ORANGE (medium) > YELLOW (faded)
- Helps your eye quickly spot priorities

### Tip 2: Multi-Op Events
- If running multi-op, set each operator's callsign/SKCC number
- Spotting shows their personal award priorities
- Each operator can see their own progress

### Tip 3: Award Strategy
- Focus on one award at a time
- When close to RED zone, hunt aggressively
- Saves time vs. random spotting

### Tip 4: Worked History
- GREEN spots = recently worked (good for testing setup)
- Use to verify highlighting is working
- If GREEN spots don't show = check highlighting settings

## Troubleshooting in 30 Seconds

| Problem | Quick Fix |
|---------|-----------|
| No highlighting appearing | ☑️ "Highlight Award-Relevant" checked? |
| Wrong colors | ☑️ SKCC number set correctly? |
| Spots missing | Click "Refresh Spots" button |
| Cache stale | Wait 5 minutes (auto-refreshes) or restart app |
| Tooltip blank | Hover longer or click spot |

---

**Need more help?** See the full guide: `SPOT_HIGHLIGHTING_GUIDE.md`

