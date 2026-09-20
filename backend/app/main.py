import math
import random
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Protein Folding Analyzer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 采样参数约束：与前端 src/constants/params.ts 共用同一套取值范围，
# 所有入口（页面、直接调用 API 等）都按这套规则判定
RESIDUES_MIN, RESIDUES_MAX = 3, 50
CONFORMATIONS_MIN, CONFORMATIONS_MAX = 100, 5000

FIELD_LABELS = {"residues": "残基数", "conformations": "构象数量"}

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
    residues: int = Field(ge=RESIDUES_MIN, le=RESIDUES_MAX,
                          description=f"残基数，取值 {RESIDUES_MIN}–{RESIDUES_MAX}")
    conformations: int = Field(ge=CONFORMATIONS_MIN, le=CONFORMATIONS_MAX,
                               description=f"构象数量，取值 {CONFORMATIONS_MIN}–{CONFORMATIONS_MAX}")


def _field_name(loc: tuple) -> str:
    parts = [str(x) for x in loc if x not in ("body", "query", "path")]
    field = parts[-1] if parts else ""
    label = FIELD_LABELS.get(field)
    return f"{label}（{field}）" if label else (field or "请求体")


@app.exception_handler(RequestValidationError)
async def sample_validation_handler(request: Request, exc: RequestValidationError):
    """参数越界/缺失时返回明确提示（指明是哪一项不合规），而不是抛出 500"""
    problems = []
    for err in exc.errors():
        name = _field_name(err.get("loc", ()))
        etype, ctx, value = err.get("type", ""), err.get("ctx") or {}, err.get("input")
        if etype == "missing":
            problems.append(f"缺少必填参数：{name}" if name != "请求体"
                            else "请求体缺失，需提供 residues（残基数）与 conformations（构象数量）")
        elif etype == "greater_than_equal":
            problems.append(f"参数 {name} 不能小于 {ctx.get('ge')}，收到 {value}")
        elif etype == "less_than_equal":
            problems.append(f"参数 {name} 不能大于 {ctx.get('le')}，收到 {value}")
        elif etype in ("int_parsing", "int_from_float"):
            problems.append(f"参数 {name} 必须是整数，收到 {value}")
        else:
            problems.append(f"参数 {name} 不合法：{err.get('msg', '')}")
    return JSONResponse(status_code=400, content={"detail": "；".join(problems)})

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