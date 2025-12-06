
from pydantic import BaseModel, Field

# --- Package Models ---

class PackageMetadata(BaseModel):
    name: str = Field(..., description="Package name")
    version: str = Field(..., description="Package version")
    id: str = Field(..., description="Package ID")
    type: str = Field("code", description="Package type")

class PackageData(BaseModel):
    content: str | None = Field(None, description="Base64 encoded zip file content")
    url: str | None = Field(None, description="Package URL (for ingest)")
    jsprogram: str | None = Field(None, description="JavaScript program for sensitive modules")
    name: str | None = Field(None, description="Package name (optional)")

class Package(BaseModel):
    metadata: PackageMetadata
    data: PackageData

class MetricScore(BaseModel):
    score: float
    latency: float

class PackageRating(BaseModel):
    bus_factor: MetricScore
    bus_factor_latency: float
    code_quality: MetricScore
    code_quality_latency: float
    ramp_up_time: MetricScore
    ramp_up_time_latency: float
    responsive_maintainer: MetricScore
    responsive_maintainer_latency: float
    license: MetricScore
    license_latency: float
    good_pinning_practice: MetricScore
    good_pinning_practice_latency: float
    reviewedness: MetricScore
    reviewedness_latency: float
    net_score: MetricScore
    net_score_latency: float
    tree_score: MetricScore
    tree_score_latency: float
    reproducibility: MetricScore
    reproducibility_latency: float
    performance_claims: MetricScore
    performance_claims_latency: float
    dataset_and_code_score: MetricScore
    dataset_and_code_score_latency: float
    dataset_quality: MetricScore
    dataset_quality_latency: float
    size_score: MetricScore
    size_score_latency: float
    name: str | None = None
    category: str | None = None

class PackageHistoryEntry(BaseModel):
    User: dict
    Date: str
    PackageMetadata: PackageMetadata
    Action: str

class PackageQuery(BaseModel):
    name: str = Field(..., description="Package name")
    version: str | None = Field(None, description="Package version")
    types: list[str] | None = Field(None, description="Package types")

class PackageRegEx(BaseModel):
    RegEx: str = Field(..., description="Regex for searching packages")

# --- User/Auth Models ---

class User(BaseModel):
    name: str
    isAdmin: bool

class AuthenticationRequest(BaseModel):
    User: User
    Secret: str

class AuthenticationToken(BaseModel):
    bearerToken: str

# --- Error Models ---

class Error(BaseModel):
    code: int
    message: str
