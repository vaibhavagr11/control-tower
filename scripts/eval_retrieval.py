"""Grade the retriever against evals/retrieval_cases.json.

Metrics:
  - recall@1 / recall@3 / MRR  -> did we find the right DOCUMENT, ranked high?
  - context completeness       -> does the retrieved TEXT contain the actual rule?
  - junk no-match accuracy     -> did the gate return nothing on off-topic queries?
"""

import json
from collections import defaultdict
from pathlib import Path

from control_tower.policies.repository import retrieve_policy_docs

CASES = json.loads((Path(__file__).resolve().parents[1] / "evals" / "retrieval_cases.json").read_text())


def unique_doc_ids(docs) -> list:
    seen, out = set(), []
    for d in docs:
        did = d.metadata.get("doc_id")
        if did and did not in seen:
            seen.add(did)
            out.append(did)
    return out


def _norm(text: str) -> str:
    return " ".join(text.split()).lower()


def evaluate() -> None:
    agg = defaultdict(lambda: {"r1": 0, "r3": 0, "rr": 0.0, "n": 0})
    junk = {"correct": 0, "n": 0}
    ctx = {"correct": 0, "n": 0}

    for c in CASES:
        docs = retrieve_policy_docs(c["query"])
        retrieved = unique_doc_ids(docs)

        # context completeness: is the expected rule TEXT actually present?
        if c.get("must_contain"):
            ctx["n"] += 1
            joined = _norm(" ".join(d.page_content for d in docs))
            is_complete = _norm(c["must_contain"]) in joined
            ctx["correct"] += int(is_complete)

            if not is_complete:
                print("\n" + "=" * 100)
                print("CONTEXT MISS")
                print("Query:", c["query"])
                print("Type:", c["type"])
                print("Expected doc(s):", c["expected"])
                print("Must contain:", c["must_contain"])
                print("Retrieved doc IDs:", retrieved)
                print("-" * 100)
                for i, d in enumerate(docs, start=1):
                    print(f"\nDoc #{i}")
                    print("doc_id:", d.metadata.get("doc_id"))
                    print("title:", d.metadata.get("title"))
                    print("parent_id:", d.metadata.get("parent_id"))
                    print("text preview:")
                    print(d.page_content[:1000])

        if c["type"] == "junk":
            junk["n"] += 1
            junk["correct"] += int(len(retrieved) == 0)
            continue

        expected = set(c["expected"])
        hit1 = int(bool(retrieved[:1]) and retrieved[0] in expected)
        hit3 = int(any(r in expected for r in retrieved[:3]))
        rr = next((1.0 / i for i, r in enumerate(retrieved, 1) if r in expected), 0.0)
        for key in (c["type"], "ALL"):
            agg[key]["n"] += 1
            agg[key]["r1"] += hit1
            agg[key]["r3"] += hit3
            agg[key]["rr"] += rr

    print(f"\n{'category':<12}{'n':>4}{'recall@1':>10}{'recall@3':>10}{'MRR':>8}")
    print("-" * 44)
    for key in ["semantic", "exact", "ambiguous", "ALL"]:
        a = agg[key]
        if a["n"]:
            print(f"{key:<12}{a['n']:>4}{a['r1']/a['n']:>10.2f}{a['r3']/a['n']:>10.2f}{a['rr']/a['n']:>8.2f}")
    print(f"\ncontext completeness (rule text present): {ctx['correct']}/{ctx['n']} = {ctx['correct']/ctx['n']:.2f}")
    print(f"junk no-match accuracy:                   {junk['correct']}/{junk['n']} = {junk['correct']/junk['n']:.2f}\n")


if __name__ == "__main__":
    evaluate()
