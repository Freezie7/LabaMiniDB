import re
import shlex
import sys

from database import Database, DBError, col
import seed

HELP = """Команды:
  tables
  describe <таблица>
  create <таблица> id:int:pk name:string dataset_id:int:fk=datasets.id
  insert <таблица> поле=значение ...
  select <таблица> [поле1,поле2 или *] [where поле оператор значение]
  update <таблица> set поле=значение ... where поле оператор значение
  delete <таблица> where поле оператор значение
  seed        заполнить тестовыми данными
  help
  exit
Операторы: = != > < >= <=
Если в значении есть пробелы, берите его в кавычки: name="dataset 6"
"""


def print_table(columns, rows):
    widths = []
    for name in columns:
        widths.append(len(name))
    for row in rows:
        for i in range(len(columns)):
            widths[i] = max(widths[i], len(str(row[columns[i]])))

    header = []
    for i in range(len(columns)):
        header.append(columns[i].ljust(widths[i]))
    print(" | ".join(header))

    lines = []
    for w in widths:
        lines.append("-" * w)
    print("-+-".join(lines))

    for row in rows:
        cells = []
        for i in range(len(columns)):
            cells.append(str(row[columns[i]]).ljust(widths[i]))
        print(" | ".join(cells))
    print("Строк: %d" % len(rows))


def parse_where(tokens):
    text = " ".join(tokens)
    match = re.match(r"^(\w+)\s*(>=|<=|!=|=|>|<)\s*(.+)$", text)
    if match is None:
        raise DBError("Неверное условие '%s'. Пример: where accuracy > 0.8" % text)
    return (match.group(1), match.group(2), match.group(3))


def split_where(tokens):
    # делим команду на то, что до where, и само условие
    for i in range(len(tokens)):
        if tokens[i].lower() == "where":
            return tokens[:i], parse_where(tokens[i + 1:])
    return tokens, None


def parse_assignments(tokens): # ['a=1', 'b=text'] -> {'a': '1', 'b': 'text'}
    result = {}
    for token in tokens:
        if "=" not in token:
            raise DBError("Ожидалось поле=значение, а получено '%s'" % token)
        name, value = token.split("=", 1)
        result[name] = value
    return result


def parse_column(spec):# 'dataset_id:int:fk=datasets.id' -> описание столбца
    parts = spec.split(":")
    if len(parts) < 2:
        raise DBError("Неверное описание поля '%s'. Пример: id:int:pk" % spec)
    pk = False
    fk = None
    for extra in parts[2:]:
        if extra.lower() == "pk":
            pk = True
        elif extra.lower().startswith("fk=") and "." in extra:
            fk = tuple(extra[3:].split(".", 1))
        else:
            raise DBError("Неизвестный модификатор '%s' у поля '%s'" % (extra, parts[0]))
    return col(parts[0], parts[1].upper(), pk=pk, fk=fk)


def run_command(db, line):
    try:
        tokens = shlex.split(line)
    except ValueError:
        raise DBError("Не закрыта кавычка")
    if len(tokens) == 0:
        return
    command = tokens[0].lower()

    if command == "help":
        print(HELP)

    elif command == "tables":
        for name in db.tables:
            print("%s (%d записей)" % (name, len(db.select(name))))

    elif command == "describe":
        if len(tokens) < 2:
            raise DBError("Использование: describe <таблица>")
        table = db.get_table(tokens[1])
        for c in table.columns:
            text = "  %s %s" % (c["name"], c["type"])
            if c["pk"]:
                text += " PRIMARY KEY"
            if c["fk"]:
                text += " -> %s.%s" % c["fk"]
            print(text)

    elif command == "create":
        if len(tokens) < 3:
            raise DBError("Использование: create <таблица> поле:тип[:pk][:fk=таблица.поле] ...")
        columns = []
        for spec in tokens[2:]:
            columns.append(parse_column(spec))
        db.create_table(tokens[1], columns)
        print("Таблица '%s' создана" % tokens[1])

    elif command == "insert":
        if len(tokens) < 3:
            raise DBError("Использование: insert <таблица> поле=значение ...")
        new_id = db.insert(tokens[1], parse_assignments(tokens[2:]))
        print("Добавлено, id = %s" % new_id)

    elif command == "select":
        if len(tokens) < 2:
            raise DBError("Использование: select <таблица> [поля] [where ...]")
        before_where, where = split_where(tokens)
        table_name = before_where[1]
        rest = before_where[2:]
        if len(rest) == 0 or rest == ["*"]:
            columns = None
        else:
            columns = "".join(rest).split(",")
        rows = db.select(table_name, columns, where)
        if columns is None:
            columns = db.get_table(table_name).column_names()
        print_table(columns, rows)

    elif command == "update":
        before_where, where = split_where(tokens)
        if where is None:
            raise DBError("В update нужен where")
        if len(before_where) < 4 or before_where[2].lower() != "set":
            raise DBError("Использование: update <таблица> set поле=значение ... where ...")
        count = db.update(before_where[1], parse_assignments(before_where[3:]), where)
        print("Изменено записей: %d" % count)

    elif command == "delete":
        before_where, where = split_where(tokens)
        if where is None:
            raise DBError("В delete нужен where")
        if len(before_where) != 2:
            raise DBError("Использование: delete <таблица> where ...")
        count = db.delete(before_where[1], where)
        print("Удалено записей: %d" % count)

    elif command == "seed":
        if seed.fill(db):
            print("Тестовые данные добавлены")
        else:
            print("В базе уже есть данные")

    else:
        raise DBError("Неизвестная команда '%s'. Напишите help" % command)


def main():
    folder = "data"
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    db = Database(folder)
    print("MiniDB, база: %s. Список команд - help" % folder)

    while True:
        try:
            line = input("minidb> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.lower() in ("exit", "quit"):
            break
        try:
            run_command(db, line)
        except DBError as error:
            print("Ошибка:", error)


if __name__ == "__main__":
    main()
