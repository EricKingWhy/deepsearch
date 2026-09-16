/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import { AxiosResponse } from 'axios'

/**
 * 取响应体 —— 全仓唯一的出口（T70）。
 *
 * 本 client **不解包**（`unwrap` 契约已于 T70 删除，见 `./request.ts`）：
 * 调用方拿到的始终是 `AxiosResponse`，响应体在 `response.data`。
 * 所有 api module 一律经此取体，不再各自写 `const res = await …; return res.data`
 * （`api/news.ts` 曾把同一句抄 8 遍 —— 约定只该有一个归属地）。
 *
 * 将来若要改回「client 解包」，只需改这里一处。
 */
export async function readBody<T>(response: Promise<AxiosResponse<T>>): Promise<T> {
  return (await response).data
}
