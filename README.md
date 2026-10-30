# testing_data_sfdx_proj

SFDX project with complex validation rules. Each of the 14 rules nests 6-9 levels deep and packs 11+ distinct functions and mixes logical, text, math, date/time, picklist, regex, CASE and VLOOKUP functions. Every function in the allowed list is used at least once. See [COVERAGE.md](COVERAGE.md).

## Deploy

```
sf project deploy start --dry-run -d force-app -o <alias>   # validate first
sf project deploy start -d force-app -o <alias>
sf org assign permset -n Full_Access -o <alias>
```
Use a scratch org or sandbox. Not meant for production.

## Objects

- `Employee_Record__c` (24 fields)
- `Project__c` (22 fields)
- `Rate_Table__c` (2 fields)
- `Shipment__c` (21 fields)

## Validation rules (14)


### Employee_Record__c

- `Emp_Age_Pay_Bands` [Math/trig/geo]: Age at hire (ADDMONTHS), leap-day birthdays, termination ordering, grade-based salary bands (CASE) scaled for part-timers, and a log-scaled bonus ceiling.
- `Emp_Identity_Forensics` [String forensics]: National Id, Employee Id, Badge Code and Name/Email are validated with REGEX, VALUE, REVERSE, ASCII, CHR, MOD, LPAD-style, INITCAP and SUBSTITUTE forensics.
- `Emp_Manager_Review_Mega` [Mega-combo]: Performance may not exceed the manager's (VLOOKUP by name), scores move in half-point steps in 0-5, review timestamps are checked with DATETIMEVALUE/TIMEVALUE and the bio length is bounded by skills.
- `Emp_Shift_Skill_Location_Rules` [Picklist & multi-picklist logic]: Shift windows (HOUR/MINUTE math vs weekly hours), skill requirements per grade (INCLUDES/PICKLISTCOUNT), on-site distance limit per grade (DISTANCE in km), and salary/review change freezes after termination.

### Project__c

- `Prj_Calendar_Engine` [Date/Time engineering]: Non-draft projects must start and kick off in the same ISO year within a priority-driven number of ISO weeks, end within a clamped month horizon, avoid unexempted weekend starts, and avoid year-end starts that fall in the wrong quarter-month window.
- `Prj_Change_Control` [Change tracking]: Inserts and clones must start clean; updates enforce a status ladder, a budget change policy and a frozen identity once approved, using ISNEW, ISCLONE, ISCHANGED and PRIORVALUE.
- `Prj_Code_Name_Forensics` [String forensics]: Code must match PRJ-YYYY-NNNN-XX with a sane year, XX equal to the name initials, a zero-padded non-palindromic serial and a hyphen at the right offset; names, notes and contact email get whitespace, case, ASCII, line-break and structural checks.
- `Prj_Region_Geo_Currency_Gate` [Cross-object (VLOOKUP)]: Regulated projects need a Region Key resolving through VLOOKUP into an active Rate Table row with a capped rate, a location within 3000 miles of a reference point, an 18-char CASESAFEID account, a positive currency rate and a line-break-free name.
- `Prj_Risk_Burn_Math` [Math/trig/geo]: Unapproved projects face a log/exp/sqrt risk curve against budget, a time-prorated burn-rate ceiling (TRUNC/FLOOR/MIN/MAX), and whole-thousand budget and 5% completion step rules; null risk is skipped via ISNULL.
- `Prj_Tags_Status_Matrix` [Picklist & multi-picklist logic]: Multi-picklist Tags are checked against Priority, Status (ranked by a CASE ladder), approval, notes and contact data, with count ceilings and forbidden combinations.
- `Prj_Time_Epoch_Forensics` [Date/Time engineering]: Epoch seconds must agree with Kickoff At (year, hour, 5-minute grid, no stale midnight), durations must render with day units, standup times must sit in a lunch-free window, and active kickoffs cannot be in the future.

### Shipment__c

- `Shp_Carrier_Handling_Matrix` [Picklist & multi-picklist logic]: Carrier-specific tracking formats (CASE ladder), handling vs service level rules, customs code shape for international shipments and declared-value insurance rules.
- `Shp_Timeline_Lock_Project_Risk` [Mega-combo]: Mega-rule: ETA/delivery timestamps (DATETIMEVALUE, ISOWEEK, FORMATDURATION), dock-window time checks, post-ship lock via ISCHANGED/PRIORVALUE, and a VLOOKUP into the project's risk score that demands Signature Required.
- `Shp_Trig_Geometry` [Math/trig/geo]: Haversine (SIN/COS/ATAN2/SQRT/PI) must agree with DISTANCE for international shipments; box dimensions pass ATAN/ASIN/ACOS/TAN sanity bands; volume and density pass LOG/EXP checks; transit speed must be physically possible.

## Tooling

- `tools/generate.py`: regenerates metadata from `tools/model.py` and `tools/rules_*.py`.
- `tools/verify.py`: static checks (XML, parens, allowed functions, field refs, coverage). `--coverage` rewrites COVERAGE.md.
