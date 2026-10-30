# testing_data_sfdx_proj

SFDX project with complex validation rules. Each rule nests 3-5 levels deep and mixes logical, text, math, date/time, picklist, regex, CASE and VLOOKUP functions. Every function in the allowed list is used at least once. See [COVERAGE.md](COVERAGE.md).

## Deploy

```
sf project deploy start --dry-run -d force-app -o <alias>   # validate first
sf project deploy start -d force-app -o <alias>
sf org assign permset -n Full_Access -o <alias>
```
Use a scratch org or sandbox. Not meant for production.

## Objects

- `Project__c` (23 fields)
- `Task_Item__c` (16 fields)
- `Invoice__c` (20 fields)
- `Shipment__c` (24 fields)
- `Employee_Record__c` (27 fields)
- `Rate_Table__c` (4 fields)
- `Account` (standard, +7 custom fields)
- `Opportunity` (standard, +5 custom fields)

## Validation rules (83)


### Account

- `Acc_Annual_Spend_Change_Rule` [Change tracking]: Annual Spend may drop by at most 50% in one edit, tier downgrades need a Type of 'Customer - Direct' or blank, and territory changes lock Global accounts.
- `Acc_Contact_Info_Mega` [Mega-combo]: Mega-check of phone digits, website prefix, billing country/state coherence, employee counts and rating vs tier.
- `Acc_Founding_Employees_Revenue` [Math/trig/geo]: Revenue per employee must be sane (log-scaled), founding date must not be in the future and young companies (<2y) cannot report >1B revenue.
- `Acc_Tax_Id_Region_Code` [String forensics]: Tax Id must be 2-letter region + hyphen + 9 digits, region must equal Region Code prefix, and the website slug must be lowercase and hyphenated.
- `Acc_Tier_Spend_Ladder` [Picklist & multi-picklist logic]: Account tier requires minimum annual spend (CASE) and Platinum accounts must have a website, a global territory and a phone.

### Employee_Record__c

- `Emp_Age_At_Hire` [Date/Time engineering]: Employees must be 16+ at hire, hire date cannot be in the future by more than 90 days, interns under 26, and hire must not fall on 29 Feb for a non-leap check.
- `Emp_Badge_Code_Mirror` [String forensics]: Badge code is a letter-digit mixture whose first and last chars cannot be equal, whose ASCII sum is checkable, and whose casing must be upper.
- `Emp_Manager_Grade_Order` [Cross-object (VLOOKUP)]: Performance score may not exceed the manager's score (VLOOKUP on the manager's Name), and scores must be within 0-5 on half-point steps.
- `Emp_Mega_Compliance` [Mega-combo]: Compliance mega-rule: age math, ID format, shift minutes, salary log scale, email parity and skill counts, all together.
- `Emp_Name_Email_Alignment` [String forensics]: Work email must start with first initial + last name (lowercase) and the employee name must be INITCAP-ed 'First Last'.
- `Emp_National_Id_Format` [String forensics]: National Id must look like NNN-NN-NNNN, not start with 000, 666 or 9, and its 3 groups may not be all-zero or reversed duplicates.
- `Emp_Office_Home_Distance` [Math/trig/geo]: On-site staff must live within a grade-based radius (120/150/200 miles) of the office.
- `Emp_Salary_Grade_Bands` [Math/trig/geo]: Salary must sit in a grade band (CASE), bonus cannot exceed a log-scaled share of salary, and part-timers' salaries are scaled by weekly hours.
- `Emp_Shift_Hours_Consistency` [Date/Time engineering]: Shift end must be after start, the shift length must match weekly hours / 5 within an hour, and shifts cannot start in the 22:00-05:59 window.
- `Emp_Skill_Grade_Requirements` [Picklist & multi-picklist logic]: Senior+ grades need at least 2 skills and Integration or Security; Directors need Data; Interns cannot carry Security.
- `Emp_Termination_Review_Lock` [Change tracking]: Termination date requires it to be after hire, salary freezes after termination and review timestamps cannot go back in time.

### Invoice__c

- `Inv_Currency_Rate_Sanity` [Math/trig/geo]: Currency code must be uppercase letters, the system rate for the invoice currency must be positive, and a custom exchange rate must be within 25% of it.
- `Inv_Due_Date_Terms_Match` [Date/Time engineering]: Due date must equal issue date plus the payment-terms days (CASE ladder), allowing 1 day slack and forbidding Sunday due dates for Net 30+.
- `Inv_Mega_Billing_Audit` [Mega-combo]: Sent invoices must pass an audit mixing dates, strings, money math, picklist counts and email shape.
- `Inv_Number_Format_Check_Digit` [String forensics]: Invoice number must be INV-YYYY-NNNNNN, year must equal the issue year, and the digit sum parity must be even (a mod-2 check on the first and last digits).
- `Inv_Paid_Timestamp_Rules` [Date/Time engineering]: Paid timestamp is required only for Paid invoices, must be after the issue date, not in the future, and not in the last 5 minutes of a day.
- `Inv_Payment_Method_Logic` [Picklist & multi-picklist logic]: Wire is mandatory above 50k, Check is banned for Due on Receipt, Card is capped at 10k, and recurring invoices cannot use Check.
- `Inv_Project_Contact_Domain_Match` [Cross-object (VLOOKUP)]: Billing email domain must equal the linked project's contact email domain (VLOOKUP by project Name); lookup ids must be 18 chars when case-safe.
- `Inv_Rate_Table_Region_Tax` [Cross-object (VLOOKUP)]: A custom Rate Table row named by the PO prefix supplies the maximum tax rate; invoices may not exceed it.
- `Inv_Status_Change_Control` [Change tracking]: Paid invoices are frozen, Void is terminal, and amount changes on Sent invoices need the status to be reset to Draft in the same edit.
- `Inv_Tax_Discount_Math` [Math/trig/geo]: Tax rate must be sub-50%, discount cannot exceed the larger of 30% of amount and 1000, and tax-inclusive total (rounded to cents) must be positive.

### Opportunity

- `Opp_Approval_Code_Structure` [String forensics]: Approval code is required when discount is over 20% and must be AP-<DDD>-<2 letter stage initials> where DDD is the close day-of-year.
- `Opp_Close_Date_Contract_Math` [Date/Time engineering]: Contract start must be on/after the close date and within 6 months, contract months must be a multiple of 3 (or 1) and cannot cross 5 years.
- `Opp_Closed_Won_Freeze` [Change tracking]: Closed Won opportunities cannot change amount or close date and cannot be reopened except to Closed Lost.
- `Opp_Competitor_Stage_Rules` [Picklist & multi-picklist logic]: Closed Won deals cannot list more than 2 competitors and Negotiation deals with Hooli need a Description.
- `Opp_Stage_Probability_Discount` [Math/trig/geo]: Probability must match the stage ladder within 10 points, and discount rises only up to sqrt-scaled caps for the amount.

### Project__c

- `Prj_Active_Kickoff_Freshness` [Date/Time engineering]: Active projects cannot kick off more than a day in the future, more than 2 years in the past, or later today than the current UTC time.
- `Prj_Approved_Immutable_Core` [Change tracking]: Once approved, the code, account and parent are frozen and dates may only be tightened (end earlier, start later).
- `Prj_Budget_Change_Control` [Change tracking]: Budget edits cannot fall below spend, approved budgets may move at most 20%, and completed projects are frozen.
- `Prj_Burn_Rate_Proration` [Math/trig/geo]: Spend (as truncated percent of budget) may not exceed the time-prorated share of the timeline plus a priority-based allowance.
- `Prj_Clone_Reset_Guard` [Change tracking]: A cloned project must start clean: not approved, no spend, Draft, 0% complete and no stale kickoff or epoch.
- `Prj_Code_Format_Checksum` [String forensics]: Code must match PRJ-YYYY-NNNN-XX, the year must be sane, and the suffix must equal the uppercased first two letters of the name.
- `Prj_Contact_Email_Forensics` [String forensics]: Contact email must be lowercase with a sane @ position, no '..' in the domain, no trailing dot, and external projects cannot use 'internal.' hosts.
- `Prj_Duration_Matches_Calendar` [Date/Time engineering]: Duration (seconds) cannot be negative or exceed the calendar span; day-or-longer durations must render with a day unit.
- `Prj_Epoch_Kickoff_Consistency` [Date/Time engineering]: Epoch Seconds must agree with Kickoff At within an hour, share its calendar year, and not sit more than 10 years ahead.
- `Prj_Kickoff_Datetime_Window` [Date/Time engineering]: Kickoff must lie between 7 days before 00:00:00 on the start date and 23:59:59 on the end date; completed projects must have enough elapsed hours.
- `Prj_Kickoff_ISO_Week_Alignment` [Date/Time engineering]: Non-draft projects must kick off in the same ISO year as the start date and within 2 ISO weeks of it.
- `Prj_Mega_Code_Forensics` [Mega-combo]: Code suffix must equal the initials of the first two name words, serial must not mirror the year, the epoch year must equal the code year, and approved codes must end in a letter.
- `Prj_Mega_Launch_Readiness` [Mega-combo]: Active projects must pass a launch-readiness gauntlet: code format, ISO-week parity, calendar span, burn rate, tags-per-priority, regulated contacts and a risk/completion balance.
- `Prj_Name_Hygiene` [String forensics]: Names must be trimmed, free of double spaces, not start with a digit (ASCII 48-57), and approved names must be in title case.
- `Prj_Notes_Line_Discipline` [String forensics]: Notes may have at most 50 line breaks, no tab or leading-space characters, and cancelled projects need a real explanation.
- `Prj_Parent_Code_Year_Order` [Cross-object (VLOOKUP)]: A child project's code year may not precede its parent's, and it cannot reuse the parent's code (VLOOKUP on the parent project's Name).
- `Prj_Phone_Digit_Forensics` [String forensics]: After stripping punctuation the phone must be numeric, 10-15 digits long, and an international '+' number cannot start with 0.
- `Prj_Region_Rate_Lookup` [Cross-object (VLOOKUP)]: Regulated projects need a Region Key that exists as a Rate Table record (VLOOKUP by Name) with an active region and a rate no higher than 25%.
- `Prj_Regulated_Geo_Fence` [Math/trig/geo]: Regulated projects must have a location within 3000 miles of the (37.7749, -122.4194) reference point.
- `Prj_Risk_Curve_vs_Budget` [Math/trig/geo]: Unapproved projects whose sqrt(risk)*e^-completion*ln(risk+1) exceeds log10(budget) are too risky for their size.
- `Prj_Round_Number_Discipline` [Math/trig/geo]: Non-draft budgets of 10k+ must be whole thousands, completion must move in 5% steps, and approved spend must be whole dollars.
- `Prj_Serial_Padding_Mirror` [String forensics]: Code serial must be zero-padded to 4 digits, may not be a non-zero palindrome, and zero serials are Draft-only.
- `Prj_Session_Guard` [Mega-combo]: Approved Completed projects cannot be created by a session-less context (GETSESSIONID empty) or carry a line break in the name.
- `Prj_Standup_Time_Grid` [Date/Time engineering]: Standup time must sit on a 5-minute grid between 06:00 and 20:00, with no seconds/millis and no 12:00-12:29 slot.
- `Prj_Status_Priority_Matrix` [Picklist & multi-picklist logic]: A CASE-ranked status ladder gates Critical priority, completion percent, drafts, high-priority approval and on-hold notes.
- `Prj_Status_Regression_Lock` [Change tracking]: Status may not drop two or more ladder ranks, Cancelled can only reopen to Planning, and Completed requires approval.
- `Prj_Tag_Count_vs_Priority` [Picklist & multi-picklist logic]: The number of tags must be within a priority-driven ceiling; High/Critical need at least one tag; External+Internal needs Regulated.
- `Prj_Tags_Compliance` [Picklist & multi-picklist logic]: Regulated projects must be approved, carry at most 3 tags, avoid the Pilot+Strategic combo and have a contact email.
- `Prj_Timeline_Max_Months` [Date/Time engineering]: End date must not precede start and may not exceed start plus 12/24/36 months depending on priority (clamped by MIN/MAX).
- `Prj_Weekend_Start_Guard` [Date/Time engineering]: Weekend start dates are only allowed for Critical projects or on Jan 1, and never in Dec/Jan unless that exemption holds.

### Rate_Table__c

- `Rate_Key_Region_Format` [String forensics]: Rate keys must be 3 uppercase letters, the region must be a prefix of it when set, and rates are capped at 100% with 2 decimal places.

### Shipment__c

- `Shp_Customs_Code_Locale` [String forensics]: International shipments need a customs code like 'HS-1234.56' built by LPAD/RPAD rules, domestic shipments must not have one.
- `Shp_Declared_Value_Insurance` [Math/trig/geo]: High declared values must be consistent with the weight (value per kg bounded by sqrt of weight) and require Signature Required handling.
- `Shp_Delivered_Lock` [Change tracking]: Delivered shipments are locked except for return transitions; tracking number and carrier cannot change after shipping.
- `Shp_Distance_Transit_Speed` [Math/trig/geo]: Average transit speed (miles per hour from DISTANCE and transit seconds) must be below 600 mph, and Ground service below 80 mph.
- `Shp_Dock_Window_Time` [Date/Time engineering]: Dock time must be in 07:00-18:59, not a lunch slot at 12:xx on the half hour, and the datetime-to-time check on ETA must not land on the dock-closed 00:00 sentinel.
- `Shp_Eta_Delivery_Windows` [Date/Time engineering]: ETA must follow shipping, delivered shipments need a delivery stamp no earlier than shipping, and ETA cannot be more than 60 days away.
- `Shp_Great_Circle_Haversine` [Math/trig/geo]: A trig haversine cross-check (SIN/COS/ATAN2/SQRT/PI) of the stored distance must agree with DISTANCE within 5% for international shipments.
- `Shp_Handling_Service_Matrix` [Picklist & multi-picklist logic]: Hazmat cannot fly Air/Express, Refrigerated needs Express or Air, Oversized needs Freight, and handling counts are bounded by service.
- `Shp_Inverse_Trig_Dimensions` [Math/trig/geo]: The box diagonal angle (ATAN, ASIN, ACOS, TAN) must stay in a stable band: height/length slope and normalised ratios cannot be degenerate.
- `Shp_Mega_Dispatch_Audit` [Mega-combo]: Dispatch audit: geo distance, ISO-week cutoffs, handling, tracking shape, weight math and transit duration formatting all in one pass.
- `Shp_Project_Risk_Handling` [Cross-object (VLOOKUP)]: Shipments for projects with risk above 7 (VLOOKUP by project Name) need Signature Required, and high-risk international shipments cannot go Ground or be declared above 5000.
- `Shp_Tracking_Number_By_Carrier` [String forensics]: Tracking numbers are validated by a carrier-specific CASE ladder of length and prefix rules, plus a no-spaces / uppercase check.
- `Shp_Volume_Weight_Density` [Math/trig/geo]: Declared volume must match L x W x H within 2%, and density (kg/m3) must be between 1 and 20000 using logarithmic bounds.

### Task_Item__c

- `Tsk_Assignee_Email_Domain_Case` [String forensics]: Assignee email must be lowercase, contain exactly one '@' (CHR(64)), and its local part may not be longer than 40 characters.
- `Tsk_Blocker_Due_Month_End` [Date/Time engineering]: Blocker tasks cannot be due on the last day of a month, on a Sunday, or before the end of last month.
- `Tsk_Completion_Timeline` [Date/Time engineering]: Completion must follow start, hours cannot exceed wall-clock time, only Done tasks have completion, Minor tasks avoid weekend completion and identical clock times on different days are rejected.
- `Tsk_Done_Change_Lock` [Change tracking]: A Done task is frozen (hours, project) and can only be reopened to In Progress.
- `Tsk_Labels_vs_Severity` [Picklist & multi-picklist logic]: Security-labelled tasks cannot be Minor, Database work needs Backend, and label counts are capped by severity.
- `Tsk_Progress_Hours_Model` [Math/trig/geo]: For billable tasks, reported progress may not deviate from actual/estimated hours by more than a status- and severity-based tolerance.
- `Tsk_Sprint_ISO_Calendar` [Date/Time engineering]: Non-blocker tasks must sit in sprint ceil(ISO week / 2), sprint must be whole and <= 27, and the ISO year cannot be older than last year.
- `Tsk_Ticket_Slug_Pattern` [String forensics]: Ticket ref must look like ABC-123, and the slug must be lowercase, space-free, not end with '-' and begin with the ticket prefix.

## Tooling

- `tools/generate.py`: regenerates metadata from `tools/model.py` and `tools/rules_*.py`.
- `tools/verify.py`: static checks (XML, parens, allowed functions, field refs, coverage). `--coverage` rewrites COVERAGE.md.
