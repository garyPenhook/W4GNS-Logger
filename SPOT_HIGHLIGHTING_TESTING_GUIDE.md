# Spot Highlighting - Testing & Verification Guide

**Date:** October 28, 2025  
**Status:** ✅ Ready to Test

---

## 🎯 Quick Test Procedure

### Step 1: Verify Settings
1. Start the application
2. Open **Settings** (File → Settings)
3. Go to **Operator** tab
4. Verify:
   - **Callsign**: W4GNS
   - **SKCC Number**: 14947T (in ADIF tab)
5. Click **Save**

### Step 2: Check Startup Logs
Watch the console or log file for:

```
✅ SpotMatcher initialized: award_eligibility_available=True
✅ SpotEligibilityAnalyzer initialized for W4GNS (14947T)
✅ Award eligibility analysis enabled for W4GNS
```

If you see these messages, the feature is **ACTIVE** ✅

### Step 3: Start Monitoring
1. Click **SKCC/DX Spots** tab
2. Click **Start Monitoring** button
3. Watch for spots to appear
4. Colored spots = Award-relevant!

### Step 4: Look for Highlighting
When spots arrive, you should see:

| Spot Type | Color | Meaning |
|-----------|-------|---------|
| 🔴 Red highlighted | CRITICAL | **WORK THIS NOW** - Need ≤5 more |
| 🟠 Orange highlighted | HIGH | Important - Need ≤20 more |
| 🟡 Yellow highlighted | MEDIUM | Medium priority - 21-100+ needed |
| 🟢 Green highlighted | LOW | Already worked or low priority |
| No highlight | NONE | Not relevant to your awards |

### Step 5: Hover for Details
Move mouse over **any colored spot row**:
- Tooltip appears
- Shows exact reason for highlighting
- Examples:
  - "CRITICAL: Need 2 more for Centurion"
  - "HIGH: Need 8 more for Tribune"
  - "MEDIUM: 150+ needed for Senator"

---

## 📊 Expected Behavior Examples

### Scenario 1: Red Spot (CRITICAL)
```
Event: VU2OR appears on 7 MHz
Your Progress:
  - Centurion: 98/100 (need 2 more)
  - Tribune: 88/100 (need 12 more)
  - Senator: 75/100 (need 25 more)

Action:
  ✅ Row highlighted in RED
  ✅ Tooltip: "CRITICAL: Need 2 more for Centurion"
  ✅ You should work this ASAP
```

### Scenario 2: Orange Spot (HIGH)
```
Event: K4MZ appears on 14 MHz
Your Progress:
  - Centurion: 95/100 (need 5 more)
  - Tribune: 78/100 (need 22 more)  ← Closest unmet
  - Senator: 45/100 (need 55 more)

Action:
  ✅ Row highlighted in ORANGE
  ✅ Tooltip: "HIGH: Need 22 more for Tribune"
  ✅ Good opportunity to work
```

### Scenario 3: Yellow Spot (MEDIUM)
```
Event: W1ABC appears on 20 MHz
Your Progress:
  - Centurion: 98/100 (need 2 more)
  - Tribune: 88/100 (need 12 more)
  - Senator: 45/100 (need 55 more)  ← Closest unmet
  - Triple Key SK: 78/100, Bug: 99/100, SS: 20/100 ← SS is 80 away

Action:
  ✅ Row highlighted in YELLOW
  ✅ Tooltip: "MEDIUM: 80+ needed for Sideswiper"
  ✅ Work if convenient, but not urgent
```

### Scenario 4: No Highlight
```
Event: N5XYZ appears on 10 MHz
Your Progress:
  - Already have this station (worked before)
  OR
  - Not an SKCC member
  OR
  - Not relevant to any active award

Action:
  ✅ No highlight
  ✅ No tooltip
  ✅ Duplicate or not relevant
```

---

## 🔍 Verification Checklist

### Application Startup
- [ ] Application starts without errors
- [ ] No Python exceptions in console
- [ ] Settings load successfully
- [ ] Config shows W4GNS + 14947T

### SpotMatcher Initialization
- [ ] In logs: `SpotMatcher initialized: award_eligibility_available=True`
- [ ] In logs: `SpotEligibilityAnalyzer initialized for W4GNS`
- [ ] In logs: `Award eligibility analysis enabled for W4GNS`

### Spot Reception & Highlighting
- [ ] Can click "Start Monitoring" successfully
- [ ] RBN connection connects (look for status indicator)
- [ ] Spots appear in table
- [ ] At least some spots have color highlighting
- [ ] Highlighting corresponds to award needs

### Color Mapping
For testing, create test spots (or wait for real ones):

```python
# Pseudo-code to understand highlighting
if needs_count <= 5:
    color = RED (255, 0, 0)           # CRITICAL
elif needs_count <= 20:
    color = ORANGE (255, 100, 0)      # HIGH
elif needs_count <= 100:
    color = YELLOW (255, 200, 0)      # MEDIUM
elif worked_less_than_30_days_ago:
    color = GREEN (100, 200, 100)     # LOW (duplicate)
else:
    color = NONE (no highlight)       # Not relevant
```

### Tooltips
- [ ] Hover over red spots → See "CRITICAL: ..." message
- [ ] Hover over orange spots → See "HIGH: ..." message
- [ ] Hover over yellow spots → See "MEDIUM: ..." message
- [ ] Green spots → May or may not have tooltip
- [ ] No highlight spots → No tooltip

---

## 📈 Award-Specific Testing

### Centurion Award (100 unique SKCC members)
**Your Status:** 98/100 needed

**Test:**
1. Look for SKCC member spots
2. Should be mostly RED when need ≤5
3. When you log a new contact, highlighting should update

**Expected:** Red spots for unworked SKCC members

### Tribune Award (100 Tribune+ members)
**Your Status:** 88/100 needed

**Test:**
1. Look for Tribune+ member spots
2. Should show ORANGE or YELLOW (depending on Centurion need)
3. Wait until Centurion is satisfied → Tribune will become more RED

**Expected:** Spots highlight ORANGE until Centurion complete

### Senator Award (100 Senator members)
**Your Status:** 75/100 needed

**Test:**
1. Look for Senator member spots
2. Will be YELLOW (lower priority) until Tribune/Centurion complete
3. Once Centurion/Tribune done → Should turn more orange/red

**Expected:** Yellow/Orange highlighting for Senator progress

### Triple Key (SK, Bug, Sideswiper)
**Your Status:** SK=78/100, Bug=99/100, SS=20/100

**Test:**
1. Spots with SKCC # showing Sideswiper key = HIGH PRIORITY
2. Bug should be mostly worked (99/100) - show orange at best
3. SK should show yellow/orange
4. SS (your weakest) = CRITICAL when available

**Expected:** 
- SS spots very important (80 needed)
- SK spots important (22 needed)  
- Bug spots common (1 needed)

---

## 🐛 Troubleshooting

### Issue: No Colored Spots
**Diagnosis:**
```bash
# Check application logs for:
grep -i "award_eligibility_available=False" app.log
```

**Solution:**
- [ ] Check Settings → ADIF tab for SKCC number
- [ ] Ensure SKCC number saved (not empty)
- [ ] Restart application
- [ ] Check for errors in logs

### Issue: Wrong Spot Colors
**Diagnosis:**
- Red spots appearing for stations you need (wrong color!)
- Or no red spots when you clearly need them

**Solution:**
1. Verify award progress in Awards tabs
2. Manually check Centurion tab → How many need?
3. Check if spots are SKCC members (check SKCC# column)
4. Verify database has correct SKCC numbers

**Command to check database:**
```bash
sqlite3 ~/.w4gns_logger/contacts.db \
  "SELECT callsign, skcc_number FROM contacts LIMIT 10;"
```

### Issue: Analyzer Not Initializing
**In logs you see:**
```
award_eligibility_available=False
```

**Solution:**
- Verify config keys are correct:
  - `general.operator_callsign` (should be W4GNS)
  - `adif.my_skcc_number` (should be 14947T)
- Restart application
- Check console for Python errors

### Issue: Performance Issues
**If highlighting is slow (>100ms per spot):**

**Solution:**
- First spot: ~50ms (builds cache)
- Subsequent spots: <1ms (cached)
- If still slow, check system resources
- Verify database isn't corrupted

---

## 📝 Logging to Enable Debugging

### Enable Debug Logging
Edit configuration or check `~/.w4gns_logger/config.yaml`:

```yaml
logging:
  level: DEBUG  # Will show detailed messages
```

### Watch for These Debug Messages
```
DEBUG - SpotMatcher cache refreshed: 214 worked callsigns
DEBUG - Award cache updated: worked=98, critical=2, target=100
DEBUG - Analyzing spot: VU2OR (SKCC member)
DEBUG - Eligibility for VU2OR: CRITICAL (Centurion needs 2)
```

### Log File Location
```
~/.w4gns_logger/w4gns_logger.log
```

---

## ✅ Final Verification

Before declaring success:

1. **Feature is Active:**
   - [ ] Application starts
   - [ ] SpotEligibilityAnalyzer initializes
   - [ ] Logs show `award_eligibility_available=True`

2. **Spots Receive Highlighting:**
   - [ ] Can start monitoring
   - [ ] Spots appear in table
   - [ ] Some spots are highlighted with colors

3. **Colors Match Awards:**
   - [ ] Red spots = Need ≤5 for an award
   - [ ] Orange spots = Need ≤20 for an award
   - [ ] Yellow spots = Need 21+ for an award
   - [ ] Green spots = Already worked

4. **Tooltips Show Details:**
   - [ ] Hover reveals award details
   - [ ] Message format: "CRITICAL: Need X more for Award"

5. **Interaction Works:**
   - [ ] Can click spots
   - [ ] Spot info populates logging form
   - [ ] Can log contact normally

---

## 🎯 Real-World Test Scenario

**Best test:** Just let it run and monitor!

```
Timeline:
  21:40 - Start monitoring
  21:41 - First spots arrive (likely green/yellow, working on awards)
  21:42 - RED spot arrives (urgent!)
  21:43 - Click red spot, log contact
  21:44 - Highlighting updates for next spots
  ✅ SUCCESS!
```

---

## 📞 Support

If highlighting doesn't work:

1. **Check logs first:**
   ```bash
   tail -100 ~/.w4gns_logger/w4gns_logger.log | grep -i "award\|eligibility\|analyzer"
   ```

2. **Verify configuration:**
   ```bash
   grep -E "operator_callsign|my_skcc_number" ~/.w4gns_logger/config.yaml
   ```

3. **Restart application** (often fixes cache issues)

4. **Check for Python errors** in console

---

## 📊 Expected Output

### Successful Startup (Watch logs):
```
✅ SpotMatcher initialized: highlight_worked=True, recent_days=30, award_eligibility_available=True
✅ SpotEligibilityAnalyzer initialized for W4GNS (14947T)
✅ Award eligibility analysis enabled for W4GNS
```

### Successful Monitoring (Watch table):
```
| Callsign | Freq | Mode | Speed | SKCC# | Reporter | Time | Age |
|----------|------|------|-------|-------|----------|------|-----|
| IT9ATQ/B | 21.1 | CW   | 25    |       | N1ABC    | 21:40| 5s  |  ← No highlight (not SKCC)
| VU2OR    | 14.0 | CW   | 20    | 12345 | W4XYZ    | 21:40| 4s  |  ← RED highlight ← CRITICAL!
| KH6RS    | 24.9 | CW   | 18    | 98765 | N2LLL    | 21:40| 3s  |  ← ORANGE highlight
```

---

## 🎉 Success Criteria

**The feature is working when:**

✅ Application starts without errors  
✅ SpotEligibilityAnalyzer initializes successfully  
✅ Spots appear in table  
✅ At least SOME spots have colored highlighting  
✅ Colored spots match your actual award needs  
✅ Hovering shows detailed tooltips  

**If all above are true → Feature is LIVE and WORKING!** 🚀

---

## Next Steps

Once you verify the highlighting works:

1. **Optional: Add cache invalidation** after logging contacts
2. **Optional: Enable more awards** (DXCC, WAS, WAC)
3. **Optional: Add filtering UI** for "Show only CRITICAL"
4. **Optional: Add statistics dashboard**

For now, just enjoy the highlighted spots showing your award-relevant opportunities! 📻🎯

---

**Happy spotting and award hunting!**
