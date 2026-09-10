import json
from collections import defaultdict

INPUT_FILE = "final_results/stories_ranking_results.json"
OUTPUT_FILE = "final_results/story_ranking_analysis.json"

GRADE_MAP = {
    "Excellent": 4,
    "Good": 3,
    "Fair": 2,
    "Poor": 1
}


def load_data(path):
    with open(path, "r") as f:
        return json.load(f)


def analyze_campaign_data(data):
    model_stats = defaultdict(lambda: {
        "ranks": [],
        "grades": [],
        "grade_counts": defaultdict(int),
        "campaigns": set()
    })

    for campaign_id, campaign_data in data.items():
        rankings = campaign_data.get("ranking", [])

        for item in rankings:
            model = item.get("model")
            if not model:
                continue

            rank = item.get("rank")
            grade = item.get("grade")

            model_stats[model]["campaigns"].add(campaign_id)

            if rank is not None:
                model_stats[model]["ranks"].append(rank)

            if grade:
                model_stats[model]["grades"].append(GRADE_MAP.get(grade, 0))
                model_stats[model]["grade_counts"][grade] += 1

    return model_stats


def compute_summary(model_stats):
    summary = {}

    for model, stats in model_stats.items():

        avg_rank = (
            sum(stats["ranks"]) / len(stats["ranks"])
            if stats["ranks"] else None
        )

        avg_grade = (
            sum(stats["grades"]) / len(stats["grades"])
            if stats["grades"] else None
        )

        summary[model] = {
            "average_rank": avg_rank,
            "average_grade_score": avg_grade,
            "grade_distribution": dict(stats["grade_counts"])
        }

    return summary


def run():
    data = load_data(INPUT_FILE)

    stats = analyze_campaign_data(data)
    summary = compute_summary(stats)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Analysis written to {OUTPUT_FILE}")


if __name__ == "__main__":
    run()