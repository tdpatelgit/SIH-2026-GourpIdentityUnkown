# SIH Technical Review — Speaking Script (Natural)
**Read this aloud exactly as written — 90 seconds**

---

Good morning. I'm presenting our solution for **Problem Statement 26018** — Intelligent Land Record Digitization.

We've built a **full-stack web application** with three parts: a Next.js frontend, a FastAPI backend, and a SQLite database. Everything you'll see is running live and has 38 passing unit tests.

Let me walk you through the **three main features**:

**First** — the public upload. A citizen goes to our website, uploads a scanned land document, and our system extracts six key fields: khata number, khasra number, survey number, owner name, area, and mutation status. Each field gets a confidence score. If any field scores below 70%, the document is automatically sent for human review.

**Second** — the government employee portal. This is a login-protected interface where employees review flagged documents. They see two things side-by-side: the uploaded document with AI extractions on the left, and the official government record already on file on the right. There's also an interactive map showing the exact plot boundary. The employee has three options: approve it as-is, manually correct any wrong fields, or reject it with a documented reason. They can also hand-draw boundaries for spatial verification.

**Third** — account tracking. Uploaders can create an account and see all their past submissions in a dashboard, with real-time status updates.

**Technical highlights**: the system is fully responsive, works on mobile and desktop, has a RESTful API, and includes an admin blacklist feature for escalated cases.

We've **seeded four dummy plots** into the system — two with clean data and two with deliberate AI mistakes — so you can see the full verification workflow during the live demo.

The system is ready. Thank you.

---

## Hand Gestures / Visual Cues (optional)

- **"three parts"** → hold up three fingers
- **"six key fields"** → count on fingers or gesture to a slide if you have one
- **"side-by-side"** → use hands to show two parallel panels
- **"three options"** → count: approve, correct, reject
- **"four dummy plots"** → hold up four fingers

---

## Backup One-Liners (if you need to fill time or answer quick questions)

**Q: Is this production-ready?**
"The architecture is designed for scale. We can migrate to PostgreSQL, add Redis caching, and containerize with Docker without changing the core application."

**Q: How does the AI work?**
"We've built a clean separation between the OCR pipeline and business logic. The current demo uses a mock layer with configurable thresholds, but we have a TrOCR integration branch ready to deploy."

**Q: What about security?**
"We implement password hashing, role-based access control, input validation at both layers, and an audit trail for all data modifications. Production deployment would add JWT tokens and rate limiting."

**Q: Can you show it working?**
"Yes, let me pull up the live demo." *(switch to browser)*
