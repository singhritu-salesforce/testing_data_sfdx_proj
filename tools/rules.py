"""Validation rules (source of truth). 14 deep-nested, function-dense rules."""
MACROS = {
 "CODE_RE": "'PRJ-[0-9]{4}-[0-9]{4}-[A-Z]{2}'",
 "RANK_NEW": "CASE(TEXT(Status__c), 'Draft', 0, 'Planning', 1, 'Active', 2, 'On Hold', 2, 'Completed', 3, 'Cancelled', 3, -1)",
 "RANK_OLD": "CASE(TEXT(PRIORVALUE(Status__c)), 'Draft', 0, 'Planning', 1, 'Active', 2, 'On Hold', 2, 'Completed', 3, 'Cancelled', 3, -1)",
 "HAV": "(SIN((Destination__latitude__s - Origin__latitude__s) * PI() / 360) ^ 2 + COS(Origin__latitude__s * PI() / 180) * COS(Destination__latitude__s * PI() / 180) * SIN((Destination__longitude__s - Origin__longitude__s) * PI() / 360) ^ 2)",
 "RT_RATE": "VLOOKUP($ObjectType.Rate_Table__c.Fields.Rate__c, $ObjectType.Rate_Table__c.Fields.Name, UPPER(Region_Key__c))",
 "RT_REGION": "VLOOKUP($ObjectType.Rate_Table__c.Fields.Region__c, $ObjectType.Rate_Table__c.Fields.Name, UPPER(Region_Key__c))",
 "MGR_SCORE": "VLOOKUP($ObjectType.Employee_Record__c.Fields.Performance_Score__c, $ObjectType.Employee_Record__c.Fields.Name, Manager_Name_Ref__c)",
 "PRJ_RISK": "VLOOKUP($ObjectType.Project__c.Fields.Risk_Score__c, $ObjectType.Project__c.Fields.Name, Project_Name_Ref__c)",
}
D = "Date/Time engineering"; S = "String forensics"; M = "Math/trig/geo"; PLG = "Picklist & multi-picklist logic"
C = "Change tracking"; X = "Cross-object (VLOOKUP)"; G = "Mega-combo"
RULES = []
def R(obj, name, group, desc, msg, formula):
    RULES.append(dict(obj=obj, name=name, group=group, desc=desc, msg=msg, formula=formula.strip()))

P = "Project__c"
R(P, "Prj_Calendar_Engine", D,
  "Non-draft projects must start and kick off in the same ISO year within a priority-driven number of ISO weeks, end within a clamped month horizon, avoid unexempted weekend starts, and avoid year-end starts that fall in the wrong quarter-month window.",
  "Project calendar (ISO week/year, horizon, weekend or year-end start) is not allowed.",
  """
AND(
  NOT(ISBLANK(Start_Date__c)),
  NOT(ISBLANK(End_Date__c)),
  NOT(ISBLANK(Kickoff_At__c)),
  IF(
    ISPICKVAL(Status__c, 'Draft'),
    FALSE,
    OR(
      End_Date__c < Start_Date__c,
      ISOYEAR(DATEVALUE(Kickoff_At__c)) <> ISOYEAR(Start_Date__c),
      ABS(ISOWEEK(DATEVALUE(Kickoff_At__c)) - ISOWEEK(Start_Date__c)) > CASE(TEXT(Priority__c), 'Critical', 1, 'High', 2, 4),
      End_Date__c > ADDMONTHS(Start_Date__c, MIN(36, MAX(12, CASE(TEXT(Priority__c), 'Critical', 12, 'High', 24, 36)))),
      AND(
        OR(WEEKDAY(Start_Date__c) = 1, WEEKDAY(Start_Date__c) = 7),
        NOT(OR(ISPICKVAL(Priority__c, 'Critical'), DAYOFYEAR(Start_Date__c) = 1)),
        IF(
          CASE(MONTH(Start_Date__c), 12, 1, 1, 1, 0) = 1,
          DAY(Start_Date__c) > 20,
          DATE(YEAR(Start_Date__c), MONTH(Start_Date__c), 1) < ADDMONTHS(TODAY(), -120)
        )
      )
    )
  )
)""")

R(P, "Prj_Time_Epoch_Forensics", D,
  "Epoch seconds must agree with Kickoff At (year, hour, 5-minute grid, no stale midnight), durations must render with day units, standup times must sit in a lunch-free window, and active kickoffs cannot be in the future.",
  "Kickoff/Epoch/Duration/Standup time values are inconsistent.",
  """
AND(
  NOT(ISBLANK(Kickoff_At__c)),
  OR(
    AND(
      NOT(ISBLANK(Epoch_Seconds__c)),
      OR(
        ABS(UNIXTIMESTAMP(Kickoff_At__c) - Epoch_Seconds__c) > 3600,
        YEAR(DATEVALUE(FROMUNIXTIME(Epoch_Seconds__c))) <> YEAR(DATEVALUE(Kickoff_At__c)),
        IF(
          FROMUNIXTIME(Epoch_Seconds__c) > NOW() + 3650,
          TRUE,
          DATETIMEVALUE(TEXT(DATEVALUE(Kickoff_At__c)) & ' 00:00:00') > Kickoff_At__c
        )
      )
    ),
    AND(
      ISPICKVAL(Status__c, 'Active'),
      OR(
        Kickoff_At__c > NOW() + 1,
        AND(DATEVALUE(Kickoff_At__c) = TODAY(), TIMEVALUE(Kickoff_At__c) > TIMENOW()),
        MOD(MINUTE(TIMEVALUE(Kickoff_At__c)), 5) + SECOND(TIMEVALUE(Kickoff_At__c)) + MILLISECOND(TIMEVALUE(Kickoff_At__c)) > 0
      )
    ),
    AND(
      NOT(ISBLANK(Duration_Secs__c)),
      OR(
        Duration_Secs__c < 0,
        AND(Duration_Secs__c >= 86400, NOT(CONTAINS(FORMATDURATION(Duration_Secs__c, TRUE), 'd'))),
        CEILING(Duration_Secs__c / 86400) > NULLVALUE(End_Date__c - Start_Date__c, 9999) + 1
      )
    ),
    AND(
      NOT(ISBLANK(Standup_Time__c)),
      OR(
        Standup_Time__c < TIMEVALUE('06:00:00.000'),
        HOUR(Standup_Time__c) >= 20,
        AND(HOUR(Standup_Time__c) = 12, MINUTE(Standup_Time__c) < 30)
      )
    )
  )
)""")

R(P, "Prj_Code_Name_Forensics", S,
  "Code must match PRJ-YYYY-NNNN-XX with a sane year, XX equal to the name initials, a zero-padded non-palindromic serial and a hyphen at the right offset; names, notes and contact email get whitespace, case, ASCII, line-break and structural checks.",
  "Project code, name, notes or contact email failed the string forensics checks.",
  """
OR(
  AND(
    NOT(ISBLANK(Code__c)),
    IF(
      REGEX(Code__c, @CODE_RE@),
      OR(
        VALUE(MID(Code__c, 5, 4)) < 2000,
        VALUE(MID(Code__c, 5, 4)) > YEAR(TODAY()) + 1,
        RIGHT(Code__c, 2) <> (UPPER(LEFT(Name, 1)) & UPPER(MID(Name, FIND(' ', Name) + 1, 1))),
        LPAD(TEXT(VALUE(MID(Code__c, 10, 4))), 4, '0') <> MID(Code__c, 10, 4),
        AND(MID(Code__c, 10, 4) = REVERSE(MID(Code__c, 10, 4)), VALUE(MID(Code__c, 10, 4)) > 0),
        RPAD(RIGHT(Code__c, 2), 4, '*') <> RPAD(UPPER(RIGHT(Code__c, 2)), 4, '*'),
        ASCII(MID(Code__c, 14, 1)) <> ASCII(CHR(45)),
        AND(Is_Approved__c, ASCII(RIGHT(Code__c, 1)) < 65)
      ),
      TRUE
    )
  ),
  Name <> TRIM(Name),
  AND(Is_Approved__c, Name <> INITCAP(LOWER(Name))),
  AND(ASCII(LEFT(Name, 1)) >= 48, ASCII(LEFT(Name, 1)) <= 57),
  AND(
    NOT(ISBLANK(Notes__c)),
    OR(
      LEN(Notes__c) - LEN(SUBSTITUTE(Notes__c, BR(), '')) > 50,
      CONTAINS(Notes__c, CHR(9)),
      LEFT(Notes__c, 1) = CHR(32)
    )
  ),
  AND(ISPICKVAL(Status__c, 'Cancelled'), LEN(TRIM(BLANKVALUE(Notes__c, ''))) < 20),
  AND(
    NOT(ISBLANK(Contact_Email__c)),
    OR(
      FIND('@', Contact_Email__c) < 2,
      LOWER(Contact_Email__c) <> Contact_Email__c,
      CONTAINS(MID(Contact_Email__c, MAX(1, FIND('@', Contact_Email__c)), 100), '..'),
      BEGINS(RIGHT(Contact_Email__c, MAX(0, LEN(Contact_Email__c) - FIND('@', Contact_Email__c))), '.')
    )
  ),
  AND(
    NOT(ISBLANK(Phone__c)),
    NOT(ISNUMBER(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(Phone__c, '-', ''), ' ', ''), '(', ''), ')', ''), '+', '')))
  )
)""")

R(P, "Prj_Risk_Burn_Math", M,
  "Unapproved projects face a log/exp/sqrt risk curve against budget, a time-prorated burn-rate ceiling (TRUNC/FLOOR/MIN/MAX), and whole-thousand budget and 5% completion step rules; null risk is skipped via ISNULL.",
  "Risk, burn rate, budget rounding or completion step breaks the math rules.",
  """
AND(
  NOT(Is_Approved__c),
  NOT(ISNULL(Risk_Score__c)),
  Risk_Score__c > 0,
  NOT(ISBLANK(Budget__c)),
  OR(
    ROUND(SQRT(Risk_Score__c) * EXP(-NULLVALUE(Completion_Pct__c, 0)) * LN(Risk_Score__c + 1), 3) > LOG(MAX(10, Budget__c)),
    AND(
      Budget__c > 0,
      NOT(ISBLANK(Start_Date__c)),
      NOT(ISBLANK(End_Date__c)),
      TRUNC(NULLVALUE(Spent__c, 0) / MAX(1, Budget__c) * 100, 0) >
        FLOOR(100 * MIN(1, MAX(0, (TODAY() - Start_Date__c) / MAX(1, End_Date__c - Start_Date__c))) + CASE(TEXT(Priority__c), 'Critical', 30, 'High', 20, 10))
    ),
    IF(
      NOT(ISPICKVAL(Status__c, 'Draft')),
      OR(
        AND(Budget__c >= 10000, MOD(MFLOOR(Budget__c), 1000) <> 0),
        AND(NOT(ISBLANK(Completion_Pct__c)), MOD(ROUND(Completion_Pct__c * 100, 0), 5) <> 0),
        MCEILING(NULLVALUE(Spent__c, 0)) - MFLOOR(NULLVALUE(Spent__c, 0)) > 1
      ),
      FALSE
    )
  )
)""")

R(P, "Prj_Tags_Status_Matrix", PLG,
  "Multi-picklist Tags are checked against Priority, Status (ranked by a CASE ladder), approval, notes and contact data, with count ceilings and forbidden combinations.",
  "Tags, priority, status, approval and notes are not consistent.",
  """
OR(
  AND(
    INCLUDES(Tags__c, 'Regulated'),
    OR(
      NOT(Is_Approved__c),
      PICKLISTCOUNT(Tags__c) > 3,
      AND(INCLUDES(Tags__c, 'Pilot'), INCLUDES(Tags__c, 'Strategic')),
      ISBLANK(Contact_Email__c)
    )
  ),
  IF(
    ISBLANK(Tags__c),
    OR(ISPICKVAL(Priority__c, 'High'), ISPICKVAL(Priority__c, 'Critical')),
    OR(
      PICKLISTCOUNT(Tags__c) > CASE(TEXT(Priority__c), 'Low', 1, 'Medium', 2, 'High', 3, 5),
      AND(INCLUDES(Tags__c, 'External'), INCLUDES(Tags__c, 'Internal'), NOT(INCLUDES(Tags__c, 'Regulated')))
    )
  ),
  AND(ISPICKVAL(Priority__c, 'Critical'), @RANK_NEW@ < 1),
  AND(ISPICKVAL(Status__c, 'Completed'), NULLVALUE(Completion_Pct__c, 0) < 1),
  AND(@RANK_NEW@ = 2, NOT(Is_Approved__c), CASE(TEXT(Priority__c), 'High', 1, 'Critical', 1, 0) = 1),
  AND(ISPICKVAL(Status__c, 'On Hold'), ISBLANK(Notes__c))
)""")

R(P, "Prj_Change_Control", C,
  "Inserts and clones must start clean; updates enforce a status ladder, a budget change policy and a frozen identity once approved, using ISNEW, ISCLONE, ISCHANGED and PRIORVALUE.",
  "This change violates the project change-control policy.",
  """
IF(
  ISNEW(),
  IF(
    ISCLONE(),
    OR(
      Is_Approved__c,
      NULLVALUE(Spent__c, 0) > 0,
      NOT(ISPICKVAL(Status__c, 'Draft')),
      AND(NOT(ISBLANK(Kickoff_At__c)), Kickoff_At__c < NOW()),
      AND(NOT(ISBLANK(Epoch_Seconds__c)), Epoch_Seconds__c < UNIXTIMESTAMP(NOW()))
    ),
    AND(Is_Approved__c, ISPICKVAL(Status__c, 'Completed'), LEN(GETSESSIONID()) = 0)
  ),
  OR(
    AND(
      ISCHANGED(Status__c),
      OR(
        @RANK_OLD@ - @RANK_NEW@ >= 2,
        AND(ISPICKVAL(PRIORVALUE(Status__c), 'Cancelled'), NOT(ISPICKVAL(Status__c, 'Planning'))),
        AND(ISPICKVAL(Status__c, 'Completed'), NOT(Is_Approved__c))
      )
    ),
    AND(
      ISCHANGED(Budget__c),
      OR(
        Budget__c < NULLVALUE(Spent__c, 0),
        AND(Is_Approved__c, ABS(Budget__c - BLANKVALUE(PRIORVALUE(Budget__c), 0)) > 0.2 * MAX(1, BLANKVALUE(PRIORVALUE(Budget__c), 0))),
        AND(ISPICKVAL(Status__c, 'Completed'), Budget__c <> PRIORVALUE(Budget__c))
      )
    ),
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
  )
)""")

R(P, "Prj_Region_Geo_Currency_Gate", X,
  "Regulated projects need a Region Key resolving through VLOOKUP into an active Rate Table row with a capped rate, a location within 3000 miles of a reference point, an 18-char CASESAFEID account, a positive currency rate and a line-break-free name.",
  "Regulated project failed the region, geo, currency or identity gate.",
  """
AND(
  INCLUDES(Tags__c, 'Regulated'),
  OR(
    ISBLANK(Region_Key__c),
    IF(
      LEN(TRIM(Region_Key__c)) <> 3,
      TRUE,
      OR(
        ISBLANK(@RT_REGION@),
        NULLVALUE(@RT_RATE@, 1) > 0.25
      )
    ),
    AND(
      NOT(ISBLANK(Location__latitude__s)),
      NOT(ISBLANK(Location__longitude__s)),
      DISTANCE(Location__c, GEOLOCATION(37.7749, -122.4194), 'mi') > 3000
    ),
    CURRENCYRATE('USD') <= 0,
    AND(NOT(ISBLANK(Account__c)), LEN(CASESAFEID(Account__c)) <> 18),
    CONTAINS(Name, BR())
  )
)""")

SH = "Shipment__c"
R(SH, "Shp_Trig_Geometry", M,
  "Haversine (SIN/COS/ATAN2/SQRT/PI) must agree with DISTANCE for international shipments; box dimensions pass ATAN/ASIN/ACOS/TAN sanity bands; volume and density pass LOG/EXP checks; transit speed must be physically possible.",
  "Shipment geometry, volume/density or transit speed is implausible.",
  """
AND(
  NOT(ISBLANK(Origin__latitude__s)),
  NOT(ISBLANK(Destination__latitude__s)),
  OR(
    AND(
      Is_International__c,
      ABS(3958.8 * 2 * ATAN2(SQRT(@HAV@), SQRT(1 - @HAV@)) - DISTANCE(Origin__c, Destination__c, 'mi')) > 0.05 * MAX(1, DISTANCE(Origin__c, Destination__c, 'mi'))
    ),
    AND(
      NULLVALUE(Length_Cm__c, 0) > 0,
      NULLVALUE(Width_Cm__c, 0) > 0,
      NOT(ISBLANK(Height_Cm__c)),
      OR(
        ATAN(Height_Cm__c / Length_Cm__c) * 180 / PI() > 80,
        ASIN(MIN(1, Width_Cm__c / MAX(Length_Cm__c, Width_Cm__c, Height_Cm__c))) < ACOS(0.99),
        ROUND(TAN(ATAN(Width_Cm__c / Length_Cm__c)) * Length_Cm__c, 1) <> ROUND(Width_Cm__c, 1),
        AND(
          NULLVALUE(Volume_M3__c, 0) > 0,
          OR(
            ABS(Volume_M3__c - Length_Cm__c * Width_Cm__c * Height_Cm__c / 1000000) > 0.02 * Volume_M3__c,
            LOG(NULLVALUE(Weight_Kg__c, 0) / Volume_M3__c + 1) > LOG(20000),
            NULLVALUE(Weight_Kg__c, 0) / Volume_M3__c < EXP(0)
          )
        )
      )
    ),
    AND(
      NULLVALUE(Transit_Seconds__c, 0) > 0,
      DISTANCE(Origin__c, Destination__c, 'mi') / (Transit_Seconds__c / 3600) > IF(ISPICKVAL(Service_Level__c, 'Ground'), 80, 600)
    )
  )
)""")

R(SH, "Shp_Carrier_Handling_Matrix", PLG,
  "Carrier-specific tracking formats (CASE ladder), handling vs service level rules, customs code shape for international shipments and declared-value insurance rules.",
  "Tracking number, handling instructions, customs code or declared value conflict with the shipment's carrier/service.",
  """
OR(
  AND(
    NOT(ISBLANK(Tracking_Number__c)),
    OR(
      CASE(TEXT(Carrier__c),
        'UPS', IF(AND(BEGINS(Tracking_Number__c, '1Z'), LEN(Tracking_Number__c) = 18), 0, 1),
        'FedEx', IF(OR(LEN(Tracking_Number__c) = 12, LEN(Tracking_Number__c) = 15), 0, 1),
        'DHL', IF(AND(LEN(Tracking_Number__c) = 10, ISNUMBER(Tracking_Number__c)), 0, 1),
        0) = 1,
      Tracking_Number__c <> UPPER(Tracking_Number__c),
      CONTAINS(Tracking_Number__c, ' ')
    )
  ),
  AND(
    NOT(ISBLANK(Handling__c)),
    OR(
      AND(INCLUDES(Handling__c, 'Hazmat'), OR(ISPICKVAL(Service_Level__c, 'Air'), ISPICKVAL(Service_Level__c, 'Express'))),
      AND(INCLUDES(Handling__c, 'Refrigerated'), CASE(TEXT(Service_Level__c), 'Air', 0, 'Express', 0, 1) = 1),
      AND(INCLUDES(Handling__c, 'Oversized'), NOT(ISPICKVAL(Service_Level__c, 'Freight'))),
      PICKLISTCOUNT(Handling__c) > IF(ISPICKVAL(Service_Level__c, 'Ground'), 2, 4)
    )
  ),
  IF(
    Is_International__c,
    OR(
      ISBLANK(Customs_Code__c),
      NOT(REGEX(BLANKVALUE(Customs_Code__c, 'x'), 'HS-[0-9]{4}[.][0-9]{2}')),
      LPAD(RIGHT(BLANKVALUE(Customs_Code__c, '00'), 2), 3, '0') = RPAD('0', 3, '0')
    ),
    NOT(ISBLANK(Customs_Code__c))
  ),
  AND(
    NOT(ISBLANK(Declared_Value__c)),
    NULLVALUE(Weight_Kg__c, 0) > 0,
    OR(
      Declared_Value__c / Weight_Kg__c > 1000 * SQRT(Weight_Kg__c),
      AND(Declared_Value__c >= 5000, NOT(INCLUDES(Handling__c, 'Signature Required')))
    )
  )
)""")

R(SH, "Shp_Timeline_Lock_Project_Risk", G,
  "Mega-rule: ETA/delivery timestamps (DATETIMEVALUE, ISOWEEK, FORMATDURATION), dock-window time checks, post-ship lock via ISCHANGED/PRIORVALUE, and a VLOOKUP into the project's risk score that demands Signature Required.",
  "Shipment timeline, lock or project-risk handling rules failed.",
  """
OR(
  AND(
    NOT(ISBLANK(Shipped_At__c)),
    NOT(ISBLANK(Estimated_Arrival__c)),
    OR(
      Estimated_Arrival__c <= Shipped_At__c,
      Estimated_Arrival__c > Shipped_At__c + 60,
      AND(ISOWEEK(DATEVALUE(Shipped_At__c)) = 53, NOT(INCLUDES(Handling__c, 'Signature Required')))
    )
  ),
  AND(
    ISPICKVAL(Status__c, 'Delivered'),
    OR(ISBLANK(Delivered_At__c), Delivered_At__c < NULLVALUE(Shipped_At__c, Delivered_At__c))
  ),
  AND(NOT(ISBLANK(Delivered_At__c)), DATEVALUE(Delivered_At__c) > TODAY() + 1),
  AND(NULLVALUE(Transit_Seconds__c, 0) > 0, LEN(FORMATDURATION(Transit_Seconds__c)) = 0),
  AND(
    NOT(ISBLANK(Dock_Time__c)),
    OR(
      HOUR(Dock_Time__c) < 7,
      HOUR(Dock_Time__c) > 18,
      AND(HOUR(Dock_Time__c) = 12, MINUTE(Dock_Time__c) = 30),
      AND(
        NOT(ISBLANK(Estimated_Arrival__c)),
        TIMEVALUE(Estimated_Arrival__c) = TIMEVALUE('00:00:00.000'),
        SECOND(Dock_Time__c) + MILLISECOND(Dock_Time__c) > 0
      )
    )
  ),
  AND(
    NOT(ISNEW()),
    OR(
      AND(ISPICKVAL(PRIORVALUE(Status__c), 'Delivered'), ISCHANGED(Status__c), NOT(ISPICKVAL(Status__c, 'Returned'))),
      AND(NOT(ISBLANK(PRIORVALUE(Shipped_At__c))), OR(ISCHANGED(Tracking_Number__c), ISCHANGED(Carrier__c)))
    )
  ),
  AND(
    NOT(ISBLANK(Project_Name_Ref__c)),
    NULLVALUE(@PRJ_RISK@, 0) > 7,
    OR(
      NOT(INCLUDES(Handling__c, 'Signature Required')),
      AND(Is_International__c, OR(ISPICKVAL(Service_Level__c, 'Ground'), NULLVALUE(Declared_Value__c, 0) > 5000))
    )
  )
)""")

E = "Employee_Record__c"
R(E, "Emp_Identity_Forensics", S,
  "National Id, Employee Id, Badge Code and Name/Email are validated with REGEX, VALUE, REVERSE, ASCII, CHR, MOD, LPAD-style, INITCAP and SUBSTITUTE forensics.",
  "Employee identity fields (national id, employee id, badge, name/email) are malformed.",
  """
OR(
  AND(
    NOT(ISBLANK(National_Id__c)),
    IF(
      REGEX(National_Id__c, '[0-9]{3}-[0-9]{2}-[0-9]{4}'),
      OR(
        LEFT(National_Id__c, 3) = '000',
        LEFT(National_Id__c, 3) = '666',
        VALUE(LEFT(National_Id__c, 1)) = 9,
        MID(National_Id__c, 5, 2) = '00',
        RIGHT(National_Id__c, 4) = '0000',
        AND(LEFT(National_Id__c, 3) = REVERSE(LEFT(National_Id__c, 3)), MID(National_Id__c, 5, 2) = REVERSE(MID(National_Id__c, 5, 2)))
      ),
      TRUE
    )
  ),
  AND(
    NOT(ISBLANK(Employee_Id__c)),
    OR(
      NOT(REGEX(Employee_Id__c, 'E[0-9]{6}')),
      AND(REGEX(Employee_Id__c, 'E[0-9]{6}'), MOD(VALUE(RIGHT(Employee_Id__c, 6)), 97) = 0, NOT(Is_Remote__c))
    )
  ),
  AND(
    NOT(ISBLANK(Badge_Code__c)),
    OR(
      Badge_Code__c <> UPPER(Badge_Code__c),
      NOT(REGEX(Badge_Code__c, '[A-Z][A-Z0-9]{5,11}')),
      LEFT(Badge_Code__c, 1) = RIGHT(Badge_Code__c, 1),
      MOD(ASCII(LEFT(Badge_Code__c, 1)) + ASCII(RIGHT(Badge_Code__c, 1)), 13) = 0,
      LEN(SUBSTITUTE(Badge_Code__c, CHR(48), '')) < LEN(Badge_Code__c) - 3
    )
  ),
  AND(
    NOT(ISBLANK(Work_Email__c)),
    NOT(ISBLANK(First_Name__c)),
    NOT(ISBLANK(Last_Name__c)),
    OR(
      NOT(BEGINS(Work_Email__c, LOWER(LEFT(First_Name__c, 1) & SUBSTITUTE(Last_Name__c, ' ', '')))),
      Name <> INITCAP(LOWER(First_Name__c & ' ' & Last_Name__c))
    )
  )
)""")

R(E, "Emp_Age_Pay_Bands", M,
  "Age at hire (ADDMONTHS), leap-day birthdays, termination ordering, grade-based salary bands (CASE) scaled for part-timers, and a log-scaled bonus ceiling.",
  "Hire/birth/termination dates or salary/bonus are outside the allowed bands.",
  """
OR(
  AND(
    NOT(ISBLANK(Hire_Date__c)),
    NOT(ISBLANK(Birthdate__c)),
    OR(
      ADDMONTHS(Birthdate__c, 192) > Hire_Date__c,
      Hire_Date__c > TODAY() + 90,
      AND(ISPICKVAL(Employment_Type__c, 'Intern'), ADDMONTHS(Birthdate__c, 312) < Hire_Date__c),
      AND(MONTH(Birthdate__c) = 2, DAY(Birthdate__c) = 29, MOD(YEAR(Birthdate__c), 4) <> 0),
      YEAR(TODAY()) - YEAR(Birthdate__c) > 75
    )
  ),
  AND(NOT(ISBLANK(Termination_Date__c)), NOT(ISBLANK(Hire_Date__c)), Termination_Date__c < Hire_Date__c),
  AND(
    NOT(ISBLANK(Salary__c)),
    Salary__c > 0,
    OR(
      Salary__c < CASE(TEXT(Grade__c), 'Junior', 40000, 'Mid', 65000, 'Senior', 90000, 'Staff', 120000, 'Principal', 150000, 'Director', 180000, 0)
        * IF(ISPICKVAL(Employment_Type__c, 'Part Time'), MIN(1, NULLVALUE(Weekly_Hours__c, 40) / 40), 1),
      Salary__c > CASE(TEXT(Grade__c), 'Junior', 90000, 'Mid', 130000, 'Senior', 190000, 'Staff', 260000, 'Principal', 350000, 'Director', 600000, 10000000),
      NULLVALUE(Bonus__c, 0) > Salary__c * ROUND(LN(Salary__c) / 40, 2),
      FLOOR(LOG(Salary__c)) < 4
    )
  )
)""")

R(E, "Emp_Shift_Skill_Location_Rules", PLG,
  "Shift windows (HOUR/MINUTE math vs weekly hours), skill requirements per grade (INCLUDES/PICKLISTCOUNT), on-site distance limit per grade (DISTANCE in km), and salary/review change freezes after termination.",
  "Shift, skills, location or post-termination change rules were violated.",
  """
OR(
  AND(
    NOT(ISBLANK(Shift_Start__c)),
    NOT(ISBLANK(Shift_End__c)),
    OR(
      Shift_End__c <= Shift_Start__c,
      OR(HOUR(Shift_Start__c) >= 22, HOUR(Shift_Start__c) < 6),
      AND(
        NOT(ISBLANK(Weekly_Hours__c)),
        ABS((HOUR(Shift_End__c) * 60 + MINUTE(Shift_End__c) - HOUR(Shift_Start__c) * 60 - MINUTE(Shift_Start__c)) / 60 - Weekly_Hours__c / 5) > 1
      )
    )
  ),
  AND(
    CASE(TEXT(Grade__c), 'Senior', 1, 'Staff', 1, 'Principal', 1, 'Director', 1, 0) = 1,
    OR(
      PICKLISTCOUNT(Skills__c) < 2,
      NOT(OR(INCLUDES(Skills__c, 'Integration'), INCLUDES(Skills__c, 'Security'))),
      AND(ISPICKVAL(Grade__c, 'Director'), NOT(INCLUDES(Skills__c, 'Data')))
    )
  ),
  AND(ISPICKVAL(Employment_Type__c, 'Intern'), INCLUDES(Skills__c, 'Security')),
  AND(
    NOT(Is_Remote__c),
    NOT(ISBLANK(Office_Location__latitude__s)),
    NOT(ISBLANK(Home_Location__latitude__s)),
    DISTANCE(Office_Location__c, Home_Location__c, 'km') > CASE(TEXT(Grade__c), 'Director', 320, 'Principal', 240, 190)
  ),
  AND(
    NOT(ISNEW()),
    OR(
      AND(NOT(ISBLANK(PRIORVALUE(Termination_Date__c))), ISCHANGED(Salary__c)),
      AND(ISCHANGED(Last_Review_At__c), NOT(ISBLANK(PRIORVALUE(Last_Review_At__c))), Last_Review_At__c < PRIORVALUE(Last_Review_At__c))
    )
  )
)""")

R(E, "Emp_Manager_Review_Mega", G,
  "Performance may not exceed the manager's (VLOOKUP by name), scores move in half-point steps in 0-5, review timestamps are checked with DATETIMEVALUE/TIMEVALUE and the bio length is bounded by skills.",
  "Performance score, review timing or bio violates the manager/score rules.",
  """
AND(
  NOT(ISPICKVAL(Employment_Type__c, 'Contractor')),
  OR(
    AND(
      NOT(ISBLANK(Manager_Name_Ref__c)),
      NOT(ISBLANK(Performance_Score__c)),
      Performance_Score__c > NULLVALUE(@MGR_SCORE@, Performance_Score__c)
    ),
    AND(
      NOT(ISBLANK(Performance_Score__c)),
      OR(
        Performance_Score__c < 0,
        Performance_Score__c > 5,
        ROUND(Performance_Score__c * 2, 0) <> Performance_Score__c * 2
      )
    ),
    AND(
      NOT(ISBLANK(Last_Review_At__c)),
      OR(
        Last_Review_At__c > NOW(),
        DATETIMEVALUE(TEXT(DATEVALUE(Last_Review_At__c)) & ' 23:59:59') < Last_Review_At__c,
        TIMEVALUE(Last_Review_At__c) < TIMEVALUE('06:00:00.000')
      )
    ),
    AND(NOT(ISBLANK(Bio__c)), LEN(Bio__c) > 2000, PICKLISTCOUNT(Skills__c) = 0)
  )
)""")
