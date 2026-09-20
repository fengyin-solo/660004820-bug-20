import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { Conformation, SamplingResult, ProteinParams } from '@/types'
import { validateProteinParams } from '@/constants/params'

export const useProteinStore = defineStore('protein', () => {
  const loading = ref(false)
  const result = ref<SamplingResult | null>(null)
  const selectedConformation = ref<Conformation | null>(null)
  const selectedCluster = ref('all')

  async function runSampling(params: ProteinParams) {
    const invalid = validateProteinParams(params)
    if (invalid) { ElMessage.error(invalid); return }
    loading.value = true
    try {
      const { data } = await axios.post('/api/sample', params)
      result.value = data
      selectedConformation.value = null
      selectedCluster.value = 'all'
    } catch (err) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : null
      ElMessage.error(typeof detail === 'string' ? detail : '采样请求失败，请稍后重试')
    } finally { loading.value = false }
  }

  function selectConformation(conf: Conformation) { selectedConformation.value = conf }
  function filterByCluster(cluster: string) { selectedCluster.value = cluster }

  return { loading, result, selectedConformation, selectedCluster, runSampling, selectConformation, filterByCluster }
})
