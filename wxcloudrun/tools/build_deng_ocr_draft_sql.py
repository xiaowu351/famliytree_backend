import hashlib
import re
from collections import defaultdict
from pathlib import Path


TREE_ID = "tree_deng_chengzizhen_001"
NOW_SQL = "DATE_FORMAT(NOW(), '%Y-%m-%dT%H:%i:%s')"

BASE_LINEAGE = [
    (52, "晦", "", "长子", ""),
    (53, "遄", "晦", "长子", ""),
    (54, "灿", "遄", "长子", ""),
    (55, "勤成", "灿", "次子", "直"),
    (56, "宁", "勤成", "之子", ""),
    (57, "喜", "宁", "次子", ""),
    (58, "骥", "喜", "之子", ""),
    (59, "志", "骥", "长子", ""),
    (60, "纯", "志", "长子", ""),
    (61, "期", "纯", "之子", ""),
    (62, "岳", "期", "长子", ""),
    (63, "节", "岳", "次子", ""),
    (64, "烈", "节", "长子", ""),
    (65, "崇", "烈", "之子", "峙"),
    (66, "宇", "崇", "之子", ""),
    (67, "桓", "宇", "之子", ""),
    (68, "青", "桓", "之子", ""),
    (69, "阅", "青", "次子", ""),
    (70, "陵", "阅", "长子", ""),
    (71, "裕", "陵", "之子", ""),
    (72, "参", "裕", "长子", ""),
    (73, "本", "参", "之子", ""),
    (74, "稽", "本", "之子", ""),
    (75, "离", "稽", "之子", ""),
    (76, "旭", "离", "之子", ""),
    (77, "刊", "旭", "之子", "邵"),
    (78, "毅", "刊", "长子", ""),
    (79, "徵", "毅", "之子", ""),
    (80, "乾", "徵", "长子", ""),
    (81, "拯", "乾", "之子", ""),
    (82, "圣求", "拯", "之子", "润甫"),
    (83, "协", "圣求", "之子", ""),
    (84, "均", "协", "长子", ""),
    (85, "守", "均", "之子", ""),
    (86, "瓒", "守", "之子", ""),
    (87, "发玙", "瓒", "之子", ""),
    (88, "敦让", "发玙", "之子", ""),
]

GEN_PREFIXES = {
    "翘": 102,
    "瞻": 103,
    "万": 104,
    "里": 105,
    "国": 106,
    "咸": 107,
    "沐": 108,
    "九": 109,
    "重": 110,
    "仁": 111,
    "必": 112,
    "见": 113,
    "安": 114,
    "居": 115,
    "宅": 116,
    "理": 116,
    "子": 116,
}

NOISE = set("上下系庆甫公之长次嗣承年月日民国男女丨一二三四五六七八九十0123456789")
CONNECTOR_RE = re.compile(r"[→↓—\-|丨｜]+" )
TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,4}")


def sql_quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def member_id(name: str, generation: int, source: str) -> str:
    digest = hashlib.md5(f"{generation}:{name}:{source}".encode("utf-8")).hexdigest()[:8]
    return f"deng_czz_g{generation}_{digest}"


def generation_for(name: str) -> int | None:
    for prefix, generation in GEN_PREFIXES.items():
        if name.startswith(prefix):
            return generation
    return None


def is_candidate(token: str) -> bool:
    if len(token) < 2 or len(token) > 4:
        return False
    if token in {"庆甫", "系下", "长子", "次子", "之子", "嗣子", "民国", "九江", "城子"}:
        return False
    if all(ch in NOISE for ch in token):
        return False
    return generation_for(token) is not None


def extract_edges(raw: str) -> list[tuple[str, str, str]]:
    edges: list[tuple[str, str, str]] = []
    current_page = ""
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("===== image"):
            current_page = line.replace("=", "").strip()
            continue
        if not any(mark in line for mark in ("→", "丨", "|", "｜", "—", "↓")):
            continue

        normalized = line.replace("一", "—").replace("十", "|")
        parts = [part for part in CONNECTOR_RE.split(normalized) if part]
        names: list[str] = []
        for part in parts:
            for token in TOKEN_RE.findall(part):
                if is_candidate(token):
                    names.append(token)

        for parent, child in zip(names, names[1:]):
            parent_gen = generation_for(parent)
            child_gen = generation_for(child)
            if parent_gen and child_gen and 0 < child_gen - parent_gen <= 2:
                edges.append((parent, child, current_page))
    return edges


def build_members(edges: list[tuple[str, str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    by_key: dict[tuple[int, str], str] = {}
    name_sources: dict[tuple[int, str], set[str]] = defaultdict(set)
    parent_by_key: dict[tuple[int, str], tuple[int, str]] = {}

    previous_id = ""
    for generation, name, parent_name, rank_type, alias_name in BASE_LINEAGE:
        row_id = member_id(name, generation, "word-table")
        by_key[(generation, name)] = row_id
        name_sources[(generation, name)].add("Word表格")
        rows.append({
            "id": row_id,
            "name": name,
            "generation": generation,
            "parent_id": previous_id,
            "rank_type": rank_type,
            "alias_name": alias_name,
            "desc": "据《邓氏宗谱九江县城子镇》Word表格录入。",
        })
        previous_id = row_id

    for parent_name, child_name, source in edges:
        parent_gen = generation_for(parent_name)
        child_gen = generation_for(child_name)
        if not parent_gen or not child_gen:
            continue
        parent_key = (parent_gen, parent_name)
        child_key = (child_gen, child_name)
        name_sources[parent_key].add(source)
        name_sources[child_key].add(source)
        parent_by_key.setdefault(child_key, parent_key)
        by_key.setdefault(parent_key, member_id(parent_name, parent_gen, source))
        by_key.setdefault(child_key, member_id(child_name, child_gen, source))

    existing_ids = {row["id"] for row in rows}
    for key, row_id in sorted(by_key.items(), key=lambda item: (item[0][0], item[0][1])):
        if row_id in existing_ids:
            continue
        generation, name = key
        parent_key = parent_by_key.get(key)
        parent_id = by_key.get(parent_key, "") if parent_key else ""
        sources = "、".join(sorted(name_sources[key]))
        rows.append({
            "id": row_id,
            "name": name,
            "generation": generation,
            "parent_id": parent_id,
            "rank_type": "",
            "alias_name": "",
            "desc": f"OCR草稿录入，来源页：{sources}。请人工核对原图后再正式导入。",
        })
    return rows


def render_sql(rows: list[dict[str, object]]) -> str:
    columns = [
        "id", "tree_id", "name", "gender", "is_alive", "parent_id", "spouse_id", "desc",
        "create_time", "generation", "avatar_url", "surname", "rank_type", "marital_status",
        "birth_order", "alias_name", "other_name", "style_name", "pseudonym", "birth_date",
        "spouse_father", "education_school", "education_major", "education_degree", "occupation",
        "is_spouse", "spouse_type", "education_status", "adoption_type",
    ]

    values = []
    for row in rows:
        values.append("(" + ", ".join([
            sql_quote(str(row["id"])),
            sql_quote(TREE_ID),
            sql_quote(str(row["name"])),
            sql_quote("M"),
            "1",
            sql_quote(str(row["parent_id"])),
            sql_quote(""),
            sql_quote(str(row["desc"])),
            NOW_SQL,
            str(row["generation"]),
            sql_quote(""),
            sql_quote("邓"),
            sql_quote(str(row["rank_type"])),
            sql_quote(""),
            sql_quote(""),
            sql_quote(str(row["alias_name"])),
            sql_quote(""),
            sql_quote(""),
            sql_quote(""),
            sql_quote(""),
            sql_quote(""),
            sql_quote(""),
            sql_quote(""),
            sql_quote(""),
            sql_quote(""),
            "0",
            sql_quote(""),
            sql_quote(""),
            sql_quote(""),
        ]) + ")")

    return "\n".join([
        "-- 邓氏宗谱九江县城子镇初始化数据（OCR扩展草稿）",
        "-- 来源：新--邓氏宗谱九江县城子镇（定稿）.docx",
        "-- 说明：本文件包含 Word 表格直系数据，以及从 73 张扫描图片中 OCR 抽取的可见箭头/竖线关系。",
        "-- 注意：OCR 识别存在错字、漏线、断链；带“OCR草稿录入”的成员必须人工核对原图后再正式导入商用库。",
        "START TRANSACTION;",
        "",
        f"DELETE FROM `members` WHERE `tree_id` = {sql_quote(TREE_ID)};",
        f"DELETE FROM `trees` WHERE `id` = {sql_quote(TREE_ID)};",
        "",
        "INSERT INTO `trees` (`id`, `surname`, `title`, `hall_name`, `region`, `create_time`, `update_time`, `creator_id`) VALUES",
        f"({sql_quote(TREE_ID)}, {sql_quote('邓')}, {sql_quote('邓氏宗谱九江县城子镇')}, {sql_quote('')}, {sql_quote('江西省九江市九江县城子镇龙江湖村邓家嘴')}, {NOW_SQL}, {NOW_SQL}, NULL);",
        "",
        "INSERT INTO `members` (`" + "`, `".join(columns) + "`) VALUES",
        ",\n".join(values) + ";",
        "",
        "COMMIT;",
        "",
    ])


def main() -> None:
    raw_path = Path("backend/wxcloudrun/data/deng_chengzizhen_ocr_raw.txt")
    raw = raw_path.read_text(encoding="utf-8")
    edges = extract_edges(raw)
    rows = build_members(edges)
    out_path = Path("backend/wxcloudrun/data/deng_chengzizhen_ocr_draft.sql")
    out_path.write_text(render_sql(rows), encoding="utf-8")
    print(f"edges={len(edges)}")
    print(f"members={len(rows)}")
    print(f"written={out_path}")


if __name__ == "__main__":
    main()
