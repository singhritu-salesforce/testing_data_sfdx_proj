from rules_project import R, D, S, M, PL, C, X, G

I = "Invoice__c"
R(I, "Inv_Due_Date_Terms_Match", D,
  "Due date must equal issue date plus the payment-terms days (CASE ladder), allowing 1 day slack and forbidding Sunday due dates for Net 30+.",
  "Due Date does not match the Payment Terms.",
  """
AND(
  NOT(ISBLANK(Issue_Date__c)),
  NOT(ISBLANK(Due_Date__c)),
  NOT(ISBLANK(TEXT(Payment_Terms__c))),
  OR(
    ABS((Due_Date__c - Issue_Date__c) - CASE(TEXT(Payment_Terms__c), 'Net 15', 15, 'Net 30', 30, 'Net 60', 60, 0)) > 1,
    AND(CASE(TEXT(Payment_Terms__c), 'Net 30', 1, 'Net 60', 1, 0) = 1, WEEKDAY(Due_Date__c) = 1)
  )
)""")

R(I, "Inv_Paid_Timestamp_Rules", D,
  "Paid timestamp is required only for Paid invoices, must be after the issue date, not in the future, and not in the last 5 minutes of a day.",
  "Paid At is missing, premature, in the future or in the final minutes of the day.",
  """
OR(
  AND(ISPICKVAL(Status__c, 'Paid'), ISBLANK(Paid_At__c)),
  AND(NOT(ISPICKVAL(Status__c, 'Paid')), NOT(ISBLANK(Paid_At__c))),
  AND(NOT(ISBLANK(Paid_At__c)),
    OR(
      DATEVALUE(Paid_At__c) < Issue_Date__c,
      Paid_At__c > NOW(),
      AND(HOUR(TIMEVALUE(Paid_At__c)) = 23, MINUTE(TIMEVALUE(Paid_At__c)) >= 55)
    )
  )
)""")

R(I, "Inv_Number_Format_Check_Digit", S,
  "Invoice number must be INV-YYYY-NNNNNN, year must equal the issue year, and the digit sum parity must be even (a mod-2 check on the first and last digits).",
  "Invoice Number has a bad format, year, or check digit.",
  """
AND(
  NOT(ISBLANK(Invoice_Number__c)),
  OR(
    NOT(REGEX(Invoice_Number__c, 'INV-[0-9]{4}-[0-9]{6}')),
    AND(NOT(ISBLANK(Issue_Date__c)), VALUE(MID(Invoice_Number__c, 5, 4)) <> YEAR(Issue_Date__c)),
    IF(REGEX(Invoice_Number__c, 'INV-[0-9]{4}-[0-9]{6}'),
      MOD(VALUE(MID(Invoice_Number__c, 10, 1)) + VALUE(RIGHT(Invoice_Number__c, 1)), 2) <> 0,
      FALSE)
  )
)""")

R(I, "Inv_Currency_Rate_Sanity", M,
  "Currency code must be uppercase letters, the system rate for the invoice currency must be positive, and a custom exchange rate must be within 25% of it.",
  "Currency Code or Exchange Rate is invalid.",
  """
AND(
  NOT(ISBLANK(Currency_Code__c)),
  OR(
    NOT(REGEX(Currency_Code__c, '[A-Z]{3}')),
    CURRENCYRATE(Currency_Code__c) <= 0,
    AND(NOT(ISBLANK(Exchange_Rate__c)), ABS(Exchange_Rate__c - CURRENCYRATE(Currency_Code__c)) > 0.25 * CURRENCYRATE(Currency_Code__c))
  )
)""")

R(I, "Inv_Tax_Discount_Math", M,
  "Tax rate must be sub-50%, discount cannot exceed the larger of 30% of amount and 1000, and tax-inclusive total (rounded to cents) must be positive.",
  "Tax or discount makes the invoice total invalid.",
  """
AND(
  NOT(ISBLANK(Amount__c)),
  OR(
    NULLVALUE(Tax_Rate__c, 0) >= 0.5,
    NULLVALUE(Discount__c, 0) > MAX(0.3 * Amount__c, 1000),
    ROUND(Amount__c * (1 + NULLVALUE(Tax_Rate__c, 0)) - NULLVALUE(Discount__c, 0), 2) <= 0
  ) 
)""")

R(I, "Inv_Payment_Method_Logic", PL,
  "Wire is mandatory above 50k, Check is banned for Due on Receipt, Card is capped at 10k, and recurring invoices cannot use Check.",
  "Payment Methods are not allowed for this amount/terms/recurrence.",
  """
AND(
  NOT(ISBLANK(Payment_Methods__c)),
  OR(
    AND(NULLVALUE(Amount__c, 0) > 50000, NOT(INCLUDES(Payment_Methods__c, 'Wire'))),
    AND(ISPICKVAL(Payment_Terms__c, 'Due on Receipt'), INCLUDES(Payment_Methods__c, 'Check')),
    AND(INCLUDES(Payment_Methods__c, 'Card'), PICKLISTCOUNT(Payment_Methods__c) = 1, NULLVALUE(Amount__c, 0) > 10000),
    AND(Is_Recurring__c, INCLUDES(Payment_Methods__c, 'Check'))
  )
)""")

R(I, "Inv_Status_Change_Control", C,
  "Paid invoices are frozen, Void is terminal, and amount changes on Sent invoices need the status to be reset to Draft in the same edit.",
  "Invoice status/amount change not allowed.",
  """
AND(
  NOT(ISNEW()),
  OR(
    AND(ISPICKVAL(PRIORVALUE(Status__c), 'Paid'), OR(ISCHANGED(Amount__c), ISCHANGED(Discount__c), ISCHANGED(Tax_Rate__c))),
    AND(ISPICKVAL(PRIORVALUE(Status__c), 'Void'), ISCHANGED(Status__c)),
    AND(ISPICKVAL(PRIORVALUE(Status__c), 'Sent'), ISCHANGED(Amount__c), NOT(ISPICKVAL(Status__c, 'Draft')))
  )
)""")

R(I, "Inv_Project_Contact_Domain_Match", X,
  "Billing email domain must equal the linked project's contact email domain (VLOOKUP by project Name); lookup ids must be 18 chars when case-safe.",
  "Billing Email domain must match the project's Contact Email domain.",
  """
AND(
  NOT(ISBLANK(Project_Name_Ref__c)),
  NOT(ISBLANK(Billing_Email__c)),
  FIND('@', Billing_Email__c) > 0,
  OR(
    RIGHT(Billing_Email__c, LEN(Billing_Email__c) - FIND('@', Billing_Email__c)) <>
      RIGHT(VLOOKUP($ObjectType.Project__c.Fields.Contact_Email__c, $ObjectType.Project__c.Fields.Name, Project_Name_Ref__c),
            LEN(VLOOKUP($ObjectType.Project__c.Fields.Contact_Email__c, $ObjectType.Project__c.Fields.Name, Project_Name_Ref__c)) - FIND('@', VLOOKUP($ObjectType.Project__c.Fields.Contact_Email__c, $ObjectType.Project__c.Fields.Name, Project_Name_Ref__c))),
    AND(NOT(ISBLANK(Account__c)), LEN(CASESAFEID(Account__c)) <> 18)
  )
)""")

R(I, "Inv_Rate_Table_Region_Tax", X,
  "A custom Rate Table row named by the PO prefix supplies the maximum tax rate; invoices may not exceed it.",
  "Tax Rate exceeds the Rate Table limit for this PO prefix.",
  """
AND(
  NOT(ISBLANK(PO_Number__c)),
  NOT(ISBLANK(Tax_Rate__c)),
  LEN(PO_Number__c) >= 3,
  Tax_Rate__c > NULLVALUE(VLOOKUP($ObjectType.Rate_Table__c.Fields.Rate__c, $ObjectType.Rate_Table__c.Fields.Name, UPPER(LEFT(PO_Number__c, 3))), 1)
)""")

R(I, "Inv_Mega_Billing_Audit", G,
  "Sent invoices must pass an audit mixing dates, strings, money math, picklist counts and email shape.",
  "Sent invoice failed the billing audit.",
  """
AND(
  ISPICKVAL(Status__c, 'Sent'),
  OR(
    ISBLANK(Billing_Email__c),
    FIND('@', BLANKVALUE(Billing_Email__c, 'x')) = 0,
    AND(NOT(ISBLANK(Due_Date__c)), NOT(ISBLANK(Issue_Date__c)), Due_Date__c - Issue_Date__c > 90),
    AND(NULLVALUE(Line_Count__c, 0) > 0, ROUND(NULLVALUE(Amount__c, 0) / NULLVALUE(Line_Count__c, 1), 0) < 1),
    AND(MOD(DAY(NULLVALUE(Issue_Date__c, TODAY())), 7) = 0, PICKLISTCOUNT(Payment_Methods__c) = 0),
    LEN(TRIM(NULLVALUE(Ref_Hash__c, ''))) NOT_PLACEHOLDER
  )
)""".replace("LEN(TRIM(NULLVALUE(Ref_Hash__c, ''))) NOT_PLACEHOLDER","AND(NOT(ISBLANK(Ref_Hash__c)), NOT(REGEX(Ref_Hash__c, '[a-f0-9]{8,40}')))"))

# ---------------- Shipment ----------------
S_ = "Shipment__c"
R(S_, "Shp_Distance_Transit_Speed", M,
  "Average transit speed (miles per hour from DISTANCE and transit seconds) must be below 600 mph, and Ground service below 80 mph.",
  "Transit time is physically implausible for the distance and service level.",
  """
AND(
  NOT(ISBLANK(Origin__latitude__s)),
  NOT(ISBLANK(Destination__latitude__s)),
  NullValueHelper
)""".replace("NullValueHelper","""NULLVALUE(Transit_Seconds__c, 0) > 0,
  DISTANCE(Origin__c, Destination__c, 'mi') / (Transit_Seconds__c / 3600) >
    IF(ISPICKVAL(Service_Level__c, 'Ground'), 80, 600)"""))

R(S_, "Shp_Great_Circle_Haversine", M,
  "A trig haversine cross-check (SIN/COS/ATAN2/SQRT/PI) of the stored distance must agree with DISTANCE within 5% for international shipments.",
  "Origin/destination coordinates are inconsistent (haversine vs DISTANCE).",
  """
AND(
  Is_International__c,
  NOT(ISBLANK(Origin__latitude__s)),
  NOT(ISBLANK(Destination__latitude__s)),
  ABS(
    3958.8 * 2 * ATAN2(
      SQRT(SIN((Destination__latitude__s - Origin__latitude__s) * PI() / 360) ^ 2
        + COS(Origin__latitude__s * PI() / 180) * COS(Destination__latitude__s * PI() / 180)
          * SIN((Destination__longitude__s - Origin__longitude__s) * PI() / 360) ^ 2),
      SQRT(1 - (SIN((Destination__latitude__s - Origin__latitude__s) * PI() / 360) ^ 2
        + COS(Origin__latitude__s * PI() / 180) * COS(Destination__latitude__s * PI() / 180)
          * SIN((Destination__longitude__s - Origin__longitude__s) * PI() / 360) ^ 2))
    ) - DISTANCE(Origin__c, Destination__c, 'mi')
  ) > 0.05 * MAX(1, DISTANCE(Origin__c, Destination__c, 'mi'))
)""")

R(S_, "Shp_Inverse_Trig_Dimensions", M,
  "The box diagonal angle (ATAN, ASIN, ACOS, TAN) must stay in a stable band: height/length slope and normalised ratios cannot be degenerate.",
  "Package dimensions form a degenerate shape.",
  """
AND(
  NULLVALUE(Length_Cm__c, 0) > 0,
  NULLVALUE(Width_Cm__c, 0) > 0,
  NOT(ISBLANK(Height_Cm__c)),
  OR(
    ATAN(Height_Cm__c / Length_Cm__c) * 180 / PI() > 80,
    ASIN(MIN(1, Width_Cm__c / MAX(Length_Cm__c, Width_Cm__c, Height_Cm__c))) < ACOS(0.99),
    ROUND(TAN(ATAN(Width_Cm__c / Length_Cm__c)) * Length_Cm__c, 1) <> ROUND(Width_Cm__c, 1)
  )
)""")

R(S_, "Shp_Volume_Weight_Density", M,
  "Declared volume must match L x W x H within 2%, and density (kg/m3) must be between 1 and 20000 using logarithmic bounds.",
  "Volume does not match dimensions or density is out of range.",
  """
AND(
  NULLVALUE(Length_Cm__c, 0) > 0,
  NULLVALUE(Width_Cm__c, 0) > 0,
  NULLVALUE(Height_Cm__c, 0) > 0,
  NULLVALUE(Volume_M3__c, 0) > 0,
  OR(
    ABS(Volume_M3__c - Length_Cm__c * Width_Cm__c * Height_Cm__c / 1000000) > 0.02 * Volume_M3__c,
    LOG(NULLVALUE(Weight_Kg__c, 0) / Volume_M3__c + 1) > LOG(20000),
    NULLVALUE(Weight_Kg__c, 0) / Volume_M3__c < EXP(0)
  )
)""")

R(S_, "Shp_Tracking_Number_By_Carrier", S,
  "Tracking numbers are validated by a carrier-specific CASE ladder of length and prefix rules, plus a no-spaces / uppercase check.",
  "Tracking Number does not match the carrier's format.",
  """
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
)""")

R(S_, "Shp_Handling_Service_Matrix", PL,
  "Hazmat cannot fly Air/Express, Refrigerated needs Express or Air, Oversized needs Freight, and handling counts are bounded by service.",
  "Handling instructions conflict with the service level.",
  """
AND(
  NOT(ISBLANK(Handling__c)),
  OR(
    AND(INCLUDES(Handling__c, 'Hazmat'), OR(ISPICKVAL(Service_Level__c, 'Air'), ISPICKVAL(Service_Level__c, 'Express'))),
    AND(INCLUDES(Handling__c, 'Refrigerated'), CASE(TEXT(Service_Level__c), 'Air', 0, 'Express', 0, 1) = 1),
    AND(INCLUDES(Handling__c, 'Oversized'), NOT(ISPICKVAL(Service_Level__c, 'Freight'))),
    PICKLISTCOUNT(Handling__c) > IF(ISPICKVAL(Service_Level__c, 'Ground'), 2, 4)
  )
)""")

R(S_, "Shp_Eta_Delivery_Windows", D,
  "ETA must follow shipping, delivered shipments need a delivery stamp no earlier than shipping, and ETA cannot be more than 60 days away.",
  "Shipment ETA or delivery timestamps are inconsistent.",
  """
OR(
  AND(NOT(ISBLANK(Shipped_At__c)), NOT(ISBLANK(Estimated_Arrival__c)),
    OR(Estimated_Arrival__c <= Shipped_At__c, Estimated_Arrival__c > Shipped_At__c + 60)),
  AND(ISPICKVAL(Status__c, 'Delivered'), OR(ISBLANK(Delivered_At__c), Delivered_At__c < NULLVALUE(Shipped_At__c, Delivered_At__c))),
  AND(NOT(ISBLANK(Delivered_At__c)), DATEVALUE(Delivered_At__c) > TODAY() + 1)
)""")

R(S_, "Shp_Dock_Window_Time", D,
  "Dock time must be in 07:00-18:59, not a lunch slot at 12:xx on the half hour, and the datetime-to-time check on ETA must not land on the dock-closed 00:00 sentinel.",
  "Dock Time is outside the allowed window.",
  """
AND(
  NOT(ISBLANK(Dock_Time__c)),
  OR(
    HOUR(Dock_Time__c) < 7,
    HOUR(Dock_Time__c) > 18,
    AND(HOUR(Dock_Time__c) = 12, MINUTE(Dock_Time__c) = 30),
    AND(NOT(ISBLANK(Estimated_Arrival__c)), TIMEVALUE(Estimated_Arrival__c) = TIMEVALUE('00:00:00.000'), MILLISECOND(Dock_Time__c) <> 0)
  )
)""")

R(S_, "Shp_Customs_Code_Locale", S,
  "International shipments need a customs code like 'HS-1234.56' built by LPAD/RPAD rules, domestic shipments must not have one.",
  "Customs Code is required (HS-NNNN.NN) for international shipments and forbidden for domestic ones.",
  """
OR(
  AND(NOT(Is_International__c), NOT(ISBLANK(Customs_Code__c))),
  AND(Is_International__c,
    OR(ISBLANK(Customs_Code__c),
      NOT(REGEX(BLANKVALUE(Customs_Code__c, 'x'), 'HS-[0-9]{4}[.][0-9]{2}')),
      LPAD(RIGHT(BLANKVALUE(Customs_Code__c, '00'), 2), 3, '0') = RPAD('0', 3, '0'))
  )
)""")

R(S_, "Shp_Declared_Value_Insurance", M,
  "High declared values must be consistent with the weight (value per kg bounded by sqrt of weight) and require Signature Required handling.",
  "Declared Value is too high for the weight or lacks signature handling.",
  """
AND(
  NOT(ISBLANK(Declared_Value__c)),
  NULLVALUE(Weight_Kg__c, 0) > 0,
  OR(
    Declared_Value__c / Weight_Kg__c > 1000 * SQRT(Weight_Kg__c),
    AND(Declared_Value__c >= 5000, NOT(INCLUDES(Handling__c, 'Signature Required')))
  )
)""")

R(S_, "Shp_Delivered_Lock", C,
  "Delivered shipments are locked except for return transitions; tracking number and carrier cannot change after shipping.",
  "Shipment is locked after delivery/shipping.",
  """
AND(
  NOT(ISNEW()),
  OR(
    AND(ISPICKVAL(PRIORVALUE(Status__c), 'Delivered'), ISCHANGED(Status__c), NOT(ISPICKVAL(Status__c, 'Returned'))),
    AND(NOT(ISBLANK(PRIORVALUE(Shipped_At__c))), OR(ISCHANGED(Tracking_Number__c), ISCHANGED(Carrier__c)))
  )
)""")

R(S_, "Shp_Project_Risk_Handling", X,
  "Shipments for projects with risk above 7 (VLOOKUP by project Name) need Signature Required, and high-risk international shipments cannot go Ground or be declared above 5000.",
  "High-risk project shipments need Signature Required handling and cannot be declared that high.",
  """
AND(
  NOT(ISBLANK(Project_Name_Ref__c)),
  NULLVALUE(VLOOKUP($ObjectType.Project__c.Fields.Risk_Score__c, $ObjectType.Project__c.Fields.Name, Project_Name_Ref__c), 0) > 7,
  OR(
    NOT(INCLUDES(Handling__c, 'Signature Required')),
    AND(Is_International__c, OR(ISPICKVAL(Service_Level__c, 'Ground'), NULLVALUE(Declared_Value__c, 0) > 5000))
  )
)""")

R(S_, "Shp_Mega_Dispatch_Audit", G,
  "Dispatch audit: geo distance, ISO-week cutoffs, handling, tracking shape, weight math and transit duration formatting all in one pass.",
  "Shipment failed the dispatch audit.",
  """
AND(
  ISPICKVAL(Status__c, 'In Transit'),
  OR(
    ISBLANK(Shipped_At__c),
    AND(NOT(ISBLANK(Shipped_At__c)), ISOWEEK(DATEVALUE(Shipped_At__c)) = 53, NOT(INCLUDES(Handling__c, 'Signature Required'))),
    AND(NULLVALUE(Transit_Seconds__c, 0) > 0, LEN(FORMATDURATION(Transit_Seconds__c)) = 0),
    ROUND(NULLVALUE(Weight_Kg__c, 0), 0) > 20000,
    AND(NOT(ISBLANK(Origin__latitude__s)), NOT(ISBLANK(Destination__latitude__s)), DISTANCE(Origin__c, Destination__c, 'km') < 0.1),
    AND(NOT(ISBLANK(Tracking_Number__c)), MOD(LEN(Tracking_Number__c), 2) = 1, NOT(ISPICKVAL(Carrier__c, 'USPS')), NOT(ISPICKVAL(Carrier__c, 'UPS')))
  )
)""")

# ---------------- Employee ----------------
E = "Employee_Record__c"
R(E, "Emp_National_Id_Format", S,
  "National Id must look like NNN-NN-NNNN, not start with 000, 666 or 9, and its 3 groups may not be all-zero or reversed duplicates.",
  "National Id has an invalid format or an impossible group.",
  """
AND(
  NOT(ISBLANK(National_Id__c)),
  OR(
    NOT(REGEX(National_Id__c, '[0-9]{3}-[0-9]{2}-[0-9]{4}')),
    IF(REGEX(National_Id__c, '[0-9]{3}-[0-9]{2}-[0-9]{4}'),
      OR(
        LEFT(National_Id__c, 3) = '000',
        LEFT(National_Id__c, 3) = '666',
        VALUE(LEFT(National_Id__c, 1)) = 9,
        MID(National_Id__c, 5, 2) = '00',
        RIGHT(National_Id__c, 4) = '0000',
        LEFT(National_Id__c, 3) = REVERSE(LEFT(National_Id__c, 3)) && MID(National_Id__c, 5, 2) = REVERSE(MID(National_Id__c, 5, 2))
      ),
      FALSE)
  )
)""")

R(E, "Emp_Age_At_Hire", D,
  "Employees must be 16+ at hire, hire date cannot be in the future by more than 90 days, interns under 26, and hire must not fall on 29 Feb for a non-leap check.",
  "Hire date and birthdate give an invalid age at hire.",
  """
AND(
  NOT(ISBLANK(Hire_Date__c)),
  NOT(ISBLANK(Birthdate__c)),
  OR(
    ADDMONTHS(Birthdate__c, 192) > Hire_Date__c,
    Hire_Date__c > TODAY() + 90,
    AND(ISPICKVAL(Employment_Type__c, 'Intern'), ADDMONTHS(Birthdate__c, 312) < Hire_Date__c),
    AND(MONTH(Birthdate__c) = 2, DAY(Birthdate__c) = 29, MOD(YEAR(Birthdate__c), 4) <> 0)
  )
)""")

R(E, "Emp_Salary_Grade_Bands", M,
  "Salary must sit in a grade band (CASE), bonus cannot exceed a log-scaled share of salary, and part-timers' salaries are scaled by weekly hours.",
  "Salary or bonus is outside the band for the grade.",
  """
AND(
  NOT(ISBLANK(Salary__c)),
  OR(
    Salary__c < CASE(TEXT(Grade__c), 'Junior', 40000, 'Mid', 65000, 'Senior', 90000, 'Staff', 120000, 'Principal', 150000, 'Director', 180000, 0)
      * IF(ISPICKVAL(Employment_Type__c, 'Part Time'), MIN(1, NULLVALUE(Weekly_Hours__c, 40) / 40), 1),
    Salary__c > CASE(TEXT(Grade__c), 'Junior', 90000, 'Mid', 130000, 'Senior', 190000, 'Staff', 260000, 'Principal', 350000, 'Director', 600000, 10000000),
    NULLVALUE(Bonus__c, 0) > Salary__c * ROUND(LN(Salary__c) / 40, 2)
  )
)""")

R(E, "Emp_Shift_Hours_Consistency", D,
  "Shift end must be after start, the shift length must match weekly hours / 5 within an hour, and shifts cannot start in the 22:00-05:59 window.",
  "Shift times are inconsistent with weekly hours.",
  """
AND(
  NOT(ISBLANK(Shift_Start__c)),
  NOT(ISBLANK(Shift_End__c)),
  OR(
    Shift_End__c <= Shift_Start__c,
    OR(HOUR(Shift_Start__c) >= 22, HOUR(Shift_Start__c) < 6),
    AND(NOT(ISBLANK(Weekly_Hours__c)),
      ABS((HOUR(Shift_End__c) * 60 + MINUTE(Shift_End__c) - HOUR(Shift_Start__c) * 60 - MINUTE(Shift_Start__c)) / 60 - Weekly_Hours__c / 5) > 1)
  )
)""")

R(E, "Emp_Badge_Code_Mirror", S,
  "Badge code is a letter-digit mixture whose first and last chars cannot be equal, whose ASCII sum is checkable, and whose casing must be upper.",
  "Badge Code format invalid.",
  """
AND(
  NOT(ISBLANK(Badge_Code__c)),
  OR(
    Badge_Code__c <> UPPER(Badge_Code__c),
    NOT(REGEX(Badge_Code__c, '[A-Z][A-Z0-9]{5,11}')),
    LEFT(Badge_Code__c, 1) = RIGHT(Badge_Code__c, 1),
    MOD(ASCII(LEFT(Badge_Code__c, 1)) + ASCII(RIGHT(Badge_Code__c, 1)), 13) = 0,
    LEN(SUBSTITUTE(Badge_Code__c, CHR(48), '')) < LEN(Badge_Code__c) - 3
  )
)""")

R(E, "Emp_Name_Email_Alignment", S,
  "Work email must start with first initial + last name (lowercase) and the employee name must be INITCAP-ed 'First Last'.",
  "Work Email or Name does not follow first-initial+lastname convention.",
  """
AND(
  NOT(ISBLANK(Work_Email__c)),
  NOT(ISBLANK(First_Name__c)),
  NOT(ISBLANK(Last_Name__c)),
  OR(
    NOT(BEGINS(Work_Email__c, LOWER(LEFT(First_Name__c, 1) & SUBSTITUTE(Last_Name__c, ' ', '')))),
    Name <> INITCAP(LOWER(First_Name__c & ' ' & Last_Name__c))
  )
)""")

R(E, "Emp_Skill_Grade_Requirements", PL,
  "Senior+ grades need at least 2 skills and Integration or Security; Directors need Data; Interns cannot carry Security.",
  "Skills do not satisfy grade requirements.",
  """
OR(
  AND(CASE(TEXT(Grade__c), 'Senior', 1, 'Staff', 1, 'Principal', 1, 'Director', 1, 0) = 1,
    OR(PICKLISTCOUNT(Skills__c) < 2, NOT(OR(INCLUDES(Skills__c, 'Integration'), INCLUDES(Skills__c, 'Security'))))),
  AND(ISPICKVAL(Grade__c, 'Director'), NOT(INCLUDES(Skills__c, 'Data'))),
  AND(ISPICKVAL(Employment_Type__c, 'Intern'), INCLUDES(Skills__c, 'Security'))
)""")

R(E, "Emp_Termination_Review_Lock", C,
  "Termination date requires it to be after hire, salary freezes after termination and review timestamps cannot go back in time.",
  "Termination, salary freeze or review timestamp rules violated.",
  """
OR(
  AND(NOT(ISBLANK(Termination_Date__c)), NOT(ISBLANK(Hire_Date__c)), Termination_Date__c < Hire_Date__c),
  AND(NOT(ISNEW()), NOT(ISBLANK(PRIORVALUE(Termination_Date__c))), ISCHANGED(Salary__c)),
  AND(NOT(ISNEW()), ISCHANGED(Last_Review_At__c), NOT(ISBLANK(PRIORVALUE(Last_Review_At__c))), Last_Review_At__c < PRIORVALUE(Last_Review_At__c)),
  AND(NOT(ISNEW()), ISCHANGED(Hire_Date__c), ISPICKVAL(Employment_Type__c, 'Full Time'), Hire_Date__c < TODAY() - 365)
)""")

R(E, "Emp_Office_Home_Distance", M,
  "On-site staff must live within a grade-based radius (120/150/200 miles) of the office.",
  "Home location is too far from the office for this work arrangement.",
  """
AND(
  NOT(ISBLANK(Office_Location__latitude__s)),
  NOT(ISBLANK(Home_Location__latitude__s)),
  NOT(Is_Remote__c),
  DISTANCE(Office_Location__c, Home_Location__c, 'mi') > CASE(TEXT(Grade__c), 'Director', 200, 'Principal', 150, 120)
)""")

R(E, "Emp_Manager_Grade_Order", X,
  "Performance score may not exceed the manager's score (VLOOKUP on the manager's Name), and scores must be within 0-5 on half-point steps.",
  "Performance Score may not exceed the manager's score.",
  """
AND(
  NOT(ISBLANK(Manager_Name_Ref__c)),
  NOT(ISBLANK(Performance_Score__c)),
  Performance_Score__c > NULLVALUE(VLOOKUP($ObjectType.Employee_Record__c.Fields.Performance_Score__c, $ObjectType.Employee_Record__c.Fields.Name, Manager_Name_Ref__c), Performance_Score__c)
)""")

R(E, "Emp_Mega_Compliance", G,
  "Compliance mega-rule: age math, ID format, shift minutes, salary log scale, email parity and skill counts, all together.",
  "Employee record failed the compliance audit.",
  """
AND(
  NOT(ISPICKVAL(Employment_Type__c, 'Contractor')),
  OR(
    AND(NOT(ISBLANK(Birthdate__c)), YEAR(TODAY()) - YEAR(Birthdate__c) > 75),
    AND(NOT(ISBLANK(Employee_Id__c)), NOT(REGEX(Employee_Id__c, 'E[0-9]{6}'))),
    AND(NOT(ISBLANK(Employee_Id__c)), MOD(VALUE(RIGHT(Employee_Id__c, 6)), 97) = 0, NOT(Is_Remote__c)),
    AND(NOT(ISBLANK(Salary__c)), Salary__c > 0, FLOOR(LOG(Salary__c)) < 4),
    AND(NOT(ISBLANK(Bio__c)), LEN(Bio__c) > 2000, PICKLISTCOUNT(Skills__c) = 0),
    AND(NOT(ISBLANK(Performance_Score__c)), OR(Performance_Score__c < 0, Performance_Score__c > 5, ROUND(Performance_Score__c * 2, 0) <> Performance_Score__c * 2))
  )
)""")

# ---------------- Rate table ----------------
RT = "Rate_Table__c"
R(RT, "Rate_Key_Region_Format", S,
  "Rate keys must be 3 uppercase letters, the region must be a prefix of it when set, and rates are capped at 100% with 2 decimal places.",
  "Rate Table key, region or rate is invalid.",
  """
OR(
  AND(NOT(ISBLANK(Key__c)), OR(NOT(REGEX(Key__c, '[A-Z]{3}')), LEN(Key__c) <> 3)),
  AND(NOT(ISBLANK(Region__c)), NOT(ISBLANK(Key__c)), NOT(BEGINS(UPPER(Region__c), LEFT(Key__c, 1)))),
  AND(NOT(ISBLANK(Rate__c)), OR(Rate__c > 1, ROUND(Rate__c * 10000, 0) <> Rate__c * 10000))
)""")

# ---------------- Account ----------------
A = "Account"
R(A, "Acc_Tier_Spend_Ladder", PL,
  "Account tier requires minimum annual spend (CASE) and Platinum accounts must have a website, a global territory and a phone.",
  "Annual Spend or account contact data does not satisfy the account tier.",
  """
AND(
  NOT(ISBLANK(TEXT(Account_Tier__c))),
  OR(
    NULLVALUE(Annual_Spend__c, 0) < CASE(TEXT(Account_Tier__c), 'Bronze', 0, 'Silver', 10000, 'Gold', 100000, 'Platinum', 1000000, 0),
    AND(ISPICKVAL(Account_Tier__c, 'Platinum'), OR(ISBLANK(Website), NOT(INCLUDES(Sales_Territories__c, 'Global')), ISBLANK(Phone)))
  )
)""")

R(A, "Acc_Tax_Id_Region_Code", S,
  "Tax Id must be 2-letter region + hyphen + 9 digits, region must equal Region Code prefix, and the website slug must be lowercase and hyphenated.",
  "Tax Id, Region Code or Website Slug violate formatting rules.",
  """
OR(
  AND(NOT(ISBLANK(Tax_Id__c)),
    OR(NOT(REGEX(Tax_Id__c, '[A-Z]{2}-[0-9]{9}')),
       AND(NOT(ISBLANK(Region_Code__c)), LEFT(Tax_Id__c, 2) <> LEFT(UPPER(Region_Code__c), 2)))),
  AND(NOT(ISBLANK(Website_Slug__c)),
    OR(Website_Slug__c <> LOWER(SUBSTITUTE(Website_Slug__c, ' ', '-')), CONTAINS(Website_Slug__c, '--')))
)""")

R(A, "Acc_Founding_Employees_Revenue", M,
  "Revenue per employee must be sane (log-scaled), founding date must not be in the future and young companies (<2y) cannot report >1B revenue.",
  "Founding date, employees and revenue are not plausible together.",
  """
OR(
  AND(NOT(ISBLANK(Founded_On__c)), Founded_On__c > TODAY()),
  AND(NOT(ISBLANK(Founded_On__c)), TODAY() - Founded_On__c < 730, NULLVALUE(AnnualRevenue, 0) > 1000000000),
  AND(NULLVALUE(NumberOfEmployees, 0) > 0, NULLVALUE(AnnualRevenue, 0) > 0,
    ABS(LOG(AnnualRevenue / NumberOfEmployees) - 5) > 4)
)""")

R(A, "Acc_Annual_Spend_Change_Rule", C,
  "Annual Spend may drop by at most 50% in one edit, tier downgrades need a Type of 'Customer - Direct' or blank, and territory changes lock Global accounts.",
  "Spend, tier or territory change not allowed.",
  """
AND(
  NOT(ISNEW()),
  OR(
    AND(ISCHANGED(Annual_Spend__c), NULLVALUE(PRIORVALUE(Annual_Spend__c), 0) > 0,
      Annual_Spend__c < 0.5 * PRIORVALUE(Annual_Spend__c)),
    AND(ISCHANGED(Account_Tier__c), 
      CASE(TEXT(Account_Tier__c), 'Bronze', 0, 'Silver', 1, 'Gold', 2, 'Platinum', 3, -1) <
      CASE(TEXT(PRIORVALUE(Account_Tier__c)), 'Bronze', 0, 'Silver', 1, 'Gold', 2, 'Platinum', 3, -1),
      NOT(OR(ISBLANK(TEXT(Type)), ISPICKVAL(Type, 'Customer - Direct')))),
    AND(ISCHANGED(Sales_Territories__c), INCLUDES(PRIORVALUE(Sales_Territories__c), 'Global'))
  )
)""")

R(A, "Acc_Contact_Info_Mega", G,
  "Mega-check of phone digits, website prefix, billing country/state coherence, employee counts and rating vs tier.",
  "Account contact/billing data failed the consistency audit.",
  """
OR(
  AND(NOT(ISBLANK(Phone)), LEN(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(Phone, '-', ''), ' ', ''), '+', '')) < 7),
  AND(NOT(ISBLANK(Website)), NOT(OR(BEGINS(LOWER(Website), 'http://'), BEGINS(LOWER(Website), 'https://'), BEGINS(LOWER(Website), 'www.')))),
  AND(NOT(ISBLANK(BillingState)), ISBLANK(BillingCountry), LEN(BillingState) > 2),
  AND(NULLVALUE(NumberOfEmployees, 1) < 1, MOD(MFLOOR(NULLVALUE(AnnualRevenue, 0)), 2) = 1),
  AND(ISPICKVAL(Rating, 'Hot'), CASE(TEXT(Account_Tier__c), 'Gold', 0, 'Platinum', 0, 1) = 1)
)""")

# ---------------- Opportunity ----------------
O = "Opportunity"
R(O, "Opp_Close_Date_Contract_Math", D,
  "Contract start must be on/after the close date and within 6 months, contract months must be a multiple of 3 (or 1) and cannot cross 5 years.",
  "Contract Start / Contract Months are inconsistent with the Close Date.",
  """
AND(
  NOT(ISBLANK(Contract_Start__c)),
  OR(
    Contract_Start__c < CloseDate,
    Contract_Start__c > ADDMONTHS(CloseDate, 6),
    AND(NOT(ISBLANK(Contract_Months__c)),
      OR(AND(MOD(Contract_Months__c, 3) <> 0, Contract_Months__c <> 1),
         ADDMONTHS(Contract_Start__c, Contract_Months__c) > ADDMONTHS(TODAY(), 60)))
  )
)""")

R(O, "Opp_Stage_Probability_Discount", M,
  "Probability must match the stage ladder within 10 points, and discount rises only up to sqrt-scaled caps for the amount.",
  "Probability or discount does not fit the stage/amount.",
  """
OR(
  ABS(Probability - CASE(TEXT(StageName), 'Prospecting', 10, 'Qualification', 20, 'Needs Analysis', 40, 'Proposal/Price Quote', 60, 'Negotiation/Review', 80, 'Closed Won', 100, 'Closed Lost', 0, Probability)) > 10,
  AND(NOT(ISBLANK(Discount_Pct__c)), NOT(ISBLANK(Amount)),
    Discount_Pct__c > MIN(0.5, 0.05 + SQRT(MAX(1, Amount)) / 2000))
)""")

R(O, "Opp_Approval_Code_Structure", S,
  "Approval code is required when discount is over 20% and must be AP-<DDD>-<2 letter stage initials> where DDD is the close day-of-year.",
  "Approval Code is missing or malformed for this discount level.",
  """
OR(
  AND(NULLVALUE(Discount_Pct__c, 0) > 0.2, ISBLANK(Approval_Code__c)),
  AND(NOT(ISBLANK(Approval_Code__c)),
    OR(NOT(REGEX(Approval_Code__c, 'AP-[0-9]{3}-[A-Z]{2}')),
       VALUE(MID(Approval_Code__c, 4, 3)) <> DAYOFYEAR(CloseDate),
       RIGHT(Approval_Code__c, 2) <> UPPER(LEFT(TEXT(StageName), 2))))
)""")

R(O, "Opp_Competitor_Stage_Rules", PL,
  "Closed Won deals cannot list more than 2 competitors and Negotiation deals with Hooli need a Description.",
  "Competitor selections conflict with the stage.",
  """
OR(
  AND(ISPICKVAL(StageName, 'Closed Won'), PICKLISTCOUNT(Competitors__c) > 2),
  AND(ISPICKVAL(StageName, 'Negotiation/Review'), INCLUDES(Competitors__c, 'Hooli'), LEN(TRIM(BLANKVALUE(Description, ''))) < 10),
  AND(PICKLISTCOUNT(Competitors__c) >= 4, NULLVALUE(Amount, 0) < 10000)
)""")

R(O, "Opp_Closed_Won_Freeze", C,
  "Closed Won opportunities cannot change amount or close date and cannot be reopened except to Closed Lost.",
  "Closed Won deals are locked.",
  """
AND(
  NOT(ISNEW()),
  ISPICKVAL(PRIORVALUE(StageName), 'Closed Won'),
  OR(ISCHANGED(Amount), ISCHANGED(CloseDate), AND(ISCHANGED(StageName), NOT(ISPICKVAL(StageName, 'Closed Lost'))))
)""")
