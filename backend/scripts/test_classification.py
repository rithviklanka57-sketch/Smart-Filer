"""
scripts/test_classification.py — Phase 4 Definition of Done verification.

Run from the backend/ directory:
    python scripts/test_classification.py

Prints JSON classification output for 5 varied sample documents.
Requires ANTHROPIC_API_KEY and EMBEDDING_API_KEY set in .env
"""
import sys
import os
import json
import asyncio

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.extraction import extract_text
from services.llm import classify_document
from services.embeddings import embed_text

# ── Sample documents (inline text — no files needed) ──────────────────────────
SAMPLES = [
    {
        "name": "invoice.txt",
        "mime_type": "text/plain",
        "expected_type": "invoice",
        "content": b"""INVOICE #INV-2024-0412
Date: April 12, 2024
Bill To: Acme Corporation, 123 Main St, New York NY 10001

Item                          Qty   Unit Price   Total
Web Design Services            1    $3,500.00    $3,500.00
Hosting (annual)               1      $240.00      $240.00
Domain Registration            1       $15.00       $15.00

                                          Subtotal  $3,755.00
                                               Tax    $300.40
                                             TOTAL  $4,055.40

Payment due within 30 days. Bank transfer: Chase Bank, Acct 4821-XXXX
""",
    },
    {
        "name": "contract.txt",
        "mime_type": "text/plain",
        "expected_type": "contract",
        "content": b"""SERVICE AGREEMENT

This Service Agreement ("Agreement") is entered into as of January 15, 2024,
between TechCorp LLC ("Service Provider") and GlobalRetail Inc ("Client").

1. SERVICES. Service Provider agrees to deliver software development services
   as described in Exhibit A attached hereto.

2. TERM. This Agreement commences on the Effective Date and continues for
   twelve (12) months unless terminated earlier.

3. COMPENSATION. Client shall pay Service Provider $15,000 per month.

4. CONFIDENTIALITY. Both parties agree to keep all business information
   strictly confidential for a period of five (5) years.

IN WITNESS WHEREOF the parties have executed this Agreement as of the date
first written above.

_________________________        _________________________
TechCorp LLC                     GlobalRetail Inc
""",
    },
    {
        "name": "meeting_notes.txt",
        "mime_type": "text/plain",
        "expected_type": "notes",
        "content": b"""Meeting Notes — Product Roadmap Q2 2024
Date: March 5, 2024
Attendees: Sarah (PM), James (Eng Lead), Priya (Design), Tom (Marketing)

Action Items:
- [Sarah] Finalize Q2 OKRs by March 15
- [James] Spike on new auth system — estimate by March 20
- [Priya] Deliver new onboarding mockups for review
- [Tom] Draft launch plan for v2.0

Discussion:
We agreed to delay the analytics dashboard to Q3 to focus engineering
bandwidth on the new mobile app. Tom raised concern about messaging —
Sarah to schedule a separate sync.

Next meeting: March 19, 2024, 2pm EST
""",
    },
    {
        "name": "resume.txt",
        "mime_type": "text/plain",
        "expected_type": "resume",
        "content": b"""ALEX JOHNSON
alex.johnson@email.com | (555) 234-5678 | LinkedIn: linkedin.com/in/alexjohnson
San Francisco, CA

SUMMARY
Experienced software engineer with 8 years of experience building scalable
backend systems at high-growth startups and enterprise companies.

EXPERIENCE
Senior Software Engineer — Stripe, Inc. (2020–Present)
  • Led migration of payment processing pipeline reducing latency by 40%
  • Mentored team of 6 engineers across 3 time zones

Software Engineer — Airbnb (2017–2020)
  • Built real-time pricing recommendation engine serving 10M requests/day

EDUCATION
B.S. Computer Science, Stanford University, 2017

SKILLS: Python, Go, Kubernetes, PostgreSQL, Redis, AWS
""",
    },
    {
        "name": "letter.txt",
        "mime_type": "text/plain",
        "expected_type": "letter",
        "content": b"""April 3, 2024

Dear Mr. Thompson,

I am writing to express my sincere gratitude for the scholarship award from
the Henderson Foundation. This generous support will allow me to complete
my final year of studies in Environmental Science at State University.

The funding will cover tuition and research materials for my thesis on
urban water quality monitoring systems.

I am committed to making the most of this opportunity and will keep the
Foundation updated on my academic progress.

With warm regards,
Maya Patel
""",
    },
]


async def run_test():
    print("=" * 70)
    print("Phase 4 — Classification Test Script")
    print("=" * 70)
    print()

    passed = 0
    results = []

    for sample in SAMPLES:
        print(f"📄 Processing: {sample['name']}")
        print(f"   Expected type: {sample['expected_type']}")

        # Extract text
        text = extract_text(sample["content"], sample["name"], sample["mime_type"])

        # Classify
        try:
            classification = classify_document(text)
            doc_type = classification.get("doc_type", "unknown").lower()
            summary = classification.get("summary", "")
            entities = classification.get("entities", {})
            topic = classification.get("suggested_topic", "")

            # Check pass/fail
            ok = sample["expected_type"] in doc_type or doc_type in sample["expected_type"]
            status = "✅ PASS" if ok else "❌ FAIL"
            if ok:
                passed += 1

            print(f"   Got type:      {doc_type}  {status}")
            print(f"   Summary:       {summary[:100]}...")
            print(f"   Topic:         {topic}")
            print(f"   Entities:      {json.dumps(entities)}")

            # Generate embedding
            embed_input = f"{summary} {topic} {doc_type}"
            embedding = await embed_text(embed_input)
            if embedding:
                print(f"   Embedding:     {len(embedding)}-dim vector ✅")
            else:
                print(f"   Embedding:     ⚠️  Not generated (check EMBEDDING_API_KEY)")

            results.append({
                "file": sample["name"],
                "expected": sample["expected_type"],
                "got": doc_type,
                "pass": ok,
                "summary": summary,
                "entities": entities,
                "topic": topic,
                "embedding_dim": len(embedding) if embedding else 0,
            })
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append({
                "file": sample["name"],
                "expected": sample["expected_type"],
                "got": "error",
                "pass": False,
                "error": str(e),
            })

        print()

    # Summary
    print("=" * 70)
    print(f"RESULT: {passed}/{len(SAMPLES)} documents correctly classified")
    print("Definition of Done threshold: 4/5")
    dod_pass = passed >= 4
    print(f"Phase 4 Definition of Done: {'✅ PASSED' if dod_pass else '❌ FAILED'}")
    print("=" * 70)
    print()
    print("Full JSON output:")
    print(json.dumps(results, indent=2))

    return dod_pass


if __name__ == "__main__":
    ok = asyncio.run(run_test())
    sys.exit(0 if ok else 1)
