/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import 'axios'

declare module 'axios' {
  export interface AxiosRequestConfig {
    /**
     * 是否显示 loading 遮罩
     * plugins/loading.ts
     */
    loading?: boolean

    /**
     * 请求异常时是否显示 toast 提示
     * plugins/error-toast.ts
     */
    errorToast?: boolean

    /**
     * 取消重复请求
     * plugins/repeat.ts
     */
    cancelRepeat?: boolean
    repeatKey?: string

    /**
     * 展开接口数据
     * 将 response.data.data 提升到 response.data
     * plugins/service.ts
     */
    unwrap?: boolean
  }

  // D 为对齐 axios 原始 AxiosResponse<T, D> 签名所必需（声明合并要求参数列表一致），此处无法使用
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- 见上，仅签名占位
  export interface AxiosResponse<T, D> {
    /**
     * 展开接口数据前的原始数据
     * plugins/service.ts
     */
    _data?: {
      code: number
      msg: string
      data: T
    }
  }
}
