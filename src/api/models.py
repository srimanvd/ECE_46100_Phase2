
from pydantic import BaseModel, Field

# --- Package Models ---

class PackageMetadata(BaseModel):
    Name: str = Field(..., description="Package name")
    Version: str = Field(..., description="Package version")
    ID: str = Field(..., description="Package ID")

class PackageData(BaseModel):
    Content: str | None = Field(None, description="Base64 encoded zip file content", alias="content")
    URL: str | None = Field(None, description="Package URL (for ingest)", alias="url")
    JSProgram: str | None = Field(None, description="JavaScript program for sensitive modules", alias="jsprogram")
    Name: str | None = Field(None, description="Package name (optional)", alias="name")

    class Config:
        populate_by_name = True

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
    Name: str = Field(..., description="Package name", alias="name")
    Version: str | None = Field(None, description="Package version", alias="version")
    Types: list[str] | None = Field(None, description="Package types", alias="types")

    class Config:
        populate_by_name = True

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
