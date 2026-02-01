#!/bin/bash
# 创建简单的 SVG 图标并转换为 PNG

# 创建 SVG
cat > icon.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <rect width="128" height="128" fill="#2196F3" rx="20"/>
  <text x="64" y="85" font-family="Arial" font-size="70" fill="white" text-anchor="middle" font-weight="bold">G</text>
</svg>
SVGEOF

echo "✅ SVG 图标已创建"
echo "💡 请使用在线工具将 icon.svg 转换为 16x16, 48x48, 128x128 的 PNG"
echo "   推荐网站: https://cloudconvert.com/svg-to-png"
echo ""
echo "或者暂时删除 manifest.json 中的 icons 配置，扩展也能正常工作"
