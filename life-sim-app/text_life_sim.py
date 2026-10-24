#!/usr/bin/env python3
"""Text-based life simulation game.

Live a life one year at a time: grow up, go to school, find work, build
relationships, and react to random events until your story ends.

Run:  python text_life_sim.py            (new game or continue)
      python text_life_sim.py --seed 42  (reproducible run)
"""

import argparse
import json
import os
import random
import sys

SAVE_FILE = os.path.join(os.path.expanduser("~"), ".text_life_sim_save.json")

FIRST = ["Ava", "Mia", "Noah", "Liam", "Olivia", "Emma", "Sophia", "Ethan", "Mason",
         "Isabella", "Amelia", "Harper", "Lucas", "Elijah", "Aria", "Jordan", "Riley"]
LAST = ["Johnson", "Smith", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Lopez", "Wilson", "Anderson", "Nguyen", "Patel"]
CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Seattle",
          "Boston", "Denver", "Atlanta", "Miami", "Austin", "Portland"]
DEGREES = ["Biology", "Nursing", "Business", "Computer Science", "Psychology",
           "Engineering", "Education", "Art", "Finance", "Law"]

EDU_RANK = {"None": 0, "High School": 1, "College": 2}

JOBS = [
    {"title": "Fast Food Worker", "smarts": 0,  "edu": "None",        "salary": 22000},
    {"title": "Retail Associate", "smarts": 10, "edu": "High School", "salary": 28000},
    {"title": "Barista",          "smarts": 10, "edu": "High School", "salary": 30000},
    {"title": "Sales Rep",        "smarts": 20, "edu": "High School", "salary": 36000},
    {"title": "Electrician",      "smarts": 35, "edu": "High School", "salary": 55000},
    {"title": "IT Support",       "smarts": 45, "edu": "College",     "salary": 52000},
    {"title": "Accountant",       "smarts": 55, "edu": "College",     "salary": 64000},
    {"title": "Teacher",          "smarts": 50, "edu": "College",     "salary": 50000},
    {"title": "Software Dev",     "smarts": 65, "edu": "College",     "salary": 90000},
    {"title": "Lawyer",           "smarts": 75, "edu": "College",     "salary": 120000},
    {"title": "Doctor",           "smarts": 85, "edu": "College",     "salary": 190000},
]

LEVELS = ["Junior", "Mid", "Senior", "Lead", "Manager", "Director", "Executive"]
STATS = ("health", "happiness", "smarts", "looks")

rng = random.Random()


# ---------------------------------------------------------------- helpers

def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


def money(n):
    return f"-${abs(int(n)):,}" if n < 0 else f"${int(n):,}"


def bar(v, width=20):
    filled = round(v / 100 * width)
    return "█" * filled + "░" * (width - filled)


def ask(prompt, options):
    """Show numbered options, return the chosen index."""
    for i, label in enumerate(options, 1):
        print(f"  [{i}] {label}")
    while True:
        try:
            raw = input(f"{prompt} > ").strip()
        except EOFError:
            print()
            sys.exit(0)
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(f"  Enter a number from 1 to {len(options)}.")


def rand_name(last=None):
    return f"{rng.choice(FIRST)} {last or rng.choice(LAST)}"


# ---------------------------------------------------------------- state

def new_life():
    last = rng.choice(LAST)
    return {
        "name": rand_name(last),
        "city": rng.choice(CITIES),
        "age": 0,
        "alive": True,
        "health": rng.randint(60, 95),
        "happiness": rng.randint(50, 90),
        "smarts": rng.randint(25, 75),
        "looks": rng.randint(25, 75),
        "karma": 50,
        "money": 0,
        "education": "None",
        "school": "None",
        "degree": None,
        "job": None,  # {"title", "salary", "level", "performance"}
        "actions_left": 0,
        "people": [
            {"name": rand_name(last), "relation": "Mother", "closeness": rng.randint(50, 90)},
            {"name": rand_name(last), "relation": "Father", "closeness": rng.randint(40, 90)},
        ],
        "log": [],
    }


def log(s, line):
    s["log"].append(f"Age {s['age']}: {line}")
    s["log"] = s["log"][-300:]
    print(f"  • {line}")


def apply(s, **eff):
    for k, v in eff.items():
        if k == "money":
            s["money"] += v
        elif k == "performance" and s["job"]:
            s["job"]["performance"] = clamp(s["job"]["performance"] + v)
        elif k in STATS or k == "karma":
            s[k] = clamp(s[k] + v)


def save_game(s):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(s, f)
    except OSError as e:
        print(f"  (Could not save: {e})")


def load_game():
    try:
        with open(SAVE_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------- display

def show_status(s):
    print()
    print("=" * 52)
    status = "" if s["alive"] else "  (deceased)"
    print(f" {s['name']}, age {s['age']} — {s['city']}{status}")
    print("-" * 52)
    for k in STATS:
        print(f" {k.capitalize():<10} {bar(s[k])} {s[k]:>3}")
    print(f" {'Karma':<10} {bar(s['karma'])} {s['karma']:>3}")
    print("-" * 52)
    print(f" Money:     {money(s['money'])}")
    edu = s["education"] + (f" ({s['degree']})" if s["degree"] else "")
    print(f" Education: {edu}" + (f"  | In: {s['school']}" if s["school"] != "None" else ""))
    if s["job"]:
        j = s["job"]
        print(f" Job:       {j['level']} {j['title']} — {money(j['salary'])}/yr, "
              f"performance {j['performance']}")
    else:
        print(" Job:       None")
    print("=" * 52)


def show_people(s):
    print("\n Relationships:")
    if not s["people"]:
        print("  (nobody)")
    for p in sorted(s["people"], key=lambda p: -p["closeness"]):
        print(f"  {p['relation']:<9} {p['name']:<20} {bar(p['closeness'], 10)} {p['closeness']}")


def show_log(s, n=20):
    print(f"\n Life story (last {n}):")
    for line in s["log"][-n:]:
        print(f"  {line}")


# ---------------------------------------------------------------- school

def school_tick(s):
    a = s["age"]
    if a == 5:
        s["school"] = "Elementary School"
        log(s, "Started elementary school.")
    elif a == 11:
        s["school"] = "Middle School"
        log(s, "Started middle school.")
    elif a == 14:
        s["school"] = "High School"
        log(s, "Started high school.")
    elif a == 18 and s["school"] == "High School":
        if s["smarts"] >= 25 or rng.random() < 0.6:
            s["education"] = "High School"
            log(s, "Graduated high school!")
            s["school"] = "None"
            college_offer(s)
        else:
            s["school"] = "None"
            log(s, "Dropped out of high school.")
            apply(s, happiness=-10)
    elif s["school"] == "College" and s.get("college_years", 0) >= 4:
        s["education"] = "College"
        s["school"] = "None"
        log(s, f"Graduated college with a degree in {s['degree']}!")
        apply(s, happiness=10)
    elif s["school"] == "College":
        s["college_years"] = s.get("college_years", 0) + 1

    if s["school"] != "None":
        apply(s, smarts=rng.randint(0, 3))


def college_offer(s):
    print("\n 🎓 You can apply to college. Tuition is $20,000/yr.")
    choice = ask("What do you do", ["Apply to college", "Start working", "Take a gap year"])
    if choice == 0:
        if s["smarts"] >= 40 or rng.random() < 0.3:
            s["degree"] = DEGREES[ask("Pick a major", DEGREES)]
            s["school"] = "College"
            s["college_years"] = 0
            log(s, f"Enrolled in college to study {s['degree']}.")
        else:
            log(s, "Was rejected from college.")
            apply(s, happiness=-8)
    elif choice == 2:
        log(s, "Took a gap year to see the world.")
        apply(s, happiness=8, money=-2000)


# ---------------------------------------------------------------- career

def eligible_jobs(s):
    return [j for j in JOBS
            if EDU_RANK[s["education"]] >= EDU_RANK[j["edu"]] and s["smarts"] >= j["smarts"]]


def job_board(s):
    if s["age"] < 16:
        print("  You're too young to work. Come back at 16.")
        return
    if s["school"] == "College":
        print("  You're a full-time student. Finish college first.")
        return
    jobs = eligible_jobs(s)
    if not jobs:
        print("  No jobs available. Raise your smarts or education.")
        return
    labels = [f"{j['title']} (~{money(j['salary'])}/yr)" for j in jobs] + ["Back"]
    i = ask("Apply for", labels)
    if i == len(jobs):
        return
    j = jobs[i]
    odds = 0.45 + (s["smarts"] - j["smarts"]) / 100 + s["looks"] / 400
    if rng.random() < odds:
        old = s["job"]["title"] if s["job"] else None
        s["job"] = {"title": j["title"], "salary": j["salary"] + rng.randint(-3000, 5000),
                    "level": "Junior", "performance": 50}
        msg = f"Hired as {j['title']} at {money(s['job']['salary'])}/yr!"
        log(s, msg if not old else f"Left {old}. {msg}")
    else:
        log(s, f"Applied to be a {j['title']} but didn't get the job.")
        apply(s, happiness=-3)


def career_tick(s):
    j = s["job"]
    if not j:
        return
    taxes = int(j["salary"] * (0.12 if j["salary"] < 40000 else 0.22))
    s["money"] += j["salary"] - taxes
    j["performance"] = clamp(j["performance"] + rng.randint(-8, 8))
    promo = 0.05 + (j["performance"] - 50) / 150
    if rng.random() < max(0, promo) and j["level"] != LEVELS[-1]:
        j["level"] = LEVELS[LEVELS.index(j["level"]) + 1]
        j["salary"] = int(j["salary"] * rng.uniform(1.08, 1.2))
        log(s, f"Promoted to {j['level']} {j['title']}! New salary {money(j['salary'])}.")
        apply(s, happiness=8)
    elif j["performance"] < 25 and rng.random() < 0.4:
        log(s, f"Got fired from your job as {j['title']}.")
        s["job"] = None
        apply(s, happiness=-15)
    if s["age"] >= 65 and s["job"] and rng.random() < 0.3:
        log(s, f"Retired from your career as a {j['title']}.")
        s["job"] = None
        apply(s, happiness=10)


def expenses(s):
    if s["age"] < 18:
        return 0
    cost = (15000 if s["job"] else 6000) + (8000 if s["job"] and s["job"]["salary"] > 80000 else 0)
    if s["school"] == "College":
        cost += 20000
    return cost


# ---------------------------------------------------------------- people

def people_tick(s):
    for p in s["people"]:
        p["closeness"] = clamp(p["closeness"] + rng.randint(-6, 4))
    if 6 <= s["age"] <= 30 and rng.random() < 0.3:
        f = {"name": rand_name(), "relation": "Friend", "closeness": rng.randint(35, 70)}
        s["people"].append(f)
        log(s, f"Made a new friend: {f['name']}.")
    # Parents age and eventually pass.
    for p in list(s["people"]):
        if p["relation"] in ("Mother", "Father") and s["age"] > 40 and rng.random() < (s["age"] - 40) / 120:
            s["people"].remove(p)
            log(s, f"Your {p['relation'].lower()}, {p['name']}, passed away.")
            apply(s, happiness=-20)
    # Drop friends you've drifted away from.
    for p in list(s["people"]):
        if p["relation"] == "Friend" and p["closeness"] <= 5:
            s["people"].remove(p)
            log(s, f"You drifted apart from {p['name']}.")


def has(s, rel):
    return next((p for p in s["people"] if p["relation"] == rel), None)


def social_menu(s):
    if not s["people"]:
        print("  You have nobody to talk to.")
        return
    people = sorted(s["people"], key=lambda p: -p["closeness"])
    i = ask("Interact with", [f"{p['relation']}: {p['name']}" for p in people] + ["Back"])
    if i == len(people):
        return
    p = people[i]
    opts = ["Spend time together", "Have a conversation", "Give a gift ($200)", "Argue"]
    if p["relation"] == "Partner" and s["age"] >= 18:
        opts.append("Propose marriage")
    if p["relation"] == "Spouse" and 18 <= s["age"] <= 50:
        opts.append("Try for a baby")
    if p["relation"] in ("Partner", "Spouse"):
        opts.append("Break up" if p["relation"] == "Partner" else "Divorce")
    act = opts[ask("Do what", opts)]

    if act == "Spend time together":
        p["closeness"] = clamp(p["closeness"] + rng.randint(4, 12))
        apply(s, happiness=4)
        log(s, f"Spent quality time with {p['name']}.")
    elif act == "Have a conversation":
        p["closeness"] = clamp(p["closeness"] + rng.randint(1, 6))
        log(s, f"Had a good talk with {p['name']}.")
    elif act.startswith("Give a gift"):
        if s["money"] < 200:
            print("  You can't afford that.")
            return
        apply(s, money=-200, karma=2)
        p["closeness"] = clamp(p["closeness"] + rng.randint(6, 15))
        log(s, f"Gave {p['name']} a gift.")
    elif act == "Argue":
        p["closeness"] = clamp(p["closeness"] - rng.randint(8, 20))
        apply(s, happiness=-4)
        log(s, f"Got into an argument with {p['name']}.")
    elif act == "Propose marriage":
        if p["closeness"] >= 60 and rng.random() < p["closeness"] / 100:
            p["relation"] = "Spouse"
            apply(s, happiness=15, money=-8000)
            log(s, f"Married {p['name']}! 💍")
        else:
            p["closeness"] = clamp(p["closeness"] - 15)
            apply(s, happiness=-10)
            log(s, f"Proposed to {p['name']}, who said no.")
    elif act == "Try for a baby":
        if rng.random() < 0.5:
            kid = {"name": rand_name(s["name"].split()[-1]), "relation": "Child", "closeness": 80}
            s["people"].append(kid)
            apply(s, happiness=12)
            log(s, f"Welcomed a child, {kid['name']}! 👶")
        else:
            log(s, "Tried for a baby, but no luck this year.")
    elif act in ("Break up", "Divorce"):
        s["people"].remove(p)
        cost = s["money"] // 2 if act == "Divorce" and s["money"] > 0 else 0
        apply(s, happiness=-12, money=-cost)
        log(s, f"{'Divorced' if act == 'Divorce' else 'Broke up with'} {p['name']}."
               + (f" Lost {money(cost)} in the settlement." if cost else ""))


# ---------------------------------------------------------------- activities

def activities_menu(s):
    a = s["age"]
    opts = [("Study / read", lambda: apply(s, smarts=rng.randint(2, 5), happiness=-1)),
            ("Exercise", lambda: apply(s, health=rng.randint(2, 6), looks=rng.randint(0, 3))),
            ("Meditate", lambda: apply(s, happiness=rng.randint(3, 7), health=1)),
            ("Volunteer", lambda: apply(s, karma=rng.randint(3, 8), happiness=2))]
    if a >= 16:
        opts.append(("Go to a party", lambda: party(s)))
        opts.append(("Look for love", lambda: find_love(s)))
        opts.append(("Work a side gig", lambda: apply(s, money=rng.randint(200, 800), happiness=-2)))
    if a >= 18:
        opts.append(("Gamble at the casino ($500)", lambda: gamble(s)))
        opts.append(("Visit the doctor ($300)", lambda: apply(s, money=-300, health=rng.randint(4, 10))))
    if a >= 13:
        opts.append(("Commit petty theft", lambda: crime(s)))
    labels = [o[0] for o in opts] + ["Back"]
    i = ask("Activity", labels)
    if i == len(opts):
        return False
    label, fn = opts[i]
    before = {k: s[k] for k in STATS + ("karma", "money")}
    fn()
    changes = [f"{k} {s[k] - before[k]:+d}" for k in before if s[k] != before[k]]
    log(s, f"{label}." + (f" ({', '.join(changes)})" if changes else ""))
    return True


def party(s):
    apply(s, happiness=rng.randint(4, 10), health=-rng.randint(0, 4), money=-100)
    if rng.random() < 0.25:
        f = {"name": rand_name(), "relation": "Friend", "closeness": rng.randint(30, 55)}
        s["people"].append(f)
        print(f"  You met {f['name']} at the party.")


def find_love(s):
    if has(s, "Partner") or has(s, "Spouse"):
        print("  You're already in a relationship.")
        apply(s, karma=-3)
        return
    if rng.random() < 0.2 + s["looks"] / 200:
        p = {"name": rand_name(), "relation": "Partner", "closeness": rng.randint(45, 75)}
        s["people"].append(p)
        print(f"  You started dating {p['name']}! ❤️")
        apply(s, happiness=10)
    else:
        print("  No sparks this time.")
        apply(s, happiness=-3)


def gamble(s):
    if s["money"] < 500:
        print("  You don't have $500 to gamble.")
        return
    roll = rng.random()
    if roll < 0.05:
        apply(s, money=10000, happiness=20)
        print("  JACKPOT! You won $10,000!")
    elif roll < 0.45:
        apply(s, money=500, happiness=5)
        print("  You doubled your money.")
    else:
        apply(s, money=-500, happiness=-5)
        print("  You lost it all.")


def crime(s):
    apply(s, karma=-10)
    if rng.random() < 0.35:
        fine = 1500
        apply(s, money=-fine, happiness=-12, looks=-2)
        print(f"  You got caught and paid a {money(fine)} fine.")
        if s["job"] and rng.random() < 0.5:
            print(f"  Your employer found out and fired you.")
            s["job"] = None
    else:
        apply(s, money=rng.randint(50, 600), happiness=3)
        print("  You got away with it.")


# ---------------------------------------------------------------- random events

def random_event(s):
    a = s["age"]
    pool = []
    if a < 13:
        pool += [
            ("A kid at school is being bullied.",
             [("Stand up for them", dict(karma=8, happiness=2, health=-2)),
              ("Tell a teacher", dict(karma=5)),
              ("Join in", dict(karma=-10, happiness=1))]),
            ("You found a lost puppy.",
             [("Bring it home", dict(happiness=10, karma=3)),
              ("Take it to a shelter", dict(karma=6)),
              ("Leave it", dict(karma=-4))]),
        ]
    if 13 <= a < 18:
        pool += [
            ("Friends offer you a cigarette.",
             [("Try it", dict(health=-6, happiness=2)),
              ("Say no", dict(karma=2)),
              ("Lecture them", dict(happiness=-2, karma=1))]),
            ("You have a big exam tomorrow.",
             [("Study all night", dict(smarts=5, health=-2)),
              ("Cheat", dict(smarts=1, karma=-6)),
              ("Wing it", dict(happiness=2, smarts=-2))]),
        ]
    if a >= 18:
        pool += [
            ("Your car broke down.",
             [("Pay a mechanic ($1,200)", dict(money=-1200)),
              ("Fix it yourself", dict(smarts=2, health=-2, money=-300)),
              ("Take the bus for a while", dict(happiness=-5))]),
            ("A stranger offers you a 'guaranteed' investment.",
             [("Invest $2,000", "invest"),
              ("Decline politely", dict()),
              ("Report the scam", dict(karma=5))]),
            ("You found a wallet with $300 in it.",
             [("Return it", dict(karma=10, happiness=3)),
              ("Keep the cash", dict(money=300, karma=-10)),
              ("Leave it", dict())]),
        ]
    if s["job"]:
        pool.append((f"Your boss asks you to work the weekend as {s['job']['title']}.",
                     [("Agree", dict(performance=10, happiness=-4)),
                      ("Refuse", dict(performance=-8, happiness=2)),
                      ("Call in sick", dict(performance=-4, karma=-2))]))
    pool.append(("You came down with the flu.",
                 [("Rest at home", dict(health=4, happiness=-2)),
                  ("See a doctor", dict(health=8, money=-250 if a >= 18 else 0)),
                  ("Push through it", dict(health=-8))]))

    title, choices = rng.choice(pool)
    print(f"\n 📌 {title}")
    i = ask("Your choice", [c[0] for c in choices])
    label, eff = choices[i]
    if eff == "invest":
        if rng.random() < 0.2:
            apply(s, money=6000, happiness=10)
            log(s, f"{title} Invested and tripled the money!")
        else:
            apply(s, money=-2000, happiness=-8)
            log(s, f"{title} Invested and lost it all.")
        return
    apply(s, **eff)
    log(s, f"{title} → {label}.")


# ---------------------------------------------------------------- aging & death

def death_check(s):
    a = s["age"]
    risk = 0.0005
    if a > 60:
        risk += ((a - 60) / 40) ** 3
    if s["health"] < 20:
        risk += 0.15
    if s["health"] <= 0:
        risk = 1.0
    if rng.random() < risk:
        s["alive"] = False
        cause = "illness" if s["health"] < 30 else ("old age" if a > 70 else "an accident")
        log(s, f"Died of {cause} at age {a}.")
        return True
    return False


def age_up(s):
    s["age"] += 1
    print(f"\n ── Year {s['age']} ──")
    if s["age"] == 1:
        log(s, "Took your first steps.")

    school_tick(s)
    career_tick(s)
    cost = expenses(s)
    if cost:
        s["money"] -= cost
    people_tick(s)

    # Natural drift: health slips with age, happiness wanders.
    decay = 0 if s["age"] < 50 else (s["age"] - 50) // 10 + 1
    apply(s, health=rng.randint(-2, 2) - decay, happiness=rng.randint(-4, 4))
    if s["age"] > 40:
        apply(s, looks=-rng.randint(0, 2))
    if s["money"] < -10000:
        log(s, "You're drowning in debt.")
        apply(s, happiness=-6, health=-1)

    if death_check(s):
        return
    if rng.random() < 0.7:
        random_event(s)
    s["actions_left"] = 3


def eulogy(s):
    print("\n" + "=" * 52)
    print(f" 🕯️  {s['name']} ({s['city']}), died at age {s['age']}")
    print("=" * 52)
    print(f" Net worth:  {money(s['money'])}")
    print(f" Education:  {s['education']}" + (f" ({s['degree']})" if s["degree"] else ""))
    kids = [p for p in s["people"] if p["relation"] == "Child"]
    spouse = has(s, "Spouse")
    print(f" Family:     {'married to ' + spouse['name'] if spouse else 'unmarried'}, "
          f"{len(kids)} child{'ren' if len(kids) != 1 else ''}")
    k = s["karma"]
    verdict = ("a saint" if k >= 85 else "a good person" if k >= 60 else
               "an ordinary soul" if k >= 40 else "a troublemaker" if k >= 20 else "a villain")
    print(f" Remembered as {verdict}.")
    score = s["age"] * 10 + max(0, s["money"]) // 1000 + s["happiness"] * 5 + k * 3 + len(kids) * 50
    print(f" Life score: {score}")
    show_log(s, 10)


# ---------------------------------------------------------------- main loop

def play(s):
    while s["alive"]:
        show_status(s)
        opts = ["Age up one year",
                f"Activities ({s['actions_left']} left this year)",
                "Relationships", "Job board", "Life story", "Save & quit"]
        i = ask("What next", opts)
        if i == 0:
            age_up(s)
            save_game(s)
        elif i == 1:
            if s["actions_left"] <= 0:
                print("  You're out of energy this year. Age up to continue.")
            elif activities_menu(s):
                s["actions_left"] -= 1
        elif i == 2:
            show_people(s)
            social_menu(s)
        elif i == 3:
            job_board(s)
        elif i == 4:
            show_log(s)
        elif i == 5:
            save_game(s)
            print(f"  Saved to {SAVE_FILE}. See you next time!")
            return
    eulogy(s)
    try:
        os.remove(SAVE_FILE)
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser(description="Text-based life simulation game")
    ap.add_argument("--seed", type=int, help="random seed for a reproducible life")
    ap.add_argument("--new", action="store_true", help="ignore any saved game")
    args = ap.parse_args()
    if args.seed is not None:
        rng.seed(args.seed)

    print("\n  ✦ TEXT LIFE SIM ✦  — live one life, one year at a time.\n")
    s = None if args.new else load_game()
    if s and s.get("alive"):
        if ask(f"Continue as {s['name']} (age {s['age']})?", ["Continue", "Start a new life"]) == 1:
            s = None
    else:
        s = None
    while True:
        if s is None:
            s = new_life()
            s["actions_left"] = 3
            print(f"\n  You were born in {s['city']}. Your name is {s['name']}.")
            s["log"].append(f"Age 0: Born in {s['city']}.")
        play(s)
        if s["alive"] or ask("\nPlay again?", ["Yes", "No"]) == 1:
            break
        s = None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Bye!")
