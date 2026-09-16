/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ResponseError } from './error'
import { readBody } from './read-body'
import { createRequest } from './request'

/**
 * T70 契约测试：client **不解包**。
 *
 * 此前 `index.ts` 声明了 `unwrap: true`（「把 response.data.data 提升到
 * response.data」），但没有任何插件读取它 —— interface 承诺了一件实现从不做的事。
 * T70 选择删除该选项，并把「调用方拿到 AxiosResponse、响应体在 `response.data`」
 * 显式写进 `createRequest` 的文档。本文件把这条契约钉住。
 *
 * 全部用例走注入的 axios `adapter`，不触网。
 */

function clientReturning(body: unknown, configs: Record<string, unknown> = {}) {
  return createRequest({
    adapter: async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => ({
      data: body,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    }),
    loading: false,
    errorToast: false,
    cancelRepeat: false,
    ...configs,
  })
}

afterEach(() => {
  vi.restoreAllMocks()
  Reflect.deleteProperty(window, '$app')
})

describe('request client 契约（T70）', () => {
  it('不解包：调用方拿到 AxiosResponse，响应体在 response.data', async () => {
    const body = { id: 1, name: '示例' }

    const response = await clientReturning(body).get<typeof body>('/demo')

    expect(response.status).toBe(200)
    expect(response.data).toEqual(body)
  })

  it('响应体「碰巧带 data 字段」时不被改写 —— 重新引入 unwrap 会让这条变红', async () => {
    // /news/list 的真实形状：data 只是业务字段之一，total / stats 必须活着。
    // 按 `unwrap` 声明的语义（response.data = response.data.data）实现，这里会只剩 [1, 2]。
    const body = { success: true, data: [1, 2], total: 2, stats: { recent_24h: 1 } }

    const response = await clientReturning(body).get<typeof body>('/news/list')

    expect(response.data).toEqual(body)
    expect(response.data.total).toBe(2)
    expect(response.data.stats).toEqual({ recent_24h: 1 })
  })

  it('不再暴露 _data（该类型随 unwrap 契约一并删除）', async () => {
    const response = await clientReturning({ a: 1 }).get('/demo')

    expect(Reflect.get(response, '_data')).toBeUndefined()
  })

  it('readBody 是唯一的取体出口：直接给到后端返回体', async () => {
    const body = { value: 42 }

    await expect(readBody(clientReturning(body).get<typeof body>('/demo'))).resolves.toEqual(body)
  })

  it('业务失败仍以 ResponseError 抛出后端 msg，且 toast 能取到（错误分支不回归）', async () => {
    const errorToast = vi.fn()
    Object.assign(window, { $app: { message: { error: errorToast } } })
    const client = clientReturning({ status: 'error', message: '业务级失败' }, { errorToast: true })

    await expect(client.get('/demo')).rejects.toBeInstanceOf(ResponseError)
    await expect(
      client.get('/demo').then(
        () => 'resolved',
        (error: Error) => error.message,
      ),
    ).resolves.toBe('业务级失败')
    expect(errorToast).toHaveBeenCalledWith('业务级失败')
  })
})
