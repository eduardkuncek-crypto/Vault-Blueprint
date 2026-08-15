---
title: Setup questions
tags:
  - index
---

# Setup questions

Fifty questions. Answering them turns an empty blueprint into a vault that knows
who you are.

**Two ways to do this — pick either:**

1. **Get interviewed.** Say *"run the vault setup interview"* and your AI works
   through these with you conversationally, one section at a time, writing
   answers into `AIOS/me.md` and `Atlas/About Me/` as it goes.
2. **Type into this file.** Fill in the `→` lines yourself, then say *"process my
   setup answers"*. Same result, no conversation. Good if you'd rather do it in
   one sitting with music on.

You can mix them. Answer what you feel like typing, then say *"interview me on
the rest"*.

**You don't have to finish.** Section 1 alone makes the thing usable. Everything
after is upgrades. Stop whenever; your AI will offer the rest later.

> [!tip] Short answers are fine. "Dunno" is a real answer.
> It gets recorded as undecided, which is genuinely useful. A guessed answer
> sitting in `me.md` for six months is worse than an admitted blank.

---

## Section 1 — The basics (10)

*Answer these and the vault works. Everything else is upgrades.*

**1. What's your full name, and what do people actually call you?**

→

**2. How old are you, and when's your birthday?**

→

**3. Where do you live — town and country?** (Drives weather, timezone, shops,
legal stuff.)

→

**4. What languages do you speak, and which do you want the AI to write to you
in?**

→

**5. What do you do all day right now — school, studies, a job, something else?**

→

**6. Who do you live with?**

→

**7. What's the main thing you're trying to get done in the next few months?**

→

**8. What are you actually good at?** Be specific — not "computers", but the
thing you'd be comfortable doing with no help.

→

**9. What do you want to be good at that you currently aren't?**

→

**10. What should an AI never assume about you?** (This one catches more than it
looks like it will.)

→

---

## Section 2 — Your machines (6)

*Skip if you only use one device and it's unremarkable.*

**11. What's your main computer — OS, rough specs, what you use it for?**

→

**12. Any other machines?** Old laptops, a tablet, a server, a Pi.

→

**13. What phone, and what OS?** (Android can sync and edit the vault directly;
iOS mostly can't. This changes what's possible.)

→

**14. Where does this vault live, and how does it sync between machines?**

→

**15. Anything about your setup that constantly gets in your way?** No admin
rights, tiny disk, bad wifi, a shared machine.

→

**16. Do you use a terminal?** Comfortable in one, or would rather not?

→

---

## Section 3 — What you can actually do (6)

*The section AI gets wrong most often, in both directions.*

**17. Can you write code by hand?** Which languages, and how well, honestly?

→

**18. If you build things with AI rather than writing code yourself — say so
plainly.** It's a completely different working mode and it changes every answer
you'll get.

→

**19. What have you genuinely never touched?** Name things. This is the useful
half.

→

**20. When something breaks, what do you do first?**

→

**21. How do you learn best?** Reading, video, breaking things, being told, being
shown.

→

**22. What jargon should always be explained the first time it comes up?**

→

---

## Section 4 — School or work (5)

**23. Where do you study or work, and what are you doing there?**

→

**24. What are you strong in? What are you struggling with?**

→

**25. Any deadlines, exams or reviews coming up worth tracking?**

→

**26. Who matters there?** Teachers, a manager, people you actually talk to.

→

**27. Where is this going next?** A course, a school, a role, a change.

→

---

## Section 5 — Projects (5)

*One line each is enough. The AI makes a note per project.*

**28. What are you actively working on right now?**

→

**29. What's stuck, and what's it stuck on?**

→

**30. What have you abandoned, and why?** Keep these. *"We tried this and it
didn't work"* is worth more than silence.

→

**31. What do you want to build but haven't started?**

→

**32. What's the one thing that, if it got finished, would unblock the most other
stuff?**

→

---

## Section 6 — How you want the AI to behave (8)

*The highest-value section in the whole interview. Be blunt.*

**33. Short answers or thorough ones?**

→

**34. Should it push back when you're wrong, or go along with you?**

→

**35. When your plan has a flaw — lead with the flaw, or help first and mention
it after?**

→

**36. Do you want to be taught, or handed the working thing?**

→

**37. What's the most annoying thing an AI has ever done to you?**

→

**38. How should it handle being unsure?** Guess and flag it, or say "I don't
know".

→

**39. When something's broken — one fix at a time, or the whole list?**

→

**40. Emoji: yes, no, or only when the conversation isn't serious?**

→

---

## Section 7 — Money, body, routine (6)

*Skip anything you'd rather keep in `Privat/`. That's what it's for.*

**41. What does a normal weekday look like?** When you're up, when you're free.

→

**42. When's your head clearest? When are you useless?**

→

**43. What's your money situation, roughly?** What are you saving for, what can't
you afford.

→

**44. Anything about your health, sleep or body that affects your days?**

→

**45. Do you do any sport or training?**

→

**46. What do you eat, and is there anything you can't or won't?**

→

---

## Section 8 — Taste (4)

*Not filler. "What's my favourite film" is the single most common thing people
test a memory system with, and it fails without this.*

**47. Favourite film, book, show, game, album** — whichever you actually have an
answer for.

→

**48. What are you watching, reading or playing right now, and where are you in
it?**

→

**49. What do you want to check out but haven't started?** (These become
`Atlas/Radar.md` rows.)

→

**50. What's something you have a strong and slightly unreasonable opinion
about?**

→

---

## What happens to the answers

| Section | Lands in |
|---|---|
| 1 | `AIOS/me.md` §Who I am, §Where I'm heading + `Atlas/About Me/Identity.md` |
| 2 | `Atlas/Reference/My machines.md` + `AIOS/me.md` §My devices |
| 3 | `Atlas/About Me/Tech skill inventory.md` + `AIOS/me.md` §What I actually know |
| 4 | `Atlas/About Me/` (school or work note) + `Efforts/` if there are deadlines |
| 5 | One note per project in `Efforts/`, plus rows in `Efforts/Efforts.md` |
| 6 | `Atlas/About Me/Working with AI.md` + `AIOS/me.md` §How to work with me |
| 7 | `Atlas/About Me/` — `Daily routine.md`, `Money.md`, `Health.md`, `Food.md` |
| 8 | `Atlas/About Me/Preferences and tastes.md`, `Atlas/Media/`, `Atlas/Radar.md` |

## When you're done

Delete this file and the `setup-vault` skill. They've done their job.

Want to go deeper later? There's no fixed longer list — just say *"interview me
properly about X"* and point at a subject. The AI writes one note per subject as
it goes. The vault this blueprint came from was built from a 453-question pass
and ended up with 27 notes in `Atlas/About Me/`. That's the ceiling, not the
requirement.

## Related

- [[me]] — where most of this lands
- [[About Me]] — the long version
- [[how-to-use-this]] — the guide
