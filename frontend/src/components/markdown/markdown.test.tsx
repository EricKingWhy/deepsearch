import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import Markdown from './index'

/**
 * P-18 回归测试：`marked`（v5 起已移除内置 `sanitize`）的输出必须先消毒再写进 DOM。
 *
 * 这些用例故意走**渲染后的真实 DOM**，而不是断言「源码里出现了 DOMPurify」——
 * 只有这样才能被「撤掉消毒」的变异击穿（见 tickets.md 的变异检验表）。
 */

function renderMarkdown(value: string) {
  const utils = render(<Markdown value={value} />)
  const root = utils.container.firstElementChild as HTMLElement
  return { ...utils, root, html: root.innerHTML }
}

describe('Markdown 输出消毒（P-18）', () => {
  it('剥离 <script> 标签，且不留下可执行内容', () => {
    const { root, html } = renderMarkdown('<script>window.__pwned = 1</script>\n\n正文')

    expect(root.querySelector('script')).toBeNull()
    expect(html).not.toContain('<script')
    expect(html).not.toContain('__pwned')
    // 正常文本仍应保留 —— 消毒不能把正文一起删掉
    expect(html).toContain('正文')
  })

  it('剥离内联事件处理器（onerror / onload / onclick）', () => {
    const { root } = renderMarkdown(
      '<img src="x" onerror="window.__pwned = 1">\n\n<p onclick="window.__pwned = 1">t</p>\n\n' +
        '<body onload="window.__pwned = 1">',
    )

    for (const el of Array.from(root.querySelectorAll('*'))) {
      for (const attr of Array.from(el.attributes)) {
        expect(attr.name.toLowerCase().startsWith('on')).toBe(false)
      }
    }
  })

  it('剥离 javascript: 协议的链接', () => {
    const { root, html } = renderMarkdown('[点我](javascript:alert(1))')

    expect(html).not.toMatch(/javascript:/i)
    for (const a of Array.from(root.querySelectorAll('a'))) {
      expect(a.getAttribute('href') ?? '').not.toMatch(/javascript:/i)
    }
  })

  it('自定义图片渲染的属性插值不能闭合属性并注入事件处理器', () => {
    // renderer.image 把 markdown 的 alt / title 直接拼进 HTML 字符串；若 payload 里带 `"`
    // 就能闭合 alt 并追加 onerror。消毒在写 DOM 前进行，必须把它剥掉。
    const { root, html } = renderMarkdown('![x" onerror="window.__pwned=1](https://example.com/a.png)')

    expect(html).not.toMatch(/onerror/i)
    for (const el of Array.from(root.querySelectorAll('*'))) {
      for (const attr of Array.from(el.attributes)) {
        expect(attr.name.toLowerCase().startsWith('on')).toBe(false)
      }
    }
  })

  it('保留正常 Markdown 结构（消毒不误删合法内容）', () => {
    const { html } = renderMarkdown('## 标题\n\n**加粗** 与 [链接](https://example.com)\n\n- 一\n- 二')

    expect(html).toContain('<h2')
    expect(html).toContain('<strong>')
    expect(html).toContain('<ul>')
    expect(html).toContain('href="https://example.com"')
  })

  it('保留合法图片（含 data: 内联图）与懒加载属性', () => {
    const remote = renderMarkdown('![图](https://example.com/a.png)')
    expect(remote.root.querySelector('img')?.getAttribute('src')).toBe('https://example.com/a.png')
    expect(remote.root.querySelector('img')?.getAttribute('loading')).toBe('lazy')
    expect(remote.root.querySelector('img')?.getAttribute('class')).toBe('markdown-image')

    // 图表以 base64 内联返回，必须放行；否则「可视化图表」会整片空白
    const dataUri = 'data:image/png;base64,iVBORw0KGgo='
    const inline = renderMarkdown(`![图](${dataUri})`)
    expect(inline.root.querySelector('img')?.getAttribute('src')).toBe(dataUri)
  })

  it('无效图片 URL 仍被隐藏（保留原有行为）', () => {
    const { root } = renderMarkdown('![图](ftp://example.com/a.png)')

    expect(root.querySelector('img')).toBeNull()
  })
})
