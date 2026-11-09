#!/usr/bin/env bash
# doc-check.sh — 文档地图、词表与文件的对账（九项）
#
# 用法：
#   bash doc-check.sh [--root <项目根>] [--strict]
#
# 退出码：0 通过（可能有 WARN） / 1 有 FAIL（或 --strict 下有 WARN） / 64 用法错或找不到 AGENTS.md
#
# 有 DOC_MAP.md 时对账地图与词表；没有时按最小档处理，只允许 AGENTS.md、STATUS.md、README.md。
# 只查能对账的部分：结构、路径、枚举值、链接、标签是否在词表内。
# 不查内容质量，也不判标签是否说真话——那会成为打分器，还会让人以为漂移已被自动治理。

set -u

# 全程按字节比较。BSD awk 在 en_US.UTF-8 下用 strcoll，任意两个中文词都算相等，判断会悄悄出错
export LC_ALL=C

# 判定线都是初值，项目要调就改这里
MAX_AGENTS_LINES=120     # AGENTS.md 行数
MAX_VOCAB_LINES=50       # 词表块行数
MAX_READ_TAGS=12         # 时机标签个数
MIN_PARENT_DOCS=3        # 主题父级至少覆盖几份文档
MAX_PARENT_PCT=40        # 主题父级最多覆盖百分之几的文档
MIN_DOCS_FOR_FREQ=10     # 地图行数少于它时不查频率
CAP_EXEMPT_MAX_DOCS=20   # 地图行数不超过它时不查 40% 上限，小地图上这条线太紧
HEAD_SCAN_LINES=15       # 文档头要出现在前多少行

ROOT="."
STRICT=0

while [ $# -gt 0 ]; do
  case "$1" in
    --root)
      shift
      [ $# -gt 0 ] || { echo "--root 需要一个目录参数" >&2; exit 64; }
      ROOT="$1"
      ;;
    --root=*) ROOT="${1#--root=}" ;;
    --strict) STRICT=1 ;;
    -h|--help)
      sed -n '2,11p' "$0"
      exit 0
      ;;
    *) echo "未知参数：$1" >&2; exit 64 ;;
  esac
  shift
done

[ -d "$ROOT" ] || { echo "目录不存在：$ROOT" >&2; exit 64; }
ROOT=$(cd "$ROOT" && pwd -P) || { echo "无法进入目录：$ROOT" >&2; exit 64; }

AGENTS="$ROOT/AGENTS.md"
[ -f "$AGENTS" ] || {
  echo "找不到 AGENTS.md：$AGENTS" >&2
  echo "本脚本只认 AGENTS.md 作为入口；没有就先按 SKILL.md 第 4 步建立。" >&2
  exit 64
}

TMPD=$(mktemp -d "${TMPDIR:-/tmp}/doccheck.XXXXXX") || exit 64
trap 'rm -rf "$TMPD"' EXIT

MAP="$ROOT/DOC_MAP.md"
ROWS="$TMPD/rows"     # 路径 \t 层 \t 主题 \t 时机 \t 事件 \t 格式是否完整（标签用 | 分隔）
IDX="$TMPD/idx"       # 被覆盖的路径，一行一个
VOCAB="$TMPD/vocab"   # 类别 \t 标签
FILES="$TMPD/files"   # 参与扫描的 .md
EXCL="$TMPD/excl"     # 豁免 glob
MSGS="$TMPD/msgs"     # 当前检查待输出的消息
: > "$ROWS"
: > "$VOCAB"
: > "$EXCL"
: > "$MSGS"

FAIL=0
WARN=0

ok()    { printf '  OK    %s\n' "$1"; }
bad()   { printf '  FAIL  %s\n' "$1"; FAIL=$((FAIL+1)); }
warnf() { printf '  WARN  %s\n' "$1"; WARN=$((WARN+1)); }

summary() {
  echo ""
  echo "—— 汇总：${FAIL} 项 FAIL，${WARN} 项 WARN ——"
}

# flush <bad|warnf> <检查名>：输出 $MSGS 的前 5 条，其余只给总数，然后清空
flush() {
  local fn=$1 name=$2 total line
  total=$(wc -l < "$MSGS" | tr -d ' ')
  while IFS= read -r line; do
    "$fn" "$line"
  done < <(sed -n '1,5p' "$MSGS")
  if [ "$total" -gt 5 ]; then
    "$fn" "${name}：另有 $((total-5)) 条（只列前 5 条）"
    # 汇总按真实条数算，上面这行只占 1 项
    if [ "$fn" = bad ]; then FAIL=$((FAIL+total-6)); else WARN=$((WARN+total-6)); fi
  fi
  : > "$MSGS"
}

# 取出一段文本里的全部【标签】，用 | 连接；按字节和按字符处理的 awk 都能用
AWK_TAGS='
function tags(s,    out, i, j) {
  out = ""
  while ((i = index(s, "【")) > 0) {
    s = substr(s, i + length("【"))
    j = index(s, "】")
    if (j == 0) break
    out = out (out == "" ? "" : "|") substr(s, 1, j - 1)
    s = substr(s, j + length("】"))
  }
  return out
}'

echo "▶ doc-check | 根目录：$ROOT"

# ---------- 检查 1：地图可解析 ----------
if [ -f "$MAP" ]; then
  HAS_MAP=1
  awk "$AWK_TAGS"'
    /<!--[ \t]*docmap:begin[ \t]*-->/ { inb = 1; next }
    /<!--[ \t]*docmap:end[ \t]*-->/   { inb = 0; next }
    inb && /^- `/ {
      rest = substr($0, 4)
      e = index(rest, "`")
      if (e == 0) { print rest "\t\t\t\t\t0"; next }
      path = substr(rest, 1, e - 1)
      rest = substr(rest, e + 1)
      n = split(rest, c, "；")
      lvl = ""
      if (match(c[1], /^ L[0-3]/)) lvl = substr(c[1], RSTART + 1, 2)
      about = tags(c[1]); rd = tags(c[2]); wr = tags(c[3])
      good = (n == 3 && lvl != "" && about != "" && rd != "" && wr != "" &&
              index(c[1], "关于") > 0 && index(c[2], "时读") > 0 && index(c[3], "时改") > 0)
      print path "\t" lvl "\t" about "\t" rd "\t" wr "\t" good
    }
  ' "$MAP" > "$ROWS"
  ROWCOUNT=$(wc -l < "$ROWS" | tr -d ' ')
  if [ "$ROWCOUNT" -eq 0 ]; then
    bad "检查 1：DOC_MAP.md 里没有可解析的地图行（缺 docmap 标记，或行首不是「- 反引号路径」）"
    summary
    exit 1
  fi
  ok "检查 1：DOC_MAP.md 可解析（${ROWCOUNT} 行）"
else
  HAS_MAP=0
  for f in AGENTS.md STATUS.md README.md; do
    if [ -f "$ROOT/$f" ]; then
      printf '%s\t\t\t\t\t1\n' "$f" >> "$ROWS"
    fi
  done
  ROWCOUNT=$(wc -l < "$ROWS" | tr -d ' ')
  ok "检查 1：没有 DOC_MAP.md，按最小档检查（只允许 AGENTS.md、STATUS.md、README.md）"
fi

awk -F'\t' '{ p = $1; sub(/\/$/, "", p); print p }' "$ROWS" > "$IDX"

# ---------- 检查 2：地图里的路径都存在 ----------
MISSING=0
while IFS= read -r p; do
  [ -n "$p" ] || continue
  if [ ! -e "$ROOT/$p" ]; then
    bad "检查 2：地图路径不存在：${p}"
    MISSING=$((MISSING+1))
  fi
done < "$IDX"
if [ "$MISSING" -eq 0 ]; then
  ok "检查 2：地图路径全部存在（${ROWCOUNT} 行）"
fi

# ---------- 检查 3：仓库内 .md 都被覆盖或已豁免；隐藏目录不扫 ----------
# 豁免块：<!-- docmap:exclude:begin --> ... <!-- docmap:exclude:end -->
if [ "$HAS_MAP" -eq 1 ]; then
  awk '
    /<!--[ \t]*docmap:exclude:begin[ \t]*-->/ { inb = 1; next }
    /<!--[ \t]*docmap:exclude:end[ \t]*-->/   { inb = 0; next }
    inb { print }
  ' "$MAP" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' | grep -v '^$' | grep -v '^#' > "$EXCL"
fi

find "$ROOT" -mindepth 1 \
  -type d \( -name '.*' -o -name node_modules -o -name vendor -o -name dist -o -name build -o -name __pycache__ \) -prune -o \
  -type f -name '*.md' -print > "$FILES"

while IFS= read -r f; do
  [ -n "$f" ] || continue
  rel=${f#"$ROOT"/}

  skip=0
  while IFS= read -r pat; do
    [ -n "$pat" ] || continue
    # 豁免模式允许通配（如 docs/archive/*），此处刻意按 glob 匹配而非字面量
    # shellcheck disable=SC2254
    case "$rel" in $pat) skip=1; break ;; esac
  done < "$EXCL"
  [ "$skip" -eq 1 ] && continue

  covered=0
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    if [ "$rel" = "$p" ]; then covered=1; break; fi
    case "$rel" in "$p"/*) covered=1; break ;; esac
  done < "$IDX"

  if [ "$covered" -eq 0 ]; then
    if [ "$HAS_MAP" -eq 1 ]; then
      printf '检查 3：未被地图覆盖：%s\n' "$rel" >> "$MSGS"
    else
      printf '检查 3：超出进门三件：%s（先建 DOC_MAP.md）\n' "$rel" >> "$MSGS"
    fi
  fi
done < "$FILES"
if [ -s "$MSGS" ]; then
  flush bad "检查 3"
else
  ok "检查 3：所有 .md 都已覆盖或豁免"
fi

# ---------- 检查 4：被索引的文档有元信息头，且层与地图行一致 ----------
cut -f1,2 "$ROWS" > "$TMPD/heads"
while IFS=$'\t' read -r p lvl; do
  case "$p" in *.md) ;; *) continue ;; esac
  [ "$p" = "AGENTS.md" ] && continue
  f="$ROOT/$p"
  [ -f "$f" ] || continue
  hd=$(awk -v max="$HEAD_SCAN_LINES" '
    NR > max { exit }
    index($0, "> L") == 1 && index($0, "| 权威：") > 0 && index($0, "不权威：") > 0 {
      print substr($0, 3, 2)
      exit
    }
  ' "$f")
  if [ -z "$hd" ]; then
    printf '检查 4：缺元信息头：%s（应为 > Lx | 权威：… | 不权威：…）\n' "$p" >> "$MSGS"
  elif [ -n "$lvl" ] && [ "$hd" != "$lvl" ]; then
    printf '检查 4：层不一致：%s（地图 %s，文档头 %s）\n' "$p" "$lvl" "$hd" >> "$MSGS"
  fi
done < "$TMPD/heads"
if [ -s "$MSGS" ]; then
  flush warnf "检查 4"
else
  ok "检查 4：被索引文档的元信息头都合规"
fi

# ---------- 检查 5：STATUS 的状态枚举与证据列 ----------
STATUS=""
while IFS= read -r p; do
  case "$p" in *STATUS.md|*status.md) STATUS="$ROOT/$p"; break ;; esac
done < "$IDX"

if [ -z "$STATUS" ] || [ ! -f "$STATUS" ]; then
  warnf "检查 5：找不到 STATUS.md，进度无法机检"
else
  BADST=0
  while IFS=$'\t' read -r b st ev; do
    [ -n "$b" ] || continue
    case "$st" in
      未开始|进行中|进行中（待验证）|已完成|受阻|已取消) ;;
      *) bad "检查 5：状态值非法「${st}」（批次 ${b}）；只允许 未开始/进行中/进行中（待验证）/已完成/受阻/已取消"
         BADST=$((BADST+1)) ;;
    esac
    case "$st" in
      已完成)
        case "$ev" in
          ""|"-"|"—"|"待补"|"见上文"|"已测")
            bad "检查 5：批次 ${b} 标了已完成但证据列为空或空指代"
            BADST=$((BADST+1)) ;;
        esac ;;
    esac
  done <<EOF
$(awk -F'|' '
  /^[ \t]*\|/ {
    b=$2; gsub(/^[ \t]+|[ \t]+$/,"",b)
    if (b=="" || b=="批次") next
    if (b ~ /^[-: ]+$/) next
    st=$4; gsub(/^[ \t]+|[ \t]+$/,"",st); gsub(/`/,"",st)
    ev=$5; gsub(/^[ \t]+|[ \t]+$/,"",ev)
    print b "\t" st "\t" ev
  }' "$STATUS")
EOF
  [ "$BADST" -eq 0 ] && ok "检查 5：STATUS 状态与证据列合规"
fi

# ---------- 检查 6：文档内相对链接的目标存在 ----------
while IFS= read -r f; do
  [ -n "$f" ] || continue
  dir=$(dirname "$f")
  grep -oE '\]\([^)]+\)' "$f" 2>/dev/null | sed -e 's/^](//' -e 's/)$//' > "$TMPD/links"
  while IFS= read -r t; do
    [ -n "$t" ] || continue
    case "$t" in
      http://*|https://*|mailto:*|\#*|/*) continue ;;
      *'%'*) continue ;;
    esac
    t=${t%%#*}
    [ -n "$t" ] || continue
    if [ ! -e "$dir/$t" ] && [ ! -e "$ROOT/$t" ]; then
      printf '检查 6：死链 %s → %s\n' "${f#"$ROOT"/}" "$t" >> "$MSGS"
    fi
  done < "$TMPD/links"
done < "$FILES"
if [ -s "$MSGS" ]; then
  flush warnf "检查 6"
else
  ok "检查 6：文档内相对链接均可解析"
fi

# ---------- 检查 7–9：词表与标签（只在有地图时） ----------
if [ "$HAS_MAP" -eq 1 ]; then
  awk -v lc="$TMPD/vocab.lines" "$AWK_TAGS"'
    function emit(kind, s,    n, a, i) {
      n = split(tags(s), a, "|")
      for (i = 1; i <= n; i++) print kind "\t" a[i]
    }
    /<!--[ \t]*doctags:begin[ \t]*-->/ { inb = 1; next }
    /<!--[ \t]*doctags:end[ \t]*-->/   { inb = 0; next }
    !inb { next }
    { lines++ }
    /^#+[ \t]*主题标签/ { kind = "主题"; next }
    /^#+[ \t]*时机标签/ { kind = "时机"; next }
    /^#+[ \t]*修改事件/ { kind = "事件"; next }
    kind != "" { emit(kind, $0) }
    END { print lines + 0 > lc }
  ' "$MAP" > "$VOCAB"
fi

if [ "$HAS_MAP" -eq 1 ] && [ ! -s "$VOCAB" ]; then
  bad "检查 7：DOC_MAP.md 缺 doctags 词表，标签无从核对"
elif [ "$HAS_MAP" -eq 1 ]; then
  # 检查 7：地图行三段齐全，标签都在对应词表内
  awk -F'\t' -v vocab="$VOCAB" '
    BEGIN {
      while ((getline line < vocab) > 0) { split(line, f, "\t"); known[f[1], f[2]] = 1 }
    }
    function chk(list, kind, path,    n, a, i) {
      n = split(list, a, "|")
      for (i = 1; i <= n; i++)
        if (!((kind, a[i]) in known)) print "检查 7：词表外的" kind "标签【" a[i] "】：" path
    }
    $6 != 1 { print "检查 7：地图行格式不对：" $1 "（应为 反引号路径 Lx — 关于【】；在【】时读；在【】时改）"; next }
    { chk($3, "主题", $1); chk($4, "时机", $1); chk($5, "事件", $1) }
  ' "$ROWS" > "$MSGS"
  if [ -s "$MSGS" ]; then
    flush bad "检查 7"
  else
    ok "检查 7：地图行三段齐全，标签都在词表内"
  fi

  # 检查 8：同一个标签不能跨类，否则 grep 分不清它在哪一段
  awk -F'\t' '
    !(($2, $1) in seen) { seen[$2, $1] = 1; cnt[$2]++; kinds[$2] = kinds[$2] " " $1 }
    END { for (t in cnt) if (cnt[t] > 1) print "检查 8：标签【" t "】跨类同名：" kinds[t] }
  ' "$VOCAB" | sort > "$MSGS"
  if [ -s "$MSGS" ]; then
    flush bad "检查 8"
  else
    ok "检查 8：标签没有跨类同名"
  fi

  # 检查 9：频率只管主题父级；时机标签和修改事件低频是常态，不查
  awk -F'\t' -v vocab="$VOCAB" -v freq_min="$MIN_DOCS_FOR_FREQ" -v cap_exempt="$CAP_EXEMPT_MAX_DOCS" \
      -v low="$MIN_PARENT_DOCS" -v high="$MAX_PARENT_PCT" '
    function parent(t,    i) { i = index(t, "-"); return i ? substr(t, 1, i - 1) : t }
    BEGIN {
      while ((getline line < vocab) > 0) {
        split(line, f, "\t")
        all[f[2]] = 1
        if (f[1] == "主题") { topic[f[2]] = 1; par[parent(f[2])] = 1 }
      }
    }
    {
      rows++
      split("", seen)
      n = split($3, a, "|")
      for (i = 1; i <= n; i++) {
        used[a[i]] = 1
        p = parent(a[i])
        if (!(p in seen)) { seen[p] = 1; cnt[p]++ }
      }
    }
    END {
      for (p in par)
        for (t in all)
          if (t != p && index(t, p) == 1 && index(t, p "-") != 1)
            print "检查 9：前缀碰撞：主题父级【" p "】和【" t "】，按父级查询时会混在一起"
      if (rows < freq_min) exit
      for (p in par) {
        c = cnt[p] + 0
        if (c == 0)
          print "检查 9：词表里未使用的主题标签【" p "】"
        else if (c < low)
          print "检查 9：主题父级【" p "】只覆盖 " c " 份（至少 " low " 份）"
        else if (rows > cap_exempt && c * 100 > rows * high)
          print "检查 9：主题父级【" p "】覆盖 " c " 份，超过 " high "%（共 " rows " 份）"
      }
      for (t in topic)
        if (index(t, "-") > 0 && !(t in used))
          print "检查 9：词表里未使用的主题标签【" t "】"
    }
  ' "$ROWS" | sort > "$MSGS"

  READ_TAGS=$(grep -c '^时机' "$VOCAB")
  if [ "$READ_TAGS" -gt "$MAX_READ_TAGS" ]; then
    printf '检查 9：时机标签 %s 个，超过 %s 个\n' "$READ_TAGS" "$MAX_READ_TAGS" >> "$MSGS"
  fi
  VOCAB_LINES=$(cat "$TMPD/vocab.lines")
  if [ "$VOCAB_LINES" -gt "$MAX_VOCAB_LINES" ]; then
    printf '检查 9：词表 %s 行，超过 %s 行\n' "$VOCAB_LINES" "$MAX_VOCAB_LINES" >> "$MSGS"
  fi
fi

# 检查 9 的预算线：AGENTS.md 每次会话都付费，有没有地图都要查
AGENTS_LINES=$(wc -l < "$AGENTS" | tr -d ' ')
if [ "$AGENTS_LINES" -gt "$MAX_AGENTS_LINES" ]; then
  printf '检查 9：AGENTS.md %s 行，超过 %s 行\n' "$AGENTS_LINES" "$MAX_AGENTS_LINES" >> "$MSGS"
fi
if [ -s "$MSGS" ]; then
  flush warnf "检查 9"
else
  ok "检查 9：频率、前缀与预算都在线内"
fi

# ---------- 汇总 ----------
summary

if [ "$FAIL" -gt 0 ]; then exit 1; fi
if [ "$STRICT" -eq 1 ] && [ "$WARN" -gt 0 ]; then
  echo "（--strict：WARN 也算失败）"
  exit 1
fi
exit 0
