# SkillBridge user research plan

Updated for the opportunity-aggregator scope. The research question changed: not
"do students want an explanation of a match" but "does aggregating permitted
sources actually save them enough time to be worth adopting, and can they trust
what the system says about a listing and about eligibility".

## 1. Research questions

### Students — the MVP audience

- Which platforms do you search today, and in what order?
- How long does it take to find something genuinely relevant?
- What do you do when a listing is only in Korean and you are unsure of a term?
- How do you tell whether a requirement is mandatory or preferred?
- What is the hardest part: finding listings, understanding requirements, or
  knowing whether you are allowed to apply?
- What do you currently do about deadlines?
- What information would you refuse to give an AI system?

### International-student-specific

- How do you currently determine whether you may work a given job?
- What has gone wrong before, and what would have helped?
- What do you want a system to say when it does not know the answer?

This group is the sharpest test of the product's honesty constraint. If a
student's default assumption is that a tool implying eligibility means they are
permitted, the design is failing regardless of what it literally says.

### Career offices and recruiters — deferred, not dropped

Retain these questions for when those surfaces are reconsidered. They do not gate
the MVP:

- How do you currently review student profiles?
- How do you publish and approve opportunities?
- Which student skills are difficult to assess?
- What decisions must remain human?

## 2. Source-access research

This is research, not engineering, and it is Stage 1 of the roadmap. For each
candidate source, establish and record:

- Does it publish a terms of service covering automated access?
- What does `robots.txt` allow?
- Is there a documented API, feed, or export?
- Does an affiliate or partner program exist?
- If none of the above: the source is `link_only`, and that is the answer

Write the finding into the source registry with the URL checked and the date. A
negative finding is a valid and valuable result.

## 3. First interview round

Recruit:

- 6–8 students, weighted toward international students in Korea
- 1–2 career-office or student-support staff
- 1–2 recruiters, alumni, or mentors

Use the same question structure. Record notes with consent. Ask students to
demonstrate their current search — watching the real workflow is worth more than
their description of it.

## 4. Prototype test

Test the actual aggregation and matching flow, not a mock:

```text
Create a profile (skills, major, TOPIK, location, availability)
→ View a personalized scored feed
→ Read why one listing matched and what is missing
→ Notice a "not specified by the source" eligibility line
→ Correct one extracted field
→ Follow the original source link
```

Do not ask whether users like the design. Ask:

- Do you trust this score? Why or why not?
- Where are you confused?
- What did it get wrong?
- Would you rather see a listing it scored low, or have it hidden?
- What would it take for you to rely on this instead of searching yourself?

That last question is the real adoption test.

## 5. Success signals

- Students can explain what the match score means in their own words
- Students correctly state that SkillBridge does not assess visa eligibility
- Students reach the original posting without being told to
- Students correct at least one extracted field
- Reported search time drops, measured against their own before/after
- Students notice when a source is `link_only` and still find it useful

## 6. Failure signals

- Students treat the score as a hiring decision
- Students read the eligibility line as permission
- Explanations cannot be traced to source text
- Students distrust the extraction and fall back to reading Korean themselves
- Aggregation saves so little time that the original search was not a real
  problem
- The product needs more personal data than the task justifies

The last two matter most. If aggregation does not save real time, the project
needs a different thesis, and that is better learned in five interviews than
after six months of ingestion work.

## 7. Research output

Record findings in `docs/USER_RESEARCH.md` after the first round. Use them to
revisit the source registry, the filter set, the default weights, and the first
demo dataset. Findings that contradict a design assumption get written down
prominently, not filed away.
