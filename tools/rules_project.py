"""Validation rules for Project__c and Task_Item__c.
Each rule: (object, name, group, description, message, formula). Macros use @NAME@."""

MACROS = {
 "CODE_RE": "'PRJ-[0-9]{4}-[0-9]{4}-[A-Z]{2}'",
 "RANK_NEW": "CASE(TEXT(Status__c), 'Draft', 0, 'Planning', 1, 'Active', 2, 'On Hold', 2, 'Completed', 3, 'Cancelled', 3, -1)",
 "RANK_OLD": "CASE(TEXT(PRIORVALUE(Status__c)), 'Draft', 0, 'Planning', 1, 'Active', 2, 'On Hold', 2, 'Completed', 3, 'Cancelled', 3, -1)",
 "DIGITS": "SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(Phone__c, '-', ''), ' ', ''), '(', ''), ')', ''), '+', '')",
 "PARENT_CODE": "VLOOKUP($ObjectType.Project__c.Fields.Code__c, $ObjectType.Project__c.Fields.Name, Parent_Name_Ref__c)",
}

RULES = []
def R(obj, name, group, desc, msg, formula):
    RULES.append(dict(obj=obj, name=name, group=group, desc=desc, msg=msg, formula=formula.strip()))

P = "Project__c"
D = "Date/Time engineering"
S = "String forensics"
M = "Math/trig/geo"
PL = "Picklist & multi-picklist logic"
C = "Change tracking"
X = "Cross-object (VLOOKUP)"
G = "Mega-combo"

# ---------------- Date / Time ----------------
R(P, "Prj_Kickoff_ISO_Week_Alignment", D,
  "Non-draft projects must kick off in the same ISO year as the start date and within 2 ISO weeks of it.",
  "Kickoff must fall in the same ISO year and within 2 ISO weeks of the Start Date.",
  """
AND(
  NOT(ISBLANK(Kickoff_At__c)),
  NOT(ISBLANK(Start_Date__c)),
  NOT(ISPICKVAL(Status__c, 'Draft')),
  OR(
    ISOYEAR(DATEVALUE(Kickoff_At__c)) <> ISOYEAR(Start_Date__c),
    ABS(ISOWEEK(DATEVALUE(Kickoff_At__c)) - ISOWEEK(Start_Date__c)) > 2
  )
)""")

R(P, "Prj_Weekend_Start_Guard", D,
  "Weekend start dates are only allowed for Critical projects or on Jan 1, and never in Dec/Jan unless that exemption holds.",
  "Start Date falls on a weekend without an exemption.",
  """
AND(
  NOT(ISBLANK(Start_Date__c)),
  OR(WEEKDAY(Start_Date__c) = 1, WEEKDAY(Start_Date__c) = 7),
  NOT(OR(ISPICKVAL(Priority__c, 'Critical'), DAYOFYEAR(Start_Date__c) = 1)),
  CASE(MONTH(Start_Date__c), 12, 0, 1, 0, 1) = 1
)""")

R(P, "Prj_Timeline_Max_Months", D,
  "End date must not precede start and may not exceed start plus 12/24/36 months depending on priority (clamped by MIN/MAX).",
  "End Date is before Start Date or beyond the allowed horizon for this priority.",
  """
AND(
  NOT(OR(ISBLANK(Start_Date__c), ISBLANK(End_Date__c))),
  OR(
    End_Date__c < Start_Date__c,
    End_Date__c > ADDMONTHS(Start_Date__c, MIN(36, MAX(12, CASE(TEXT(Priority__c), 'Critical', 12, 'High', 24, 36))))
  )
)""")

R(P, "Prj_Epoch_Kickoff_Consistency", D,
  "Epoch Seconds must agree with Kickoff At within an hour, share its calendar year, and not sit more than 10 years ahead.",
  "Epoch Seconds does not match the Kickoff At timestamp.",
  """
AND(
  NOT(ISBLANK(Kickoff_At__c)),
  NOT(ISBLANK(Epoch_Seconds__c)),
  OR(
    ABS(UNIXTIMESTAMP(Kickoff_At__c) - Epoch_Seconds__c) > 3600,
    YEAR(DATEVALUE(FROMUNIXTIME(Epoch_Seconds__c))) <> YEAR(DATEVALUE(Kickoff_At__c)),
    FROMUNIXTIME(Epoch_Seconds__c) > NOW() + 3650
  )
)""")

R(P, "Prj_Standup_Time_Grid", D,
  "Standup time must sit on a 5-minute grid between 06:00 and 20:00, with no seconds/millis and no 12:00-12:29 slot.",
  "Standup Time must be on a 5-minute grid between 06:00 and 20:00 (not during 12:00-12:29).",
  """
AND(
  NOT(ISBLANK(Standup_Time__c)),
  OR(
    Standup_Time__c < TIMEVALUE('06:00:00.000'),
    Standup_Time__c >= TIMEVALUE('20:00:00.000'),
    MOD(MINUTE(Standup_Time__c), 5) <> 0,
    SECOND(Standup_Time__c) + MILLISECOND(Standup_Time__c) > 0,
    AND(HOUR(Standup_Time__c) = 12, MINUTE(Standup_Time__c) < 30)
  )
)""")

R(P, "Prj_Active_Kickoff_Freshness", D,
  "Active projects cannot kick off more than a day in the future, more than 2 years in the past, or later today than the current UTC time.",
  "Active project has an implausible Kickoff At.",
  """
AND(
  ISPICKVAL(Status__c, 'Active'),
  NOT(ISBLANK(Kickoff_At__c)),
  OR(
    Kickoff_At__c > NOW() + 1,
    TODAY() - DATEVALUE(Kickoff_At__c) > 730,
    AND(DATEVALUE(Kickoff_At__c) = TODAY(), TIMEVALUE(Kickoff_At__c) > TIMENOW())
  )
)""")

R(P, "Prj_Duration_Matches_Calendar", D,
  "Duration (seconds) cannot be negative or exceed the calendar span; day-or-longer durations must render with a day unit.",
  "Duration Secs is inconsistent with the Start/End dates.",
  """
AND(
  NOT(ISBLANK(Duration_Secs__c)),
  NOT(ISBLANK(Start_Date__c)),
  NOT(ISBLANK(End_Date__c)),
  OR(
    Duration_Secs__c < 0,
    CEILING(Duration_Secs__c / 86400) > (End_Date__c - Start_Date__c) + 1,
    AND(Duration_Secs__c >= 86400, NOT(CONTAINS(FORMATDURATION(Duration_Secs__c, TRUE), 'd')))
  )
)""")

R(P, "Prj_Kickoff_Datetime_Window", D,
  "Kickoff must lie between 7 days before 00:00:00 on the start date and 23:59:59 on the end date; completed projects must have enough elapsed hours.",
  "Kickoff At is outside the project window or too recent for a completed project.",
  """
AND(
  NOT(ISBLANK(Start_Date__c)),
  NOT(ISBLANK(End_Date__c)),
  NOT(ISBLANK(Kickoff_At__c)),
  OR(
    Kickoff_At__c < DATETIMEVALUE(TEXT(Start_Date__c) & ' 00:00:00') - 7,
    Kickoff_At__c > DATETIMEVALUE(TEXT(End_Date__c) & ' 23:59:59'),
    AND(
      ISPICKVAL(Status__c, 'Completed'),
      FLOOR((NOW() - Kickoff_At__c) * 24) < ROUND(NULLVALUE(Duration_Secs__c, 0) / 3600, 0)
    )
  )
)""")

# ---------------- String forensics ----------------
R(P, "Prj_Code_Format_Checksum", S,
  "Code must match PRJ-YYYY-NNNN-XX, the year must be sane, and the suffix must equal the uppercased first two letters of the name.",
  "Code must look like PRJ-YYYY-NNNN-XX with XX = first two letters of the name.",
  """
AND(
  NOT(ISBLANK(Code__c)),
  OR(
    NOT(REGEX(Code__c, @CODE_RE@)),
    IF(
      REGEX(Code__c, @CODE_RE@),
      OR(
        VALUE(MID(Code__c, 5, 4)) < 2000,
        VALUE(MID(Code__c, 5, 4)) > YEAR(TODAY()) + 1,
        RIGHT(Code__c, 2) <> UPPER(LEFT(SUBSTITUTE(Name, ' ', ''), 2))
      ),
      FALSE
    )
  )
)""")

R(P, "Prj_Name_Hygiene", S,
  "Names must be trimmed, free of double spaces, not start with a digit (ASCII 48-57), and approved names must be in title case.",
  "Project name fails hygiene checks (spacing, leading digit, casing, or length).",
  """
OR(
  Name <> TRIM(Name),
  FIND('  ', Name) > 0,
  AND(ASCII(LEFT(Name, 1)) >= 48, ASCII(LEFT(Name, 1)) <= 57),
  AND(Is_Approved__c, Name <> INITCAP(LOWER(Name))),
  LEN(Name) > 80
)""")

R(P, "Prj_Notes_Line_Discipline", S,
  "Notes may have at most 50 line breaks, no tab or leading-space characters, and cancelled projects need a real explanation.",
  "Notes violate line-break/whitespace rules or a cancelled project lacks an explanation.",
  """
OR(
  AND(ISPICKVAL(Status__c, 'Cancelled'), LEN(TRIM(BLANKVALUE(Notes__c, ''))) < 20),
  AND(
    NOT(ISBLANK(Notes__c)),
    OR(
      LEN(Notes__c) - LEN(SUBSTITUTE(Notes__c, BR(), '')) > 50,
      CONTAINS(Notes__c, CHR(9)),
      LEFT(Notes__c, 1) = CHR(32)
    )
  )
)""")

R(P, "Prj_Serial_Padding_Mirror", S,
  "Code serial must be zero-padded to 4 digits, may not be a non-zero palindrome, and zero serials are Draft-only.",
  "Code serial is not zero-padded, is a palindrome, or is 0000 on a non-draft project.",
  """
IF(
  REGEX(Code__c, @CODE_RE@),
  OR(
    LPAD(TEXT(VALUE(MID(Code__c, 10, 4))), 4, '0') <> MID(Code__c, 10, 4),
    AND(MID(Code__c, 10, 4) = REVERSE(MID(Code__c, 10, 4)), VALUE(MID(Code__c, 10, 4)) > 0),
    AND(VALUE(MID(Code__c, 10, 4)) = 0, NOT(ISPICKVAL(Status__c, 'Draft'))),
    RPAD(RIGHT(Code__c, 2), 4, '*') <> RPAD(UPPER(RIGHT(Code__c, 2)), 4, '*')
  ),
  FALSE
)""")

R(P, "Prj_Contact_Email_Forensics", S,
  "Contact email must be lowercase with a sane @ position, no '..' in the domain, no trailing dot, and external projects cannot use 'internal.' hosts.",
  "Contact Email fails structural checks.",
  """
AND(
  NOT(ISBLANK(Contact_Email__c)),
  OR(
    FIND('@', Contact_Email__c) < 2,
    LOWER(Contact_Email__c) <> Contact_Email__c,
    CONTAINS(MID(Contact_Email__c, MAX(1, FIND('@', Contact_Email__c)), 100), '..'),
    BEGINS(RIGHT(Contact_Email__c, MAX(0, LEN(Contact_Email__c) - FIND('@', Contact_Email__c))), '.'),
    RIGHT(Contact_Email__c, 1) = '.',
    AND(INCLUDES(Tags__c, 'External'), CONTAINS(Contact_Email__c, 'internal.'))
  )
)""")

R(P, "Prj_Phone_Digit_Forensics", S,
  "After stripping punctuation the phone must be numeric, 10-15 digits long, and an international '+' number cannot start with 0.",
  "Phone must contain 10-15 digits (punctuation allowed).",
  """
AND(
  NOT(ISBLANK(Phone__c)),
  OR(
    NOT(ISNUMBER(@DIGITS@)),
    LEN(@DIGITS@) < 10,
    LEN(@DIGITS@) > 15,
    AND(BEGINS(Phone__c, '+'), LEFT(@DIGITS@, 1) = '0')
  )
)""")

# ---------------- Math / trig / geo ----------------
R(P, "Prj_Risk_Curve_vs_Budget", M,
  "Unapproved projects whose sqrt(risk)*e^-completion*ln(risk+1) exceeds log10(budget) are too risky for their size.",
  "Risk score is too high for the budget and completion level of this unapproved project.",
  """
AND(
  NOT(ISNULL(Risk_Score__c)),
  Risk_Score__c > 0,
  NOT(ISBLANK(Budget__c)),
  NOT(Is_Approved__c),
  ROUND(SQRT(Risk_Score__c) * EXP(-NULLVALUE(Completion_Pct__c, 0)) * LN(Risk_Score__c + 1), 3) > LOG(MAX(10, Budget__c))
)""")

R(P, "Prj_Burn_Rate_Proration", M,
  "Spend (as truncated percent of budget) may not exceed the time-prorated share of the timeline plus a priority-based allowance.",
  "Spent is burning faster than the timeline and priority allow.",
  """
AND(
  NOT(ISBLANK(Budget__c)),
  Budget__c > 0,
  NOT(ISBLANK(Spent__c)),
  NOT(ISBLANK(Start_Date__c)),
  NOT(ISBLANK(End_Date__c)),
  NOT(Is_Approved__c),
  TRUNC(Spent__c / MAX(1, Budget__c) * 100, 0) >
    FLOOR(100 * MIN(1, MAX(0, (TODAY() - Start_Date__c) / MAX(1, End_Date__c - Start_Date__c)))
      + CASE(TEXT(Priority__c), 'Critical', 30, 'High', 20, 10))
)""")

R(P, "Prj_Round_Number_Discipline", M,
  "Non-draft budgets of 10k+ must be whole thousands, completion must move in 5% steps, and approved spend must be whole dollars.",
  "Budget, Completion or Spent breaks the rounding conventions.",
  """
AND(
  NOT(ISPICKVAL(Status__c, 'Draft')),
  OR(
    AND(Budget__c >= 10000, MOD(MFLOOR(Budget__c), 1000) <> 0),
    AND(NOT(ISBLANK(Completion_Pct__c)), MOD(ROUND(Completion_Pct__c * 100, 0), 5) <> 0),
    AND(Is_Approved__c, NOT(ISBLANK(Spent__c)), TRUNC(Spent__c, 0) <> Spent__c, MCEILING(Spent__c) > MFLOOR(Spent__c))
  )
)""")

R(P, "Prj_Regulated_Geo_Fence", M,
  "Regulated projects must have a location within 3000 miles of the (37.7749, -122.4194) reference point.",
  "Regulated projects must be located within 3000 miles of the reference HQ.",
  """
AND(
  INCLUDES(Tags__c, 'Regulated'),
  NOT(ISBLANK(Location__latitude__s)),
  NOT(ISBLANK(Location__longitude__s)),
  DISTANCE(Location__c, GEOLOCATION(37.7749, -122.4194), 'mi') > 3000
)""")

# ---------------- Picklists ----------------
R(P, "Prj_Status_Priority_Matrix", PL,
  "A CASE-ranked status ladder gates Critical priority, completion percent, drafts, high-priority approval and on-hold notes.",
  "Status, priority, completion, approval and notes are not consistent.",
  """
OR(
  AND(ISPICKVAL(Priority__c, 'Critical'), @RANK_NEW@ < 1),
  AND(ISPICKVAL(Status__c, 'Completed'), NULLVALUE(Completion_Pct__c, 0) < 1),
  AND(ISPICKVAL(Status__c, 'Draft'), NULLVALUE(Completion_Pct__c, 0) > 0.1),
  AND(@RANK_NEW@ >= 2, NOT(Is_Approved__c), CASE(TEXT(Priority__c), 'High', 1, 'Critical', 1, 0) = 1),
  AND(ISPICKVAL(Status__c, 'On Hold'), ISBLANK(Notes__c))
)""")

R(P, "Prj_Tags_Compliance", PL,
  "Regulated projects must be approved, carry at most 3 tags, avoid the Pilot+Strategic combo and have a contact email.",
  "Regulated projects require approval, at most 3 tags, no Pilot+Strategic combo, and a contact email.",
  """
AND(
  INCLUDES(Tags__c, 'Regulated'),
  OR(
    NOT(Is_Approved__c),
    PICKLISTCOUNT(Tags__c) > 3,
    AND(INCLUDES(Tags__c, 'Pilot'), INCLUDES(Tags__c, 'Strategic')),
    ISBLANK(Contact_Email__c)
  )
)""")

R(P, "Prj_Tag_Count_vs_Priority", PL,
  "The number of tags must be within a priority-driven ceiling; High/Critical need at least one tag; External+Internal needs Regulated.",
  "Tag count or tag combination does not fit the project priority.",
  """
OR(
  AND(ISBLANK(Tags__c), OR(ISPICKVAL(Priority__c, 'High'), ISPICKVAL(Priority__c, 'Critical'))),
  AND(NOT(ISBLANK(Tags__c)),
    OR(
      PICKLISTCOUNT(Tags__c) > CASE(TEXT(Priority__c), 'Low', 1, 'Medium', 2, 'High', 3, 5),
      AND(INCLUDES(Tags__c, 'External'), INCLUDES(Tags__c, 'Internal'), NOT(INCLUDES(Tags__c, 'Regulated')))
    )
  )
)""")

# ---------------- Change tracking ----------------
R(P, "Prj_Status_Regression_Lock", C,
  "Status may not drop two or more ladder ranks, Cancelled can only reopen to Planning, and Completed requires approval.",
  "This status transition is not allowed.",
  """
AND(
  NOT(ISNEW()),
  ISCHANGED(Status__c),
  OR(
    @RANK_OLD@ - @RANK_NEW@ >= 2,
    AND(ISPICKVAL(PRIORVALUE(Status__c), 'Cancelled'), NOT(ISPICKVAL(Status__c, 'Planning'))),
    AND(ISPICKVAL(Status__c, 'Completed'), NOT(Is_Approved__c))
  )
)""")

R(P, "Prj_Budget_Change_Control", C,
  "Budget edits cannot fall below spend, approved budgets may move at most 20%, and completed projects are frozen.",
  "Budget change violates change-control rules.",
  """
AND(
  NOT(ISNEW()),
  ISCHANGED(Budget__c),
  OR(
    Budget__c < NULLVALUE(Spent__c, 0),
    AND(Is_Approved__c, ABS(Budget__c - BLANKVALUE(PRIORVALUE(Budget__c), 0)) > 0.2 * MAX(1, BLANKVALUE(PRIORVALUE(Budget__c), 0))),
    AND(ISPICKVAL(Status__c, 'Completed'), Budget__c <> PRIORVALUE(Budget__c))
  )
)""")

R(P, "Prj_Clone_Reset_Guard", C,
  "A cloned project must start clean: not approved, no spend, Draft, 0% complete and no stale kickoff or epoch.",
  "Cloned projects must be reset (Draft, unapproved, no spend, no stale dates).",
  """
AND(
  ISNEW(),
  ISCLONE(),
  OR(
    Is_Approved__c,
    NULLVALUE(Spent__c, 0) > 0,
    NOT(ISPICKVAL(Status__c, 'Draft')),
    NULLVALUE(Completion_Pct__c, 0) > 0,
    AND(NOT(ISBLANK(Kickoff_At__c)), Kickoff_At__c < NOW()),
    AND(NOT(ISBLANK(Epoch_Seconds__c)), Epoch_Seconds__c < UNIXTIMESTAMP(NOW()))
  )
)""")

R(P, "Prj_Approved_Immutable_Core", C,
  "Once approved, the code, account and parent are frozen and dates may only be tightened (end earlier, start later).",
  "Approved projects have locked identity fields and may only tighten dates.",
  """
IF(
  ISNEW(),
  FALSE,
  AND(
    PRIORVALUE(Is_Approved__c),
    OR(
      ISCHANGED(Code__c),
      ISCHANGED(Account__c),
      ISCHANGED(Parent_Project__c),
      AND(ISCHANGED(End_Date__c), End_Date__c > PRIORVALUE(End_Date__c)),
      AND(ISCHANGED(Start_Date__c), Start_Date__c < PRIORVALUE(Start_Date__c))
    )
  )
)""")

# ---------------- Cross object ----------------
R(P, "Prj_Parent_Code_Year_Order", X,
  "A child project's code year may not precede its parent's, and it cannot reuse the parent's code (VLOOKUP on the parent project's Name).",
  "Child project code must not predate or equal its parent's code.",
  """
AND(
  NOT(ISBLANK(Parent_Name_Ref__c)),
  REGEX(Code__c, @CODE_RE@),
  REGEX(@PARENT_CODE@, @CODE_RE@),
  OR(
    VALUE(MID(@PARENT_CODE@, 5, 4)) > VALUE(MID(Code__c, 5, 4)),
    @PARENT_CODE@ = Code__c
  )
)""")

R(P, "Prj_Region_Rate_Lookup", X,
  "Regulated projects need a Region Key that exists as a Rate Table record (VLOOKUP by Name) with an active region and a rate no higher than 25%.",
  "Regulated project needs a Region Key matching an active Rate Table row with rate <= 25%.",
  """
AND(
  INCLUDES(Tags__c, 'Regulated'),
  OR(
    ISBLANK(Region_Key__c),
    LEN(TRIM(Region_Key__c)) <> 3,
    AND(NOT(ISBLANK(Region_Key__c)),
      OR(
        ISBLANK(VLOOKUP($ObjectType.Rate_Table__c.Fields.Region__c, $ObjectType.Rate_Table__c.Fields.Name, UPPER(Region_Key__c))),
        NULLVALUE(VLOOKUP($ObjectType.Rate_Table__c.Fields.Rate__c, $ObjectType.Rate_Table__c.Fields.Name, UPPER(Region_Key__c)), 1) > 0.25
      )
    )
  )
)""")

# ---------------- Mega ----------------
R(P, "Prj_Mega_Launch_Readiness", G,
  "Active projects must pass a launch-readiness gauntlet: code format, ISO-week parity, calendar span, burn rate, tags-per-priority, regulated contacts and a risk/completion balance.",
  "Active project failed the launch-readiness checks.",
  """
AND(
  ISPICKVAL(Status__c, 'Active'),
  NOT(ISBLANK(Start_Date__c)),
  NOT(ISBLANK(End_Date__c)),
  OR(
    NOT(REGEX(BLANKVALUE(Code__c, '-'), @CODE_RE@)),
    AND(MOD(ISOWEEK(Start_Date__c), 2) = 1, NOT(Is_Approved__c)),
    End_Date__c - Start_Date__c < CEILING(NULLVALUE(Duration_Secs__c, 0) / 86400),
    ROUND(NULLVALUE(Spent__c, 0) / MAX(1, NULLVALUE(Budget__c, 0)), 2)
      > MIN(1, MAX(0.05, (TODAY() - Start_Date__c) / MAX(1, End_Date__c - Start_Date__c))) + 0.15,
    CASE(TEXT(Priority__c), 'Critical', 2, 'High', 1, 0) > PICKLISTCOUNT(Tags__c),
    AND(INCLUDES(Tags__c, 'Regulated'), OR(ISBLANK(Contact_Email__c), ISBLANK(Phone__c))),
    ABS(NULLVALUE(Risk_Score__c, 0) - 10 * (1 - NULLVALUE(Completion_Pct__c, 0))) > 7
  )
)""")

R(P, "Prj_Mega_Code_Forensics", G,
  "Code suffix must equal the initials of the first two name words, serial must not mirror the year, the epoch year must equal the code year, and approved codes must end in a letter.",
  "Project code failed the forensic cross-check against name, epoch and approval state.",
  """
AND(
  NOT(ISBLANK(Code__c)),
  NOT(ISBLANK(Epoch_Seconds__c)),
  REGEX(Code__c, @CODE_RE@),
  OR(
    RIGHT(Code__c, 2) <> (UPPER(LEFT(Name, 1)) & UPPER(MID(Name, FIND(' ', Name) + 1, 1))),
    MID(Code__c, 10, 4) = REVERSE(MID(Code__c, 5, 4)),
    YEAR(DATEVALUE(FROMUNIXTIME(Epoch_Seconds__c))) <> VALUE(MID(Code__c, 5, 4)),
    MID(Code__c, 14, 1) <> CHR(45),
    AND(Is_Approved__c, ASCII(RIGHT(Code__c, 1)) < 65)
  )
)""")

R(P, "Prj_Session_Guard", G,
  "Approved Completed projects cannot be created by a session-less context (GETSESSIONID empty) or carry a line break in the name.",
  "Approved, completed projects cannot be created from a session-less context.",
  """
AND(
  ISNEW(),
  Is_Approved__c,
  ISPICKVAL(Status__c, 'Completed'),
  OR(LEN(GETSESSIONID()) = 0, CONTAINS(Name, BR()))
)""")

# ================= Task_Item__c =================
T_ = "Task_Item__c"
R(T_, "Tsk_Completion_Timeline", D,
  "Completion must follow start, hours cannot exceed wall-clock time, only Done tasks have completion, Minor tasks avoid weekend completion and identical clock times on different days are rejected.",
  "Task timeline is inconsistent.",
  """
AND(
  NOT(ISBLANK(Started_At__c)),
  NOT(ISBLANK(Completed_At__c)),
  OR(
    Completed_At__c < Started_At__c,
    NULLVALUE(Actual_Hours__c, 0) > ROUND((Completed_At__c - Started_At__c) * 24, 2) + 0.5,
    NOT(ISPICKVAL(Status__c, 'Done')),
    AND(ISPICKVAL(Severity__c, 'Minor'), OR(WEEKDAY(DATEVALUE(Completed_At__c)) = 1, WEEKDAY(DATEVALUE(Completed_At__c)) = 7)),
    AND(
      HOUR(TIMEVALUE(Started_At__c)) = HOUR(TIMEVALUE(Completed_At__c)),
      MINUTE(TIMEVALUE(Started_At__c)) = MINUTE(TIMEVALUE(Completed_At__c)),
      SECOND(TIMEVALUE(Started_At__c)) = SECOND(TIMEVALUE(Completed_At__c)),
      DATEVALUE(Started_At__c) <> DATEVALUE(Completed_At__c)
    )
  )
)""")

R(T_, "Tsk_Ticket_Slug_Pattern", S,
  "Ticket ref must look like ABC-123, and the slug must be lowercase, space-free, not end with '-' and begin with the ticket prefix.",
  "Ticket Ref or Slug has an invalid shape.",
  """
AND(
  NOT(ISBLANK(Ticket_Ref__c)),
  NOT(ISBLANK(Slug__c)),
  OR(
    NOT(REGEX(Ticket_Ref__c, '[A-Z]{2,5}-[0-9]{1,7}')),
    NOT(BEGINS(Slug__c, LOWER(LEFT(Ticket_Ref__c, MAX(0, FIND('-', Ticket_Ref__c) - 1))))),
    Slug__c <> LOWER(Slug__c),
    CONTAINS(Slug__c, ' '),
    RIGHT(Slug__c, 1) = '-'
  )
)""")

R(T_, "Tsk_Sprint_ISO_Calendar", D,
  "Non-blocker tasks must sit in sprint ceil(ISO week / 2), sprint must be whole and <= 27, and the ISO year cannot be older than last year.",
  "Sprint Number does not match the due date's ISO calendar.",
  """
AND(
  NOT(ISBLANK(Sprint_Number__c)),
  NOT(ISBLANK(Due_Date__c)),
  NOT(ISPICKVAL(Severity__c, 'Blocker')),
  OR(
    Sprint_Number__c <> CEILING(ISOWEEK(Due_Date__c) / 2),
    MOD(Sprint_Number__c, 1) <> 0,
    Sprint_Number__c > 27,
    ISOYEAR(Due_Date__c) < YEAR(TODAY()) - 1
  )
)""")

R(T_, "Tsk_Blocker_Due_Month_End", D,
  "Blocker tasks cannot be due on the last day of a month, on a Sunday, or before the end of last month.",
  "Blocker tasks cannot be due on month end, on a Sunday, or in the past.",
  """
AND(
  ISPICKVAL(Severity__c, 'Blocker'),
  NOT(ISBLANK(Due_Date__c)),
  OR(
    Due_Date__c = ADDMONTHS(DATE(YEAR(Due_Date__c), MONTH(Due_Date__c), 1), 1) - 1,
    Due_Date__c < TODAY() - DAY(TODAY()),
    WEEKDAY(Due_Date__c) = 1
  )
)""")

R(T_, "Tsk_Labels_vs_Severity", PL,
  "Security-labelled tasks cannot be Minor, Database work needs Backend, and label counts are capped by severity.",
  "Labels and severity are not consistent.",
  """
AND(
  NOT(ISBLANK(Labels__c)),
  OR(
    AND(INCLUDES(Labels__c, 'Security'), ISPICKVAL(Severity__c, 'Minor')),
    AND(INCLUDES(Labels__c, 'Database'), NOT(INCLUDES(Labels__c, 'Backend'))),
    PICKLISTCOUNT(Labels__c) > IF(ISPICKVAL(Severity__c, 'Blocker'), 5, 3)
  )
)""")

R(T_, "Tsk_Progress_Hours_Model", M,
  "For billable tasks, reported progress may not deviate from actual/estimated hours by more than a status- and severity-based tolerance.",
  "Progress deviates too far from the hours burned.",
  """
AND(
  Is_Billable__c,
  NULLVALUE(Estimated_Hours__c, 0) > 0,
  NOT(ISBLANK(Progress__c)),
  ABS(Progress__c - MIN(1, NULLVALUE(Actual_Hours__c, 0) / MAX(0.01, NULLVALUE(Estimated_Hours__c, 0))))
    > IF(ISPICKVAL(Status__c, 'Blocked'), 0.75, CASE(TEXT(Severity__c), 'Blocker', 0.3, 'Major', 0.4, 0.5))
)""")

R(T_, "Tsk_Done_Change_Lock", C,
  "A Done task is frozen (hours, project) and can only be reopened to In Progress.",
  "Done tasks are locked; reopen to In Progress first.",
  """
AND(
  NOT(ISNEW()),
  ISPICKVAL(PRIORVALUE(Status__c), 'Done'),
  OR(
    ISCHANGED(Estimated_Hours__c),
    ISCHANGED(Actual_Hours__c),
    ISCHANGED(Project__c),
    AND(ISCHANGED(Status__c), NOT(ISPICKVAL(Status__c, 'In Progress')))
  )
)""")

R(T_, "Tsk_Assignee_Email_Domain_Case", S,
  "Assignee email must be lowercase, contain exactly one '@' (CHR(64)), and its local part may not be longer than 40 characters.",
  "Assignee Email must be lowercase with a single @ and a short local part.",
  """
AND(
  NOT(ISBLANK(Assignee_Email__c)),
  OR(
    Assignee_Email__c <> LOWER(Assignee_Email__c),
    LEN(Assignee_Email__c) - LEN(SUBSTITUTE(Assignee_Email__c, CHR(64), '')) <> 1,
    FIND(CHR(64), Assignee_Email__c) > 41
  )
)""")
