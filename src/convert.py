import re
import json
import os

def convert_sqlite_to_pg(sql: str) -> str:
    # 1) date(...)      → col::date
    sql = re.sub(r"\bdate\(\s*([^)]+)\)", r"\1::date", sql, flags=re.IGNORECASE)
    # 2) datetime(...)  → to_timestamp(...)
    sql = re.sub(r"\bdatetime\(\s*([^)]+)\)", r"to_timestamp(\1)", sql, flags=re.IGNORECASE)
    # 3) strftime → to_char
    sql = re.sub(
        r"strftime\(\s*'(%[YmdHMS-]+)'\s*,\s*([^)]+)\)",
        lambda m: f"to_char({m.group(2)}, '{m.group(1)[1:]}')",
        sql,
        flags=re.IGNORECASE
    )
    # 4) || concatenador → concat()
    sql = re.sub(
        r"(\w+)\s*\|\|\s*(\w+)",
        r"concat(\1, \2)",
        sql
    )
    # 5) escaped quotes e barras
    sql = sql.replace("\\r\\n", "\n").replace("\\/", "/")
    return sql

def port_json(input_path: str, output_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        if "answer" in item:
            item["answer"] = convert_sqlite_to_pg(item["answer"])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Convertido em: {output_path}")

if __name__ == "__main__":
    # obtém a pasta onde este script está
    base = os.path.dirname(__file__)
    # monta caminhos absolutos
    src = os.path.join(base, "arq", "data_cybersyn-financial-data.json")
    dst = os.path.join(base, "arq", "data_cybersyn-financial-data-pg.json")

    # garante que o arquivo de entrada existe
    if not os.path.isfile(src):
        raise FileNotFoundError(f"Arquivo não encontrado: {src}")

    port_json(src, dst)

