import type { ProteinParams } from './types'

// 采样参数约束的唯一口径，与后端 backend/app/main.py 中的 PARAM_RULES 保持一致，
// 修改取值范围或上限时两边必须同步更新。
export const PARAM_RULES = {
  residues: { label: '残基数', min: 3, max: 50 },
  conformations: { label: '构象数量', min: 100, max: 5000 },
} as const

/** 逐项校验采样参数，返回指明具体字段的提示列表；为空表示全部合法 */
export function validateParams(params: Partial<Record<keyof ProteinParams, number | null>>): string[] {
  const errors: string[] = []
  for (const key of Object.keys(PARAM_RULES) as (keyof typeof PARAM_RULES)[]) {
    const rule = PARAM_RULES[key]
    const value = params[key]
    if (value === undefined || value === null || Number.isNaN(value)) {
      errors.push(`缺少必填参数：${rule.label}`)
    } else if (!Number.isInteger(value)) {
      errors.push(`参数不合法：${rule.label} 必须为整数`)
    } else if (value < rule.min || value > rule.max) {
      errors.push(`参数越界：${rule.label} 的取值范围为 ${rule.min}–${rule.max}`)
    }
  }
  return errors
}
