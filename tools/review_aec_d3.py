"""Collect replacement D3 decisions and retain the provenance of the other five."""

from pathlib import Path

from aia_mp1.assessment import load_assessment, read_json
from aia_mp1.human_reference import load_reference
from aia_mp1.labels import label_status, record_label


def main():
    root = Path("../artifacts/evidence/P1-03/aec-course")
    old, original, records, _ = load_assessment(root, "aec-course-baseline-review")
    reference = load_reference(old, original, records)
    notice = read_json(old / "human-reference-withdrawal.json")
    if notice["human_reference_sha256"] != reference["sha256"]:
        raise ValueError("Withdrawal references a different human review")
    assessment_id = notice["replacement_assessment"]
    directory, replacement, items, rubric = load_assessment(root, assessment_id)
    for field in ("selected_ids", "cohort_sha256", "rubric_sha256", "data_sha256"):
        if original[field] != replacement[field]:
            raise ValueError(f"Replacement assessment differs in {field}")
    pending = label_status(root, assessment_id)["pending_item_ids"]
    print(f"{len(pending)} D3 tool lists left to review.")
    if not pending:
        return
    if (directory / "judges").exists() or (directory / "human-reference.json").exists():
        raise ValueError("Replacement assessment already has judge or frozen reference evidence")
    reviewer = reference["reviewer"]
    print(f"Continue only if you are {reviewer}, have not seen judge scores for these items,")
    print("and want to keep your own D1, D2, D4, D5 and D6 ratings for each item.")
    if input("Type yes to proceed: ").strip().lower() != "yes":
        return
    d3 = next(row for row in rubric["dimensions"] if row["id"] == "D3")
    print(f"Pass (1): {d3['pass_anchor']}\nFail (0): {d3['fail_anchor']}")
    by_id = {row["item_id"]: row["item"] for row in items}
    for item_id in pending:
        item = by_id[item_id]
        print(f"\n{item_id}\n{item['question']}\nTools listed:")
        for tool in item["tools_required"]:
            print(f"  - {tool}")
        while True:
            answer = input("Your D3 rating [1=pass, 0=fail, s=skip, q=quit]: ").strip().lower()
            if answer in {"1", "0", "s", "q"}:
                break
        if answer == "q":
            return
        if answer == "s":
            continue
        prior = reference["labels"][item_id]
        comment = input("Your reason for D3 (optional): ").strip()
        record_label(
            root,
            assessment_id,
            item_id,
            prior["decisions"] | {"D3": int(answer)},
            reviewer,
            review_stage="blind",
            notes=(
                f"D3 course Tool Realism review. {comment}\nD1/D2/D4/D5/D6 carried forward "
                f"by reviewer from {original['assessment_id']}, label {prior['label_id']}, "
                f"reference {reference['sha256']}. Original notes remain in that reference."
            ),
        )
        print(f"Saved {item_id}")
    left = len(label_status(root, assessment_id)["pending_item_ids"])
    print(f"Remaining items: {left}")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nReview closed. Reopen the launcher to resume.")
