"""Replace fake seed contacts with real client contacts from MCP data."""
import json
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.company import Company
from app.models.contact import Contact

engine = create_engine("sqlite:///data/signals.db", connect_args={"check_same_thread": False})
db = sessionmaker(bind=engine)()

# Client external team members extracted from MCP calls
# Only including contacts with valid company emails (not gmail/personal)
CLIENT_CONTACTS = {
    "Ford Motor Company": [
        {"name": "James Farley", "title": "Executive (CEO)", "email": "jfarle21@ford.com"},
        {"name": "Kim Pitts", "title": "Finance", "email": "kpitts@ford.com"},
        {"name": "Brian Bohl", "title": "Legal", "email": "bbohl@ford.com"},
        {"name": "Mike Keogh", "title": "Finance", "email": "mdkeogh@ford.com"},
        {"name": "Rochell Peters", "title": "Legal", "email": "rpeter49@ford.com"},
        {"name": "Felicita Lugo", "title": "Accounting", "email": "flugo1@ford.com"},
        {"name": "Frank Frohling", "title": "Finance", "email": "ffrohlin@ford.com"},
        {"name": "Mark Truby", "title": "Marketing", "email": "mtruby@ford.com"},
        {"name": "Cathy O'Callaghan", "title": "Finance", "email": "cocalla1@ford.com"},
        {"name": "Jennifer Waldo", "title": "Human Resources", "email": "jennifer.waldo@ford.com"},
        {"name": "Josh Fodale", "title": "Information Technology", "email": "jfodale@ford.com"},
        {"name": "Laura Kaczorowski", "title": "Sales", "email": "lkaczoro@ford.com"},
        {"name": "Rita Joshi", "title": "Information Technology", "email": "rjoshi5@ford.com"},
        {"name": "Alex Swaneck", "title": "Accounting", "email": "aswaneck@ford.com"},
        {"name": "David Dudley", "title": "Accounting", "email": "ddudley3@ford.com"},
    ],
    "General Motors": [
        {"name": "Kimberly Lemaux", "title": "Finance", "email": "kimberly.lemaux@gm.com"},
        {"name": "Lauren Smith", "title": "Sales", "email": "lauren.smith@gm.com"},
        {"name": "Matthew Stevens", "title": "Analytics", "email": "matthew.1.stevens@gm.com"},
        {"name": "Michael Robinson", "title": "Strategy", "email": "michael.robinson@gmfinancial.com"},
        {"name": "Muharema Kolasinac", "title": "Finance", "email": "muharema.kolasinac@gm.com"},
        {"name": "Peter Eardley", "title": "Information Technology", "email": "peter.eardley@gmfinancial.com"},
        {"name": "Rachel Landin", "title": "Operations", "email": "rachel.bhattacharya@gm.com"},
        {"name": "Diela Lulgjuraj", "title": "Information & Cyber Security", "email": "diela.lulgjuraj@gm.com"},
        {"name": "Judy Cooper", "title": "Transformation", "email": "judy.m.cooper@gm.com"},
        {"name": "Maria Stoykov", "title": "Tax", "email": "maria.stoykov@gm.com"},
        {"name": "Shannon Myers", "title": "Human Resources", "email": "shannon.myers@gm.com"},
        {"name": "Craig Johnson", "title": "Compliance", "email": "craig.p.johnson@gm.com"},
        {"name": "Eric Mitchell", "title": "Legal", "email": "eric.mitchell@gm.com"},
    ],
    "Boeing Company": [
        {"name": "Brianne Sood", "title": "Executive", "email": "brianne.c.sood@boeing.com"},
        {"name": "Brett Gerry", "title": "Legal", "email": "brett.c.gerry@boeing.com"},
        {"name": "Claire Sokoloski", "title": "Accounting", "email": "claire.j.sokoloski@boeing.com"},
        {"name": "David Cade", "title": "Information Technology", "email": "david.cade@boeing.com"},
        {"name": "David Gonzalez", "title": "Finance", "email": "david.gonzalez9@boeing.com"},
        {"name": "Shannon Hampton", "title": "Operations", "email": "shannon.d.hampton@boeing.com"},
        {"name": "Bethany Johnson", "title": "Operations", "email": "bethany.j.johnson@boeing.com"},
        {"name": "Jamie Ng", "title": "Finance", "email": "jamie.k.ng@boeing.com"},
        {"name": "Marie Olson", "title": "Compliance", "email": "marie.e.olson@boeing.com"},
        {"name": "Melissa Fleener", "title": "Transformation", "email": "melissa.s.fleener@boeing.com"},
        {"name": "Neal Levine", "title": "Information Technology", "email": "neal.s.levine@boeing.com"},
        {"name": "Shawn Ervin", "title": "Supply Chain", "email": "shawn.m.ervin@boeing.com"},
        {"name": "Andy Chiodini", "title": "Information Technology", "email": "andy.a.chiodini@boeing.com"},
    ],
    "Lockheed Martin": [
        {"name": "Anthony Pirocacos", "title": "Finance", "email": "anthony.pirocacos@lmco.com"},
        {"name": "Ed Gordon", "title": "Finance", "email": "ed.gordon@lmco.com"},
        {"name": "Kenny McLean", "title": "Digital", "email": "kenny.mclean@lmco.com"},
        {"name": "Michael Nance", "title": "Operations", "email": "michael.nance@lmco.com"},
        {"name": "Monet Nathaniel", "title": "Human Resources", "email": "monet.nathaniel@lmco.com"},
        {"name": "Richard Vitek", "title": "Information Technology", "email": "richard.d.vitek.iii@lmco.com"},
        {"name": "Robert Powell", "title": "Operations", "email": "robert.n.powell@lmco.com"},
        {"name": "Ashley Watkins", "title": "Finance", "email": "ashley.d.watkins@lmco.com"},
        {"name": "Jamie Dutkiewicz", "title": "Accounting", "email": "jamie.dutkiewicz@lmco.com"},
        {"name": "Thomas J. Harris", "title": "Finance", "email": "thomas.j.harris@lmco.com"},
        {"name": "Allison Pai", "title": "Compliance", "email": "allison.b.pai@lmco.com"},
        {"name": "Brian Erickson", "title": "Finance", "email": "brian.d.erickson@lmco.com"},
    ],
    "Northrop Grumman": [
        {"name": "Tom Wilson", "title": "Executive", "email": "tom.wilson@ngc.com"},
        {"name": "Julie Klepec", "title": "Finance", "email": "julie.klepec@ngc.com"},
        {"name": "Lisa Edwards", "title": "Finance", "email": "lisa.edwards@ngc.com"},
        {"name": "Adam Pierce", "title": "Information Technology", "email": "adam.pierce@ngc.com"},
        {"name": "Andy Coates", "title": "Accounting", "email": "andrew.coates@ngc.com"},
        {"name": "Keith Gayowski", "title": "Finance", "email": "keith.gayowski@ngc.com"},
        {"name": "Susie Choung", "title": "Legal", "email": "susie.choung@ngc.com"},
        {"name": "Kate Connelly", "title": "Legal", "email": "catherine.connelly@ngc.com"},
        {"name": "Sandra Sickmann", "title": "Compliance", "email": "sandra.sickmann@ngc.com"},
        {"name": "Stephen Movius", "title": "Finance", "email": "steve.movius@ngc.com"},
    ],
    "RTX Corporation": [
        {"name": "David Jacobs", "title": "Corporate Development", "email": "david.c.jacobs@raytheon.com"},
        {"name": "Matthew Scott", "title": "Accounting", "email": "matthew_g_scott@raytheon.com"},
        {"name": "Sarah Burnham", "title": "Tax", "email": "sarah.burnham@rtx.com"},
        {"name": "Shawn Dyer", "title": "Information & Cyber Security", "email": "shawn.dyer@prattwhitney.com"},
        {"name": "Diana Bishop", "title": "Information Technology", "email": "diana.bishop@rtx.com"},
        {"name": "Gregory Fearn", "title": "Compliance", "email": "gregory.fearn@rtx.com"},
        {"name": "Jason Swindell", "title": "Information & Cyber Security", "email": "jason.swindell@rtx.com"},
        {"name": "Sherryll Goodwin", "title": "Finance", "email": "sherryll.goodwin@pw.utc.com"},
    ],
    "General Dynamics": [
        {"name": "Brian Arndt", "title": "Analytics", "email": "barndt@generaldynamics.com"},
        {"name": "Shelby Stone", "title": "Human Resources", "email": "sstone@generaldynamics.com"},
        {"name": "Laurie Sorensen", "title": "Finance", "email": "laurie.sorensen@gdit.com"},
        {"name": "Jim Hayes", "title": "Strategy", "email": "james.hayes@csra.com"},
        {"name": "Thomas DeGraba", "title": "Compliance", "email": "tdegraba@generaldynamics.com"},
        {"name": "Bola Otitoju", "title": "Finance", "email": "botitoju@generaldynamics.com"},
        {"name": "Ellen Rutherford", "title": "Finance", "email": "ellen.rutherford@gdit.com"},
        {"name": "Scott Zamer", "title": "Finance", "email": "scott.zamer@gdbiw.com"},
    ],
    "L3Harris Technologies": [
        {"name": "Matthew Steenman", "title": "Executive", "email": "matthew.steenman@l3harris.com"},
        {"name": "John Bartos", "title": "Strategy", "email": "john.bartos@l3harris.com"},
        {"name": "Doug Dillman", "title": "Accounting", "email": "ddillman@harris.com"},
        {"name": "Mike Fernandez", "title": "Finance", "email": "mike.fernandez@l3harris.com"},
        {"name": "Bryan Strom", "title": "Information Technology", "email": "bryan.strom@l3harris.com"},
        {"name": "Beth Cheatham", "title": "Compliance", "email": "beth.cheatham@l3harris.com"},
        {"name": "Greta Billings", "title": "Finance", "email": "greta.billings@l3harris.com"},
        {"name": "Melanie Rakita", "title": "Human Resources", "email": "melanie.rakita@l3harris.com"},
    ],
    "Tesla Inc": [
        {"name": "Heather Nicholls", "title": "Finance", "email": "hnicholls@tesla.com"},
        {"name": "Ken Moore", "title": "Accounting", "email": "kemoore@tesla.com"},
        {"name": "Faith Taylor", "title": "Environment & Sustainability", "email": "fataylor@tesla.com"},
        {"name": "Ashley Lopuski", "title": "Internal Audit", "email": "alopuski@tesla.com"},
        {"name": "Andy Chang", "title": "Tax", "email": "andchang@tesla.com"},
        {"name": "Evelyn Chan", "title": "Accounting", "email": "evchan@tesla.com"},
        {"name": "Amy Li", "title": "Finance", "email": "amli@tesla.com"},
        {"name": "Nelson Wong", "title": "Operations", "email": "nwong@tesla.com"},
        {"name": "Eric Schweiker", "title": "Compliance", "email": "eschweiker@tesla.com"},
        {"name": "Louis Larrus", "title": "Information Technology", "email": "llarrus@tesla.com"},
        {"name": "Phil Rothenberg", "title": "Legal", "email": "prothenberg@tesla.com"},
        {"name": "Sean Kang", "title": "Accounting", "email": "seakang@tesla.com"},
    ],
    "Rivian Automotive": [
        {"name": "Richard Farquhar", "title": "Executive", "email": "rfarquhar@rivian.com"},
        {"name": "Matt Horton", "title": "Strategy", "email": "mhorton@rivian.com"},
        {"name": "Ian Makowske", "title": "Finance", "email": "imakowske@rivian.com"},
        {"name": "Jeff Hammoud", "title": "Information Technology", "email": "jhammoud@rivian.com"},
        {"name": "Julie Hoeniges", "title": "Compliance", "email": "jhoeniges@rivian.com"},
        {"name": "Emily Fitzgerald", "title": "Supply Chain", "email": "efitzgerald@rivian.com"},
        {"name": "Andrew Catalano", "title": "Accounting", "email": "acatalano@rivian.com"},
        {"name": "Chris Jenny", "title": "Finance", "email": "cjenny@rivian.com"},
        {"name": "Heather Pillot", "title": "Legal", "email": "hpillot@rivian.com"},
        {"name": "Ben Hewitt", "title": "Corporate Development", "email": "ben.hewitt@rivian.com"},
    ],
    "Chevron Corporation": [
        {"name": "Jeff Gustavson", "title": "Board Member", "email": "jeff.gustavson@chevron.com"},
        {"name": "Margaret Tipton", "title": "Tax", "email": "margaret.tipton@chevron.com"},
        {"name": "Alana Knowles", "title": "Accounting", "email": "alanaknowles@chevron.com"},
        {"name": "Kevin Jones", "title": "Risk", "email": "kevin.jones@chevron.com"},
        {"name": "Whit Parker", "title": "Finance", "email": "whitley.parker@chevron.com"},
        {"name": "Bryant Ko", "title": "Strategy", "email": "beko@chevron.com"},
        {"name": "Charles Taylor", "title": "Environment & Sustainability", "email": "chuck.taylor@chevron.com"},
        {"name": "Stacy Johnston", "title": "Accounting", "email": "stacy.johnston@chevron.com"},
        {"name": "Yen Pham", "title": "Internal Audit", "email": "yen.pham@chevron.com"},
    ],
}

# Companies with no client contacts in CRM — delete fake data, leave empty
NO_CONTACTS = ["Aptiv", "Stellantis", "Magna International", "Bosch"]

total_deleted = 0
total_created = 0

for company_name, contacts in CLIENT_CONTACTS.items():
    company = db.query(Company).filter(Company.name == company_name).first()
    if not company:
        print(f"  SKIP: {company_name} not found")
        continue

    # Delete all existing contacts
    deleted = db.query(Contact).filter(Contact.company_id == company.id).delete()
    total_deleted += deleted

    # Insert real contacts
    for c in contacts:
        db.add(Contact(
            id=str(uuid.uuid4()),
            company_id=company.id,
            name=c["name"],
            title=c["title"],
            email=c["email"],
            notes="From PwC CRM",
        ))
        total_created += 1

    print(f"  {company_name}: deleted {deleted} fake, added {len(contacts)} real")

# Delete fake data for companies with no CRM contacts
for company_name in NO_CONTACTS:
    company = db.query(Company).filter(Company.name == company_name).first()
    if company:
        deleted = db.query(Contact).filter(Contact.company_id == company.id).delete()
        if deleted:
            total_deleted += deleted
            print(f"  {company_name}: deleted {deleted} fake (no CRM data)")

db.commit()
print(f"\nDone. Deleted {total_deleted} fake, created {total_created} real contacts.")

# Export to seed fixture
import sqlite3
conn = sqlite3.connect("data/signals.db")
c = conn.cursor()
c.execute("""
    SELECT co.name, c.name, c.title, c.email, c.relationship_strength, c.notes
    FROM contacts c JOIN companies co ON c.company_id = co.id
    ORDER BY co.name, c.name
""")
records = []
for company, name, title, email, strength, notes in c.fetchall():
    records.append({
        "company_name": company,
        "name": name,
        "title": title,
        "email": email,
        "relationship_strength": strength,
        "notes": notes,
    })

with open("backend/seed_data/client_contacts.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"Exported {len(records)} contacts to seed fixture")
conn.close()
db.close()
