import type { ProteinParams } from '@/types'

// 采样参数约束：与后端 backend/app/main.py 中的 RESIDUES_*/CONFORMATIONS_* 保持一致，
// 前后端共用同一套取值范围与判定规则
export const PARAM_RULES = {
  residues: { min: 3, max: 50, label: '残基数' },
  conformations: { min: 100, max: 5000, label: '构象数量' },
} as const

/** 校验采样参数，返回 null 表示合法，否则返回指明是哪一项不合规的提示 */
export function validateProteinParams(params: Partial<Record<keyof ProteinParams, unknown>>): string | null {
  for (const key of ['residues', 'conformations'] as const) {
    const rule = PARAM_RULES[key]
    const value = params[key]
    if (value === undefined || value === null || value === '') {
      return `缺少必填参数：${rule.label}（${key}）`
    }
    if (typeof value !== 'number' || !Number.isInteger(value)) {
      return `参数 ${rule.label}（${key}）必须是整数，收到 ${value}`
    }
    if (value < rule.min) {
      return `参数 ${rule.label}（${key}）不能小于 ${rule.min}，收到 ${value}`
    }
    if (value > rule.max) {
      return `参数 ${rule.label}（${key}）不能大于 ${rule.max}，收到 ${value}`
    }
  }
  return null
}
