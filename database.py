import operator
import os

from table import Table, create_table_files


class DBError(Exception):
    pass


OPERATORS = {
    "=": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}

TYPES = ["INT", "STRING", "FLOAT"]


def col(name, type_, pk=False, fk=None):
    # описание столбца, fk это (таблица, столбец)
    return {"name": name, "type": type_, "pk": pk, "fk": fk}


class Database:
    def __init__(self, folder):
        self.folder = folder
        self.tables = {}
        if not os.path.exists(folder):
            os.makedirs(folder)

        # при открытии читаем все .txt файлы (по одному на таблицу) из папки
        for filename in sorted(os.listdir(folder)):
            if filename.endswith(".txt"):
                name = filename[:-len(".txt")]
                self.tables[name] = Table(folder, name)

    def get_table(self, name):
        if name not in self.tables:
            raise DBError("Таблица '%s' не найдена" % name)
        return self.tables[name]

    def get_pk(self, table):
        for c in table.columns:
            if c["pk"]:
                return c

    def convert_value(self, column, value):
        # приводим значение к типу столбца
        name = column["name"]

        if column["type"] == "INT":
            if isinstance(value, float):
                raise DBError("Поле '%s' должно быть целым числом (INT)" % name)
            try:
                number = int(value)
            except (ValueError, TypeError):
                raise DBError("Поле '%s' должно быть целым числом (INT), а получено '%s'" % (name, value))
            return number

        if column["type"] == "FLOAT":
            try:
                return float(value)
            except (ValueError, TypeError):
                raise DBError("Поле '%s' должно быть числом (FLOAT), а получено '%s'" % (name, value))

        text = str(value)
        if ";" in text or "\n" in text or "\r" in text:
            raise DBError("В поле '%s' нельзя использовать ; и перенос строки" % name)
        return text

    def row_exists(self, table_name, column_name, value):
        table = self.get_table(table_name)
        for offset, row in table.read_all():
            if row[column_name] == value:
                return True
        return False

    def check_foreign_keys(self, table, row):
        for c in table.columns:
            if c["fk"] is None:
                continue
            ref_table, ref_col = c["fk"]
            value = row[c["name"]]
            if not self.row_exists(ref_table, ref_col, value):
                raise DBError("Нарушение внешнего ключа: в таблице '%s' нет записи с %s = %s"
                              % (ref_table, ref_col, value))

    def find_rows(self, table, where):
        # where это (столбец, операция, значение), если None - берём все записи
        all_rows = table.read_all()
        if where is None:
            return all_rows

        column_name, op, raw_value = where
        column = table.get_column(column_name)
        if column is None:
            raise DBError("В таблице '%s' нет поля '%s'" % (table.name, column_name))
        if op not in OPERATORS:
            raise DBError("Неизвестная операция '%s'" % op)

        value = self.convert_value(column, raw_value)
        result = []
        for offset, row in all_rows:
            if OPERATORS[op](row[column_name], value):
                result.append((offset, row))
        return result

    def create_table(self, name, columns):
        if not name.isidentifier():
            raise DBError("Неправильное имя таблицы '%s'" % name)
        if name in self.tables:
            raise DBError("Таблица '%s' уже существует" % name)

        names = []
        pk_count = 0
        for c in columns:
            if not c["name"].isidentifier():
                raise DBError("Неправильное имя поля '%s'" % c["name"])
            if c["name"] in names:
                raise DBError("Поле '%s' указано дважды" % c["name"])
            names.append(c["name"])

            if c["type"] not in TYPES:
                raise DBError("Неизвестный тип '%s' (есть INT, STRING, FLOAT)" % c["type"])

            if c["pk"]:
                pk_count += 1
                if c["type"] != "INT":
                    raise DBError("PRIMARY KEY должен быть типа INT")

            if c["fk"] is not None:
                ref_table, ref_col = c["fk"]
                if ref_table not in self.tables:
                    raise DBError("FK: таблица '%s' не найдена" % ref_table)
                target = self.tables[ref_table].get_column(ref_col)
                if target is None or not target["pk"]:
                    raise DBError("FK должен ссылаться на PRIMARY KEY таблицы '%s'" % ref_table)
                if target["type"] != c["type"]:
                    raise DBError("Тип поля '%s' не совпадает с '%s.%s'" % (c["name"], ref_table, ref_col))

        if pk_count != 1:
            raise DBError("В таблице должен быть ровно один PRIMARY KEY")

        self.tables[name] = create_table_files(self.folder, name, columns)

    def insert(self, table_name, values):
        # values - словарь {поле: значение}, возвращает id новой записи
        table = self.get_table(table_name)

        for name in values:
            if table.get_column(name) is None:
                raise DBError("В таблице '%s' нет поля '%s'" % (table_name, name))

        row = {}
        for c in table.columns:
            name = c["name"]
            if name in values:
                row[name] = self.convert_value(c, values[name])
            elif c["pk"]:
                row[name] = table.get_next_id()   # авто-ID
            else:
                raise DBError("Не указано значение для поля '%s'" % name)

        pk = self.get_pk(table)
        pk_value = row[pk["name"]]
        if self.row_exists(table_name, pk["name"], pk_value):
            raise DBError("Дубликат: в таблице '%s' уже есть запись с %s = %s"
                          % (table_name, pk["name"], pk_value))

        self.check_foreign_keys(table, row)

        table.append(row)
        return pk_value

    def select(self, table_name, columns=None, where=None):
        # возвращает список словарей
        table = self.get_table(table_name)

        if columns is None:
            columns = table.column_names()
        for name in columns:
            if table.get_column(name) is None:
                raise DBError("В таблице '%s' нет поля '%s'" % (table_name, name))

        result = []
        for offset, row in self.find_rows(table, where):
            item = {}
            for name in columns:
                item[name] = row[name]
            result.append(item)
        return result

    def update(self, table_name, changes, where=None):
        # changes - словарь {поле: новое значение}, возвращает сколько записей изменили
        table = self.get_table(table_name)

        if len(changes) == 0:
            raise DBError("Не указано, что менять")

        converted = {}
        for name, raw in changes.items():
            column = table.get_column(name)
            if column is None:
                raise DBError("В таблице '%s' нет поля '%s'" % (table_name, name))
            if column["pk"]:
                raise DBError("Менять PRIMARY KEY нельзя")
            converted[name] = self.convert_value(column, raw)

        # сначала проверяем все записи, потом пишем, чтобы при ошибке ничего не поменялось
        new_rows = []
        for offset, row in self.find_rows(table, where):
            new_row = dict(row)
            new_row.update(converted)
            self.check_foreign_keys(table, new_row)
            new_rows.append((offset, new_row))

        table.update_rows(new_rows)
        return len(new_rows)

    def delete(self, table_name, where=None):
        # возвращает сколько записей удалили
        table = self.get_table(table_name)
        rows = self.find_rows(table, where)

        # нельзя удалять то, на что ссылаются другие таблицы
        for other in self.tables.values():
            for c in other.columns:
                if c["fk"] is None or c["fk"][0] != table_name:
                    continue
                ref_col = c["fk"][1]
                used = []
                for offset, other_row in other.read_all():
                    used.append(other_row[c["name"]])
                for offset, row in rows:
                    if row[ref_col] in used:
                        raise DBError("Нельзя удалить: на запись %s = %s ссылается таблица '%s'"
                                      % (ref_col, row[ref_col], other.name))

        numbers = []
        for number, row in rows:
            numbers.append(number)
        table.delete_rows(numbers)
        return len(rows)
