import os

SEPARATOR = ";"


def make_header(columns):
    # [{"name": "id", "type": "INT", "pk": True, ...}, ...] -> "id:INT:PK;..."
    items = []
    for col in columns:
        item = col["name"] + ":" + col["type"]
        if col["pk"]:
            item += ":PK"
        if col["fk"]:
            item += ":FK=" + col["fk"][0] + "." + col["fk"][1]
        items.append(item)
    return SEPARATOR.join(items)


class Table:
    def __init__(self, folder, name):
        self.name = name
        self.path = os.path.join(folder, name + ".txt")
        self.columns = []
        self.read_header()

    def read_header(self):
        # первая строка файла, например: dataset_id:INT:FK=datasets.id
        f = open(self.path, encoding="utf-8")
        header = f.readline().strip()
        f.close()

        for item in header.split(SEPARATOR):
            parts = item.split(":")
            col = {"name": parts[0], "type": parts[1], "pk": False, "fk": None}
            for word in parts[2:]:
                if word == "PK":
                    col["pk"] = True
                elif word.startswith("FK="):
                    ref_table, ref_col = word[3:].split(".")
                    col["fk"] = (ref_table, ref_col)
            self.columns.append(col)

    def get_column(self, name):
        for col in self.columns:
            if col["name"] == name:
                return col
        return None

    def column_names(self):
        names = []
        for col in self.columns:
            names.append(col["name"])
        return names

    def read_rows(self):
        # читаем файл, каждую строку превращаем в словарь нужных типов
        f = open(self.path, encoding="utf-8")
        lines = f.read().split("\n")
        f.close()

        rows = []
        for line in lines[1:]:          # первую строку (шапку) пропускаем
            if line == "":
                continue
            values = line.split(SEPARATOR)
            row = {}
            for col, text in zip(self.columns, values):
                if col["type"] == "INT":
                    row[col["name"]] = int(text)
                elif col["type"] == "FLOAT":
                    row[col["name"]] = float(text)
                else:
                    row[col["name"]] = text
            rows.append(row)
        return rows

    def row_to_line(self, row):
        values = []
        for col in self.columns:
            values.append(str(row[col["name"]]))
        return SEPARATOR.join(values)

    def save_rows(self, rows):
        # переписываем файл целиком: шапка и все записи
        f = open(self.path, "w", encoding="utf-8")
        f.write(make_header(self.columns) + "\n")
        for row in rows:
            f.write(self.row_to_line(row) + "\n")
        f.close()

    def read_all(self):
        # возвращает список (номер записи в файле, запись)
        result = []
        rows = self.read_rows()
        for i in range(len(rows)):
            result.append((i, rows[i]))
        return result

    def append(self, row):
        f = open(self.path, "a", encoding="utf-8")
        f.write(self.row_to_line(row) + "\n")
        f.close()

    def update_rows(self, changed):
        # changed - список (номер записи, новая запись)
        rows = self.read_rows()
        for i, new_row in changed:
            rows[i] = new_row
        self.save_rows(rows)

    def delete_rows(self, numbers):
        # numbers - номера записей, которые нужно убрать из файла
        rows = self.read_rows()
        kept = []
        for i in range(len(rows)):
            if i not in numbers:
                kept.append(rows[i])
        self.save_rows(kept)

    def get_next_id(self):
        # следующий id = самый большой из существующих + 1
        for col in self.columns:
            if col["pk"]:
                pk_name = col["name"]
        biggest = 0
        for row in self.read_rows():
            if row[pk_name] > biggest:
                biggest = row[pk_name]
        return biggest + 1


def create_table_files(folder, name, columns):
    # новый файл таблицы: пока только шапка
    f = open(os.path.join(folder, name + ".txt"), "w", encoding="utf-8")
    f.write(make_header(columns) + "\n")
    f.close()
    return Table(folder, name)
