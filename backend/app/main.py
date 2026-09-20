import math
import random
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Protein Folding Analyzer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 采样参数约束的唯一口径：取值范围、上限与字段说明都以此为准，
# 前端 frontend/src/constants.ts 中的 PARAM_RULES 必须与此保持一致。
PARAM_RULES = {
    "residues":     {"label": "残基数",  "min": 3,   "max": 50},
    "conformations": {"label": "构象数量", "min": 100, "max": 5000},
}

RAMACHANDRAN_REGIONS = [
    {"name": "alpha-helix", "phi": (-100, -30), "psi": (-80, -10)},
    {"name": "beta-sheet",  "phi": (-180, -45), "psi": (60, 180)},
    {"name": "left-helix",  "phi": (20, 100),   "psi": (-40, 80)},
    {"name": "beta-sheet-2","phi": (-180, -45), "psi": (-180, -60)},
]

def classify_region(phi: float, psi: float) -> str:
    for region in RAMACHANDRAN_REGIONS:
        if region["phi"][0] <= phi <= region["phi"][1] and region["psi"][0] <= psi <= region["psi"][1]:
            name = region["name"]
            return "beta-sheet" if name == "beta-sheet-2" else name
    return "disallowed"

def lennard_jones_energy(phi: float, psi: float, sigma: float = 3.4, epsilon: float = 0.5) -> float:
    """Simplified Lennard-Jones potential for phi-psi angle pair"""
    r = math.sqrt(phi * phi + psi * psi) / 180.0 * 3.0 + 2.0
    r = max(r, 1.0)
    ratio = sigma / r
    return 4 * epsilon * (ratio ** 12 - ratio ** 6) + epsilon

class SampleRequest(BaseModel):
    # 不设默认值：缺失即视为不合法，由校验异常处理器给出明确提示
    residues: int = Field(ge=PARAM_RULES["residues"]["min"], le=PARAM_RULES["residues"]["max"])
    conformations: int = Field(ge=PARAM_RULES["conformations"]["min"], le=PARAM_RULES["conformations"]["max"])

def _describe_validation_error(err: dict) -> str:
    """把单条校验错误翻译成指明具体字段的中文提示"""
    loc = [x for x in err.get("loc", []) if x != "body"]
    field = loc[-1] if loc else None
    rule = PARAM_RULES.get(field) if isinstance(field, str) else None
    if rule is None:
        return "请求体格式不正确：需要 JSON 对象，包含 residues 与 conformations 两个整数参数"
    label = f"{rule['label']}（{field}）"
    err_type = err.get("type", "")
    if err_type == "missing":
        return f"缺少必填参数：{label}"
    if err_type in ("int_parsing", "int_from_float", "int_type"):
        return f"参数不合法：{label} 必须为整数"
    return f"参数越界：{label} 的取值范围为 {rule['min']}–{rule['max']}"

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        msg = _describe_validation_error(err)
        if msg not in messages:
            messages.append(msg)
    return JSONResponse(status_code=400, content={"detail": "；".join(messages)})

class ConformationOut(BaseModel):
    id: int
    phi: float
    psi: float
    energy: float
    region: str
    cluster: str

class SampleResponse(BaseModel):
    params: dict
    conformations: list[ConformationOut]
    energyRange: list[float]
    stats: dict

@app.post("/api/sample", response_model=SampleResponse)
def sample_conformations(req: SampleRequest):
    confs = []
    for i in range(req.conformations):
        phi = random.uniform(-180, 180)
        psi = random.uniform(-180, 180)
        energy = lennard_jones_energy(phi, psi) + random.gauss(0, 0.05)
        region = classify_region(phi, psi)
        confs.append({
            "id": i + 1, "phi": round(phi, 2), "psi": round(psi, 2),
            "energy": round(energy, 3), "region": region
        })

    energies = [c["energy"] for c in confs]
    e_min, e_max = min(energies), max(energies)
    clusters = ["low-energy", "mid-energy", "high-energy"]
    for c in confs:
        t = (c["energy"] - e_min) / (e_max - e_min or 1)
        c["cluster"] = clusters[0] if t < 0.33 else (clusters[1] if t < 0.67 else clusters[2])

    regions = [c["region"] for c in confs]
    stats = {"alpha": regions.count("alpha-helix"), "beta": regions.count("beta-sheet"),
             "left": regions.count("left-helix"), "disallowed": regions.count("disallowed")}

    return SampleResponse(
        params={"residues": req.residues, "conformations": req.conformations},
        conformations=confs, energyRange=[e_min, e_max], stats=stats
    )