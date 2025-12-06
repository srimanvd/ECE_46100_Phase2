
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

class PackageRating(BaseModel):
    bus_factor: float
    bus_factor_latency: float
    code_quality: float
    code_quality_latency: float
    ramp_up_time: float
    ramp_up_time_latency: float
    responsive_maintainer: float
    responsive_maintainer_latency: float
    license: float
    license_latency: float
    good_pinning_practice: float
    good_pinning_practice_latency: float
    reviewedness: float
    reviewedness_latency: float
    net_score: float
    net_score_latency: float
    treescore: float
    treescore_latency: float
    reproducibility: float
    reproducibility_latency: float
    performance_claims: float
    performance_claims_latency: float
    dataset_and_code_score: float
    dataset_and_code_score_latency: float
    dataset_quality: float
    dataset_quality_latency: float
    size: float
    size_latency: float
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
