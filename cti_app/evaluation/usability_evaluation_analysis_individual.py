import json
import os
from collections import defaultdict
from pathlib import Path

# mapping grades to numeric scores
GRADE_MAP = {
    "Excellent": 4,
    "Good": 3,
    "Fair": 2,
    "Poor": 1
}


def load_data(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def analyze(data):
    model_stats = defaultdict(lambda: {
        "scores": [],
        "grade_distribution": defaultdict(int),
    })

    for entry in data:
        for eval in entry["evaluations"]:
            provider = eval["provider"]
            model = eval["model"]
            key = f"{provider}::{model}"

            grade = eval["usability_grade"]
            score = GRADE_MAP.get(grade, 0)

            model_stats[key]["scores"].append(score)
            model_stats[key]["grade_distribution"][grade] += 1

    # compute averages
    summary = {}
    for model, stats in model_stats.items():
        avg_score = sum(stats["scores"]) / len(stats["scores"])

        summary[model] = {
            "average_grade_score": avg_score,
            "grade_distribution": dict(stats["grade_distribution"]),
        }

    return summary


def save_results(summary, input_file):
    output_file = os.path.join(
        os.path.dirname(input_file),
        "usability_evaluation_analysis_individual.json"
    )

    with open(output_file, "w") as f:
        json.dump({"model_summary": summary}, f, indent=2)

    print(f"Saved analysis to {output_file}")


def main():
    BASE_DIR = Path(__file__).resolve().parent
    input_file = BASE_DIR / "final_results/model_responses_individual_evaluation.json"  # change if needed
    data = load_data(input_file)

    summary = analyze(data)
    save_results(summary, input_file)


if __name__ == "__main__":
    main()