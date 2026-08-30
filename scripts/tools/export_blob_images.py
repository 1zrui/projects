import oracledb, os

# thin 模式：BLOB 直接以 bytes 返回，不需要 Oracle Client
oracledb.defaults.fetch_lobs = False

CONN = dict(
    user="zlhis",
    password="his",
    host="119.29.238.30",
    port=1521,
    service_name="XEPDB1",
)

# ===== TODO: 按实际填写 =====
TABLE = "表名"            # 例如 病案主页相关表
BLOB_COL = "BLOB字段名"    # 存图片的 BLOB 列
NAME_COL = "文件名来源列"   # 主键/业务号，用来给导出文件命名
IMG_EXT = "jpg"           # 实际格式：jpg / png / bmp
# ===========================

OUT_DIR = r"D:\Downloads\blob_export"
os.makedirs(OUT_DIR, exist_ok=True)

conn = oracledb.connect(**CONN)
cur = conn.cursor()
cur.execute(f"SELECT {NAME_COL}, {BLOB_COL} FROM {TABLE} WHERE {BLOB_COL} IS NOT NULL")
n = 0
for name, blob in cur:
    if not blob:
        continue
    fn = os.path.join(OUT_DIR, f"{name}.{IMG_EXT}")
    with open(fn, "wb") as f:
        f.write(blob)
    n += 1
print(f"导出 {n} 个文件 -> {OUT_DIR}")
cur.close()
conn.close()
