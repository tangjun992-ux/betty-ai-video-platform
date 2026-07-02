#!/bin/bash
# betty 平台 — 竞品对标监控脚本 (fixed)
set -uo pipefail

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_DIR="/home/tom/ai-video-platform/.benchmarks"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date '+%Y%m%d-%H%M%S').log"
SUMMARY="$LOG_DIR/changelog.md"

declare -A COMPETITORS=(
  ["yapper"]="https://yapper.so"
  ["midjourney"]="https://www.midjourney.com"
  ["runway"]="https://runwayml.com"
  ["leonardo"]="https://leonardo.ai"
  ["krea"]="https://www.krea.ai"
  ["ideogram"]="https://ideogram.ai"
)

fetch_snapshot() {
  local name=$1
  local url=$2
  local out="$LOG_DIR/${name}_$(date '+%Y%m%d-%H%M').html"
  
  curl -sL -m 15 -A "Mozilla/5.0 (compatible; betty-benchmark/1.0)" \
    -o "$out" "$url" 2>/dev/null || {
    echo "  ❌ $name: 连接失败" | tee -a "$LOG_FILE"
    return 1
  }
  
  local size=$(wc -c < "$out" 2>/dev/null || echo 0)
  local title=$(grep -oP '<title>\K[^<]+' "$out" 2>/dev/null | head -1 || echo "N/A")
  
  echo "  ✅ $name: ${size} bytes | title=\"$title\"" | tee -a "$LOG_FILE"
  echo "  📊 $name 特征:" >> "$LOG_FILE"
  
  { grep -oP 'https?://[^"'"'"' ]*(api|sdk|generate|create|v1|v2)[^"'"'"' ]*' "$out" 2>/dev/null || true; } | \
    sort -u | head -5 | while read -r endpoint; do
    [ -n "$endpoint" ] && echo "     - API: $endpoint" >> "$LOG_FILE"
  done
  
  { grep -oP '(react@|next@|tailwindcss@)[0-9.]+' "$out" 2>/dev/null || true; } | \
    sort -u | head -3 | while read -r dep; do
    [ -n "$dep" ] && echo "     - 依赖: $dep" >> "$LOG_FILE"
  done
  
  for keyword in "video" "3d" "edit" "collaboration" "team" "api" "mobile" "real-time" "live" "community"; do
    grep -qi "$keyword" "$out" 2>/dev/null && echo "     - 特性: $keyword" >> "$LOG_FILE" || true
  done
  
  return 0
}

detect_changes() {
  local name=$1
  local prev=$(ls -t "$LOG_DIR/${name}_"*.html 2>/dev/null | head -2 | tail -1)
  local curr=$(ls -t "$LOG_DIR/${name}_"*.html 2>/dev/null | head -1)
  
  [ -z "$prev" ] || [ -z "$curr" ] || [ "$prev" = "$curr" ] && return 0
  
  local prev_size=$(wc -c < "$prev" 2>/dev/null || echo 0)
  local curr_size=$(wc -c < "$curr" 2>/dev/null || echo 0)
  local diff_pct=0
  
  [ "$prev_size" -gt 0 ] && diff_pct=$(( (curr_size - prev_size) * 100 / prev_size ))
  
  if [ "${diff_pct#-}" -gt 5 ]; then
    echo "  🔔 **$name 有变化!** (页面大小: ${prev_size}→${curr_size}, ${diff_pct}%)" | tee -a "$SUMMARY"
  fi
}

echo "## betty 竞品对标 — $TIMESTAMP" > "$LOG_FILE"
echo "" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"

success=0
total=${#COMPETITORS[@]}

for name in "${!COMPETITORS[@]}"; do
  echo "📡 正在抓取 $name..." | tee -a "$LOG_FILE"
  if fetch_snapshot "$name" "${COMPETITORS[$name]}"; then
    detect_changes "$name"
    ((success++))
  fi
  echo "" >> "$LOG_FILE"
done

echo "---" >> "$LOG_FILE"
echo "**结果: $success/$total 成功** ($TIMESTAMP)" >> "$LOG_FILE"

echo "✅ 对标完成: $success/$total 个竞品成功 ($LOG_FILE)"
