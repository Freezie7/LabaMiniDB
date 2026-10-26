# MiniDB

Мини-СУБД на Python для лабораторной №1. Данные лежат в текстовых файлах, готовые базы и библиотеки не используются.

## Запуск

```bash
python seed.py
python cli.py
```

`seed.py` создаёт папку `data/` и заполняет её тестовыми данными (5 datasets, 5 models, 20 experiments). Готовая `data/` уже есть в репозитории, так что можно сразу запускать `cli.py`.

## Таблицы

- datasets: id, name, task, size
- models: id, name, version
- experiments: id, dataset_id, model_id, accuracy, status

`experiments.dataset_id` ссылается на `datasets.id`, `experiments.model_id` на `models.id`.

## Что умеет

- создавать таблицы (типы INT, FLOAT, STRING, первичный и внешний ключ)
- insert, select, update, delete
- выбор столбцов и фильтр в select: `=`, `!=`, `>`, `<`, `>=`, `<=`
- id ставится сам, дубликаты нельзя
- проверка внешних ключей: нельзя добавить experiment с несуществующим dataset или model и нельзя удалить запись, на которую есть ссылки
- при ошибке выводится сообщение

## Команды

```
tables
describe experiments
create <таблица> id:int:pk name:string dataset_id:int:fk=datasets.id
insert datasets name="dataset 6" task=classification size=70000
select experiments
select experiments id,accuracy where accuracy > 0.8
update experiments set status=completed where id=3
delete experiments where id=20
help
exit
```

Значения с пробелами пишутся в кавычках. В update и delete where обязателен.

## Код

- `cli.py`: консоль
- `database.py`: операции и проверки (типы, дубликаты, внешние ключи)
- `table.py`: чтение и запись файла таблицы
- `seed.py`: тестовые данные

## Как хранятся данные

Одна таблица это один файл в `data/`. Первая строка описывает столбцы, дальше записи через `;`:

```
id:INT:PK;dataset_id:INT:FK=datasets.id;model_id:INT:FK=models.id;accuracy:FLOAT;status:STRING
1;1;1;0.91;completed
2;1;2;0.88;completed
```

insert дописывает строку в конец файла, update и delete переписывают файл заново, select читает файл целиком. Новый id это максимальный id плюс один.

## Ограничения

- в строках нельзя `;` и перенос строки
- при insert нужно указывать все поля, кроме id
