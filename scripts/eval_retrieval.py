"""Grade the retriever against evals/retrieval_cases.json — recall@k + MRR per type."""
import json
from collections import defaultdict
from pathlib import Path

from control_tower.policies.repository import retrieve_policy_docs

CASES = json.loads((Path(__file__).resolve().parents[1] / "evals" / "retrieval_cases.json").read_text())

def unique_doc_ids(docs) -> list:
    """Collapse retrieved chunks to an ordered list of unique doc_ids (rank preserved)."""
    seen, out = set(), []
    for d in docs:
        did = d.metadata.get("doc_id")
        if did and did not in seen:
            seen.add(did)
            out.append(did)
    return out

def evaluate() -> None:
    agg = defaultdict(lambda: {"r1": 0, "r3": 0, "rr": 0.0, "n": 0})
    junk = {"correct": 0, "n": 0}

    for c in CASES:
        retrieved = unique_doc_ids(retrieve_policy_docs(c["query"]))

        if c["type"] == "junk":                       # success = retrieved nothing
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
    print(f"\njunk no-match accuracy: {junk['correct']}/{junk['n']} = {junk['correct']/junk['n']:.2f}\n")


if __name__ == "__main__":
    evaluate()