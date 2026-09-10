import json
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "final_results" / "model_responses_ranked_and_evaluated.json"
OUTPUT_FILE = BASE_DIR / "final_results" / "usability_evaluation_analysis_ranked.json"

GRADE_MAP = {
    "Excellent": 4,
    "Good": 3,
    "Fair": 2,
    "Poor": 1
}


def load_data(path):
    with open(path, "r") as f:
        return json.load(f)


def analyze_rankings(data):
    model_stats = defaultdict(lambda: {
        "ranks": [],
        "grades": [],
        "grade_counts": defaultdict(int)
    })

    for entry in data:
        ranked_list = entry.get("ranking", {}).get("ranked_list", [])
        for item in ranked_list:
            model_key = f"{item['provider']}_{item['model']}"

            rank = item.get("rank")
            grade = item.get("usability_grade")

            if rank is not None:
                model_stats[model_key]["ranks"].append(rank)

            if grade:
                model_stats[model_key]["grades"].append(GRADE_MAP.get(grade, 0))
                model_stats[model_key]["grade_counts"][grade] += 1

    return model_stats


def compute_summary(model_stats):
    summary = {}

    for model, stats in model_stats.items():
        avg_rank = sum(stats["ranks"]) / len(stats["ranks"]) if stats["ranks"] else None
        avg_grade = sum(stats["grades"]) / len(stats["grades"]) if stats["grades"] else None

        summary[model] = {
            "average_rank": avg_rank,
            "average_grade_score": avg_grade,
            "grade_distribution": dict(stats["grade_counts"])
        }

    return summary


def save_results(summary):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Saved analysis to {OUTPUT_FILE}")


def run():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    data = load_data(INPUT_FILE)

    if "ranking" in data[0]:
        stats = analyze_rankings(data)
    else:
        raise ValueError("Unknown data format")

    summary = compute_summary(stats)
    save_results(summary)


if __name__ == "__main__":
    run()