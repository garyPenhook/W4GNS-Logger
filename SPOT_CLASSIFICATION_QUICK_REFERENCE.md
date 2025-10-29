# Quick Reference: Spot Classification

## What You See in the Spots Table

### 🟢 GREEN (GOAL)
**You need this station for your awards**

Examples:
- First contact with someone + need for Centurion
- Tribune member + working Tribune award
- Senator + working toward Senator

**Why:** You've never worked them AND your incomplete awards need them.

---

### 🔵 BLUE (TARGET)  
**They might need YOU, but you don't need them for awards**

Examples:
- Already worked them 5+ times
- Not an SKCC member
- Centurion complete, they're just a regular member
- Senator when you're not working Senator award yet

**Why:** Either you don't need them for any incomplete awards, or you've worked them enough already.

---

### ⚪ NO COLOR (SKIP)
**Not relevant to your awards**

Examples:
- Not in SKCC roster at all
- QSO would violate some award rule

---

## How Classification Works

The system checks, in order:

1. **Contact Count** 
   - "Have I worked this callsign 3+ times?" 
   - If YES → **TARGET** (skip to end)

2. **SKCC Roster**
   - "Is this person an SKCC member?"
   - If NO → **None/Skip**

3. **Award Needs**
   - "Do my incomplete awards need this person's level/type?"
   - If NO → **TARGET**
   - If YES + never worked → **GOAL**
   - If YES + worked before → **BOTH**

---

## Awards That Use Classification

✅ **Centurion** - Any SKCC member
✅ **Tribune** - Tribune/Senator members only  
✅ **Senator** - Senator members only
✅ **TripleKey** - Contacts with specific key types

❌ **WAS/WAC** - Not possible (roster lacks geography)
❌ **DXCC** - Not checked in spots (use awards tab instead)

---

## Examples

| Spot | Your Status | Result |
|---|---|---|
| K5ABC (Tribune) - never worked | Centurion: 87/100 | 🟢 GOAL |
| K5ABC (Tribune) - worked 8 times | Centurion: 87/100 | 🔵 TARGET |
| W3DEF (not SKCC) | Any | ⚪ None |
| K1XYZ (Tribune) - worked 2x | Tribune: 45/50 T/S | 🟡 BOTH |

---

## Settings

**Spot Source Dropdown:**
- Auto-detect (tries Skimmer, falls back to RBN)
- SKCC Skimmer (if available)
- Direct RBN (direct connection)

**Show Goals/Targets:**
- Toggle checkboxes to filter table
- Classify happens regardless

---

## Performance

- First 5 minutes: Database queries as spots arrive
- After 5 minutes: Uses cached award data (fast)
- After new contact logged: Cache refreshes (3-5 sec)

---

## Data Used

From your database:
- Contact history (have you worked this callsign?)
- Award eligibility (what do you need?)
- SKCC roster (what level are they?)
- Your SKCC number (which awards apply to you?)

No external data needed (except SKCC roster if not downloaded).

---

## Troubleshooting

**All spots showing GOAL?**
→ Check if your awards tab shows incomplete awards. If all complete, spots should be TARGET.

**All spots showing TARGET?**
→ Your awards are complete! You're just networking now.

**No spots showing?**
→ Check spot filter settings or SKCC roster loaded.

**Spots disappearing?**
→ 3-minute duplicate filter per callsign. Same person won't re-appear for 3 min.

---

## Contact Support

For classification questions, check:
1. Awards tab (verify your award status)
2. Logs (enable DEBUG for classification details)
3. SKCC roster (verify member data loaded)
