# Python 调用 MySQL 核心知识

## 1. 作用与目标

在 Python 项目中调用 MySQL，核心目的是完成这几类事情：

- 建立数据库连接
- 执行查询语句
- 执行新增、修改、删除语句
- 处理事务
- 关闭连接并回收资源

当前项目的依赖更偏向使用官方驱动 `mysql-connector-python`。

## 2. 常见驱动选择

Python 连接 MySQL 常见有两类驱动：

- `mysql-connector-python`
  - MySQL 官方驱动
  - 当前项目更适合优先使用它
- `pymysql`
  - 纯 Python 实现
  - 安装简单，也很常见

如果项目里已经明确依赖了 `mysql-connector-python`，最好统一使用这一套，不要混用两种风格。

## 3. 安装方式

```bash
pip install mysql-connector-python
```

如果使用 `requirements.txt`，通常会写成：

```txt
mysql-connector-python~=9.4.0
```

## 4. 建立数据库连接

最基本的连接方式如下：

```python
import mysql.connector

conn = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="your_password",
    database="menu",
    charset="utf8mb4"
)
```

连接参数的含义：

- `host`：数据库地址
- `port`：数据库端口，MySQL 默认是 `3306`
- `user`：用户名
- `password`：密码
- `database`：默认连接的数据库名
- `charset`：字符集，建议使用 `utf8mb4`

判断是否连接成功：

```python
if conn.is_connected():
    print("MySQL connected")
```

## 5. 基本查询流程

Python 调用 MySQL 的标准流程通常是：

1. 建立连接
2. 创建游标 `cursor`
3. 执行 SQL
4. 读取结果
5. 关闭游标
6. 关闭连接

示例：

```python
import mysql.connector

conn = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="your_password",
    database="menu",
    charset="utf8mb4"
)

cursor = conn.cursor()
cursor.execute("SELECT id, name, price FROM menu_items")

rows = cursor.fetchall()
for row in rows:
    print(row)

cursor.close()
conn.close()
```

## 6. 游标 cursor 的作用

`cursor` 可以理解为执行 SQL 的操作对象。

常见用法：

- `cursor.execute(sql, params)`：执行一条 SQL
- `cursor.executemany(sql, data)`：批量执行多条参数化 SQL
- `cursor.fetchone()`：取一条结果
- `cursor.fetchall()`：取全部结果

普通游标返回的结果通常是元组：

```python
(1, "宫保鸡丁", 28.0)
```

如果希望结果按字典返回，可以这样写：

```python
cursor = conn.cursor(dictionary=True)
cursor.execute("SELECT id, name, price FROM menu_items")
rows = cursor.fetchall()
print(rows[0])
```

结果类似：

```python
{"id": 1, "name": "宫保鸡丁", "price": 28.0}
```

## 7. 参数化查询

不要手动拼接 SQL 字符串，应该使用参数化查询。

错误写法：

```python
name = "可乐"
sql = f"SELECT * FROM menu_items WHERE name = '{name}'"
cursor.execute(sql)
```

这样会带来 SQL 注入风险。

正确写法：

```python
name = "可乐"
sql = "SELECT * FROM menu_items WHERE name = %s"
cursor.execute(sql, (name,))
```

多个参数示例：

```python
sql = "SELECT * FROM menu_items WHERE category = %s AND price <= %s"
cursor.execute(sql, ("饮品", 10))
```

## 8. 查询单条与多条数据

查询单条：

```python
sql = "SELECT id, name FROM menu_items WHERE id = %s"
cursor.execute(sql, (1,))
row = cursor.fetchone()
print(row)
```

查询多条：

```python
sql = "SELECT id, name FROM menu_items"
cursor.execute(sql)
rows = cursor.fetchall()
for row in rows:
    print(row)
```

## 9. 插入、更新、删除

### 9.1 插入数据

```python
sql = """
INSERT INTO menu_items (name, category, price)
VALUES (%s, %s, %s)
"""
cursor.execute(sql, ("红茶", "饮品", 8.0))
conn.commit()
```

### 9.2 更新数据

```python
sql = "UPDATE menu_items SET price = %s WHERE id = %s"
cursor.execute(sql, (9.0, 1))
conn.commit()
```

### 9.3 删除数据

```python
sql = "DELETE FROM menu_items WHERE id = %s"
cursor.execute(sql, (1,))
conn.commit()
```

要点：

- `SELECT` 不需要 `commit()`
- `INSERT`、`UPDATE`、`DELETE` 一般需要 `commit()`

## 10. 事务处理

事务的核心目标是保证一组操作要么全部成功，要么全部失败。

示例：

```python
import mysql.connector

conn = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="your_password",
    database="menu"
)

cursor = conn.cursor()

try:
    cursor.execute(
        "UPDATE menu_items SET price = %s WHERE id = %s",
        (20.0, 1)
    )
    cursor.execute(
        "UPDATE menu_items SET price = %s WHERE id = %s",
        (18.0, 2)
    )
    conn.commit()
except mysql.connector.Error:
    conn.rollback()
    raise
finally:
    cursor.close()
    conn.close()
```

关键点：

- 成功后执行 `commit()`
- 失败后执行 `rollback()`

## 11. 异常处理

推荐捕获数据库异常，避免程序直接崩溃。

```python
import mysql.connector

try:
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="your_password",
        database="menu"
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM menu_items")
    rows = cursor.fetchall()
    print(rows)
except mysql.connector.Error as e:
    print(f"MySQL error: {e}")
finally:
    if "cursor" in locals():
        cursor.close()
    if "conn" in locals() and conn.is_connected():
        conn.close()
```

## 12. 推荐封装方式

实际项目中不要在每个业务函数里重复写连接代码，通常会把数据库访问封装成工具函数或类。

简单函数封装示例：

```python
import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="your_password",
        database="menu",
        charset="utf8mb4"
    )


def get_menu_items():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM menu_items")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
```

这种做法的好处：

- 连接逻辑集中管理
- 业务代码更简洁
- 后续切换配置更容易

## 13. 配置管理

数据库账号密码不要写死在代码里，应该放到环境变量或配置文件中。

示例：

```python
import os
import mysql.connector

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "menu"),
    charset="utf8mb4"
)
```

常见环境变量命名：

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`

## 14. 与当前项目更贴近的示例

如果当前项目需要查询 `menu` 数据库中的 `menu_items` 表，可以这样写：

```python
import os
import mysql.connector


def get_menu_items_list():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "menu"),
        charset="utf8mb4"
    )

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM menu_items")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
```

## 15. 常见问题

### 15.1 Access denied

通常表示：

- 用户名或密码错误
- 当前用户没有目标数据库权限
- 主机访问权限未开放

### 15.2 Unknown database

通常表示数据库名写错，或者数据库还没有创建。

### 15.3 查询结果乱码

通常与字符集有关，建议统一使用：

- MySQL 端使用 `utf8mb4`
- Python 连接时指定 `charset="utf8mb4"`

### 15.4 忘记 commit

如果执行了新增、修改、删除，但数据库里没变化，通常是忘了执行 `conn.commit()`。

### 15.5 连接未关闭

如果连接或游标长期不关闭，容易造成：

- 连接数占满
- 资源泄漏
- 后续请求变慢

## 16. 核心记忆点

把 Python 调用 MySQL 压缩成最重要的几句话，就是：

1. 先 `connect()` 建立连接
2. 再 `cursor()` 执行 SQL
3. 查询用 `fetchone()` 或 `fetchall()`
4. 写操作后要 `commit()`
5. 异常时要 `rollback()`
6. 最后关闭 `cursor` 和 `conn`
7. 永远使用参数化查询，不手拼 SQL

## 17. 一份最小可运行模板

```python
import mysql.connector


def main():
    conn = mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="your_password",
        database="menu",
        charset="utf8mb4"
    )
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM menu_items")
        rows = cursor.fetchall()
        print(rows)
    except mysql.connector.Error as e:
        print(f"MySQL error: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
```
