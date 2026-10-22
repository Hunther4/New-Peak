import React, { useMemo } from "react"
import { marked } from "marked"

// Configure marked for clean GFM with line breaks
marked.setOptions({
  breaks: true,
  gfm: true,
})

export function MathRenderer({ text = "", className = "", inline = false }) {
  const htmlContent = useMemo(() => {
    if (!text || typeof text !== "string") return ""

    const mathBlocks = []

    // 1. Protect display math $$...$$
    let protectedText = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, expr) => {
      const idx = mathBlocks.length
      mathBlocks.push({ display: true, expr: expr.trim() })
      return `@@MATH_BLOCK_${idx}@@`
    })

    // 2. Protect inline math $...$
    // Ensure we do not match escaped dollars \$ or empty dollars $$
    protectedText = protectedText.replace(/(^|[^\\])\$([^\$\n]+?)\$/g, (_, prefix, expr) => {
      const idx = mathBlocks.length
      mathBlocks.push({ display: false, expr: expr.trim() })
      return `${prefix}@@MATH_BLOCK_${idx}@@`
    })

    // 3. Unescape any \$ to literal $
    protectedText = protectedText.replace(/\\\$/g, "$")

    // Determine if we should parse as inline snippet (options, single formulas) or full block document
    const hasNewlines = protectedText.includes("\n")
    const isBlockMarkdown = hasNewlines || /^(#|-|\d+\.|>)\s/.test(protectedText.trim())
    const shouldInline = inline || !isBlockMarkdown

    // 4. Parse markdown with marked
    let parsedHtml = ""
    try {
      if (shouldInline) {
        parsedHtml = marked.parseInline(protectedText)
      } else {
        parsedHtml = marked.parse(protectedText)
      }
    } catch {
      parsedHtml = protectedText
    }

    // 5. Re-inject rendered KaTeX
    const finalHtml = parsedHtml.replace(/@@MATH_BLOCK_(\d+)@@/g, (_, idStr) => {
      const block = mathBlocks[Number(idStr)]
      if (!block) return ""

      if (typeof window !== "undefined" && window.katex) {
        try {
          return window.katex.renderToString(block.expr, {
            displayMode: block.display,
            throwOnError: false,
          })
        } catch {
          return block.display
            ? `<div class="font-mono text-emerald-400 my-2 text-center overflow-x-auto">${block.expr}</div>`
            : `<span class="font-mono text-emerald-400">${block.expr}</span>`
        }
      }

      return block.display
        ? `<div class="font-mono text-emerald-400 my-2 text-center overflow-x-auto">${block.expr}</div>`
        : `<span class="font-mono text-emerald-400">${block.expr}</span>`
    })

    return finalHtml
  }, [text, inline])

  const Component = inline ? "span" : "div"

  return (
    <Component
      className={`leading-relaxed text-neutral-200 
        [&_p]:mb-3 [&_p:last-child]:mb-0 
        [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:my-2.5 [&_ul]:space-y-1.5
        [&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:my-2.5 [&_ol]:space-y-1.5
        [&_li]:leading-relaxed
        [&_strong]:text-white [&_strong]:font-bold
        [&_em]:text-neutral-300 [&_em]:italic
        [&_code]:bg-neutral-800/80 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded-md [&_code]:font-mono [&_code]:text-emerald-300 [&_code]:text-[11px]
        [&_blockquote]:border-l-2 [&_blockquote]:border-emerald-500/40 [&_blockquote]:pl-3 [&_blockquote]:italic [&_blockquote]:text-neutral-400 [&_blockquote]:my-2
        [&_hr]:border-white/[0.08] [&_hr]:my-4
        ${className}`}
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  )
}
