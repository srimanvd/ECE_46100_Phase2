
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
    BusFactor: float
    BusFactorLatency: float
    Correctness: float
    CorrectnessLatency: float
    RampUp: float
    RampUpLatency: float
    ResponsiveMaintainer: float
    ResponsiveMaintainerLatency: float
    LicenseScore: float
    LicenseScoreLatency: float
    GoodPinningPractice: float
    GoodPinningPracticeLatency: float
    PullRequest: float
    PullRequestLatency: float
    NetScore: float
    NetScoreLatency: float
    TreeScore: float
    TreeScoreLatency: float
    Reproducibility: float
    ReproducibilityLatency: float

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
