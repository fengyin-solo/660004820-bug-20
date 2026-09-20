<template>
  <div class="control-card">
    <el-form :model="form" inline>
      <el-form-item label="残基数">
        <el-input-number v-model="form.residues" :min="PARAM_RULES.residues.min" :max="PARAM_RULES.residues.max" />
      </el-form-item>
      <el-form-item label="构象数量">
        <el-input-number v-model="form.conformations" :min="PARAM_RULES.conformations.min" :max="PARAM_RULES.conformations.max" :step="100" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="emitSample" :loading="store.loading">🎲 生成构象采样</el-button>
      </el-form-item>
    </el-form>
    <div class="filters" v-if="store.result">
      <el-radio-group v-model="activeCluster" @change="onCluster">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="alpha-helix">α-螺旋</el-radio-button>
        <el-radio-button label="beta-sheet">β-折叠</el-radio-button>
        <el-radio-button label="left-helix">左手螺旋</el-radio-button>
        <el-radio-button label="disallowed">禁阻区</el-radio-button>
      </el-radio-group>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue"
import { useProteinStore } from "../store/protein"
import { PARAM_RULES } from "../constants/params"
const emit = defineEmits<{ sample: [params: { residues: number; conformations: number }] }>()
const store = useProteinStore()
const form = reactive({ residues: 10, conformations: 1000 })
const activeCluster = ref("all")
function emitSample() { emit("sample", { ...form }) }
function onCluster(val: string) { store.filterByCluster(val) }
</script>

<style scoped>
.control-card { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.filters { margin-top: 12px; }
</style>
