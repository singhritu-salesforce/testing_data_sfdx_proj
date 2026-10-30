"""Data model definition. Used by generate.py to emit SFDX source."""

def F(name, label, type_, **kw):
    d = dict(name=name, label=label, type=type_)
    d.update(kw)
    return d

def T(name, label, length=40): return F(name, label, "Text", length=length)
def NUM(name, label, p=10, s=2): return F(name, label, "Number", precision=p, scale=s)
def CUR(name, label): return F(name, label, "Currency", precision=16, scale=2)
def PCT(name, label): return F(name, label, "Percent", precision=7, scale=2)
def DT(name, label): return F(name, label, "Date")
def DTM(name, label): return F(name, label, "DateTime")
def TIM(name, label): return F(name, label, "Time")
def CB(name, label): return F(name, label, "Checkbox")
def EML(name, label): return F(name, label, "Email")
def PH(name, label): return F(name, label, "Phone")
def GEO(name, label): return F(name, label, "Location")
def PL(name, label, vals): return F(name, label, "Picklist", values=vals)
def MPL(name, label, vals): return F(name, label, "MultiselectPicklist", values=vals, visible=5)
def LTA(name, label): return F(name, label, "LongTextArea", length=32768, visible=6)
def LK(name, label, ref, rel, rellabel): return F(name, label, "Lookup", ref=ref, rel=rel, rellabel=rellabel)

CUSTOM_OBJECTS = {
 "Project__c": dict(label="Project", plural="Projects", nameLabel="Project Name", fields=[
    CUR("Budget__c","Budget"), CUR("Spent__c","Spent"),
    DT("Start_Date__c","Start Date"), DT("End_Date__c","End Date"), DTM("Kickoff_At__c","Kickoff At"),
    PL("Status__c","Status",["Draft","Planning","Active","On Hold","Completed","Cancelled"]),
    PL("Priority__c","Priority",["Low","Medium","High","Critical"]),
    MPL("Tags__c","Tags",["Internal","External","Regulated","Pilot","Strategic"]),
    T("Code__c","Code",30), EML("Contact_Email__c","Contact Email"), PH("Phone__c","Phone"),
    PCT("Completion_Pct__c","Completion Pct"), NUM("Risk_Score__c","Risk Score",5,2),
    CB("Is_Approved__c","Is Approved"), GEO("Location__c","Location"), LTA("Notes__c","Notes"),
    NUM("Duration_Secs__c","Duration Secs",18,0), NUM("Epoch_Seconds__c","Epoch Seconds",18,0),
    TIM("Standup_Time__c","Standup Time"), T("Parent_Name_Ref__c","Parent Name Ref",80), T("Region_Key__c","Region Key",10),
    LK("Account__c","Account","Account","Projects","Projects"),
    LK("Parent_Project__c","Parent Project","Project__c","Child_Projects","Child Projects"),
 ]),
 "Task_Item__c": dict(label="Task Item", plural="Task Items", nameLabel="Task Name", fields=[
    LK("Project__c","Project","Project__c","Task_Items","Task Items"),
    NUM("Estimated_Hours__c","Estimated Hours",8,2), NUM("Actual_Hours__c","Actual Hours",8,2),
    DT("Due_Date__c","Due Date"), DTM("Started_At__c","Started At"), DTM("Completed_At__c","Completed At"),
    PL("Status__c","Status",["Not Started","In Progress","Blocked","Done"]),
    PL("Severity__c","Severity",["Minor","Major","Blocker"]),
    MPL("Labels__c","Labels",["Frontend","Backend","Database","Security","Docs"]),
    T("Ticket_Ref__c","Ticket Ref",20), EML("Assignee_Email__c","Assignee Email"),
    PCT("Progress__c","Progress"), CB("Is_Billable__c","Is Billable"),
    T("Slug__c","Slug",80), NUM("Sprint_Number__c","Sprint Number",3,0), TIM("Standup_Time__c","Standup Time"),
 ]),
 "Invoice__c": dict(label="Invoice", plural="Invoices", nameLabel="Invoice Name", fields=[
    LK("Project__c","Project","Project__c","Invoices","Invoices"),
    LK("Account__c","Account","Account","Invoices","Invoices"),
    T("Invoice_Number__c","Invoice Number",20), CUR("Amount__c","Amount"), PCT("Tax_Rate__c","Tax Rate"),
    CUR("Discount__c","Discount"), DT("Issue_Date__c","Issue Date"), DT("Due_Date__c","Due Date"),
    DTM("Paid_At__c","Paid At"),
    PL("Status__c","Status",["Draft","Sent","Paid","Overdue","Void"]),
    PL("Payment_Terms__c","Payment Terms",["Net 15","Net 30","Net 60","Due on Receipt"]),
    T("Currency_Code__c","Currency Code",3),
    MPL("Payment_Methods__c","Payment Methods",["Card","Wire","ACH","Check"]),
    T("PO_Number__c","PO Number",20), T("Project_Name_Ref__c","Project Name Ref",80), EML("Billing_Email__c","Billing Email"),
    CB("Is_Recurring__c","Is Recurring"), NUM("Exchange_Rate__c","Exchange Rate",10,6),
    NUM("Line_Count__c","Line Count",3,0), T("Ref_Hash__c","Ref Hash",40),
 ]),
 "Shipment__c": dict(label="Shipment", plural="Shipments", nameLabel="Shipment Name", fields=[
    GEO("Origin__c","Origin"), GEO("Destination__c","Destination"),
    NUM("Weight_Kg__c","Weight Kg",10,2), NUM("Volume_M3__c","Volume M3",10,3),
    NUM("Length_Cm__c","Length Cm",8,1), NUM("Width_Cm__c","Width Cm",8,1), NUM("Height_Cm__c","Height Cm",8,1),
    T("Tracking_Number__c","Tracking Number",30),
    PL("Carrier__c","Carrier",["FedEx","UPS","DHL","USPS"]),
    PL("Service_Level__c","Service Level",["Ground","Air","Express","Freight"]),
    MPL("Handling__c","Handling",["Fragile","Hazmat","Refrigerated","Oversized","Signature Required"]),
    DTM("Shipped_At__c","Shipped At"), DTM("Estimated_Arrival__c","Estimated Arrival"), DTM("Delivered_At__c","Delivered At"),
    PL("Status__c","Status",["Pending","In Transit","Delivered","Returned","Lost"]),
    CUR("Declared_Value__c","Declared Value"), NUM("Transit_Seconds__c","Transit Seconds",18,0),
    LK("Account__c","Account","Account","Shipments","Shipments"),
    LK("Project__c","Project","Project__c","Shipments","Shipments"),
    TIM("Dock_Time__c","Dock Time"), T("Project_Name_Ref__c","Project Name Ref",80), CB("Is_International__c","Is International"),
    T("Customs_Code__c","Customs Code",15), PH("Contact_Phone__c","Contact Phone"),
 ]),
 "Employee_Record__c": dict(label="Employee Record", plural="Employee Records", nameLabel="Employee Name", fields=[
    T("Employee_Id__c","Employee Id",20), T("Manager_Name_Ref__c","Manager Name Ref",80), T("National_Id__c","National Id",11),
    T("First_Name__c","First Name",40), T("Last_Name__c","Last Name",40),
    DT("Hire_Date__c","Hire Date"), DT("Birthdate__c","Birthdate"), DT("Termination_Date__c","Termination Date"),
    CUR("Salary__c","Salary"), CUR("Bonus__c","Bonus"),
    PL("Grade__c","Grade",["Junior","Mid","Senior","Staff","Principal","Director"]),
    PL("Employment_Type__c","Employment Type",["Full Time","Part Time","Contractor","Intern"]),
    MPL("Skills__c","Skills",["Apex","LWC","Flow","Integration","Data","Security"]),
    EML("Work_Email__c","Work Email"), PH("Mobile__c","Mobile"),
    LK("Manager__c","Manager","Employee_Record__c","Direct_Reports","Direct Reports"),
    LK("Project__c","Project","Project__c","Employees","Employees"),
    GEO("Office_Location__c","Office Location"), GEO("Home_Location__c","Home Location"),
    T("Badge_Code__c","Badge Code",12), NUM("Performance_Score__c","Performance Score",3,1),
    DTM("Last_Review_At__c","Last Review At"), TIM("Shift_Start__c","Shift Start"), TIM("Shift_End__c","Shift End"),
    CB("Is_Remote__c","Is Remote"), LTA("Bio__c","Bio"), NUM("Weekly_Hours__c","Weekly Hours",5,2),
 ]),
 "Rate_Table__c": dict(label="Rate Table", plural="Rate Tables", nameLabel="Rate Name", fields=[
    T("Key__c","Key",40), PCT("Rate__c","Rate"), T("Region__c","Region",20), CB("Is_Active__c","Is Active"),
 ]),
}

STANDARD_OBJECTS = {
 "Account": [
    T("Tax_Id__c","Tax Id",12), CUR("Annual_Spend__c","Annual Spend"),
    PL("Account_Tier__c","Account Tier",["Bronze","Silver","Gold","Platinum"]),
    DT("Founded_On__c","Founded On"), T("Region_Code__c","Region Code",5), T("Website_Slug__c","Website Slug",60),
    MPL("Sales_Territories__c","Sales Territories",["North","South","East","West","Global"]),
 ],
 "Opportunity": [
    DT("Contract_Start__c","Contract Start"), NUM("Contract_Months__c","Contract Months",3,0),
    PCT("Discount_Pct__c","Discount Pct"), T("Approval_Code__c","Approval Code",20),
    MPL("Competitors__c","Competitors",["Acme","Globex","Initech","Umbrella","Hooli"]),
 ],
}

# standard fields referenced by rules on standard objects
STD_REFS = {
 "Account": {"Name","Phone","Website","BillingState","BillingCountry","NumberOfEmployees","AnnualRevenue","Industry","Type","Rating","Id"},
 "Opportunity": {"Name","Amount","CloseDate","StageName","Probability","Type","LeadSource","Description","Id"},
}
