import sys

from database import Database, col

DATASETS = [
    ("dataset 1", "classification", 70000),
    ("dataset 2", "classification", 60000),
    ("dataset 3", "sentiment", 50000),
    ("dataset 4", "regression", 506),
    ("dataset 5", "detection", 118000),
]

MODELS = [
    ("model 1", "1.0"),
    ("model 2", "2.1"),
    ("model 3", "1.0"),
    ("model 4", "3.0"),
    ("model 5", "1.7"),
]

# (dataset_id, model_id, accuracy, status)
EXPERIMENTS = [
    (1, 1, 0.91, "completed"),
    (1, 2, 0.88, "completed"),
    (2, 1, 0.76, "running"),
    (1, 3, 0.97, "completed"),
    (1, 4, 0.83, "completed"),
    (2, 2, 0.71, "completed"),
    (2, 3, 0.89, "completed"),
    (2, 4, 0.79, "failed"),
    (3, 1, 0.84, "completed"),
    (3, 2, 0.80, "running"),
    (3, 5, 0.93, "completed"),
    (3, 4, 0.87, "completed"),
    (4, 1, 0.65, "completed"),
    (4, 2, 0.72, "completed"),
    (4, 5, 0.69, "failed"),
    (5, 3, 0.58, "running"),
    (5, 4, 0.62, "completed"),
    (5, 2, 0.55, "completed"),
    (5, 5, 0.60, "running"),
    (4, 3, 0.74, "completed"),
]


def create_tables(db):
    if "datasets" not in db.tables:
        db.create_table("datasets", [
            col("id", "INT", pk=True),
            col("name", "STRING"),
            col("task", "STRING"),
            col("size", "INT"),
        ])
    if "models" not in db.tables:
        db.create_table("models", [
            col("id", "INT", pk=True),
            col("name", "STRING"),
            col("version", "STRING"),
        ])
    if "experiments" not in db.tables:
        db.create_table("experiments", [
            col("id", "INT", pk=True),
            col("dataset_id", "INT", fk=("datasets", "id")),
            col("model_id", "INT", fk=("models", "id")),
            col("accuracy", "FLOAT"),
            col("status", "STRING"),
        ])


def fill(db):
    # возвращает False, если данные уже были
    create_tables(db)
    if len(db.select("datasets")) > 0:
        return False

    for name, task, size in DATASETS:
        db.insert("datasets", {"name": name, "task": task, "size": size})
    for name, version in MODELS:
        db.insert("models", {"name": name, "version": version})
    for dataset_id, model_id, accuracy, status in EXPERIMENTS:
        db.insert("experiments", {
            "dataset_id": dataset_id,
            "model_id": model_id,
            "accuracy": accuracy,
            "status": status,
        })
    return True


if __name__ == "__main__":
    folder = "data"
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    db = Database(folder)
    if fill(db):
        print("База '%s' заполнена: %d datasets, %d models, %d experiments" % (
            folder, len(DATASETS), len(MODELS), len(EXPERIMENTS)))
    else:
        print("В базе '%s' уже есть данные, ничего не добавлено" % folder)
