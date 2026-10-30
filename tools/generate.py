"""Generates force-app metadata + README/COVERAGE from model.py and rules_*.py. Run: python3 -I tools/generate.py"""
import os, sys, re, shutil
from xml.sax.saxutils import escape
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model, rules_project, rules_other
from rules_project import RULES, MACROS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBJ = os.path.join(ROOT, "force-app/main/default/objects")
PS = os.path.join(ROOT, "force-app/main/default/permissionsets")
NS = 'xmlns="http://soap.sforce.com/2006/04/metadata"'
HDR = '<?xml version="1.0" encoding="UTF-8"?>\n'

def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(text)

def field_xml(f, parent_obj):
    t = f["type"]; n = f["name"]
    x = [HDR, f'<CustomField {NS}>\n', f'    <fullName>{n}</fullName>\n', f'    <label>{escape(f["label"])}</label>\n']
    req = False
    if t == "Text": x += [f'    <length>{f["length"]}</length>\n', '    <required>false</required>\n', '    <type>Text</type>\n', '    <unique>false</unique>\n']
    elif t in ("Number", "Currency", "Percent"):
        x += [f'    <precision>{f["precision"]}</precision>\n', '    <required>false</required>\n', f'    <scale>{f["scale"]}</scale>\n', f'    <type>{t}</type>\n']
        if t == "Number": x.append('    <unique>false</unique>\n')
    elif t in ("Date", "DateTime", "Time", "Email", "Phone"):
        x += ['    <required>false</required>\n', f'    <type>{t}</type>\n']
        if t == "Email": x.append('    <unique>false</unique>\n')
    elif t == "Checkbox": x += ['    <defaultValue>false</defaultValue>\n', '    <type>Checkbox</type>\n']
    elif t == "Location": x += ['    <displayLocationInDecimal>true</displayLocationInDecimal>\n', '    <required>false</required>\n', '    <scale>6</scale>\n', '    <type>Location</type>\n']
    elif t == "LongTextArea": x += [f'    <length>{f["length"]}</length>\n', '    <type>LongTextArea</type>\n', f'    <visibleLines>{f["visible"]}</visibleLines>\n']
    elif t in ("Picklist", "MultiselectPicklist"):
        x += ['    <required>false</required>\n', f'    <type>{t}</type>\n']
        if t == "MultiselectPicklist": x.append(f'    <visibleLines>{f["visible"]}</visibleLines>\n')
        x.append('    <valueSet>\n        <restricted>true</restricted>\n        <valueSetDefinition>\n            <sorted>false</sorted>\n')
        for v in f["values"]:
            x.append(f'            <value>\n                <fullName>{escape(v)}</fullName>\n                <default>false</default>\n                <label>{escape(v)}</label>\n            </value>\n')
        x.append('        </valueSetDefinition>\n    </valueSet>\n')
    elif t == "Lookup":
        x += [f'    <deleteConstraint>SetNull</deleteConstraint>\n', f'    <referenceTo>{f["ref"]}</referenceTo>\n',
              f'    <relationshipLabel>{escape(f["rellabel"])}</relationshipLabel>\n', f'    <relationshipName>{f["rel"]}</relationshipName>\n',
              '    <required>false</required>\n', '    <type>Lookup</type>\n']
    # sort-friendly: externalId etc. omitted
    x.append('</CustomField>\n')
    return "".join(x)

def object_xml(label, plural, nameLabel):
    return (HDR + f'<CustomObject {NS}>\n    <actionOverrides><actionName>Accept</actionName><type>Default</type></actionOverrides>\n'
      f'    <allowInChatterGroups>false</allowInChatterGroups>\n    <compactLayoutAssignment>SYSTEM</compactLayoutAssignment>\n'
      f'    <deploymentStatus>Deployed</deploymentStatus>\n    <enableActivities>false</enableActivities>\n    <enableBulkApi>true</enableBulkApi>\n'
      f'    <enableFeeds>false</enableFeeds>\n    <enableHistory>false</enableHistory>\n    <enableReports>true</enableReports>\n'
      f'    <enableSearch>true</enableSearch>\n    <enableSharing>true</enableSharing>\n    <enableStreamingApi>true</enableStreamingApi>\n'
      f'    <label>{escape(label)}</label>\n    <nameField>\n        <label>{escape(nameLabel)}</label>\n        <trackHistory>false</trackHistory>\n        <type>Text</type>\n    </nameField>\n'
      f'    <pluralLabel>{escape(plural)}</pluralLabel>\n    <sharingModel>ReadWrite</sharingModel>\n    <visibility>Public</visibility>\n</CustomObject>\n')

def expand(formula):
    f = formula
    for k, v in MACROS.items(): f = f.replace(f"@{k}@", v)
    assert "@" not in re.sub(r"'[^']*'", "", f), f
    return f

def main():
    shutil.rmtree(os.path.join(ROOT, "force-app/main/default/objects"), ignore_errors=True)
    shutil.rmtree(PS, ignore_errors=True)
    allfields = {}  # obj -> set of field names
    for o, d in model.CUSTOM_OBJECTS.items():
        w(f"{OBJ}/{o}/{o}.object-meta.xml", object_xml(d["label"], d["plural"], d["nameLabel"]))
        for f in d["fields"]:
            w(f"{OBJ}/{o}/fields/{f['name']}.field-meta.xml", field_xml(f, o))
        allfields[o] = d["fields"]
    for o, fl in model.STANDARD_OBJECTS.items():
        for f in fl:
            w(f"{OBJ}/{o}/fields/{f['name']}.field-meta.xml", field_xml(f, o))
        allfields[o] = fl
    # rules
    for r in RULES:
        fx = expand(r["formula"])
        assert len(fx) < 3900, (r["name"], len(fx))
        assert len(r["name"]) <= 40, r["name"]
        x = (HDR + f'<ValidationRule {NS}>\n    <fullName>{r["name"]}</fullName>\n    <active>true</active>\n'
             f'    <description>{escape(r["desc"])}</description>\n    <errorConditionFormula>{escape(fx)}</errorConditionFormula>\n'
             f'    <errorMessage>{escape(r["msg"])}</errorMessage>\n</ValidationRule>\n')
        w(f'{OBJ}/{r["obj"]}/validationRules/{r["name"]}.validationRule-meta.xml', x)
        r["expanded"] = fx
    # permission set
    ps = [HDR, f'<PermissionSet {NS}>\n    <description>Grants full access to all objects and fields in this project</description>\n    <hasActivationRequired>false</hasActivationRequired>\n    <label>Full Access</label>\n']
    for o, fl in allfields.items():
        for f in fl:
            if o in model.CUSTOM_OBJECTS and f["type"] in ("Checkbox",) or f["type"] == "Required": pass
        # custom object name field is always accessible; list non-required fields
        for f in sorted(fl, key=lambda z: z["name"]):
            ps.append(f'    <fieldPermissions>\n        <editable>true</editable>\n        <field>{o}.{f["name"]}</field>\n        <readable>true</readable>\n    </fieldPermissions>\n')
    for o in model.CUSTOM_OBJECTS:
        ps.append(f'    <objectPermissions>\n        <allowCreate>true</allowCreate>\n        <allowDelete>true</allowDelete>\n        <allowEdit>true</allowEdit>\n        <allowRead>true</allowRead>\n        <modifyAllRecords>true</modifyAllRecords>\n        <object>{o}</object>\n        <viewAllRecords>true</viewAllRecords>\n    </objectPermissions>\n')
    ps.append('</PermissionSet>\n')
    w(f"{PS}/Full_Access.permissionset-meta.xml", "".join(ps))
    return allfields

if __name__ == "__main__":
    af = main()
    print("objects", len(model.CUSTOM_OBJECTS), "fields", sum(len(v) for v in af.values()), "rules", len(RULES))
